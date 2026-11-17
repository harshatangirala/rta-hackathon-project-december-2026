# Milestone guide (authoritative build order from session 2)

This file supersedes the time-boxed order in BUILD_RUNBOOK.md. Milestones run one at a time;
the next one starts only after the user pastes the evidence for the previous one.
Status labels: CONFIRMED · INFERRED · ASSUMED · BLOCKED · REQUIRES DSS VALIDATION.
**Paste aggregates only. Never paste raw rows, NOL_ID or Driver_id values.**

| # | Milestone | Status |
|---|---|---|
| M1 | Add 3 catalog datasets + data-quality inspection | COMPLETE (evidence in PROGRESS.md) |
| M2 | Cleaning recipes (exclude PII, Route → Text, DQ flag) | COMPLETE (C user-reported) |
| M3 | Route-level and route × 15-min aggregates | COMPLETE |
| M4 | Baseline + 15/60-min models, MAE/RMSE/MAPE/WAPE, time split | IN PROGRESS: A, B, C done; D issued (E pending) |
| M5 | Crowding / under-use / reliability indicators | READY: Python recipe code/m5m6_decision_engine.py (with M6) |
| M6 | Cost-neutral bus-swap scenario (deterministic) | READY: same recipe as M5 |
| M7 | 2 specialist agents + 1 coordinator (or labelled deterministic fallback) | READY: code/agent_prompts.md; fallback column rule_based_commentary |
| M8 | Minimal webapp | not started |
| M9 | Demo sequence + slide outline | not started |

---

**Instance UI notes (CONFIRMED from screenshot):**
- Dataiku Cloud, Design Node. The Flow toolbar has APPLY A VIEW, search, SELECT ALL ITEMS, **COBUILD**, **+ ADD ITEM**.
- The right-side panel collapses behind a "←" arrow at the top-right.
- Shared datasets are black tiles named `DATA.<name>`.
- The user is a first-time Dataiku user and needs click-by-click detail ("single-click selects, double-click opens").

## M1 — Add the three catalog datasets and inspect them
Goal: the 3 raw datasets are in the project Flow and the facts below are recorded. **No cleaning yet.**
Time box: about 20 min. GTFS and Communities are deliberately NOT imported yet (2026 plan, later use).

### Step 1.0 Record the DSS version
1. **Menu:** the **?** (Help) icon, top-right → **About Dataiku DSS**. Fallback: the user avatar menu, or ask a mentor.
2. **Object:** none.  3. **In/Out:** none.  4. **Settings:** none.  5. **Grain:** n/a.
6. **Verify:** the version number is visible (e.g. 12.x / 13.x / 14.x).
7. **Paste back:** the exact version string.
8. **Why:** Prompt recipes, Agents and some Join/Window options depend on version, so this decides M4 and M7 options.

### Step 1.1 Open or create the project
1. **Menu:** Dataiku logo (top-left) → **Projects**. If organisers created a Team 7 project, open it.
   Otherwise **+ New project → Blank project**.
2. **Object:** project `RTA_T7_DemandPulse` (only if you create one).
3. **In/Out:** none.  4. **Settings:** none.  5. **Grain:** n/a.
6. **Verify:** the project name shows top-left. Confirm with teammates that only ONE team project exists.
7. **Paste back:** project name + project key (in the browser URL `.../projects/<KEY>/...`).
8. **Fallback:** if you cannot create projects, use the organiser-assigned project and ask a mentor for access.

### Step 1.2 Add the three catalog datasets
1. **Menu:** top bar **Catalog** (or the 9-dot menu → **Data Collections**) → collection
   *RTA Future Move Hackathon* → click `nol_card_details_15-Dec-2025` → button **Import** /
   **Use in project** / **Add to project** (the label varies by version) → choose your project → confirm.
   Repeat for `Running_time_15-Dec-2025` and `Fleet_List`.
2. **Object:** none new. The datasets keep their names and may display as `DATA.<name>` (source project key `DATA`).
3. **In:** catalog datasets in project `DATA`. **Out:** linked (shared) datasets in your Flow.
4. **Settings:** prefer *share/link*. If the only option is *copy*, accept it: copying does not alter the source,
   but it takes time and storage. **Never edit the source datasets' settings or schema.**
5. **Expected grain:**
   - Nol: one row per card tap. INFERRED: each row has one CKI/CKO flag.
   - Runtime: one row per trip × stop event. INFERRED from Trip_ID + Stop_Seq.
   - Fleet: one row per vehicle. ASSUMED until Step 1.4.
6. **Verify:** all 3 appear in the Flow (a shared/link icon is expected). Each opens in **Explore** with the
   columns listed in EVIDENCE_AND_SCHEMA §4.1–4.3.
7. **Paste back:** the exact dataset names as displayed in your Flow, and whether they show as shared or copied.
8. **Fallback:** if there is no import button, check whether the datasets already appear in your Flow
   (organisers may have pre-shared them). Otherwise ask a mentor to share them from project `DATA`.
   Status of this step: REQUIRES DSS VALIDATION.

### Step 1.3 Create the first two Flow Zones
1. **Menu:** **Flow** → **+ Zone** (top-right of the Flow).
2. **Objects:** zones `Z0 Raw catalog inputs (read-only)` and `Z1 Data quality checks`.
3. **In/Out:** none.  4. **Settings:** move the 3 datasets into Z0 (right-click dataset → **Move to a flow zone**).
5. **Grain:** n/a.  6. **Verify:** the 3 datasets sit inside Z0.  7. **Paste back:** "zones done" (or "skipped").
8. **Fallback:** select a dataset → right panel → **Move to a flow zone → Create a new zone**.
   If zones are unavailable, skip them: the `dq_` name prefix below still groups the outputs.

### Step 1.4 Fleet profile (small dataset; Analyze is enough)
1. **Menu:** open `Fleet_List` → **Explore** tab. Click column header `Body_number` → **Analyze** →
   set the sample selector to **Whole data** → **Compute**. Repeat for `Bus_Type` and `Total`.
2. **Object:** none.  3. **In:** Fleet_List. **Out:** none.
4. **Settings:** **Whole data**, NOT the default sample (Explore samples the first 10,000 rows).
5. **Grain to test:** one row per Body_number.
6. **Verify:**
   - If distinct Body_number = row count, the one-row-per-vehicle grain is CONFIRMED.
   - If they differ, duplicates exist. The M5 fleet join would then multiply rows, so it is BLOCKED until deduplicated.
   - Also check: Total has 0 invalid values and a sensible min/max.
7. **Paste back:** row count; distinct Body_number; empty Body_number count; Bus_Type value counts;
   Total min / max / invalid count.
8. **Fallback:** if Analyze has no Whole-data option, use a Group recipe on Fleet_List with key `Body_number`
   and count → `dq_fleet_body_counts`. Then check that the max of `count` is 1.

### Step 1.5 Nol: date and tap-type profile (Group recipe; full data, no PII)
1. **Menu:** **Flow** → click `nol_card_details_15-Dec-2025` → right panel **Actions** → Visual recipes **Group**.
2. **Objects:** recipe `grp_dq_nol_date_tap`, output dataset `dq_nol_date_tap_counts` (zone Z1).
3. **In:** nol_card_details_15-Dec-2025. **Out:** dq_nol_date_tap_counts.
4. **Settings:** Group keys `Transaction_date`, `CKI`, `CKO`. Keep **Compute count for each group** ticked.
   No other aggregations. Add the description "DQ: row counts by date and tap type (no PII)". Click **Run**.
5. **Output grain:** one row per (Transaction_date, CKI, CKO) combination; expect only a handful of rows.
6. **Verify:**
   - The job finished green.
   - Is there only one date (15-DEC-25)? After-midnight taps might sit on 16-DEC.
   - Are there any (CKI=1, CKO=1), (0,0) or empty combinations?
   - Sum of `count` = total Nol rows.
7. **Paste back:** the whole output table (it is tiny and aggregated) and the total of `count`.
8. **Fallback:** if the recipe cannot read the shared dataset (permission error), paste the error text and mark
   it BLOCKED. A mentor may need to grant read access. Do not try to copy the data elsewhere.

### Step 1.6 Nol: Route completeness
1. **Menu:** **Flow** → the Nol dataset → **Actions** → **Group**.
2. **Objects:** recipe `grp_dq_nol_route`, output `dq_nol_route_counts` (zone Z1).
3. **In:** Nol. **Out:** dq_nol_route_counts.
4. **Settings:** Group key `Route`; count ticked; Run. Then open the output → **Explore** → sort by `Route`.
   The row with an empty Route = the missing count.
   Cross-check: in the Nol **Explore**, click `Route` → **Analyze** → **Whole data**, and read **Empty** and **Invalid**.
5. **Output grain:** one row per distinct Route value, including one row for empty.
6. **Verify:**
   - The empty count matches between the two methods.
   - **"Invalid" ≠ missing.** Invalid only means codes like F23 don't fit the locked *Decimal* meaning (CONFIRMED artifact).
   - Look for odd codes such as `0`, `-`, `NULL` or spaces.
7. **Paste back:** number of distinct non-empty routes; empty-Route count and % of total rows;
   the 10 largest routes by count; any odd codes.
8. **Fallback:** if the output has more than 10,000 rows (unlikely), switch the Explore sample to whole data before sorting.

### Step 1.7 Runtime: date profile and Diff_in_seconds range
1. **Menu:**
   (a) **Flow** → Runtime dataset → **Actions** → **Group**.
   (b) Open Runtime → **Explore** → header `Diff_in_seconds` → **Analyze** → **Whole data** → **Compute**.
2. **Objects:** recipe `grp_dq_runtime_date`, output `dq_runtime_date_counts` (zone Z1).
3. **In:** Running_time_15-Dec-2025. **Out:** dq_runtime_date_counts.
4. **Settings:** (a) keys `Date`, `Day_type`; count; Run.
   **Do NOT use Group min/max on `Diff_in_seconds`.** Its storage is *string*, so min/max would be alphabetical.
5. **Output grain:** one row per (Date, Day_type).
6. **Verify:**
   - One date only?
   - Diff_in_seconds invalid count = 0?
   - **Is the min negative?** If yes, early departures are signed (INFERRED). If the min is ≥ 0, the sign
     convention is unresolved (REQUIRES DSS VALIDATION in M2, where we recompute the delay ourselves).
7. **Paste back:** the output table; Diff_in_seconds min, max, mean, median, empty count, invalid count.
8. **Fallback:** if Analyze shows only text statistics, record the top values and the empty count now.
   The numeric range moves to M2, after we parse the column.

### M1 devil's-advocate checks
| Question | Answer for M1 |
|---|---|
| Grain correct? | Nol/Runtime grain INFERRED; Fleet grain tested in 1.4 |
| Join multiplication? | No joins in M1. Fleet duplicates would hit M5 (tested now) |
| Train/test leakage? | n/a (no features yet) |
| 2025 vs 2026 mixing? | GTFS not imported in M1 on purpose |
| One day sufficient? | Dates checked in 1.5 and 1.7; one-day claim only |
| PII exposed? | DQ outputs contain no NOL_ID/Driver_id; never paste those values |
| LLM computing numbers? | No LLM in M1 |
| Feature in my DSS? | Import from collection, Analyze whole data, Group recipe: REQUIRES DSS VALIDATION (Step 1.0) |
| Doable in time? | About 20 min; Group recipes on 1 day of data should be quick |

### M1 evidence template (copy, fill in, paste back)
```
DSS version:
Project name / key:
Datasets in Flow (names, shared or copied):
Zones: done / skipped
FLEET  rows= | distinct Body_number= | empty Body_number= | Bus_Type counts= | Total min/max/invalid=
NOL dq_nol_date_tap_counts table:
   Transaction_date | CKI | CKO | count
NOL total rows (sum of count)=
NOL routes: distinct non-empty= | empty count= | empty %= | top 10= | odd codes=
RUNTIME dq_runtime_date_counts table:
   Date | Day_type | count
RUNTIME Diff_in_seconds min= max= mean= median= empty= invalid=
Errors / anything unexpected:
```


---
## M2 Part A — clean Nol (issued 2026-11-16)
Recipe `prep_nol` (Prepare): `DATA.nol_card_details_15-Dec-2025` -> `nol_taps_clean`. Grain unchanged (one row per tap, 1,056,343 rows).
Steps: Delete/Keep columns by name (delete NOL_ID, device_id_hex); Route meaning -> Text; Formula `route_dq_flag` = `if(isBlank(Route), "MISSING_ROUTE", "OK")`.
Claim wording: NOL_ID is excluded from OUR output; the source dataset still contains it (V25).
Evidence: output row count, flag counts (MISSING_ROUTE expect 106), column list without NOL_ID.

## M2 Part B — clean Runtime (issued 2026-11-16)
Recipe Prepare: `DATA.Running_time_15-Dec-2025` -> `runtime_events_clean`. Grain unchanged (trip x stop event, 259,435 rows).
Steps: Delete columns `Driver_id` (PII); Formula `delay_dq_flag` = `if(isBlank(Diff_in_seconds), "NO_DELAY_VALUE", "OK")`. No delay recomputation yet (V07 stays INFERRED).
Evidence: rows, Driver_id absent, flag counts (expect NO_DELAY_VALUE 11,098), whole-data Empty counts for Act_Dep, Sched_Dep, Act_Arr, Difference (diagnoses V26).

## M2 Part C — clean Fleet (issued 2026-11-17)
Prepare `fleet_clean` (DATA.Fleet_List): Find and replace on Bus_Type (Complete value): 'Standard' and 'Standard -City bus' -> STANDARD (the 'Convert to uppercase' processor was not found on this DSS); formula `vehicle_class` (BUS / NON_BUS / UNKNOWN_TYPE); formula `capacity_dq_flag` (OK / ZERO_CAPACITY).
Then Group `fleet_capacity_lookup` by Body_number: Max(Total), First(Bus_Type), First(vehicle_class), count. Grain = one row per bus.
Expected (derived from M1 Analyze): STANDARD 2,044; NON_BUS 5; UNKNOWN_TYPE 124; BUS 3,135; ZERO_CAPACITY 619; lookup rows 3,263; Body_number 3100 count 2.

## M3 — route and time-slot aggregates (issued 2026-11-17)
M3-0 Analyze Transaction_Time length (expect 5/5). M3-1 Prepare nol_taps_clean -> nol_taps_slotted: Split column on ':' (outputs Transaction_Time_00 / Transaction_Time_01), Formulas minute_of_day = numval("Transaction_Time_00")*60 + numval("Transaction_Time_01"),, slot15 = toInt(floor(minute_of_day/15)), hour_of_day.
M3-2 Group -> route_slot15_demand (keys Route, slot15; Sum CKI, Sum CKO, count; pre-filter route_dq_flag == "OK"; names CKI_sum, CKO_sum, count). Sparse grain; zero-fill in M4.
M3-3 Group -> route_day_demand (key Route; Sum/Max CKI_sum, Sum CKO_sum, Sum count -> count_sum; Compute count = active slots).
No joins, no model. Invariants: Sum count 1,056,237; CKI_sum + CKO_sum 1,056,237; F24 = 24,329; TR1 = 4; about 200 routes. Next: M4 (zero-filled grid, lags, baseline, train/test split at slot boundary).

## M4 - forecast (issued 2026-11-17)
A: forecast_routes (Filter count_sum >= 3000), slot_list (Group slot15 -> 96 rows), route_slot_grid (cross join; rows = routes x 96; Python fallback).
B: left-join route_slot15_demand on Route+slot15, fill missing CKI_sum/CKO_sum with 0 -> Window lags (CKI_sum lag 1..8, CKO_sum lag 1..4) -> forecast_features.
C: split train slot15 8-55 / test 56-95; baseline naive h1 = lag1, naive h4 = lag4; baseline errors.
D: Visual ML (regression, target CKI_sum): h1 features lag1-8, CKO lags, Route; h4 features lag4-8 only. Explicit train/test datasets. Score test.
E: forecast_metrics: MAE, RMSE, MAPE (actual >= 5), WAPE; model vs baseline; AM peak slots 24-35, PM peak 64-79 (ASSUMED); skill = 1 - MAE_model/MAE_baseline.
