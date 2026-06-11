#!/bin/bash
# yoga_heartbeat_check.sh — OFF-BOX heartbeat for the Yoga server.
# Staged 2026-06-10 (Sterling/A7). MUST run on a machine OTHER than Yoga
# (Chromebook / phone / VPS) so it can detect when Yoga itself goes dark.
#
# Logic: probe Yoga's health endpoint every 10 min via cron. On a miss
# (no HTTP response), page the Commander on Telegram. Self-deduplicates so
# it pages once per outage, not every 10 min.
#
# Install (on the off-box host):
#   1) chmod +x yoga_heartbeat_check.sh
#   2) crontab -e  →  add (token supplied via env, NOT hardcoded):
#        */10 * * * * TELEGRAM_BOT_TOKEN='8754681793:<token>' COMMANDER_ID='7554895206' /path/to/yoga_heartbeat_check.sh >> /tmp/yoga_heartbeat.log 2>&1
#      (the D2MC2C bot token is in Yoga's /home/john/Thunderbird/.env as TELEGRAM_BOT_TOKEN)
#
set -u

# --- config -----------------------------------------------------------------
YOGA_URL="${YOGA_URL:-https://itinerary.d2mluxury.quest/}"   # public health surface
YOGA_TS_URL="${YOGA_TS_URL:-http://100.69.222.124/}"          # tailscale fallback
# SECRET HYGIENE: token MUST come from the environment — never hardcode it in a
# git-tracked file. Set it in the off-box crontab line or a sourced env file.
TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:?set TELEGRAM_BOT_TOKEN in the cron env}"
COMMANDER_ID="${COMMANDER_ID:-7554895206}"
STATE_FILE="${STATE_FILE:-/tmp/yoga_heartbeat.state}"
# ----------------------------------------------------------------------------

probe() {
    local code
    code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 12 "$1" 2>/dev/null)
    [ -n "$code" ] && [ "$code" != "000" ]
}

if probe "$YOGA_URL" || probe "$YOGA_TS_URL"; then
    # alive — clear any outage state, page recovery if we were down
    if [ -f "$STATE_FILE" ]; then
        rm -f "$STATE_FILE"
        curl -sf --max-time 12 "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
            -d chat_id="${COMMANDER_ID}" \
            -d text="🟢 HEARTBEAT: Yoga is back online ($(date -Is))." >/dev/null 2>&1
    fi
    echo "$(date -Is) yoga OK"
    exit 0
fi

# miss — page once per outage
if [ ! -f "$STATE_FILE" ]; then
    touch "$STATE_FILE"
    curl -sf --max-time 12 "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
        -d chat_id="${COMMANDER_ID}" \
        -d text="🔴 HEARTBEAT MISS: Yoga unreachable at $(date -Is). Both public + tailscale probes failed. The Wing may be DOWN — no other monitor can see this." >/dev/null 2>&1
fi
echo "$(date -Is) yoga DOWN — paged"
exit 1
