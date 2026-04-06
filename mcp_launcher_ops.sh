#!/bin/bash
# Thunderbird MCP — OPS profile
# Tools: core + commissions, reconciliation, weekly reports, files API,
#        skills API, evernote, star protocol, browser, guest forms,
#        product intake, grant tools (~45 tools)
set -a
source /home/john/Thunderbird/.env
set +a
export MCP_PROFILE=ops
exec python3 /home/john/Thunderbird/core/mcp/travel_mcp_server.py "$@"
