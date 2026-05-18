"""Tests for the Outlook integration: conversion + mock client + end-to-end."""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

import pytest

import settings
from db import seed
from db.connection import get_conn, init_db
from integrations.outlook import (
    LiveOutlookClient,
    MockOutlookClient,
    RecapEmail,
    email_to_raw_text,
    get_client,
)
from llm.factory import get_provider
from matcher import store_matcher
from parser.note_splitter import split_notes


FIXTURE = settings.OUTLOOK_FIXTURE_PATH


@pytest.fixture()
def conn(tmp_path: Path):
    db = tmp_path / "out.db"
    init_db(db)
    c = get_conn(db)
    seed.import_stores_csv(c, settings.SEED_STORES_CSV)
    seed.import_contacts_csv(c, settings.SEED_CONTACTS_CSV)
    yield c
    c.close()


def _email(**overrides) -> RecapEmail:
    base = dict(
        id="t1",
        subject="Zoom meeting recap: Maple Grove check-in",
        received_at=datetime(2026, 5, 2, 18, 30, tzinfo=timezone.utc),
        sender_email="noreply@zoom.us",
        sender_name="Zoom Recordings",
        transcript_text="Emma needs a second register sooner.",
        meeting_topic="Maple Grove Pet Supply check-in",
    )
    base.update(overrides)
    return RecapEmail(**base)


def test_email_to_raw_text_short_transcript_no_summarization() -> None:
    text = email_to_raw_text(_email(), provider=get_provider("mock"))
    assert text.startswith("5/2 ")
    assert "Zoom recap:" in text
    assert "Maple Grove Pet Supply" in text
    assert "Emma needs a second register sooner." in text


def test_email_to_raw_text_long_transcript_invokes_summarizer() -> None:
    long_transcript = (
        "Hey, good morning everyone. Can you hear me okay?\n"
        + "Dani Kim confirmed the menu list and the 5/15 go-live target. " * 30
        + "Action items: send schedule by Friday."
    )
    assert len(long_transcript) > 1500
    text = email_to_raw_text(
        _email(transcript_text=long_transcript, meeting_topic="Pioneer sync"),
        provider=get_provider("mock"),
    )
    # Header preserved.
    assert "Zoom recap: Pioneer sync" in text
    # Mock summarizer strips filler.
    assert "good morning" not in text.lower()
    # Substance survives.
    assert "Dani Kim" in text or "menu list" in text


def test_email_to_raw_text_no_provider_means_no_summarization() -> None:
    """If no provider is wired, long transcripts still render verbatim — the
    UI can choose to skip the LLM call to save tokens."""
    long_transcript = "x " * 2000
    text = email_to_raw_text(_email(transcript_text=long_transcript), provider=None)
    assert "x x x" in text


def test_email_to_raw_text_no_transcript_still_renders() -> None:
    text = email_to_raw_text(_email(transcript_text=""), provider=None)
    assert "(no transcript attached)" in text


def test_mock_client_filters_by_local_date() -> None:
    client = MockOutlookClient(FIXTURE)
    emails = client.list_recap_emails(on_date=date(2026, 5, 2))
    assert len(emails) == 3
    assert client.list_recap_emails(on_date=date(2026, 1, 1)) == []


def test_mock_client_handles_missing_fixture(tmp_path: Path) -> None:
    client = MockOutlookClient(tmp_path / "missing.json")
    assert client.list_recap_emails(on_date=date(2026, 5, 2)) == []


def test_factory_modes() -> None:
    assert isinstance(get_client("mock", FIXTURE), MockOutlookClient)
    assert isinstance(get_client("live"), LiveOutlookClient)
    with pytest.raises(ValueError):
        get_client("bogus", FIXTURE)


def test_live_client_skeleton_raises_until_implemented() -> None:
    with pytest.raises(NotImplementedError):
        LiveOutlookClient().list_recap_emails(on_date=date(2026, 5, 2))


def test_pipeline_end_to_end_recaps_match_seeded_stores(conn) -> None:
    """Pull mock recaps, render to raw text (with summarization for the long
    one), then run the splitter + matcher. Asserts each recap lands in the
    expected confidence band against the seeded stores.
    """
    client = MockOutlookClient(FIXTURE)
    emails = client.list_recap_emails(on_date=date(2026, 5, 2))
    assert len(emails) == 3

    provider = get_provider("mock")
    bulk = "\n\n".join(email_to_raw_text(e, provider=provider) for e in emails)
    notes = split_notes(bulk)
    assert len(notes) == 3

    # Pioneer Coffee — long transcript was summarized; alias 'pioneer coffee'
    # appears in the meeting topic so the matcher locks on.
    pioneer = next(n for n in notes if "Pioneer" in n.raw_text)
    cands = store_matcher.match_for_text(conn, pioneer.raw_text)
    assert cands and cands[0].confidence >= 70

    # Maple Grove — owner first name 'Emma' + alias 'maple grove' present.
    maple = next(n for n in notes if "Maple Grove" in n.raw_text)
    cands = store_matcher.match_for_text(conn, maple.raw_text)
    assert cands and cands[0].confidence >= 90

    # Westside — owner last name 'Reilly' + alias 'westside' present.
    westside = next(n for n in notes if "Westside" in n.raw_text)
    cands = store_matcher.match_for_text(conn, westside.raw_text)
    assert cands and cands[0].confidence >= 90
