#!/usr/bin/env bash
# run_perx_keepalive.sh — Run Perx session keepalive using .venv
# Usage: bash scripts/run_perx_keepalive.sh
set -e
cd "$(dirname "$0")/.."
echo "[$(date '+%Y-%m-%d %H:%M')] Running Perx session keepalive..."
.venv/bin/python scripts/perx_session_keepalive.py
echo "[$(date '+%Y-%m-%d %H:%M')] Done."
