"""Parse page: paste bulk notes, split into chunks, run the matcher."""

from __future__ import annotations

import streamlit as st

from db import stores_repo
from db.connection import get_conn
from matcher import store_matcher
from parser.note_splitter import split_notes
from ui.state import band_color, confidence_band, reset_pipeline


def render() -> None:
    st.header("Parse")
    st.caption(
        "Paste your day's raw notes. The parser splits on date headers (your "
        "convention) and the matcher identifies the store for each chunk."
    )

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
