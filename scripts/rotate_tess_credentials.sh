#!/bin/bash
# rotate_tess_credentials.sh — Inject a fresh TESS token captured from browser
# localStorage, then verify + restart the keepalive service.
#
# Usage:
#   bash scripts/rotate_tess_credentials.sh '<authenticationData JSON blob>'
#
# The blob is the value of the "authenticationData" key in
# https://crm.myagentgenie.com localStorage (DevTools -> Application ->
# Local Storage). See OpsCenter/elon_proposals/TESS_ROTATION_READY.md for the
# exact capture steps.

set -euo pipefail

THUNDERBIRD_DIR="$HOME/Thunderbird"
TESS_PY="$THUNDERBIRD_DIR/core/booking/thunderbird_tess.py"
TOKEN_FILE="$THUNDERBIRD_DIR/tess_token.json"

if [ $# -ne 1 ] || [ -z "$1" ]; then
    echo "ERROR: pass the authenticationData JSON blob as a single quoted argument."
    echo ""
    echo "Usage: bash $0 '<authenticationData JSON>'"
    exit 1
fi

BLOB="$1"

echo "=== TESS Credential Rotation ==="
echo ""

# ── Inject ────────────────────────────────────────────────────────────────
echo "Injecting token..."
python3 "$TESS_PY" --inject-token "$BLOB"
echo ""

if [ ! -f "$TOKEN_FILE" ]; then
    echo "ERROR: $TOKEN_FILE was not written. Injection failed."
    exit 1
fi

USER_ID=$(python3 -c "import json; print(json.load(open('$TOKEN_FILE')).get('userID',''))")
if [ -z "$USER_ID" ]; then
    echo "ERROR: userID is still empty after injection — the pasted blob likely"
    echo "       did not contain a valid JWT with UserID/CompanyID claims."
    exit 1
fi
echo "userID captured: $USER_ID"
echo ""

# ── Verify live connection ──────────────────────────────────────────────────
echo "Testing live connection..."
if python3 "$TESS_PY" --test | tee /tmp/tess_rotate_test.json | grep -q '"error"'; then
    echo ""
    echo "ERROR: connection test still failing after injection. See output above."
    exit 1
fi
echo ""
echo "Connection test PASSED."
echo ""

# ── Restart keepalive timer so the next cycle runs against the fresh token ──
echo "Restarting tess-token-keepalive.timer..."
systemctl --user restart tess-token-keepalive.timer
systemctl --user status tess-token-keepalive.timer --no-pager -l | head -10
echo ""

echo "=== Rotation complete. TESS is live. ==="
