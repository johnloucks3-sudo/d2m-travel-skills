#!/bin/bash
# Session-stop checkpoint — runs via SessionStop hook
# Writes HALE BUS state for inter-instance handoff

set -euo pipefail

TBIRD="/home/john/Thunderbird"
LOG="$TBIRD/logs/session_stop.log"

mkdir -p "$TBIRD/logs"

echo "=== SESSION STOP $(date -u +%Y-%m-%dT%H:%M:%SZ) ===" >> "$LOG"

# HALE BUS checkpoint — write state for next instance
python3 << 'EOPY' >> "$LOG" 2>&1 || true
import sys
from pathlib import Path

sys.path.insert(0, str(Path("/home/john/Thunderbird/core/hale_bus")))
try:
    from hale_bus_write import checkpoint_session
    checkpoint_session()
    print("[HALE BUS] ✅ Checkpoint written at session end")
except Exception as e:
    print(f"[HALE BUS] ⚠️ Checkpoint failed: {e}")
EOPY

echo "=== DONE $(date -u +%Y-%m-%dT%H:%M:%SZ) ===" >> "$LOG"
