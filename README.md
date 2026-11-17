# DemandPulse: RTA Future Move Hackathon (Team 7), December 2026

Matching Dubai bus capacity to passenger demand, built end to end in Dataiku DSS 15.2 on one observed day of Nol card taps and bus running times (Monday 15 Dec 2025).

> Hackathon prototype. Not an official RTA publication. No raw data is stored in this repository.

## Headline results (one observed day)

- **Forecast:** 15-minute boardings forecast has 18.3% lower MAE than the last-known-value baseline (60 minutes: 6.1%). Ridge regression, time-ordered split, leakage-safe features.
- **Capacity:** 28 route-hours with more taps than seats, 1,262 mostly empty route-hours, 761 unreliable route-hours.
- **Bus-swap what-if:** 18 swaps move 792 seats and bring 13 of the 28 crowded route-hours below 1.0 with 0 trips removed.
- **Congestion:** 388 of 4,620 route-segment-hours run 30 s or more over schedule; route F27 (Max Metro Bus Stop Landside 2 to Satwa, Masjid 1) dominates.
- **AI agents:** two specialists and a coordinator write action cards; an automatic checker verified all 24 AI answers (numbers, forbidden advice, format). The check proves numbers, not reasoning.

## Where to start

| Folder / file | What it is |
|---|---|
| `reports/DemandPulse_Technical_Report.md` | Full technical report |
| `reports/DemandPulse_Explained_Simply.md` | Plain-language explainer with glossary and likely judge questions |
| `deck/` | Source of the 17-slide presentation (one HTML file per slide, shared CSS, speaker notes) |
| `code/` | Python recipes, the two webapps (HTML + Python backend) and the agent prompts |
| `docs/` | Build log, Flow design, evidence and schema, validation register, runbook |

## Documentation index

| File | Purpose |
|---|---|
| docs/HANDOFF.md | State of the project at hand-off |
| docs/PROGRESS.md | Authoritative log of verified numbers and decisions |
| docs/MILESTONES.md | Build milestones M1 to M9 |
| docs/VALIDATION_AND_LIMITATIONS.md | Claim register (CONFIRMED / INFERRED / ASSUMED / BLOCKED) and limitations |
| docs/EVIDENCE_AND_SCHEMA.md | Datasets, fields, join keys, period rules |
| docs/DATAIKU_FLOW.md | Architecture and recipe-by-recipe design |
| docs/BUILD_RUNBOOK.md | Step-by-step build guide |
| docs/REPORT_DRAFT.md | Verified-facts draft behind the report |
| docs/WIKI_PAGE.md | Text for the project Wiki |
| AGENTS.md / CLAUDE.md | Working rules used by the coding assistants |

## Rules the project follows

- Nol and running times are actual 2025 data for one day; the 2026 GTFS stops file is planned data and is used only to place stops on a map. They are never compared as one period.
- Card and driver identifiers are dropped in the first cleaning step, before any analysis or language model.
- No fare changes, no trip or frequency cuts, no new infrastructure; driver rest and vehicle types respected; two human confirmations before any action is approved.
- Forecasts are intraday (15 and 60 minutes). No weekly, seasonal or event claims.

## Honest limits

One observed day. Demand pressure (boardings per offered seat) is a screening proxy, not on-board load. Scenario results are what-ifs. The forecast is validated separately and does not yet feed the decision recipe. See the technical report for the full list.

## Using the code

The Python files are Dataiku recipes: they read and write Dataiku datasets and need a Dataiku project with the matching Flow. The webapp HTML and Python files are pasted into a Dataiku Standard webapp. The data is not included.
