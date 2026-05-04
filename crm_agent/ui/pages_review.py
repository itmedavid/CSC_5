"""Review page: per-note card with raw vs formatted, match override, approve/skip."""

from __future__ import annotations

from datetime import date as date_cls
from typing import Optional

import streamlit as st

from db import stores_repo
from db.connection import get_conn
from db.stores_repo import Store
from formatter.note_formatter import format_note
from llm.factory import get_provider
from ui.state import band_color, confidence_band


def _resolve_provider_name() -> str:
    return st.session_state.provider_override or None


def _format_for(note_id: str, store: Optional[Store]) -> None:
    note = st.session_state.raw_notes[note_id]
    note_date = note.detected_date or st.session_state.default_date
    if isinstance(note_date, date_cls):
        date_arg = note_date
    else:
        date_arg = st.session_state.default_date

    try:
        provider = get_provider(_resolve_provider_name())
    except Exception as e:
        st.error(f"LLM provider error: {e}")
        return

    with st.spinner("Generating note..."):
        try:
            fn = format_note(
                raw_note=note.raw_text,
                note_date=date_arg,
                initials=st.session_state.default_initials,
                store=store,
                provider=provider,
            )
        except Exception as e:
            st.error(f"Formatter error: {e}")
            return

    st.session_state.formatted[note_id] = fn
    if note_id not in st.session_state.edits or not st.session_state.edits[note_id]:
        st.session_state.edits[note_id] = fn.text


def _create_stub_store(name: str, phone: str, conn) -> int:
    sid = stores_repo.create_stub_store(conn, store_name=name, phone=phone or None)
    conn.commit()
    return sid


def render() -> None:
    st.header("Review")
    if not st.session_state.order:
        st.info("Nothing to review. Paste raw notes on the **Parse** page first.")
        return

    auto = st.session_state.auto_threshold
    review = st.session_state.review_threshold

    conn = get_conn()
    try:
        for nid in st.session_state.order:
            note = st.session_state.raw_notes[nid]
            cands = st.session_state.matches.get(nid, [])
            decision = st.session_state.decisions.get(nid, "pending")
            top = cands[0] if cands else None
            band = confidence_band(top.confidence) if top else "unmatched"

            selected_id = st.session_state.selected_store.get(nid)
            store = stores_repo.get_store(conn, selected_id) if selected_id else None
            store_label = store.store_name if store else "(no store)"
            decision_badge = {
                "approved": "✅ approved",
                "skipped": "⏭️ skipped",
                "needs_store": "🆕 needs store",
                "pending": "•",
            }.get(decision, "•")
            header = (
                f"{band_color(band)} {store_label} — "
                f"conf {top.confidence if top else 0} • {decision_badge}"
            )

            with st.container(border=True):
                st.markdown(f"### {header}")
                meta = []
                if note.detected_date:
                    meta.append(f"date {note.detected_date.isoformat()}")
                if note.detected_phone:
                    meta.append(f"phone {note.detected_phone}")
                meta.append(f"split: {note.split_reason}")
                st.caption(" • ".join(meta))

                # Match selector — radio when needs review, search/create when unmatched.
                if cands and top.confidence < auto:
                    options = [(c.store_id, c) for c in cands[:3]]
                    labels = []
                    for sid, c in options:
                        s = stores_repo.get_store(conn, sid)
                        labels.append(
                            f"{s.store_name if s else sid}  ({c.confidence}) — "
                            f"{', '.join(c.evidence[:3])}"
                        )
                    current = selected_id
                    idx = next(
                        (i for i, (sid, _) in enumerate(options) if sid == current), 0
                    )
                    pick = st.radio(
                        "Pick the right store",
                        options=list(range(len(options))),
                        format_func=lambda i: labels[i],
                        index=idx,
                        key=f"radio_{nid}",
                    )
                    st.session_state.selected_store[nid] = options[pick][0]

                if (not cands) or (top and top.confidence < review):
                    with st.expander("Create stub store for this note"):
                        col1, col2 = st.columns(2)
                        with col1:
                            stub_name = st.text_input(
                                "Store name", key=f"stub_name_{nid}"
                            )
                        with col2:
                            stub_phone = st.text_input(
                                "Phone (optional)",
                                value=note.detected_phone or "",
                                key=f"stub_phone_{nid}",
                            )
                        if st.button("Create stub", key=f"stub_btn_{nid}"):
                            if not stub_name.strip():
                                st.error("Store name is required.")
                            else:
                                sid = _create_stub_store(stub_name, stub_phone, conn)
                                st.session_state.selected_store[nid] = sid
                                st.session_state.decisions[nid] = "pending"
                                st.success(f"Created stub store '{stub_name}'.")
                                st.rerun()

                col_raw, col_fmt = st.columns(2)
                with col_raw:
                    st.markdown("**Raw**")
                    st.text_area(
                        "raw",
                        value=note.raw_text,
                        height=220,
                        disabled=True,
                        key=f"raw_{nid}",
                        label_visibility="collapsed",
                    )
                with col_fmt:
                    st.markdown("**Formatted**")
                    if nid not in st.session_state.formatted:
                        st.caption("Not generated yet.")
                    fn = st.session_state.formatted.get(nid)
                    if fn and fn.validation_warnings:
                        for w in fn.validation_warnings:
                            st.warning(w)
                    edit_value = st.session_state.edits.get(nid, "")
                    new_value = st.text_area(
                        "formatted",
                        value=edit_value,
                        height=220,
                        key=f"fmt_{nid}",
                        label_visibility="collapsed",
                    )
                    st.session_state.edits[nid] = new_value

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    if st.button("Generate / Regenerate", key=f"gen_{nid}"):
                        sel_id = st.session_state.selected_store.get(nid)
                        sel_store = stores_repo.get_store(conn, sel_id) if sel_id else None
                        _format_for(nid, sel_store)
                        st.rerun()
                with col2:
                    can_approve = (
                        st.session_state.selected_store.get(nid) is not None
                        and bool(st.session_state.edits.get(nid, "").strip())
                    )
                    if st.button(
                        "Approve",
                        key=f"approve_{nid}",
                        type="primary",
                        disabled=not can_approve,
                    ):
                        st.session_state.decisions[nid] = "approved"
                        st.rerun()
                with col3:
                    if st.button("Skip", key=f"skip_{nid}"):
                        st.session_state.decisions[nid] = "skipped"
                        st.rerun()
                with col4:
                    if fn:
                        st.caption(
                            f"{fn.provider}/{fn.model} • {fn.latency_ms}ms • "
                            f"in={fn.token_usage.get('input',0)} "
                            f"out={fn.token_usage.get('output',0)} "
                            f"cache={fn.token_usage.get('cache_read',0)}"
                        )
    finally:
        conn.close()

    approved = sum(1 for d in st.session_state.decisions.values() if d == "approved")
    skipped = sum(1 for d in st.session_state.decisions.values() if d == "skipped")
    pending = sum(1 for d in st.session_state.decisions.values() if d == "pending")
    st.caption(f"approved: {approved} • skipped: {skipped} • pending: {pending}")
