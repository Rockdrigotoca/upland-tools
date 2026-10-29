#!/usr/bin/env bash
# Commit and push the data files a collector step changed.
# Usage: commit_data.sh "<commit message>" <pathspec>...
set -euo pipefail
msg="$1"; shift
git config user.name "collector"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
git add -- "$@"
if git diff --cached --quiet; then
  echo "No changes"
  exit 0
fi
git commit -q -m "$msg"
for attempt in 1 2 3; do
  if git pull -q --rebase --autostash && git push -q; then
    echo "Pushed: $msg"
    exit 0
  fi
  sleep 5
done
echo "Could not push after 3 tries" >&2
exit 1
