from datetime import datetime, timezone
from sqlalchemy import Integer, String, ForeignKey, DateTime, Float
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.db.base import Base


def utc_now():
    return datetime.now(timezone.utc)


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    total_pp_gain: Mapped[float] = mapped_column(Float, nullable=False)
    lost_scores_count: Mapped[int] = mapped_column(Integer, nullable=False)
    submission_date: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    report_path: Mapped[str] = mapped_column(String, nullable=False)

    user = relationship("User", back_populates="submissions")

    def __init__(
        self,
        user_id: int,
        total_pp_gain: float,
        lost_scores_count: int,
        report_path: str,
    ):
        super().__init__()
        self.user_id = user_id
        self.total_pp_gain = total_pp_gain
        self.lost_scores_count = lost_scores_count
        self.report_path = report_path
