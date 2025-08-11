from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import httpx
import asyncio
import logging
from app.api.deps import get_db
from app.schemas.beatmap import BeatmapEnrichRequest, BeatmapEnrichResponse, BeatmapData
from app.crud.crud_beatmap import (
    get_beatmaps_by_md5,
    create_beatmap,
    get_invalid_md5s,
    create_invalid_md5
)
from app.core.osu_api_client import get_client_credentials_token
from app.core.rate_limiter import osu_api_rate_limiter

router = APIRouter()
logger = logging.getLogger(__name__)

OSU_API_BASE_URL = "https://osu.ppy.sh"


async def fetch_beatmap_by_md5(md5_hash: str, token: str) -> dict | None:
    try:
        await osu_api_rate_limiter.acquire()
        async with httpx.AsyncClient(timeout=10.0) as client:
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json"
            }
            url = f"{OSU_API_BASE_URL}/api/v2/beatmaps/lookup?checksum={md5_hash}"
            response = await client.get(url, headers=headers)

            if response.status_code == 404:
                return None

            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Failed to fetch beatmap for MD5 {md5_hash}: {e}")
        return None


@router.post("/enrich", response_model=BeatmapEnrichResponse)
async def enrich_beatmaps(
    request: BeatmapEnrichRequest,
    db: Session = Depends(get_db)
):
    md5_hashes = request.md5_hashes
    result = {}

    invalid_md5s = get_invalid_md5s(db, md5_hashes)
    for md5 in invalid_md5s:
        result[md5] = None

    remaining_md5s = [md5 for md5 in md5_hashes if md5 not in invalid_md5s]

    cached_beatmaps = get_beatmaps_by_md5(db, remaining_md5s)
    for md5, beatmap in cached_beatmaps.items():
        if beatmap:
            result[md5] = BeatmapData(
                beatmap_id=beatmap.beatmap_id,
                beatmapset_id=beatmap.beatmapset_id,
                ranked_status=beatmap.ranked_status,
                artist=beatmap.artist,
                title=beatmap.title,
                creator=beatmap.creator,
                version=beatmap.version,
                hit_objects=beatmap.hit_objects,
                max_combo=beatmap.max_combo
            )

    missing_md5s = [md5 for md5 in remaining_md5s if md5 not in cached_beatmaps]

    if missing_md5s:
        logger.info(f"Fetching {len(missing_md5s)} missing beatmaps from osu! API")
        token = await get_client_credentials_token()
        fetch_tasks = [fetch_beatmap_by_md5(md5, token) for md5 in missing_md5s]
        fetched_data = await asyncio.gather(*fetch_tasks)

        for md5, data in zip(missing_md5s, fetched_data):
            if data is None:
                logger.info(f"MD5 {md5} returned 404, caching as invalid")
                create_invalid_md5(db, md5, "404_not_found")
                result[md5] = None
            else:
                logger.info(f"Saving beatmap {data['id']} (MD5: {md5}) to database")
                beatmap_data = {
                    "beatmap_id": data["id"],
                    "beatmapset_id": data["beatmapset_id"],
                    "ranked_status": data["status"],
                    "md5_hash": md5,
                    "artist": data["beatmapset"]["artist"],
                    "title": data["beatmapset"]["title"],
                    "creator": data["beatmapset"]["creator"],
                    "version": data["version"],
                    "hit_objects": data.get("count_circles", 0) + data.get("count_sliders", 0) + data.get("count_spinners", 0),
                    "max_combo": data.get("max_combo")
                }

                try:
                    beatmap = create_beatmap(db, beatmap_data)
                    logger.info(f"Successfully saved beatmap {beatmap.beatmap_id}")
                except Exception as e:
                    logger.error(f"Failed to save beatmap: {e}")
                    raise

                result[md5] = BeatmapData(
                    beatmap_id=beatmap.beatmap_id,
                    beatmapset_id=beatmap.beatmapset_id,
                    ranked_status=beatmap.ranked_status,
                    artist=beatmap.artist,
                    title=beatmap.title,
                    creator=beatmap.creator,
                    version=beatmap.version,
                    hit_objects=beatmap.hit_objects,
                    max_combo=beatmap.max_combo
                )

    db.commit()
    return BeatmapEnrichResponse(beatmaps=result)
