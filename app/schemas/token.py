from pydantic import BaseModel
import datetime


class OsuToken(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int


class Token(BaseModel):
    access_token: str
    refresh_token: str
    expires_at: datetime.datetime
    owner_id: int


class TokenCreate(Token):
    pass


class TokenUpdate(BaseModel):
    access_token: str
    refresh_token: str
    expires_at: datetime.datetime


class SessionToken(BaseModel):
    session_token: str
    token_type: str
