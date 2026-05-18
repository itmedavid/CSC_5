"""Condense long meeting transcripts before they reach the note formatter.

Why a separate LLM call instead of stuffing the whole transcript into the note
formatter's user prompt:
  - Cost: a 30-minute Zoom transcript can be 5K+ tokens. Per-note formatter
    calls would balloon and prompt-cache hits would drop.
  - Quality: the formatter's job is template enforcement, not condensation.
    Asking one LLM call to do both produces worse results than two focused
    calls.

Hard rules (mirror the note formatter):
  - Never invent. Preserve every named entity, dollar amount, date, deadline,
    commitment, and decision verbatim.
  - No bullets in the output — the downstream formatter expects flowing prose.
  - Drop greetings, small talk, scheduling chit-chat, and meta ("can you hear
    me?"). Keep substance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import settings
from llm.base import LLMProvider, LLMResponse

SYSTEM_PROMPT = """You condense raw meeting transcripts into a concise factual summary that another LLM will turn into a CRM note. Your output is intermediate, not user-facing.

HARD RULES:
- Preserve every named entity, dollar amount, percentage, date, deadline, commitment, and decision verbatim. If a name appears in the transcript, keep it.
- Do not invent names, numbers, dates, or commitments not present in the transcript.
- Drop greetings ("hey", "how are you"), small talk, scheduling chit-chat, audio meta ("can you hear me", "you're on mute"), and filler.
- Keep substantive discussion: status updates, blockers, risks, decisions, action items, who-said-what when it matters.
- No bullet points, no asterisks, no markdown, no headings. Output is flowing prose.
- Target length: roughly one third of the original transcript or shorter. Shorter is fine if the substance is small.
- Tone: neutral and factual. No "the meeting was productive" filler.
- Output only the condensed text. No preamble like "Summary:" or "Here is...".

If the transcript is already short and substantive, return it lightly cleaned up rather than padding it.
"""


@dataclass
class Recap:
    text: str
    model: str
    provider: str
    latency_ms: int = 0
    token_usage: dict = field(default_factory=dict)
    was_summarized: bool = True
    raw_response: Optional[LLMResponse] = field(default=None, repr=False)


def _build_user_prompt(transcript: str, *, meeting_context: str = "") -> str:
    ctx_line = f"Meeting context: {meeting_context}\n" if meeting_context.strip() else ""
    return (
        f"{ctx_line}"
        f"Transcript:\n"
        f'"""\n{transcript.strip()}\n"""'
    )


def needs_summarization(transcript: str, *, char_threshold: int = 1500) -> bool:
    """Cheap heuristic. ~1500 chars ≈ ~400 tokens; below that the formatter
    can ingest the raw transcript directly without bloating its prompt."""
    return len(transcript or "") > char_threshold


def summarize(
    transcript: str,
    *,
    provider: LLMProvider,
    meeting_context: str = "",
    char_threshold: int = 1500,
    max_tokens: int = 600,
) -> Recap:
    """Condense `transcript`. If below `char_threshold`, returns the transcript
    unchanged (was_summarized=False) without making an LLM call."""
    transcript = (transcript or "").strip()
    if not transcript:
        return Recap(text="", model="", provider=provider.name, was_summarized=False)

    if not needs_summarization(transcript, char_threshold=char_threshold):
        return Recap(
            text=transcript,
            model="",
            provider=provider.name,
            was_summarized=False,
        )

    user_prompt = _build_user_prompt(transcript, meeting_context=meeting_context)
    response = provider.complete(
        SYSTEM_PROMPT,
        user_prompt,
        max_tokens=max_tokens,
        temperature=settings.LLM_TEMPERATURE,
        cache_system=settings.ENABLE_PROMPT_CACHE,
    )
    return Recap(
        text=response.text.strip(),
        model=response.model,
        provider=response.provider,
        latency_ms=response.latency_ms,
        token_usage=response.usage_dict(),
        was_summarized=True,
        raw_response=response,
    )
