# 2026-27 season scoreboard

Interim, from the hub's WIS scores (`model-evaluation/latest-forecast_scores.csv`), horizons 1-4, target weeks Oct-May. Ratio = pedro-Chronos2 WIS / comparator WIS, geometric mean over countries and targets; below 1 means pedro-Chronos2 is better. Teams ranked if they share at least half the widest overlap.

| comparator | ratio | shared cells | rounds | ranked |
|---|---|---|---|---|
| respicast-hubEnsemble | 1.04 | 105 | 2 |  |
| respicast-quantileBaseline | 0.80 | 105 | 2 |  |
| DHauser-FluChronos | 1.05 | 105 | 2 | yes |
| ECDC-SARIMA | 0.75 | 95 | 2 | yes |
| ECDC-soca_simplex | 0.87 | 102 | 2 | yes |
| ISI-LightGBM | 0.94 | 105 | 2 | yes |
| ISI-RespiVAR | 1.08 | 105 | 2 | yes |
| ISI-Respiro | 1.08 | 87 | 2 | yes |
| IceLab-EDM | 1.03 | 105 | 2 | yes |
| ItaLuxColab-EpiEKF | 0.58 | 54 | 2 | yes |
| ItaLuxColab-EpiNetEKF | 0.71 | 52 | 2 | no |
| NDP-v1 | 0.86 | 23 | 1 | no |
| QMUL-ARIMA | 0.52 | 43 | 2 | no |
| QMUL-SEIR | 0.47 | 37 | 2 | no |
| QMUL-SEIR_agumented | 0.49 | 32 | 2 | no |
| RIVM-KFdlm | 0.57 | 54 | 2 | yes |
| fluxengine-chronos2 | 0.80 | 3 | 2 | no |
| fluxengine-triad | 0.89 | 3 | 2 | no |
| safinea-PRFM | 0.67 | 103 | 2 | yes |

By round, vs respicast-hubEnsemble:

| round | ratio | cells |
|---|---|---|
| 2026-10-28 | 1.05 | 71 |
| 2026-11-04 | 0.96 | 34 |
