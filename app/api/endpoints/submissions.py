import json
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.api.deps import get_db
from app.core.osu_api_client import get_public_user_data
from app.crud import crud_submission, crud_beatmap
from app.models.submission import Submission as SubmissionModel

logger = logging.getLogger(__name__)
router = APIRouter()

REPO_ROOT = Path(__file__).resolve().parents[3]


class SubmissionSummary(BaseModel):
    username: str
    user_id: int
    scan_date: str
    lost_scores_count: int
    total_pp_gain: float
    current_pp: float
    potential_pp: float


class LostScore(BaseModel):
    pp: float
    beatmap_id: int
    beatmapset_id: int | None = None
    artist: str
    title: str
    creator: str
    version: str
    mods: list[str]
    accuracy: float
    count100: int
    count50: int
    countMiss: int
    rank: str
    score_time: str


class CurrentUserStats(BaseModel):
    current_pp: float
    current_global_rank: int
    current_country_rank: int
    username: str
    avatar_url: str
    country_code: str


class SubmissionDetail(BaseModel):
    metadata: dict
    summary_stats: dict
    lost_scores: list[LostScore]
    current_user_stats: Optional[CurrentUserStats] = None
    total_count: Optional[int] = None


@router.get("/list", response_model=list[SubmissionSummary])
async def list_submissions(limit: int = 100, db: Session = Depends(get_db)):
    db_submissions = crud_submission.get_recent_submissions(db, limit=limit)

    return [_summary_from_db(sub) for sub in db_submissions]


@router.get("/{username}", response_model=SubmissionDetail)
async def get_submission(username: str, offset: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    db_submission = crud_submission.get_latest_submission_by_username(db, username)

    if not db_submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    return await _detail_from_db(db_submission, db, offset=offset, limit=limit)


def _summary_from_db(submission: SubmissionModel) -> SubmissionSummary:
    osu_user_id = submission.user.osu_user_id if submission.user else submission.user_id
    return SubmissionSummary(
        username=submission.username,
        user_id=osu_user_id,
        scan_date=submission.scan_timestamp.isoformat(),
        lost_scores_count=submission.lost_count,
        total_pp_gain=submission.delta_pp,
        current_pp=submission.current_pp,
        potential_pp=submission.potential_pp,
    )


async def _detail_from_db(
    submission: SubmissionModel,
    db: Session,
    offset: int,
    limit: int,
) -> SubmissionDetail:
    json_path = _resolve_path(submission.thin_json_path)

    if not json_path.exists():
        logger.warning("Submission file not found at %s", json_path)
        raise HTTPException(status_code=404, detail="Submission data not found")

    metadata, summary, raw_scores = _load_submission_file(json_path)
    total_count = len(raw_scores)
    paginated_scores = raw_scores[offset: offset + limit]

    beatmap_lookup = {}
    beatmap_ids = [score.get("beatmap_id") for score in paginated_scores if score.get("beatmap_id")]
    if beatmap_ids:
        beatmap_lookup = crud_beatmap.get_beatmaps_by_ids(db, beatmap_ids)

    lost_scores: list[LostScore] = []
    for score in paginated_scores:
        beatmap_id = score.get("beatmap_id")
        beatmapset_id = score.get("beatmapset_id")
        if beatmapset_id is None and beatmap_id in beatmap_lookup:
            beatmapset_id = beatmap_lookup[beatmap_id].beatmapset_id

        lost_scores.append(
            LostScore(
                pp=float(score.get("pp", 0.0)),
                beatmap_id=beatmap_id,
                beatmapset_id=beatmapset_id,
                artist=score.get("artist", ""),
                title=score.get("title", ""),
                creator=score.get("creator", ""),
                version=score.get("version", ""),
                mods=score.get("mods", []),
                accuracy=float(score.get("accuracy", 0.0)),
                count100=int(score.get("count100", 0)),
                count50=int(score.get("count50", 0)),
                countMiss=int(score.get("countMiss", 0)),
                rank=score.get("rank", ""),
                score_time=score.get("score_time", ""),
            )
        )

    summary_stats = _merge_summary(summary, submission)
    metadata = metadata or {}
    metadata.setdefault("username", submission.username)
    metadata.setdefault("user_id", submission.user.osu_user_id if submission.user else submission.user_id)
    metadata.setdefault("analysis_timestamp", submission.scan_timestamp.isoformat())

    current_user_stats = await _fetch_user_stats(submission)

    return SubmissionDetail(
        metadata=metadata,
        summary_stats=summary_stats,
        lost_scores=lost_scores,
        current_user_stats=current_user_stats,
        total_count=total_count,
    )



def _resolve_path(path_str: str) -> Path:
    path = Path(path_str)
    if not path.is_absolute():
        path = (REPO_ROOT / path).resolve()
    return path


def _load_submission_file(path: Path) -> tuple[dict, dict, list[dict]]:
    with open(path, "r", encoding="utf-8") as fp:
        data = json.load(fp)

    metadata = data.get("metadata", {})
    summary = data.get("summary_stats") or data.get("summary", {})

    if "score_lists" in data:
        lost_scores = data["score_lists"].get("lost_scores", [])
    else:
        lost_scores = data.get("lost_scores", [])

    return metadata, summary, lost_scores


def _merge_summary(summary: dict, submission: SubmissionModel) -> dict:
    summary_stats = dict(summary or {})

    summary_stats.setdefault("lost_scores_found", submission.lost_count)
    summary_stats.setdefault("delta_pp", submission.delta_pp)
    summary_stats.setdefault("current_pp", submission.current_pp)
    summary_stats.setdefault("potential_pp", submission.potential_pp)

    return summary_stats


async def _fetch_user_stats(submission: SubmissionModel) -> Optional[CurrentUserStats]:
    try:
        user_identifier = submission.user.osu_user_id if submission.user else submission.username
        user_data = await get_public_user_data(user_identifier, mode="osu")
        return CurrentUserStats(
            current_pp=user_data["statistics"]["pp"],
            current_global_rank=user_data["statistics"]["global_rank"],
            current_country_rank=user_data["statistics"]["country_rank"],
            username=user_data["username"],
            avatar_url=user_data["avatar_url"],
            country_code=user_data["country_code"],
        )
    except Exception as exc:
        logger.error("Failed to fetch live user data for %s: %s", submission.username, exc)
        return None
