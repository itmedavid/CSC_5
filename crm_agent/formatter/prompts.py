"""System prompt + user-prompt builder for the CRM note formatter.

The system prompt is large and stable, so the Anthropic provider caches it
via `cache_control={"type": "ephemeral"}`. Keep it stable across edits or the
cache hit rate drops.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

SYSTEM_PROMPT = """You convert raw onboarding-rep notes into a strict CRM note format used in GuideCX. Follow the format exactly.

OUTPUT FORMAT (line-prefix, no JSON, no markdown, no bullets):

Line 1 — header (single line):
[Date] #[Initials] |

Line 2 — fluid status summary paragraph (no bullets, no line breaks inside the paragraph). One management-update-tone paragraph that summarizes what happened, who was involved, and the current state.

Then three labeled lines, each on its own line, in this exact order:
Outstanding: <what is still open / waiting on someone / not yet done>
Risk/Blocker: <what could derail the project, or "None.">
Next step: <the single most important next action>

HARD RULES:
- Never invent details. Do not add names, dates, dollar amounts, store names, or commitments not present in the raw note.
- Preserve all named entities, dollar amounts, and dates verbatim.
- Light grammar and clarity fixes only. Preserve meaning.
- No bullet points, no asterisks, no numbered lists, no markdown.
- Always emit ALL THREE labels (Outstanding, Risk/Blocker, Next step). If a section has nothing to report, write the label followed by "None." Never omit a label.
- Tone: management update. Concise, direct, professional. No filler.
- Output only the formatted note. No preamble, no explanation, no closing remarks.
- The header line must be exactly: [Date] #[Initials] | — including the trailing pipe.
- Use the Date and Initials provided in the user message. Use the Store context to inform phrasing but never to invent facts the raw note does not support.
- If the Store context is "UNKNOWN — do not invent a store name.", do not name a store anywhere in the output. Use neutral phrasing like "the prospect" or "the contact" and flag the store identity as outstanding.

WORKED EXAMPLE

User input:
Date: 5/2
Initials: DB
Store context: Joe's Market (project J-1042), owner Anita Patel
Raw note:
\"\"\"
5/2 Joe's Market - call w Anita, hardware delivery slipped to next wk, she is fine w it. need to send updated install schedule by friday.
\"\"\"

Expected output:
5/2 #DB |
Spoke with Anita Patel at Joe's Market regarding the hardware delivery, which has slipped by one week. Anita is comfortable with the revised timing.
Outstanding: Updated install schedule needs to be sent to Anita by Friday.
Risk/Blocker: None.
Next step: Send the updated install schedule by Friday.
"""


def build_user_prompt(
    *,
    raw_note: str,
    note_date: date | str,
    initials: str,
    store_context: str,
) -> str:
    """Compose the per-call user prompt. `note_date` may be a date or a
    pre-formatted string ('5/2'); we normalize date objects to M/D format."""
    if hasattr(note_date, "strftime"):
        date_str = f"{note_date.month}/{note_date.day}"
    else:
        date_str = str(note_date)

    return (
        f"Date: {date_str}\n"
        f"Initials: {initials}\n"
        f"Store context: {store_context}\n"
        f"Raw note:\n"
        f'"""\n{raw_note.strip()}\n"""'
    )


def store_context_string(
    *,
    store_name: Optional[str] = None,
    project_name: Optional[str] = None,
    guidecx_project_id: Optional[str] = None,
    owner_name: Optional[str] = None,
    primary_contact: Optional[str] = None,
) -> str:
    """Build a short factual store_context string from a Store row.

    Caller passes the matched Store. If unmatched, pass nothing -> sentinel.
    """
    if not store_name:
        return "UNKNOWN — do not invent a store name."

    parts = [store_name]
    proj_bits = []
    if guidecx_project_id:
        proj_bits.append(guidecx_project_id)
    if project_name and project_name != store_name:
        proj_bits.append(project_name)
    if proj_bits:
        parts.append(f"(project {', '.join(proj_bits)})")
    if owner_name:
        parts.append(f"owner {owner_name}")
    if primary_contact and primary_contact != owner_name:
        parts.append(f"primary contact {primary_contact}")

    return ", ".join(parts).replace(", (", " (")
