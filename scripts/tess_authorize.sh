#!/bin/bash
# tess_authorize.sh — Walk through TESS OAuth authorization for Thunderbird OS
# Run once to get tess_token.json; thereafter TESS integration is live.
#
# Auth endpoint:  https://auth.outsideagents.com/oauth2
# API base:       https://api.outsideagents.com/tess/v2
# Token file:     ~/Thunderbird/tess_token.json
# Config file:    ~/Thunderbird/tess_config.json

set -euo pipefail

THUNDERBIRD_DIR="$HOME/Thunderbird"
TOKEN_FILE="$THUNDERBIRD_DIR/tess_token.json"
CONFIG_FILE="$THUNDERBIRD_DIR/tess_config.json"
TESS_PY="$THUNDERBIRD_DIR/thunderbird_tess.py"

# ── Banner ──────────────────────────────────────────────────────────────────

echo ""
echo "═══════════════════════════════════════════════"
echo "  TESS (Outside Agents) — OAuth Setup"
echo "  Dreams2Memories Travel, LLC"
echo "═══════════════════════════════════════════════"
echo ""
echo "This will open a browser to authorize Thunderbird OS"
echo "to access your Outside Agents / TESS account."
echo ""
echo "Scopes requested:"
echo "  agent:read/write  bookings:read/write"
echo "  clients:read/write  commissions:read  suppliers:read"
echo ""

# ── Pre-flight: Python ───────────────────────────────────────────────────────

if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found. Install Python 3.9+ and retry."
    exit 1
fi

if [ ! -f "$TESS_PY" ]; then
    echo "ERROR: thunderbird_tess.py not found at $TESS_PY"
    echo "       Run from ~/Thunderbird or confirm the Thunderbird dir is correct."
    exit 1
fi

# ── Already authorized? ──────────────────────────────────────────────────────

if [ -f "$TOKEN_FILE" ]; then
    echo "Found existing token file: $TOKEN_FILE"
    echo ""
    read -rp "Re-authorize anyway? (y/N): " REAUTH
    if [[ ! "$REAUTH" =~ ^[Yy]$ ]]; then
        echo ""
        echo "Skipping re-authorization. Running connection test instead..."
        echo ""
        python3 "$TESS_PY" --test
        exit 0
    fi
    echo ""
fi

# ── Credential resolution ────────────────────────────────────────────────────

echo "Prerequisites:"
echo "  - Active Outside Agents account"
echo "  - TESS API credentials (Client ID + Client Secret)"
echo "    Get them at: https://portal.outsideagents.com/settings/api"
echo ""

# Priority: env vars > config file > interactive prompt

if [ -z "${TESS_CLIENT_ID:-}" ] || [ -z "${TESS_CLIENT_SECRET:-}" ]; then
    # Try config file
    if [ -f "$CONFIG_FILE" ]; then
        echo "Found $CONFIG_FILE — credentials will be loaded from file."
        echo ""
    else
        # Interactive prompt
        echo "TESS_CLIENT_ID and/or TESS_CLIENT_SECRET not set."
        echo ""
        read -rp "Enter TESS Client ID: " INPUT_CLIENT_ID
        read -rsp "Enter TESS Client Secret: " INPUT_CLIENT_SECRET
        echo ""
        echo ""

        if [ -z "$INPUT_CLIENT_ID" ] || [ -z "$INPUT_CLIENT_SECRET" ]; then
            echo "ERROR: Client ID and Client Secret are both required."
            exit 1
        fi

        # Write tess_config.json so the Python module picks them up
        cat > "$CONFIG_FILE" <<EOF
{
  "client_id": "$INPUT_CLIENT_ID",
  "client_secret": "$INPUT_CLIENT_SECRET"
}
EOF
        echo "Credentials saved to $CONFIG_FILE"
        echo ""
    fi
else
    echo "TESS_CLIENT_ID and TESS_CLIENT_SECRET found in environment."
    echo ""
fi

# ── Port check ───────────────────────────────────────────────────────────────
# thunderbird_tess.py uses localhost:8089 for the OAuth callback.

if ss -tlnp 2>/dev/null | grep -q ':8089 ' || netstat -tlnp 2>/dev/null | grep -q ':8089 '; then
    echo "WARNING: Port 8089 appears to be in use."
    echo "         The OAuth callback listener may fail. Free port 8089 and retry."
    echo ""
    read -rp "Continue anyway? (y/N): " CONTINUE_ANYWAY
    if [[ ! "$CONTINUE_ANYWAY" =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# ── Run authorization ────────────────────────────────────────────────────────

echo "Starting OAuth 2.0 + PKCE authorization flow..."
echo "(Callback listener on http://localhost:8089/callback)"
echo ""

if python3 "$TESS_PY" --authorize; then
    echo ""
else
    echo ""
    echo "ERROR: Authorization script exited with an error."
    echo "       Check the output above for details."
    exit 1
fi

# ── Verify token was saved ───────────────────────────────────────────────────

if [ ! -f "$TOKEN_FILE" ]; then
    echo "ERROR: tess_token.json was not created."
    echo "       Authorization may have failed or timed out."
    echo "       Try again, or check Outside Agents account status."
    exit 1
fi

echo "Token file confirmed: $TOKEN_FILE"
echo ""

# ── Test connection ──────────────────────────────────────────────────────────

echo "Running connection test (fetching agent profile)..."
echo ""

if python3 "$TESS_PY" --test; then
    echo ""
    echo "═══════════════════════════════════════════════"
    echo "  TESS authorization complete."
    echo ""
    echo "  Thunderbird OS is now connected to TESS."
    echo "  Tokens auto-refresh — no need to re-run this."
    echo ""
    echo "  MCP tools now live:"
    echo "    tess_list_trips       tess_get_booking"
    echo "    tess_search_bookings  tess_get_commissions"
    echo "    tess_list_clients     tess_get_client"
    echo "    tess_upload_document  tess_get_client_tasks"
    echo "    tess_test_connection"
    echo "═══════════════════════════════════════════════"
    echo ""
else
    echo ""
    echo "WARNING: Authorization succeeded but connection test failed."
    echo "         Token is saved — TESS may be temporarily unavailable."
    echo "         Re-test with: python3 ~/Thunderbird/thunderbird_tess.py --test"
    exit 1
fi
