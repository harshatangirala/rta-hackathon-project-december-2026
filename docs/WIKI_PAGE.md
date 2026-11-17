# DemandPulse: Team 7 (paste into the Dataiku project Wiki)

## Goal
Help RTA match bus capacity to demand: forecast route boardings 15 and 60 minutes ahead, flag route-hours
with high demand pressure, under-use or unreliable running, and test a cost-neutral bus-swap scenario.

## Data and period
- Nol taps and running times are ACTUAL observations for one day, Monday 15 Dec 2025.
- Fleet list gives vehicle type and capacity.
- GTFS is the PLANNED Sep-Dec 2026 timetable and is not compared with 2025 as the same period.

## Privacy
NOL_ID (card) and Driver_id are excluded from every analytical dataset. Source datasets are unchanged.
LLM agents only see route-level summary tables.

## Flow zones (left to right)
1. Source Data: the four raw datasets (Nol card taps, running times, fleet list, stops). Unchanged.
2. Data Cleaning & Quality: Prepare recipes drop NOL_ID and Driver_id, fix types, and produce the data-quality counts.
3. Demand Aggregation & Preparation: boardings per route and 15-minute slot, a complete route x slot grid, zeros filled.
4. Forecasting & Evaluation: lag features, time-ordered split, Ridge / Random forest / XGBoost per horizon, scored test sets, forecast_metrics.
5. Fleet & Route Operations: offered seats per route-hour, demand pressure, flags, evidence card, swap scenario.
6. Crowding & Operational Reporting: stop crowding, congestion hotspots, alternative routes, daily report, ops summary.
7. AI Decision Support: case file, specialist and coordinator Prompt recipes, number checker (agent_checks).

## AI agents
Two specialists (congestion/reliability, supply-demand) and one coordinator write a 4-line action card per case
(CHANGE, WHY, MEASURABLE, GUARDRAIL CHECK) from summary facts only. A check recipe verifies that every number appears
in the supplied facts and that no forbidden advice appears. Only passing cards are shown in the webapp; otherwise the
rule-based text is shown. The check does not prove the reasoning is right: every action needs human approval.

## Outputs
DemandPulse Ops webapp (live, reads the datasets): map and hotspots, actions and agents, supply-demand gaps,
passenger advisory, forecast and method. DemandPulse Team7 webapp: planning snapshot with the swap scenario.

## Key assumptions
- Forecast scope: 117 routes with >= 3,000 taps that day (88.5% of boardings). Selected on whole-day volume (disclosed).
- Train = 02:00-13:59, test = 14:00-23:59 (time holdout). Features = past slots only; no clock features.
- Baseline = last value known at forecast time (15 or 60 minutes earlier).
- Peak windows: AM 06:00-08:59, PM 16:00-19:59 (test contains PM only).
- Demand pressure = boardings / offered places per hour (proxy, not on-board load).
- Thresholds: under-used <= 0.25, high pressure >= 1.0, late > 5 min, unreliable >= 30% late.
- Fleet capacity 0 treated as unknown and imputed with the route median; non-buses excluded.

## Limitations
One observed day (no weekly/seasonal/event effects); scenario results are rule-based what-ifs;
crowding needs on-board load (APC) confirmation; agents explain, never compute.
