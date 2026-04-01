#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# mcp_bridge.sh — Thunderbird MCP Bridge for Goose
# ═══════════════════════════════════════════════════════════════════════════════
# Gives Goose (or any CLI agent) access to all 292 Thunderbird MCP tools via
# a single shell command. Routes through safe_cli_gate.py for policy enforcement.
#
# USAGE:
#   mcp_bridge.sh <command> [args...]
#
# COMMANDS:
#   call   <tool_name> [json_args]   — Call an MCP tool (through safe_cli_gate)
#   raw    <tool_name> [json_args]   — Call an MCP tool (bypass gate — DANGER)
#   list   [filter]                  — List available tools (optional grep filter)
#   search <keyword>                 — Search tools by name
#   schema <tool_name>               — Show tool input schema
#   health                           — Check MCP server health
#   help                             — Show this help
#
# EXAMPLES:
#   mcp_bridge.sh call gmail_search_messages '{"query":"from:silversea"}'
#   mcp_bridge.sh list cruise
#   mcp_bridge.sh schema search_hotels
#   mcp_bridge.sh health
#
# ARCHITECTURE:
#   Goose → mcp_bridge.sh → safe_cli_gate.py → HTTP POST → MCP server (8765)
#
# Standing Order: All calls through 'call' are policy-gated.
#                 'raw' bypasses the gate — use only for debugging.
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

# ── Configuration ─────────────────────────────────────────────────────────────
MCP_HOST="${MCP_HOST:-127.0.0.1}"
MCP_PORT="${MCP_PORT:-8765}"
MCP_ENDPOINT="http://${MCP_HOST}:${MCP_PORT}/mcp"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
THUNDERBIRD_ROOT="$(dirname "$SCRIPT_DIR")"
SAFE_CLI_GATE="${SCRIPT_DIR}/safe_cli_gate.py"
PYTHON="${THUNDERBIRD_ROOT}/.venv/bin/python"
BRIDGE_LOG="${SCRIPT_DIR}/mcp_bridge.log"

# Caller identification — Goose by default, overridable
AGENT="${MCP_BRIDGE_AGENT:-Goose}"

# ── Helpers ───────────────────────────────────────────────────────────────────

_log() {
    local ts
    ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "${ts} [mcp_bridge] $*" >> "$BRIDGE_LOG"
}

_die() {
    echo "ERROR: $*" >&2
    _log "ERROR: $*"
    exit 1
}

_json_rpc() {
    # Send a JSON-RPC request to the MCP server
    local method="$1"
    local params="${2:-null}"
    local id="${3:-1}"
    local payload
    payload=$(cat <<JSONEOF
{"jsonrpc":"2.0","method":"${method}","params":${params},"id":${id}}
JSONEOF
)
    curl -sf -X POST "$MCP_ENDPOINT" \
        -H 'Content-Type: application/json' \
        -H 'Accept: application/json, text/event-stream' \
        --max-time 120 \
        -d "$payload" 2>/dev/null
}

_uuid() {
    # Generate a task ID
    python3 -c "import uuid; print(f'MB-{uuid.uuid4().hex[:12]}')"
}

_timestamp() {
    date -u +%Y-%m-%dT%H:%M:%SZ
}

# ── Commands ──────────────────────────────────────────────────────────────────

cmd_health() {
    echo "Checking MCP server at ${MCP_ENDPOINT}..."
    local resp
    resp=$(_json_rpc "tools/list" "null" "health-check" 2>&1) || {
        echo "FAIL — MCP server not responding at ${MCP_ENDPOINT}"
        echo "Check: systemctl --user status thunderbird-mcp"
        return 1
    }

    local count
    count=$(echo "$resp" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('result',{}).get('tools',[])))" 2>/dev/null) || count="?"

    echo "OK — MCP server alive, ${count} tools available"
    _log "health: OK, ${count} tools"
    return 0
}

cmd_list() {
    local filter="${1:-}"
    local resp
    resp=$(_json_rpc "tools/list") || _die "MCP server not responding"

    if [ -z "$filter" ]; then
        echo "$resp" | python3 -c "
import sys, json
d = json.load(sys.stdin)
tools = d.get('result', {}).get('tools', [])
print(f'Available MCP tools ({len(tools)} total):')
print('=' * 50)
for t in sorted(tools, key=lambda x: x['name']):
    desc = t.get('description', '')[:60]
    print(f'  {t[\"name\"]:<45} {desc}')
"
    else
        echo "$resp" | python3 -c "
import sys, json
d = json.load(sys.stdin)
tools = d.get('result', {}).get('tools', [])
filt = '${filter}'.lower()
matches = [t for t in tools if filt in t['name'].lower() or filt in t.get('description', '').lower()]
print(f'Tools matching \"{filt}\" ({len(matches)} of {len(tools)}):')
print('=' * 50)
for t in sorted(matches, key=lambda x: x['name']):
    desc = t.get('description', '')[:60]
    print(f'  {t[\"name\"]:<45} {desc}')
"
    fi
}

cmd_search() {
    [ -z "${1:-}" ] && _die "Usage: mcp_bridge.sh search <keyword>"
    cmd_list "$1"
}

cmd_schema() {
    local tool_name="${1:-}"
    [ -z "$tool_name" ] && _die "Usage: mcp_bridge.sh schema <tool_name>"

    local resp
    resp=$(_json_rpc "tools/list") || _die "MCP server not responding"

    echo "$resp" | python3 -c "
import sys, json
d = json.load(sys.stdin)
tools = d.get('result', {}).get('tools', [])
name = '${tool_name}'
match = [t for t in tools if t['name'] == name]
if not match:
    # Try fuzzy match
    match = [t for t in tools if name.lower() in t['name'].lower()]
    if match:
        print(f'No exact match for \"{name}\". Did you mean:')
        for t in match:
            print(f'  {t[\"name\"]}')
        sys.exit(1)
    else:
        print(f'Tool \"{name}\" not found')
        sys.exit(1)
tool = match[0]
print(f'Tool: {tool[\"name\"]}')
print(f'Description: {tool.get(\"description\", \"N/A\")}')
print()
schema = tool.get('inputSchema', {})
if schema:
    print('Input Schema:')
    print(json.dumps(schema, indent=2))
else:
    print('No input schema defined')
"
}

cmd_call() {
    local tool_name="${1:-}"
    [ -z "$tool_name" ] && _die "Usage: mcp_bridge.sh call <tool_name> [json_args]"
    local args="${2:-{}}"
    local task_id
    task_id=$(_uuid)
    local ts
    ts=$(_timestamp)

    _log "CALL tool=${tool_name} task=${task_id} agent=${AGENT}"

    # ── Build ExecutionManifest ───────────────────────────────────────────
    local manifest
    manifest=$(python3 -c "
import json, sys
manifest = {
    'task_id': '${task_id}',
    'timestamp': '${ts}',
    'originating_agent': '${AGENT}',
    'requested_tool': '${tool_name}',
    'arguments': json.loads('''${args}'''),
    'security_context': {
        'pii_check': True,
        'wf17_gate': False,
        'directive_enforcement': 'PASSED'
    }
}
print(json.dumps(manifest))
" 2>&1) || _die "Failed to build manifest — check JSON args: ${args}"

    # ── Policy gate ───────────────────────────────────────────────────────
    local gate_result
    gate_result=$("$PYTHON" "$SAFE_CLI_GATE" "$manifest" 2>/dev/null) || {
        local exit_code=$?
        echo "$gate_result"
        _log "BLOCKED tool=${tool_name} task=${task_id} exit=${exit_code}"
        return $exit_code
    }

    # Check if gate returned a BLOCKED status (exit 0 but blocked in JSON)
    if echo "$gate_result" | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if d.get('status')=='BLOCKED' else 1)" 2>/dev/null; then
        echo "$gate_result"
        _log "BLOCKED (policy) tool=${tool_name} task=${task_id}"
        return 2
    fi

    # ── Gate passed but mcp2cli may not exist — call MCP server directly ─
    # If safe_cli_gate returned OK with mcp2cli output, use that.
    # Otherwise, fall through to direct HTTP call.
    if echo "$gate_result" | python3 -c "
import sys,json
d=json.load(sys.stdin)
if d.get('status')=='OK' and d.get('stdout','').strip():
    print(d['stdout'])
    sys.exit(0)
sys.exit(1)
" 2>/dev/null; then
        _log "OK (via mcp2cli) tool=${tool_name} task=${task_id}"
        return 0
    fi

    # ── Direct HTTP call to MCP server ────────────────────────────────────
    local mcp_resp
    mcp_resp=$(_json_rpc "tools/call" "{\"name\":\"${tool_name}\",\"arguments\":$(echo "$args")}" "$task_id") || {
        _die "MCP server call failed for tool=${tool_name}. Is thunderbird-mcp running?"
    }

    # Extract and format result
    echo "$mcp_resp" | python3 -c "
import sys, json
d = json.load(sys.stdin)
if 'error' in d:
    err = d['error']
    print(json.dumps({'status': 'ERROR', 'code': err.get('code'), 'message': err.get('message')}, indent=2))
    sys.exit(1)
result = d.get('result', {})
content = result.get('content', [])
for item in content:
    if item.get('type') == 'text':
        # Try to parse as JSON for pretty printing
        try:
            parsed = json.loads(item['text'])
            print(json.dumps(parsed, indent=2))
        except (json.JSONDecodeError, TypeError):
            print(item['text'])
    elif item.get('type') == 'image':
        print(f'[IMAGE: {item.get(\"mimeType\", \"unknown\")} - {len(item.get(\"data\", \"\"))} bytes]')
    else:
        print(json.dumps(item, indent=2))
"
    local mcp_exit=$?

    _log "OK tool=${tool_name} task=${task_id}"
    return $mcp_exit
}

cmd_raw() {
    # Direct MCP call — no policy gate. For debugging only.
    local tool_name="${1:-}"
    [ -z "$tool_name" ] && _die "Usage: mcp_bridge.sh raw <tool_name> [json_args]"
    local args="${2:-{}}"
    local task_id
    task_id=$(_uuid)

    _log "RAW (ungated) tool=${tool_name} task=${task_id}"
    echo "WARNING: Bypassing safe_cli_gate policy engine" >&2

    local mcp_resp
    mcp_resp=$(_json_rpc "tools/call" "{\"name\":\"${tool_name}\",\"arguments\":${args}}" "$task_id") || {
        _die "MCP server call failed for tool=${tool_name}"
    }

    echo "$mcp_resp" | python3 -c "
import sys, json
d = json.load(sys.stdin)
if 'error' in d:
    print(json.dumps(d['error'], indent=2))
    sys.exit(1)
result = d.get('result', {})
content = result.get('content', [])
for item in content:
    if item.get('type') == 'text':
        try:
            parsed = json.loads(item['text'])
            print(json.dumps(parsed, indent=2))
        except (json.JSONDecodeError, TypeError):
            print(item['text'])
    else:
        print(json.dumps(item, indent=2))
"
    return $?
}

cmd_help() {
    cat <<'HELPEOF'
═══════════════════════════════════════════════════════════════════════
  Thunderbird MCP Bridge — CLI access to 292 MCP tools
═══════════════════════════════════════════════════════════════════════

COMMANDS:
  call   <tool> [json_args]   Call a tool (policy-gated via safe_cli_gate)
  raw    <tool> [json_args]   Call a tool (NO policy gate — debug only)
  list   [filter]             List tools (optional keyword filter)
  search <keyword>            Search tools by name/description
  schema <tool>               Show tool input schema
  health                      Check MCP server status
  help                        This message

ENVIRONMENT:
  MCP_HOST              MCP server host (default: 127.0.0.1)
  MCP_PORT              MCP server port (default: 8765)
  MCP_BRIDGE_AGENT      Calling agent name (default: Goose)

EXAMPLES:
  # Check server health
  mcp_bridge.sh health

  # List all cruise-related tools
  mcp_bridge.sh list cruise

  # Get schema for a tool
  mcp_bridge.sh schema search_hotels

  # Search Gmail
  mcp_bridge.sh call gmail_search_messages '{"query":"from:silversea","max_results":5}'

  # Run innovation scan
  mcp_bridge.sh call run_innovation_scan '{}'

  # List Drive files
  mcp_bridge.sh call drive_list_files '{"folder_name":"D2M Trip Dossiers"}'

  # Check system health
  mcp_bridge.sh call system_health_check '{}'

POLICY GATE:
  The 'call' command routes through safe_cli_gate.py which enforces:
  - Tool whitelist/blacklist (no delete/trash/send without approval)
  - PII detection (SSN, credit card, phone blocked in args)
  - Banned string detection (no "Love Group Travel", no "rm -rf")
  - Agent verification (only Goose, Claude, Hale recognized)
  - All calls logged to star_protocol_log.csv
  - Blocked calls alert Commander via Telegram

═══════════════════════════════════════════════════════════════════════
HELPEOF
}

# ── Main Dispatch ─────────────────────────────────────────────────────────────

cmd="${1:-help}"
shift || true

case "$cmd" in
    call)    cmd_call "$@" ;;
    raw)     cmd_raw "$@" ;;
    list)    cmd_list "$@" ;;
    search)  cmd_search "$@" ;;
    schema)  cmd_schema "$@" ;;
    health)  cmd_health ;;
    help|-h|--help)  cmd_help ;;
    *)
        echo "Unknown command: $cmd" >&2
        echo "Run 'mcp_bridge.sh help' for usage." >&2
        exit 1
        ;;
esac
