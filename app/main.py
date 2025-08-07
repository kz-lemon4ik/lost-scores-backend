from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "https://lemon4ik.kz",
        "https://lost.lemon4ik.kz",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Welcome to the osu! Lost Scores API"}
