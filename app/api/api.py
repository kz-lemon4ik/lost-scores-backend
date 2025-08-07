from fastapi import APIRouter
from app.api.endpoints import auth, proxy, hall_of_fame, user, submissions

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(user.router, prefix="/user", tags=["user"])
api_router.include_router(proxy.router, prefix="/proxy", tags=["proxy"])
api_router.include_router(
    hall_of_fame.router, prefix="/hall-of-fame", tags=["hall-of-fame"]
)
api_router.include_router(
    submissions.router, prefix="/submissions", tags=["submissions"]
)
