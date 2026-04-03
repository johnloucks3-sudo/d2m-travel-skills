#!/bin/bash
# hale_post_scan.sh — Post-scan Hale synthesis trigger
# Called as ExecStartPost in scan services.
# Usage: hale_post_scan.sh <scan_type> <output_file>
#
# Reads raw scan output from file, synthesizes via Hale, sends to Telegram.
# If output file not provided, reads from HALE_SCAN_OUTPUT env var.

set -e

SCAN_TYPE="${1:-general}"
OUTPUT_FILE="${2:-${HALE_SCAN_OUTPUT:-}}"

cd /home/john/Thunderbird

if [ -z "$OUTPUT_FILE" ] || [ ! -f "$OUTPUT_FILE" ]; then
    echo "[hale_post_scan] No output file found for synthesis. Skipping."
    exit 0
fi

echo "[hale_post_scan] Synthesizing $SCAN_TYPE scan from $OUTPUT_FILE"

.venv/bin/python3 OpsCenter/hale_scan_wrapper.py \
    --type "$SCAN_TYPE" \
    --file "$OUTPUT_FILE" \
    --send

echo "[hale_post_scan] Synthesis complete."
