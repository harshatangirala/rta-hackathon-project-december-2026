# Validation register and limitations

Labels: **CONFIRMED** (seen in data or docs) · **INFERRED** (strongly implied, not proven)
· **ASSUMED** (design choice, must be stated) · **BLOCKED** (cannot be done with available data)
· **REQUIRES DSS VALIDATION** (depends on the live instance).
Update a row whenever a milestone produces evidence. Last update: 2026-11-16, session 2, before M1 evidence.

## Claim register
| ID | Claim | Status | Evidence / how it gets resolved |
|---|---|---|---|
| V01 | Nol and Runtime cover only 15 Dec 2025 | Nol CONFIRMED (single date); Runtime CONFIRMED (single date 15-DEC-2025, 259,435 rows) | dataset names + previews → M1 steps 1.5 and 1.7 |
| V02 | GTFS = planned services 11 Sep–31 Dec 2026 | CONFIRMED | asset description + calendar preview |
| V03 | Nol grain = one row per card tap | INFERRED | columns → M1 1.5 |
| V04 | CKI=1 boarding, CKO=1 alighting | INFERRED (flags are mutually exclusive: CONFIRMED) | 544,583 CKI vs 511,760 CKO rows |
| V05 | Some Nol rows have empty Route | CONFIRMED (extent unknown) | preview → M1 1.6 |
| V06 | Red "invalid" Route cells are a meaning artifact (locked Decimal), not bad data | CONFIRMED | storage = string in preview |
| V07 | Diff_in_seconds = Act_Dep − Sched_Dep | INFERRED | holds on about 17 preview rows → recompute in M2 |
| V08 | Early departures are negative in Diff_in_seconds | CONFIRMED (signed) | min -2,945 s, median +117 s (Analyze, whole data) |
| V09 | Fleet has one row per Body_number | **FALSE**: 3100 duplicated | `fleet_capacity_lookup` = Group by Body_number, Max(Total) (user-reported 3,263 rows); verify no row growth in M5 join |
| V10 | Runtime.Body = Fleet.Body_number | ASSUMED | match rate in M5 |
| V11 | Digits of Nol Body_EVD_ID = Fleet.Body_number | ASSUMED | match rate in M5 (optional use) |
| V12 | Fleet `Total` = usable vehicle capacity | ASSUMED; Total=0 in 19% of rows → missing; Bus_Type includes non-buses (CRANE, FORKLIFT, PICKUP, TANKER) | Standing is "not verified"; Seats sometimes equals Total |
| V13 | Nol `Amount` meaning | BLOCKED | undocumented → not used |
| V14 | Runtime lists only trips that actually ran | ASSUMED | affects the "scheduled supply" feature (small leakage risk, disclosed) |
| V15 | Forecasts beyond the same day (multi-day, weekly, seasonal, events) | BLOCKED | one observed day |
| V16 | Peak windows AM 06–09 (slots 24-35), PM 16–20 (slots 64-79) | ASSUMED | labelling choice for reporting only. Test half (slots 56-95) contains only the PM peak; AM peak is training-only |
| V17 | Rule thresholds (pressure 0.8 / 0.2, late share 0.3) | ASSUMED | tunable, shown as parameters |
| V18 | demand_pressure is NOT a load factor | CONFIRMED (by construction) | boardings ÷ offered places per hour |
| V19 | Prompt recipe + LLM connection available | REQUIRES DSS VALIDATION | DSS 15.2 includes Prompt recipes (INFERRED from Help banner); whether an LLM connection is configured on this instance gets checked in M7 |
| V20 | Agents feature available | REQUIRES DSS VALIDATION | DSS 15.2 ships agents; whether this instance has them enabled and has an LLM gets checked in M7 |
| V21 | Join "Cross join" and Window "Lag" available | INFERRED (long-standing visual recipes; DSS 15.2) | M3/M4; Python fallback exists |
| V22 | Catalog datasets can be imported/shared into the team project | CONFIRMED | M1: 3 datasets appear in Flow with `DATA.` prefix (linked, not copied) |
| V23 | Electric vs diesel analysis | BLOCKED | no propulsion field in Fleet_List |
| V24 | Community polygons usable for a geo join | REQUIRES DSS VALIDATION | Polygon JSON must be parsed; stretch only |
| V26 | 11,098 Runtime rows (4.3%) have empty Diff_in_seconds; cause unknown | REQUIRES DSS VALIDATION | Act_Dep never empty; only 135 rows lack Sched_Dep/Difference; >=10,963 rows have Difference but no Diff_in_seconds. Exclude from delay stats, keep for supply counts. M5: check missing share by route/hour; consider recomputing delay = Act_Dep - Sched_Dep only after it matches Diff_in_seconds on overlapping rows |
| V28 | Customer trip-planner chatbot allowed | **CONFLICTS with guide DO #19**; ask a mentor; not built by default | decision pending |
| V29 | Nol taps measure road congestion | **FALSE**: they measure passenger crowding at stops; road congestion comes from running-time delay added between stops | design note |
| V30 | Stop coordinates (2026 GTFS) valid for 2025 stops | ASSUMED (location lookup only) | stops_with_coords_pct and taps_with_coords_pct in ops_summary |
| V31 | Straight-line speed proxy = real road speed | NOT CLAIMED: relative comparison only | segment speeds |
| V32 | Alternative routes = same stop pair, same hour, spare seats, less delay | ASSUMED candidates, not true re-routing | alt_route_candidates |
| V33 | Daily report is sent automatically | REQUIRES DSS VALIDATION (Scenario + messaging channel) | ask admin/mentor |
| V34 | Nol taps are bus-only | **FALSE/UNCERTAIN**: stops named 'Marine Transport Station' appear in Nol; routes like TR1/FR5 may be tram/ferry | state as limitation; check route list |
| V35 | Time over schedule = traffic | NOT CLAIMED: confounded with timetable error | dashboards say 'traffic or timetable' |
| V36 | Webapp live backend works on this DSS | REQUIRES DSS VALIDATION (first load) | fallback message + saved forecast values |
| V25 | Personal data deleted | **NOT CLAIMED** | we exclude NOL_ID/Driver_id from our outputs; the source catalog is unchanged |

## Known limitations (state these in the deck)
1. One observed day: forecasts are intraday 15/60-min nowcasts. There is no day-of-week, seasonal or event signal.
2. Temporal holdout = the afternoon/evening of the same day. That tests within-day generalisation only.
3. Boardings per route-slot are not on-board load. There is no trip-level OD, so crowding is a proxy.
4. Capacity depends on unverified standing figures and on fleet join coverage.
5. 2026 GTFS can only appear as a labelled assumption scenario, never as a comparison with 2025.
6. Scenario impacts are deterministic what-ifs under stated rules, not measured outcomes.
7. Model tuning uses cross-validation inside the training half, which is not time-ordered; only the final test half is a true time holdout.
8. LLM agents explain and check. They do not compute; every number comes from a recipe.
