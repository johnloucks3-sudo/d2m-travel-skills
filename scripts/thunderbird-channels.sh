#!/usr/bin/env bash
# thunderbird-channels.sh — Launch Claude Code with Telegram channel
# IOC-1: Claude Code Channels → Telegram integration
#
# Prerequisites:
#   1. Claude Code v2.1.80+
#   2. Plugin installed: /plugin install telegram@claude-plugins-official
#   3. Token configured: /telegram:configure $TELEGRAM_C2_BOT_TOKEN
#   4. Paired + allowlisted: /telegram:access policy allowlist
#
# Usage:
#   ./scripts/thunderbird-channels.sh             # Telegram channel
#   ./scripts/thunderbird-channels.sh --discord    # Discord channel (if configured)
#   ./scripts/thunderbird-channels.sh --both       # Both channels
#
# NOTE: This is SEPARATE from the D2MC2C Telegram bot (thunderbird_telegram_c2.py).
# The C2 bot handles structured commands (/hale, /dani, /sss, drafts).
# The Channel gives you freeform Claude Code access from Telegram.
# They use DIFFERENT bot tokens — create a second BotFather bot for the channel.

set -euo pipefail
cd "$(dirname "$0")/.." || exit 1

CHANNEL_TOKEN_FILE="$HOME/.claude/channels/telegram/.env"

# Check prerequisites
if ! command -v claude &>/dev/null; then
    echo "ERROR: claude CLI not found. Install Claude Code first."
    exit 1
fi

# Parse args
CHANNELS="plugin:telegram@claude-plugins-official"
case "${1:-}" in
    --discord)
        CHANNELS="plugin:discord@claude-plugins-official"
        ;;
    --both)
        CHANNELS="plugin:telegram@claude-plugins-official,plugin:discord@claude-plugins-official"
        ;;
    --help|-h)
        head -20 "$0" | grep '^#' | sed 's/^# \?//'
        exit 0
        ;;
esac

# Check if token is configured
if [[ ! -f "$CHANNEL_TOKEN_FILE" ]]; then
    echo "Telegram channel token not configured yet."
    echo ""
    echo "First-time setup:"
    echo "  1. Create a NEW bot via @BotFather (separate from D2MC2C)"
    echo "  2. Run: claude"
    echo "  3. Inside session: /plugin install telegram@claude-plugins-official"
    echo "  4. Inside session: /telegram:configure <YOUR_NEW_BOT_TOKEN>"
    echo "  5. Send a message to the new bot in Telegram"
    echo "  6. Inside session: /telegram:access pair <6-char-code>"
    echo "  7. Inside session: /telegram:access policy allowlist"
    echo "  8. Exit and re-run this script"
    exit 1
fi

echo "═══════════════════════════════════════════════"
echo "  THUNDERBIRD OS — Channel Mode"
echo "  Channels: $CHANNELS"
echo "  Working dir: $(pwd)"
echo "═══════════════════════════════════════════════"
echo ""
echo "Telegram messages will appear as channel events."
echo "Use Ctrl+C to disconnect."
echo ""

exec claude --channels "$CHANNELS"
