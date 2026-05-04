# Future milestones (deliberately out of MVP1)

These are intentionally not stubbed in code — empty modules invite accidental
imports. Each will land as its own milestone with its own PR.

- `integrations/ringcentral.py` — pull today's calls (call log + voicemail
  transcripts) and feed them into the parser as additional raw notes.
- `integrations/outlook.py` — scan inbox for Zoom recap emails, download
  attached/linked transcripts.
- `agents/recap_summarizer.py` — condense long Zoom transcripts before they hit
  the formatter (otherwise the per-note token budget blows up).
- `integrations/guidecx_browser.py` — Playwright-driven helper that opens the
  matched project in GuideCX and pastes the approved note. Still gated behind a
  manual click; never autonomous.

Each future milestone must keep the MVP1 hard rules: no auto-paste without
approval, never invent details, log every action.
