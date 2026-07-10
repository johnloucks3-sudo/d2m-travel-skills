#!/bin/bash
# ask_wrapper.sh — Unified /ask (Sonnet) and /ask-opus dispatcher
#
# Invocation:
#   ask "task"                          # /ask  → Sonnet
#   ask-opus "task"                     # /ask-opus → Opus
#   ask --opus "task"                   # (backward compat)
#   ask --etc "4h" --rdt "18:00" "task" # with estimates
#   ask --track                         # Usage stats
#
# ETC (Estimated Time to Complete) and RDT (Required Delivery Time)
# are displayed prominently and an elapsed timer runs until completion.
#
# NOTE: /ask and /ask-opus are the canonical names.
# The leading / is a documentation convention (bash can't have slashes in commands).

set -e

PYTHON_SCRIPT="/home/john/Thunderbird/OpsCenter/opencode_sonnet_inline.py"
TRACK_FILE="/home/john/Thunderbird/.ask_usage_log"
TASK_DESC=""
MODEL="sonnet"
ETC=""
RDT=""
DISPATCH_TIME=""

# Detect model from command name
CMD_NAME=$(basename "$0")
if [[ "$CMD_NAME" == "ask-opus" ]]; then
    MODEL="opus"
fi

# Parse args
ARGS=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --opus)
            MODEL="opus"
            shift
            ;;
        --etc)
            ETC="$2"
            shift 2
            ;;
        --rdt)
            RDT="$2"
            shift 2
            ;;
        --track)
            if [[ -f "$TRACK_FILE" ]]; then
                echo "USAGE STATS (Leak Verification):"
                echo ""
                tail -20 "$TRACK_FILE" | awk -F'|' '{printf "  %s %s \342\206\222 %s (%.1fs)\n", $2, $3, $4, $5}'
                echo ""
                SONNET_COUNT=$(grep -c "sonnet" "$TRACK_FILE" 2>/dev/null || echo 0)
                OPUS_COUNT=$(grep -c "opus" "$TRACK_FILE" 2>/dev/null || echo 0)
                TOTAL=$((SONNET_COUNT + OPUS_COUNT))
                echo "  Total dispatches: $TOTAL (Sonnet: $SONNET_COUNT, Opus: $OPUS_COUNT)"
                echo ""
                echo "If you see ONLY 'sonnet' and 'opus' above, leak is PLUGGED."
                echo "If you see 'claude_inbox', you're still screen-switching."
            else
                echo "No usage yet. Use: ask 'your task'  or  ask-opus 'task'"
            fi
            exit 0
            ;;
        -h|--help)
            echo "Usage:"
            echo "  ask 'task'                           # /ask  → Sonnet"
            echo "  ask-opus 'task'                      # /ask-opus → Opus"
            echo "  ask --etc '4h' --rdt '18:00' 'task'  # with ETC/RDT timer"
            echo "  ask --opus 'task'                    # backward compat (deprecated)"
            echo "  ask --track                          # Usage stats"
            exit 0
            ;;
        *)
            ARGS+=("$1")
            shift
            ;;
    esac
done

TASK_DESC="${ARGS[*]}"

# Validate input
if [[ -z "$TASK_DESC" ]]; then
    echo "Usage:"
    echo "  ask 'task description'       # /ask  → Sonnet"
    echo "  ask-opus 'task description'  # /ask-opus → Opus"
    echo "  ask --etc '4h' --rdt '18:00' 'task'  # with timer"
    echo "  ask --track                  # Usage stats"
    exit 1
fi

# Record dispatch time
DISPATCH_TIME=$(date "+%H:%M:%S")
DISPATCH_EPOCH=$(date +%s)

# Print dispatch banner with ETC/RDT
MODEL_LABEL="Sonnet"
[[ "$MODEL" == "opus" ]] && MODEL_LABEL="Opus"
echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  /ask — $MODEL_LABEL"
echo "║  Time:  $DISPATCH_TIME MT"
if [[ -n "$ETC" ]]; then
    echo "║  ETC:   $ETC"
fi
if [[ -n "$RDT" ]]; then
    echo "║  RDT:   $RDT"
fi
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# Log the dispatch
mkdir -p "$(dirname "$TRACK_FILE")"
TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")
echo "$TIMESTAMP|$TIMESTAMP|$MODEL|inline|0" >> "$TRACK_FILE"

# Dispatch and record elapsed time
if [[ "$MODEL" == "opus" ]]; then
    START_EPOCH=$(date +%s)
    python3 /home/john/Thunderbird/OpsCenter/opencode_sonnet_inline.py "$TASK_DESC" --model opus  # alias
    END_EPOCH=$(date +%s)
else
    START_EPOCH=$(date +%s)
    python3 "$PYTHON_SCRIPT" "$TASK_DESC"
    END_EPOCH=$(date +%s)
fi

ELAPSED=$((END_EPOCH - START_EPOCH))
ELAPSED_MIN=$((ELAPSED / 60))
ELAPSED_SEC=$((ELAPSED % 60))

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  COMPLETE — ${ELAPSED_MIN}m ${ELAPSED_SEC}s elapsed"
if [[ -n "$ETC" ]]; then
    echo "║  ETC: $ETC | Elapsed: ${ELAPSED_MIN}m ${ELAPSED_SEC}s"
fi
echo "╚══════════════════════════════════════════════════════╝"
echo ""
