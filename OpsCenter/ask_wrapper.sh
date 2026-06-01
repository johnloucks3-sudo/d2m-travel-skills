#!/bin/bash
# ask_wrapper.sh — Unified Sonnet/Opus dispatcher with leak tracking
#
# Usage:
#   ask "task description"       # → Sonnet (auto-detect, default)
#   ask --opus "task"            # → Opus (explicit premium)
#   ask --track                  # Show usage stats + confirm leak is plugged

set -e

PYTHON_SCRIPT="/home/john/Thunderbird/OpsCenter/opencode_sonnet_inline.py"
TRACK_FILE="/home/john/Thunderbird/.ask_usage_log"
TASK_DESC=""
MODEL="sonnet"

# Parse args
while [[ $# -gt 0 ]]; do
    case "$1" in
        --opus)
            MODEL="opus"
            shift
            ;;
        --track)
            if [[ -f "$TRACK_FILE" ]]; then
                echo "📊 USAGE STATS (Leak Verification):"
                echo ""
                tail -20 "$TRACK_FILE" | awk -F'|' '{printf "  %s %s → %s (%.1fs)\n", $2, $3, $4, $5}'
                echo ""
                SONNET_COUNT=$(grep -c "sonnet" "$TRACK_FILE" 2>/dev/null || echo 0)
                OPUS_COUNT=$(grep -c "opus" "$TRACK_FILE" 2>/dev/null || echo 0)
                TOTAL=$((SONNET_COUNT + OPUS_COUNT))
                echo "  Total dispatches: $TOTAL (Sonnet: $SONNET_COUNT, Opus: $OPUS_COUNT)"
                echo ""
                echo "✅ If you see ONLY 'sonnet' and 'opus' above, leak is PLUGGED."
                echo "❌ If you see 'claude_inbox', you're still screen-switching."
            else
                echo "No usage yet. Start with: ask 'your task'"
            fi
            exit 0
            ;;
        *)
            TASK_DESC="$@"
            break
            ;;
    esac
done

# Validate input
if [[ -z "$TASK_DESC" ]]; then
    echo "Usage: ask 'task description'"
    echo "       ask --opus 'premium task'"
    echo "       ask --track"
    exit 1
fi

# Log the dispatch
mkdir -p "$(dirname "$TRACK_FILE")"
TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")
echo "$TIMESTAMP|$TIMESTAMP|$MODEL|inline|0" >> "$TRACK_FILE"

# Dispatch based on model
if [[ "$MODEL" == "opus" ]]; then
    echo "🔷 Dispatching to Opus (premium reasoning)..."
    python3 /home/john/Thunderbird/OpsCenter/opencode_sonnet_inline.py "$TASK_DESC" --model claude-opus-4-7
else
    # Sonnet (default)
    python3 "$PYTHON_SCRIPT" "$TASK_DESC"
fi
