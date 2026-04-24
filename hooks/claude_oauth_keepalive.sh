#!/usr/bin/env bash
# claude_oauth_keepalive.sh — keeps Max OAuth token alive
# Cron: add via: crontab -e
#   */90 * * * * /home/john/Thunderbird/hooks/claude_oauth_keepalive.sh
LOG="/home/john/Thunderbird/logs/oauth_keepalive.log"
mkdir -p /home/john/Thunderbird/logs
RESULT=$(env -u ANTHROPIC_API_KEY /home/john/.local/bin/claude --dangerously-skip-permissions --model claude-haiku-4-5-20251001 -p "Reply with: ok" 2>&1 | head -2)
if echo "$RESULT" | grep -qi "ok"; then
  echo "[$(date '+%Y-%m-%d %H:%M')] keepalive OK" >> "$LOG"
else
  echo "[$(date '+%Y-%m-%d %H:%M')] keepalive WARN: $RESULT" >> "$LOG"
fi
