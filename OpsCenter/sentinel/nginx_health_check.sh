#!/bin/bash
# nginx_health_check.sh — Thunderbird Tier-3 detection layer
# Rebuilt 2026-06-10 (Sterling/A7) — original was deleted, never committed.
# Curls the local nginx health endpoint; pages Commander on Telegram if it fails.
# Env: TELEGRAM_BOT_TOKEN, TELEGRAM_COMMANDER_ID (loaded by unit via EnvironmentFile).
set -u
URL="${NGINX_HEALTH_URL:-http://127.0.0.1/}"
# nginx is alive if it returns ANY HTTP status (even 403/404) — a response proves the
# daemon is serving. We only page when curl gets no HTTP response at all (000 = down/refused).
CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$URL" 2>/dev/null)
if [ -n "$CODE" ] && [ "$CODE" != "000" ]; then
    echo "$(date -Is) nginx OK ($URL → HTTP $CODE)"
    exit 0
fi
echo "$(date -Is) nginx DOWN ($URL → no HTTP response) — paging Commander"
curl -sf --max-time 10 "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    -d chat_id="${TELEGRAM_COMMANDER_ID}" \
    -d text="🔴 SENTINEL: nginx health check FAILED at $URL ($(date -Is)) — no HTTP response. Web/ttyd front door may be down." >/dev/null 2>&1
exit 1
