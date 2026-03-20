#!/bin/bash
# import_all_workflows.sh — Import all D2M n8n workflows
#
# Tries n8n CLI first (no API key needed), falls back to REST API.
#
# Usage:
#   ./import_all_workflows.sh                  # Auto-detect method
#   ./import_all_workflows.sh --dry-run        # List without importing
#   N8N_API_KEY=xxx ./import_all_workflows.sh  # Force REST API

set -euo pipefail
cd "$(dirname "$0")" || exit 1

N8N_URL="${N8N_URL:-http://localhost:5678}"
DRY_RUN=false
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true

echo "═══════════════════════════════════════════════"
echo "  D2M n8n Workflow Import"
echo "═══════════════════════════════════════════════"
echo ""

imported=0
skipped=0
failed=0

# ── Method 1: n8n CLI (preferred — no API key needed) ──────────────────
if command -v n8n &>/dev/null && [[ -z "${N8N_API_KEY:-}" ]]; then
    echo "  Using: n8n CLI import"
    echo ""

    for wf in wf*.json; do
        name=$(python3 -c "import json; print(json.load(open('$wf'))['name'])" 2>/dev/null || echo "$wf")

        if $DRY_RUN; then
            echo "  [DRY] $wf → $name"
            continue
        fi

        if n8n import:workflow --input="$wf" 2>/dev/null; then
            echo "  [OK]   $wf → $name"
            ((imported++)) || true
        else
            echo "  [FAIL] $wf → $name"
            ((failed++)) || true
        fi
    done

# ── Method 2: REST API (needs N8N_API_KEY) ─────────────────────────────
else
    echo "  Using: REST API → $N8N_URL"
    if [[ -z "${N8N_API_KEY:-}" ]]; then
        echo ""
        echo "  ERROR: N8N_API_KEY not set and n8n CLI not found."
        echo "  Generate an API key: n8n UI → Settings → API → Create Key"
        echo "  Then: N8N_API_KEY=your-key bash $0"
        exit 1
    fi
    echo ""

    for wf in wf*.json; do
        name=$(python3 -c "import json; print(json.load(open('$wf'))['name'])" 2>/dev/null || echo "$wf")

        if $DRY_RUN; then
            echo "  [DRY] $wf → $name"
            continue
        fi

        # Check if workflow already exists by name
        existing=$(curl -s "${N8N_URL}/api/v1/workflows" \
            -H "X-N8N-API-KEY: $N8N_API_KEY" \
            2>/dev/null | python3 -c "
import json, sys
data = json.load(sys.stdin)
workflows = data.get('data', data.get('workflows', []))
for w in workflows:
    if w.get('name') == '$name':
        print(w['id'])
        break
" 2>/dev/null || echo "")

        if [[ -n "$existing" ]]; then
            echo "  [SKIP] $wf → $name (already exists as ID $existing)"
            ((skipped++)) || true
            continue
        fi

        # Import workflow
        status=$(curl -s -o /dev/null -w "%{http_code}" \
            -X POST "${N8N_URL}/api/v1/workflows" \
            -H "X-N8N-API-KEY: $N8N_API_KEY" \
            -H "Content-Type: application/json" \
            -d @"$wf" 2>/dev/null)

        if [[ "$status" == "200" || "$status" == "201" ]]; then
            echo "  [OK]   $wf → $name"
            ((imported++)) || true
        else
            echo "  [FAIL] $wf → $name (HTTP $status)"
            ((failed++)) || true
        fi
    done
fi

echo ""
echo "Results: $imported imported, $skipped skipped, $failed failed"
echo ""
if [[ $imported -gt 0 ]]; then
    echo "Activate workflows in n8n UI: ${N8N_URL}"
fi
