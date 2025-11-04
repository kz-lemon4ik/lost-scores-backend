from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from app.core.config import settings


def is_sqlite_database(url: str) -> bool:
    """Return True if the SQLAlchemy URL points to a SQLite database."""
    return url.startswith("sqlite:")


def resolve_sqlite_path(url: str | None = None) -> Path:
    """
    Resolve the filesystem path for a SQLite database URL.

    Raises:
        ValueError: if the URL is not a SQLite URL.
    """
    database_url = url or settings.DATABASE_URL

    if not is_sqlite_database(database_url):
        raise ValueError("Only sqlite:// URLs are supported for direct filesystem access.")

    parsed = urlparse(database_url)
    if not parsed.path:
        raise ValueError("Invalid sqlite URL: missing path component.")

    raw_path = parsed.path

    # Strip leading slash for relative paths like sqlite:///./storage/database.db
    if raw_path.startswith("/") and not raw_path.startswith("//"):
        raw_path = raw_path.lstrip("/")

    path = Path(raw_path)
    if not path.is_absolute():
        project_root = Path(__file__).resolve().parents[2]
        path = (project_root / path).resolve()

    return path


def ensure_storage_directory(path: Path) -> None:
    """Make sure the target directory exists (similar to SessionLocal initialisation)."""
    path.parent.mkdir(parents=True, exist_ok=True)
