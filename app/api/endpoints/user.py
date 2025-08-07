from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
import httpx
from datetime import datetime, timezone

from app.api import deps
from app.core import security
from app.core.config import settings
from app.crud import crud_user, crud_token

router = APIRouter()


@router.get("/me")
async def get_current_user(request: Request, db: Session = Depends(deps.get_db)):
    cookie_value = request.cookies.get(settings.SESSION_COOKIE_NAME)

    if not cookie_value:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = security.decode_session_token(cookie_value)
        user_id = int(payload.get("sub"))
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = crud_user.get_user(db, user_id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id": user.id,
        "username": user.username,
        "osu_user_id": user.osu_user_id,
    }


@router.get("/{user_id}/osu-data")
async def get_osu_user_data(user_id: int, db: Session = Depends(deps.get_db)):
    user = crud_user.get_user_by_osu_id(db, osu_user_id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    token = crud_token.get_token_by_owner_id(db, owner_id=user.id)
    if not token:
        raise HTTPException(status_code=404, detail="No osu! token found for user")

    if token.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Token expired")

    async with httpx.AsyncClient() as client:
        try:
            headers = {"Authorization": f"Bearer {token.access_token}"}
            response = await client.get(
                f"https://osu.ppy.sh/api/v2/users/{user_id}/osu", headers=headers
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=exc.response.status_code,
                detail=f"Failed to fetch osu! data: {exc.response.text}",
            )
