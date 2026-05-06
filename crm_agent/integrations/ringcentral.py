"""RingCentral call-log integration.

Fetches today's calls and converts each one into a date-headered raw note
string that drops into the existing parse/match/format pipeline. The pipeline
already handles date headers, phone extraction, and store matching by phone,
so this module's job is purely:

  1. Talk to RingCentral (or a mock).
  2. Normalize each call into a `Call` dataclass.
  3. Render each call as a raw-note chunk that the splitter will recognize.

Auth is intentionally NOT implemented in the live client — RingCentral OAuth
needs your real credentials and a callback URL, both of which depend on your
environment. The skeleton documents what to fill in.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

from matcher.normalize import to_e164


@dataclass
class Call:
    """Normalized call record. Provider-agnostic shape."""
    id: str
    direction: str                      # "Inbound" | "Outbound"
    start_time: datetime                # always tz-aware UTC
    duration_seconds: int
    result: str                         # "Accepted" | "Missed" | "Voicemail" | "Declined"
    from_phone: Optional[str] = None
    from_name: Optional[str] = None
    to_phone: Optional[str] = None
    to_name: Optional[str] = None
    transcript_text: Optional[str] = None
    recording_url: Optional[str] = None
    raw: dict = field(default_factory=dict, repr=False)

    @property
    def from_phone_e164(self) -> Optional[str]:
        return to_e164(self.from_phone)

    @property
    def to_phone_e164(self) -> Optional[str]:
        return to_e164(self.to_phone)

    @property
    def counterpart_phone(self) -> Optional[str]:
        """Phone number of the other party (not yourself)."""
        return self.from_phone if self.direction == "Inbound" else self.to_phone

    @property
    def counterpart_name(self) -> Optional[str]:
        return self.from_name if self.direction == "Inbound" else self.to_name


def _format_duration(seconds: int) -> str:
    if seconds <= 0:
        return "0s"
    m, s = divmod(seconds, 60)
    if m == 0:
        return f"{s}s"
    return f"{m}m {s}s" if s else f"{m}m"


def _format_local_time(dt: datetime) -> str:
    """Render the call's start time as a short local clock string."""
    local = dt.astimezone()
    return local.strftime("%-I:%M%p").lower() if hasattr(local, "strftime") else str(local)


def call_to_raw_text(call: Call) -> str:
    """Render a Call as a date-headered raw note that the splitter recognizes.

    Format:
        5/2 Call <direction> <name|phone> at <time>, <duration>
        Transcript: <text>            (omitted if no transcript)

    Missed/voicemail calls without a transcript still produce a chunk so the
    matcher can tie them to a store via the phone number alone.
    """
    local = call.start_time.astimezone()
    date_header = f"{local.month}/{local.day}"
    time_str = _format_local_time(call.start_time)

    counterpart = call.counterpart_name or call.counterpart_phone or "unknown"
    direction_word = "from" if call.direction == "Inbound" else "to"
    duration = _format_duration(call.duration_seconds)

    header = (
        f"{date_header} Call {direction_word} {counterpart} at {time_str}, "
        f"{duration} ({call.result.lower()})"
    )

    if call.counterpart_phone and call.counterpart_name:
        header = (
            f"{date_header} Call {direction_word} {call.counterpart_name} "
            f"({call.counterpart_phone}) at {time_str}, "
            f"{duration} ({call.result.lower()})"
        )

    if call.transcript_text and call.transcript_text.strip():
        return f"{header}\nTranscript: {call.transcript_text.strip()}"

    return f"{header}\n(no transcript available)"


class RingCentralClient(ABC):
    """Provider-agnostic interface — anything callable by the UI lives here."""

    @abstractmethod
    def list_calls(self, *, on_date: date) -> list[Call]:
        """Return all call-log entries that started on `on_date` (local)."""


class MockRingCentralClient(RingCentralClient):
    """Reads a fixture JSON file. Used for offline dev and tests.

    Fixture format:
        [
          {
            "id": "abc",
            "direction": "Inbound",
            "start_time": "2026-05-02T14:30:00Z",
            "duration_seconds": 245,
            "result": "Accepted",
            "from": {"phone": "+14155551212", "name": "Anita Patel"},
            "to":   {"phone": "+19998887777", "name": "DB"},
            "transcript_text": "..."
          },
          ...
        ]
    """

    def __init__(self, fixture_path: Path) -> None:
        self._fixture_path = fixture_path

    def list_calls(self, *, on_date: date) -> list[Call]:
        if not self._fixture_path.exists():
            return []
        records = json.loads(self._fixture_path.read_text(encoding="utf-8"))
        out: list[Call] = []
        for r in records:
            start = datetime.fromisoformat(r["start_time"].replace("Z", "+00:00"))
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
            if start.astimezone().date() != on_date:
                continue
            out.append(
                Call(
                    id=r["id"],
                    direction=r.get("direction", "Inbound"),
                    start_time=start,
                    duration_seconds=int(r.get("duration_seconds", 0)),
                    result=r.get("result", "Accepted"),
                    from_phone=(r.get("from") or {}).get("phone"),
                    from_name=(r.get("from") or {}).get("name"),
                    to_phone=(r.get("to") or {}).get("phone"),
                    to_name=(r.get("to") or {}).get("name"),
                    transcript_text=r.get("transcript_text"),
                    recording_url=r.get("recording_url"),
                    raw=r,
                )
            )
        return out


class LiveRingCentralClient(RingCentralClient):
    """Skeleton for the real RingCentral SDK integration.

    To wire this up:
      1. `pip install ringcentral` (the official Python SDK).
      2. Set RINGCENTRAL_CLIENT_ID, RINGCENTRAL_CLIENT_SECRET,
         RINGCENTRAL_SERVER_URL, RINGCENTRAL_JWT in `.env`.
      3. Implement `_authenticate()` using JWT auth (recommended for
         server-side apps — avoids the OAuth-callback dance):

             from ringcentral import SDK
             rcsdk = SDK(client_id, client_secret, server_url)
             platform = rcsdk.platform()
             platform.login(jwt=jwt_token)

      4. Implement `list_calls()` against `/restapi/v1.0/account/~/extension/~/call-log`
         with `dateFrom` / `dateTo` set to the local-day window in UTC.
      5. For voicemail/recording transcripts, hit
         `/restapi/v1.0/account/~/extension/~/message-store/<id>/content`
         on each call's `recording.id` and store the result in
         `Call.transcript_text`.

    Until then, this raises so the factory falls back to mock.
    """

    def list_calls(self, *, on_date: date) -> list[Call]:
        raise NotImplementedError(
            "LiveRingCentralClient is a skeleton. Implement _authenticate() and "
            "list_calls() per the docstring, or set RINGCENTRAL_MODE=mock."
        )


def get_client(mode: str, fixture_path: Optional[Path] = None) -> RingCentralClient:
    """Factory. `mode` is 'mock' or 'live'."""
    mode = (mode or "mock").strip().lower()
    if mode == "mock":
        if fixture_path is None:
            raise ValueError("MockRingCentralClient requires fixture_path")
        return MockRingCentralClient(fixture_path)
    if mode == "live":
        return LiveRingCentralClient()
    raise ValueError(f"Unknown RingCentral mode: {mode!r}")
