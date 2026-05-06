#!/bin/bash
# Thunderbird MCP Launcher — routes to best available transport.
# If persistent HTTP server (8767) is up → proxy through it (survives gateway restarts).
# Otherwise → fall back to direct stdio server.
set -a
source /home/john/Thunderbird/.env
[ -f /home/john/Thunderbird/.env.keys ] && source /home/john/Thunderbird/.env.keys
set +a
cd /home/john/Thunderbird

export PYTHONPATH="/home/john/Thunderbird:/home/john/Thunderbird/core/ai_infra:/home/john/Thunderbird/core/booking:/home/john/Thunderbird/core/client:/home/john/Thunderbird/core/communication:/home/john/Thunderbird/core/email:/home/john/Thunderbird/core/intel:/home/john/Thunderbird/core/learning:/home/john/Thunderbird/core/mcp:/home/john/Thunderbird/core/memory:/home/john/Thunderbird/core/ops:/home/john/Thunderbird/core/scheduling:/home/john/Thunderbird/core/travel:/home/john/Thunderbird/core/watchtower:/home/john/Thunderbird/itinerary:/home/john/Thunderbird/api:/home/john/Thunderbird/agents:/home/john/Thunderbird/business:/home/john/Thunderbird/comms:/home/john/Thunderbird/templates"

exec /home/john/Thunderbird/.venv/bin/python /home/john/Thunderbird/core/mcp/travel_mcp_server.py "$@"
