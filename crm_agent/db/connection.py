"""SQLite connection helpers and one-shot schema bootstrap."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import settings


def get_conn(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or settings.DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


@contextmanager
def cursor(db_path: Path | None = None) -> Iterator[sqlite3.Cursor]:
    conn = get_conn(db_path)
    try:
        yield conn.cursor()
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: Path | None = None) -> None:
    """Apply schema.sql. Idempotent — safe to call on every app start."""
    schema = settings.SCHEMA_PATH.read_text()
    conn = get_conn(db_path)
    try:
        conn.executescript(schema)
        conn.commit()
    finally:
        conn.close()
