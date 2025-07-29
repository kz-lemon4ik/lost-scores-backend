from typing import Generator, AsyncGenerator
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt
from jose.exceptions import JWTError
from pydantic import ValidationError
from sqlalchemy.orm import Session
import httpx

from app.db.session import SessionLocal
from app.core.config import settings
from app.models import user as user_model
from app.core import security
from app.crud import crud_user

reusable_oauth2 = HTTPBearer()


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    async with httpx.AsyncClient() as client:
        yield client


def get_current_user(
    db: Session = Depends(get_db),
    token_obj: HTTPAuthorizationCredentials = Depends(reusable_oauth2),
) -> user_model.User:
    token = token_obj.credentials
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            )
    except (JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    user = db.query(user_model.User).filter(user_model.User.id == int(user_id)).first()

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return user


def get_current_user_from_cookie(
    request: Request, db: Session = Depends(get_db)
) -> user_model.User:
    """
    Gets the current user from the session cookie.
    Raises HTTPException if the user is not logged in or the token is invalid.
    """
    token = request.session.get(settings.SESSION_COOKIE_NAME)
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated via cookie",
        )

    try:
        payload = security.decode_session_token(token)
        user_id = payload.get("sub") if payload else None
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: No user ID in payload",
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials from cookie",
        )

    user = crud_user.get_user(db, user_id=int(user_id)) if user_id else None
    if not user:
        raise HTTPException(status_code=404, detail="User from token not found")

    return user


def get_current_user_from_cookie_optional(
    request: Request, db: Session = Depends(get_db)
) -> user_model.User | None:
    """
    Tries to get the current user from the session cookie.
    If the user is not logged in or the token is invalid, returns None instead of raising an exception.
    """
    try:
        return get_current_user_from_cookie(request, db)
    except HTTPException:
        return None
