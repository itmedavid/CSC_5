"""Multi-signal store matcher.

Scores each candidate store against a raw note chunk and returns the top-N
with confidence (0-100) plus human-readable evidence strings. Confidence
banding is the caller's responsibility (see settings thresholds).

Signal weights (max sum 100, capped):
  95  phone exact (E.164) match anywhere in chunk (treated as a unique key)
  60  alias exact (normalized) match
  35  store name fuzzy via rapidfuzz; uses max(token_set_ratio, partial_ratio)
  20  owner name match (10 last-name only, 5 first-name only)
  15  primary contact name match (8 last-name only, 4 first-name only)
  15  email domain match (10 local-part only)
   5  city corroboration (3 state-only)
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass, field
from typing import Iterable

from rapidfuzz import fuzz

from db import stores_repo
from db.stores_repo import Store
from matcher.normalize import (
    extract_phone_e164s,
    ngrams,
    normalize_text,
)

EMAIL_RE = re.compile(r"\b([A-Za-z0-9._%+\-]+)@([A-Za-z0-9.\-]+\.[A-Za-z]{2,})\b")


@dataclass
class MatchCandidate:
    store_id: int
    confidence: int
    evidence: list[str] = field(default_factory=list)


def _emails_in(text: str) -> list[tuple[str, str]]:
    return [(m.group(1).lower(), m.group(2).lower()) for m in EMAIL_RE.finditer(text)]


def _last_name(full: str | None) -> str:
    if not full:
        return ""
    parts = normalize_text(full).split()
    return parts[-1] if parts else ""


def _first_name(full: str | None) -> str:
    if not full:
        return ""
    parts = normalize_text(full).split()
    return parts[0] if parts else ""


def _has_word(text_norm: str, word: str) -> bool:
    if not word:
        return False
    return f" {word} " in f" {text_norm} "


def _score_one(
    raw_text: str,
    store: Store,
    *,
    phones_in_text: list[str],
    text_norm: str,
    text_ngrams: set[str],
    emails_in_text: list[tuple[str, str]],
) -> MatchCandidate:
    score = 0
    evidence: list[str] = []

    # --- phone exact (unique key, very high weight) ---
    store_phones = {p for p in [store.phone_e164] if p}
    for c in store.contacts:
        if c.get("phone_e164"):
            store_phones.add(c["phone_e164"])
    matched_phones = [p for p in phones_in_text if p in store_phones]
    if matched_phones:
        score += 95
        evidence.append(f"phone exact: {matched_phones[0]}")

    # --- alias exact ---
    alias_norms = {normalize_text(a) for a in store.aliases if a}
    alias_norms.add(normalize_text(store.store_name))
    alias_hits = sorted(a for a in (alias_norms & text_ngrams) if a)
    if alias_hits:
        score += 60
        evidence.append(f"alias exact: {alias_hits[0]!r}")

    # --- name fuzzy (max of token_set_ratio and partial_ratio) ---
    store_name_norm = normalize_text(store.store_name)
    name_score = max(
        fuzz.token_set_ratio(text_norm, store_name_norm),
        fuzz.partial_ratio(text_norm, store_name_norm),
    )
    scaled = max(0, int((name_score - 50) / 50 * 35))
    if scaled > 0:
        score += scaled
        evidence.append(f"name fuzzy {int(name_score)}")

    # --- owner name ---
    owner_norm = normalize_text(store.owner_name) if store.owner_name else ""
    if owner_norm and owner_norm in text_norm:
        score += 20
        evidence.append(f"owner: {store.owner_name}")
    elif store.owner_name:
        ln = _last_name(store.owner_name)
        fn = _first_name(store.owner_name)
        if ln and len(ln) >= 3 and _has_word(text_norm, ln):
            score += 10
            evidence.append(f"owner last name: {ln}")
        elif fn and len(fn) >= 3 and _has_word(text_norm, fn):
            score += 5
            evidence.append(f"owner first name: {fn}")

    # --- primary contact ---
    pc_norm = normalize_text(store.primary_contact) if store.primary_contact else ""
    if pc_norm and pc_norm != owner_norm and pc_norm in text_norm:
        score += 15
        evidence.append(f"contact: {store.primary_contact}")
    elif store.primary_contact and pc_norm != owner_norm:
        ln = _last_name(store.primary_contact)
        fn = _first_name(store.primary_contact)
        if ln and len(ln) >= 3 and _has_word(text_norm, ln):
            score += 8
            evidence.append(f"contact last name: {ln}")
        elif fn and len(fn) >= 3 and _has_word(text_norm, fn):
            score += 4
            evidence.append(f"contact first name: {fn}")

    # --- email ---
    if emails_in_text and store.email:
        store_local, _, store_domain = store.email.lower().partition("@")
        for local, domain in emails_in_text:
            if domain == store_domain:
                score += 15
                evidence.append(f"email domain: {domain}")
                break
            if local == store_local:
                score += 10
                evidence.append(f"email local: {local}")
                break

    # --- city / state ---
    if store.city and normalize_text(store.city) in text_norm:
        score += 5
        evidence.append(f"city: {store.city}")
    elif store.state and len(store.state) == 2:
        if re.search(rf"\b{store.state}\b", raw_text):
            score += 3
            evidence.append(f"state: {store.state}")

    score = min(score, 100)
    return MatchCandidate(store_id=store.id, confidence=score, evidence=evidence)


def rank_candidates(
    raw_text: str,
    stores: Iterable[Store],
    *,
    top_n: int = 5,
    auto_threshold: int = 90,
    ambiguity_margin: int = 10,
) -> list[MatchCandidate]:
    """Score every store, return top-N. Applies the ambiguity guard: if top1
    >= auto_threshold but top2 is within `ambiguity_margin`, top1 is demoted
    by trimming its score to (auto_threshold - 1) so the UI shows it as
    needs-review. Original confidence is preserved in evidence."""
    text_norm = normalize_text(raw_text)
    tokens = text_norm.split()
    text_ngrams = set(ngrams(tokens, 1, 3))
    phones_in_text = extract_phone_e164s(raw_text)
    emails_in_text = _emails_in(raw_text)

    scored = [
        _score_one(
            raw_text,
            s,
            phones_in_text=phones_in_text,
            text_norm=text_norm,
            text_ngrams=text_ngrams,
            emails_in_text=emails_in_text,
        )
        for s in stores
    ]
    scored.sort(key=lambda c: c.confidence, reverse=True)
    top = scored[:top_n]

    if len(top) >= 2 and top[0].confidence >= auto_threshold:
        if top[0].confidence - top[1].confidence < ambiguity_margin:
            original = top[0].confidence
            top[0] = MatchCandidate(
                store_id=top[0].store_id,
                confidence=auto_threshold - 1,
                evidence=top[0].evidence
                + [f"ambiguity guard: original {original}, top2 {top[1].confidence}"],
            )

    # Drop any zero-confidence candidates from the visible top.
    return [c for c in top if c.confidence > 0]


def match_for_text(
    conn: sqlite3.Connection,
    raw_text: str,
    *,
    top_n: int = 5,
    auto_threshold: int = 90,
) -> list[MatchCandidate]:
    """Convenience wrapper that loads all stores and ranks them."""
    stores = stores_repo.all_stores(conn)
    # Hydrate contacts for phone matching.
    full = []
    for s in stores:
        full.append(stores_repo.get_store(conn, s.id))
    full = [s for s in full if s is not None]
    return rank_candidates(
        raw_text, full, top_n=top_n, auto_threshold=auto_threshold
    )
