from typing import Optional

from sqlalchemy.orm import Session

from app.models.beatmap import Beatmap
from app.models.invalid_md5 import InvalidMD5


def get_beatmaps_by_md5(db: Session, md5_hashes: list[str]) -> dict[str, Optional[Beatmap]]:
    if not md5_hashes:
        return {}
    beatmaps = db.query(Beatmap).filter(Beatmap.md5_hash.in_(md5_hashes)).all()
    return {b.md5_hash: b for b in beatmaps}


def get_beatmaps_by_ids(db: Session, beatmap_ids: list[int]) -> dict[int, Beatmap]:
    if not beatmap_ids:
        return {}
    beatmaps = db.query(Beatmap).filter(Beatmap.beatmap_id.in_(beatmap_ids)).all()
    return {b.beatmap_id: b for b in beatmaps}


def create_beatmap(db: Session, beatmap_data: dict) -> Beatmap:
    beatmap = Beatmap(**beatmap_data)
    db.add(beatmap)
    db.flush()
    return beatmap


def get_invalid_md5s(db: Session, md5_hashes: list[str]) -> set[str]:
    if not md5_hashes:
        return set()
    invalid = db.query(InvalidMD5.md5_hash).filter(InvalidMD5.md5_hash.in_(md5_hashes)).all()
    return {md5[0] for md5 in invalid}


def create_invalid_md5(db: Session, md5_hash: str, reason: str = "404_not_found") -> InvalidMD5:
    invalid = InvalidMD5(md5_hash=md5_hash, reason=reason)
    db.add(invalid)
    db.flush()
    return invalid
