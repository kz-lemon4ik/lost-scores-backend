import json
from datetime import datetime
import shutil
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.submission import Submission

REPO_ROOT = Path(__file__).resolve().parents[1]
TEST_STORAGE_DIR = REPO_ROOT / "storage" / "test_submissions"


def _write_sample_report(path: Path):
    data = {
        "metadata": {
            "user_identifier": "PlayerOne",
            "analysis_timestamp": "2025-08-01T12:00:00",
            "user_id": 1,
        },
        "summary_stats": {
            "lost_scores_found": 2,
            "delta_pp": 150.0,
            "current_pp": 7000.0,
            "potential_pp": 7150.0,
        },
        "lost_scores": [
            {
                "pp": 100.0,
                "beatmap_id": 1,
                "beatmapset_id": 10,
                "artist": "Artist",
                "title": "Title",
                "creator": "Mapper",
                "version": "Insane",
                "mods": ["HD"],
                "accuracy": 98.5,
                "count100": 5,
                "count50": 0,
                "countMiss": 0,
                "rank": "S",
                "score_time": "2025-07-20 12:00:00",
            }
        ],
    }
    path.write_text(json.dumps(data), encoding="utf-8")


def _create_submission(db_session: Session, user: User, filename: str) -> Submission:
    TEST_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    json_path = TEST_STORAGE_DIR / filename
    _write_sample_report(json_path)
    submission = Submission(
        user_id=user.id,
        username=user.username,
        scan_timestamp=datetime(2025, 8, 1, 12, 0, 0),
        lost_count=2,
        current_pp=7000.0,
        potential_pp=7150.0,
        delta_pp=150.0,
        thin_json_path=str(json_path.relative_to(REPO_ROOT)),
    )
    db_session.add(submission)
    db_session.commit()
    db_session.refresh(submission)
    return submission


def test_list_submissions_returns_database_entries(client: TestClient, db_session: Session):
    user = User(osu_user_id=1, username="PlayerOne")
    db_session.add(user)
    db_session.commit()

    submission = _create_submission(db_session, user, "analysis_list.json")

    response = client.get("/api/submissions/list")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["username"] == submission.username
    assert payload[0]["lost_scores_count"] == submission.lost_count


def test_get_submission_returns_detail(client: TestClient, db_session: Session):
    user = User(osu_user_id=2, username="PlayerTwo")
    db_session.add(user)
    db_session.commit()

    _create_submission(db_session, user, "analysis_detail.json")

    response = client.get("/api/submissions/PlayerTwo")

    assert response.status_code == 200
    payload = response.json()
    assert payload["metadata"]["username"] == "PlayerTwo"
    assert payload["summary_stats"]["lost_scores_found"] == 2
    assert len(payload["lost_scores"]) == 1


def test_get_submission_not_found(client: TestClient):
    response = client.get("/api/submissions/UnknownUser")
    assert response.status_code == 404


def teardown_module(module):
    if TEST_STORAGE_DIR.exists():
        shutil.rmtree(TEST_STORAGE_DIR)
