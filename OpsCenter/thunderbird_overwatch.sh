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

# PYTHONPATH — core/ reorg requires all subdirs on path
export PYTHONPATH="/home/john/Thunderbird:/home/john/Thunderbird/api:/home/john/Thunderbird/OpsCenter:/home/john/Thunderbird/agents:/home/john/Thunderbird/business:/home/john/Thunderbird/comms:/home/john/Thunderbird/intel:/home/john/Thunderbird/itinerary:/home/john/Thunderbird/media:/home/john/Thunderbird/ops:/home/john/Thunderbird/core/ai_infra:/home/john/Thunderbird/core/booking:/home/john/Thunderbird/core/client:/home/john/Thunderbird/core/communication:/home/john/Thunderbird/core/crewai:/home/john/Thunderbird/core/email:/home/john/Thunderbird/core/intel:/home/john/Thunderbird/core/learning:/home/john/Thunderbird/core/mcp:/home/john/Thunderbird/core/ops:/home/john/Thunderbird/core/scheduling:/home/john/Thunderbird/core/travel:/home/john/Thunderbird/core/watchtower"
# ---------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="/home/john/Thunderbird/.venv/bin/python3"

# Fallback to system python if venv doesn't exist
[ ! -f "$PYTHON" ] && PYTHON="python3"

echo "[$(date)] Hale-Loop starting Python task processor..." >> "$SCRIPT_DIR/overwatch.log"

exec "$PYTHON" "$SCRIPT_DIR/task_processor.py" --daemon
