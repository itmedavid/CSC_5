"""GuideCX browser-paste integration.

Two modes:

  - `dry_run` (default, safe) — simulates the paste. Records the destination
    project URL, the note text, and a timestamp. Does NOT launch a browser.
    Used during development and as a fallback when you don't want to risk a
    real paste.

  - `live` — Playwright-driven paste against a persistent browser context. The
    user logs into GuideCX manually once (and any 2FA), and the cookies live
    in `GUIDECX_USER_DATA_DIR` so subsequent runs reuse the session.

Hard rules (mirror the rest of the app):
  - Never auto-paste without an explicit per-note click. There is no batch
    "paste all" surface.
  - The note text and destination URL are surfaced to the user BEFORE the
    paste action runs.
  - Every paste — dry-run or live — appends a row to `logs/action_log.jsonl`.

Live-mode wiring is intentionally a skeleton. GuideCX's DOM is not part of
this repo, so the selectors are configurable via env vars: when GuideCX
changes its markup, you patch `.env`, not the codebase.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import settings


@dataclass
class PasteRequest:
    """Inputs for a single paste action."""
    store_id: int
    store_name: str
    guidecx_project_id: Optional[str]
    note_text: str
    raw_note_id: str
    session_id: str


@dataclass
class PasteResult:
    """Outcome of a single paste action."""
    ok: bool
    mode: str                    # "dry_run" | "live"
    project_url: Optional[str]   # the URL we tried to (or did) open
    message: str = ""            # human-readable detail / error
    ts: str = ""
    request: Optional[PasteRequest] = field(default=None, repr=False)

    def as_log_row(self) -> dict:
        return {
            "ts": self.ts,
            "session_id": self.request.session_id if self.request else None,
            "raw_note_id": self.request.raw_note_id if self.request else None,
            "decision": "pasted" if (self.ok and self.mode == "live") else "dry_run_pasted",
            "ok": self.ok,
            "mode": self.mode,
            "store_id": self.request.store_id if self.request else None,
            "store_name_snapshot": self.request.store_name if self.request else None,
            "guidecx_project_id": self.request.guidecx_project_id if self.request else None,
            "project_url": self.project_url,
            "formatted_text": self.request.note_text if self.request else None,
            "message": self.message,
        }


def build_project_url(guidecx_project_id: Optional[str]) -> Optional[str]:
    """Render the destination URL via `GUIDECX_PROJECT_URL_TEMPLATE`. Returns
    None if the store has no project ID configured."""
    if not guidecx_project_id:
        return None
    template = settings.GUIDECX_PROJECT_URL_TEMPLATE
    if not template:
        return None
    return template.format(project_id=guidecx_project_id)


class GuideCXClient(ABC):
    """Provider-agnostic interface."""

    mode: str = "abstract"

    @abstractmethod
    def paste(self, request: PasteRequest) -> PasteResult:
        """Attempt to paste `request.note_text` into the project. Returns a
        PasteResult; does NOT raise on expected failures (missing project ID,
        DOM not found). Callers display the message to the user."""


class DryRunClient(GuideCXClient):
    """Default mode. Simulates the paste without launching a browser.

    Useful for end-to-end testing of the surrounding UI + logging, and as a
    safe fallback when the live client is misbehaving (DOM changed, login
    expired, etc).
    """

    mode = "dry_run"

    def paste(self, request: PasteRequest) -> PasteResult:
        url = build_project_url(request.guidecx_project_id)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        if url is None:
            return PasteResult(
                ok=False,
                mode=self.mode,
                project_url=None,
                message=(
                    f"No GuideCX project URL for store '{request.store_name}'. "
                    "Set guidecx_project_id on the store, or configure "
                    "GUIDECX_PROJECT_URL_TEMPLATE in .env."
                ),
                ts=ts,
                request=request,
            )
        if not request.note_text.strip():
            return PasteResult(
                ok=False,
                mode=self.mode,
                project_url=url,
                message="Note text is empty — nothing to paste.",
                ts=ts,
                request=request,
            )
        return PasteResult(
            ok=True,
            mode=self.mode,
            project_url=url,
            message=(
                f"Dry-run: would have pasted {len(request.note_text)} chars "
                f"into {url}."
            ),
            ts=ts,
            request=request,
        )


class PlaywrightClient(GuideCXClient):
    """Skeleton for the real Playwright-driven paste.

    To wire this up:

    1. `pip install playwright && playwright install chromium`.
    2. Set `GUIDECX_MODE=live` in `.env`.
    3. Set `GUIDECX_USER_DATA_DIR` to a path where browser cookies will live
       (e.g. `~/.crm_agent/chromium-profile`). On first launch you'll log into
       GuideCX manually in the headed browser; subsequent runs reuse the
       cookies via Playwright's persistent context.
    4. Set `GUIDECX_PROJECT_URL_TEMPLATE` to the URL pattern that opens a
       project's notes view, with `{project_id}` as the placeholder.
    5. Identify the three selectors with browser DevTools and set them in
       `.env` (or override on the page below):
         GUIDECX_NOTES_TAB_SELECTOR   — clicks into the notes tab/section
         GUIDECX_NOTE_TEXTAREA_SELECTOR — focuses the textarea that receives the note
         GUIDECX_SAVE_BUTTON_SELECTOR — the save/post button
    6. Replace the `raise NotImplementedError` with the body sketched in the
       comments below.

    Suggested implementation:

        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            ctx = p.chromium.launch_persistent_context(
                user_data_dir=settings.GUIDECX_USER_DATA_DIR,
                headless=settings.GUIDECX_HEADLESS,
            )
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto(url, wait_until="networkidle")
            page.click(settings.GUIDECX_NOTES_TAB_SELECTOR)
            page.fill(settings.GUIDECX_NOTE_TEXTAREA_SELECTOR, "")
            page.fill(settings.GUIDECX_NOTE_TEXTAREA_SELECTOR, request.note_text)
            # DELIBERATELY DO NOT auto-click save — let the user verify the
            # paste in the real UI and click save themselves. This is the
            # final approval gate.

    Until implemented, raising forces the factory or UI to fall back to
    dry-run rather than silently doing nothing.
    """

    mode = "live"

    def paste(self, request: PasteRequest) -> PasteResult:
        raise NotImplementedError(
            "PlaywrightClient is a skeleton. Implement paste() per the docstring, "
            "or set GUIDECX_MODE=dry_run."
        )


def get_client(mode: Optional[str] = None) -> GuideCXClient:
    """Factory. `mode` defaults to `settings.GUIDECX_MODE` (dry_run by default)."""
    m = (mode or settings.GUIDECX_MODE or "dry_run").strip().lower()
    if m == "dry_run":
        return DryRunClient()
    if m == "live":
        return PlaywrightClient()
    raise ValueError(
        f"Unknown GUIDECX_MODE: {m!r}. Use 'dry_run' or 'live'."
    )
