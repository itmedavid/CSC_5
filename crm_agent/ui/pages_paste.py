"""Paste page: per-note explicit "send to GuideCX" actions.

Hard rules enforced here (mirror the rest of the app):
  - No batch "paste all" button. Every paste is a per-note click.
  - The destination URL and the exact note text are shown BEFORE the click.
  - Every paste attempt — dry-run or live — appends to action_log.jsonl.
  - "Open in GuideCX" link is always available as a manual-paste fallback.
"""

from __future__ import annotations

from typing import Optional

import streamlit as st

import settings
from db import stores_repo
from db.connection import get_conn
from db.stores_repo import Store
from exporters import action_log
from integrations.guidecx_browser import (
    PasteRequest,
    build_project_url,
    get_client,
)


def _approved_ids() -> list[str]:
    return [
        nid for nid in st.session_state.order
        if st.session_state.decisions.get(nid) == "approved"
    ]


def _paste_state_key(nid: str) -> str:
    return f"paste_result_{nid}"


def _do_paste(nid: str, store: Store) -> None:
    note_text = st.session_state.edits.get(nid, "")
    request = PasteRequest(
        store_id=store.id,
        store_name=store.store_name,
        guidecx_project_id=store.guidecx_project_id,
        note_text=note_text,
        raw_note_id=nid,
        session_id=st.session_state.session_id,
    )
    try:
        client = get_client(settings.GUIDECX_MODE)
    except Exception as e:
        st.error(f"GuideCX client error: {e}")
        return

    try:
        result = client.paste(request)
    except NotImplementedError as e:
        st.error(
            f"{e}\n\nFalling back to dry-run for this paste so you have a log row."
        )
        result = get_client("dry_run").paste(request)
    except Exception as e:
        st.error(f"Paste failed unexpectedly: {e}")
        return

    action_log.append_row(result.as_log_row())
    st.session_state[_paste_state_key(nid)] = result


def render() -> None:
    st.header("Paste")
    st.caption(
        "Send approved notes to GuideCX. Dry-run is the default — no browser "
        "is launched and nothing is pasted; the action_log just records the "
        "attempt. Switch GUIDECX_MODE to `live` in `.env` once the Playwright "
        "client is wired."
    )

    mode_badge = "🟢 live" if settings.GUIDECX_MODE == "live" else "🔵 dry-run"
    st.markdown(f"**Current mode:** {mode_badge}")
    if settings.GUIDECX_MODE == "live":
        st.warning(
            "Live mode is active. Each paste launches Playwright and fills the "
            "GuideCX notes textarea. The Save button is NOT clicked automatically "
            "— you still review and click Save in the browser as the final gate."
        )

    approved_ids = _approved_ids()
    if not approved_ids:
        st.info(
            "No approved notes yet. Approve some on the **Review** page first."
        )
        return

    conn = get_conn()
    try:
        for nid in approved_ids:
            note = st.session_state.raw_notes[nid]
            store_id = st.session_state.selected_store.get(nid)
            store: Optional[Store] = (
                stores_repo.get_store(conn, store_id) if store_id else None
            )

            url = build_project_url(store.guidecx_project_id) if store else None
            store_label = store.store_name if store else "(no store)"
            project_label = (
                store.guidecx_project_id if store and store.guidecx_project_id else "—"
            )

            with st.container(border=True):
                st.markdown(f"### {store_label}  ·  project `{project_label}`")
                caption_bits = []
                if note.detected_date:
                    caption_bits.append(f"detected date {note.detected_date.isoformat()}")
                caption_bits.append(f"raw_note_id `{nid[:8]}…`")
                st.caption(" • ".join(caption_bits))

                st.markdown("**Note text to paste**")
                st.code(
                    st.session_state.edits.get(nid, ""), language="text"
                )

                if url:
                    st.markdown(f"**Destination:** [{url}]({url})")
                else:
                    st.error(
                        "No `guidecx_project_id` on this store. Add one on the "
                        "Stores page (or via SQL) before pasting."
                    )

                col1, col2, col3 = st.columns([1, 1, 4])
                with col1:
                    can_paste = bool(
                        url and st.session_state.edits.get(nid, "").strip()
                    )
                    if st.button(
                        "Send to GuideCX",
                        key=f"paste_btn_{nid}",
                        type="primary",
                        disabled=not can_paste,
                    ):
                        _do_paste(nid, store)
                        st.rerun()
                with col2:
                    if url:
                        st.link_button("Open in browser (manual)", url=url)

                result = st.session_state.get(_paste_state_key(nid))
                if result is not None:
                    if result.ok:
                        st.success(f"[{result.mode}] {result.message}")
                    else:
                        st.error(f"[{result.mode}] {result.message}")
                    st.caption(f"logged at {result.ts}")
    finally:
        conn.close()
