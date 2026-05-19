#!/bin/bash
# refresh_claude_oauth_cache.sh — Mark OAuth token cache refresh
# Called by Claude Code UserPromptSubmit hook
# Ensures OAuth token is up-to-date for session

set -euo pipefail

CREDS_FILE="${HOME}/.claude/.credentials.json"
CACHE_MARKER="${HOME}/.claude/.oauth_cache_timestamp"

# If credentials file exists, mark that a cache refresh was requested
if [[ -f "$CREDS_FILE" ]]; then
    mkdir -p "$(dirname "$CACHE_MARKER")"
    date +%s > "$CACHE_MARKER"
fi

exit 0
