"""Deterministic mock provider for offline dev and tests.

Builds a template-shaped response from the user prompt using simple regex
extraction. Always passes the post-hoc validator. No API calls.
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

        date = _extract(user, r"^Date:\s*(.+)$", default="Today")
        initials = _extract(user, r"^Initials:\s*(.+)$", default="DB")
        store_ctx = _extract(user, r"^Store context:\s*(.+)$", default="UNKNOWN")
        raw = _extract_block(user, r'^Raw note:\s*"""\s*\n(.*?)\n\s*"""', default="")

        summary = _summarize(raw) or "No content provided."
        text = (
            f"{date} #{initials} |\n"
            f"Mock formatter for {store_ctx}. {summary}\n"
            f"Outstanding: None.\n"
            f"Risk/Blocker: None.\n"
            f"Next step: Confirm with the user before relying on this mock output."
        )
        latency = int((time.perf_counter() - start) * 1000)
        return LLMResponse(
            text=text,
            model="mock-1",
            provider=self.name,
            input_tokens=len(system.split()) + len(user.split()),
            output_tokens=len(text.split()),
            latency_ms=latency,
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
