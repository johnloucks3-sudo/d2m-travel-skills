#!/bin/bash
# Thunderbird MCP — CORE profile
# Tools: gmail, drive, dossiers, personas, learning, inbox, sss (~25 tools)
set -a
source /home/john/Thunderbird/.env
set +a
export MCP_PROFILE=core
exec python3 /home/john/Thunderbird/core/mcp/travel_mcp_server.py "$@"
