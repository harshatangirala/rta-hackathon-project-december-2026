# Evidence and Schema (verified from screenshots + hackathon docs)

Last updated: 2026-11-16 (first pass, all 36 screenshots read).
Rule: only fields seen in a screenshot are listed. "Not seen" = may exist, unverified.
All catalog datasets live in Dataiku project key `DATA` (preview titles read `DATA.<name>`).
In every preview, storage type = `string`; the blue label is Dataiku's *inferred meaning*.
**No row counts are known yet.** Get them in Dataiku (dataset > Status > Compute).

## 1. Source files
| Source | Path | Used for |
|---|---|---|
| Mission slide | Downloads/The Hackathon Mission.png | 4 mission pillars, required output |
| Evaluation rubric | Downloads/Hackathon_Evaluation_Criteria.png | scoring (5 x 20 pts) |
| Data toolkit slide | Downloads/The Data Tool Kit for the Hackathon.png | intended field lists |
| Survival guide | Downloads/Dataiku_RTA_Hackathon_Guide.pdf | 25 DOs, 21 DON'Ts |
| Asset descriptions | Downloads/ASSET NAME & DESCRIPTION.md | dataset meaning + period |
| Schema screenshots | OneDrive/Pictures/Screenshots/Screenshot 2026-11-16 1908xx–1922xx.png (36) | fields below |

## 2. Scoring and rules that shape the design
Rubric (20 pts each): 1 Practical application. 2 Documentation and visuals. 3 Innovation.
4 AI model (selection, train/test separation, explainability). 5 **Forecast accuracy
(MAE/MAPE/RMSE on held-out data, gain vs naive baseline, accuracy across horizons and at peaks).**

Binding guide rules: visual recipes first; Flow Zones + recipe descriptions; clear dataset names;
wiki; hash/mask/drop PII before any LLM; no data off-platform; all compute inside Dataiku;
check for leakage; no fare increases; no infrastructure proposals; keep network equity
(no cutting access); respect driver rest and shift limits; treat bus types differently;
do not overwrite raw catalog datasets; coordinate before heavy builds; use sampling while developing.

## 3. Period constraint (non-negotiable)
- Nol + Running_time = **actual observations, one day: Mon 15 Dec 2025** (runtime Day_type = "Mon-Wed").
- GTFS = **planned services 11 Sep – 31 Dec 2026** (calendar start_date 20260911, end_date 20261231).
- Never compare them as the same period. Any 2025-demand-vs-2026-plan view is a labelled
  **assumption scenario** ("if the Dec-2025 Monday profile held in 2026").
- One observed day → forecasting is **intraday, short-horizon** (15–60 min ahead). No multi-day,
  weekly or seasonal claims. No holiday/event effects can be learned.

## 4. Datasets and fields

### 4.1 nol_card_details_15-Dec-2025 (RTA NOL, actual) — demand
| Field | Observed format / meaning | Use |
|---|---|---|
| Transaction_date | "15-DEC-25" | constant; check only |
| Transaction_Time | "HH:MM" (minute resolution) | time bin |
| Body_EVD_ID | "B<digits>_EVD_<nn>" | extract bus body number → fleet join |
| device_id | integer | not needed |
| device_id_hex | mixed hex; Dataiku mis-reads some as decimal/scientific | **drop** |
| NOL_ID | card identifier | **PII → drop immediately** |
| CKI | 0/1 | 1 = check-in (boarding) |
| CKO | 0/1 | 1 = check-out (alighting) |
| Route | bus route code (F23, C03, E101, 13, 106…); **some rows empty** | demand key |
| Stop_name | text | labels |
| Amount | decimal; positive, negative and 0 values seen | **not used** (meaning undocumented) |
| Stop_Id | 6-digit numeric | stop key |
Quality flags: Route meaning is locked to *Decimal* in the catalog, so alphanumeric codes show as
invalid (red). The storage is string, so nothing is lost; set meaning to Text in our Prepare recipe.
Rows with empty Route need counting and excluding from route-level demand.

### 4.2 Running_time_15-Dec-2025 (RTA Operations, actual) — supply + reliability
Date ("15-DEC-2025"), Day_type ("Mon-Wed"), Body (integer), Trip_ID, Route (e.g. F47),
Driver_id (**PII → drop**), Direction, Stop_Seq (starts at 0), Stop_ID, Stop_Name,
Sched_Arr, Act_Arr, Sched_Dep, Act_Dep ("HH:MM:SS"), Difference ("HH:MM:SS"),
Door_Satus [sic] ("Door Open", "Drive Through"), block_no, avm_pattern_id,
Trip_end (empty in preview), Diff_in_seconds (integer), OP_Hour ("05", text), TID.
Verified on preview rows: Difference = Act_Dep − Sched_Dep; Diff_in_seconds = same value in seconds.
**Unknown:** how early departures are encoded (negative or absolute?). Recompute a signed delay
ourselves from Sched_Dep/Act_Dep and compare.

### 4.3 Fleet_List (RTA Fleet) — capacity
Body_number, Manufacturer (MAN, MERCEDES, VDL, OPTARE seen), Bus_Type (STANDARD, ARTICULATED,
DOUBLE, MIDI seen; COACH listed in toolkit), Model Year, Operator (PUBLIC-BUSES, INTER-CITY seen),
No_of_Seats, RTA Standing (not verified), Total.
Quality: some rows have Standing = 0 and Seats = Total, so Seats sometimes holds total capacity.
→ Use **Total** as capacity and treat Standing as unverified.
**No propulsion (electric/diesel) field was seen**, so make no EV claims from data.

### 4.4 GTFS (OPS GTFS, planned Sep–Dec 2026)
- routes: route_id, agency_id, route_short_name, route_long_name, route_type, route_color,
  route_text_color. route_type 1 = metro (MRed1, MRed2, MGrn), 0 = tram (T1), 3 = bus.
  Rail rows have string route_id (e.g. "11-MRe-2-y08-1") and empty long name.
- trips: route_id, service_id, trip_id, shape_id, trip_headsign, direction_id, block_id (empty),
  trip_short_name (empty). More columns to the right: not seen.
- stop_times: trip_id, arrival_time, departure_time (HH:MM:SS), stop_id, stop_sequence,
  stop_headsign (empty), pickup_type, drop_off_type, shape_dist_traveled. Preview showed rail trips only.
- stops: stop_id, stop_name, stop_lat, stop_lon, zone_id ("0005"), location_type (empty), stop_code,
  stop_desc (empty), stop_url (empty), platform_code. Rail stop ids are 5-digit; bus stop ids appear
  6-digit (seen in Nol/runtime/transfers).
- calendar: service_id (alpha codes like US/UL/T2/TA and numeric 1,4,5,6), monday..sunday (0/1),
  start_date, end_date (YYYYMMDD).
- calendar_dates: service_id, date, exception_type. **Preview showed no rows.**
- frequencies: trip_id (e.g. "3352:3:18000:9003:1"), start_time, end_time, headway_secs (600 seen),
  exact_times. Preview ~10 rows (may be a small table).
- shapes: shape_id, shape_pt_lat, shape_pt_lon, shape_pt_sequence, shape_dist_traveled (units not stated).
- transfers: from_stop_id, to_stop_id, transfer_type (2, 3 seen), min_transfer_time (sec; empty for
  type 3). Contains **bus-stop ↔ metro-station links**, which supports feeder analysis.
- agency (1 row, RTA, Asia/Dubai), feed_info (3 columns only: publisher name, url, lang),
  translations (Arabic headsigns; not needed).

### 4.5 Communities (RTA Geographic)
- community_2026-10-20_09-28-00: snippet (empty), name ("kml_1"…), description (HTML table string),
  id, ExtendedData (JSON array of SchemaData/SimpleData values), Polygon (JSON:
  outerBoundaryIs → LinearRing → coordinates). Geometry needs parsing into WKT before a geo join.
- Communities_2026-11-09_attribute-details (dictionary): c_prefix_a/e, cname_a/e (names),
  comm_num (PK), community_a/e, dgis_id (PK), label_a/e, ndgis_id, objectid, shape (GEOMETRY),
  shape.area, shape.len. Mapping of these names to ExtendedData positions: **unverified**.

## 5. Candidate join keys (validate match rate before relying on them)
| Join | Keys | Risk |
|---|---|---|
| Nol ↔ Runtime | Route; Stop_Id = Stop_ID | formats look aligned |
| Nol → Fleet | digits from Body_EVD_ID ("B2256_EVD_03" → 2256) = Body_number | assumption, check rate |
| Runtime → Fleet | Body = Body_number | assumption, check rate |
| 2025 data ↔ GTFS | Route = routes.route_short_name; Stop_Id = stops.stop_id | **different periods** (scenario only) |
| GTFS internal | standard GTFS keys | standard |
| Stops → Communities | point-in-polygon after parsing Polygon JSON | stretch goal |

## 6. Open questions to check in Dataiku (first 15 min)
1. Row counts of Nol, Runtime, Fleet, stop_times.
2. Share of Nol rows with empty Route; CKI/CKO combos (both 0? both 1?).
3. Diff_in_seconds min/max and sign of early departures.
4. Fleet join rate from Runtime.Body and Nol body digits.
5. Route code overlap: Nol vs Runtime vs GTFS route_short_name.
6. LLM connection available (Prompt recipe LLM list) and whether "Agents" exist in this DSS version.

## 7. Data-handling caution
The screenshots in OneDrive contain raw rows (including card-ID and driver-ID columns). Guide rule
DON'T #8 forbids moving hackathon data to personal or cloud storage. Ask a mentor whether these
screenshots are acceptable, and delete them after the event. This repo holds **schema only**.
Never paste raw rows here.
