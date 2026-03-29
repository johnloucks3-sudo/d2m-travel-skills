#!/bin/bash
# Thunderbird MCP Launcher — sources .env before starting stdio server
# This ensures ANTHROPIC_API_KEY and other keys reach the MCP subprocess
set -a
source /home/john/Thunderbird/.env
# Defensive: source legacy .env.keys if it still exists (all keys consolidated to .env)
[ -f /home/john/Thunderbird/.env.keys ] && source /home/john/Thunderbird/.env.keys
set +a
cd /home/john/Thunderbird
exec /home/john/Thunderbird/.venv/bin/python /home/john/Thunderbird/travel_mcp_server.py "$@"
