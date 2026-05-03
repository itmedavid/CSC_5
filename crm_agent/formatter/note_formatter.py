"""Glue: build prompt -> call provider -> validate output.

`format_note()` is the single entry point used by the UI. It returns a
`FormattedNote` regardless of validation result; callers surface warnings
visibly so the user can decide whether to regenerate.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

import settings
from db.stores_repo import Store
from formatter.prompts import (
    SYSTEM_PROMPT,
    build_user_prompt,
    store_context_string,
)
from llm.base import LLMProvider, LLMResponse

REQUIRED_LABELS = ("Outstanding:", "Risk/Blocker:", "Next step:")
HEADER_RE = re.compile(r"^\S.*\|\s*$", re.MULTILINE)
BULLET_RE = re.compile(r"(?m)^\s*([-*•]|\d+[.)])\s+")


@dataclass
class FormattedNote:
    text: str
    model: str
    provider: str
    latency_ms: int = 0
    token_usage: dict = field(default_factory=dict)
    validation_warnings: list[str] = field(default_factory=list)
    raw_response: Optional[LLMResponse] = field(default=None, repr=False)


def validate(text: str) -> list[str]:
    """Return a list of warning strings. Empty list means clean output."""
    warnings: list[str] = []
    if not text.strip():
        return ["empty output"]

    lines = [l for l in text.splitlines() if l.strip()]
    if not lines:
        return ["empty output"]

    if not lines[0].rstrip().endswith("|"):
        warnings.append("header line does not end with '|'")

    for label in REQUIRED_LABELS:
        if label not in text:
            warnings.append(f"missing required label: {label}")

    if BULLET_RE.search(text):
        warnings.append("contains bullet/numbered list markers; template forbids them")

    if "```" in text:
        warnings.append("contains markdown code fences")

    return warnings


def format_note(
    *,
    raw_note: str,
    note_date: date | str,
    initials: str = None,
    store: Optional[Store] = None,
    provider: LLMProvider,
) -> FormattedNote:
    initials = initials or settings.DEFAULT_INITIALS

    if store:
        ctx = store_context_string(
            store_name=store.store_name,
            project_name=store.project_name,
            guidecx_project_id=store.guidecx_project_id,
            owner_name=store.owner_name,
            primary_contact=store.primary_contact,
        )
    else:
        ctx = store_context_string()  # UNKNOWN sentinel

    user_prompt = build_user_prompt(
        raw_note=raw_note,
        note_date=note_date,
        initials=initials,
        store_context=ctx,
    )

    response = provider.complete(
        SYSTEM_PROMPT,
        user_prompt,
        max_tokens=settings.LLM_MAX_TOKENS,
        temperature=settings.LLM_TEMPERATURE,
        cache_system=settings.ENABLE_PROMPT_CACHE,
    )
    text = response.text.strip()
    warnings = validate(text)

    return FormattedNote(
        text=text,
        model=response.model,
        provider=response.provider,
        latency_ms=response.latency_ms,
        token_usage=response.usage_dict(),
        validation_warnings=warnings,
        raw_response=response,
    )
