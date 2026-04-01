#!/bin/bash
# ============================================================
# mcp_bridge.sh — CLI bridge to Thunderbird MCP tools for Goose
# ============================================================
# Usage:
#   mcp_bridge.sh <tool_name> [json_args]
#   mcp_bridge.sh --list                    # list all available tools
#   mcp_bridge.sh --help                    # show usage
#
# Examples:
#   mcp_bridge.sh system_health_check '{"format":"summary"}'
#   mcp_bridge.sh gmail_search_messages '{"query":"from:julie","max_results":5}'
#   mcp_bridge.sh drive_search '{"query":"Westbrook"}'
#   mcp_bridge.sh --list
#
# How it works:
#   Spawns the full Thunderbird MCP server over stdio, sends a JSON-RPC
#   initialize + tools/call request, captures the result, and exits.
#   One-shot. No persistent server.
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="${SCRIPT_DIR}/.venv/bin/python"
ENV_FILE="${SCRIPT_DIR}/.env"
ENV_KEYS="${SCRIPT_DIR}/.env.keys"

# ── Usage ──
usage() {
    cat <<'USAGE'
mcp_bridge.sh — CLI bridge to 120+ Thunderbird MCP tools

Usage:
  mcp_bridge.sh <tool_name> [json_args]    Call a tool
  mcp_bridge.sh --list                     List all available tools
  mcp_bridge.sh --list <filter>            List tools matching filter
  mcp_bridge.sh --help                     This help

Examples:
  mcp_bridge.sh system_health_check
  mcp_bridge.sh system_health_check '{"format":"json"}'
  mcp_bridge.sh gmail_search_messages '{"query":"from:julie","max_results":5}'
  mcp_bridge.sh --list gmail
USAGE
    exit 0
}

# ── Args ──
[[ $# -eq 0 ]] && usage
[[ "$1" == "--help" || "$1" == "-h" ]] && usage

# ── Python bridge script (inline) ──
# This does the heavy lifting: imports the MCP server, calls the tool directly
# via the registered async function, returns JSON.
# We bypass stdio protocol entirely — direct Python call is faster and simpler.

if [[ "$1" == "--list" ]]; then
    FILTER="${2:-}"
    exec "${VENV_PYTHON}" -c "
import sys, os, json
os.chdir('${SCRIPT_DIR}')
sys.path.insert(0, '${SCRIPT_DIR}')

# Load env
from dotenv import load_dotenv
load_dotenv('${ENV_FILE}')
if os.path.exists('${ENV_KEYS}'):
    load_dotenv('${ENV_KEYS}', override=True)

# Suppress all logging during import
import logging
logging.disable(logging.CRITICAL)

from travel_mcp_server import mcp

tools = sorted(mcp._tool_manager._tools.keys())
filt = '${FILTER}'.lower()
if filt:
    tools = [t for t in tools if filt in t.lower()]

for t in tools:
    print(t)
print(f'--- {len(tools)} tools ---')
" 2>/dev/null
fi

TOOL_NAME="$1"
TOOL_ARGS="${2:-{\}}"

# Validate JSON args
echo "$TOOL_ARGS" | "${VENV_PYTHON}" -c "import sys,json; json.load(sys.stdin)" 2>/dev/null || {
    echo '{"error": "Invalid JSON arguments. Use: mcp_bridge.sh tool_name '\''{}'\''"}' >&2
    exit 1
}

# ── Call the tool directly via Python ──
exec "${VENV_PYTHON}" - "$TOOL_NAME" "$TOOL_ARGS" <<'PYTHON_BRIDGE'
import sys, os, json, asyncio, logging

os.chdir(os.environ.get("THUNDERBIRD_HOME", "/home/john/Thunderbird"))
sys.path.insert(0, os.getcwd())

# Load env
from dotenv import load_dotenv
load_dotenv(".env")
if os.path.exists(".env.keys"):
    load_dotenv(".env.keys", override=True)

# Suppress all logging during import — clean stdout for Goose
logging.disable(logging.CRITICAL)

tool_name = sys.argv[1]
tool_args = json.loads(sys.argv[2])

try:
    from travel_mcp_server import mcp

    # Access the tool registry
    tool_mgr = mcp._tool_manager
    if tool_name not in tool_mgr._tools:
        # Try partial match
        matches = [t for t in tool_mgr._tools if tool_name in t]
        if matches:
            print(json.dumps({
                "error": f"Tool '{tool_name}' not found. Did you mean: {matches[:5]}",
                "status": "error"
            }))
        else:
            print(json.dumps({
                "error": f"Tool '{tool_name}' not found. Use --list to see available tools.",
                "status": "error"
            }))
        sys.exit(1)

    # Get the tool's callable
    tool_entry = tool_mgr._tools[tool_name]
    fn = tool_entry.fn

    # Call it (async tools need event loop)
    if asyncio.iscoroutinefunction(fn):
        result = asyncio.run(fn(**tool_args))
    else:
        result = fn(**tool_args)

    # Output — try to parse if it's JSON string, otherwise wrap
    if isinstance(result, str):
        try:
            parsed = json.loads(result)
            print(json.dumps({"status": "success", "tool": tool_name, "result": parsed}, indent=2))
        except json.JSONDecodeError:
            print(json.dumps({"status": "success", "tool": tool_name, "result": result}, indent=2))
    elif isinstance(result, (dict, list)):
        print(json.dumps({"status": "success", "tool": tool_name, "result": result}, indent=2))
    else:
        print(json.dumps({"status": "success", "tool": tool_name, "result": str(result)}, indent=2))

except Exception as e:
    print(json.dumps({"status": "error", "tool": tool_name, "error": str(e)}, indent=2))
    sys.exit(1)
PYTHON_BRIDGE
