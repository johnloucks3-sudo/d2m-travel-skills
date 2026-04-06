#!/bin/bash
# Thunderbird MCP — INTEL profile
# Tools: core + world intel, ship intel, tech monitor, x-osint, innovation,
#        academic, competitive surveillance, price monitor, email intel,
#        airline monitor, intel crew, crewai, a2a (~40 tools)
set -a
source /home/john/Thunderbird/.env
set +a
export MCP_PROFILE=intel
exec python3 /home/john/Thunderbird/core/mcp/travel_mcp_server.py "$@"
