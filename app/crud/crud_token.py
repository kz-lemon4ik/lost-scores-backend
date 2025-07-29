from sqlalchemy.orm import Session
from app.models.token import Token
from app.schemas.token import OsuToken
from datetime import datetime, timedelta, timezone


def get_token_by_owner_id(db: Session, owner_id: int):
    return db.query(Token).filter(Token.owner_id == owner_id).first()


def create_or_update_token(db: Session, token_data: OsuToken, user_id: int) -> Token:
    db_token = get_token_by_owner_id(db, owner_id=user_id)

    expires_at = datetime.now(timezone.utc) + timedelta(seconds=token_data.expires_in)

    if db_token:
        db_token.access_token = token_data.access_token  # type: ignore
        db_token.refresh_token = token_data.refresh_token  # type: ignore
        db_token.expires_at = expires_at  # type: ignore
    else:
        db_token = Token(
            owner_id=user_id,
            access_token=token_data.access_token,
            refresh_token=token_data.refresh_token,
            expires_at=expires_at,
        )
        db.add(db_token)

    db.commit()
    db.refresh(db_token)
    return db_token


def update_refreshed_token(db: Session, db_token: Token, new_token_data: dict) -> Token:
    new_expires_at = datetime.now(timezone.utc) + timedelta(
        seconds=new_token_data["expires_in"]
    )

    db_token.access_token = new_token_data["access_token"]
    db_token.refresh_token = new_token_data["refresh_token"]
    db_token.expires_at = new_expires_at  # type: ignore

    db.commit()
    db.refresh(db_token)
    return db_token
