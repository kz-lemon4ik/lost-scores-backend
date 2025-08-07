from fastapi import APIRouter, HTTPException
from pathlib import Path
import json
import logging
from typing import Optional
from pydantic import BaseModel
from app.core.osu_api_client import get_public_user_data

logger = logging.getLogger(__name__)

router = APIRouter()

STORAGE_DIR = Path(__file__).parent.parent.parent.parent / "storage" / "submissions"


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
async def list_submissions():
    submissions = []

    if not STORAGE_DIR.exists():
        return submissions

    for submission_dir in STORAGE_DIR.iterdir():
        if not submission_dir.is_dir():
            continue

        analysis_file = submission_dir / "analysis_results.json"
        if not analysis_file.exists():
            continue

        try:
            with open(analysis_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            submissions.append(SubmissionSummary(
                username=data["metadata"]["user_identifier"],
                user_id=0,
                scan_date=data["metadata"]["analysis_timestamp"],
                lost_scores_count=data["summary_stats"]["lost_scores_found"],
                total_pp_gain=data["summary_stats"]["delta_pp"],
                current_pp=data["summary_stats"]["current_pp"],
                potential_pp=data["summary_stats"]["potential_pp"]
            ))
        except Exception as e:
            continue

    return submissions


@router.get("/{username}", response_model=Optional[SubmissionDetail])
async def get_submission(username: str, offset: int = 0, limit: int = 50):
    if not STORAGE_DIR.exists():
        raise HTTPException(status_code=404, detail="Submission not found")

    for submission_dir in STORAGE_DIR.iterdir():
        if not submission_dir.is_dir():
            continue

        analysis_file = submission_dir / "analysis_results.json"
        if not analysis_file.exists():
            continue

        try:
            with open(analysis_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            if data["metadata"]["user_identifier"].lower() == username.lower():
                sorted_scores = sorted(
                    data["lost_scores"],
                    key=lambda x: x["pp"],
                    reverse=True
                )

                total_count = len(sorted_scores)
                paginated_scores = sorted_scores[offset:offset + limit]

                lost_scores = [
                    LostScore(
                        pp=score["pp"],
                        beatmap_id=score["beatmap_id"],
                        artist=score["artist"],
                        title=score["title"],
                        creator=score["creator"],
                        version=score["version"],
                        mods=score["mods"],
                        accuracy=score["accuracy"],
                        count100=score["count100"],
                        count50=score["count50"],
                        countMiss=score["countMiss"],
                        rank=score["rank"],
                        score_time=score["score_time"]
                    )
                    for score in paginated_scores
                ]

                current_user_stats = None
                try:
                    user_data = await get_public_user_data(username, mode="osu")
                    current_user_stats = CurrentUserStats(
                        current_pp=user_data["statistics"]["pp"],
                        current_global_rank=user_data["statistics"]["global_rank"],
                        current_country_rank=user_data["statistics"]["country_rank"],
                        username=user_data["username"],
                        avatar_url=user_data["avatar_url"],
                        country_code=user_data["country_code"]
                    )
                except Exception as e:
                    logger.error(f"Failed to fetch current user data: {e}")

                return SubmissionDetail(
                    metadata=data["metadata"],
                    summary_stats=data["summary_stats"],
                    lost_scores=lost_scores,
                    current_user_stats=current_user_stats,
                    total_count=total_count
                )
        except Exception as e:
            continue

    raise HTTPException(status_code=404, detail="Submission not found")


@router.get("/{username}/image/{image_type}")
async def get_submission_image(username: str, image_type: str):
    from fastapi.responses import FileResponse

    if image_type not in ["lost_scores_result", "potential_top_result", "summary_badge"]:
        raise HTTPException(status_code=400, detail="Invalid image type")

    if not STORAGE_DIR.exists():
        raise HTTPException(status_code=404, detail="Submission not found")

    for submission_dir in STORAGE_DIR.iterdir():
        if not submission_dir.is_dir():
            continue

        analysis_file = submission_dir / "analysis_results.json"
        if not analysis_file.exists():
            continue

        try:
            with open(analysis_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            if data["metadata"]["user_identifier"].lower() == username.lower():
                image_file = submission_dir / f"{image_type}.png"
                if image_file.exists():
                    return FileResponse(
                        image_file,
                        media_type="image/png",
                        headers={"Cache-Control": "public, max-age=3600"}
                    )
        except Exception:
            continue

    raise HTTPException(status_code=404, detail="Image not found")
