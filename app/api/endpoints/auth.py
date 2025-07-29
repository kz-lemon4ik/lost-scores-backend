import secrets
import base64
import json
from fastapi import Request, APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
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

    request.session["oauth_csrf"] = state_data["csrf_token"]

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
        "port": "5174",  # Default to dev server port
        "client_type": "web",
    }

    state_str = json.dumps(state_data)
    state_b64 = base64.urlsafe_b64encode(state_str.encode()).decode()

    request.session["oauth_csrf"] = state_data["csrf_token"]

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
    if "oauth_csrf" not in request.session:
        raise HTTPException(
            status_code=403, detail="OAuth CSRF token missing from session."
        )

    try:
        state_json = base64.urlsafe_b64decode(state).decode()
        state_data = json.loads(state_json)
    except (ValueError, TypeError, json.JSONDecodeError):
        raise HTTPException(status_code=400, detail="Invalid state parameter.")

    if request.session.pop("oauth_csrf") != state_data.get("csrf_token"):
        raise HTTPException(status_code=403, detail="OAuth CSRF token mismatch.")

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
    client_type = state_data.get("client_type", "web")  # Default to web

    if callback_port:
        if client_type == "desktop":
            # Для desktop приложений отправляем callback на локальный порт приложения
            callback_url = f"http://localhost:{callback_port}/?jwt_token={session_jwt}&user_id={osu_user_id}&username={username}"
            response = RedirectResponse(url=callback_url)
        elif client_type == "web":
            # Для web OAuth делаем redirect обратно на главную страницу (пользователь уже аутентифицирован через cookie)
            if callback_port == "5174":  # Lost Scores Site dev server
                callback_url = "http://localhost:5174/"
            elif callback_port == "443":  # Production HTTPS (lost.lemon4ik.kz)
                callback_url = "https://lost.lemon4ik.kz/"
            else:
                # Fallback для других портов
                callback_url = f"http://localhost:{callback_port}/"
            response = RedirectResponse(url=callback_url)
        else:
            # Legacy: определяем тип клиента по порту
            if callback_port == "5174" or callback_port == "443":
                # Веб клиент - редирект на главную
                if callback_port == "5174":
                    callback_url = "http://localhost:5174/"
                else:
                    callback_url = "https://lost.lemon4ik.kz/"
            else:
                # Desktop клиент - показываем success страницу
                callback_url = f"http://localhost:5174/oauth/success?username={username}&user_id={osu_user_id}&source=desktop"
            response = RedirectResponse(url=callback_url)
    else:
        response = JSONResponse(
            content=SessionToken(
                session_token=session_jwt, token_type="bearer"
            ).model_dump()
        )

    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=session_jwt,
        httponly=True,
        max_age=settings.SESSION_COOKIE_EXPIRE_SECONDS,
        samesite="lax",
    )
    return response
