#!/bin/bash
# import_all_workflows.sh — Import all D2M n8n workflows via REST API
#
# Prerequisites:
#   - n8n running on localhost:5678
#   - N8N_API_KEY set (or will use default from n8n settings)
#
# Usage:
#   N8N_API_KEY=your-key ./import_all_workflows.sh
#   ./import_all_workflows.sh --dry-run     # Just list what would be imported

set -euo pipefail
cd "$(dirname "$0")" || exit 1

N8N_URL="${N8N_URL:-http://localhost:5678}"
DRY_RUN=false
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true

echo "═══════════════════════════════════════════════"
echo "  D2M n8n Workflow Import"
echo "  Target: $N8N_URL"
echo "═══════════════════════════════════════════════"
echo ""

imported=0
skipped=0
failed=0

for wf in wf*.json; do
    name=$(python3 -c "import json; print(json.load(open('$wf'))['name'])" 2>/dev/null || echo "$wf")

    if $DRY_RUN; then
        echo "  [DRY] $wf → $name"
        continue
    fi

    # Check if workflow already exists by name
    existing=$(curl -s "${N8N_URL}/api/v1/workflows" \
        ${N8N_API_KEY:+-H "X-N8N-API-KEY: $N8N_API_KEY"} \
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
        ${N8N_API_KEY:+-H "X-N8N-API-KEY: $N8N_API_KEY"} \
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

echo ""
echo "Results: $imported imported, $skipped skipped, $failed failed"
echo ""
echo "Activate workflows in n8n UI: ${N8N_URL}"
