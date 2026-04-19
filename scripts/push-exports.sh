#!/usr/bin/env bash
# Trigger a fresh export on the VPS, sync it back, commit, push.
# Run manually or from cron/launchd on a machine with git push access.
# Requires HETZNER_VPS_USER_1 and HETZNER_VPS_HOST_1 in the environment.
set -euo pipefail

: "${HETZNER_VPS_USER_1:?must be exported}"
: "${HETZNER_VPS_HOST_1:?must be exported}"

VPS="${YT_VPS:-${HETZNER_VPS_USER_1}@${HETZNER_VPS_HOST_1}}"
VPS_DIR="${YT_VPS_DIR:-album-etorika}"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"

cd "$REPO_DIR"

# 1. Run incremental export on the VPS
ssh "$VPS" "cd $VPS_DIR && ~/.local/bin/uv run python main.py export"

# 2. Mirror exports/ back to local (VPS is source of truth)
rsync -az --delete "$VPS:$VPS_DIR/exports/" "$REPO_DIR/exports/"

# 3. Commit + push if anything changed
if [[ -n "$(git status --porcelain exports/)" ]]; then
  git add exports/
  git commit -q -m "snapshot $(date -u +%FT%H:%MZ)"
  git push -q
  echo "Pushed snapshot $(date -u +%FT%H:%MZ)"
else
  echo "No new data."
fi
