"""Season scoreboard from the hub's own WIS scores: pedro-Chronos2 against the hub ensemble and the
other Chronos entries, on cells both forecast. Interim only: the final 2026-27 result follows the
pre-registered rules (truth as of 2027-06-30, block-bootstrap interval).

Usage: python scoreboard.py <hub_checkout> <out.md> [model] [season_start]
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

MODEL = "pedro-Chronos2"
SEASON_START = "2026-10-28"
COMPARATORS = ["respicast-hubEnsemble", "Chronos-Chronos2", "DHauser-FluChronos"]
HORIZONS = [1, 2, 3, 4]
IN_SEASON_MONTHS = [10, 11, 12, 1, 2, 3, 4, 5]
KEY = ["origin_date", "target", "target_end_date", "horizon", "location"]


def load_scores(hub: Path, season_start: str) -> pd.DataFrame:
    sc = pd.read_csv(hub / "model-evaluation" / "latest-forecast_scores.csv",
                     parse_dates=["origin_date", "target_end_date"])
    sc = sc[(sc.metric == "WIS") & (sc.origin_date >= season_start) & sc.horizon.isin(HORIZONS)
            & sc.target_end_date.dt.month.isin(IN_SEASON_MONTHS)]
    sc["model"] = sc.team_id + "-" + sc.model_id
    return sc


def ratio(pair: pd.DataFrame, model: str, other: str) -> float:
    """Geometric mean over (target, location) of mean-WIS ratio, as in the backtest."""
    by_series = pair.groupby(["target", "location"])[[model, other]].mean()
    by_series = by_series[by_series[other] > 0]
    return float(np.exp(np.log(by_series[model] / by_series[other]).mean()))


def shared(sc: pd.DataFrame, model: str, other: str) -> pd.DataFrame:
    return sc[sc.model.isin([model, other])].pivot_table(index=KEY, columns="model", values="value_absolute").dropna()


def build(sc: pd.DataFrame, model: str) -> str:
    lines = ["# 2026-27 season scoreboard", "",
             f"Interim, from the hub's WIS scores (`model-evaluation/latest-forecast_scores.csv`), horizons 1-4, "
             f"target weeks Oct-May. Ratio = {model} WIS / comparator WIS, geometric mean over countries and targets; "
             "below 1 means {model} is better.".replace("{model}", model), "",
             "| comparator | ratio | shared cells | rounds |", "|---|---|---|---|"]
    for other in [c for c in COMPARATORS if c != model]:
        pair = shared(sc, model, other)
        if pair.empty:
            lines.append(f"| {other} | - | 0 | 0 |")
            continue
        rounds = pair.index.get_level_values("origin_date").nunique()
        lines.append(f"| {other} | {ratio(pair, model, other):.2f} | {len(pair)} | {rounds} |")
    pair = shared(sc, model, COMPARATORS[0])
    lines += ["", f"By round, vs {COMPARATORS[0]}:", "", "| round | ratio | cells |", "|---|---|---|"]
    for origin, g in pair.groupby(level="origin_date"):
        lines.append(f"| {origin.date()} | {ratio(g, model, COMPARATORS[0]):.2f} | {len(g)} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    hub, out = Path(sys.argv[1]), Path(sys.argv[2])
    model = sys.argv[3] if len(sys.argv) > 3 else MODEL
    season_start = sys.argv[4] if len(sys.argv) > 4 else SEASON_START
    out.write_text(build(load_scores(hub, season_start), model))
    print(f"[scoreboard] wrote {out}")


if __name__ == "__main__":
    main()
