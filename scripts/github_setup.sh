#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# github_setup.sh — one-time GitHub remote setup for Thunderbird
# Run this once from a terminal. Nothing to fill in.
# ─────────────────────────────────────────────────────────────

set -e

cd /home/john/Thunderbird

echo ""
echo "Step 1 — Logging into GitHub..."
echo "(A browser window will open — sign in and authorize)"
echo ""
gh auth login --web --git-protocol https

echo ""
echo "Step 2 — Creating private repo and pushing..."
gh repo create thunderbird-os --private --source=. --remote=origin --push

echo ""
echo "✅ Done. Your code is on GitHub at:"
gh repo view --json url -q .url
echo ""
echo "From now on, 'git push' will work directly."
