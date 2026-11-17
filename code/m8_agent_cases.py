# Dataiku Python recipe: build_agent_cases   (Milestone 8: case file for the AI agents)
# Inputs : segment_hotspots, alt_route_candidates, route_hour_decisions, route_evidence_card
# Output : agent_cases   (12 rows: facts as text, a rule-based suggestion, and the specialist role)
# Summary text only: route codes, stop names, numbers. No card or driver identifiers. The LLM never computes numbers.
import dataiku
import numpy as np
import pandas as pd

ds = dataiku.Dataset


def hh(h):
    return f"{int(h):02d}:00"


def hrs(hours):
    hours = sorted(set(int(h) for h in hours))
    out, start, prev = [], hours[0], hours[0]
    for h in hours[1:] + [None]:
        if h is not None and h == prev + 1:
            prev = h
            continue
        out.append(hh(start) if start == prev else f"{hh(start)}-{hh(prev)}")
        if h is not None:
            start = prev = h
    return ", ".join(out)


def as_bool(s):
    return s.astype(str).str.lower().eq("true")


hs = ds("segment_hotspots").get_dataframe()
alts = ds("alt_route_candidates").get_dataframe()
rhd = ds("route_hour_decisions").get_dataframe()
rc = ds("route_evidence_card").get_dataframe()
rhd["is_large_vehicle"] = as_bool(rhd["is_large_vehicle"])
for c in ["from_stop", "to_stop"]:
    hs[c] = pd.to_numeric(hs[c], errors="coerce")
    if len(alts):
        alts[c] = pd.to_numeric(alts[c], errors="coerce")

CONG = "the congestion and reliability specialist"
SUPP = "the supply-demand specialist"
rows = []

# ---------- 5 congested corridors (hours grouped, so the same stop pair is one case) ----------
grp = []
for (route, fs, ts), g in hs.groupby(["Route", "from_stop", "to_stop"]):
    worst = g.sort_values("pax_delay_min", ascending=False).iloc[0]
    grp.append(dict(route=route, fs=fs, ts=ts, g=g, worst=worst, pax=g["pax_delay_min"].sum(),
                    board=g["boardings_from"].sum(), mn=g["median_extra_s"].min(), mx=g["median_extra_s"].max()))
grp = sorted(grp, key=lambda x: x["pax"], reverse=True)[:5]
for c in grp:
    w = c["worst"]
    span = f"{c['mx']:.0f}" if round(c["mn"]) == round(c["mx"]) else f"{c['mn']:.0f} to {c['mx']:.0f}"
    facts = (f"Route {c['route']}: stop pair {w['from_name']} to {w['to_name']}. Buses ran {span} seconds "
             f"slower than scheduled (median) at {hrs(c['g']['hour'])}; worst at {hh(w['hour'])} with {int(w['n_trips'])} trips and a 90th "
             f"percentile of {w['p90_extra_s']:.0f} seconds. About {c['board']:.0f} passengers boarded at the start of the segment across "
             f"these hours. Straight-line speed proxy {w['median_speed_kmh']:.1f} km/h at the worst hour (unreliable for short segments).")
    a = alts[(alts["hotspot_route"] == c["route"]) & (alts["from_stop"] == c["fs"]) & (alts["to_stop"] == c["ts"])] if len(alts) else alts
    if len(a):
        b = a.sort_values("alt_extra_s").iloc[0]
        extra = "on or ahead of schedule" if b["alt_extra_s"] <= 0 else f"{b['alt_extra_s']:.0f} seconds over schedule"
        facts += (f" Candidate alternative on the same stop pair: route {b['alt_route']} at {hh(b['hour'])} ({extra}, demand pressure "
                  f"{b['alt_pressure']:.2f}, {int(b['alt_trips'])} trips).")
        act = f"Hold a standby bus on route {b['alt_route']} for that hour and advise passengers; confirm a spare bus and a rested driver."
    else:
        facts += " No alternative route was found on the same stop pair."
        act = "Review the timetable and dispatch headway for these hours; the delay can come from traffic or from an unrealistic timetable."
    rows.append(dict(case_type="CORRIDOR", route=c["route"], specialist=CONG, facts=facts, rule_action=act,
                     task="Explain what this delay means for passengers, say whether the data can tell traffic from timetable error, and name one operational step."))

# ---------- 3 crowded route-hours and 2 spare-capacity route-hours ----------
hp = rhd[rhd["capacity_flag"] == "HIGH_PRESSURE"].sort_values("demand_pressure", ascending=False).head(3)
for _, r in hp.iterrows():
    rows.append(dict(case_type="CROWDING", route=r["Route"], specialist=SUPP,
        facts=(f"Route {r['Route']} at {hh(r['hour'])}: {r['boardings']:.0f} boardings, {r['trips']:.0f} trip(s), demand pressure {r['demand_pressure']:.2f} "
               f"boardings per offered seat (a screening proxy, not on-board load). Average vehicle capacity {r['avg_vehicle_capacity']:.0f} seats."),
        rule_action=str(r["recommended_action"]),
        task="Explain the demand pressure and recommend one capacity step that keeps every trip."))
un = rhd[(rhd["capacity_flag"] == "UNDER_USED") & rhd["is_large_vehicle"]].sort_values("demand_pressure").head(2)
for _, r in un.iterrows():
    rows.append(dict(case_type="SPARE", route=r["Route"], specialist=SUPP,
        facts=(f"Route {r['Route']} at {hh(r['hour'])}: {r['boardings']:.0f} boardings, {r['trips']:.0f} trip(s), demand pressure only {r['demand_pressure']:.2f} "
               f"boardings per offered seat on a large bus (average {r['avg_vehicle_capacity']:.0f} seats)."),
        rule_action="Run a standard bus instead of a large one if a busier hour needs the large bus; keep every trip.",
        task="Explain why this hour has spare capacity and whether the large bus could serve a busier hour without cutting any trip."))

# ---------- 2 least reliable routes ----------
for _, r in rc.sort_values("unreliable_hours", ascending=False).head(2).iterrows():
    rows.append(dict(case_type="RELIABILITY", route=r["Route"], specialist=CONG,
        facts=(f"Route {r['Route']}: {int(r['unreliable_hours'])} route-hours where 30 percent or more of timed departures were more than 5 minutes late; "
               f"median delay across hours {r['median_delay_s']:.0f} seconds; busiest hour {hh(r['peak_hour'])}; {r['boardings_day']:.0f} boardings that day."),
        rule_action="Review the scheduled running time and recovery buffer for the affected hours.",
        task="Explain the reliability problem for passengers and name one operational fix such as a running-time buffer or headway control."))

out = pd.DataFrame(rows)
out.insert(0, "case_id", [f"C{i + 1:02d}" for i in range(len(out))])
out["role"] = out["specialist"]
ds("agent_cases").write_with_schema(out[["case_id", "case_type", "route", "role", "task", "facts", "rule_action"]])
