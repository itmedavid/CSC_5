"""Outlook / Microsoft Graph integration: pull Zoom recap emails.

Same shape as the RingCentral integration:
  1. Talk to Outlook (or a mock).
  2. Normalize each recap into a `RecapEmail` dataclass.
  3. Render it as a date-headered raw-note chunk the splitter recognizes.

Long transcripts are routed through `formatter.recap_summarizer.summarize()`
before rendering so the per-note token budget stays small.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

from formatter import recap_summarizer
from llm.base import LLMProvider


@dataclass
class RecapEmail:
    """Normalized Zoom-recap email. Provider-agnostic shape."""
    id: str
    subject: str
    received_at: datetime              # always tz-aware UTC
    sender_email: Optional[str] = None
    sender_name: Optional[str] = None
    transcript_text: str = ""
    meeting_topic: Optional[str] = None
    raw: dict = field(default_factory=dict, repr=False)


def email_to_raw_text(
    email: RecapEmail,
    *,
    provider: Optional[LLMProvider] = None,
    char_threshold: int = 1500,
) -> str:
    """Render a `RecapEmail` as a date-headered raw-note chunk.

    If `provider` is supplied AND the transcript is long enough to need
    condensation, the summarizer is invoked. Otherwise the transcript is used
    verbatim.

    Format:
        5/2 Zoom recap: <topic|subject> with <sender> at <time>
        <transcript or summary>
    """
    local = email.received_at.astimezone()
    date_header = f"{local.month}/{local.day}"
    time_str = local.strftime("%-I:%M%p").lower()

    topic = (email.meeting_topic or email.subject or "Zoom meeting").strip()
    sender = email.sender_name or email.sender_email or "unknown"

    header = f"{date_header} Zoom recap: {topic} with {sender} at {time_str}"

    body = email.transcript_text.strip()
    if not body:
        return f"{header}\n(no transcript attached)"

    if provider is not None and recap_summarizer.needs_summarization(
        body, char_threshold=char_threshold
    ):
        recap = recap_summarizer.summarize(
            body,
            provider=provider,
            meeting_context=f"{topic} with {sender}",
            char_threshold=char_threshold,
        )
        if recap.text:
            body = recap.text

    return f"{header}\n{body}"


class OutlookClient(ABC):
    @abstractmethod
    def list_recap_emails(self, *, on_date: date) -> list[RecapEmail]:
        """Return all Zoom-recap emails received on `on_date` (local)."""


class MockOutlookClient(OutlookClient):
    """Reads a fixture JSON file.

    Fixture format:
        [
          {
            "id": "msg_001",
            "subject": "Zoom meeting recap: Joe's Market onboarding",
            "received_at": "2026-05-02T15:00:00Z",
            "sender": {"email": "noreply@zoom.us", "name": "Zoom"},
            "meeting_topic": "Joe's Market onboarding",
            "transcript_text": "..."
          },
          ...
        ]
    """

    def __init__(self, fixture_path: Path) -> None:
        self._fixture_path = fixture_path

    def list_recap_emails(self, *, on_date: date) -> list[RecapEmail]:
        if not self._fixture_path.exists():
            return []
        records = json.loads(self._fixture_path.read_text(encoding="utf-8"))
        out: list[RecapEmail] = []
        for r in records:
            received = datetime.fromisoformat(r["received_at"].replace("Z", "+00:00"))
            if received.tzinfo is None:
                received = received.replace(tzinfo=timezone.utc)
            if received.astimezone().date() != on_date:
                continue
            out.append(
                RecapEmail(
                    id=r["id"],
                    subject=r.get("subject", ""),
                    received_at=received,
                    sender_email=(r.get("sender") or {}).get("email"),
                    sender_name=(r.get("sender") or {}).get("name"),
                    transcript_text=r.get("transcript_text", "") or "",
                    meeting_topic=r.get("meeting_topic"),
                    raw=r,
                )
            )
        return out


class LiveOutlookClient(OutlookClient):
    """Skeleton for the real Microsoft Graph integration.

    To wire this up:
      1. `pip install msal` (Microsoft Authentication Library) and either
         `msgraph-sdk` or use plain `httpx` against the Graph REST endpoints.
      2. Register an app in Azure AD with the `Mail.Read` delegated permission
         (or `Mail.Read.Shared` for a shared mailbox).
      3. Set OUTLOOK_TENANT_ID, OUTLOOK_CLIENT_ID, OUTLOOK_CLIENT_SECRET in
         `.env`. For server-side flows prefer the
         OAuth2 client-credentials grant (no user interaction).
      4. Implement `_authenticate()` to acquire a bearer token via MSAL.
      5. Implement `list_recap_emails()` against
         `GET /me/mailFolders/Inbox/messages?$filter=...&$search=...`. Filter
         by `receivedDateTime ge 2026-05-02T00:00:00Z and ...le ...` and a
         subject `contains 'Zoom meeting recap'` (or your org's actual recap
         subject convention).
      6. Zoom recap emails usually link to the transcript rather than
         attaching it. Either follow the link (auth-gated by Zoom) or fetch
         the email body's transcript section if Zoom includes it inline.

    Until then, this raises so the factory falls back to mock.
    """

    def list_recap_emails(self, *, on_date: date) -> list[RecapEmail]:
        raise NotImplementedError(
            "LiveOutlookClient is a skeleton. Implement _authenticate() and "
            "list_recap_emails() per the docstring, or set OUTLOOK_MODE=mock."
        )


def get_client(mode: str, fixture_path: Optional[Path] = None) -> OutlookClient:
    mode = (mode or "mock").strip().lower()
    if mode == "mock":
        if fixture_path is None:
            raise ValueError("MockOutlookClient requires fixture_path")
        return MockOutlookClient(fixture_path)
    if mode == "live":
        return LiveOutlookClient()
    raise ValueError(f"Unknown Outlook mode: {mode!r}")
