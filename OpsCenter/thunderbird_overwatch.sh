#!/bin/bash
# thunderbird_overwatch.sh - The Hale-Loop Daemon
# Thin bash wrapper that launches the Python task processor.
# All real work happens in task_processor.py.
#
# Division of Labor:
#   Groq (free)      → Classification, routing, summaries
#   Gemini Flash ($)  → Research, briefs, bulk text
#   Claude MAX ($0)   → Client-facing only (queued to 03_CLAUDE_MAX_QUEUE.json)
#   Local Python      → Queue mechanics, deadline checks (no LLM)

# --- Environment Injection (required for systemd isolation) ---
export HOME="/home/john"
export PATH="/home/john/.local/bin:/home/john/.local/share/claude/versions/current/bin:$HOME/.nvm/versions/node/$(ls $HOME/.nvm/versions/node/ 2>/dev/null | tail -1)/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
export XDG_CONFIG_HOME="$HOME/.config"

# Source .env for API keys (Groq, Gemini, Telegram, etc.)
set -a
source /home/john/Thunderbird/.env
source /home/john/Thunderbird/.env.telegram
set +a

# Force OAuth for Claude CLI — unset any API key that would hijack it
unset ANTHROPIC_API_KEY
# ---------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="/home/john/Thunderbird/.venv/bin/python3"

# Fallback to system python if venv doesn't exist
[ ! -f "$PYTHON" ] && PYTHON="python3"

echo "[$(date)] Hale-Loop starting Python task processor..." >> "$SCRIPT_DIR/overwatch.log"

exec "$PYTHON" "$SCRIPT_DIR/task_processor.py" --daemon
