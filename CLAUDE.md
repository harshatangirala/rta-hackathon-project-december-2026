# Agent instructions — RTA Future Move Hackathon, Team 7

Start with docs/HANDOFF.md. Keep docs/PROGRESS.md and docs/HANDOFF.md updated after every work block.

## Hard rules
- Never invent schema fields, row counts, statistics, metrics or successful Dataiku runs.
  Only fields listed in docs/EVIDENCE_AND_SCHEMA.md are verified.
- Nol + Running_time = actual, one day (Mon 15 Dec 2025). GTFS = planned 11 Sep–31 Dec 2026.
  Never compare them as the same period. Label any cross-period view "ASSUMPTION SCENARIO".
- No multi-day, weekly, seasonal or holiday forecasting claims (one observed day). Forecasts are intraday 15/60 min.
- Hackathon guide: visual recipes before code; Flow Zones + recipe descriptions; drop/hash PII
  (NOL_ID, Driver_id) before any LLM; data stays in Dataiku (no raw rows in this repo);
  no fare increases; no infrastructure proposals; protect equity and driver rest; leakage checks.
- The user builds in the Dataiku UI. Give click-level steps, Dataiku formula syntax (numval, floor, if)
  and paste-ready code. No local data processing.
- Keep chat output concise. One agent; no broad unrelated research.

## Layout
README.md · docs/ (evidence, flow design, runbook, progress, handoff) · code/ (prompts, webapp, fallback recipes)
