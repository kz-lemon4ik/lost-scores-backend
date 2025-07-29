from pydantic import BaseModel, ConfigDict
import datetime


class SubmissionBase(BaseModel):
    total_pp_gain: float
    lost_scores_count: int


class SubmissionCreate(SubmissionBase):
    report_path: str


class Submission(SubmissionBase):
    id: int
    user_id: int
    submission_date: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class SubmissionLeaderboard(BaseModel):
    rank: int
    username: str
    osu_user_id: int
    total_pp_gain: float
    lost_scores_count: int
    submission_date: datetime.datetime
