"""Weekly RespiCast forecast: zero-shot Chronos-2, written in the hub's model-output format.

Same model and settings as the backtest (data-advisory scripts respicast_chronos.chronos2), copied
here so this repo runs on its own. Do not change it during the season: the live test is
pre-registered with these settings.

Usage: python forecast.py <hub_checkout> <origin YYYY-MM-DD> <out_dir>
Exit 3 when the hub has no data for this round yet (newest snapshot older than the Friday before).
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

MODEL_ID = "amazon/chronos-2"
MODEL_REVISION = "29ec3766d36d6f73f0696f85560a422f50e8498c"
HUB_MODEL = "pedro-Chronos2"
QUANTILES = [0.01, 0.025, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5,
             0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 0.975, 0.99]
HORIZONS = [1, 2, 3, 4]
STEPS = 5  # one spare step: a fresh series may end a week early
MAX_STALENESS_DAYS = 7  # skip a series whose last week is older than the expected last week + 7 days
DATA_LEAD_DAYS = 5  # the round's data is published on the Friday before the Wednesday origin
COLUMNS = ["origin_date", "target", "target_end_date", "horizon", "location", "output_type", "output_type_id", "value"]
EXIT_NO_DATA = 3


def target_end_date(origin: pd.Timestamp, horizon: int) -> pd.Timestamp:
    return origin - pd.Timedelta(days=3) + pd.Timedelta(weeks=horizon - 1)


def load_snapshots(hub: Path) -> pd.DataFrame:
    """Every published snapshot (ERVISS + FluID), tagged with its publication date."""
    rows = []
    for source in ["ERVISS", "FluID"]:
        for path in sorted((hub / "target-data" / source / "snapshots").glob("*_incidence.csv")):
            snap = pd.read_csv(path, usecols=["target", "location", "truth_date", "value"])
            snap["published"] = pd.Timestamp(path.name[:10])
            rows.append(snap)
    snaps = pd.concat(rows)
    snaps["date"] = pd.to_datetime(snaps.pop("truth_date"))
    snaps["value"] = snaps.value.astype(float)
    return snaps


def history_as_of(snaps: pd.DataFrame, origin: pd.Timestamp) -> pd.DataFrame:
    """For each (target, location, week), the value in the newest snapshot published before the origin."""
    seen = snaps[snaps.published < origin]
    latest = seen.sort_values("published").groupby(["target", "location", "date"]).tail(1)
    return latest[["target", "location", "date", "value"]].sort_values(["target", "location", "date"])


def fresh_history(history: pd.DataFrame, origin: pd.Timestamp) -> pd.DataFrame:
    last = history.sort_values("date").groupby(["target", "location"]).tail(1)
    expected_last_week = target_end_date(origin, 0)
    fresh = last[last.date >= expected_last_week - pd.Timedelta(days=MAX_STALENESS_DAYS)]
    return history.merge(fresh[["target", "location"]], on=["target", "location"])


def context_frame(history: pd.DataFrame) -> pd.DataFrame:
    """Weekly-regular history for each series; gaps (off-season weeks) left as NaN."""
    frames = []
    for (target, location), g in history.groupby(["target", "location"]):
        s = g.set_index("date").value.sort_index()
        s = s.reindex(pd.date_range(s.index.min(), s.index.max(), freq="7D"))
        frames.append(pd.DataFrame({"item_id": f"{target}|{location}", "timestamp": s.index, "target": s.to_numpy()}))
    return pd.concat(frames)


def predict(context: pd.DataFrame, origin: pd.Timestamp) -> pd.DataFrame:
    from chronos import Chronos2Pipeline
    pipe = Chronos2Pipeline.from_pretrained(MODEL_ID, revision=MODEL_REVISION, device_map="cpu")
    pred = pipe.predict_df(context, target="target", prediction_length=STEPS, quantile_levels=QUANTILES,
                           cross_learning=True, batch_size=100)
    quantile_cols = [c for c in pred.columns if _is_quantile(c)]
    long = pred.melt(id_vars=["item_id", "timestamp", "target_name"], value_vars=quantile_cols,
                     var_name="q", value_name="value")
    long["q"] = long.q.astype(float)
    long[["target", "location"]] = long.item_id.str.split("|", expand=True)
    by_date = {target_end_date(origin, h): h for h in HORIZONS}
    long["horizon"] = pd.to_datetime(long.timestamp).map(by_date)
    long = long.dropna(subset=["horizon"]).astype({"horizon": int})
    long["value"] = long.value.clip(lower=0)
    # quantile crossing can occur after clipping; sort within each cell
    long = long.sort_values(["target", "location", "horizon", "q"])
    long["value"] = long.groupby(["target", "location", "horizon"]).value.transform(np.sort)
    return long[["target", "location", "horizon", "q", "value"]]


def _is_quantile(col) -> bool:
    try:
        return 0 < float(col) < 1
    except (TypeError, ValueError):
        return False


def to_hub_format(fc: pd.DataFrame, origin: pd.Timestamp) -> pd.DataFrame:
    fc = fc.copy()
    fc["origin_date"] = origin.strftime("%Y-%m-%d")
    fc["target_end_date"] = [target_end_date(origin, h).strftime("%Y-%m-%d") for h in fc.horizon]
    quantiles = fc.assign(output_type="quantile", output_type_id=fc.q.map(lambda q: f"{q:g}"))
    # the hub asks for exactly one median row per cell; ours is the 0.5 quantile
    medians = fc[fc.q == 0.5].assign(output_type="median", output_type_id="")
    return pd.concat([quantiles, medians])[COLUMNS].sort_values(COLUMNS[:7]).reset_index(drop=True)


def validate(fc: pd.DataFrame, hub: Path, origin: pd.Timestamp) -> None:
    """The format rules from the hub wiki and tasks.json that a bad run could break."""
    tasks = json.loads((hub / "hub-config" / "tasks.json").read_text())["rounds"][0]["model_tasks"][0]["task_ids"]
    problems = []
    if not set(fc.location) <= set(tasks["location"]["optional"]):
        problems.append(f"unknown locations {set(fc.location) - set(tasks['location']['optional'])}")
    if origin.strftime("%Y-%m-%d") not in tasks["origin_date"]["optional"]:
        problems.append("origin_date is not a hub round")
    if (fc.value < 0).any() or fc.value.isna().any():
        problems.append("negative or missing values")
    cells = fc.groupby(["target", "location", "horizon"]).output_type
    if (cells.apply(lambda s: (s == "quantile").sum()) != len(QUANTILES)).any():
        problems.append("cell without all 23 quantiles")
    if (cells.apply(lambda s: (s == "median").sum()) != 1).any():
        problems.append("cell without exactly one median")
    q = fc[fc.output_type == "quantile"].assign(q=lambda d: d.output_type_id.astype(float)).sort_values("q")
    if (q.groupby(["target", "location", "horizon"]).value.diff() < 0).any():
        problems.append("quantiles cross")
    if problems:
        raise ValueError(f"[forecast] {origin.date()}: " + "; ".join(problems))


def main() -> None:
    hub, origin, out_dir = Path(sys.argv[1]), pd.Timestamp(sys.argv[2]), Path(sys.argv[3])
    if origin.day_of_week != 2:
        raise ValueError(f"[forecast] origin {origin.date()} is not a Wednesday")
    snaps = load_snapshots(hub)
    newest = snaps[snaps.published < origin].published.max()
    if newest < origin - pd.Timedelta(days=DATA_LEAD_DAYS):
        print(f"[forecast] {origin.date()}: newest snapshot is {newest.date()}, this round's data isn't out yet")
        sys.exit(EXIT_NO_DATA)
    history = fresh_history(history_as_of(snaps, origin), origin)
    if history.empty:
        raise RuntimeError(f"[forecast] {origin.date()}: no series fresh enough to forecast")
    fc = to_hub_format(predict(context_frame(history), origin), origin)
    validate(fc, hub, origin)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{origin.strftime('%Y-%m-%d')}-{HUB_MODEL}.csv"
    fc.to_csv(path, index=False)
    medians = fc[fc.output_type == "median"]
    print(f"[forecast] {path.name}: {len(medians)} cells, {medians.location.nunique()} countries, data to {newest.date()}")


if __name__ == "__main__":
    main()
