#!/usr/bin/env bash
# Starts MCP server in SSE mode + Cloudflare quick tunnel
# Usage: ./start_mcp_sse.sh [--http]

TRANSPORT_FLAG="${1:---sse}"
PORT=8765
LOG_DIR="$HOME/Thunderbird/logs"
mkdir -p "$LOG_DIR"

# Kill any previous instance on this port
EXISTING_PID=$(lsof -ti :$PORT 2>/dev/null)
if [ -n "$EXISTING_PID" ]; then
    echo "Killing previous process on port $PORT (PID: $EXISTING_PID)..."
    kill $EXISTING_PID 2>/dev/null
    sleep 1
fi

# Also kill any lingering cloudflared tunnels
pkill -f "cloudflared tunnel --url http://localhost:$PORT" 2>/dev/null

# Clear old logs
> "$LOG_DIR/mcp_sse.log"
> "$LOG_DIR/cloudflared.log"

cleanup() {
    echo "Shutting down..."
    kill $MCP_PID $CF_PID 2>/dev/null
    wait $MCP_PID $CF_PID 2>/dev/null
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# Start MCP server
source "$HOME/Thunderbird/venv/bin/activate"
PYTHONPATH="$HOME/Thunderbird" python "$HOME/Thunderbird/travel_mcp_server.py" \
    $TRANSPORT_FLAG --port=$PORT 2>&1 | tee "$LOG_DIR/mcp_sse.log" &
MCP_PID=$!
sleep 2

# Verify MCP started
if ! kill -0 $MCP_PID 2>/dev/null; then
    echo "ERROR: MCP server failed to start. Check logs/mcp_sse.log"
    exit 1
fi
echo "MCP server running (PID: $MCP_PID)"

# Start cloudflared quick tunnel, capture URL
cloudflared tunnel --url http://localhost:$PORT 2>&1 | tee "$LOG_DIR/cloudflared.log" &
CF_PID=$!

# Wait for tunnel URL to appear in log (up to 15s)
TUNNEL_URL=""
for i in $(seq 1 30); do
    TUNNEL_URL=$(grep -oP 'https://[a-z0-9-]+\.trycloudflare\.com' "$LOG_DIR/cloudflared.log" | head -1)
    if [ -n "$TUNNEL_URL" ]; then
        echo "$TUNNEL_URL" > "$HOME/Thunderbird/tunnel_url.txt"
        echo "============================="
        echo "TUNNEL URL: $TUNNEL_URL"
        echo "============================="
        break
    fi
    sleep 0.5
done

if [ -z "$TUNNEL_URL" ]; then
    echo "WARNING: Could not capture tunnel URL within 15s"
fi

# Keep running until killed
wait
