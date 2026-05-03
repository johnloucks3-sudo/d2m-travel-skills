#!/bin/bash
# Thunderbird MCP — FULL profile (headless Claude has access to ALL tools)
# Tools: 120+ including gmail, flight/hotel/tour search, intel, ops, dossiers, personas, learning, inbox
set -a
source /home/john/Thunderbird/.env
set +a
export MCP_PROFILE=full

# PYTHONPATH — flat module names still work after core/ reorg
export PYTHONPATH=/home/john/Thunderbird:\
/home/john/Thunderbird/core/intel:\
/home/john/Thunderbird/core/email:\
/home/john/Thunderbird/core/booking:\
/home/john/Thunderbird/core/travel:\
/home/john/Thunderbird/core/communication:\
/home/john/Thunderbird/core/ai_infra:\
/home/john/Thunderbird/core/client:\
/home/john/Thunderbird/core/ops:\
/home/john/Thunderbird/core/scheduling:\
/home/john/Thunderbird/core/watchtower:\
/home/john/Thunderbird/core/learning:\
/home/john/Thunderbird/core/mcp:\
/home/john/Thunderbird/api:\
/home/john/Thunderbird/agents:\
/home/john/Thunderbird/ops:\
/home/john/Thunderbird/business:\
/home/john/Thunderbird/comms:\
/home/john/Thunderbird/itinerary:\
/home/john/Thunderbird/intel:\
${PYTHONPATH}

exec /home/john/Thunderbird/.venv/bin/python \
  /home/john/Thunderbird/core/mcp/travel_mcp_server.py "$@"
