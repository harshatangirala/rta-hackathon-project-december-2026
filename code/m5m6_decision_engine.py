# Dataiku Python recipe: compute_route_hour_decisions   (Milestones 5 + 6)
# Inputs : route_slot15_demand, runtime_events_clean, fleet_capacity_lookup
# Outputs: route_hour_decisions, route_evidence_card, decision_summary
# All numbers are deterministic rules on ACTUAL 15 Dec 2025 data. No LLM computes anything.
import dataiku
import numpy as np
import pandas as pd

# ---------- Rule parameters (ASSUMPTIONS - state them in the report) ----------
UNDER_USED_MAX = 0.25     # boardings per offered place per hour; conservative because peak load <= boardings
HIGH_PRESSURE_MIN = 1.00  # screening flag only: passenger turnover means this is NOT proof of crowding
LATE_SEC = 300            # a departure more than 5 min late counts as late
UNRELIABLE_SHARE = 0.30   # >= 30% of timed departures late in that route-hour
MIN_EVENTS = 20           # need >= 20 timed departures before judging reliability
LARGE_CAP = 100           # total capacity >= 100 = articulated / double-deck class
DONOR_MAX_AFTER = 0.50    # a donor route-hour must stay <= 0.50 after giving up its large bus


def first_col(df, prefix):
    hits = [c for c in df.columns if c.lower().startswith(prefix.lower())]
    if not hits:
        raise KeyError(f"No column starting with '{prefix}' in {list(df.columns)}")
    return hits[0]


# ---------- Demand: observed boardings per route-hour ----------
dem = dataiku.Dataset("route_slot15_demand").get_dataframe()
dem["Route"] = dem["Route"].astype(str).str.strip()
dem["hour"] = (dem["slot15"] // 4).astype(int)
dem = dem.groupby(["Route", "hour"], as_index=False).agg(
    boardings=("CKI_sum", "sum"), alightings=("CKO_sum", "sum"))

# ---------- Fleet capacity lookup (one row per bus) ----------
fl = dataiku.Dataset("fleet_capacity_lookup").get_dataframe()
fl = fl.rename(columns={first_col(fl, "Total"): "capacity",
                        first_col(fl, "Bus_Type"): "bus_type",
                        first_col(fl, "vehicle_class"): "vehicle_class"})
fl = fl[["Body_number", "capacity", "bus_type", "vehicle_class"]].copy()
fl["Body_number"] = pd.to_numeric(fl["Body_number"], errors="coerce")
fl["capacity"] = pd.to_numeric(fl["capacity"], errors="coerce")
# capacity 0 means "unknown", not "empty bus"; non-buses never carry passengers
fl.loc[(fl["capacity"] <= 0) | (fl["vehicle_class"] != "BUS"), "capacity"] = np.nan
fl = fl.dropna(subset=["Body_number"])
assert fl["Body_number"].is_unique, "fleet_capacity_lookup must have one row per bus"

# ---------- Supply and reliability from actual running times ----------
rt = dataiku.Dataset("runtime_events_clean").get_dataframe(
    columns=["Route", "Trip_ID", "Body", "OP_Hour", "Diff_in_seconds"])
rt["Route"] = rt["Route"].astype(str).str.strip()
rt["Body"] = pd.to_numeric(rt["Body"], errors="coerce")
rt["hour"] = pd.to_numeric(rt["OP_Hour"], errors="coerce")
rt["delay_s"] = pd.to_numeric(rt["Diff_in_seconds"], errors="coerce")
events_outside_0_23 = int(((rt["hour"] < 0) | (rt["hour"] >= 24) | rt["hour"].isna()).sum())
rt = rt[(rt["hour"] >= 0) & (rt["hour"] < 24)].copy()
rt["hour"] = rt["hour"].astype(int)

n_before = len(rt)
rt = rt.merge(fl, how="left", left_on="Body", right_on="Body_number")
assert len(rt) == n_before, "Fleet join multiplied rows - stop and check fleet_capacity_lookup"
fleet_match_rate = float(rt["Body_number"].notna().mean())
capacity_valid_rate = float(rt["capacity"].notna().mean())

trip = rt.groupby(["Route", "hour", "Trip_ID"], as_index=False).agg(capacity=("capacity", "max"))
global_median_cap = trip["capacity"].median()
trip["capacity_imputed"] = trip["capacity"].isna()
trip["capacity"] = (trip["capacity"]
                    .fillna(trip.groupby("Route")["capacity"].transform("median"))
                    .fillna(global_median_cap))
sup = trip.groupby(["Route", "hour"], as_index=False).agg(
    trips=("Trip_ID", "nunique"),
    capacity_offered=("capacity", "sum"),
    avg_vehicle_capacity=("capacity", "mean"),
    share_capacity_imputed=("capacity_imputed", "mean"))

timed = rt.dropna(subset=["delay_s"]).copy()
timed["late"] = timed["delay_s"] > LATE_SEC
rel = timed.groupby(["Route", "hour"], as_index=False).agg(
    timed_departures=("delay_s", "size"),
    median_delay_s=("delay_s", "median"),
    share_late_5min=("late", "mean"))

# ---------- Route-hour evidence and rule flags ----------
rh = dem.merge(sup, on=["Route", "hour"], how="left").merge(rel, on=["Route", "hour"], how="left")
rh["has_supply"] = rh["capacity_offered"].fillna(0) > 0
rh["demand_pressure"] = np.where(rh["has_supply"], rh["boardings"] / rh["capacity_offered"], np.nan)
rh["is_large_vehicle"] = rh["avg_vehicle_capacity"].fillna(0) >= LARGE_CAP


def capacity_flag(r):
    if not r["has_supply"]:
        return "NO_SUPPLY_MATCH"
    if r["demand_pressure"] >= HIGH_PRESSURE_MIN:
        return "HIGH_PRESSURE"
    if r["demand_pressure"] <= UNDER_USED_MAX and r["trips"] >= 2:
        return "UNDER_USED"
    return "OK"


rh["capacity_flag"] = rh.apply(capacity_flag, axis=1)
rh["reliability_flag"] = np.where(
    (rh["timed_departures"].fillna(0) >= MIN_EVENTS) & (rh["share_late_5min"].fillna(0) >= UNRELIABLE_SHARE),
    "UNRELIABLE", "OK")


def action(r):
    acts = []
    if r["capacity_flag"] == "HIGH_PRESSURE":
        acts.append("Add a standby or short-turn trip if a spare bus and rested driver exist; confirm on-board load"
                    if r["is_large_vehicle"] else
                    "Use a larger bus (articulated/double) at this hour; keep frequency; confirm on-board load")
    elif r["capacity_flag"] == "UNDER_USED":
        acts.append("Run a standard bus instead of a large one; keep every trip (no frequency cut)"
                    if r["is_large_vehicle"] else "Keep service unchanged (network equity); monitor")
    if r["reliability_flag"] == "UNRELIABLE":
        acts.append("Review the scheduled running time / recovery buffer for this hour")
    return " | ".join(acts) if acts else "No change"


rh["recommended_action"] = rh.apply(action, axis=1)

# ---------- Cost-neutral swap scenario: same buses, same trips, same hour ----------
rh["swap_role"] = ""
rh["capacity_after_swap"] = rh["capacity_offered"]
places_moved = 0.0
for hour, g in rh[rh["has_supply"]].groupby("hour"):
    receivers = g[(g["capacity_flag"] == "HIGH_PRESSURE") & (~g["is_large_vehicle"])] \
        .sort_values("demand_pressure", ascending=False)
    donor_idx = list(g[(g["capacity_flag"] == "UNDER_USED") & (g["is_large_vehicle"])]
                     .sort_values("demand_pressure").index)
    for ri in receivers.index:
        while donor_idx:
            di = donor_idx.pop(0)
            gain = rh.at[di, "avg_vehicle_capacity"] - rh.at[ri, "avg_vehicle_capacity"]
            new_donor_cap = rh.at[di, "capacity_after_swap"] - gain
            if gain > 0 and new_donor_cap > 0 and rh.at[di, "boardings"] / new_donor_cap <= DONOR_MAX_AFTER:
                rh.at[ri, "capacity_after_swap"] += gain
                rh.at[di, "capacity_after_swap"] = new_donor_cap
                rh.at[ri, "swap_role"] = "RECEIVER"
                rh.at[di, "swap_role"] = "DONOR"
                places_moved += gain
                break
rh["demand_pressure_after_swap"] = np.where(
    rh["has_supply"], rh["boardings"] / rh["capacity_after_swap"], np.nan)

# ---------- One row per route for the agents and the HTML page ----------
m = rh[rh["has_supply"]]
card = m.groupby("Route").agg(
    boardings_day=("boardings", "sum"),
    peak_hour=("boardings", lambda s: int(m.loc[s.idxmax(), "hour"])),
    max_demand_pressure=("demand_pressure", "max"),
    high_pressure_hours=("capacity_flag", lambda s: int((s == "HIGH_PRESSURE").sum())),
    under_used_hours=("capacity_flag", lambda s: int((s == "UNDER_USED").sum())),
    unreliable_hours=("reliability_flag", lambda s: int((s == "UNRELIABLE").sum())),
    median_delay_s=("median_delay_s", "median"),
    avg_vehicle_capacity=("avg_vehicle_capacity", "mean"),
    swap_receiver_hours=("swap_role", lambda s: int((s == "RECEIVER").sum())),
    swap_donor_hours=("swap_role", lambda s: int((s == "DONOR").sum())),
).reset_index()


def commentary(r):
    parts = [f"Route {r['Route']}: {int(r['boardings_day'])} boardings on 15 Dec 2025, busiest hour {int(r['peak_hour']):02d}:00."]
    if r["high_pressure_hours"] > 0:
        parts.append(f"{r['high_pressure_hours']} hour(s) with high demand pressure (max {r['max_demand_pressure']:.2f}): "
                     "consider a larger bus at those hours and confirm on-board load.")
    if r["under_used_hours"] > 0:
        parts.append(f"{r['under_used_hours']} hour(s) under-used: right-size the vehicle, keep all trips.")
    if r["unreliable_hours"] > 0:
        parts.append(f"{r['unreliable_hours']} hour(s) with >= 30% of departures over 5 min late: review running-time buffers.")
    if len(parts) == 1:
        parts.append("No change suggested.")
    return " ".join(parts)


card["rule_based_commentary"] = card.apply(commentary, axis=1)
card["commentary_source"] = "RULE-BASED (deterministic, not LLM)"
card = card.sort_values("boardings_day", ascending=False)

# ---------- Summary (key, value) for the report and HTML ----------
recv = rh[rh["swap_role"] == "RECEIVER"]
summary = {
    "route_hours_with_demand": len(rh),
    "route_hours_matched_to_runtime": int(rh["has_supply"].sum()),
    "routes_with_demand": rh["Route"].nunique(),
    "routes_matched_to_runtime": rh.loc[rh["has_supply"], "Route"].nunique(),
    "runtime_events_used": len(rt),
    "runtime_events_hour_outside_0_23": events_outside_0_23,
    "fleet_match_rate_pct": round(100 * fleet_match_rate, 1),
    "valid_capacity_rate_pct": round(100 * capacity_valid_rate, 1),
    "high_pressure_route_hours": int((rh["capacity_flag"] == "HIGH_PRESSURE").sum()),
    "under_used_route_hours": int((rh["capacity_flag"] == "UNDER_USED").sum()),
    "unreliable_route_hours": int((rh["reliability_flag"] == "UNRELIABLE").sum()),
    "boardings_in_high_pressure_hours_pct": round(
        100 * rh.loc[rh["capacity_flag"] == "HIGH_PRESSURE", "boardings"].sum() / rh["boardings"].sum(), 1),
    "scenario_swaps": len(recv),
    "scenario_receivers_below_threshold_after": int((recv["demand_pressure_after_swap"] < HIGH_PRESSURE_MIN).sum()),
    "scenario_places_moved_total": round(places_moved, 0),
    "scenario_trips_removed": 0,
    "param_under_used_max": UNDER_USED_MAX,
    "param_high_pressure_min": HIGH_PRESSURE_MIN,
    "param_late_sec": LATE_SEC,
    "param_unreliable_share": UNRELIABLE_SHARE,
    "param_large_capacity": LARGE_CAP,
    "param_donor_max_after": DONOR_MAX_AFTER,
}
summary_df = pd.DataFrame({"metric": list(summary.keys()), "value": [float(v) for v in summary.values()]})

dataiku.Dataset("route_hour_decisions").write_with_schema(rh)
dataiku.Dataset("route_evidence_card").write_with_schema(card)
dataiku.Dataset("decision_summary").write_with_schema(summary_df)
