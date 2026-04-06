#!/usr/bin/env bash
# =============================================================================
# D2M MCP Security Hardening Verification Script
# Dreams2Memories Travel, LLC
# Created: 2026-03-20
# =============================================================================
# Checks current security posture of MCP and API infrastructure.
# Run: bash ~/Thunderbird/scripts/harden_mcp.sh
# =============================================================================

set -uo pipefail

THUNDERBIRD_DIR="${HOME}/Thunderbird"
MCP_SERVER="${THUNDERBIRD_DIR}/travel_mcp_server.py"
API_SERVER="${THUNDERBIRD_DIR}/api/thunderbird_api.py"
TOKEN_FILE="${THUNDERBIRD_DIR}/.api_token"
CF_CONFIG="${HOME}/.cloudflared/config.yml"

PASS="[PASS]"
FAIL="[FAIL]"
WARN="[WARN]"
INFO="[INFO]"

pass_count=0
fail_count=0
warn_count=0

report() {
    local status="$1"
    local message="$2"
    echo "  ${status} ${message}"
    case "$status" in
        "$PASS") pass_count=$((pass_count + 1)) ;;
        "$FAIL") fail_count=$((fail_count + 1)) ;;
        "$WARN") warn_count=$((warn_count + 1)) ;;
    esac
}

echo ""
echo "=============================================="
echo "  D2M MCP SECURITY HARDENING CHECK"
echo "  $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "=============================================="
echo ""

# --- 1. MCP Server Binding ---
echo "1. MCP SERVER BINDING"
if [ -f "$MCP_SERVER" ]; then
    if grep -q 'host = "127.0.0.1"' "$MCP_SERVER"; then
        report "$PASS" "MCP server bound to 127.0.0.1 (localhost only)"
    elif grep -q 'host = "0.0.0.0"' "$MCP_SERVER"; then
        report "$FAIL" "MCP server bound to 0.0.0.0 — exposed to all interfaces!"
    else
        report "$WARN" "Could not determine MCP server bind address"
    fi
else
    report "$FAIL" "MCP server file not found: ${MCP_SERVER}"
fi
echo ""

# --- 2. REST API Binding ---
echo "2. REST API BINDING"
if [ -f "$API_SERVER" ]; then
    if grep -q 'host = "127.0.0.1"' "$API_SERVER"; then
        report "$PASS" "REST API bound to 127.0.0.1 (localhost only)"
    elif grep -q 'host = "0.0.0.0"' "$API_SERVER"; then
        report "$FAIL" "REST API bound to 0.0.0.0 — exposed to all interfaces!"
    else
        report "$WARN" "Could not determine REST API bind address"
    fi
else
    report "$FAIL" "REST API file not found: ${API_SERVER}"
fi
echo ""

# --- 3. shell_exec Disabled ---
echo "3. SHELL_EXEC STATUS"
if [ -f "$MCP_SERVER" ]; then
    # Check if shell_exec is active (uncommented @mcp.tool decorator with shell_exec name)
    if grep -P '^\s*@mcp\.tool\(' "$MCP_SERVER" | grep -q 'shell_exec' 2>/dev/null; then
        report "$FAIL" "shell_exec tool is ACTIVE — arbitrary command execution enabled!"
    elif grep -q 'SECURITY: Disabled' "$MCP_SERVER" && grep -q '# async def shell_exec' "$MCP_SERVER"; then
        report "$PASS" "shell_exec is disabled (commented out with security note)"
    elif grep -q 'shell_exec' "$MCP_SERVER"; then
        report "$WARN" "shell_exec references found but status unclear — manual review needed"
    else
        report "$PASS" "No shell_exec tool found in MCP server"
    fi
else
    report "$FAIL" "MCP server file not found"
fi
echo ""

# --- 4. API Token File ---
echo "4. API TOKEN FILE"
if [ -f "$TOKEN_FILE" ]; then
    perms=$(stat -c '%a' "$TOKEN_FILE" 2>/dev/null)
    owner=$(stat -c '%U' "$TOKEN_FILE" 2>/dev/null)
    if [ "$perms" = "600" ]; then
        report "$PASS" ".api_token has correct permissions (600)"
    else
        report "$FAIL" ".api_token has permissions ${perms} — should be 600"
    fi
    if [ "$owner" = "$(whoami)" ]; then
        report "$PASS" ".api_token owned by current user (${owner})"
    else
        report "$WARN" ".api_token owned by ${owner}, not $(whoami)"
    fi
    token_len=$(wc -c < "$TOKEN_FILE" | tr -d ' ')
    if [ "$token_len" -ge 32 ]; then
        report "$PASS" "Token length adequate (${token_len} bytes)"
    else
        report "$WARN" "Token length is only ${token_len} bytes — consider a longer token"
    fi
else
    report "$FAIL" ".api_token file does not exist at ${TOKEN_FILE}"
fi
echo ""

# --- 5. Bearer Token Auth on REST API ---
echo "5. BEARER TOKEN AUTH"
if [ -f "$API_SERVER" ]; then
    if grep -q 'BearerTokenMiddleware' "$API_SERVER"; then
        report "$PASS" "REST API has BearerTokenMiddleware"
    else
        report "$FAIL" "REST API missing bearer token authentication"
    fi
fi
if [ -f "$MCP_SERVER" ]; then
    if grep -q 'BearerTokenMiddleware\|bearer.*auth\|Authorization.*Bearer' "$MCP_SERVER"; then
        report "$PASS" "MCP server has bearer token authentication"
    else
        report "$WARN" "MCP server has NO bearer token auth — relies on Cloudflare Access"
    fi
fi
echo ""

# --- 6. Cloudflared Tunnel Status ---
echo "6. CLOUDFLARED TUNNEL"
if command -v cloudflared &>/dev/null; then
    cf_version=$(cloudflared --version 2>&1 | head -1)
    report "$INFO" "cloudflared version: ${cf_version}"
else
    report "$FAIL" "cloudflared not installed"
fi

if pgrep -f 'cloudflared tunnel' &>/dev/null; then
    tunnel_pid=$(pgrep -f 'cloudflared tunnel' | head -1)
    report "$PASS" "cloudflared tunnel running (PID: ${tunnel_pid})"
else
    report "$FAIL" "cloudflared tunnel is NOT running"
fi

if [ -f "$CF_CONFIG" ]; then
    report "$PASS" "Tunnel config exists: ${CF_CONFIG}"
    # Check which hostnames are configured
    hostname_count=$(grep -c 'hostname:' "$CF_CONFIG" 2>/dev/null || echo 0)
    report "$INFO" "${hostname_count} hostnames configured in tunnel"
else
    report "$FAIL" "Tunnel config not found at ${CF_CONFIG}"
fi
echo ""

# --- 7. Cloudflare Access (informational) ---
echo "7. CLOUDFLARE ACCESS"
report "$WARN" "Cloudflare Access policies cannot be verified locally"
report "$INFO" "Check via: https://one.dash.cloudflare.com/ → Access → Applications"
report "$INFO" "See: ~/Thunderbird/intel/cloudflare_access_setup.md for setup steps"
echo ""

# --- 8. .gitignore Coverage ---
echo "8. GITIGNORE COVERAGE"
gitignore="${THUNDERBIRD_DIR}/.gitignore"
if [ -f "$gitignore" ]; then
    for pattern in ".api_token" ".cf_service_token" "*.env" "credentials.json"; do
        if grep -qF "$pattern" "$gitignore" 2>/dev/null; then
            report "$PASS" "${pattern} is in .gitignore"
        else
            report "$WARN" "${pattern} is NOT in .gitignore"
        fi
    done
else
    report "$FAIL" ".gitignore not found"
fi
echo ""

# --- 9. Network Exposure Check ---
echo "9. NETWORK EXPOSURE (listening ports)"
for port in 8765 8766 8780 5678; do
    listen_info=$(ss -tlnp 2>/dev/null | grep ":${port} " | head -1)
    if [ -n "$listen_info" ]; then
        if echo "$listen_info" | grep -q '127.0.0.1'; then
            report "$PASS" "Port ${port} listening on localhost only"
        elif echo "$listen_info" | grep -q '0.0.0.0\|\*:'; then
            report "$FAIL" "Port ${port} listening on ALL interfaces"
        else
            report "$INFO" "Port ${port}: ${listen_info}"
        fi
    else
        report "$INFO" "Port ${port} not currently listening"
    fi
done
echo ""

# --- Summary ---
echo "=============================================="
echo "  SUMMARY"
echo "=============================================="
echo "  Passed:   ${pass_count}"
echo "  Failed:   ${fail_count}"
echo "  Warnings: ${warn_count}"
echo "=============================================="

if [ "$fail_count" -gt 0 ]; then
    echo "  STATUS: HARDENING INCOMPLETE — ${fail_count} issue(s) require attention"
    exit 1
elif [ "$warn_count" -gt 0 ]; then
    echo "  STATUS: MOSTLY HARDENED — ${warn_count} advisory item(s)"
    exit 0
else
    echo "  STATUS: FULLY HARDENED"
    exit 0
fi
