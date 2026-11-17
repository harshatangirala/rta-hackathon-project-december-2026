# Dataiku Python recipe: compute_forecast_metrics   (Milestone 4-E)
# Inputs : scored_test_h1, scored_test_h4   (Score recipe outputs on features_test)
# Output : forecast_metrics
# Test half = slots 56-95 (14:00-23:59) of 15 Dec 2025. Models never saw these rows.
import dataiku
import numpy as np
import pandas as pd

MAPE_MIN_ACTUAL = 5  # MAPE only on slots with >= 5 actual boardings (MAPE is undefined at 0)

rows = []
for horizon_min, ds_name, naive_col in [(15, "scored_test_h1", "boardings_lag1"),
                                        (60, "scored_test_h4", "boardings_lag4")]:
    df = dataiku.Dataset(ds_name).get_dataframe()
    y_all = df["boardings"].astype(float).values
    preds = {
        # counts cannot be negative, so model output is clipped at 0 (disclosed)
        "model": np.clip(df["prediction"].astype(float).values, 0, None),
        # baseline = last value known at forecast time (15 min or 60 min earlier)
        "naive_last_known_slot": df[naive_col].astype(float).values,
    }
    for method, p_all in preds.items():
        for segment in ["ALL", "PM_PEAK", "OFF_PEAK"]:
            mask = np.ones(len(df), dtype=bool) if segment == "ALL" else (df["period"] == segment).values
            y, p = y_all[mask], p_all[mask]
            err = p - y
            nz = y >= MAPE_MIN_ACTUAL
            rows.append({
                "horizon_min": horizon_min,
                "method": method,
                "segment": segment,
                "n_rows": int(mask.sum()),
                "MAE": float(np.mean(np.abs(err))),
                "RMSE": float(np.sqrt(np.mean(err ** 2))),
                "MAPE_pct": float(100 * np.mean(np.abs(err[nz]) / y[nz])) if nz.any() else np.nan,
                "WAPE_pct": float(100 * np.sum(np.abs(err)) / np.sum(y)) if np.sum(y) > 0 else np.nan,
                "actual_boardings": float(np.sum(y)),
            })

out = pd.DataFrame(rows)
naive = out[out["method"] == "naive_last_known_slot"].set_index(["horizon_min", "segment"])
for m in ["MAE", "RMSE", "WAPE_pct"]:
    out[f"{m}_improvement_vs_naive_pct"] = [
        100 * (1 - r[m] / naive.loc[(r["horizon_min"], r["segment"]), m]) for _, r in out.iterrows()
    ]

dataiku.Dataset("forecast_metrics").write_with_schema(out)
