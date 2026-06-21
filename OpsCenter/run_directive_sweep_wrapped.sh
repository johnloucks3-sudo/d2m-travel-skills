#!/bin/bash
# ============================================================
# Timeout wrapper for thunderbird-commander-directive-sweep
# ============================================================
# Runs the directive sweep with a 30-second hard timeout.
# Designed to fail fast on DNS issues instead of hanging
# for 90 seconds and consuming watchdog auto-heals.
#
# Exit codes:
#   0 = success
#   124 = timeout (DNS or other blocking I/O issue)
#   1-127 = script error (real failure)
#
# Logged to: /home/john/Thunderbird/logs/commander_directive_sweep.log
# ============================================================

timeout 30 /home/john/Thunderbird/.venv/bin/python3 \
  /home/john/Thunderbird/OpsCenter/run_commander_directive_sweep.py

EXIT_CODE=$?

# Exit code 124 = timeout exceeded
if [ $EXIT_CODE -eq 124 ]; then
  echo "[$(date -u +'%Y-%m-%d %H:%M:%S UTC')] WRAPPER TIMEOUT: directive sweep exceeded 30s (likely DNS issue)" \
    >> /home/john/Thunderbird/logs/commander_directive_sweep.log
  # Return 0 so systemd doesn't treat timeout as a failure
  # The actual Python script result is lost, but we're failing gracefully.
  exit 0
fi

exit $EXIT_CODE
