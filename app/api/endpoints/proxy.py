from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
import httpx
import logging

from app.api import deps
from app.models.user import User
from app.crud import crud_token
from app.core.osu_api_client import OsuAPIClient

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/{full_path:path}")
async def proxy_get_request(
    full_path: str,
    request: Request,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    user_token = crud_token.get_token_by_owner_id(db, owner_id=int(current_user.id))
    if not user_token:
        raise HTTPException(status_code=401, detail="User has no valid osu! token")

    api_client = OsuAPIClient(db_session=db, user_token=user_token)

    api_endpoint = f"/api/v2/{full_path}"

    params_list = []
    for key in request.query_params.keys():
        values = request.query_params.getlist(key)
        for value in values:
            params_list.append((key, value))

    try:
        response_data = await api_client.make_request(
            method="GET", endpoint=api_endpoint, params=params_list
        )
        return response_data
    except httpx.HTTPStatusError as exc:
        logger.error(f"osu! API error {exc.response.status_code} for {api_endpoint}")
        raise HTTPException(
            status_code=exc.response.status_code, detail=exc.response.json()
        )
    except Exception as e:
        logger.error(f"Proxy error for {api_endpoint}: {e}")
        # Handle proxy error
        raise HTTPException(
            status_code=502,
            detail=f"An error occurred while proxying the request to osu! API: {e}",
        )
