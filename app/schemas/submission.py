from datetime import datetime
from pydantic import BaseModel, ConfigDict


class SubmissionBase(BaseModel):
    username: str
    scan_timestamp: datetime
    lost_count: int
    current_pp: float
    potential_pp: float
    delta_pp: float
    thin_json_path: str


class SubmissionCreate(SubmissionBase):
    pass


class Submission(SubmissionBase):
    id: int
    user_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SubmissionSummary(BaseModel):
    username: str
    user_id: int
    scan_date: datetime
    lost_scores_count: int
    total_pp_gain: float
    current_pp: float
    potential_pp: float


class SubmissionLeaderboard(BaseModel):
    rank: int
    username: str
    osu_user_id: int
    total_pp_gain: float
    lost_scores_count: int
    submission_date: datetime
