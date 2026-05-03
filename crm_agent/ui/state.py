"""Streamlit session_state schema and small helpers.

Centralizing keys here keeps page modules from drifting.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import streamlit as st

import settings

KEYS = {
    "bulk_paste": "",
    "raw_notes": dict,         # dict[uuid, RawNote]
    "order": list,             # list[uuid]
    "matches": dict,           # dict[uuid, list[MatchCandidate]]
    "selected_store": dict,    # dict[uuid, Optional[int]]
    "formatted": dict,         # dict[uuid, FormattedNote]
    "edits": dict,             # dict[uuid, str]
    "decisions": dict,         # dict[uuid, str]   "pending"|"approved"|"skipped"|"needs_store"
    "session_id": str,         # uuid for this Streamlit session
    "default_initials": str,
    "default_date": object,    # datetime.date
    "auto_threshold": int,
    "review_threshold": int,
    "provider_override": str,  # "" means use settings
}


def init_state() -> None:
    import uuid

    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())

    defaults: dict[str, Any] = {
        "bulk_paste": "",
        "raw_notes": {},
        "order": [],
        "matches": {},
        "selected_store": {},
        "formatted": {},
        "edits": {},
        "decisions": {},
        "default_initials": settings.DEFAULT_INITIALS,
        "default_date": date.today(),
        "auto_threshold": settings.AUTO_MATCH_THRESHOLD,
        "review_threshold": settings.REVIEW_THRESHOLD,
        "provider_override": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_pipeline() -> None:
    """Clear parse/match/format state but keep settings."""
    st.session_state.raw_notes = {}
    st.session_state.order = []
    st.session_state.matches = {}
    st.session_state.selected_store = {}
    st.session_state.formatted = {}
    st.session_state.edits = {}
    st.session_state.decisions = {}


def confidence_band(conf: int) -> str:
    if conf >= st.session_state.auto_threshold:
        return "auto"
    if conf >= st.session_state.review_threshold:
        return "review"
    return "unmatched"


def band_color(band: str) -> str:
    return {"auto": "🟢", "review": "🟡", "unmatched": "🔴"}.get(band, "⚪")
