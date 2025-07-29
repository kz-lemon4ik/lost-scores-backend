import json
import shutil
import uuid
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api import deps
from app.core import security
from app.models.user import User
from app.crud import crud_submission
from app.schemas.submission import SubmissionCreate, SubmissionLeaderboard

router = APIRouter()

STORAGE_PATH = Path("storage")
REPORTS_PATH = STORAGE_PATH / "reports"

REPORTS_PATH.mkdir(parents=True, exist_ok=True)


def secure_filename(filename: str) -> str:
    """Creates a secure version of a filename."""
    safe_name = Path(filename).name
    return safe_name


@router.post("/submit")
async def submit_hall_of_fame_entry(
    report_summary: str = Form(...),
    hmac_signature: str = Form(...),
    report_file: UploadFile = File(...),
    replay_files: List[UploadFile] = File([]),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    report_content = await report_file.read()
    await report_file.close()

    if not security.verify_hmac_signature(report_content, hmac_signature):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid HMAC signature. Data may be tampered.",
        )

    try:
        summary_data = json.loads(report_summary)
        total_pp_gain = float(summary_data.get("total_pp_gain", 0.0))
        lost_scores_count = int(summary_data.get("lost_scores_count", 0))
    except (json.JSONDecodeError, ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid report_summary format.",
        )

    submission_id = str(uuid.uuid4())
    user_submission_dir = REPORTS_PATH / str(current_user.id) / submission_id
    user_submission_dir.mkdir(parents=True, exist_ok=True)

    report_filename = f"{submission_id}.json"
    report_path = user_submission_dir / report_filename
    with open(report_path, "wb") as buffer:
        buffer.write(report_content)

    for replay_file in replay_files:
        safe_replay_name = secure_filename(replay_file.filename or "replay.osr")
        replay_path = user_submission_dir / safe_replay_name
        try:
            with open(replay_path, "wb") as buffer:
                shutil.copyfileobj(replay_file.file, buffer)
        finally:
            await replay_file.close()

    submission_in = SubmissionCreate(
        total_pp_gain=total_pp_gain,
        lost_scores_count=lost_scores_count,
        report_path=str(report_path),
    )
    crud_submission.create_submission(
        db, submission=submission_in, user_id=current_user.id
    )

    return {"message": "Submission successful", "submission_id": submission_id}


@router.get("/", response_model=List[SubmissionLeaderboard])
async def get_hall_of_fame_leaderboard(db: Session = Depends(deps.get_db)):
    submissions = crud_submission.get_top_submissions(db, limit=100)

    leaderboard = []
    for rank, sub in enumerate(submissions, 1):
        leaderboard.append(
            {
                "rank": rank,
                "username": sub.user.username,
                "osu_user_id": sub.user.osu_user_id,
                "total_pp_gain": sub.total_pp_gain,
                "lost_scores_count": sub.lost_scores_count,
                "submission_date": sub.submission_date,
            }
        )

    return leaderboard


@router.get("/replays/{submission_id}/{replay_filename}")
async def download_replay(
    submission_id: str,
    replay_filename: str,
    current_user: User = Depends(deps.get_current_user),
):
    if ".." in replay_filename or "/" in replay_filename or "\\" in replay_filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filename."
        )

    # Validate access permissions for the submission
    replay_path = REPORTS_PATH / str(current_user.id) / submission_id / replay_filename

    if not replay_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Replay not found."
        )

    return FileResponse(
        path=replay_path,
        media_type="application/octet-stream",
        filename=replay_filename,
    )
