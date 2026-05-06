# Future milestones (out of MVP1)

Each future milestone keeps the MVP1 hard rules: no auto-paste without
approval, never invent details, log every action.

## Shipped

- ✅ **M2: `integrations/ringcentral.py`** — pull today's calls (call log
  + voicemail transcripts) and feed them into the parser as additional raw
  notes. Mock client (fixture-backed) for offline dev; live client is a
  documented skeleton waiting on JWT auth wiring.

## Planned (not yet stubbed — empty modules invite accidental imports)

- `integrations/outlook.py` — scan inbox for Zoom recap emails, download
  attached/linked transcripts.
- `agents/recap_summarizer.py` — condense long Zoom transcripts before they hit
  the formatter (otherwise the per-note token budget blows up). Pairs with
  Outlook.
- `integrations/guidecx_browser.py` — Playwright-driven helper that opens the
  matched project in GuideCX and pastes the approved note. Still gated behind a
  manual click; never autonomous.
