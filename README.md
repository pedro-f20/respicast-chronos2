# pedro-Chronos2 for RespiCast

Weekly submissions of zero-shot [Chronos-2](https://github.com/amazon-science/chronos-forecasting) to the [European Syndromic Indicators Forecasting Hub](https://github.com/european-modelling-hubs/RespiCast-SyndromicIndicators) (ILI and ARI incidence, EU/EEA, 1-4 weeks ahead), as `pedro-Chronos2`.

## Model

- `amazon/chronos-2` at revision `29ec376`, chronos-forecasting 2.3.2, CPU, no fine-tuning.
- Input: the hub's ERVISS and FluID snapshots published before the round, raw weekly incidence, full history with off-season gaps left as missing.
- All series go in one batch with cross-learning, so countries share information.
- Countries whose latest week is more than 7 days old are skipped. Horizons 1-4, 23 quantiles.

## Backtest

2025-26 rounds, using only data published before each origin, on cells both forecast:

| | vs hub ensemble (WIS ratio) | 95% interval coverage |
|---|---|---|
| Chronos-2 | 0.82 (95% CI 0.78-0.87) | 94% |
| hub ensemble | 1 | 79% |

Things that did not beat it by the 3% bar I set before scoring: revision nowcasting, ILI and ARI forecast jointly, test positivity as a covariate, a median of foundation models, a momentum correction, a learned median correction, last week's hub forecasts as input, and fine-tuning (full and LoRA) on European ILI/ARI. The settings for the 2026-27 season were fixed on 27 Oct 2026 before the first live forecast.

## Running

`.github/workflows/submit.yml` runs Friday evening, Monday, Tuesday and twice on Wednesday (UTC). Each run forecasts the next Wednesday round, does nothing if it's already submitted or the data isn't out, and otherwise opens a PR from the `pedro-f20` fork. `submissions.csv` lists the rounds.

`.github/workflows/check.yml` runs on Thursday: it fails if the round that closed on Wednesday has no file in the hub, and updates [SEASON.md](SEASON.md), an interim scoreboard against the hub ensemble from the hub's own scores.

By hand:

```
uv venv --python 3.12 && uv pip install --torch-backend cpu -r requirements.txt
ORIGIN=2026-11-04 DRY_RUN=1 bash submit.sh
```

Disclosure: I used AI to assist in this analysis. I validated every finding.
