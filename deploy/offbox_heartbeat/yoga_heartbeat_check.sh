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
#   1) Set TELEGRAM_BOT_TOKEN + COMMANDER_ID below (or export in cron env).
#   2) chmod +x yoga_heartbeat_check.sh
#   3) crontab -e  →  add:
#        */10 * * * * /path/to/yoga_heartbeat_check.sh >> /tmp/yoga_heartbeat.log 2>&1
#
set -u

# --- config -----------------------------------------------------------------
YOGA_URL="${YOGA_URL:-https://itinerary.d2mluxury.quest/}"   # public health surface
YOGA_TS_URL="${YOGA_TS_URL:-http://100.69.222.124/}"          # tailscale fallback
TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-***REMOVED-SECRET***}"
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
