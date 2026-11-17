# Report draft: Team 7 "DemandPulse" (RTA Future Move)

Status: skeleton. Only items marked VERIFIED come from the user's Dataiku evidence (docs/PROGRESS.md).
Everything marked PENDING must be filled from real results. Never write a number that is not VERIFIED.

## 1. Decision statement (fill at the end)
What RTA should change / why / measurable difference: PENDING (from M5-M6 results).

## 2. Data and period
- Nol card taps: actual, one day, Mon 15 Dec 2025. VERIFIED: 1,056,343 rows; 544,583 check-ins (CKI) and 511,760 check-outs (CKO); one date.
- Running time (AVL): actual, same day. VERIFIED: 259,435 trip-stop rows.
- Fleet list: 3,264 rows. VERIFIED.
- GTFS: planned 11 Sep-31 Dec 2026. Not compared with 2025 as the same period (scenario only, if used).

## 3. Data quality and preparation (VERIFIED)
- Personal data: NOL_ID and Driver_id excluded from all analytical outputs; source datasets unchanged.
- Nol: 106 taps (0.01%) with blank Route, flagged (route_dq_flag) and excluded from route-level demand; all 106 were check-ins.
- Runtime: delay (Diff_in_seconds) is signed (min -2,945 s, median +117 s); 11,098 rows (4.3%) have no delay value: flagged, excluded from delay statistics.
- Fleet: duplicate Body_number (3100); mixed spellings of Standard; 5 non-bus vehicles; 124 empty types; 619 vehicles (19%) with capacity 0 treated as missing (flagged). User-reported fix: fleet_capacity_lookup, one row per bus.
- Time slots: 96 fifteen-minute slots, all present. Tap volume peaks around 07:45-09:00 and 18:15-19:00 (one day, descriptive).
- Route x slot table: 13,837 rows, totals reconcile to source (1,056,237 taps after removing 106).
- Forecast scope: 117 of 200 routes (>= 3,000 taps/day) covering 88.5% of boardings; route x slot grid 11,232 rows (117 x 96), 20.6% of cells are true zeros.
- Route table: 200 routes, 6 columns; counts match the data-quality check route by route (sampled).

## 4. Method (Flow Zones)
Ingest + PII guard -> Demand aggregates -> Features -> Forecast (visual ML) -> Evaluation -> Decision rules -> AI agents. PENDING: final recipe list and screenshots.

## 5. Forecast results (VERIFIED from forecast_metrics, test = 14:00-23:59 of 15 Dec 2025, 4,680 route-slot rows, never seen in training)
Models: Ridge regression chosen for both horizons by lowest test MAE (h1: Ridge 16.717 vs RF 16.964 vs XGBoost 17.446; h4: Ridge 21.388 vs RF 21.958 vs XGBoost 22.065). Baseline = last value known at forecast time (15 or 60 min earlier). Predictions clipped at 0.
| Horizon | Segment | n | Model MAE | Baseline MAE | MAE gain | Model RMSE | Baseline RMSE | RMSE gain | Model MAPE% | Baseline MAPE% | Model WAPE% | Baseline WAPE% |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 15 min | ALL | 4680 | 16.680 | 20.409 | +18.3% | 23.794 | 29.491 | +19.3% | 47.45 | 56.45 | 30.89 | 37.80 |
| 15 min | PM_PEAK | 1872 | 20.959 | 26.042 | +19.5% | 28.664 | 35.862 | +20.1% | 38.43 | 47.22 | 27.46 | 34.12 |
| 15 min | OFF_PEAK | 2808 | 13.827 | 16.654 | +17.0% | 19.895 | 24.334 | +18.2% | 54.14 | 63.28 | 35.36 | 42.59 |
| 60 min | ALL | 4680 | 21.334 | 22.731 | +6.1% | 30.533 | 33.319 | +8.4% | 60.68 | 60.93 | 39.51 | 42.09 |
| 60 min | PM_PEAK | 1872 | 26.661 | 28.131 | +5.2% | 37.528 | 38.872 | +3.5% | 43.66 | 46.45 | 34.93 | 36.85 |
| 60 min | OFF_PEAK | 2808 | 17.783 | 19.130 | +7.0% | 24.797 | 29.033 | +14.6% | 73.29 | 71.65 | 45.47 | 48.92 |
Reading: model beats the baseline on MAE, RMSE and WAPE in all six cells; MAPE better in 5 of 6 (worse off-peak at 60 min: MAPE is unstable at low counts). The 15-min gain is clear (about 17-20%); the 60-min gain is modest (about 5-7% MAE). Errors remain large (WAPE 31% at 15 min, 39.5% at 60 min; mean 54 boardings per route-slot). Test half contains the evening peak only; morning peak was in training. A first training run with a random split and leaky features (alightings, slot15, period, Route) gave MAE 11.4-12.6; it was discarded (leakage).

## 6. Operational indicators (VERIFIED from decision_summary / route_evidence_card)
Rule parameters (assumptions): high pressure >= 1.0 boardings per offered place per hour; under-used <= 0.25 (at least 2 trips); late = more than 5 min; unreliable = >= 30% of >= 20 timed departures late. Demand pressure = card-tap boardings / seats offered (sum of vehicle capacity over distinct trips per route-hour); a screening proxy, not on-board load.
- 3,727 route-hours with demand; 3,001 (80.5%) matched to running-time data; 166 of 200 routes matched (34 routes cannot be judged). 253,152 running-time events used; 6,283 (hour outside 0-23) excluded. Fleet match 99.7%, valid capacity 99.7%.
- High pressure: 28 route-hours, carrying 1.1% of boardings. Under-used: 1,262 route-hours (42% of matched). Unreliable: 761 route-hours (25%).
- Top routes by boardings: F24 12,201; F15 11,405; 88 9,661; 28 9,400; F23 8,983; F22 8,728; 13D 8,462; C01 8,345 (only top route above 1.0: max pressure 1.87, 12 under-used hours, 9 unreliable hours). Median delays above 130 s on X13 (204), 88 (168.5), F46 (164), C01 (162), C10 (139), 310 (135).

Crowding / under-use / reliability flags per route-hour. Demand pressure is a proxy (boardings per offered place), not on-board load.

## 7. Cost-neutral bus-swap scenario (VERIFIED outputs; WHAT-IF, not measured)
Same buses, same trips, same hour; a large bus (capacity >= 100) moves from an under-used route-hour to a high-pressure route-hour with a smaller bus; donor must stay <= 0.50 after. Result: 18 swaps, 792 places reallocated, 0 trips removed; 13 of the 28 high-pressure route-hours drop below 1.0 (15 remain).

## 7b. Congestion, alternatives and operations monitor (VERIFIED from ops_summary / segment_hotspots / alt_route_candidates)
Method: extra seconds between consecutive stops vs schedule (running times) combined with card-tap boardings at the segment start; stop coordinates from the GTFS stops file used only to place stops (98.4% of 2,607 stops, 98.6% of taps matched). 246,343 stop-to-stop segment events analysed (0.76% skipped); 4,620 route-segment-hours with >= 5 trips; 388 (8.4%) run >= 30 s over schedule; median speed proxy 20.3 km/h (straight-line).
Top corridor: route F27 Max Metro Bus Stop Landside 2 -> Satwa, Masjid 1, 17:00-22:00, up to 509 s over schedule (scheduled 7-8 min, actual 15-16 min), 259-447 boardings per hour at the start stop. Morning corridor near E311 (Rashidiya) 82-97 s over at 07-08h. Same-stop-pair alternatives are rare (1 of top 30: route F09 for F27 at 18:00). Limits: traffic vs timetable not separable; speeds are straight-line proxies; Nol includes non-bus stops.
Operations monitor: webapp with two dashboards (Control room, Planning), action queue requiring two human confirmations per action, rule-based agents, end-of-day report.

## 8. AI agents: PENDING (summary data only; they explain, they do not calculate)

## 9. Limitations (state plainly)
1. One observed day: intraday forecasts only; no day-of-week, seasonal or event effects.
2. Test set = later hours of the same day (within-day generalisation only).
3. Boardings per route-slot are not on-board load; no origin-destination.
4. Capacity depends on unverified standing figures and fleet join coverage.
5. Scenario impacts are rule-based what-ifs, not measured outcomes.
6. LLM agents never produce numbers.
7. Source screenshots held outside the platform (rule 8 of the guide): confirm with a mentor and delete after the event.

## 10. Recommendations and next steps: PENDING
