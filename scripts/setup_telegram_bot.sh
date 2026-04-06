#!/usr/bin/env bash
# =============================================================================
# Thunderbird Telegram Bot — Setup Script
# Dreams2Memories Travel, LLC
# =============================================================================
#
# This script:
#   1. Installs the python-telegram-bot dependency
#   2. Walks you through getting a bot token from BotFather
#   3. Helps you find your Telegram user ID
#   4. Creates a .env file for the bot
#   5. Provides a systemd user service file for persistent operation
#
# Usage:
#   chmod +x ~/Thunderbird/scripts/setup_telegram_bot.sh
#   ~/Thunderbird/scripts/setup_telegram_bot.sh
# =============================================================================

set -euo pipefail

THUNDERBIRD_DIR="$HOME/Thunderbird"
ENV_FILE="$THUNDERBIRD_DIR/.env.telegram"
SERVICE_DIR="$HOME/.config/systemd/user"
SERVICE_FILE="$SERVICE_DIR/thunderbird-telegram.service"

echo "============================================="
echo "  Thunderbird Telegram Bot — Setup"
echo "  Dreams2Memories Travel, LLC"
echo "============================================="
echo ""

# --- Step 1: Install dependency ---
echo "[1/5] Installing python-telegram-bot..."
pip install --quiet "python-telegram-bot>=21.0"
echo "  Done."
echo ""

# --- Step 2: BotFather instructions ---
echo "[2/5] Create your bot via BotFather"
echo "  ─────────────────────────────────"
echo "  1. Open Telegram on your Galaxy Z Fold 6"
echo "  2. Search for @BotFather and start a chat"
echo "  3. Send:  /newbot"
echo "  4. Name:  Thunderbird Command"
echo "  5. Username:  d2m_thunderbird_bot  (or similar — must end in 'bot')"
echo "  6. BotFather will give you a token like:  123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
echo "  7. Copy that token."
echo ""
echo "  Optional — set bot description and photo:"
echo "    /setdescription — 'Dreams2Memories AI Staff — Commander Access Only'"
echo "    /setuserpic     — upload the D2M logo"
echo ""

read -rp "Paste your bot token here (or press Enter to skip): " BOT_TOKEN
echo ""

# --- Step 3: Get user ID ---
echo "[3/5] Find your Telegram user ID"
echo "  ─────────────────────────────────"
echo "  1. Search for @userinfobot on Telegram"
echo "  2. Send it any message"
echo "  3. It will reply with your numeric user ID"
echo "  4. This restricts the bot to ONLY you."
echo ""

read -rp "Paste your Telegram user ID here (or press Enter to skip): " COMMANDER_ID
echo ""

# --- Step 4: Create .env file ---
echo "[4/5] Creating environment file..."

cat > "$ENV_FILE" <<ENVEOF
# Thunderbird Telegram Bot — Environment Variables
# Generated: $(date -Iseconds)

TELEGRAM_BOT_TOKEN=${BOT_TOKEN:-PASTE_YOUR_TOKEN_HERE}
TELEGRAM_COMMANDER_ID=${COMMANDER_ID:-PASTE_YOUR_USER_ID_HERE}
ENVEOF

chmod 600 "$ENV_FILE"
echo "  Saved to: $ENV_FILE"
echo "  (permissions: 600 — owner-only read/write)"
echo ""

# --- Step 5: systemd user service ---
echo "[5/5] Creating systemd user service..."

mkdir -p "$SERVICE_DIR"

cat > "$SERVICE_FILE" <<SVCEOF
[Unit]
Description=Thunderbird Telegram Bot — D2M Wing Commander Interface
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$THUNDERBIRD_DIR
EnvironmentFile=$ENV_FILE
ExecStart=$(which python3) $THUNDERBIRD_DIR/OpsCenter/thunderbird_telegram.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

# Graceful shutdown
TimeoutStopSec=10

[Install]
WantedBy=default.target
SVCEOF

echo "  Service file: $SERVICE_FILE"
echo ""

# --- Summary ---
echo "============================================="
echo "  Setup Complete!"
echo "============================================="
echo ""
echo "  Quick start (manual):"
echo "    source $ENV_FILE"
echo "    export TELEGRAM_BOT_TOKEN TELEGRAM_COMMANDER_ID"
echo "    cd $THUNDERBIRD_DIR && python thunderbird_telegram.py"
echo ""
echo "  Run as a persistent service:"
echo "    systemctl --user daemon-reload"
echo "    systemctl --user enable thunderbird-telegram"
echo "    systemctl --user start thunderbird-telegram"
echo ""
echo "  Check status:"
echo "    systemctl --user status thunderbird-telegram"
echo ""
echo "  View logs:"
echo "    journalctl --user -u thunderbird-telegram -f"
echo ""
echo "  Stop:"
echo "    systemctl --user stop thunderbird-telegram"
echo ""

if [[ "${BOT_TOKEN:-}" == "" ]] || [[ "${COMMANDER_ID:-}" == "" ]]; then
    echo "  NOTE: Edit $ENV_FILE to add your token and user ID"
    echo "  before starting the bot."
    echo ""
fi
