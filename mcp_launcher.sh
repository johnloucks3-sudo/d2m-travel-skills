#!/bin/bash
# Thunderbird MCP Launcher — routes to best available transport.
# If persistent HTTP server (8767) is up → proxy through it (survives gateway restarts).
# Otherwise → fall back to direct stdio server.
set -a
source /home/john/Thunderbird/.env
[ -f /home/john/Thunderbird/.env.keys ] && source /home/john/Thunderbird/.env.keys
set +a
cd /home/john/Thunderbird

if curl -sf --max-time 2 http://127.0.0.1:8767/mcp -X POST \
    -H "Content-Type: application/json" \
    -H "Accept: application/json, text/event-stream" \
    -d '{"jsonrpc":"2.0","id":0,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"probe","version":"1.0"}}}' \
    > /dev/null 2>&1; then
    exec /home/john/Thunderbird/.venv/bin/python /home/john/Thunderbird/goose_mcp_proxy.py "$@"
else
    exec /home/john/Thunderbird/.venv/bin/python /home/john/Thunderbird/travel_mcp_server.py "$@"
fi
