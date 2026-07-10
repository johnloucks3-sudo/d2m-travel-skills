#!/bin/bash
# Telegram gateway 24h diagnostic capture — auto-heal disabled 2026-07-06
# Tails the unit's journal to a timestamped log for crash/exit analysis.
set -euo pipefail
LOGFILE="/home/john/Thunderbird/logs/telegram_diagnostic_$(date +%Y%m%d_%H%M%S).log"
echo "=== Telegram diagnostic capture started $(date -Iseconds) ===" > "$LOGFILE"
echo "=== Restart=no active (auto-heal disabled) — capturing raw crash/exit behavior ===" >> "$LOGFILE"
timeout 24h journalctl --user -u thunderbird-telegram-gw.service -f --no-pager >> "$LOGFILE" 2>&1
echo "=== Capture window ended $(date -Iseconds) ===" >> "$LOGFILE"
