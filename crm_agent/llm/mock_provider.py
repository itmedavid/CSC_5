"""Deterministic mock provider for offline dev and tests.

Recognizes two prompt shapes:

  1. Note-formatter prompts (start with `Date:` / `Initials:` / `Store context:`
     / `Raw note:`) — builds a template-shaped CRM note.
  2. Recap-summarizer prompts (contain `Transcript:`) — returns a trimmed copy
     of the transcript with a few obvious filler phrases dropped, simulating
     condensation without making an API call.

Always passes the post-hoc validator on the note-formatter path.
"""

from __future__ import annotations

import re
import time

from llm.base import LLMProvider, LLMResponse


class MockProvider(LLMProvider):
    name = "mock"

    def complete(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int = 800,
        temperature: float = 0.2,
        cache_system: bool = True,
    ) -> LLMResponse:
        start = time.perf_counter()

        if _looks_like_recap(user):
            text = _mock_recap_summary(user)
        else:
            text = _mock_note(user)

        latency = int((time.perf_counter() - start) * 1000)
        return LLMResponse(
            text=text,
            model="mock-1",
            provider=self.name,
            input_tokens=len(system.split()) + len(user.split()),
            output_tokens=len(text.split()),
            latency_ms=latency,
        )


def _looks_like_recap(user_prompt: str) -> bool:
    # Recap prompts wrap the transcript in triple quotes after a `Transcript:`
    # line and never include `Raw note:` / `Store context:`.
    return (
        "Transcript:" in user_prompt
        and "Raw note:" not in user_prompt
        and "Store context:" not in user_prompt
    )


def _mock_recap_summary(user_prompt: str) -> str:
    transcript = _extract_block(
        user_prompt, r'^Transcript:\s*"""\s*\n(.*?)\n\s*"""', default=""
    )
    # Drop obvious filler lines so the mock visibly "condenses" something.
    lines = []
    filler = (
        "hey", "hi ", "hello", "how are you", "can you hear me",
        "you're on mute", "good morning", "good afternoon",
    )
    for line in transcript.splitlines():
        s = line.strip().lower()
        if not s:
            continue
        if any(s.startswith(f) or f in s[:30] for f in filler):
            continue
        lines.append(line.strip())
    joined = " ".join(lines)
    return joined or transcript.strip() or "(empty transcript)"


def _mock_note(user_prompt: str) -> str:
    date = _extract(user_prompt, r"^Date:\s*(.+)$", default="Today")
    initials = _extract(user_prompt, r"^Initials:\s*(.+)$", default="DB")
    store_ctx = _extract(user_prompt, r"^Store context:\s*(.+)$", default="UNKNOWN")
    raw = _extract_block(user_prompt, r'^Raw note:\s*"""\s*\n(.*?)\n\s*"""', default="")

    summary = _summarize(raw) or "No content provided."
    return (
        f"{date} #{initials} |\n"
        f"Mock formatter for {store_ctx}. {summary}\n"
        f"Outstanding: None.\n"
        f"Risk/Blocker: None.\n"
        f"Next step: Confirm with the user before relying on this mock output."
    )


def _extract(text: str, pattern: str, *, default: str = "") -> str:
    m = re.search(pattern, text, re.MULTILINE)
    return (m.group(1).strip() if m else default).strip()


def _extract_block(text: str, pattern: str, *, default: str = "") -> str:
    m = re.search(pattern, text, re.DOTALL | re.MULTILINE)
    return (m.group(1).strip() if m else default).strip()


def _summarize(raw: str, max_chars: int = 220) -> str:
    raw = " ".join(raw.split())
    if not raw:
        return ""
    if len(raw) <= max_chars:
        return raw
    return raw[: max_chars - 1].rstrip() + "…"
