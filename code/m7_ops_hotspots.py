# Dataiku Python recipe: compute_ops_hotspots   (Milestone 7: congestion, alternatives, daily report)
# Inputs : nol_taps_slotted, runtime_events_clean, route_hour_decisions, DATA.stops
# Outputs: stop_hour_crowding, segment_hotspots, alt_route_candidates, daily_ops_report, ops_summary
# ACTUAL 15 Dec 2025 data only. Stop coordinates come from the GTFS stops file and are used ONLY to locate stops.
# All numbers are deterministic. No LLM computes anything. Speeds use straight-line distance (a relative proxy).
import dataiku
import numpy as np
import pandas as pd

# ---------- Parameters (ASSUMPTIONS - state them in the report) ----------
MIN_TRIPS = 5          # trips needed on a route-segment-hour to judge it
ALT_MIN_TRIPS = 3      # trips needed to trust an alternative route on the same stop pair
MIN_EXTRA_S = 30       # a segment counts as congested if buses run >= 30 s slower than scheduled (median)
TOP_N = 60             # hotspot segments kept
ALT_TOP = 30           # hotspots checked for alternatives
ALT_MAX_PRESSURE = 0.5 # an alternative route-hour must have spare seats (demand pressure <= 0.5)
ALT_EXTRA_RATIO = 0.5  # and run at most half the extra time of the hotspot
ds = dataiku.Dataset


def to_secs(s):
    p = s.astype(str).str.extract(r"^\s*(\d+):(\d+):(\d+)")
    return p[0].astype(float) * 3600 + p[1].astype(float) * 60 + p[2].astype(float)


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi, dl = p2 - p1, np.radians(lon2) - np.radians(lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * r * np.arcsin(np.sqrt(a))


def as_bool(s):
    return s.astype(str).str.lower().eq("true")


# ---------- Stop coordinates (location lookup only) ----------
stops = ds("DATA.stops").get_dataframe(columns=["stop_id", "stop_name", "stop_lat", "stop_lon"])
stops["stop_id"] = pd.to_numeric(stops["stop_id"], errors="coerce")
stops["stop_lat"] = pd.to_numeric(stops["stop_lat"], errors="coerce")
stops["stop_lon"] = pd.to_numeric(stops["stop_lon"], errors="coerce")
stops = stops.dropna(subset=["stop_id", "stop_lat", "stop_lon"]).drop_duplicates("stop_id").set_index("stop_id")

# ---------- Passenger crowding from Nol taps ----------
nol = ds("nol_taps_slotted").get_dataframe(columns=["Route", "Stop_Id", "Stop_name", "hour_of_day", "CKI", "CKO"])
nol["Route"] = nol["Route"].astype(str).str.strip()
nol["Stop_Id"] = pd.to_numeric(nol["Stop_Id"], errors="coerce")
nol["hour"] = pd.to_numeric(nol["hour_of_day"], errors="coerce")
nol["CKI"] = pd.to_numeric(nol["CKI"], errors="coerce").fillna(0)
nol["CKO"] = pd.to_numeric(nol["CKO"], errors="coerce").fillna(0)
nol = nol.dropna(subset=["Stop_Id", "hour"])
nol["hour"] = nol["hour"].astype(int)
taps_with_coords_pct = round(100 * nol["Stop_Id"].isin(stops.index).mean(), 1)

crowd = nol.groupby(["Stop_Id", "hour"], as_index=False).agg(
    boardings=("CKI", "sum"), alightings=("CKO", "sum"), stop_name=("Stop_name", "first"))
crowd["stop_lat"] = crowd["Stop_Id"].map(stops["stop_lat"])
crowd["stop_lon"] = crowd["Stop_Id"].map(stops["stop_lon"])
crowd["has_coords"] = crowd["stop_lat"].notna()
board_rsh = nol.groupby(["Route", "Stop_Id", "hour"])["CKI"].sum().rename("boardings_from").reset_index()

# ---------- Congestion from running times: extra time between consecutive stops ----------
rt = ds("runtime_events_clean").get_dataframe(columns=[
    "Route", "Direction", "Trip_ID", "Stop_Seq", "Stop_ID", "Stop_Name",
    "Sched_Arr", "Act_Arr", "Sched_Dep", "Act_Dep"])
rt["Route"] = rt["Route"].astype(str).str.strip()
rt["Stop_Seq"] = pd.to_numeric(rt["Stop_Seq"], errors="coerce")
rt["Stop_ID"] = pd.to_numeric(rt["Stop_ID"], errors="coerce")
for c in ["Sched_Arr", "Act_Arr", "Sched_Dep", "Act_Dep"]:
    rt[c + "_s"] = to_secs(rt[c])
rt = rt.dropna(subset=["Stop_Seq", "Stop_ID"]).sort_values(["Route", "Direction", "Trip_ID", "Stop_Seq"])
names = rt.drop_duplicates("Stop_ID").set_index("Stop_ID")["Stop_Name"]
g = rt.groupby(["Route", "Direction", "Trip_ID"], sort=False, dropna=False)
rt["from_stop"] = g["Stop_ID"].shift(1)
rt["prev_seq"] = g["Stop_Seq"].shift(1)
rt["prev_act_dep"] = g["Act_Dep_s"].shift(1)
rt["prev_sched_dep"] = g["Sched_Dep_s"].shift(1)
actual = rt["Act_Arr_s"] - rt["prev_act_dep"]
sched = rt["Sched_Arr_s"] - rt["prev_sched_dep"]
actual = actual.where(actual >= -43200, actual + 86400)   # midnight wrap
sched = sched.where(sched >= -43200, sched + 86400)
ok = (rt["from_stop"].notna() & ((rt["Stop_Seq"] - rt["prev_seq"]) == 1)
      & actual.between(5, 3600) & sched.between(5, 3600))
events_total = int(rt["from_stop"].notna().sum())
ev = pd.DataFrame({
    "Route": rt.loc[ok, "Route"], "from_stop": rt.loc[ok, "from_stop"], "to_stop": rt.loc[ok, "Stop_ID"],
    "hour": ((rt.loc[ok, "prev_sched_dep"] // 3600) % 24).astype(int),
    "actual_s": actual[ok], "sched_s": sched[ok]})
ev["extra_s"] = ev["actual_s"] - ev["sched_s"]
ev["over60"] = ev["extra_s"] > 60
d_km = haversine_km(ev["from_stop"].map(stops["stop_lat"]), ev["from_stop"].map(stops["stop_lon"]),
                    ev["to_stop"].map(stops["stop_lat"]), ev["to_stop"].map(stops["stop_lon"]))
spd = d_km / (ev["actual_s"] / 3600)
ev["speed_kmh"] = spd.where((ev["actual_s"] >= 20) & (d_km >= 0.05) & (spd <= 120))

keys = ["Route", "from_stop", "to_stop", "hour"]
gg = ev.groupby(keys)
seg = gg.agg(n_trips=("extra_s", "size"), median_extra_s=("extra_s", "median"),
             share_over_60s=("over60", "mean"), median_speed_kmh=("speed_kmh", "median"),
             median_sched_s=("sched_s", "median")).reset_index()
seg["p90_extra_s"] = gg["extra_s"].quantile(0.9).values
seg_all = seg[seg["n_trips"] >= ALT_MIN_TRIPS].copy()
seg = seg[seg["n_trips"] >= MIN_TRIPS].copy()
seg = seg.merge(board_rsh, left_on=["Route", "from_stop", "hour"], right_on=["Route", "Stop_Id", "hour"], how="left").drop(columns=["Stop_Id"])
seg["boardings_from"] = seg["boardings_from"].fillna(0)
seg["pax_delay_min"] = seg["boardings_from"] * seg["median_extra_s"].clip(lower=0) / 60.0
hot = seg[seg["median_extra_s"] >= MIN_EXTRA_S].sort_values("pax_delay_min", ascending=False)
top = hot.head(TOP_N).copy()
top["from_name"] = top["from_stop"].map(names)
top["to_name"] = top["to_stop"].map(names)
for side, col in [("from", "from_stop"), ("to", "to_stop")]:
    top[side + "_lat"] = top[col].map(stops["stop_lat"])
    top[side + "_lon"] = top[col].map(stops["stop_lon"])
top["has_coords"] = top["from_lat"].notna() & top["to_lat"].notna()
top.insert(0, "rank", range(1, len(top) + 1))

# ---------- Supply and demand context ----------
rhd = ds("route_hour_decisions").get_dataframe()
rhd["Route"] = rhd["Route"].astype(str).str.strip()
rhd["hour"] = pd.to_numeric(rhd["hour"], errors="coerce")
rhd["has_supply"] = as_bool(rhd["has_supply"])
rhd["is_large_vehicle"] = as_bool(rhd["is_large_vehicle"])

# ---------- Alternatives: other routes on the SAME stop pair, same hour, with spare seats and less delay ----------
h = top.head(ALT_TOP)[["rank", "Route", "from_stop", "to_stop", "hour", "median_extra_s"]].rename(
    columns={"Route": "hotspot_route", "median_extra_s": "hotspot_extra_s"})
alt = h.merge(seg_all[["Route", "from_stop", "to_stop", "hour", "n_trips", "median_extra_s"]]
              .rename(columns={"Route": "alt_route", "n_trips": "alt_trips", "median_extra_s": "alt_extra_s"}),
              on=["from_stop", "to_stop", "hour"])
alt = alt[alt["alt_route"] != alt["hotspot_route"]]
alt = alt.merge(rhd[["Route", "hour", "demand_pressure", "has_supply"]].rename(
    columns={"Route": "alt_route", "demand_pressure": "alt_pressure", "has_supply": "alt_has_supply"}),
    on=["alt_route", "hour"], how="left")
alt = alt[(alt["alt_has_supply"] == True) & (alt["alt_pressure"] <= ALT_MAX_PRESSURE)
          & (alt["alt_extra_s"] <= ALT_EXTRA_RATIO * alt["hotspot_extra_s"])]
alt = alt.sort_values(["rank", "alt_extra_s"]).groupby("rank").head(3).drop(columns=["alt_has_supply"])
alt["from_name"] = alt["from_stop"].map(names)
alt["to_name"] = alt["to_stop"].map(names)
if alt.empty:  # keep a valid schema even when nothing qualifies
    alt = pd.DataFrame(columns=["rank", "hotspot_route", "from_stop", "to_stop", "hour", "hotspot_extra_s", "alt_route",
                                "alt_trips", "alt_extra_s", "alt_pressure", "from_name", "to_name"])
hot_with_alt = int(alt["rank"].nunique()) if len(alt) else 0

# ---------- Daily operations report (rule-based text; label stays RULE-BASED) ----------
rep = []


def add(priority, section, headline, detail, evidence):
    rep.append({"priority": priority, "section": section, "headline": headline, "detail": detail,
                "evidence": evidence, "source": "RULE-BASED (deterministic, not LLM)"})


for _, r in top.head(5).iterrows():
    where = f"Route {r['Route']} from {r['from_name']} to {r['to_name']}, {int(r['hour']):02d}:00"
    a = alt[alt["rank"] == r["rank"]]
    if len(a):
        b = a.iloc[0]
        extra_txt = "on or ahead of schedule" if b["alt_extra_s"] <= 0 else f"{b['alt_extra_s']:.0f} s extra"
        act = (f"Brief dispatch to hold a standby bus on route {b['alt_route']} (same stop pair, {extra_txt}, "
               f"demand pressure {b['alt_pressure']:.2f}) and issue a passenger advisory for that hour.")
    else:
        act = "Review the running-time buffer and headway control for this hour; no same-corridor alternative route found."
    add("P1", "Congestion hotspot", where,
        f"Buses ran {r['median_extra_s']:.0f} s slower than scheduled on this stop pair (median over {int(r['n_trips'])} trips), "
        f"{int(r['boardings_from'])} passengers boarded at its start in that hour. {act}",
        f"pax_delay_min={r['pax_delay_min']:.0f}; n_trips={int(r['n_trips'])}; p90_extra_s={r['p90_extra_s']:.0f}")
hp = rhd[(rhd["capacity_flag"] == "HIGH_PRESSURE")].sort_values("demand_pressure", ascending=False).head(5)
for _, r in hp.iterrows():
    add("P2", "Supply-demand gap (crowding)", f"Route {r['Route']}, {int(r['hour']):02d}:00",
        f"Demand pressure {r['demand_pressure']:.2f} boardings per offered seat. {r['recommended_action']}",
        f"boardings={int(r['boardings'])}; trips={r['trips']}")
un = rhd[(rhd["capacity_flag"] == "UNDER_USED") & rhd["is_large_vehicle"]].sort_values("demand_pressure").head(5)
for _, r in un.iterrows():
    add("P3", "Supply-demand gap (spare capacity)", f"Route {r['Route']}, {int(r['hour']):02d}:00",
        f"Demand pressure only {r['demand_pressure']:.2f}. Candidate donor for the cost-neutral bus swap; keep every trip.",
        f"boardings={int(r['boardings'])}; trips={r['trips']}")
add("Check", "Guardrails", "Checked before any action is approved",
    "No fare change, no trip cut, no new infrastructure, driver rest and vehicle types respected, network equity kept.", "static checklist")
report = pd.DataFrame(rep)

# ---------- Summary ----------
summary = {
    "stops_in_nol": int(nol["Stop_Id"].nunique()),
    "stops_with_coords_pct": round(100 * pd.Index(nol["Stop_Id"].unique()).isin(stops.index).mean(), 1),
    "taps_with_coords_pct": taps_with_coords_pct,
    "segment_events_valid": len(ev),
    "segment_events_skipped": events_total - len(ev),
    "segment_hours_analysed": len(seg),
    "segment_hours_over_30s_pct": round(100 * (seg["median_extra_s"] >= MIN_EXTRA_S).mean(), 1) if len(seg) else 0.0,
    "hotspots_flagged": len(hot),
    "hotspots_kept": len(top),
    "hotspots_with_alternative_in_top": hot_with_alt,
    "median_speed_kmh_proxy": round(float(ev["speed_kmh"].median()), 1) if ev["speed_kmh"].notna().any() else 0.0,
    "param_min_trips": MIN_TRIPS, "param_min_extra_s": MIN_EXTRA_S, "param_alt_max_pressure": ALT_MAX_PRESSURE,
    "param_alt_extra_ratio": ALT_EXTRA_RATIO,
}
summary_df = pd.DataFrame({"metric": list(summary.keys()), "value": [float(v) for v in summary.values()]})

ds("stop_hour_crowding").write_with_schema(crowd)
ds("segment_hotspots").write_with_schema(top)
ds("alt_route_candidates").write_with_schema(alt)
ds("daily_ops_report").write_with_schema(report)
ds("ops_summary").write_with_schema(summary_df)
