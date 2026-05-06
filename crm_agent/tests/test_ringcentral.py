"""Tests for the RingCentral integration: conversion + mock client."""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

import pytest

import settings
from db import seed
from db.connection import get_conn, init_db
from integrations.ringcentral import (
    Call,
    LiveRingCentralClient,
    MockRingCentralClient,
    call_to_raw_text,
    get_client,
)
from matcher import store_matcher
from parser.note_splitter import split_notes


FIXTURE = settings.RINGCENTRAL_FIXTURE_PATH


@pytest.fixture()
def conn(tmp_path: Path):
    db = tmp_path / "rc.db"
    init_db(db)
    c = get_conn(db)
    seed.import_stores_csv(c, settings.SEED_STORES_CSV)
    seed.import_contacts_csv(c, settings.SEED_CONTACTS_CSV)
    yield c
    c.close()


def _call(**overrides) -> Call:
    base = dict(
        id="t1",
        direction="Inbound",
        start_time=datetime(2026, 5, 2, 21, 30, tzinfo=timezone.utc),
        duration_seconds=245,
        result="Accepted",
        from_phone="+14155551212",
        from_name="Anita Patel",
        to_phone="+19998887777",
        to_name="DB",
        transcript_text="Hardware delivery slipped to next week.",
    )
    base.update(overrides)
    return Call(**base)


def test_call_to_raw_text_includes_date_header_phone_and_transcript() -> None:
    text = call_to_raw_text(_call())
    assert text.startswith("5/2 ")
    assert "Anita Patel" in text
    assert "+14155551212" in text
    assert "(accepted)" in text
    assert "Transcript: Hardware delivery slipped to next week." in text


def test_call_to_raw_text_missing_transcript_still_renders() -> None:
    text = call_to_raw_text(_call(transcript_text=None, result="Missed"))
    assert "(missed)" in text
    assert "(no transcript available)" in text


def test_call_to_raw_text_outbound_uses_to_party() -> None:
    text = call_to_raw_text(
        _call(
            direction="Outbound",
            from_phone="+19998887777",
            from_name="DB",
            to_phone="+13105557701",
            to_name="Sarah Reilly",
        )
    )
    assert " to Sarah Reilly" in text
    assert "+13105557701" in text


def test_call_to_raw_text_duration_formatting() -> None:
    assert "0s" in call_to_raw_text(_call(duration_seconds=0))
    assert "45s" in call_to_raw_text(_call(duration_seconds=45))
    assert "1m" in call_to_raw_text(_call(duration_seconds=60))
    assert "4m 5s" in call_to_raw_text(_call(duration_seconds=245))


def test_mock_client_filters_by_local_date() -> None:
    client = MockRingCentralClient(FIXTURE)
    calls = client.list_calls(on_date=date(2026, 5, 2))
    assert len(calls) == 4
    other = client.list_calls(on_date=date(2026, 1, 1))
    assert other == []


def test_mock_client_handles_missing_fixture(tmp_path: Path) -> None:
    client = MockRingCentralClient(tmp_path / "does_not_exist.json")
    assert client.list_calls(on_date=date(2026, 5, 2)) == []


def test_factory_returns_mock_when_mode_is_mock() -> None:
    client = get_client("mock", FIXTURE)
    assert isinstance(client, MockRingCentralClient)


def test_factory_returns_live_skeleton_when_mode_is_live() -> None:
    client = get_client("live")
    assert isinstance(client, LiveRingCentralClient)


def test_live_client_skeleton_raises_until_implemented() -> None:
    with pytest.raises(NotImplementedError):
        LiveRingCentralClient().list_calls(on_date=date(2026, 5, 2))


def test_factory_rejects_unknown_mode() -> None:
    with pytest.raises(ValueError):
        get_client("bogus", FIXTURE)


def test_pipeline_end_to_end_calls_match_seeded_stores(conn) -> None:
    """Pull mock calls, render to raw text, run the splitter + matcher.

    Asserts that the call-rendered text actually drops cleanly into the same
    pipeline as pasted notes — phone matches Joe's Market, etc.
    """
    client = MockRingCentralClient(FIXTURE)
    calls = client.list_calls(on_date=date(2026, 5, 2))
    assert len(calls) == 4

    bulk = "\n".join(call_to_raw_text(c) for c in calls)
    notes = split_notes(bulk)
    # All four calls share the same date header (5/2) so they each become a
    # separate chunk via the date-header heuristic.
    assert len(notes) == 4

    # Joe's Market phone match — should land in the auto band.
    joes_chunk = next(n for n in notes if "Anita Patel" in n.raw_text)
    cands = store_matcher.match_for_text(conn, joes_chunk.raw_text)
    assert cands and cands[0].confidence >= 90
    assert any("phone exact" in e for e in cands[0].evidence)

    # Westside contact phone match (+13105557701 is on a contact, not the store).
    westside_chunk = next(n for n in notes if "Sarah Reilly" in n.raw_text)
    cands = store_matcher.match_for_text(conn, westside_chunk.raw_text)
    assert cands and cands[0].confidence >= 70

    # Unknown caller — should be unmatched.
    unknown_chunk = next(n for n in notes if "+15550102030" in n.raw_text)
    cands = store_matcher.match_for_text(conn, unknown_chunk.raw_text)
    assert (not cands) or cands[0].confidence < 70
