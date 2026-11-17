# Dataiku Standard webapp: PYTHON tab (backend). Serves the project's aggregate datasets as JSON to the HTML page.
# Reads only summary datasets (no card or driver identifiers). `app` is provided by Dataiku.
import json
import dataiku
import pandas as pd
from flask import Response

_cache = {}


def _load(name):
    if name not in _cache:
        _cache[name] = dataiku.Dataset(name).get_dataframe()
    return _cache[name]


def _json(df):
    return Response(df.to_json(orient="records"), mimetype="application/json")


def _kv(name):
    df = _load(name)
    return {str(m): (None if pd.isna(v) else float(v)) for m, v in zip(df["metric"], df["value"])}


@app.route("/api/summary")
def api_summary():
    body = json.dumps({"ops": _kv("ops_summary"), "dec": _kv("decision_summary")})
    return Response(body, mimetype="application/json")


@app.route("/api/forecast")
def api_forecast():
    return _json(_load("forecast_metrics"))


@app.route("/api/hotspots")
def api_hotspots():
    return _json(_load("segment_hotspots"))


@app.route("/api/alternatives")
def api_alternatives():
    return _json(_load("alt_route_candidates"))


@app.route("/api/report")
def api_report():
    return _json(_load("daily_ops_report"))


@app.route("/api/stops")
def api_stops():
    df = _load("stop_hour_crowding")
    df = df[df["has_coords"].astype(str).str.lower().eq("true")]
    df = df.sort_values("boardings", ascending=False).groupby("hour").head(300)
    return _json(df[["Stop_Id", "hour", "boardings", "alightings", "stop_name", "stop_lat", "stop_lon"]])


@app.route("/api/routes")
def api_routes():
    cols = ["Route", "boardings_day", "peak_hour", "max_demand_pressure", "high_pressure_hours",
            "under_used_hours", "unreliable_hours", "median_delay_s", "avg_vehicle_capacity"]
    return _json(_load("route_evidence_card")[cols])


@app.route("/api/route_hours")
def api_route_hours():
    cols = ["Route", "hour", "boardings", "trips", "avg_vehicle_capacity", "median_delay_s", "share_late_5min",
            "has_supply", "demand_pressure", "is_large_vehicle", "capacity_flag", "reliability_flag", "recommended_action"]
    return _json(_load("route_hour_decisions")[cols])


@app.route("/api/agent_checks")
def api_agent_checks():
    return _json(_load("agent_checks"))


@app.route("/api/agent_cases")
def api_agent_cases():
    return _json(_load("agent_cases")[["case_id", "case_type", "route", "facts", "rule_action"]])


@app.route("/api/refresh")
def api_refresh():
    _cache.clear()
    return Response(json.dumps({"ok": True}), mimetype="application/json")
