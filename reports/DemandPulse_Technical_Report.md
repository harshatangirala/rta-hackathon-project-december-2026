# DemandPulse: Matching Dubai Bus Capacity to Demand

Technical report, RTA Future Move Hackathon, Team 7. Built end to end in Dataiku DSS 15.2 on one observed day of Dubai bus data (Monday 15 Dec 2025). November 2026.

## Executive summary

DemandPulse shows where Dubai bus seats, delays and passenger demand do not match, and what RTA can change without touching fares, removing trips or building infrastructure. On the observed day it found:

- **Forecast:** route boardings can be predicted 15 minutes ahead with 18.3% lower error than the last-known-value baseline (MAE 16.68 vs 20.41 boardings per route per 15-minute slot). At 60 minutes ahead the gain is 6.1%.
- **Capacity mismatch:** 28 route-hours carry more card-tap boardings than seats offered (demand pressure of 1.0 or more), while 1,262 route-hours run at 0.25 or less.
- **Cost-neutral fix (what-if):** 18 bus swaps move 792 seats from quiet to busy route-hours. In the scenario, 13 of the 28 busy route-hours drop below 1.0, and 0 trips are removed.
- **Reliability:** 761 route-hours have 30% or more of timed departures more than 5 minutes late.
- **Congestion:** 388 of 4,620 route-segment-hours (8.4%) run 30 s or more over schedule. The worst corridor, route F27 from Max Metro Bus Stop Landside 2 to Satwa, Masjid 1, runs up to 509 s over schedule in the evening.
- **AI agents:** two specialist agents and a coordinator write 12 action cards. An automatic checker passed all 24 AI answers on numbers, forbidden advice and format.

Everything runs in one Dataiku Flow of 7 zones (39 datasets, 30 recipes, 2 saved models), with two webapps for control-room and planning use. Card and driver identifiers are dropped in the cleaning zone. The main limit is the data: one observed day, so forecasts are intraday only and scenario results are what-ifs, not measured outcomes.

## Problem and scope

Our question: where and when do bus capacity, reliability and passenger demand not match, and what can RTA change next without changing fares, removing trips or building infrastructure?

The solution serves three users:

- **Control-room dispatchers:** which corridors lose time now, which actions to take, with a human confirming each one.
- **Service planners:** which route-hours are over- or under-supplied, and which bus swaps would help.
- **Communications team:** which nearby hour is calmer on a busy route, as a demand-shifting message.

| In scope | Out of scope (and why) |
| --- | --- |
| Intraday forecasts of route boardings, 15 and 60 minutes ahead | Weekly, seasonal or event forecasts: only one observed day |
| Capacity, reliability and congestion screening per route-hour and stop pair | On-board load: there is no passenger-counter (APC) data |
| A cost-neutral bus-swap what-if | Fare changes, trip or frequency cuts, new lanes or depots: guide DON'Ts |
| AI-written, number-checked action cards for staff | A consumer trip-planner chatbot: conflicts with guide DO #19 (no consumer apps) |
| Two Dataiku webapps for staff | Comparing 2025 actuals with the planned 2026 timetable as one period |

**Guardrails applied to every recommendation:** no fare change; no trip or frequency cut, to protect network equity; no new infrastructure; driver rest respected; vehicle types respected. Every action in the webapp needs two human confirmations before it can be approved.

## Data

Four RTA catalogue datasets were linked into the project unchanged. Two of them describe what actually happened on one day; the stops file comes from the planned 2026 timetable and is used only to place stops on a map.

| Dataset | What one row is | Period | Size | Used for |
| --- | --- | --- | --- | --- |
| Nol card details | One card tap (check-in or check-out) | Actual, Mon 15 Dec 2025 | 1,056,343 taps: 544,583 check-ins, 511,760 check-outs | Demand, stop crowding |
| Running time (AVL) | One trip at one stop: scheduled vs actual departure | Actual, Mon 15 Dec 2025 | 259,435 rows | Seats offered, delay, congestion |
| Fleet list | One vehicle: type and capacity | Reference list | 3,264 rows | Seats per bus |
| Stops (GTFS) | One stop: name and coordinates | Planned timetable, 11 Sep to 31 Dec 2026 | 2,607 Nol stops placed (98.4%) | Map positions only |

**Period rule:** Nol and running times are actual 2025 observations; GTFS is a planned 2026 timetable. They are never compared as the same period.

**Privacy and data handling:**

- The card identifier (NOL_ID) and the driver identifier (Driver_id) are dropped in the cleaning zone and appear in no analytical dataset. The source datasets are unchanged.
- The language model sees only short summary text per case: route codes, stop names and aggregate numbers.
- All data stayed inside Dataiku. No external or open data was used. No raw data is stored in this repository.

**Caveat on Nol:** some taps come from non-bus stops (for example a marine transport station), so a few route codes may be tram or ferry services. Route-level counts should be checked before rollout.

## Architecture

The Flow has seven zones and two branches that share one cleaned demand table. The forecast branch ends in accuracy metrics; the decision branch feeds the AI cards and the control-room webapp.

```
Source Data  ->  Data Cleaning & Quality  ->  Demand Aggregation & Preparation
                                                  |                     |
                                       FORECAST BRANCH          DECISION BRANCH
                                  Forecasting & Evaluation   Fleet & Route Operations
                                       (forecast_metrics)    Crowding & Operational Reporting
                                                             AI Decision Support
                                                  \                     /
                                               Two Dataiku webapps
```

Raw data is cleaned once, aggregated once, then used twice. The forecast branch is validated on its own; using the forecast as an early warning inside the decision recipe is a next step.

## Data preparation and quality

Every problem found in the data was flagged and handled in a visible recipe, and every total was reconciled back to the source. The key checks:

| Area | Finding | How it was handled |
| --- | --- | --- |
| Nol dates | All taps on one date | Confirmed by a date count recipe |
| Nol routes | 106 taps (0.01%) had a blank route, all check-ins | Flagged and excluded from route demand; 1,056,237 taps kept |
| Running-time delay | Signed: minimum -2,945 s, median +117 s (early departures are negative) | Used as given; late = more than 300 s |
| Running-time gaps | 11,098 rows (4.3%) had no delay value | Kept for counting trips, excluded from delay statistics |
| Running-time hours | 6,283 events had an hour outside 0-23 | Excluded; 253,152 events used for decisions |
| Fleet duplicates | Bus 3100 appears twice | One row per bus in fleet_capacity_lookup |
| Fleet capacity | 619 vehicles (19%) had capacity 0; 5 non-bus vehicles; mixed spellings of Standard | Capacity 0 treated as unknown; 99.7% of running-time events matched a bus with valid capacity |

**Building the demand table:**

1. Each tap was placed in one of 96 fifteen-minute slots; all 96 are present. Taps peak around 07:45-09:00 and 18:15-19:00.
2. Boardings (check-ins) and alightings (check-outs) were summed per route and slot: 13,837 rows that reconcile exactly to the 1,056,237 taps.
3. The forecast covers the 117 routes with at least 3,000 taps that day, which carry 88.5% of boardings.
4. A full grid of 117 routes x 96 slots (11,232 rows) was built with a cross join, and empty slots were filled with 0. 20.6% of cells are true zeros. Without this grid, the lag features would silently skip quiet slots.

Three data-quality datasets (date and route counts) are kept in the Flow as an audit trail.

## Forecasting

A Ridge regression forecasts route boardings 15 minutes ahead with 18.3% lower MAE than the baseline, and 60 minutes ahead with 6.1% lower MAE. It beats the baseline on MAE, RMSE and WAPE in all six horizon and segment cells.

### Design

- **Target:** boardings (sum of check-ins) per route per 15-minute slot, for 117 routes.
- **Horizons:** h1 = the next slot (15 minutes ahead) and h4 = four slots ahead (60 minutes ahead). One direct model per horizon.
- **Time-ordered split:** training on 02:00-13:59 (5,616 route-slots), testing on 14:00-23:59 (4,680 route-slots) that the models never saw. Slots 00:00-01:59 are dropped because their lags would reach before midnight.
- **Baseline:** the last value known when the forecast is made (15 or 60 minutes earlier). A model that cannot beat this is not useful.
- **Algorithms:** Ridge, Random forest and XGBoost in Dataiku Visual ML, with explicit train and test datasets. Ridge was selected at both horizons. Negative predictions are clipped to 0.

### Leakage rules

Each horizon only sees information that exists at forecast time.

| Feature group | 15-minute model | 60-minute model |
| --- | --- | --- |
| Boardings lags | Lags 1-8 | Lags 4-8 only |
| Alightings lags | Lags 1-4 | Lag 4 only |
| Moving averages | ma4_h1 and ma4_h4 | ma4_h4 only |
| Rejected | Route, slot, period, same-slot alightings | The same, plus every lag under 4 slots |
| Inputs used | 14 | 7 |

A first training session used a random split and these leaky features. It looked better (Random forest MAE 11.4, R2 0.81) and was discarded, because a random split lets the model peek at neighbouring slots from the same afternoon.

### Model comparison (Dataiku Visual ML, test set of 4,680 route-slots)

| Horizon | Model | MAE | RMSE | R2 |
| --- | --- | --- | --- | --- |
| 15 min | **Ridge (selected)** | **16.717** | **23.807** | **0.762** |
| 15 min | Random forest | 16.964 | 24.648 | 0.745 |
| 15 min | XGBoost | 17.446 | 25.409 | 0.729 |
| 60 min | **Ridge (selected)** | **21.388** | **30.583** | **0.608** |
| 60 min | Random forest | 21.958 | 32.140 | 0.567 |
| 60 min | XGBoost | 22.065 | 32.867 | 0.547 |

The simplest model won because the signal is mostly recent demand on the same route. Feature importance confirms it: the 15-minute model leans on ma4_h1 and the most recent lags; the 60-minute model leans on boardings lag 4, then lags 5, 8 and 7.

### Results against the baseline (forecast_metrics recipe)

The evening peak is 16:00-19:59. The MAE here (16.680) differs slightly from Visual ML (16.717) because predictions are clipped at 0.

| Horizon | Segment | Route-slots | MAE model / baseline | MAE gain | RMSE gain | WAPE model / baseline |
| --- | --- | --- | --- | --- | --- | --- |
| 15 min | All test rows | 4,680 | 16.68 / 20.41 | +18.3% | +19.3% | 30.9% / 37.8% |
| 15 min | Evening peak | 1,872 | 20.96 / 26.04 | +19.5% | +20.1% | 27.5% / 34.1% |
| 15 min | Off-peak | 2,808 | 13.83 / 16.65 | +17.0% | +18.2% | 35.4% / 42.6% |
| 60 min | All test rows | 4,680 | 21.33 / 22.73 | +6.1% | +8.4% | 39.5% / 42.1% |
| 60 min | Evening peak | 1,872 | 26.66 / 28.13 | +5.2% | +3.5% | 34.9% / 36.9% |
| 60 min | Off-peak | 2,808 | 17.78 / 19.13 | +7.0% | +14.6% | 45.5% / 48.9% |

**How to read it:**

- The 15-minute forecast is clearly useful: about 17-20% less error in every segment, and strongest in the evening peak.
- The 60-minute forecast is only modestly better than the baseline (5-7%). Treat it as indicative.
- Errors stay large: WAPE is 31% at 15 minutes and 39.5% at 60 minutes, against an average of about 54 boardings per route-slot. Use the forecast for decision support, not exact counts.
- MAPE improves in 5 of 6 cells; it is slightly worse off-peak at 60 minutes, because percentage errors are unstable when counts are small.
- The test window holds the evening peak only. Morning-peak accuracy was not tested.

## Capacity, reliability and the bus-swap scenario

The network has far more spare capacity than shortage: 1,262 route-hours are under-used while 28 are over-pressured, and those 28 carry only 1.1% of boardings. That makes a cost-neutral reallocation possible.

### Definitions (thresholds are assumptions, tunable)

- **Demand pressure** = card-tap boardings in a route-hour / seats offered in that hour (sum of vehicle capacity over the distinct trips that ran). It is a screening proxy, not on-board load: cash and other payments are not in Nol, and passengers ride across hours.
- **High pressure:** 1.0 or more. **Under-used:** 0.25 or less, with at least 2 trips.
- **Late:** departure more than 5 minutes behind schedule. **Unreliable:** 30% or more of at least 20 timed departures late.

### Coverage

3,727 route-hours had demand. 3,001 of them (80.5%) matched running-time data, covering 166 of 200 routes. The other 34 routes cannot be judged.

### Results

| Flag | Route-hours | Share of matched |
| --- | --- | --- |
| High pressure (1.0 or more) | 28 | 0.9% (1.1% of boardings) |
| Under-used (0.25 or less) | 1,262 | 42% |
| Unreliable (30% or more late) | 761 | 25% |

**Busiest routes** (route_evidence_card):

| Route | Boardings | Busiest hour | Max pressure | Under-used hours | Unreliable hours | Median delay (s) |
| --- | --- | --- | --- | --- | --- | --- |
| F24 | 12,201 | 18:00 | 0.57 | 3 | 0 | 37.75 |
| F15 | 11,405 | 18:00 | 0.80 | 1 | 6 | 87.5 |
| 88 | 9,661 | 18:00 | 0.62 | 0 | 7 | 168.5 |
| 28 | 9,400 | 18:00 | 0.64 | 1 | 0 | 101 |
| F23 | 8,983 | 18:00 | 0.58 | 2 | 0 | 58.5 |
| F22 | 8,728 | 18:00 | 0.51 | 8 | 0 | 42 |
| 13D | 8,462 | 08:00 | 0.38 | 11 | 3 | 77 |
| C01 | 8,345 | 18:00 | 1.87 | 12 | 9 | 162.25 |

C01 is the only top route with an hour above 1.0, and it also has 12 under-used and 9 unreliable hours: its capacity is in the wrong hours.

**Highest pressure route-hours:** 11CUP at 17:00 (2.00: 138 boardings on 1 trip of 69 seats), 11CUP at 18:00 (1.99), D03 at 16:00 (1.98), C01 at 04:00 (1.87, 211 boardings on 1 trip) and F44 at 19:00 (1.46, 289 boardings on 3 trips). Most are single-trip hours, where the proxy is most sensitive, so on-board load must be confirmed.

**Least reliable routes:** 77 and J02 (14 unreliable hours each; median delays of about 241 s and 254 s) and 53 (13 hours, 206 s). Among the busiest routes, X13 (204 s), 88 (168.5 s), F46 (164 s) and C01 (162 s) have the highest median delays.

### Cost-neutral bus-swap scenario (what-if, not measured)

**Rule:** in the same hour, a large bus (100 seats or more) moves from an under-used route-hour to a high-pressure route-hour that runs a smaller bus. The donor must stay at or below 0.50 after the swap. Same buses, same trips, same hour.

**Result:** 18 swaps move 792 seats and remove 0 trips. 13 of the 28 high-pressure route-hours fall below 1.0; the other 15 need a standby trip or on-board load data first.

## Congestion hotspots and alternative routes

Buses lose time on a few repeat corridors, and one of them dominates: route F27 between Max Metro Bus Stop Landside 2 and Satwa, Masjid 1 accounts for about ten times the passenger delay of the next corridor.

### Method

Nol taps show crowding at stops, not road traffic. Road delay comes from the running times:

- **Extra seconds on a segment** = (actual arrival - previous actual departure) - (scheduled arrival - previous scheduled departure), for each pair of consecutive stops on a trip.
- A route-segment-hour needs at least 5 trips. A **hotspot** has a median of 30 s or more over schedule.
- **Passenger-delay minutes** = boardings at the segment's first stop x extra minutes, summed over the hours. It ranks corridors by how many people feel the delay; it is a proxy, not measured passenger time.
- Stop coordinates from the stops file only place stops on the map: 98.4% of 2,607 stops and 98.6% of taps matched. Speeds use straight-line distance, so they are a relative proxy.
- An **alternative** is another route serving the same stop pair in the same hour, with spare seats (pressure 0.50 or less) and at most half the hotspot's extra time.

### Results

246,343 stop-to-stop segment events were analysed (0.76% skipped as invalid). Of 4,620 route-segment-hours, 388 (8.4%) run 30 s or more over schedule. The median speed proxy is 20.3 km/h.

| Route | Corridor | Hours | Over schedule (s, median per hour) | Passenger-delay minutes |
| --- | --- | --- | --- | --- |
| F27 | Max Metro Bus Stop Landside 2 -> Satwa, Masjid 1 | 07:00, 10:00, 17:00-22:00 | 122-509 | 12,046 |
| 310 | Rashidiya Bus Station Gate 9 -> E311 Road 1 (Non Stop) | 06:00-10:00 | 47-97 | 1,163 |
| F19A | Bay Square 1 -> Burj View central Tower 1 | 16:00-18:00 | 166-507 | 1,162 |
| 320 | Silicon Oasis HQ 1 -> E311 Road 2 (Non Stop) | 17:00, 19:00 | 696-1,301 | 940 |
| F16 | Onpassive Bus Terminus 1 -> Al Quoz, Cement Factory | 06:00, 17:00, 20:00 | 45-597 | 878 |
| 24 | Cargo Village -> Al Nahda 1, Burj Al Noor 1 | 19:00 | 339 | 627 |

**F27 in detail:** the segment is about 1.57 km in straight line. In the evening it is scheduled at 7-8 minutes but takes about 15-16. Every trip ran more than 60 s over, with 5-9 trips and 259-447 boardings at the first stop per hour. The speed proxy is 5.7-6.1 km/h.

**E311 morning corridor (route 310):** 82-97 s over schedule at 07:00-08:00, about 32 km/h against 45 km/h scheduled, with 245-254 boardings. This is the most credible case of road congestion rather than timetable error.

**Alternatives are rare:** only 1 of the top 30 hotspots has one. Route F09, on Satwa Roundabout 2 -> Max Metro Bus Stop Landside 2 at 18:00, ran 28 s ahead of schedule with pressure 0.455 on 3 trips, while F27 ran 193.5 s over on the same stop pair. Matching nearby stops, not only identical stop pairs, would find more.

**What the data cannot tell:** time over schedule can be traffic or an unrealistic timetable. So the recommended action for most corridors is a timetable and headway review, not a traffic measure.

## AI agents

The agents turn the Flow's results into short action cards that a dispatcher or planner can act on. They explain and prioritise; they never compute a number. All 24 AI answers passed the automatic check, and only checked cards reach the dashboard.

### How the chain works

1. **Case file (agent_cases, Python):** 12 cases built from the Flow outputs: the 5 worst corridors, the 3 highest-pressure route-hours, 2 spare-capacity route-hours on large buses, and the 2 least reliable routes. Each case holds plain facts, a rule-based suggestion and a task. No card or driver identifiers.
2. **Specialist agents (Prompt recipe):** each case goes to its specialist, either the congestion and reliability specialist or the supply-demand specialist. The specialist explains what the facts mean for passengers and names one operational step.
3. **Coordinator agent (Prompt recipe):** merges the facts, the rule-based suggestion and the specialist view into a 4-line card: CHANGE, WHY, MEASURABLE, GUARDRAIL CHECK.
4. **Checker (agent_checks, Python):** tests every AI answer. Every number must appear in that case's facts, suggestion or task (or be the fixed rule values 5 and 30). No forbidden advice may appear (fare increase, surge pricing, bus lane, new depot, cut or reduce frequency, cancel or cut trips, skip rest, and similar). A card must contain all four lines.
5. **Display:** the DemandPulse Ops webapp shows a card as "AI-written, numbers verified" only when both of its answers passed. Otherwise it shows "held for human review" with the rule-based suggestion.

The model runs through Dataiku's LLM Mesh. That connection rejects the temperature setting, so it is left at the default.

### Results

24 of 24 answers passed (12 specialist views and 12 coordinator cards). The webapp shows "12 of 12 cases passed verification". An example card, as written by the coordinator:

> **CHANGE:** Replace the scheduled bus on Route 11CUP at 17:00 with a larger articulated or double-decker bus, subject to route and bus-type suitability and confirmation of on-board loads; keep every trip and frequency unchanged.
> **WHY:** The facts show 138 boardings, 1 trip and average capacity of 69 seats, with demand pressure of 2.00 boardings per offered seat, a screening proxy, not confirmed on-board load.
> **MEASURABLE:** Track demand pressure in boardings per offered seat on Route 11CUP at 17:00.
> **GUARDRAIL CHECK:** No fare change, trip or frequency cut, or new roads or depots; preserve every neighbourhood's service and respect driver rest periods and bus-type suitability.

### What the check proves, and what it does not

- It proves that the numbers come from the data and that forbidden advice is absent. It does not prove the reasoning is right, so every action still needs two human confirmations in the webapp.
- The wording changes each time the recipes run; the numbers are checked on every run.
- Some cards add a remark about the specialist view in the GUARDRAIL CHECK line. That is cosmetic and can be removed from the prompt.
- These are Prompt recipes in the Flow, not Dataiku's native Agent objects. A native agent with dataset tools is a next step.

### Deterministic layer

Next to the AI cards, the webapp has four rule-based summaries (congestion, supply-demand, reliability, coordinator) and an end-of-day report built from daily_ops_report. They always work, even if the language model is unavailable.

## Dashboards

Two Dataiku Standard webapps put the results in front of staff. DemandPulse Ops reads the Flow's datasets live through a Python backend, so no number is retyped; DemandPulse Team7 is a planning snapshot of the outputs as of 17 Nov 2026. Their source is in the `code/` folder.

### DemandPulse Ops (live control room and planning)

| Tab | Question it answers | What it shows |
| --- | --- | --- |
| Map and hotspots | Where do buses lose time, and how many passengers feel it? | Hour-by-hour replay of the day: stops sized by boardings, hotspot segments coloured by delay, corridors ranked by passenger delay, detail and alternatives per corridor |
| Actions and agents | What should we do, and is it safe? | 16 prioritised actions (6 corridor, 5 crowding, 5 spare-capacity). Each needs two human confirmations before Approve unlocks. Four rule-based summaries, the 12 checked AI cards and the end-of-day report |
| Supply-demand gaps | Which hours on a route are over- or under-supplied? | Route picker, 24-hour colour strip of demand pressure with late-departure markers, and network-wide top lists |
| Passenger advisory | Which nearby hour is calmer? | Busy level of a route at an hour and a calmer hour within two hours, as a message for RTA communications, not a trip planner |
| Forecast and method | How good is the forecast? | Model vs baseline table and bar chart, and the limits list |

### DemandPulse Team7 (planning snapshot)

Five tabs: forecast accuracy with horizon and metric toggles, a sortable route explorer with rule-based commentary, the swap scenario (18 swaps, 13 of 28 resolved, 0 trips removed), three decision cards, and the agent and data-handling notes.

### Design choices that reduce human error

- Every number on screen comes from a Dataiku dataset; the live webapp has no hard-coded results.
- An action cannot be approved until two named checks are ticked, such as "spare bus and rested driver available".
- Each action carries guardrail tags: no fare change, no trip cut, no new infrastructure.
- If the backend fails, the page says so and shows the saved forecast values, instead of showing wrong data.

## Recommendations for RTA

RTA can act on four changes that keep every trip, every fare and the existing infrastructure. Each is a pilot to confirm with on-board load data, not a final rollout.

| # | Change | Why (evidence from the observed day) | What to measure |
| --- | --- | --- | --- |
| 1 | **Right-size vehicles by hour:** pilot the bus swaps, moving large buses from under-used to high-pressure route-hours in the same hour | 1,262 route-hours run at 0.25 or less while 28 reach 1.0 or more. In the scenario, 18 swaps move 792 seats and bring 13 of the 28 below 1.0, with 0 trips removed | Demand pressure at the busiest hour of each pilot route, before and after; on-board load from passenger counters |
| 2 | **Review timetables and dispatch headways on the worst corridors**, starting with F27 Max Metro Bus Stop Landside 2 -> Satwa, Masjid 1 | F27 has 12,046 passenger-delay minutes, ten times the next corridor; it is scheduled at 7-8 minutes but takes about 15-16 in the evening | Median seconds over schedule per hour on the segment; passenger-delay minutes |
| 3 | **Review running-time buffers** on route-hours where 30% or more of departures run over 5 minutes late | 761 route-hours (25% of matched) meet this; routes 77 and J02 have 14 such hours each; X13, 88, F46 and C01 have median delays above 160 s | Share of departures more than 5 minutes late per route-hour; median delay |
| 4 | **Use the 15-minute forecast as an early warning** for standby and short-turn decisions; treat the 60-minute view as indicative | 18.3% lower MAE than the baseline at 15 minutes (19.5% in the evening peak), but only 6.1% at 60 minutes | Forecast WAPE on live days, per horizon and peak period |

**Guardrails on all four:** no fare change; no trip or frequency cut, to keep network equity; no new infrastructure; driver rest and vehicle types respected; two human confirmations per action.

**Suggested order:** start with change 2 on F27 (one corridor, one timetable owner), run change 1 on two or three pilot routes such as 11CUP and D03 for two weeks, and switch on change 4 once the forecast is wired into the decision recipe.

## Validation, assumptions and limitations

The results hold for one observed day and are screening tools, not measured outcomes. Each claim was labelled as checked in the data, assumed by design, or not claimed (see `docs/VALIDATION_AND_LIMITATIONS.md`).

### Checks performed

- Totals reconciled at each aggregation step (route-slot demand equals the 1,056,237 cleaned taps).
- Time-ordered train and test split; the leaky first model session was found and discarded.
- Model compared against a naive baseline on four metrics, by horizon and by peak segment.
- Python recipes tested on mock data before running on real data; webapp pages tested in a simulated browser, including the backend-failure path.
- Every AI answer checked automatically for unsupported numbers, forbidden advice and format.

### Assumptions (design choices, stated and tunable)

| Assumption | Value used |
| --- | --- |
| High pressure / under-used thresholds | 1.0 / 0.25 boardings per offered seat |
| Late departure / unreliable route-hour | More than 5 minutes / 30% or more of at least 20 departures |
| Hotspot threshold | Median 30 s or more over schedule, at least 5 trips |
| Large bus for the swap; donor limit after swap | 100 seats or more; 0.50 or less |
| Peak window | Evening 16:00-19:59 (morning 06:00-08:59 is in training only) |
| Forecast scope | 117 routes with at least 3,000 taps that day |
| Fleet capacity | The fleet's Total field; capacity 0 treated as unknown |
| Stop locations | 2026 stop coordinates used only to place 2025 stops |

### Limitations

1. **One observed day.** No weekday, seasonal or event effects; the forecast is tested on the later hours of the same day only.
2. **Demand pressure is not on-board load.** Card taps miss cash and other payments, and there is no origin-destination per trip.
3. **Capacity figures** depend on the fleet list, whose standing capacity is unverified and where 19% of vehicles had no capacity.
4. **Traffic vs timetable** cannot be separated; straight-line speeds are unreliable for segments under 1 km.
5. **Scenario results are what-ifs** under stated rules, not measured outcomes.
6. **The forecast does not yet feed the decision recipe.** Decisions use observed demand; the forecast is validated separately and recommended as an early-warning input.
7. **Model tuning** used cross-validation inside the training half, which is not time-ordered; only the final test half is a true time holdout.
8. **AI checks** prove numbers and forbidden terms, not reasoning; human approval stays mandatory.
9. **Nol may include non-bus services** (marine, possibly tram) for a few route codes.
10. **Sending the end-of-day report automatically** needs a Dataiku Scenario with a messaging channel set up by an administrator; today it is copied from the webapp.

## Fit with the hackathon guide and the judging criteria

The solution answers all five judging criteria with evidence that can be opened in the Dataiku project.

| Criterion | Evidence |
| --- | --- |
| Practical application | Four changes RTA can pilot without fares, trip cuts or infrastructure; a control-room action queue with human confirmation; a cost-neutral swap that resolves 13 of 28 over-pressured route-hours in the scenario |
| Documentation and visuals | 7 named, colour-coded Flow Zones; this report; two webapps with an hour-replay map, colour strips and a forecast chart |
| Innovation | Congestion measured from running times and weighted by Nol boardings (passenger-delay minutes); alternative-route search on identical stop pairs; AI cards that are shown only after an automatic number check |
| AI model | Visual ML comparison of Ridge, Random forest and XGBoost per horizon; leakage-safe feature sets by horizon; feature importance; a leaky session caught and discarded |
| Forecast accuracy | Beats the baseline on MAE, RMSE and WAPE in all six cells: +18.3% MAE at 15 minutes, +6.1% at 60 minutes, on a held-out afternoon and evening |

### Guide rules followed

- **Visual recipes first:** 25 of 30 recipes are visual (Prepare, Group, Join, Window, Split, Sample, Train, Score, Prompt). Python is used in 5 places a visual recipe cannot cover well: forecast metrics, the decision engine and swap, segment geometry, the agent case file and the answer checker.
- **Personal data:** NOL_ID and Driver_id are dropped before any analysis or language model.
- **Data stays on the platform:** no raw rows leave Dataiku; the language model sees aggregate text only.
- **Leakage checks:** time-ordered split and horizon-specific features.
- **DON'Ts respected:** no fare changes, no infrastructure proposals, no trip cuts; driver rest, vehicle types and equity protected.
- **No consumer app:** the passenger advisory is a message aid for RTA staff, not a public trip planner (DO #19).

## Next steps

The biggest gain comes from more days of data; the Flow is built to rerun on them without redesign.

1. **Load several weeks of Nol and running-time data** to learn weekday, weekend and event patterns, and to test the morning peak.
2. **Add on-board load from passenger counters** to confirm demand pressure before any swap is rolled out.
3. **Wire the 15-minute forecast into the decision recipe**, so high-pressure hours are flagged before they happen, and measure how many it catches.
4. **Match nearby stops, not only identical stop pairs**, to find more alternative routes.
5. **Automate the daily run:** a Dataiku Scenario that rebuilds the Flow and sends the end-of-day report through an administrator-approved channel.
6. **Move the agents to native Dataiku Agents** with read-only dataset tools, keeping the number checker in front of the dashboard.
7. **Check route codes** that may be tram or ferry services and separate them from bus demand.

## Appendix: Dataiku Flow inventory by zone

The Flow holds 71 objects (39 datasets, 30 recipes, 2 saved models) in 7 zones.

| Zone | Recipes | Key outputs |
| --- | --- | --- |
| Source Data | none (4 linked catalogue datasets) | DATA.nol_card_details_15-Dec-2025, DATA.Running_time_15-Dec-2025, DATA.Fleet_List, DATA.stops |
| Data Cleaning & Quality | 3 Prepare, 3 Group | nol_taps_clean, runtime_events_clean, fleet_clean, dq_nol_date_tap_counts, dq_nol_route_counts, dq_runtime_date_counts |
| Demand Aggregation & Preparation | Prepare, Group x3, Sample, Join x2, Prepare | nol_taps_slotted, route_slot15_demand, route_day_demand, forecast_routes, slot_list, route_slot_grid, demand_grid_joined, demand_zero_filled |
| Forecasting & Evaluation | Window, Prepare, Split, Train x2, Score x2, Python | forecast_features_raw, forecast_features_ready, features_train, features_test, models forecast_h1 and forecast_h4, scored_test_h1, scored_test_h4, forecast_metrics |
| Fleet & Route Operations | Group, Python | fleet_capacity_lookup, route_hour_decisions, route_evidence_card, decision_summary |
| Crowding & Operational Reporting | Python | stop_hour_crowding, segment_hotspots, alt_route_candidates, daily_ops_report, ops_summary |
| AI Decision Support | Python, Prompt, Prepare, Prompt, Python | agent_cases, agent_specialist_out, agent_specialist_clean, agent_decision_cards, agent_checks |

**Webapps:** DemandPulse Ops (live, Python backend reading nine datasets plus the two agent datasets) and DemandPulse Team7 (planning snapshot).

**Visual ML analyses:** forecast_h1_15min (15-minute model) and a copy configured for the 60-minute model, each with a Ridge, Random forest and XGBoost session on the explicit time split.
