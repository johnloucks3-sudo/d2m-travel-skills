#!/bin/bash
# n8n_webhook_reinit.sh
# Re-registers the Blackboard Read webhook in n8n after each service restart.
# n8n v1.x sometimes loses in-memory webhook registrations after restart;
# a deactivate/activate cycle forces re-registration.
#
# Usage: called from n8n.service ExecStartPost, or run manually.
# Workflow: z4pYJ2Dr3XqLnf5d (Blackboard Read Webhook)

set -euo pipefail

N8N_API="http://127.0.0.1:5678/api/v1"
WORKFLOW_ID="z4pYJ2Dr3XqLnf5d"
API_KEY="***REMOVED-SECRET***"
WEBHOOK_URL="https://n8n.d2mluxury.quest/webhook/${WORKFLOW_ID}/webhook/blackboard"
MAX_WAIT=60
SLEEP_INTERVAL=5

log() { echo "[n8n_webhook_reinit] $(date '+%Y-%m-%d %H:%M:%S') $*"; }

# Wait for n8n to be ready
log "Waiting for n8n API to be available..."
elapsed=0
until curl -sf -o /dev/null "http://127.0.0.1:5678/healthz" 2>/dev/null; do
    sleep $SLEEP_INTERVAL
    elapsed=$((elapsed + SLEEP_INTERVAL))
    if [ $elapsed -ge $MAX_WAIT ]; then
        log "ERROR: n8n did not become available within ${MAX_WAIT}s"
        exit 1
    fi
done
log "n8n is up."

# Deactivate
log "Deactivating workflow ${WORKFLOW_ID}..."
curl -sf -X POST "${N8N_API}/workflows/${WORKFLOW_ID}/deactivate" \
    -H "X-N8N-API-KEY: ${API_KEY}" \
    -H "Content-Type: application/json" > /dev/null
sleep 2

# Activate
log "Activating workflow ${WORKFLOW_ID}..."
curl -sf -X POST "${N8N_API}/workflows/${WORKFLOW_ID}/activate" \
    -H "X-N8N-API-KEY: ${API_KEY}" \
    -H "Content-Type: application/json" > /dev/null
sleep 2

# Verify webhook responds
log "Verifying webhook at ${WEBHOOK_URL}..."
HTTP_CODE=$(curl -sf -o /dev/null -w "%{http_code}" "${WEBHOOK_URL}" 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
    log "Webhook LIVE — HTTP ${HTTP_CODE}"
else
    log "WARNING: Webhook returned HTTP ${HTTP_CODE} — may need manual check"
fi

log "Reinit complete."
