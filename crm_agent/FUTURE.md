# Future milestones (out of MVP1)

Each future milestone keeps the MVP1 hard rules: no auto-paste without
approval, never invent details, log every action.

## Shipped

- ✅ **M2: `integrations/ringcentral.py`** — pull today's calls (call log
  + voicemail transcripts) and feed them into the parser as additional raw
  notes. Mock client (fixture-backed) for offline dev; live client is a
  documented skeleton waiting on JWT auth wiring.
- ✅ **M3: `integrations/outlook.py` + `formatter/recap_summarizer.py`** —
  pull Zoom recap emails and condense long transcripts before they hit the
  note formatter. Mock client + fixture for offline dev; live client is a
  documented Microsoft Graph skeleton.

## Planned (not yet stubbed — empty modules invite accidental imports)

- `integrations/guidecx_browser.py` — Playwright-driven helper that opens the
  matched project in GuideCX and pastes the approved note. Still gated behind a
  manual click; never autonomous.
