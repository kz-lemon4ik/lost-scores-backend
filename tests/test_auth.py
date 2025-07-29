import pytest
from unittest.mock import patch, AsyncMock
from httpx import Response
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.crud import crud_user


@pytest.mark.asyncio
async def test_auth_callback_creates_user(client: TestClient, db_session: Session):
    mock_osu_token_payload = {
        "access_token": "fake_osu_access_token",
        "refresh_token": "fake_osu_refresh_token",
        "expires_in": 7200,
        "token_type": "Bearer",
    }
    mock_osu_user_profile = {"id": 12345678, "username": "TestUser"}

    mock_post_response = Response(status_code=200, json=mock_osu_token_payload)
    mock_get_response = Response(status_code=200, json=mock_osu_user_profile)

    with (
        patch(
            "httpx.AsyncClient.post",
            new_callable=AsyncMock,
            return_value=mock_post_response,
        ) as mock_post,
        patch(
            "httpx.AsyncClient.get",
            new_callable=AsyncMock,
            return_value=mock_get_response,
        ) as mock_get,
    ):
        response = client.get("/api/auth/callback?code=fake_auth_code")

    assert response.status_code == 200
    response_data = response.json()
    assert "session_token" in response_data
    assert response_data["token_type"] == "bearer"

    user = crud_user.get_user_by_osu_id(
        db_session, osu_user_id=mock_osu_user_profile["id"]
    )
    assert user is not None
    assert user.username == mock_osu_user_profile["username"]

    mock_post.assert_called_once()
    mock_get.assert_called_once()
