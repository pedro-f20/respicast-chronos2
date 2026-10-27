#!/usr/bin/env bash
# One weekly round: forecast the next Wednesday origin and open the submission PR from the fork.
# Safe to run several times a week: it does nothing once the round is submitted or while the
# round's data isn't out. Needs GH_TOKEN (pedro-f20, public_repo + workflow scopes) and a venv at .venv.
#   ORIGIN=YYYY-MM-DD  override the round
#   DRY_RUN=1          forecast only, no push or PR
#   FINAL=1            last run before the deadline: missing data is an error, not a wait
set -euo pipefail

UPSTREAM=european-modelling-hubs/RespiCast-SyndromicIndicators
FORK=pedro-f20/RespiCast-SyndromicIndicators
MODEL=pedro-Chronos2
EXIT_NO_DATA=3

# next Wednesday, or today if it is one (date +%u: Monday=1 ... Wednesday=3)
ORIGIN=${ORIGIN:-$(date -u -d "+$(( (3 - $(date -u +%u) + 7) % 7 )) days" +%F)}
FILE="model-output/$MODEL/$ORIGIN-$MODEL.csv"
BRANCH="$MODEL-$ORIGIN"
echo "[submit] round $ORIGIN"

if [[ -z "${DRY_RUN:-}" ]]; then
  if gh api "repos/$UPSTREAM/contents/$FILE" --silent 2>/dev/null; then
    echo "[submit] $FILE is already in the hub, nothing to do"; exit 0
  fi
  open_pr=$(gh pr list --repo "$UPSTREAM" --head "$BRANCH" --state open --json url --jq '.[0].url')
  if [[ -n "$open_pr" ]]; then
    echo "[submit] PR $open_pr is open but not merged: the hub's validation probably failed" >&2; exit 1
  fi
fi

rm -rf hub
git clone -q --depth 1 --filter=blob:none --sparse "https://github.com/$UPSTREAM.git" hub
git -C hub sparse-checkout set target-data hub-config

set +e
.venv/bin/python forecast.py hub "$ORIGIN" out
status=$?
set -e
if [[ $status -eq $EXIT_NO_DATA ]]; then
  if [[ -n "${FINAL:-}" ]]; then echo "[submit] deadline run and still no data for $ORIGIN" >&2; exit 1; fi
  exit 0
fi
[[ $status -eq 0 ]] || exit $status
[[ -z "${DRY_RUN:-}" ]] || { echo "[submit] dry run, stopping before push"; exit 0; }

# the fork must hold the upstream commit the branch is built on
gh repo sync "$FORK" --source "$UPSTREAM" --branch main

mkdir -p "hub/model-output/$MODEL"
cp "out/$ORIGIN-$MODEL.csv" "hub/$FILE"
git -C hub sparse-checkout add "model-output/$MODEL"
git -C hub switch -q -c "$BRANCH"
git -C hub add "$FILE"
git -C hub -c user.name=pedro-f20 -c user.email=250035667+pedro-f20@users.noreply.github.com \
  commit -q -m "Add $MODEL forecast for $ORIGIN"
git -C hub push -q "https://x-access-token:$GH_TOKEN@github.com/$FORK.git" "$BRANCH"

cells=$(awk -F, '$6 == "median"' "out/$ORIGIN-$MODEL.csv" | wc -l | tr -d ' ')
pr=$(gh pr create --repo "$UPSTREAM" --head "pedro-f20:$BRANCH" --base main \
  --title "$MODEL forecast for $ORIGIN" \
  --body "Weekly forecast for origin $ORIGIN from $MODEL ($cells cells). Same model and settings as earlier rounds; see model-metadata/$MODEL.yml.")
echo "[submit] opened $pr"
echo "$ORIGIN,$cells,$pr" >> submissions.csv
