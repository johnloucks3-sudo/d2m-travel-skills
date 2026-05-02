#!/bin/bash
# FOOLPROOF RESEARCH TASK ORCHESTRATOR
# ====================================
# For OpenCode: Call this script to run the full research workflow.
# Usage: bash run_research_task.sh

set -e  # Exit on any error

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
RESEARCH_SCRIPT="${SCRIPT_DIR}/research_integrators_headless.py"
EMAIL_SCRIPT="${SCRIPT_DIR}/send_research_email.py"
OUTPUT_DIR="${SCRIPT_DIR}/opencode_knowledge"

echo "=========================================="
echo "THUNDERBIRD RESEARCH TASK ORCHESTRATOR"
echo "=========================================="
echo ""

# Step 1: Spawn headless Claude research
echo "[1/3] Spawning headless Claude research..."
cd "$SCRIPT_DIR"
python3 "$RESEARCH_SCRIPT"
RESEARCH_EXIT=$?

if [ $RESEARCH_EXIT -ne 0 ]; then
    echo "❌ Research spawn failed (exit code: $RESEARCH_EXIT)"
    exit 1
fi

echo ""
echo "[2/3] Waiting for Claude to complete research (monitor logs)..."
echo "      Logs at: /home/john/Thunderbird/logs/headless_claude_integrators_*.log"
echo ""

# Step 2: Find the latest output file
sleep 2  # Give Claude a moment to start writing
LATEST_RESEARCH=$(ls -t "${OUTPUT_DIR}"/research_integrators_RESULT_*.md 2>/dev/null | head -1)

if [ -z "$LATEST_RESEARCH" ]; then
    echo "⚠️  Research output not found yet. Claude may still be running."
    echo "    Check logs and rerun once output file appears."
    exit 0
fi

echo "[3/3] Found research output: $(basename "$LATEST_RESEARCH")"
echo "      Attempting to send email..."
python3 "$EMAIL_SCRIPT" "$LATEST_RESEARCH"
EMAIL_EXIT=$?

if [ $EMAIL_EXIT -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "✅ RESEARCH TASK COMPLETE"
    echo "=========================================="
    echo "Output: $LATEST_RESEARCH"
    echo "Email: Sent to johnloucks3@gmail.com"
    exit 0
else
    echo ""
    echo "⚠️  Research spawned successfully, email send had issues."
    echo "    Research output: $LATEST_RESEARCH"
    exit 1
fi
