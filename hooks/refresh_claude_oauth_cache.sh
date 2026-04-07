#!/usr/bin/env bash
# refresh_claude_oauth_cache.sh
# Called at session start (or on demand) to write the current CLAUDE_CODE_OAUTH_TOKEN
# to the cache file that thunderbird_tasking_watcher.py reads when spawning claude -p.
#
# Add to ~/.claude/settings.json hooks → PostSessionStart or run manually:
#   bash /home/john/Thunderbird/hooks/refresh_claude_oauth_cache.sh
#
# The watcher reads: /home/john/Thunderbird/OpsCenter/.claude_oauth_cache

CACHE="/home/john/Thunderbird/OpsCenter/.claude_oauth_cache"

if [ -n "${CLAUDE_CODE_OAUTH_TOKEN}" ]; then
    echo "CLAUDE_CODE_OAUTH_TOKEN=${CLAUDE_CODE_OAUTH_TOKEN}" > "${CACHE}"
    chmod 600 "${CACHE}"
    echo "[oauth-cache] Token refreshed at $(date)" >> /home/john/Thunderbird/logs/oauth_cache.log
else
    echo "[oauth-cache] WARNING: CLAUDE_CODE_OAUTH_TOKEN not set — cache not updated" >> /home/john/Thunderbird/logs/oauth_cache.log
fi
