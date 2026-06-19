#!/bin/bash
# dani_token_activate.sh — Wire new Dani Telegram token and restart gateway
# Usage: bash scripts/dani_token_activate.sh <NEW_TOKEN_FROM_BOTFATHER>
# Takes ~10 seconds. Dani goes live immediately after.

set -e

NEW_TOKEN="$1"

if [ -z "$NEW_TOKEN" ]; then
    echo "Usage: bash scripts/dani_token_activate.sh <TOKEN>"
    echo "Get the token from @BotFather → /mybots → @d2m_dani_bot → API Token → Revoke and regenerate"
    exit 1
fi

# Validate token format (digits:alphanumeric)
if ! echo "$NEW_TOKEN" | grep -qE '^[0-9]+:[A-Za-z0-9_-]+$'; then
    echo "ERROR: Token format looks wrong. Expected: 1234567890:ABCdef..."
    exit 1
fi

# Test it works before writing
echo "Testing token with Telegram API..."
RESULT=$(curl -s "https://api.telegram.org/bot${NEW_TOKEN}/getMe")
BOT_NAME=$(echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('result',{}).get('username','UNKNOWN'))" 2>/dev/null)

if [ "$BOT_NAME" = "UNKNOWN" ] || [ -z "$BOT_NAME" ]; then
    echo "ERROR: Token rejected by Telegram API."
    echo "Response: $RESULT"
    exit 1
fi

echo "✅ Token valid — bot: @$BOT_NAME"

# Write to .env
THUNDERBIRD_DIR="$(dirname "$0")/.."
ENV_FILE="$THUNDERBIRD_DIR/.env"
LIVE_ENV="/home/john/.telegram_gw_live.env"

# Update .env
if grep -q "^TELEGRAM_DANI_TOKEN=" "$ENV_FILE"; then
    sed -i "s|^TELEGRAM_DANI_TOKEN=.*|TELEGRAM_DANI_TOKEN=$NEW_TOKEN|" "$ENV_FILE"
    echo "✅ Updated .env"
else
    echo "TELEGRAM_DANI_TOKEN=$NEW_TOKEN" >> "$ENV_FILE"
    echo "✅ Added to .env"
fi

# Update live env
if [ -f "$LIVE_ENV" ]; then
    if grep -q "^TELEGRAM_DANI_TOKEN=" "$LIVE_ENV"; then
        sed -i "s|^TELEGRAM_DANI_TOKEN=.*|TELEGRAM_DANI_TOKEN=$NEW_TOKEN|" "$LIVE_ENV"
        echo "✅ Updated .telegram_gw_live.env"
    else
        echo "TELEGRAM_DANI_TOKEN=$NEW_TOKEN" >> "$LIVE_ENV"
        echo "✅ Added to .telegram_gw_live.env"
    fi
fi

# Restart gateway
echo "Restarting Telegram gateway..."
systemctl --user restart thunderbird-telegram-gw.service
sleep 4

# Verify Dani is polling
STATUS=$(systemctl --user is-active thunderbird-telegram-gw.service)
if [ "$STATUS" = "active" ]; then
    # Check logs for Dani poll thread
    if journalctl --user -u thunderbird-telegram-gw.service -n 30 --no-pager 2>/dev/null | grep -q "\[Dani\] Poll"; then
        echo ""
        echo "🦅 Dani is LIVE — @$BOT_NAME polling."
        echo "Clients can reach her at: https://t.me/$BOT_NAME"
    else
        echo "⚠️  Gateway running but Dani poll thread not confirmed — check logs:"
        echo "    journalctl --user -u thunderbird-telegram-gw.service -n 30"
    fi
else
    echo "❌ Gateway failed to start — status: $STATUS"
    exit 1
fi
