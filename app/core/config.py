import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

env_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"
)
load_dotenv(dotenv_path=env_path)


class Settings(BaseSettings):
    OSU_CLIENT_ID: str = ""
    OSU_CLIENT_SECRET: str = ""
    OSU_REDIRECT_URI: str = ""
    SESSION_COOKIE_NAME: str = "session"
    SESSION_COOKIE_EXPIRE_SECONDS: int = 86400
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200
    DATABASE_URL: str = ""
    HMAC_SECRET_KEY: str = ""

    class Config:
        case_sensitive = True
        env_file = ".env"


settings = Settings()
