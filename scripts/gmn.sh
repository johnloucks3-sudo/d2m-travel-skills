#!/bin/bash
# gmn — quick Gemini CLI wrapper (free 1,500/day Flash lane). Hale 2026-06-14.
# Usage:  gmn "your prompt"            (one-shot, Flash)
#         gmn -pro "your prompt"       (2.5 Pro, 50/day cap)
#         echo "text" | gmn "summarize this"
# Always uses the good .env key; trims CLI startup noise.

cd /home/john/Thunderbird 2>/dev/null
KEY=$(grep -E "^GEMINI_API_KEY=" /home/john/Thunderbird/.env | head -1 | cut -d= -f2)
MODEL="gemini-2.5-flash"
if [[ "${1:-}" == "-pro" ]]; then MODEL="gemini-2.5-pro"; shift; fi

STDIN=""
if [ ! -t 0 ]; then STDIN="$(cat)"; fi
PROMPT="$*"
[ -n "$STDIN" ] && PROMPT="$PROMPT"$'\n\n'"$STDIN"

env -u GOOGLE_GENAI_USE_VERTEXAI -u GOOGLE_APPLICATION_CREDENTIALS \
    GEMINI_API_KEY="$KEY" GEMINI_CLI_TRUST_WORKSPACE=true \
    gemini -m "$MODEL" -p "$PROMPT" 2>&1 \
  | grep -vE "Ripgrep is not available|^\[STARTUP\]|cleanup_ops|not running in a trusted|DeprecationWarning|trace-deprecation|^\(node:|^\(Use "
