import httpx
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.token import Token
from app.crud import crud_token

OSU_API_BASE_URL = "https://osu.ppy.sh"
logger = logging.getLogger(__name__)


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
