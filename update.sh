#!/usr/bin/env bash
#
# update.sh — refresh a local clone of the Ergo Knowledge Base and reload it.
#
# Minimal and build-tool-agnostic: it fast-forwards from origin, reports what
# changed, and prints the next step. It never builds or runs new upstream code
# automatically.
#
# Usage:
#   ./update.sh            Pull updates and report what changed.
#   ./update.sh --check    Report whether updates exist; do not pull.
#
# Optional: set EKB_SERVICE to a systemd --user unit to auto-restart it after a
# content-only update, e.g.  EKB_SERVICE=your-ekb.service ./update.sh

set -euo pipefail

REPO="$(git rev-parse --show-toplevel)"
cd "$REPO"
BRANCH="$(git rev-parse --abbrev-ref HEAD)"

git fetch --quiet origin "$BRANCH"
LOCAL="$(git rev-parse @)"
REMOTE="$(git rev-parse "origin/$BRANCH")"

if [ "$LOCAL" = "$REMOTE" ]; then
  echo "Up to date ($LOCAL)."
  exit 0
fi

CHANGED="$(git diff --name-only "$LOCAL" "$REMOTE")"
echo "Updates available on $BRANCH:"
echo "$CHANGED" | sed 's/^/  /'

if [ "${1:-}" = "--check" ]; then
  echo
  echo "Run ./update.sh to apply."
  exit 0
fi

# Fast-forward only, and never clobber local work.
if [ -n "$(git status --porcelain)" ]; then
  echo >&2
  echo "Working tree has local changes. Commit or stash them, then re-run." >&2
  exit 1
fi

git pull --ff-only --quiet origin "$BRANCH"

# Default-deny: auto-reload for content/index changes only; never auto-run new code.
CODE="$(echo "$CHANGED" | grep -E '(^|/)(lib|app)/|(^|/)package(-lock)?\.json$|(^|/)(next\.config|tsconfig)\.' || true)"

if [ -n "$CODE" ]; then
  cat <<EOF

Code or dependencies changed. Review the diff, then rebuild and restart yourself:

  cd "$REPO/mcp-server" && npm ci && npm run build
  # then restart your instance (e.g. systemctl --user restart <your-service>, or npm run start)

New upstream code is never built or run automatically.
EOF
  exit 0
fi

echo
echo "Content/index updated — no rebuild needed."
if [ -n "${EKB_SERVICE:-}" ]; then
  systemctl --user restart "$EKB_SERVICE"
  echo "Restarted $EKB_SERVICE."
else
  echo "Restart your instance to load the new index (set EKB_SERVICE to automate this)."
fi
