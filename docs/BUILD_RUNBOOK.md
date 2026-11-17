# Build Runbook — beginner steps (Dataiku DSS)

Menu labels can differ slightly by DSS version. If a button is missing, use the search bar
(top of Dataiku) or ask a mentor. **Before each heavy Build or model training, tell the team.**

## 0. Prioritised two-hour plan
| Time | Priority | Phase | Done when |
|---|---|---|---|
| 0:00–0:15 | P0 | Setup, import, Flow Zones, data-quality checks (§1) | 3 raw datasets in Flow; answers to EVIDENCE §6 Q1–Q5 noted |
| 0:15–0:40 | P0 | Z1 + Z2: clean Nol, 15-min demand grid (§2) | `demand_route_15min_full` built |
| 0:40–0:55 | P0 | Z4: supply join, lags, split (§3) | `features_train`, `features_test` built |
| 0:55–1:15 | P0 | Z5: Visual ML h1 + h4, deploy, score (§4) | 2 models; scored test sets |
| 1:15–1:25 | P0 | Z6: metrics vs naive (§5) | `forecast_metrics` table |
| 1:25–1:45 | P1 | Z3 + Z7: runtime/fleet, decisions (§6) | `route_hour_decisions`, `route_evidence_card` |
| 1:45–1:55 | P2 | Z8: agents via Prompt recipes (§7) | `recommendations_final` |
| 1:55–2:00 | P2 | Dashboard + Wiki (§8) | judges can follow the story |
| after | P3 | HTML webapp, GTFS 2026 scenario, feeder, communities, deck | |

With 3 people, run tracks in parallel after §1. A: §2–§5 (forecast). B: §6 (runtime/fleet/decisions).
C: §7–§8 + deck. Merge at 1:25.

## 1. Setup (P0)
1. Open your Team 7 project (or **+ New Project > Blank**, name `RTA_T7_DemandPulse`).
2. Bring in catalog datasets: **Catalog > Collections > RTA Future Move Hackathon**, then click
   `nol_card_details_15-Dec-2025` and use **Use in project / Import / Share** with your project
   (label varies). Repeat for `Running_time_15-Dec-2025` and `Fleet_List`. GTFS and communities
   come later (P3). They appear in your Flow as linked datasets from project `DATA`. **Never edit them.**
3. Flow Zones: Flow > **Zones > + New zone**. Create: `Z1 Ingest & PII guard`, `Z2 Demand`,
   `Z3 Supply & Reliability`, `Z4 Features`, `Z5 Forecast`, `Z6 Evaluation`, `Z7 Decisions`,
   `Z8 AI Agents`. Move the 3 raw datasets into Z1 (right-click > Move to zone).
4. Data-quality checks (guide DON'T #2). Open each dataset > **Explore**, click a column header >
   **Analyze** (whole data, not sample). Write the answers into docs/PROGRESS.md:
   - Nol: row count (Status tab > Compute); Route empty %; CKI/CKO value counts.
   - Runtime: Diff_in_seconds min/max (are there negatives?); Route value count.
   - Fleet: Bus_Type values; Total min/max.
5. Wiki: Project menu > **Wiki > Create article** "Assumptions & Data". Paste EVIDENCE §3 (period rule).

## 2. Clean Nol and build 15-min demand (P0, Z1 + Z2)
**Recipe 1 `prep_nol`.** Select `nol_card_details_15-Dec-2025` > **Actions > Prepare**. Output name
`nol_taps_clean`, then **Create recipe**. Add steps (+ Add a new step, search by name):
1. *Delete/Keep columns by name*: delete `NOL_ID`, `device_id_hex`, `Amount` (PII and undocumented fields).
2. Click the `Route` header > **Change meaning > Text** (fixes the red invalid cells).
3. *Filter rows/cells on value* (or **Remove rows where cell is empty**) on `Route`. Record how many rows dropped.
4. *Split column*: `Transaction_Time`, delimiter `:`, output prefix `t_` (gives `t_0` = hour, `t_1` = minute; check the names).
5. *Formula* `minute_of_day` = `numval("t_0")*60 + numval("t_1")`
6. *Formula* `bin15` = `floor(minute_of_day/15)`   ·   *Formula* `hour` = `numval("t_0")`
7. *Extract with regular expression* on `Body_EVD_ID`, pattern `B(\d+)_EVD`, prefix `body_`
   (gives the bus body number; check the output column name).
8. Description (recipe Settings / Summary): "Drops PII, adds 15-min time bins and body number."
Click **Run**. While developing, keep the default sample (guide DO #13).

**Recipe 4 `grp_demand_route_15min`.** Select `nol_taps_clean` > **Group**. Group keys: `Route`, `bin15`.
Aggregations: `CKI` → Sum, `CKO` → Sum. Output `demand_route_15min`. In the Output step, rename to
`boardings` and `alightings`. Run.

**Recipes 5–7: zero-filled grid.** Interval rows with no taps don't exist yet, so lags would be wrong without these steps.
- Group `demand_route_15min` by `Route` only (no aggregations) → `route_list`.
- Group `nol_taps_clean` by `bin15` only → `bin_list`.
- **Join** `route_list` with `bin_list`. Click the join type > **Cross join** → `route_bin_grid`.
- **Join** `route_bin_grid` (left) with `demand_route_15min` on `Route` + `bin15`, type **Left join**.
  Add a post-join Prepare step (or a Prepare recipe) *Fill empty cells with fixed value* `0` on
  boardings/alightings → `demand_route_15min_full`.
- If Cross join is unavailable, use the Python fallback below.

## 3. Features and split (P0, Z4) — summary, expand when reached
- Join `demand_route_15min_full` (left) with `supply_route_15min` (built by §6 step 3, or build it now)
  on Route = Route, bin15 = sched_bin15; fill 0 → `demand_supply_15min`.
- **Window** recipe: Windows definitions > Partitioning column `Route`, Order column `bin15` (ascending).
  Aggregations: `boardings` tick **Lag**, offsets `1,2,3,4,5,6,7,8`; `alightings` Lag `1,2,3,4` → `demand_features_15min`.
- Prepare `prep_features`: Formula `ma4_h1`, `ma4_h4`, `naive_h1`, `naive_h4`, `route_prefix`
  (Extract with regex `^([A-Za-z]*)`). Remove rows where lag-8 is empty → `demand_features_ready`.
- **Split** recipe > *Define filters*: `bin15 <= 55` → `features_train`; others → `features_test`.

## 4–8. Model, metrics, decisions, agents, dashboard — summary
- §4 Visual ML: select `features_train` > **Lab > AutoML Prediction**, target `boardings`, Quick prototypes.
  Design > Train/Test set > **Explicit extracts from two datasets** (train = features_train,
  test = features_test). Features handling per DATAIKU_FLOW Z5. Algorithms: LightGBM/XGBoost, RF, Ridge.
  Metric: MAE. Train. Duplicate the session for h4 and reject lag1–3. **Deploy** best → **Score** features_test.
- §5 Metrics: DATAIKU_FLOW Z6 formulas. Screenshot the table and the model report for the deck.
- §6 Runtime/fleet/decisions: DATAIKU_FLOW Z3 + Z7.
- §7 Agents: **+ Recipe > Generative AI > Prompt** (needs an LLM connection; pick one in the LLM
  dropdown). Prompts go in `code/agent_prompts.md` (to be written).
- §8 Dashboard: charts (actual vs predicted by bin, MAE by horizon/period, pressure heatmap route×hour),
  model report insight, recommendations table, Wiki link.

## Fallback: Python recipe for grid + lags (only if Cross join or Window fails)
Select `demand_route_15min` > **+ Recipe > Python**, output `demand_features_15min`:
```python
import dataiku, pandas as pd
df = dataiku.Dataset("demand_route_15min").get_dataframe()
bins = range(int(df["bin15"].min()), int(df["bin15"].max()) + 1)
grid = pd.MultiIndex.from_product([df["Route"].unique(), bins], names=["Route", "bin15"]).to_frame(index=False)
full = grid.merge(df, on=["Route", "bin15"], how="left").fillna({"boardings": 0, "alightings": 0})
full = full.sort_values(["Route", "bin15"])
g = full.groupby("Route")
for k in range(1, 9):
    full[f"boardings_lag{k}"] = g["boardings"].shift(k)
for k in range(1, 5):
    full[f"alightings_lag{k}"] = g["alightings"].shift(k)
dataiku.Dataset("demand_features_15min").write_with_schema(full)
```
(The supply join then happens after this recipe instead of before.)
