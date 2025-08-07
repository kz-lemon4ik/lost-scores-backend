import httpx
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.token import Token
from app.crud import crud_token

OSU_API_BASE_URL = "https://osu.ppy.sh"
logger = logging.getLogger(__name__)

_client_credentials_token: Optional[dict] = None


class OsuAPIClient:
    def __init__(self, db_session: Session, user_token: Token):
        self.db = db_session
        self.token = user_token
        self.client = httpx.AsyncClient(timeout=60.0)

    async def _get_valid_access_token(self) -> str:
        current_time = datetime.now(timezone.utc)
        expires_at = self.token.expires_at

        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if current_time >= expires_at - timedelta(minutes=10):
            await self._refresh_token()
        return str(self.token.access_token)

    async def _refresh_token(self):
        token_url = f"{OSU_API_BASE_URL}/oauth/token"
        refresh_data = {
            "client_id": settings.OSU_CLIENT_ID,
            "client_secret": settings.OSU_CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": self.token.refresh_token,
        }

        response = await self.client.post(token_url, data=refresh_data)

        new_token_data = response.json()
        self.token = crud_token.update_refreshed_token(
            db=self.db, db_token=self.token, new_token_data=new_token_data
        )

    async def make_request(self, method: str, endpoint: str, **kwargs):
        access_token = await self._get_valid_access_token()
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {access_token}"
        headers["Accept"] = "application/json"

        url = f"{OSU_API_BASE_URL}{endpoint}"

        try:
            response = await self.client.request(method, url, headers=headers, **kwargs)
            result = response.json()
            return result
        except Exception as e:
            logger.error(f"osu! API request failed: {method} {endpoint} - {e}")
            raise

    async def get_user(self, user_identifier: str | int, mode: str = "osu"):
        endpoint = f"/api/v2/users/{user_identifier}/{mode}"
        return await self.make_request("GET", endpoint)

    async def close(self):
        await self.client.aclose()


async def get_client_credentials_token() -> str:
    global _client_credentials_token

    current_time = datetime.now(timezone.utc)

    if _client_credentials_token and _client_credentials_token["expires_at"] > current_time:
        return _client_credentials_token["access_token"]

    async with httpx.AsyncClient() as client:
        token_url = f"{OSU_API_BASE_URL}/oauth/token"
        data = {
            "client_id": settings.OSU_CLIENT_ID,
            "client_secret": settings.OSU_CLIENT_SECRET,
            "grant_type": "client_credentials",
            "scope": "public"
        }

        response = await client.post(token_url, data=data)
        response.raise_for_status()
        token_data = response.json()

        _client_credentials_token = {
            "access_token": token_data["access_token"],
            "expires_at": current_time + timedelta(seconds=token_data["expires_in"])
        }

        return token_data["access_token"]


async def get_public_user_data(user_identifier: str | int, mode: str = "osu") -> dict:
    access_token = await get_client_credentials_token()

    async with httpx.AsyncClient(timeout=30.0) as client:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }

        url = f"{OSU_API_BASE_URL}/api/v2/users/{user_identifier}/{mode}"

        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
