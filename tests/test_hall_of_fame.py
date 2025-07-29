# import pytest  # type: ignore
import io
import hmac
import hashlib
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User
from app.models.submission import Submission


def test_submit_success(
    authenticated_client: TestClient, test_user: User, db_session: Session
):
    report_content = b'{"total_pp_gain": 123.45, "lost_scores_count": 5}'
    report_summary = '{"total_pp_gain": 123.45, "lost_scores_count": 5}'

    expected_signature = hmac.new(
        key=settings.HMAC_SECRET_KEY.encode(),
        msg=report_content,
        digestmod=hashlib.sha256,
    ).hexdigest()

    mock_report_file_tuple = (
        "report.json",
        io.BytesIO(report_content),
        "application/json",
    )
    mock_replay_file_tuple = (
        "replay.osr",
        io.BytesIO(b"replay_data"),
        "application/octet-stream",
    )

    response = authenticated_client.post(
        "/api/hall-of-fame/submit",
        data={
            "report_summary": report_summary,
            "hmac_signature": expected_signature,
        },
        files=[
            ("report_file", mock_report_file_tuple),
            ("replay_files", mock_replay_file_tuple),
        ],
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Submission successful"

    submission_in_db = (
        db_session.query(Submission).filter(Submission.user_id == test_user.id).first()
    )  # type: ignore
    assert submission_in_db is not None
    assert submission_in_db.total_pp_gain == 123.45


def test_submit_invalid_hmac(authenticated_client: TestClient):
    report_content = b'{"total_pp_gain": 100, "lost_scores_count": 2}'
    report_summary = '{"total_pp_gain": 100, "lost_scores_count": 2}'
    invalid_signature = "this_is_a_wrong_signature"

    mock_report_file = ("report.json", io.BytesIO(report_content), "application/json")

    response = authenticated_client.post(
        "/api/hall-of-fame/submit",
        data={
            "report_summary": report_summary,
            "hmac_signature": invalid_signature,
        },
        files={"report_file": mock_report_file},
    )

    assert response.status_code == 403
    assert "Invalid HMAC signature" in response.json()["detail"]


def test_get_leaderboard(client: TestClient, db_session: Session):
    user1 = User(osu_user_id=1, username="PlayerOne")
    user2 = User(osu_user_id=2, username="PlayerTwo")
    db_session.add_all([user1, user2])
    db_session.commit()

    sub1 = Submission(
        user_id=user1.id, total_pp_gain=500, lost_scores_count=10, report_path="/"
    )
    sub2 = Submission(
        user_id=user2.id, total_pp_gain=1000, lost_scores_count=20, report_path="/"
    )
    db_session.add_all([sub1, sub2])
    db_session.commit()

    response = client.get("/api/hall-of-fame/")

    assert response.status_code == 200
    leaderboard = response.json()
    assert len(leaderboard) == 2
    assert leaderboard[0]["username"] == "PlayerTwo"
    assert leaderboard[0]["total_pp_gain"] == 1000
