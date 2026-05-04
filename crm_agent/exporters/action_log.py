"""Append-only JSONL audit log of approved/skipped notes."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import settings


def append_row(row: dict) -> Path:
    settings.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    path = settings.LOGS_DIR / "action_log.jsonl"
    row.setdefault("ts", datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    row.setdefault("app_version", settings.APP_VERSION)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return path
