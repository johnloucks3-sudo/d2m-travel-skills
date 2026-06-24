#!/usr/bin/env bash
# ============================================================
# Thunderbird AI Gateway — LiteLLM Proxy startup
# Usage: ./start.sh [--port 4000] [--detach]
# ============================================================
set -euo pipefail

GATEWAY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="$GATEWAY_DIR/litellm_config.yaml"
LOG_DIR="/home/john/Thunderbird/logs"
LOG_FILE="$LOG_DIR/ai_gateway.log"
PORT="${LITELLM_PORT:-4000}"

# ── Load Wing .env if present ────────────────────────────────
ENV_FILE="/home/john/Thunderbird/.env"
if [[ -f "$ENV_FILE" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
fi

# ── Require critical keys ────────────────────────────────────
missing=()
[[ -z "${LITELLM_MASTER_KEY:-}" ]] && missing+=("LITELLM_MASTER_KEY")
# At least one model backend must be available
if [[ -z "${ANTHROPIC_API_KEY:-}" && -z "${OPENROUTER_API_KEY:-}" && -z "${GROQ_API_KEY:-}" ]]; then
    missing+=("ANTHROPIC_API_KEY or OPENROUTER_API_KEY or GROQ_API_KEY")
fi

if [[ ${#missing[@]} -gt 0 ]]; then
    echo "[gateway] ERROR: Missing required env vars: ${missing[*]}"
    echo "[gateway] Set them in $ENV_FILE or export before running."
    exit 1
fi

mkdir -p "$LOG_DIR"

LITELLM_BIN="/home/john/.local/bin/litellm"
if [[ ! -x "$LITELLM_BIN" ]]; then
    echo "[gateway] litellm not found at $LITELLM_BIN — install: pip install litellm[proxy]"
    exit 1
fi

echo "[gateway] Starting Thunderbird AI Gateway on port $PORT"
echo "[gateway] Config: $CONFIG"
echo "[gateway] Admin UI: http://localhost:$PORT/ui"
echo "[gateway] Logs: $LOG_FILE"

exec "$LITELLM_BIN" \
    --config "$CONFIG" \
    --port "$PORT" \
    --detailed_debug 2>&1 | tee -a "$LOG_FILE"
