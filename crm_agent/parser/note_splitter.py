"""Split a bulk-pasted day's worth of raw notes into individual chunks.

Heuristic order, per plan:
  1. Date header at start of line (primary; user's existing convention).
  2. Explicit delimiter (^---+$ or ^===+$).
  3. Store-name cues (short title-case lines OR lines containing a known
     normalized alias).
  4. Blank-line fallback (2+ consecutive blank lines).
  5. Last resort: single chunk.

Each chunk records its `split_reason` so the UI can show it subtly and the
user can trust why a split happened.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from matcher.normalize import extract_phone_e164s, normalize_text

DATE_HEADER_RE = re.compile(
    r"""^\s*
        (
            \d{1,2}/\d{1,2}(?:/\d{2,4})?\b                      # 5/2 or 05/02/2026
          | \d{4}-\d{2}-\d{2}\b                                 # 2026-05-02
          | (?:Mon(?:day)?
              |Tue(?:sday)?
              |Wed(?:nesday)?
              |Thu(?:rsday)?
              |Fri(?:day)?
              |Sat(?:urday)?
              |Sun(?:day)?
            )\b                                                  # weekday
          | (?:Jan(?:uary)?
              |Feb(?:ruary)?
              |Mar(?:ch)?
              |Apr(?:il)?
              |May
              |Jun(?:e)?
              |Jul(?:y)?
              |Aug(?:ust)?
              |Sep(?:tember)?
              |Oct(?:ober)?
              |Nov(?:ember)?
              |Dec(?:ember)?
            )\s+\d{1,2}\b                                       # Jan 5
        )
    """,
    re.IGNORECASE | re.VERBOSE,
)

DELIM_RE = re.compile(r"^\s*(?:-{3,}|={3,})\s*$")


@dataclass
class RawNote:
    id: str
    raw_text: str
    detected_date: Optional[date] = None
    detected_phone: Optional[str] = None
    detected_alias_hits: list[str] = field(default_factory=list)
    split_reason: str = ""


def _parse_date_from_header(line: str) -> Optional[date]:
    """Parse a date out of a header line. Returns None if it's just a weekday
    or month-name without enough info to build a real date."""
    m = re.match(r"\s*(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?", line)
    if m:
        try:
            month, day, year = int(m.group(1)), int(m.group(2)), m.group(3)
            if year:
                y = int(year)
                if y < 100:
                    y += 2000
            else:
                y = date.today().year
            return date(y, month, day)
        except ValueError:
            return None
    m = re.match(r"\s*(\d{4})-(\d{2})-(\d{2})", line)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    return None


def _store_cue_for_line(line: str, alias_norm_set: set[str]) -> Optional[str]:
    """If `line` looks like a store header (short, ends with ':', or contains
    a known alias), return the matching alias_norm or '(cue)'."""
    stripped = line.strip()
    if not stripped or len(stripped) > 60:
        return None
    norm = normalize_text(stripped.rstrip(":"))
    if norm in alias_norm_set:
        return norm
    if stripped.endswith(":") and len(stripped.split()) <= 6:
        toks = stripped.rstrip(":").split()
        if all(t[0].isupper() for t in toks if t and t[0].isalpha()):
            return "(cue)"
    if any(alias and alias in norm for alias in alias_norm_set if alias):
        for alias in alias_norm_set:
            if alias and alias in norm:
                return alias
    return None


def split_notes(
    bulk_text: str,
    *,
    alias_norm_set: Optional[set[str]] = None,
) -> list[RawNote]:
    """Split bulk paste into RawNote chunks. Empty input -> empty list."""
    if not bulk_text or not bulk_text.strip():
        return []
    alias_norm_set = alias_norm_set or set()

    lines = bulk_text.splitlines()
    n = len(lines)

    # Pass 1: find boundaries by priority. A boundary is "split BEFORE line i".
    boundaries: dict[int, str] = {0: "start"}

    has_date_header = any(DATE_HEADER_RE.match(line) for line in lines)
    has_delim = any(DELIM_RE.match(line) for line in lines)

    if has_date_header:
        for i, line in enumerate(lines):
            if i == 0:
                continue
            if DATE_HEADER_RE.match(line):
                boundaries[i] = f"date header: {line.strip()[:30]}"
    elif has_delim:
        for i, line in enumerate(lines):
            if DELIM_RE.match(line):
                # Split AFTER the delimiter line; the delim itself is dropped.
                if i + 1 < n:
                    boundaries[i + 1] = "delimiter '---'"
    else:
        # Try store-name cues first.
        cues_found = False
        for i, line in enumerate(lines):
            if i == 0:
                continue
            cue = _store_cue_for_line(line, alias_norm_set)
            if cue:
                # Only split if the previous line is non-blank-content (we're
                # starting a new section, not continuing one).
                if i - 1 >= 0 and lines[i - 1].strip():
                    boundaries[i] = f"store cue: {line.strip()[:30]}"
                    cues_found = True
        if not cues_found:
            # Blank-line fallback: split on 2+ consecutive blank lines.
            blank_run = 0
            for i, line in enumerate(lines):
                if line.strip() == "":
                    blank_run += 1
                else:
                    if blank_run >= 2 and i not in boundaries:
                        boundaries[i] = "blank-line gap"
                    blank_run = 0

    # Pass 2: build chunks.
    sorted_boundaries = sorted(boundaries.keys())
    chunks: list[RawNote] = []
    for idx, start in enumerate(sorted_boundaries):
        end = sorted_boundaries[idx + 1] if idx + 1 < len(sorted_boundaries) else n
        chunk_lines = lines[start:end]
        # If we split on a delimiter, drop the delimiter line itself which sits
        # at end-1 of the previous chunk (handled above by splitting after it).
        # Trim the delimiter line if it's the last line of this chunk.
        while chunk_lines and DELIM_RE.match(chunk_lines[-1]):
            chunk_lines.pop()
        text = "\n".join(chunk_lines).strip("\n")
        if not text.strip():
            continue
        reason = boundaries.get(start, "")
        if reason == "start":
            if has_date_header and DATE_HEADER_RE.match(chunk_lines[0]):
                reason = f"date header: {chunk_lines[0].strip()[:30]}"
            else:
                reason = "start of paste"
        chunks.append(_build_raw_note(text, reason, alias_norm_set))

    if not chunks:
        chunks.append(_build_raw_note(bulk_text.strip(), "single chunk", alias_norm_set))

    return chunks


def _build_raw_note(text: str, reason: str, alias_norm_set: set[str]) -> RawNote:
    detected_date: Optional[date] = None
    first_line = text.splitlines()[0] if text.splitlines() else ""
    if DATE_HEADER_RE.match(first_line):
        detected_date = _parse_date_from_header(first_line)

    phones = extract_phone_e164s(text)
    norm_text = normalize_text(text)
    alias_hits = sorted({a for a in alias_norm_set if a and a in norm_text})

    return RawNote(
        id=str(uuid.uuid4()),
        raw_text=text,
        detected_date=detected_date,
        detected_phone=phones[0] if phones else None,
        detected_alias_hits=alias_hits,
        split_reason=reason,
    )


def merge(notes: list[RawNote], target_id: str) -> list[RawNote]:
    """Merge `target_id` into the previous note. Returns a new list."""
    out: list[RawNote] = []
    for note in notes:
        if note.id == target_id and out:
            prev = out[-1]
            merged_text = prev.raw_text.rstrip() + "\n" + note.raw_text.lstrip()
            out[-1] = _build_raw_note(merged_text, "merged with previous", set())
        else:
            out.append(note)
    return out


def split_at(notes: list[RawNote], target_id: str, line_index: int) -> list[RawNote]:
    """Split note `target_id` into two at line_index (0-based). Returns a new list."""
    out: list[RawNote] = []
    for note in notes:
        if note.id != target_id:
            out.append(note)
            continue
        lines = note.raw_text.splitlines()
        if line_index <= 0 or line_index >= len(lines):
            out.append(note)
            continue
        first = "\n".join(lines[:line_index]).strip()
        second = "\n".join(lines[line_index:]).strip()
        if first:
            out.append(_build_raw_note(first, "user split", set()))
        if second:
            out.append(_build_raw_note(second, "user split", set()))
    return out
