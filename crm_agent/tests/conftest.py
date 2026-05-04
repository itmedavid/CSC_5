"""Add the crm_agent project root to sys.path so tests can import top-level
packages (db, parser, matcher, llm, formatter, ui, exporters, settings)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
