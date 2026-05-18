"""Tests for the recap summarizer (uses the mock LLM provider)."""

from __future__ import annotations

from formatter.recap_summarizer import (
    needs_summarization,
    summarize,
)
from llm.factory import get_provider


def test_needs_summarization_threshold() -> None:
    assert needs_summarization("a" * 2000) is True
    assert needs_summarization("a" * 100) is False
    assert needs_summarization("") is False
    assert needs_summarization(None) is False


def test_short_transcript_passes_through_unchanged() -> None:
    short = "Emma at Maple Grove needs a second register sooner."
    recap = summarize(short, provider=get_provider("mock"))
    assert recap.was_summarized is False
    assert recap.text == short


def test_long_transcript_invokes_provider_and_returns_condensed() -> None:
    long_transcript = (
        "Hey, good morning everyone. Can you hear me okay? Great.\n"
        "Hi Dani, thanks for joining.\n"
        + "Dani Kim from Pioneer Coffee Roasters confirmed the menu list. "
        * 30
        + "Action items: send schedule by Friday."
    )
    assert len(long_transcript) > 1500
    recap = summarize(long_transcript, provider=get_provider("mock"))
    assert recap.was_summarized is True
    assert recap.provider == "mock"
    # The mock drops filler ("good morning", "hi Dani", "can you hear me").
    assert "good morning" not in recap.text.lower()
    assert "hi dani" not in recap.text.lower()
    # Substance survives.
    assert "Dani Kim" in recap.text or "Pioneer Coffee" in recap.text


def test_empty_transcript_returns_empty_recap() -> None:
    recap = summarize("", provider=get_provider("mock"))
    assert recap.was_summarized is False
    assert recap.text == ""


def test_summarizer_passes_meeting_context_into_prompt() -> None:
    """Smoke test: the provider is called with a prompt that includes the
    meeting context line when supplied."""
    calls = {}

    class CapturingProvider:
        name = "capture"

        def complete(self, system, user, **kwargs):
            calls["system"] = system
            calls["user"] = user
            from llm.base import LLMResponse
            return LLMResponse(
                text="condensed text",
                model="capture-1",
                provider=self.name,
            )

    long = "x" * 2000
    summarize(
        long,
        provider=CapturingProvider(),
        meeting_context="Pioneer Coffee onboarding sync",
    )
    assert "Meeting context: Pioneer Coffee onboarding sync" in calls["user"]
    assert 'Transcript:' in calls["user"]
