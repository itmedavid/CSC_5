"""Parse page: paste bulk notes, split into chunks, run the matcher."""

from __future__ import annotations

from datetime import date

import streamlit as st

import settings
from db import stores_repo
from db.connection import get_conn
from integrations.outlook import email_to_raw_text
from integrations.outlook import get_client as get_outlook_client
from integrations.ringcentral import call_to_raw_text, get_client
from llm.factory import get_provider
from matcher import store_matcher
from parser.note_splitter import split_notes
from ui.state import band_color, confidence_band, reset_pipeline


def _resolve_provider():
    """Return the LLMProvider for summarization, or None on failure."""
    try:
        return get_provider(st.session_state.provider_override or None)
    except Exception:
        return None


def _render_ringcentral_pull() -> None:
    """Sub-section: pull today's calls and append to the bulk paste."""
    with st.expander(
        f"Pull from RingCentral (mode: **{settings.RINGCENTRAL_MODE}**)",
        expanded=False,
    ):
        if settings.RINGCENTRAL_MODE == "mock":
            st.caption(
                f"Reading fixture: `{settings.RINGCENTRAL_FIXTURE_PATH.name}`. "
                "Switch RINGCENTRAL_MODE to `live` in `.env` once the live client is wired."
            )
        else:
            st.caption(
                "Live mode is a skeleton — see `integrations/ringcentral.py` "
                "→ `LiveRingCentralClient` for the auth steps to fill in."
            )

        # Default to the fixture's date so the demo works without editing anything.
        default_pull_date = (
            date(2026, 5, 2) if settings.RINGCENTRAL_MODE == "mock" else date.today()
        )
        pull_date = st.date_input(
            "Date to pull",
            value=default_pull_date,
            key="rc_pull_date",
        )
        col1, col2 = st.columns([1, 4])
        with col1:
            pull_clicked = st.button("Pull calls", key="rc_pull_btn")
        if pull_clicked:
            try:
                client = get_client(
                    settings.RINGCENTRAL_MODE,
                    fixture_path=settings.RINGCENTRAL_FIXTURE_PATH,
                )
                calls = client.list_calls(on_date=pull_date)
            except Exception as e:
                st.error(f"RingCentral pull failed: {e}")
                return
            if not calls:
                st.warning(f"No calls found for {pull_date.isoformat()}.")
                return
            chunks = [call_to_raw_text(c) for c in calls]
            new_text = "\n\n".join(chunks)
            existing = st.session_state.bulk_paste.strip()
            st.session_state.bulk_paste = (
                f"{existing}\n\n{new_text}" if existing else new_text
            )
            st.success(
                f"Appended {len(calls)} call(s) to the paste below. "
                "Click Parse to run the pipeline."
            )
            st.rerun()


def _render_outlook_pull() -> None:
    """Sub-section: pull today's Zoom-recap emails and append to the bulk paste."""
    with st.expander(
        f"Pull from Outlook (Zoom recap emails, mode: **{settings.OUTLOOK_MODE}**)",
        expanded=False,
    ):
        if settings.OUTLOOK_MODE == "mock":
            st.caption(
                f"Reading fixture: `{settings.OUTLOOK_FIXTURE_PATH.name}`. "
                "Long transcripts are condensed via the recap summarizer before "
                "they reach the bulk paste."
            )
        else:
            st.caption(
                "Live mode is a skeleton — see `integrations/outlook.py` "
                "→ `LiveOutlookClient` for the Microsoft Graph wiring."
            )

        default_pull_date = (
            date(2026, 5, 2) if settings.OUTLOOK_MODE == "mock" else date.today()
        )
        pull_date = st.date_input(
            "Date to pull",
            value=default_pull_date,
            key="outlook_pull_date",
        )
        summarize_long = st.checkbox(
            "Summarize long transcripts via LLM",
            value=True,
            key="outlook_summarize",
            help=(
                "Transcripts longer than "
                f"{settings.RECAP_SUMMARIZE_CHAR_THRESHOLD} chars are condensed "
                "first. Uncheck to keep transcripts verbatim (no LLM call)."
            ),
        )
        if st.button("Pull recaps", key="outlook_pull_btn"):
            try:
                client = get_outlook_client(
                    settings.OUTLOOK_MODE,
                    fixture_path=settings.OUTLOOK_FIXTURE_PATH,
                )
                emails = client.list_recap_emails(on_date=pull_date)
            except Exception as e:
                st.error(f"Outlook pull failed: {e}")
                return
            if not emails:
                st.warning(f"No recap emails found for {pull_date.isoformat()}.")
                return
            provider = _resolve_provider() if summarize_long else None
            with st.spinner("Rendering recaps..."):
                chunks = [
                    email_to_raw_text(
                        e,
                        provider=provider,
                        char_threshold=settings.RECAP_SUMMARIZE_CHAR_THRESHOLD,
                    )
                    for e in emails
                ]
            new_text = "\n\n".join(chunks)
            existing = st.session_state.bulk_paste.strip()
            st.session_state.bulk_paste = (
                f"{existing}\n\n{new_text}" if existing else new_text
            )
            summarized_count = sum(
                1 for e in emails
                if len(e.transcript_text or "") > settings.RECAP_SUMMARIZE_CHAR_THRESHOLD
            )
            st.success(
                f"Appended {len(emails)} recap(s) to the paste below "
                f"({summarized_count} summarized). Click Parse to run the pipeline."
            )
            st.rerun()


def render() -> None:
    st.header("Parse")
    st.caption(
        "Paste your day's raw notes. The parser splits on date headers (your "
        "convention) and the matcher identifies the store for each chunk."
    )

    _render_ringcentral_pull()
    _render_outlook_pull()

    bulk = st.text_area(
        "Bulk paste",
        value=st.session_state.bulk_paste,
        height=320,
        placeholder="5/2 Joe's Market - call w Anita...\n5/2 Sunrise Bakery - Marcus called...",
        key="bulk_paste_widget",
    )
    st.session_state.bulk_paste = bulk

    col_a, col_b, col_c = st.columns([1, 1, 4])
    with col_a:
        parse_clicked = st.button("Parse", type="primary", disabled=not bulk.strip())
    with col_b:
        if st.button("Reset"):
            reset_pipeline()
            st.session_state.bulk_paste = ""
            st.rerun()

    if parse_clicked:
        conn = get_conn()
        try:
            alias_map = stores_repo.all_aliases_norm(conn)
            notes = split_notes(bulk, alias_norm_set=set(alias_map.keys()))
            reset_pipeline()
            st.session_state.order = [n.id for n in notes]
            st.session_state.raw_notes = {n.id: n for n in notes}
            for n in notes:
                cands = store_matcher.match_for_text(
                    conn,
                    n.raw_text,
                    auto_threshold=st.session_state.auto_threshold,
                )
                st.session_state.matches[n.id] = cands
                if cands and cands[0].confidence >= st.session_state.auto_threshold:
                    st.session_state.selected_store[n.id] = cands[0].store_id
                    st.session_state.decisions[n.id] = "pending"
                elif cands and cands[0].confidence >= st.session_state.review_threshold:
                    st.session_state.selected_store[n.id] = cands[0].store_id
                    st.session_state.decisions[n.id] = "pending"
                else:
                    st.session_state.selected_store[n.id] = None
                    st.session_state.decisions[n.id] = "needs_store"
            st.success(f"Parsed {len(notes)} chunks.")
        finally:
            conn.close()

    if not st.session_state.order:
        return

    st.divider()
    st.subheader(f"Parsed chunks ({len(st.session_state.order)})")

    conn = get_conn()
    try:
        for nid in st.session_state.order:
            note = st.session_state.raw_notes[nid]
            cands = st.session_state.matches.get(nid, [])
            top = cands[0] if cands else None
            band = confidence_band(top.confidence) if top else "unmatched"

            if top:
                store = stores_repo.get_store(conn, top.store_id)
                store_label = store.store_name if store else f"id={top.store_id}"
                header = (
                    f"{band_color(band)} **{store_label}** "
                    f"(confidence {top.confidence}, {band})"
                )
            else:
                header = f"{band_color('unmatched')} **No match found**"

            with st.expander(header, expanded=False):
                meta = []
                if note.detected_date:
                    meta.append(f"date: {note.detected_date.isoformat()}")
                if note.detected_phone:
                    meta.append(f"phone: {note.detected_phone}")
                meta.append(f"split: {note.split_reason}")
                st.caption(" • ".join(meta))
                st.code(note.raw_text, language="text")
                if top:
                    for ev in top.evidence:
                        st.caption(f"— {ev}")
    finally:
        conn.close()

    st.info("Move to the **Review** page to edit, approve, or skip each chunk.")
