#!/usr/bin/env bash
# Launches the official AgentMail MCP server, injecting the API key from the
# gitignored credentials file instead of a literal secret in .mcp.json.
set -euo pipefail
CREDS="/home/john/Thunderbird/config/agentmail_credentials.json"
export AGENTMAIL_API_KEY
AGENTMAIL_API_KEY=$(python3 -c "import json; print(json.load(open('$CREDS'))['api_key'])")
exec npx -y agentmail-mcp
