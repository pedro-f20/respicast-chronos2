#!/usr/bin/env bash
# Thursday check: refresh SEASON.md from the hub's scores, then fail (GitHub emails the owner) if
# last night's round has no pedro-Chronos2 file in the hub. Catches what submit.yml can't report
# itself, such as scheduled runs that never fired.
#   ROUND=YYYY-MM-DD  override the round (default: the Wednesday just gone)
set -euo pipefail

UPSTREAM=european-modelling-hubs/RespiCast-SyndromicIndicators
MODEL=pedro-Chronos2

ROUND=${ROUND:-$(date -u -d "last wednesday" +%F)}
FILE="model-output/$MODEL/$ROUND-$MODEL.csv"

rm -rf hub
git clone -q --depth 1 --filter=blob:none --sparse "https://github.com/$UPSTREAM.git" hub
git -C hub sparse-checkout set model-evaluation
uv run -q --python 3.12 --with pandas==3.1.0 --with numpy==2.5.4 python scoreboard.py hub SEASON.md

if ! gh api "repos/$UPSTREAM/contents/$FILE" --silent 2>/dev/null; then
  echo "[check] round $ROUND: $FILE is not in the hub, the submission was missed" >&2; exit 1
fi
echo "[check] round $ROUND: submitted"
