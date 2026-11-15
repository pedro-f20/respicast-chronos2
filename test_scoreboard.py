"""python -m unittest test_scoreboard"""
import unittest

import pandas as pd

from scoreboard import build_scores, rank_teams


def scores_frame(wis_by_model: dict) -> pd.DataFrame:
    """The hub's scores file shape after load_scores: one WIS row per model and cell."""
    rows = []
    for model, values in wis_by_model.items():
        for i, value in enumerate(values):
            if value is not None:
                rows.append({"origin_date": pd.Timestamp("2026-11-04"), "target": "ILI", "horizon": 1,
                             "target_end_date": pd.Timestamp("2026-11-11"), "location": f"L{i}",
                             "model": model, "value_absolute": value})
    return pd.DataFrame(rows)


BASE = {"us": [1.0] * 4, "respicast-hubEnsemble": [2.0] * 4, "respicast-quantileBaseline": [2.0] * 4}


class TeamsTest(unittest.TestCase):
    def test_should_lead_with_rank_among_teams_when_teams_are_scored(self):
        sc = scores_frame({**BASE, "A-good": [0.5] * 4, "B-bad": [3.0] * 4, "C-worse": [4.0] * 4})
        scores = build_scores(sc, "us", "2026-11-15")
        self.assertEqual(scores["headline"], "Better than 2 of 3 teams; 50% less error than the hub ensemble")
        self.assertEqual([r["measure"] for r in scores["rows"]][:3],
                         ["Us vs hub ensemble", "Us vs baseline", "Us vs A-good"])

    def test_should_leave_out_hub_models_and_thin_overlap_when_ranking(self):
        sc = scores_frame({**BASE, "A-wide": [2.0] * 4, "B-narrow": [9.0, None, None, None]})
        self.assertEqual([r["team"] for r in rank_teams(sc, "us")], ["A-wide"])

    def test_should_cap_card_at_six_rows_when_many_teams(self):
        sc = scores_frame({**BASE, **{f"T{i}-m": [2.0] * 4 for i in range(8)}})
        self.assertEqual(len(build_scores(sc, "us", "2026-11-15")["rows"]), 6)

    def test_should_report_pending_when_nothing_is_scored(self):
        sc = scores_frame({"us": [None], "respicast-hubEnsemble": [2.0]})
        self.assertEqual(build_scores(sc, "us", "2026-11-15")["headline"], "Live scores pending: no round scored yet")


if __name__ == "__main__":
    unittest.main()
