import secrets
import base64
import json
from fastapi import Request, APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from sqlalchemy.orm import Session
import httpx

from app.core.config import settings
from app.schemas.user import UserCreate
from app.schemas.token import OsuToken, SessionToken
from app.crud import crud_user, crud_token
from app.core import security
from app.api import deps

router = APIRouter()

OSU_API_BASE_URL = "https://osu.ppy.sh"


@router.get("/login")
async def login(
    request: Request, callback_port: int | None = None, client_type: str | None = None
):
    redirect_uri = settings.OSU_REDIRECT_URI

    state_data = {"csrf_token": secrets.token_urlsafe(16)}
    if callback_port:
        state_data["port"] = str(callback_port)
    if client_type:
        state_data["client_type"] = client_type

    state_str = json.dumps(state_data)
    state_b64 = base64.urlsafe_b64encode(state_str.encode()).decode()

    authorization_url = (
        f"https://osu.ppy.sh/oauth/authorize?client_id={settings.OSU_CLIENT_ID}"
        f"&redirect_uri={redirect_uri}&response_type=code&scope=public"
        f"&state={state_b64}"
    )
    return RedirectResponse(url=authorization_url)


@router.get("/web-login")
async def web_login(request: Request):
    """Dedicated endpoint for web OAuth flow - redirects back to home page after auth"""
    redirect_uri = settings.OSU_REDIRECT_URI

    state_data = {
        "csrf_token": secrets.token_urlsafe(16),
        "port": None,
        "client_type": "web",
    }

    state_str = json.dumps(state_data)
    state_b64 = base64.urlsafe_b64encode(state_str.encode()).decode()

    authorization_url = (
        f"https://osu.ppy.sh/oauth/authorize?client_id={settings.OSU_CLIENT_ID}"
        f"&redirect_uri={redirect_uri}&response_type=code&scope=public"
        f"&state={state_b64}"
    )
    return RedirectResponse(url=authorization_url)


@router.get("/callback")
async def auth_callback(
    code: str, state: str, request: Request, db: Session = Depends(deps.get_db)
):
    try:
        state_json = base64.urlsafe_b64decode(state).decode()
        state_data = json.loads(state_json)
    except (ValueError, TypeError, json.JSONDecodeError):
        raise HTTPException(status_code=400, detail="Invalid state parameter.")

    if not state_data.get("csrf_token"):
        raise HTTPException(status_code=403, detail="OAuth CSRF token missing.")

    token_url = f"{OSU_API_BASE_URL}/oauth/token"
    token_data = {
        "client_id": settings.OSU_CLIENT_ID,
        "client_secret": settings.OSU_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": settings.OSU_REDIRECT_URI,
    }

    async with httpx.AsyncClient() as client:
        try:
            token_response = await client.post(token_url, data=token_data)
            token_response.raise_for_status()
            osu_token_data = OsuToken(**token_response.json())

            headers = {"Authorization": f"Bearer {osu_token_data.access_token}"}
            user_response = await client.get(
                f"{OSU_API_BASE_URL}/api/v2/me/osu", headers=headers
            )
            user_response.raise_for_status()
            osu_user_profile = user_response.json()

        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=exc.response.status_code,
                detail=f"Failed to communicate with osu! API: {exc.response.text}",
            )

    osu_user_id = osu_user_profile.get("id")
    username = osu_user_profile.get("username")

    user = crud_user.get_user_by_osu_id(db, osu_user_id=osu_user_id)
    if not user:
        user_in = UserCreate(osu_user_id=osu_user_id, username=username)
        user = crud_user.create_user(db, user=user_in)

    crud_token.create_or_update_token(db, token_data=osu_token_data, user_id=user.id)

    session_jwt = security.create_session_token(data={"sub": str(user.id)})

    callback_port = state_data.get("port")
    client_type = state_data.get("client_type", "web")

    if client_type == "desktop" and callback_port:
        callback_url = f"http://localhost:{callback_port}/?jwt_token={session_jwt}&user_id={osu_user_id}&username={username}"
        response = RedirectResponse(url=callback_url)
    elif client_type == "web":
        callback_url = f"{settings.FRONTEND_BASE_URL}/oauth/success?jwt_token={session_jwt}&username={username}&user_id={osu_user_id}"
        response = RedirectResponse(url=callback_url)
    else:
        response = JSONResponse(
            content=SessionToken(
                session_token=session_jwt, token_type="bearer"
            ).model_dump()
        )

    return response
