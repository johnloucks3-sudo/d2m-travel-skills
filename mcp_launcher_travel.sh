#!/bin/bash
# Thunderbird MCP — TRAVEL profile
# Tools: core + hotels, flights, tours, excursions, transfers, dining,
#        TESS, TAAP, fare watch, trip architect, outside agents,
#        itinerary pipeline, ship comparison (~50 tools)
set -a
source /home/john/Thunderbird/.env
set +a
export MCP_PROFILE=travel
exec /home/john/Thunderbird/.venv/bin/python travel_mcp_server.py "$@"
