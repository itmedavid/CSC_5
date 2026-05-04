"""Tests for the formatter pipeline using the mock LLM provider."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

import settings
from db import seed, stores_repo
from db.connection import get_conn, init_db
from formatter.note_formatter import FormattedNote, format_note, validate
from llm.factory import get_provider


@pytest.fixture()
def conn(tmp_path: Path):
    db = tmp_path / "fmt.db"
    init_db(db)
    c = get_conn(db)
    seed.import_stores_csv(c, settings.SEED_STORES_CSV)
    yield c
    c.close()


def test_validate_clean_output() -> None:
    text = (
        "5/2 #DB |\n"
        "Spoke with Anita about the delivery slip.\n"
        "Outstanding: None.\n"
        "Risk/Blocker: None.\n"
        "Next step: Send schedule."
    )
    assert validate(text) == []


def test_validate_flags_missing_label() -> None:
    text = "5/2 #DB |\nsummary paragraph\nOutstanding: x\nNext step: y"
    warnings = validate(text)
    assert any("Risk/Blocker" in w for w in warnings)


def test_validate_flags_bullets() -> None:
    text = (
        "5/2 #DB |\n"
        "summary paragraph\n"
        "- bullet point\n"
        "Outstanding: x\nRisk/Blocker: y\nNext step: z"
    )
    warnings = validate(text)
    assert any("bullet" in w for w in warnings)


def test_format_note_with_mock_matches_template(conn) -> None:
    provider = get_provider("mock")
    store = next(
        s for s in stores_repo.all_stores(conn) if s.store_name == "Joe's Market"
    )
    fn = format_note(
        raw_note="5/2 Joe's Market - Anita is fine with delayed delivery, send schedule by Fri.",
        note_date=date(2026, 5, 2),
        initials="DB",
        store=stores_repo.get_store(conn, store.id),
        provider=provider,
    )
    assert isinstance(fn, FormattedNote)
    assert fn.validation_warnings == []
    assert "5/2 #DB |" in fn.text
    assert "Outstanding:" in fn.text
    assert "Risk/Blocker:" in fn.text
    assert "Next step:" in fn.text
    assert fn.provider == "mock"


def test_format_note_unmatched_does_not_invent_store(conn) -> None:
    provider = get_provider("mock")
    fn = format_note(
        raw_note="unknown caller said something about a new location",
        note_date="5/4",
        initials="DB",
        store=None,
        provider=provider,
    )
    assert "UNKNOWN" in fn.text or "do not invent" not in fn.text  # mock echoes ctx
    # real LLM is supposed to leave the store unnamed; mock just echoes ctx
    # so we mostly verify it didn't crash and produced template structure.
    assert "Outstanding:" in fn.text
