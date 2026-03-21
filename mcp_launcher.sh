#!/bin/bash
# Thunderbird MCP Launcher — sources .env before starting stdio server
# This ensures ANTHROPIC_API_KEY and other keys reach the MCP subprocess
set -a
source /home/john/Thunderbird/.env
set +a
exec /home/john/Thunderbird/.venv/bin/python travel_mcp_server.py "$@"
