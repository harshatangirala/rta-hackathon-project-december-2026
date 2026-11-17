# Handoff (for Codex or a new Claude session)

## Current state (2026-11-17 late, session 2)
- **BUILT AND VERIFIED in Dataiku (user screenshots):** M1-M3 (quality checks, cleaning, aggregates), M4 forecast (Ridge h1 MAE 16.717 / h4 21.388 on a time-split test; metrics vs baseline in forecast_metrics), M5/M6 decisions + swap scenario (route_hour_decisions, route_evidence_card, decision_summary), M7 congestion/alternatives/daily report (stop_hour_crowding, segment_hotspots, alt_route_candidates, daily_ops_report, ops_summary), HTML pages (code/rta_demandpulse_v2.html static; code/rta_ops_webapp.html + code/ops_webapp_backend.py live webapp 'DemandPulse Ops'; user reports the dashboard part is done). Details and numbers: docs/PROGRESS.md and docs/REPORT_DRAFT.md.
- **REMAINING (confirmed with user):** (1) Flow Zones Z0-Z8 + recipe descriptions + Wiki (guide DOs 9/16/21) - NOT DONE; (2) agents: first check whether the Prompt recipe LLM dropdown lists any model; if yes build a case-file recipe + 2 specialist Prompt recipes + a coordinator (numbers-only prompts; summary data only), if empty keep the labelled RULE-BASED agents; (3) report (fill REPORT_DRAFT sections 1, 4, 8, 10 + screenshots incl. feature importance for criterion 4.3); (4) slides; (5) demo readiness: start the webapp backend, keep code/rta_demandpulse_v2.html as backup; (6) mentor questions: OneDrive screenshots with raw rows (guide DON'T 8), messaging channel/Scenario for sending the report; (7) optional native Dataiku Dashboard and a rebuild Scenario. State in the report: no external/open data used.
- Older lines below this section describe earlier milestones and may be stale; PROGRESS.md is authoritative.
- (Historical) M1 COMPLETE; M2 COMPLETE (Part C user-reported).
- Instance = **Dataiku DSS 15.2** (INFERRED from the Help Center banner), Dataiku Cloud.
- **The user is a first-time Dataiku user:** give literal click paths ("single-click", "double-click",
  "right panel", button names) plus "what you should see" and "if it looks different" for every step.
  No results exist. Don't report any metric as achieved.
- Read in this order: AGENTS.md → docs/MILESTONES.md → docs/VALIDATION_AND_LIMITATIONS.md →
  docs/EVIDENCE_AND_SCHEMA.md → docs/DATAIKU_FLOW.md → docs/PROGRESS.md (BUILD_RUNBOOK = background).
- The user is a Dataiku beginner with ~2 hours. Main deliverable = the Dataiku Flow. Also needed: HTML page and deck.
- AI assistants have no Dataiku access. The user clicks; we give exact steps and paste-ready formulas, prompts and code.

## Working mode (session 2 onward)
- Strict milestones M1–M9 in docs/MILESTONES.md. This order supersedes BUILD_RUNBOOK's time plan.
- One milestone per turn. Stop and wait until the user confirms and pastes evidence.
- Each step card has 8 items: menu, object name, in/out, recipe + settings, grain/keys, verify, evidence, fallback.
- Challenge every major step: grain, join multiplication, leakage, 2025-vs-2026 mixing, one-day claims, PII,
  LLM doing maths, DSS feature availability, time. Uncertain items get a label in VALIDATION_AND_LIMITATIONS.md.
- After each milestone: update PROGRESS.md, HANDOFF.md, MILESTONES.md status, and the V-register.

## DEADLINE: submission is tomorrow (2026-11-18 per the user's report). Compressed plan in PROGRESS.md.
Maintain docs/REPORT_DRAFT.md after each milestone (verified numbers only).

## NEW SCOPE (feedback, 17 Nov): congestion + alternatives + supply-demand gaps + end-of-day agent report + 2 HTML dashboards (RTA Control Room; Planning and Passenger Advisory). Customer trip-planner chatbot conflicts with guide DO #19: decision pending (default = small advisory panel only). Next: user imports DATA.stops, runs code/m7_ops_hotspots.py, pastes ops_summary + top hotspots + alternatives; assistant then builds both dashboards from those numbers (aggregates only).

## STATUS (late 17 Nov): M7 hotspot recipe ran on real data; webapp 'DemandPulse Ops' (code/rta_ops_webapp.html + code/ops_webapp_backend.py) built and tested on stubs; user to paste into a new Standard webapp (HTML tab + Python tab), start the backend and check it loads. Then: Flow Zones + descriptions + Wiki, report and slides (use REPORT_DRAFT sections 5, 6, 7, 7b). Optional: Prompt-recipe agents if an LLM is connected; Dataiku Scenario to rebuild + send report (needs admin channel). Customer trip-planner NOT built (DO #19).

## Exact next actions
Follow the FINAL 2-HOUR PLAN in PROGRESS.md (blocks A-F). Ready code: code/m4e_compute_forecast_metrics.py, code/m5m6_decision_engine.py, code/agent_prompts.md, docs/WIKI_PAGE.md. After the user pastes forecast_metrics + decision_summary + top route cards, build the HTML page (aggregates only) and fill REPORT_DRAFT.md.

## Decisions already made (don't reopen without new evidence)
- Target = boardings (sum CKI) per Route × 15-min bin, 15 Dec 2025. Horizons h1 = 15 min, h4 = 60 min.
- Temporal holdout: train bin15 ≤ 55 (before 14:00), test ≥ 56. No clock-hour feature. Lags ≥ h only.
- Baseline = naive persistence (lag h). Report MAE, RMSE, MAPE (actual ≥ 5), WAPE, skill vs naive, by period.
- Capacity = Fleet `Total`. demand_pressure is a proxy, not load factor.
- LLM sees aggregated tables only. NOL_ID, Driver_id and device_id_hex are dropped in Z1.
- GTFS 2026 = planned context / labelled scenario only.
