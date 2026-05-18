"""Configuration loaded from environment variables with sane defaults.

Single source of truth for runtime configuration. The Streamlit sidebar may
override a small subset of these for the current session only; persistent
changes belong in `.env`.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PACKAGE_ROOT = Path(__file__).resolve().parent
load_dotenv(PACKAGE_ROOT / ".env")


def _bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    return int(raw) if raw else default


def _float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    return float(raw) if raw else default


LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "anthropic").strip().lower()

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o")

DEFAULT_INITIALS = os.environ.get("DEFAULT_INITIALS", "DB")
AUTO_MATCH_THRESHOLD = _int("AUTO_MATCH_THRESHOLD", 90)
REVIEW_THRESHOLD = _int("REVIEW_THRESHOLD", 70)

DB_PATH = PACKAGE_ROOT / os.environ.get("DB_PATH", "data/store_database.db")
EXPORTS_DIR = PACKAGE_ROOT / os.environ.get("EXPORTS_DIR", "exports")
LOGS_DIR = PACKAGE_ROOT / os.environ.get("LOGS_DIR", "logs")

TIMEZONE = os.environ.get("TIMEZONE", "America/Los_Angeles")

LLM_TEMPERATURE = _float("LLM_TEMPERATURE", 0.2)
LLM_MAX_TOKENS = _int("LLM_MAX_TOKENS", 800)
ENABLE_PROMPT_CACHE = _bool("ENABLE_PROMPT_CACHE", True)

APP_VERSION = "0.1.0"

SCHEMA_PATH = PACKAGE_ROOT / "data" / "schema.sql"
SEED_STORES_CSV = PACKAGE_ROOT / "data" / "seed_stores.csv"
SEED_CONTACTS_CSV = PACKAGE_ROOT / "data" / "seed_contacts.csv"

# RingCentral integration (M2). "mock" reads the fixture; "live" requires
# OAuth/JWT credentials and the official `ringcentral` SDK.
RINGCENTRAL_MODE = os.environ.get("RINGCENTRAL_MODE", "mock").strip().lower()
RINGCENTRAL_FIXTURE_PATH = PACKAGE_ROOT / os.environ.get(
    "RINGCENTRAL_FIXTURE_PATH", "tests/fixtures/sample_calls.json"
)
RINGCENTRAL_CLIENT_ID = os.environ.get("RINGCENTRAL_CLIENT_ID", "")
RINGCENTRAL_CLIENT_SECRET = os.environ.get("RINGCENTRAL_CLIENT_SECRET", "")
RINGCENTRAL_SERVER_URL = os.environ.get(
    "RINGCENTRAL_SERVER_URL", "https://platform.ringcentral.com"
)
RINGCENTRAL_JWT = os.environ.get("RINGCENTRAL_JWT", "")

# Outlook / Microsoft Graph integration (M3). "mock" reads the fixture;
# "live" requires Azure AD app credentials and the `msal` library.
OUTLOOK_MODE = os.environ.get("OUTLOOK_MODE", "mock").strip().lower()
OUTLOOK_FIXTURE_PATH = PACKAGE_ROOT / os.environ.get(
    "OUTLOOK_FIXTURE_PATH", "tests/fixtures/sample_recaps.json"
)
OUTLOOK_TENANT_ID = os.environ.get("OUTLOOK_TENANT_ID", "")
OUTLOOK_CLIENT_ID = os.environ.get("OUTLOOK_CLIENT_ID", "")
OUTLOOK_CLIENT_SECRET = os.environ.get("OUTLOOK_CLIENT_SECRET", "")

# Recap summarizer (M3). Transcripts above this character count are routed
# through the summarizer LLM before reaching the note formatter.
RECAP_SUMMARIZE_CHAR_THRESHOLD = _int("RECAP_SUMMARIZE_CHAR_THRESHOLD", 1500)
RECAP_MAX_TOKENS = _int("RECAP_MAX_TOKENS", 600)

# GuideCX browser-paste integration (M4). Default mode is "dry_run" — no
# browser is launched, paste actions only log what would have happened.
# Set GUIDECX_MODE=live to opt into the real Playwright-driven paste.
GUIDECX_MODE = os.environ.get("GUIDECX_MODE", "dry_run").strip().lower()
GUIDECX_PROJECT_URL_TEMPLATE = os.environ.get(
    "GUIDECX_PROJECT_URL_TEMPLATE",
    "https://app.guidecx.com/projects/{project_id}",
)
GUIDECX_USER_DATA_DIR = os.environ.get("GUIDECX_USER_DATA_DIR", "")
GUIDECX_HEADLESS = _bool("GUIDECX_HEADLESS", False)
GUIDECX_NOTES_TAB_SELECTOR = os.environ.get("GUIDECX_NOTES_TAB_SELECTOR", "")
GUIDECX_NOTE_TEXTAREA_SELECTOR = os.environ.get("GUIDECX_NOTE_TEXTAREA_SELECTOR", "")
GUIDECX_SAVE_BUTTON_SELECTOR = os.environ.get("GUIDECX_SAVE_BUTTON_SELECTOR", "")
