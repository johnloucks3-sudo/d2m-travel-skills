#!/bin/bash
# OPTION 1 TEST TASK
# Spawns a simple Gemini task to validate end-to-end execution

set -e

if [ -z "$GEMINI_API_KEY" ]; then
  echo "❌ GEMINI_API_KEY not set"
  echo "Run: export GEMINI_API_KEY='your-api-key-from-google-keep'"
  exit 1
fi

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_FILE="/home/john/Thunderbird/output/test_result_$TIMESTAMP.txt"
LOG_FILE="/home/john/Thunderbird/logs/test_task_$TIMESTAMP.log"

echo "[$(date)] Spawning test Gemini task..."
echo "[$(date)] Output: $OUTPUT_FILE"
echo "[$(date)] Logs: $LOG_FILE"

python3 << 'EOF' &
import google.generativeai as genai
import os
from pathlib import Path

output_file = Path(os.environ.get('OUTPUT_FILE'))
log_file = Path(os.environ.get('LOG_FILE'))

try:
    genai.configure(api_key=os.environ['GEMINI_API_KEY'])
    model = genai.GenerativeModel('gemini-2.0-flash')

    prompt = """
You are an AI analyst for Dreams2Memories Travel.

Task: Provide a 3-sentence summary of the luxury cruise market in 2026.

Focus on:
1. Leading cruise lines
2. Price trends
3. Emerging destinations
    """

    response = model.generate_content(prompt)

    with open(output_file, 'w') as f:
        f.write(response.text)

    print(f"✓ Test task complete. Output: {output_file}")

except Exception as e:
    with open(log_file, 'a') as f:
        f.write(f"Error: {e}\n")
    print(f"❌ Test task failed: {e}")
    exit(1)
EOF

TASK_PID=$!
echo ""
echo "✓ Task spawned (PID $TASK_PID)"
echo ""
echo "Waiting for completion (max 30 seconds)..."
echo ""

# Wait for output file
WAITED=0
while [ ! -f "$OUTPUT_FILE" ] && [ $WAITED -lt 30 ]; do
  sleep 1
  WAITED=$((WAITED + 1))
done

if [ -f "$OUTPUT_FILE" ]; then
  echo "✓ Task completed successfully"
  echo ""
  echo "--- OUTPUT ---"
  cat "$OUTPUT_FILE"
  echo "--- END OUTPUT ---"
  echo ""
  exit 0
else
  echo "⚠ Task did not complete within 30 seconds"
  echo "Check logs: tail -50 $LOG_FILE"
  exit 1
fi
