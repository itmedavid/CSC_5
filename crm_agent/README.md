# CRM Onboarding Assistant — MVP1

Local-first Streamlit app for turning a day's worth of raw onboarding notes
(call summaries, Zoom recap text, scratch notes) into clean, paste-ready CRM
notes that match the GuideCX template.

**Hard rules:** never auto-paste, never invent details, every approval is
logged, and the LLM provider is swappable.

## What it does in MVP1

1. You paste bulk raw notes for the day.
2. The parser splits on date headers (your existing convention), with `---`,
   store-name cues, and blank-line gaps as fallbacks.
3. The matcher identifies the store for each chunk via phone (E.164), aliases,
   fuzzy name match, owner / contact names, email, and city — combined into a
   0–100 confidence score with evidence strings.
4. The formatter calls Claude (or OpenAI) to rewrite each chunk in the
   GuideCX template (header line, fluid summary paragraph, then `Outstanding:`
   / `Risk/Blocker:` / `Next step:` labels).
5. You review, edit, approve, or skip each generated note.
6. Approved notes are exported to `exports/approved_notes_<ts>.txt` (paste-ready),
   and every approve/skip decision is appended to `logs/action_log.jsonl`.

Future milestones — RingCentral pull, Outlook/Zoom recap pull, GuideCX browser
automation — are listed in `FUTURE.md` and deliberately not stubbed.

## Setup

```bash
cd crm_agent
pip install -e .

cp .env.example .env
# edit .env and set ANTHROPIC_API_KEY (or OPENAI_API_KEY)
```

Tests work without any API key (they use the deterministic mock provider):

```bash
pytest tests/
```

## Run

```bash
streamlit run app.py
```

Then in the browser:

1. **Stores** page → "Import seed CSV" to load the 5 fixture stores.
2. **Parse** page → paste your notes (or paste the contents of
   `tests/fixtures/sample_bulk_notes.txt`) → click Parse.
3. **Review** page → for each card: pick the right store if it's in the
   needs-review band, click Generate, edit the formatted text, and Approve
   or Skip.
4. **Export** page → click "Export N approved notes" to write the text file
   and append to the action log.

## Configuration (`.env`)

| Var | Default | Purpose |
|---|---|---|
| `LLM_PROVIDER` | `anthropic` | `anthropic`, `openai`, or `mock` |
| `ANTHROPIC_API_KEY` | — | Required when provider is `anthropic` |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-6` | Override at session level via the sidebar |
| `OPENAI_API_KEY` | — | Required when provider is `openai` |
| `OPENAI_MODEL` | `gpt-4o` | |
| `DEFAULT_INITIALS` | `DB` | Used in the header line of each note |
| `AUTO_MATCH_THRESHOLD` | `90` | Confidence ≥ this auto-selects a store |
| `REVIEW_THRESHOLD` | `70` | Below auto, above this = needs review |
| `LLM_TEMPERATURE` | `0.2` | Ignored for `claude-opus-4-7` (parameter removed) |
| `LLM_MAX_TOKENS` | `800` | Per-note generation cap |
| `ENABLE_PROMPT_CACHE` | `true` | Anthropic system-block caching |
| `TIMEZONE` | `America/Los_Angeles` | Used when the parser can't find a date |

The sidebar can override `LLM_PROVIDER`, default initials, default date, and
the two confidence thresholds for the current session.

## Project layout

```
crm_agent/
  app.py                    # Streamlit entrypoint + sidebar
  settings.py               # config from env + defaults
  data/
    schema.sql              # SQLite DDL (single source of truth)
    seed_stores.csv         # 5 fixture stores
    seed_contacts.csv       # secondary contacts
    store_database.db       # gitignored
  db/                       # connection, stores_repo, CSV seeder
  parser/note_splitter.py   # bulk text -> RawNote[]
  matcher/                  # normalize.py + store_matcher.py
  llm/                      # base ABC + anthropic/openai/mock providers + factory
  formatter/                # SYSTEM_PROMPT + build_user_prompt + orchestrator
  ui/                       # Streamlit pages (parse / review / export / stores)
  exporters/                # text file writer + JSONL action log
  integrations/             # external systems
    ringcentral.py          # M2: call-log pull (mock + live skeleton)
    outlook.py              # M3: Zoom-recap email pull (mock + live skeleton)
  formatter/
    note_formatter.py       # builds prompt -> provider -> validate
    prompts.py              # SYSTEM_PROMPT for note formatting
    recap_summarizer.py     # M3: condense long transcripts before formatting
  exports/                  # gitignored: approved_notes_<ts>.txt
  logs/                     # gitignored: action_log.jsonl
  tests/                    # 51 unit + integration tests (pytest)
```

## Hard rules (also enforced in code)

- The formatter's system prompt forbids inventing names, dates, dollar amounts,
  or commitments not in the raw note.
- If the matched store is `None`, the LLM is told `"UNKNOWN — do not invent a
  store name."` and uses neutral phrasing.
- Approve is only enabled when both a store is selected and the formatted text
  is non-empty.
- Export writes a text file you have to download/copy yourself — nothing ever
  reaches GuideCX without your action.
- Every approved AND skipped item appends a row to `logs/action_log.jsonl`
  with raw text, formatted text, store snapshot, evidence, token usage, and
  validation warnings.

## Verifying prompt caching (Anthropic)

After running a few notes in a single session, `cat logs/action_log.jsonl` and
look at `llm_tokens.cache_read` — it should be 0 on the first note and >0 on
subsequent notes within the same session, indicating the system block is being
served from cache. Note: the system prompt is currently small (~500 tokens),
which is below the Sonnet 4.6 cache minimum (~2K tokens). The infrastructure
is in place for when the prompt grows.

## RingCentral integration (M2)

Pulls today's calls and converts each into a date-headered raw note that
flows through the same parse / match / format pipeline. The fixture-backed
mock client works offline; the live client is a documented skeleton.

To switch on the live client:

1. `pip install ringcentral` (the official Python SDK).
2. Set `RINGCENTRAL_MODE=live` and the four `RINGCENTRAL_*` vars in `.env`.
3. Implement `_authenticate()` and `list_calls()` in
   `integrations/ringcentral.py` per the docstring (JWT auth recommended).

In the UI: the **Parse** page has a "Pull from RingCentral" expander that
fetches calls for a chosen date and appends them to the bulk paste. Click
Parse to run the rest of the pipeline.

## Outlook + recap summarizer (M3)

Pulls Zoom recap emails the same way M2 pulls calls. Long transcripts are
routed through `formatter/recap_summarizer.py` — a separate LLM call with its
own condensation-focused system prompt — before reaching the note formatter.
This keeps per-note token budgets small and prompt-cache hit rates high.

The threshold (`RECAP_SUMMARIZE_CHAR_THRESHOLD`, default 1500 chars ≈ 400
tokens) is configurable in `.env`. Below the threshold, transcripts pass
through untouched without an LLM call.

To switch on the live Outlook client:

1. Register an app in Azure AD with `Mail.Read` (or `Mail.Read.Shared`).
2. `pip install msal` and either `msgraph-sdk` or use `httpx` directly.
3. Set `OUTLOOK_MODE=live` and the three `OUTLOOK_*` vars in `.env`.
4. Implement `_authenticate()` and `list_recap_emails()` in
   `integrations/outlook.py` per the docstring.

In the UI: the **Parse** page has a "Pull from Outlook" expander parallel to
the RingCentral one, with a checkbox to toggle whether long transcripts get
summarized via the LLM.

## Tests

```bash
pytest tests/ -v
```

51 tests cover: the SQLite schema and CSV seeder, the note splitter heuristics
(date headers, `---`, blank lines), the matcher's confidence bands and the
ambiguity guard, the formatter pipeline + post-hoc validator (using the mock
provider, no API key required), the RingCentral conversion + mock client +
end-to-end pipeline integration, the recap summarizer's threshold + provider
interaction, and the Outlook conversion + mock client + end-to-end pipeline
integration with summarization.
