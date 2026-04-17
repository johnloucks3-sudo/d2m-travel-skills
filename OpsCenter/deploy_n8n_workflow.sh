#!/bin/bash
# Deploy n8n workflow via API
# n8n v2.12.3 running on YOGA at http://192.168.1.198:5678

set -e

WORKFLOW_JSON="$1"
if [ -z "$WORKFLOW_JSON" ]; then
    WORKFLOW_JSON="n8n_touchpoint_draft_engine.json"
fi

if [ ! -f "$WORKFLOW_JSON" ]; then
    echo "Error: Workflow file $WORKFLOW_JSON not found"
    exit 1
fi

# Extract n8n credentials from env
N8N_BASE_URL="http://192.168.1.198:5678"
N8N_API_KEY="$(grep N8N_API_KEY /home/john/Thunderbird/.env | cut -d '=' -f2 | tr -d '\"')"

if [ -z "$N8N_API_KEY" ]; then
    echo "Error: N8N_API_KEY not found in .env"
    exit 1
fi

echo "Deploying workflow to n8n at $N8N_BASE_URL"
echo "Workflow file: $WORKFLOW_JSON"

# Import workflow via API
RESPONSE=$(curl -s -X POST \
    "$N8N_BASE_URL/rest/workflows" \
    -H "X-N8N-API-KEY: $N8N_API_KEY" \
    -H "Content-Type: application/json" \
    --data-binary "@$WORKFLOW_JSON")

if echo "$RESPONSE" | grep -q "\"id\":"; then
    WORKFLOW_ID=$(echo "$RESPONSE" | grep -o '"id":"[^"]*"' | cut -d '"' -f4)
    echo "✅ Workflow deployed successfully! ID: $WORKFLOW_ID"
    echo "Access at: $N8N_BASE_URL/workflow/$WORKFLOW_ID"
else
    echo "❌ Failed to deploy workflow"
    echo "Response: $RESPONSE"
    exit 1
fi