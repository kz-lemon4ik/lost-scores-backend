from sqlalchemy import desc, func
from sqlalchemy.orm import Session, joinedload

from app.models.submission import Submission
from app.schemas.submission import SubmissionCreate


def create_submission(db: Session, submission: SubmissionCreate, user_id: int) -> Submission:
    db_submission = Submission(**submission.model_dump(), user_id=user_id)
    db.add(db_submission)
    db.commit()
    db.refresh(db_submission)
    return db_submission


def get_recent_submissions(db: Session, limit: int = 100) -> list[Submission]:
    return (
        db.query(Submission)
        .options(joinedload(Submission.user))
        .order_by(desc(Submission.scan_timestamp))
        .limit(limit)
        .all()
    )


def get_latest_submission_by_username(db: Session, username: str) -> Submission | None:
    return (
        db.query(Submission)
        .options(joinedload(Submission.user))
        .filter(func.lower(Submission.username) == username.lower())
        .order_by(desc(Submission.scan_timestamp))
        .first()
    )


def get_top_delta_submissions(db: Session, limit: int = 100) -> list[Submission]:
    return (
        db.query(Submission)
        .options(joinedload(Submission.user))
        .order_by(desc(Submission.delta_pp))
        .limit(limit)
        .all()
    )
