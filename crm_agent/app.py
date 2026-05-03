"""Streamlit entrypoint and thin router.

Run: `streamlit run crm_agent/app.py` from the repo root, or
     `streamlit run app.py` from inside crm_agent/.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure crm_agent/ (this script's directory) is on sys.path so subpackage
# imports work both when launched as a top-level script and via `python -m`.
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import streamlit as st  # noqa: E402

import settings  # noqa: E402
from db.connection import init_db  # noqa: E402
from ui import pages_export, pages_parse, pages_review, pages_stores  # noqa: E402
from ui.state import init_state  # noqa: E402

st.set_page_config(page_title="CRM Onboarding Assistant", layout="wide")

init_db()
init_state()

with st.sidebar:
    st.title("CRM Assistant")
    st.caption(f"v{settings.APP_VERSION}")

    page = st.radio(
        "Page",
        ["Parse", "Review", "Export", "Stores"],
        label_visibility="collapsed",
    )

    st.divider()
    st.markdown("**Session settings**")
    st.session_state.default_initials = st.text_input(
        "Default initials", value=st.session_state.default_initials
    )
    st.session_state.default_date = st.date_input(
        "Default date (used when none detected)",
        value=st.session_state.default_date,
    )
    provider = st.selectbox(
        "LLM provider",
        ["(env default)", "anthropic", "openai", "mock"],
        index=0,
        help=f"Env default is '{settings.LLM_PROVIDER}'.",
    )
    st.session_state.provider_override = "" if provider == "(env default)" else provider

    st.session_state.auto_threshold = st.slider(
        "Auto-match threshold", 50, 100, st.session_state.auto_threshold
    )
    st.session_state.review_threshold = st.slider(
        "Review threshold", 0, st.session_state.auto_threshold,
        min(st.session_state.review_threshold, st.session_state.auto_threshold),
    )

    st.divider()
    st.caption(
        "Approved notes never auto-paste. Use Export to write a paste-ready text "
        "file for GuideCX."
    )

if page == "Parse":
    pages_parse.render()
elif page == "Review":
    pages_review.render()
elif page == "Export":
    pages_export.render()
elif page == "Stores":
    pages_stores.render()
