"""Normalization helpers used by both the seed importer and the matcher.

Single source of truth for what counts as "the same" alias / phone / name.
"""

from __future__ import annotations

import re
from typing import Iterable

import phonenumbers

PHONE_TOKEN_RE = re.compile(r"(\+?\d[\d\-\s().]{7,}\d)")


def to_e164(raw: str | None, region: str = "US") -> str | None:
    """Return the E.164 representation of `raw`, or None if unparseable."""
    if not raw:
        return None
    raw = raw.strip()
    if not raw:
        return None
    try:
        parsed = phonenumbers.parse(raw, region)
    except phonenumbers.NumberParseException:
        return None
    if not phonenumbers.is_valid_number(parsed):
        return None
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


def normalize_text(s: str | None) -> str:
    """Lowercase, strip punctuation, collapse whitespace.

    Used to compare aliases / names cheaply via exact equality on `*_norm`
    columns. Keeps letters and digits, replaces everything else with a space.
    """
    if not s:
        return ""
    s = s.casefold()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def extract_phone_e164s(text: str, region: str = "US") -> list[str]:
    """Find phone-like substrings in free text and normalize them.

    Returns deduplicated E.164 strings, preserving order of first appearance.
    """
    seen: dict[str, None] = {}
    for match in PHONE_TOKEN_RE.finditer(text):
        e164 = to_e164(match.group(1), region)
        if e164 and e164 not in seen:
            seen[e164] = None
    return list(seen.keys())


def split_aliases(field: str | None) -> list[str]:
    """Pipe-delimited alias field -> list of trimmed alias strings."""
    if not field:
        return []
    return [a.strip() for a in field.split("|") if a.strip()]


def ngrams(tokens: Iterable[str], min_n: int = 1, max_n: int = 3) -> list[str]:
    """Generate 1..max_n-grams (joined by space) from a token list."""
    toks = list(tokens)
    out: list[str] = []
    for n in range(min_n, max_n + 1):
        for i in range(len(toks) - n + 1):
            out.append(" ".join(toks[i : i + n]))
    return out
