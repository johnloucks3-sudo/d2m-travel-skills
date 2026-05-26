#!/bin/bash
LOG=/home/john/Thunderbird/logs/nginx_ttyd_restore.log
RESTORED=0

for CONF in ttyd mcp code-server syncthing; do
    DEST="/etc/nginx/vhosts.d/${CONF}.conf"
    SRC="/home/john/Thunderbird/infra/nginx/${CONF}.conf"
    if [ ! -s "$DEST" ]; then
        cp "$SRC" "$DEST" && chmod 644 "$DEST"
        echo "[$(date -Iseconds)] RESTORED $DEST" >> "$LOG"
        RESTORED=1
    fi
done

if [ "$RESTORED" = "1" ]; then
    nginx -t 2>/dev/null || exit 1
    NGINX_PID=$(pgrep -ox nginx 2>/dev/null)
    if [ -n "$NGINX_PID" ]; then
        kill -HUP "$NGINX_PID"
        echo "[$(date -Iseconds)] RELOADED nginx (PID $NGINX_PID)" >> "$LOG"
    else
        systemctl start nginx
        echo "[$(date -Iseconds)] STARTED nginx via systemctl" >> "$LOG"
    fi
fi
