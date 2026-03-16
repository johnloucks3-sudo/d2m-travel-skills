#!/usr/bin/env bash
# Starts the named Cloudflare tunnel for api.d2mluxury.quest
# Routes to thunderbird_api.py on localhost:8766
# Usage: ./start_tunnel.sh

LOG_DIR="$HOME/Thunderbird/logs"
mkdir -p "$LOG_DIR"

# Kill any previous tunnel
pkill -f "cloudflared tunnel run thunderbird" 2>/dev/null
sleep 1

# Clear old log
> "$LOG_DIR/cloudflared_named.log"

# Start named tunnel
cloudflared tunnel run thunderbird >> "$LOG_DIR/cloudflared_named.log" 2>&1 &
TUNNEL_PID=$!
sleep 2

if kill -0 $TUNNEL_PID 2>/dev/null; then
    echo "Tunnel running (PID: $TUNNEL_PID)"
    echo "URL: https://api.d2mluxury.quest"
else
    echo "ERROR: Tunnel failed to start. Check logs/cloudflared_named.log"
    exit 1
fi
