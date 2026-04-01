#!/bin/bash
# Goose Slim MCP Launcher — lightweight server for Goose
# Only loads Google, file management, search, and intel tools (~57 vs 120+)
set -a
source /home/john/Thunderbird/.env
[ -f /home/john/Thunderbird/.env.keys ] && source /home/john/Thunderbird/.env.keys
set +a
cd /home/john/Thunderbird
exec /home/john/Thunderbird/.venv/bin/python /home/john/Thunderbird/goose_mcp_server.py "$@"
