"""Tests for the note splitter heuristics."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from parser.note_splitter import (
    DATE_HEADER_RE,
    merge,
    split_at,
    split_notes,
)

FIXTURE = Path(__file__).parent / "fixtures" / "sample_bulk_notes.txt"


def test_date_regex_matches_common_formats() -> None:
    assert DATE_HEADER_RE.match("5/2 some text")
    assert DATE_HEADER_RE.match("05/02/2026 some text")
    assert DATE_HEADER_RE.match("2026-05-02 some text")
    assert DATE_HEADER_RE.match("Mon some text")
    assert DATE_HEADER_RE.match("May 2 some text")
    assert not DATE_HEADER_RE.match("just a regular note")


def test_split_on_date_headers_primary() -> None:
    text = FIXTURE.read_text()
    notes = split_notes(text)
    assert len(notes) == 6
    # Every chunk should be tagged with a date-header reason.
    assert all("date header" in n.split_reason for n in notes)
    # Detected dates should populate.
    detected = [n.detected_date for n in notes]
    assert detected[0] == date(date.today().year, 5, 2)
    assert detected[2] == date(date.today().year, 5, 3)
    assert detected[5] == date(date.today().year, 5, 4)


def test_split_on_delimiter_when_no_date_headers() -> None:
    text = "Joe Market call went well\n---\nSunrise bakery needs training\n---\nWestside risk"
    notes = split_notes(text)
    assert len(notes) == 3
    assert "delimiter" in notes[1].split_reason


def test_blank_line_fallback() -> None:
    text = "first note line\nsecond line of first\n\n\nsecond note starts here\nmore text"
    notes = split_notes(text)
    assert len(notes) == 2
    assert "blank" in notes[1].split_reason


def test_phone_extraction_in_chunk() -> None:
    text = FIXTURE.read_text()
    notes = split_notes(text)
    sunrise = notes[1]
    assert sunrise.detected_phone == "+12125559876"
    # the unknown caller note has (555) 010-2030, which is not a valid US number,
    # so detected_phone should be None.
    unknown = notes[5]
    assert unknown.detected_phone is None


def test_alias_hits() -> None:
    text = "5/2 Pioneer Coffee Roasters - dani confirmed go-live."
    notes = split_notes(text, alias_norm_set={"pioneer coffee", "pioneer", "joe s"})
    assert len(notes) == 1
    assert "pioneer coffee" in notes[0].detected_alias_hits


def test_empty_input() -> None:
    assert split_notes("") == []
    assert split_notes("   \n  \n") == []


def test_merge_combines_with_previous() -> None:
    text = FIXTURE.read_text()
    notes = split_notes(text)
    assert len(notes) == 6
    merged = merge(notes, notes[1].id)  # merge sunrise into joe's
    assert len(merged) == 5
    assert "Joe's Market" in merged[0].raw_text
    assert "Sunrise Bakery" in merged[0].raw_text


def test_split_at_user_breakpoint() -> None:
    notes = split_notes("5/2 Joe's Market line one\nline two\nline three")
    assert len(notes) == 1
    out = split_at(notes, notes[0].id, 1)
    assert len(out) == 2
    assert "line one" in out[0].raw_text
    assert "line two" in out[1].raw_text
