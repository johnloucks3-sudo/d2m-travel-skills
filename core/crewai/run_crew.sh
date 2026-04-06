#!/bin/bash
# CrewAI Bridge CLI Wrapper
# Usage: bash run_crew.sh "task description" [llm_tier] [output_file]

set -e

BRIDGE_DIR="/home/john/Thunderbird/crewai_bridge"
VENV="/home/john/Thunderbird/.venv"
PYTHON="$VENV/bin/python3"

# Load keys
source /home/john/Thunderbird/.env

if [ -z "$1" ]; then
    echo "Usage: bash run_crew.sh \"task description\" [llm_tier] [output_file]"
    echo "  llm_tier: orchestrator (default) | reasoning | router | free"
    exit 1
fi

TASK="$1"
LLM_TIER="${2:-orchestrator}"
OUTPUT_FILE="$3"

echo "========================================"
echo "CREWAI BRIDGE — Launching"
echo "Task: $TASK"
echo "LLM: $LLM_TIER"
echo "Output: $OUTPUT_FILE"
echo "========================================"

cd "$BRIDGE_DIR"
$PYTHON crew_runner.py "$TASK" "$LLM_TIER" "$OUTPUT_FILE"