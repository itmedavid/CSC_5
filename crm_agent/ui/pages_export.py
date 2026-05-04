"""Export page: assemble approved notes into a text file and append to log."""

from __future__ import annotations

import streamlit as st

from db import stores_repo
from db.connection import get_conn
from exporters import action_log, text_exporter


def render() -> None:
    st.header("Export")
    st.caption(
        "Writes approved notes to `exports/approved_notes_<ts>.txt` and appends "
        "every approved + skipped item to `logs/action_log.jsonl`. Nothing is "
        "auto-pasted into GuideCX."
    )
    if not st.session_state.order:
        st.info("Nothing to export. Go to **Parse** first.")
        return

    decisions = st.session_state.decisions
    approved_ids = [nid for nid in st.session_state.order if decisions.get(nid) == "approved"]
    skipped_ids = [nid for nid in st.session_state.order if decisions.get(nid) == "skipped"]
    pending_ids = [
        nid for nid in st.session_state.order
        if decisions.get(nid) in (None, "pending", "needs_store")
    ]

    st.write(
        f"approved: **{len(approved_ids)}** • skipped: **{len(skipped_ids)}** "
        f"• pending/needs-store: **{len(pending_ids)}**"
    )

    if not approved_ids and not skipped_ids:
        st.warning("Nothing approved or skipped yet.")
        return

    conn = get_conn()
    try:
        # Sort approved by store name then detected date.
        def _sort_key(nid: str):
            sid = st.session_state.selected_store.get(nid)
            store = stores_repo.get_store(conn, sid) if sid else None
            store_name = store.store_name if store else ""
            note = st.session_state.raw_notes[nid]
            return (store_name, note.detected_date or st.session_state.default_date)

        approved_ids_sorted = sorted(approved_ids, key=_sort_key)
        blocks = [st.session_state.edits[nid] for nid in approved_ids_sorted]

        if blocks:
            preview = ("\n\n---\n\n".join(blocks))[:4000]
            st.markdown("**Preview**")
            st.code(preview, language="text")

        if st.button(
            f"Export {len(approved_ids)} approved notes & log {len(skipped_ids)} skipped",
            type="primary",
            disabled=not (approved_ids or skipped_ids),
        ):
            export_path = text_exporter.write_export(blocks) if blocks else None

            for nid in approved_ids_sorted + skipped_ids:
                note = st.session_state.raw_notes[nid]
                cands = st.session_state.matches.get(nid, [])
                top = cands[0] if cands else None
                sid = st.session_state.selected_store.get(nid)
                store = stores_repo.get_store(conn, sid) if sid else None
                fn = st.session_state.formatted.get(nid)
                row = {
                    "session_id": st.session_state.session_id,
                    "raw_note_id": nid,
                    "decision": decisions.get(nid),
                    "store_id": sid,
                    "store_name_snapshot": store.store_name if store else None,
                    "guidecx_project_id": store.guidecx_project_id if store else None,
                    "match_confidence": top.confidence if top else None,
                    "match_evidence": top.evidence if top else [],
                    "detected_date": (
                        note.detected_date.isoformat() if note.detected_date else None
                    ),
                    "initials": st.session_state.default_initials,
                    "raw_text": note.raw_text,
                    "formatted_text": st.session_state.edits.get(nid, ""),
                    "llm_provider": fn.provider if fn else None,
                    "llm_model": fn.model if fn else None,
                    "llm_tokens": fn.token_usage if fn else {},
                    "latency_ms": fn.latency_ms if fn else None,
                    "validation_warnings": fn.validation_warnings if fn else [],
                    "export_file": str(export_path) if export_path else None,
                }
                action_log.append_row(row)

            if export_path:
                st.success(f"Wrote {export_path}")
                st.download_button(
                    "Download text file",
                    data=export_path.read_bytes(),
                    file_name=export_path.name,
                    mime="text/plain",
                )
            else:
                st.info("No approved notes to write — only logs were appended.")
    finally:
        conn.close()
