from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from app.db.utils import resolve_sqlite_path, ensure_storage_directory


def run_checkpoint(mode: str = "TRUNCATE") -> None:
    """Execute PRAGMA wal_checkpoint on the configured SQLite database."""
    db_path = resolve_sqlite_path()
    ensure_storage_directory(db_path)

    with sqlite3.connect(db_path) as conn:
        conn.execute(f"PRAGMA wal_checkpoint({mode});")


def create_snapshot(destination: Path) -> Path:
    """Create a snapshot copy of the SQLite database (includes WAL state)."""
    db_path = resolve_sqlite_path()
    ensure_storage_directory(db_path)
    ensure_storage_directory(destination)

    with sqlite3.connect(db_path) as src, sqlite3.connect(destination) as dst:
        src.backup(dst)

    return destination


def print_info() -> None:
    """Print basic information about the current SQLite database path."""
    db_path = resolve_sqlite_path()
    ensure_storage_directory(db_path)
    wal_path = db_path.with_suffix(db_path.suffix + "-wal")

    print(f"Database file : {db_path}")
    print(f"WAL file      : {wal_path} {'(present)' if wal_path.exists() else '(not found)'}")
    print(f"Size (bytes)  : {db_path.stat().st_size if db_path.exists() else 0}")


def main() -> None:
    parser = argparse.ArgumentParser(description="SQLite maintenance helper.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    checkpoint_parser = subparsers.add_parser("checkpoint", help="Flush WAL into the main database file.")
    checkpoint_parser.add_argument(
        "--mode",
        default="TRUNCATE",
        choices=["PASSIVE", "FULL", "RESTART", "TRUNCATE"],
        help="Checkpoint mode (default: TRUNCATE).",
    )

    snapshot_parser = subparsers.add_parser("snapshot", help="Create a snapshot copy of the database.")
    snapshot_parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Destination path for the snapshot copy.",
    )

    subparsers.add_parser("info", help="Show database path and WAL status.")

    args = parser.parse_args()

    if args.command == "checkpoint":
        run_checkpoint(mode=args.mode)
    elif args.command == "snapshot":
        destination = args.output.resolve()
        create_snapshot(destination)
        print(f"Snapshot created: {destination}")
    elif args.command == "info":
        print_info()


if __name__ == "__main__":
    main()
