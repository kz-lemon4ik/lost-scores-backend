from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from app.models.submission import Submission
from app.schemas.submission import SubmissionCreate


def create_submission(
    db: Session, submission: SubmissionCreate, user_id: int
) -> Submission:
    db_submission = Submission(**submission.model_dump(), user_id=user_id)
    db.add(db_submission)
    db.commit()
    db.refresh(db_submission)
    return db_submission


def get_top_submissions(db: Session, limit: int = 100):
    return (
        db.query(Submission)
        .options(joinedload(Submission.user))
        .order_by(desc(Submission.total_pp_gain))
        .limit(limit)
        .all()
    )
