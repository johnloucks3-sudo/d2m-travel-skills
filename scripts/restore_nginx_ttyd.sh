#!/usr/bin/env bash
# restore_nginx_ttyd.sh — Gate 0 recovery for ttyd terminal access
# Run this whenever code.d2mluxury.quest goes dark or nginx loses its config.
# No args needed. Requires sudo (passwordless via /etc/sudoers.d/john-nginx-ttyd).

set -euo pipefail

CANONICAL="/home/john/Thunderbird/infra/nginx/ttyd.conf"
HTPASSWD_BAK="/home/john/Thunderbird/infra/nginx/ttyd.htpasswd.bak"
DEST="/etc/nginx/vhosts.d/ttyd.conf"
HTPASSWD_DEST="/etc/nginx/ttyd.htpasswd"
LOG="/home/john/Thunderbird/logs/nginx_ttyd_restore.log"

log() { echo "[$(date -Iseconds)] $*" | tee -a "$LOG"; }

log "=== restore_nginx_ttyd.sh START ==="

# 1. Restore ttyd.conf if missing or empty
if [[ ! -s "$DEST" ]]; then
    log "MISSING: $DEST — restoring from canonical"
    sudo cp "$CANONICAL" "$DEST"
    sudo chmod 644 "$DEST"
    log "RESTORED: $DEST"
else
    log "OK: $DEST present ($(wc -c < "$DEST") bytes)"
fi

# 2. Restore htpasswd if missing
if [[ ! -s "$HTPASSWD_DEST" ]]; then
    log "MISSING: $HTPASSWD_DEST — restoring from backup"
    sudo cp "$HTPASSWD_BAK" "$HTPASSWD_DEST"
    sudo chmod 640 "$HTPASSWD_DEST"
    log "RESTORED: $HTPASSWD_DEST"
else
    log "OK: $HTPASSWD_DEST present"
fi

# 3. Test nginx config
if sudo nginx -t 2>&1 | tee -a "$LOG" | grep -q "test failed"; then
    log "ERROR: nginx config test FAILED — not reloading"
    exit 1
fi

# 4. Reload nginx if we changed anything (or always, safe either way)
sudo systemctl reload nginx
log "RELOADED: nginx"

# 5. Verify ttyd is still running
if systemctl --user is-active --quiet ttyd-terminal.service; then
    log "OK: ttyd-terminal.service running"
else
    log "WARNING: ttyd-terminal.service not running — starting"
    systemctl --user start ttyd-terminal.service
    log "STARTED: ttyd-terminal.service"
fi

# 6. Quick connectivity check
sleep 1
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 3 http://127.0.0.1:8099/ 2>/dev/null || echo "000")
if [[ "$HTTP_CODE" == "401" ]]; then
    log "VERIFIED: 8099 returning 401 (auth gate live)"
elif [[ "$HTTP_CODE" == "000" ]]; then
    log "ERROR: 8099 not responding — check nginx and ttyd"
    exit 1
else
    log "WARN: 8099 returning $HTTP_CODE (expected 401)"
fi

log "=== restore_nginx_ttyd.sh COMPLETE ==="
