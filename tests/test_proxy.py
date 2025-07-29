import pytest
import datetime
from unittest.mock import patch, AsyncMock
from httpx import Response
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.token import Token

PATCH_TARGET = "app.core.osu_api_client.httpx"


@pytest.mark.asyncio
async def test_proxy_success(
    authenticated_client: TestClient, test_user_with_token: User
):
    mock_api_response = {"id": test_user_with_token.osu_user_id, "username": "testuser"}
    mock_get_response = Response(status_code=200, json=mock_api_response)

    mocked_client_instance = AsyncMock()
    mocked_client_instance.request.return_value = mock_get_response

    with patch(PATCH_TARGET) as mock_httpx:
        mock_httpx.AsyncClient.return_value = mocked_client_instance
        response = authenticated_client.get("/api/proxy/me")

    assert response.status_code == 200
    assert response.json() == mock_api_response
    mocked_client_instance.request.assert_called_once()


@pytest.mark.asyncio
async def test_proxy_token_refresh(
    authenticated_client: TestClient, test_user_with_token: User, db_session: Session
):
    expired_token = (
        db_session.query(Token)
        .filter(Token.owner_id == test_user_with_token.id)
        .first()
    )
    expired_token.expires_at = datetime.datetime.utcnow() - datetime.timedelta(
        minutes=30
    )  # type: ignore
    db_session.commit()

    new_token_payload = {
        "access_token": "new_refreshed_access_token",
        "refresh_token": "new_refreshed_refresh_token",
        "expires_in": 7200,
    }
    mock_refresh_response = Response(status_code=200, json=new_token_payload)

    mock_api_response = {"id": test_user_with_token.osu_user_id, "username": "testuser"}
    mock_get_response = Response(status_code=200, json=mock_api_response)

    mocked_client_instance = AsyncMock()
    mocked_client_instance.post.return_value = mock_refresh_response
    mocked_client_instance.request.return_value = mock_get_response

    with patch(PATCH_TARGET) as mock_httpx:
        mock_httpx.AsyncClient.return_value = mocked_client_instance
        response = authenticated_client.get("/api/proxy/me")

    assert response.status_code == 200
    assert response.json() == mock_api_response

    mocked_client_instance.post.assert_called_once()
    mocked_client_instance.request.assert_called_once()

    refreshed_token_in_db = (
        db_session.query(Token)
        .filter(Token.owner_id == test_user_with_token.id)
        .first()
    )
    assert refreshed_token_in_db.access_token == "new_refreshed_access_token"  # type: ignore
