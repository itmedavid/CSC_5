"""Write approved notes to a paste-ready text file."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import settings

SEPARATOR = "\n\n---\n\n"


def write_export(blocks: list[str]) -> Path:
    """Write `blocks` joined by SEPARATOR to a timestamped file. Returns path."""
    settings.EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H%M")
    path = settings.EXPORTS_DIR / f"approved_notes_{ts}.txt"
    body = SEPARATOR.join(b.strip() for b in blocks if b.strip())
    path.write_text(body + "\n", encoding="utf-8")
    return path
