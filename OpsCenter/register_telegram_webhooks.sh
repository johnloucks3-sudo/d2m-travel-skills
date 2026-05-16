#!/usr/bin/env bash
# register_telegram_webhooks.sh — Register all 3 Telegram bots in webhook mode
# Run once after service starts, or after any bot token change.
# Cloudflare tunnel must be active: tg.d2mluxury.quest → localhost:8768
# 2026-05-16 | Thunderbird Wing

set -euo pipefail

# ── Load tokens ───────────────────────────────────────────────────────────────
source /home/john/Thunderbird/.env 2>/dev/null || true
source /home/john/Thunderbird/config/telegram_gw.env 2>/dev/null || true

TOKEN_HALUYODA="${TELEGRAM_D2MC2C_TOKEN:?TELEGRAM_D2MC2C_TOKEN not set}"
TOKEN_STAFF="${TELEGRAM_GOOSE_TOKEN:?TELEGRAM_GOOSE_TOKEN not set}"
TOKEN_CHANNELS="${TELEGRAM_DANI_TOKEN:?TELEGRAM_DANI_TOKEN not set}"
SECRET="${TELEGRAM_WEBHOOK_SECRET:-thunderbird-wing-2026}"
BASE_URL="${WEBHOOK_BASE_URL:-https://tg.d2mluxury.quest}"

# ── Allowed update types (reduces load — no inline_mode, chosen_inline etc.) ──
ALLOWED='["message","callback_query","edited_message"]'

echo "=== Thunderbird Webhook Registration 2026-05-16 ==="
echo "Base URL: ${BASE_URL}"
echo ""

# ── HALE-YODA (D2MC2C) ────────────────────────────────────────────────────────
echo "[1/3] Registering HALE-YODA → ${BASE_URL}/hale-yoda"
curl -sS "https://api.telegram.org/bot${TOKEN_HALUYODA}/setWebhook" \
  -d "url=${BASE_URL}/hale-yoda" \
  -d "secret_token=${SECRET}" \
  -d "allowed_updates=${ALLOWED}" \
  -d "drop_pending_updates=true" | python3 -m json.tool
echo ""

# ── HALE_D2M / Staff (GooseD2M) ───────────────────────────────────────────────
echo "[2/3] Registering HALE_D2M Staff → ${BASE_URL}/staff"
curl -sS "https://api.telegram.org/bot${TOKEN_STAFF}/setWebhook" \
  -d "url=${BASE_URL}/staff" \
  -d "secret_token=${SECRET}" \
  -d "allowed_updates=${ALLOWED}" \
  -d "drop_pending_updates=true" | python3 -m json.tool
echo ""

# ── d2m_channels (Dani/MX) ────────────────────────────────────────────────────
echo "[3/3] Registering d2m_channels → ${BASE_URL}/channels"
curl -sS "https://api.telegram.org/bot${TOKEN_CHANNELS}/setWebhook" \
  -d "url=${BASE_URL}/channels" \
  -d "secret_token=${SECRET}" \
  -d "allowed_updates=${ALLOWED}" \
  -d "drop_pending_updates=true" | python3 -m json.tool
echo ""

echo "=== Done. Verify webhook info: ==="
echo ""
for TOKEN_VAR in TOKEN_HALUYODA TOKEN_STAFF TOKEN_CHANNELS; do
  TOKEN="${!TOKEN_VAR}"
  BOT_INFO=$(curl -sS "https://api.telegram.org/bot${TOKEN}/getWebhookInfo" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('result',{}).get('url','ERROR'))")
  echo "  ${TOKEN_VAR}: ${BOT_INFO}"
done
echo ""
echo "If all URLs start with ${BASE_URL}, registration successful."
echo "Service: systemctl --user status thunderbird-telegram-webhook.service"
