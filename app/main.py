from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api.api import api_router
from app.db.base import Base
from app.db.session import engine
from app.core.config import settings

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="osu! Lost Scores API",
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Add session middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # welcome-site dev
        "http://localhost:5174",  # lost-scores-site dev
        "https://lemon4ik.kz",  # welcome-site prod
        "https://lost.lemon4ik.kz",  # lost-scores-site prod
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Welcome to the osu! Lost Scores API"}
