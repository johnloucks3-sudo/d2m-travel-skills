#!/bin/bash
# Thunderbird MCP — CORE profile
# Tools: gmail, drive, dossiers, personas, learning, inbox, sss (~25 tools)
set -a
source /home/john/Thunderbird/.env
set +a
export MCP_PROFILE=core
exec /home/john/Thunderbird/.venv/bin/python travel_mcp_server.py "$@"
