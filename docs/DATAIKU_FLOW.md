# Dataiku Flow Design — Team 7 "DemandPulse" bus copilot

Status: DESIGN ONLY. Nothing below has been built or run yet.

## 1. The solution in one paragraph
Forecast route-level bus boardings 15 and 60 minutes ahead from the actual Nol taps of
15 Dec 2025. Combine the forecast with the actual schedule, delays (Running_time) and vehicle
capacity (Fleet_List) to score every route-hour for **crowding risk, under-use and unreliability**.
A rule engine (all numbers computed in recipes) turns the scores into concrete actions: upsize or
downsize vehicles, add a standby trip, or add recovery time, each with a quantified scenario impact.
A chain of LLM "agents" (Demand, Reliability, Fleet, Guardrail/Orchestrator) **explains and checks**
those actions against RTA rules. The agents never compute numbers.
Answers the brief: *what RTA should change, why, and the measurable difference.*

Why this one: it hits every rubric line (forecast metrics vs baseline, horizons and peaks, visual ML,
explainability, decisions) and stays honest with one observed day. It also needs only datasets
whose schema we have verified.

## 2. Architecture (Flow Zones)
```
Z1 INGEST + PII GUARD     nol / runtime / fleet --Prepare--> *_clean   (drop NOL_ID, Driver_id)
        |
Z2 DEMAND                 nol_clean --Group--> route x 15-min boardings --grid+fill 0--> demand_full
Z3 SUPPLY + RELIABILITY   runtime_clean + fleet_clean --Join/Group--> supply_15min, capacity_hour, reliability_hour
        |
Z4 FEATURES               demand_full + supply_15min --Join--> Window (lags) --Prepare--> Split (time)
Z5 FORECAST (Visual ML)   model_h1 (15 min ahead), model_h4 (60 min ahead) --Score--> scored_test_h1/h4
Z6 EVALUATION             errors vs naive baseline --Stack/Group--> forecast_metrics (MAE, RMSE, MAPE, WAPE, by peak)
        |
Z7 DECISION ENGINE        demand (actual + forecast) + capacity + reliability --Prepare rules--> route_hour_decisions
                          --> route_evidence_card, impact_scenarios
Z8 AI AGENTS (LLM Mesh)   evidence_card (aggregated, no PII) --> agent_demand | agent_reliability | agent_fleet
                          --Join--> agent_orchestrator_guardrail --> recommendations_final
Z9 NETWORK CONTEXT (stretch, labelled PLANNED 2026)  GTFS Monday plan, bus-metro feeder stops, communities
OUTPUTS                   Dashboard + Wiki + HTML webapp (+ deck built from aggregated results)
```

## 3. Recipe-by-recipe
Names follow guide rule 16. "Validate" = what to look at before moving on.

### Z1 Ingest + PII guard
| # | Recipe | Input → Output | Key steps | Validate |
|---|---|---|---|---|
| 1 | Prepare `prep_nol` | nol_card_details_15-Dec-2025 → `nol_taps_clean` | Delete NOL_ID, device_id_hex, Amount. Set Route meaning = Text. Flag, then remove empty Route. Split Transaction_Time on ":" → hh, mm. Formula `minute_of_day = numval("hh")*60 + numval("mm")`, `bin15 = floor(minute_of_day/15)`, `hour = numval("hh")`. Regex extract body number from Body_EVD_ID (`B(\d+)_EVD`). | PII columns gone; % empty Route noted; bin15 in 0–95 |
| 2 | Prepare `prep_runtime` | Running_time_15-Dec-2025 → `runtime_events_clean` | Delete Driver_id. Split Sched_Dep / Act_Dep on ":" → seconds. `delay_sec = act_dep_sec - sched_dep_sec` (if < -43200 add 86400; midnight wrap). `sched_bin15 = floor(sched_dep_sec/900)`, `sched_hour`. Flags `is_late_5min = delay_sec > 300`, `is_early_1min = delay_sec < -60`. | delay_sec matches Diff_in_seconds on sample; check sign |
| 3 | Prepare `prep_fleet` | Fleet_List → `fleet_capacity_clean` | Rename Model Year → model_year. `capacity = numval("Total")`. Flag `standing_unverified`. | Bus_Type values; capacity > 0 |

### Z2 Demand
| 4 | Group `grp_demand_route_15min` | nol_taps_clean → `demand_route_15min` | Keys Route, bin15. Aggregates: sum(CKI) → boardings, sum(CKO) → alightings. | totals = sum of CKI |
| 5 | Group ×2 | demand_route_15min → `route_list`; nol_taps_clean → `bin_list` | Group on Route only, and on bin15 only | counts sensible |
| 6 | Join (Cross join) `join_route_bin_grid` | route_list × bin_list → `route_bin_grid` | Cartesian product. Fallback: Python recipe in BUILD_RUNBOOK §Fallback | rows = routes × bins |
| 7 | Join (left) + Prepare | route_bin_grid ⟕ demand_route_15min on Route, bin15 → `demand_route_15min_full` | Fill empty boardings/alightings with 0 | no gaps per route |

### Z3 Supply + reliability (actual 2025)
| 8 | Join (left) `join_runtime_fleet` | runtime_events_clean ⟕ fleet_capacity_clean on Body = Body_number → `runtime_with_fleet` | keep capacity, Bus_Type | **match rate** (empty capacity share) |
| 9 | Group `grp_supply_route_15min` | runtime_events_clean → `supply_route_15min` | Keys Route, sched_bin15. count rows → sched_stop_events, distinct Trip_ID → active_trips | planned, known in advance |
| 10 | Group ×2 `grp_capacity_route_hour` | runtime_with_fleet → by Route, sched_hour, Trip_ID (first capacity, first Bus_Type) → by Route, sched_hour: count trips, sum capacity → `capacity_route_hour` | | capacity per trip ≈ 33–115 |
| 11 | Group `grp_reliability_route_hour` | runtime_events_clean → `reliability_route_hour` | avg/stddev/max delay_sec, avg is_late_5min → share_late, count | outliers reviewed |

### Z4 Features (leakage-safe)
| 12 | Join (left) | demand_route_15min_full ⟕ supply_route_15min on Route=Route, bin15=sched_bin15 → `demand_supply_15min` | fill 0 | |
| 13 | Window `win_demand_lags` | → `demand_features_15min` | Partition Route, order bin15. Lag boardings offsets 1–8; lag alightings 1–4 | first rows per route have empty lags |
| 14 | Prepare `prep_features` | → `demand_features_ready` | `ma4_h1 = mean(lag1..lag4)`, `ma4_h4 = mean(lag4..lag7)`, `route_prefix` = leading letters of Route, baselines `naive_h1 = lag1`, `naive_h4 = lag4`. Remove rows with empty lag8. Period label (AM 06–09, PM 16–20: assumption). | |
| 15 | Split `split_time` | → `features_train` (bin15 ≤ 55, before 14:00), `features_test` (bin15 ≥ 56) | temporal holdout | test includes PM peak |

Leakage rules: no same-bin alightings, delay or actual-time features. No clock-hour feature, because
the test hours never appear in training (trees cannot extrapolate). For horizon h, only lags ≥ h.
`active_trips` / `sched_stop_events` in the target bin are allowed: they come from the schedule.
(Caveat: runtime only lists trips that ran.)

### Z5 Forecast (Visual ML, Lab → AutoML prediction, regression)
| 16 | `model_boardings_h1` | target boardings; train/test = explicit extracts features_train / features_test | Features: lag1–8, alight lag1–4, ma4_h1, ma4_h4, active_trips, sched_stop_events, Route (categorical), route_prefix. Algos: LightGBM or XGBoost, Random Forest, Ridge. Optimise MAE. | compare algos; keep best; variable importance + Shapley |
| 17 | `model_boardings_h4` | same, **reject lag1–3, alight lag1–3, ma4_h1** | | |
| 18 | Score ×2 | features_test → `scored_test_h1`, `scored_test_h4` | | |

### Z6 Evaluation
| 19 | Prepare ×2 | scored → `errors_h1/h4` | `horizon`, `abs_err = abs(prediction-boardings)`, `sq_err`, `abs_err_naive`, `sq_err_naive`, `ape` only if boardings ≥ 5 | |
| 20 | Stack → Group → Prepare | → `forecast_metrics` | by horizon (and horizon × period): MAE, RMSE = sqrt(avg sq_err), MAPE(≥5), WAPE = sum abs_err / sum boardings, `skill_vs_naive = 1 - MAE/MAE_naive` | **this is the rubric 5 table** |

### Z7 Decision engine
| 21 | Group + Join | demand_route_15min_full (actual, full day) → route-hour boardings; join capacity_route_hour, reliability_route_hour → `route_hour_evidence` | | |
| 22 | Prepare `prep_decision_rules` | → `route_hour_decisions` | `demand_pressure = boardings / capacity_offered`. Rules (thresholds = project variables, labelled assumptions): ≥ 0.8 → CROWDING_RISK; ≤ 0.2 → UNDER_USED; share_late ≥ 0.3 → UNRELIABLE. Action map: crowding → upsize vehicle or add standby trip; under-used → downsize vehicle and **keep frequency** (equity); unreliable → recovery time or headway control. | demand_pressure is a proxy: boardings per offered place per hour, not on-board load |
| 23 | Group + Prepare | → `route_evidence_card` (1 row/route), `impact_scenarios` | Swap scenario: move large vehicles from UNDER_USED to CROWDING_RISK route-hours (same fleet, cost-neutral). Count route-hours resolved and seats reallocated. | label: SCENARIO |
| 24 | (stretch) Prepare on scored_test_h1 | → `early_warning_alerts` | predicted pressure ≥ threshold 15/60 min ahead; hit rate vs naive | |

### Z8 AI agents (LLM Mesh; inputs are aggregated tables only)
| 25 | Prepare + Top N `llm_input_guard` | route_evidence_card → `llm_evidence_topN` | keep only aggregated columns; top 15 crowding + top 5 unreliable routes | no IDs except Route |
| 26 | Prompt recipe ×3 | llm_evidence_topN → `agent_demand_out`, `agent_reliability_out`, `agent_fleet_out` | role prompts; "use only the numbers given" | |
| 27 | Join + Prompt recipe `agent_orchestrator_guardrail` | → `recommendations_final` | combine the 3 views. Check guardrails (no fare change, no infrastructure, equity, driver rest, capacity limits). Output: change / why / measurable impact / risk / confidence | spot-check vs numbers |
| 28 | (optional) Visual Agent | tool = Dataset Lookup on route_evidence_card | interactive Q&A for the demo | only if the instance has Agents |

### Z9 Network context (stretch, PLANNED 2026, labelled)
- GTFS Monday plan: stop_times ⋈ trips ⋈ routes (route_type = 3) ⋈ calendar (monday = 1) → planned trips by route and hour.
  Shown **beside** the 2025 evidence as an assumption scenario. Never as the same period.
- Feeder flag: transfers where a bus stop (6-digit) links to a metro stop (route_type 1) → `feeder_stops`.
- Communities: Python recipe parses the Polygon JSON to WKT, then Geo join with stops → demand by community.

## 4. Deliverable mapping
| Rubric | Where in Flow |
|---|---|
| 1 Practical application | Z7 decisions + Z8 recommendations_final |
| 2 Documentation/visuals | Flow Zones, recipe descriptions, Wiki, Dashboard, HTML page |
| 3 Innovation | horizon-specific models + multi-agent explain-and-guardrail layer + cost-neutral swap scenario |
| 4 AI model | Visual ML algo comparison, explicit temporal holdout, Shapley/importance |
| 5 Forecast accuracy | forecast_metrics: MAE/RMSE/MAPE/WAPE, skill vs naive, h1 vs h4, peak vs off-peak |
