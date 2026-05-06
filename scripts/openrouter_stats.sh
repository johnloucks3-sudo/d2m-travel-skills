#!/usr/bin/env bash
# Fetch OpenRouter stats and cache for tmux status bar
CACHE_FILE="/tmp/openrouter_stats.txt"

# Use cached result if < 60s old
if [ -f "$CACHE_FILE" ]; then
    AGE=$(( $(date +%s) - $(stat -c %Y "$CACHE_FILE" 2>/dev/null || echo 0) ))
    if [ "$AGE" -lt 60 ]; then
        cat "$CACHE_FILE"
        exit 0
    fi
fi

python3 /home/john/Thunderbird/scripts/openrouter_stats.py 2>/dev/null > "$CACHE_FILE" || echo "OR: --" > "$CACHE_FILE"
cat "$CACHE_FILE"
