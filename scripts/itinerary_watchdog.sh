#!/bin/bash
# itinerary_watchdog.sh — Health monitor for itinerary.d2mluxury.quest
# Runs every 5 min via itinerary-watchdog.timer (user-level systemd)
# Restarts itinerary-server if HTTP probe fails.
# Restarts cloudflared only on process death (not network blips — those self-heal).
# Logs all events. Writes status JSON for AM brief. No paging on auto-restart.

LOG=/home/john/Thunderbird/logs/itinerary_watchdog.log
STATUS_JSON=/home/john/Thunderbird/OpsCenter/itinerary_watchdog_status.json

log() { echo "[$(date -Iseconds)] $*" >> "$LOG"; }

ITINERARY_STATUS="ok"
CLOUDFLARED_STATUS="ok"
RESTARTED=0
NOTES=""

log "--- check ---"

# 1. HTTP probe — 401 = server alive + auth working, 200 = alive (open path)
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://localhost:8900/ 2>/dev/null || echo "000")
if [[ "$HTTP_CODE" == "401" || "$HTTP_CODE" == "200" ]]; then
    log "OK: itinerary-server 8900 → $HTTP_CODE"
else
    log "FAIL: itinerary-server 8900 → $HTTP_CODE — restarting"
    systemctl --user restart itinerary-server
    sleep 4
    HTTP_CODE2=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://localhost:8900/ 2>/dev/null || echo "000")
    log "POST-RESTART: 8900 → $HTTP_CODE2"
    ITINERARY_STATUS="restarted"
    NOTES="itinerary-server restarted (was $HTTP_CODE)"
    RESTARTED=1
fi

# 2. cloudflared — restart only on process death, not edge connection blips
if systemctl --user is-active --quiet cloudflared; then
    log "OK: cloudflared active"
else
    log "FAIL: cloudflared not active — restarting"
    systemctl --user restart cloudflared
    log "RESTARTED: cloudflared"
    CLOUDFLARED_STATUS="restarted"
    NOTES="${NOTES:+$NOTES; }cloudflared restarted (process was dead)"
    RESTARTED=1
fi

# 3. Write status for AM brief
python3 - <<PYEOF
import json, datetime
with open("$STATUS_JSON", "w") as f:
    json.dump({
        "last_check": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "itinerary_server": "$ITINERARY_STATUS",
        "cloudflared": "$CLOUDFLARED_STATUS",
        "restarted": bool($RESTARTED),
        "notes": "$NOTES"
    }, f, indent=2)
PYEOF

if [[ "$RESTARTED" == "1" ]]; then
    log "SUMMARY: restart(s) occurred — see notes: $NOTES"
else
    log "SUMMARY: green"
fi
