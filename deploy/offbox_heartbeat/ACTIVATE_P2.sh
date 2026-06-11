#!/usr/bin/env bash
# P2 off-box heartbeat — ACTIVATION (2 Commander commands). Outward-facing:
# pushes the workflow to GitHub + stores the bot token as a GH secret. Run when ready.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
# 1. Store the D2MC2C bot token as an encrypted GitHub Actions secret:
gh secret set TELEGRAM_BOT_TOKEN   # paste token when prompted (8754681793:...)
# 2. Push the workflow so GitHub starts the schedule:
git push origin master
echo "P2 active. Verify: gh workflow run 'Off-box Wing Heartbeat'; then gh run list"
