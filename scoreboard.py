"""Season scoreboard from the hub's own WIS scores: pedro-Chronos2 against the hub ensemble and the
other Chronos entries, on cells both forecast. Interim only: the final 2026-27 result follows the
pre-registered rules (truth as of 2027-06-30, block-bootstrap interval).

Usage: python scoreboard.py <hub_checkout> <out.md> [model] [season_start]
Also writes scores.json beside out.md: the live result card the AI4G tracker shows.
"""
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

MODEL = "pedro-Chronos2"
SEASON_START = "2026-10-28"
ENSEMBLE, BASELINE = "respicast-hubEnsemble", "respicast-quantileBaseline"
HUB_PREFIX = "respicast-"  # the hub's own models; everything else is an outside team
MAX_CARD_ROWS = 6  # AI4G's parse_scores limit
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
    pair = sc[sc.model.isin([model, other])].pivot_table(index=KEY, columns="model", values="value_absolute")
    if not {model, other} <= set(pair.columns):  # one side not scored yet: nothing shared
        return pair.iloc[0:0]
    return pair.dropna()


def teams(sc: pd.DataFrame, model: str) -> list[str]:
    return sorted(m for m in sc.model.unique() if m != model and not m.startswith(HUB_PREFIX))


def rank_teams(sc: pd.DataFrame, model: str) -> list[dict]:
    """Ratio vs each outside team on shared cells, keeping teams that share at least half our widest overlap
    with any team, so a team scored on a handful of cells doesn't count as a rival; strongest teams first."""
    pairs = [(t, shared(sc, model, t)) for t in teams(sc, model)]
    pairs = [(t, p) for t, p in pairs if len(p)]
    widest = max((len(p) for _, p in pairs), default=0)
    return sorted(({"team": t, "ratio": ratio(p, model, t), "cells": len(p)} for t, p in pairs if 2 * len(p) >= widest),
                  key=lambda r: (-r["ratio"], r["team"]))


def build(sc: pd.DataFrame, model: str) -> str:
    lines = ["# 2026-27 season scoreboard", "",
             f"Interim, from the hub's WIS scores (`model-evaluation/latest-forecast_scores.csv`), horizons 1-4, "
             f"target weeks Oct-May. Ratio = {model} WIS / comparator WIS, geometric mean over countries and targets; "
             f"below 1 means {model} is better. Teams ranked if they share at least half the widest overlap.", "",
             "| comparator | ratio | shared cells | rounds | ranked |", "|---|---|---|---|---|"]
    ranked = {r["team"] for r in rank_teams(sc, model)}
    for other in [ENSEMBLE, BASELINE, *teams(sc, model)]:
        pair = shared(sc, model, other)
        if pair.empty:
            lines.append(f"| {other} | - | 0 | 0 | |")
            continue
        rounds = pair.index.get_level_values("origin_date").nunique()
        mark = "yes" if other in ranked else ("" if other.startswith(HUB_PREFIX) else "no")
        lines.append(f"| {other} | {ratio(pair, model, other):.2f} | {len(pair)} | {rounds} | {mark} |")
    pair = shared(sc, model, ENSEMBLE)
    lines += ["", f"By round, vs {ENSEMBLE}:", "", "| round | ratio | cells |", "|---|---|---|"]
    for origin, g in pair.groupby(level="origin_date"):
        lines.append(f"| {origin.date()} | {ratio(g, model, ENSEMBLE):.2f} | {len(g)} |")
    return "\n".join(lines) + "\n"


def build_scores(sc: pd.DataFrame, model: str, today: str) -> dict:
    """Headline (rank among outside teams, then the ensemble), period and rows, in the shape AI4G's status.py checks."""
    vs_ensemble = shared(sc, model, ENSEMBLE)
    if vs_ensemble.empty:
        return {"headline": "Live scores pending: no round scored yet",
                "period": f"2026-27 season, 0 rounds scored; updated {today}", "rows": []}
    rows = []
    for label, other in [("Us vs hub ensemble", ENSEMBLE), ("Us vs baseline", BASELINE)]:
        pair = shared(sc, model, other)
        rows.append({"measure": label, "value": f"{ratio(pair, model, other):.2f}" if len(pair) else "-",
                     "range": f"{len(pair)} cells"})
    ranked = rank_teams(sc, model)
    rows += [{"measure": f"Us vs {r['team']}"[:40], "value": f"{r['ratio']:.2f}", "range": f"{r['cells']} cells"}
             for r in ranked][:MAX_CARD_ROWS - len(rows)]
    r = ratio(vs_ensemble, model, ENSEMBLE)
    vs_ens = f"{round(abs(1 - r) * 100)}% {'less' if r < 1 else 'more'} error than the hub ensemble"
    beaten = sum(t["ratio"] < 1 for t in ranked)
    headline = f"Better than {beaten} of {len(ranked)} teams; {vs_ens}" if ranked else f"Only outside team so far; {vs_ens}"
    rounds = vs_ensemble.index.get_level_values("origin_date").nunique()
    period = f"2026-27 season, {rounds} round{'s' if rounds != 1 else ''} scored, interim; updated {today}"
    return {"headline": headline, "period": period, "rows": rows}


def main() -> None:
    hub, out = Path(sys.argv[1]), Path(sys.argv[2])
    model = sys.argv[3] if len(sys.argv) > 3 else MODEL
    season_start = sys.argv[4] if len(sys.argv) > 4 else SEASON_START
    sc = load_scores(hub, season_start)
    out.write_text(build(sc, model))
    scores = out.with_name("scores.json")
    scores.write_text(json.dumps(build_scores(sc, model, date.today().isoformat()), indent=2) + "\n")
    print(f"[scoreboard] wrote {out} and {scores}")


if __name__ == "__main__":
    main()
