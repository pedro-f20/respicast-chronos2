# 2026-27 season scoreboard

Interim, from the hub's WIS scores (`model-evaluation/latest-forecast_scores.csv`), horizons 1-4, target weeks Oct-May. Ratio = pedro-Chronos2 WIS / comparator WIS, geometric mean over countries and targets; below 1 means pedro-Chronos2 is better. Teams ranked if they share at least half the widest overlap.

| comparator | ratio | shared cells | rounds | ranked |
|---|---|---|---|---|
| respicast-hubEnsemble | 0.99 | 220 | 3 |  |
| respicast-quantileBaseline | 0.74 | 220 | 3 |  |
| DHauser-FluChronos | 1.02 | 220 | 3 | yes |
| ECDC-SARIMA | 0.70 | 201 | 3 | yes |
| ECDC-soca_simplex | 0.77 | 215 | 3 | yes |
| ISI-LightGBM | 0.88 | 220 | 3 | yes |
| ISI-RespiVAR | 0.97 | 218 | 3 | yes |
| ISI-Respiro | 0.99 | 188 | 3 | yes |
| IceLab-EDM | 1.01 | 220 | 3 | yes |
| ItaLuxColab-EpiEKF | 0.58 | 116 | 3 | yes |
| ItaLuxColab-EpiNetEKF | 0.73 | 114 | 3 | yes |
| NDP-v1 | 0.82 | 52 | 1 | no |
| QMUL-ARIMA | 0.60 | 94 | 3 | no |
| QMUL-SEIR | 0.56 | 81 | 3 | no |
| QMUL-SEIR_agumented | 0.42 | 70 | 3 | no |
| RIVM-KFdlm | 0.60 | 115 | 3 | yes |
| fluxengine-chronos2 | 0.99 | 5 | 2 | no |
| fluxengine-triad | 0.95 | 6 | 3 | no |
| safinea-PRFM | 0.70 | 217 | 3 | yes |

By round, vs respicast-hubEnsemble:

| round | ratio | cells |
|---|---|---|
| 2026-10-28 | 1.00 | 110 |
| 2026-11-04 | 0.93 | 73 |
| 2026-11-11 | 0.94 | 37 |
