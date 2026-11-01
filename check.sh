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

failed=0
if gh api "repos/$UPSTREAM/contents/$FILE" --silent 2>/dev/null; then
  echo "[check] round $ROUND: submitted"
else
  echo "[check] round $ROUND: $FILE is not in the hub, the submission was missed" >&2; failed=1
fi

# The hub lists target weeks only to a fixed date; ask it to extend the list well before it runs out
last_week=$(gh api "repos/$UPSTREAM/contents/hub-config/tasks.json" -H "Accept: application/vnd.github.raw" |
  jq -r '[.rounds[].model_tasks[].task_ids.target_end_date.optional[]] | max')
if [[ "$last_week" < $(date -u -d "+6 weeks" +%F) ]]; then
  echo "[check] the hub's tasks.json lists target weeks only to $last_week: ask the hub to extend it" >&2; failed=1
fi

# AI4Casting (submitted by ai4casting.yml): the hub merges by hand days later, so a PR with passing checks counts
AI4C_ROUND=$(date -u -d "last saturday" +%F)
for repo in ai4castinghub/hospitalization-forecast ai4castinghub/rvdss-forecast; do
  path="model-output/$MODEL/$AI4C_ROUND-$MODEL.csv"
  if gh api "repos/$repo/contents/$path" --silent 2>/dev/null; then echo "[check] $repo $AI4C_ROUND: in the hub"; continue; fi
  pr=$(gh pr list --repo "$repo" --head "$MODEL-$AI4C_ROUND" --state all --json url,state --jq '.[0] | select(.state != "CLOSED") | .url')
  checks=$([[ -n "$pr" ]] && gh pr checks "$pr" --json bucket --jq '[.[].bucket] | unique | join(",")' || true)
  if [[ -z "$pr" || "$checks" == *fail* || "$checks" == *cancel* ]]; then
    echo "[check] $repo $AI4C_ROUND: no PR with passing checks (${pr:-no PR}, checks: ${checks:-none})" >&2; failed=1
  else
    echo "[check] $repo $AI4C_ROUND: PR $pr ($checks), awaiting merge"
  fi
done
exit $failed
