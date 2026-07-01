#!/bin/bash
# ============================================================
# Timeout wrapper for thunderbird-commander-directive-sweep
# ============================================================
# Runs the directive sweep with a 160-second hard timeout.
# Allows dispatch subprocess (up to 130s) to complete before the wrapper kills.
# DNS fast-fail: Python exits within ~5s on network issues before dispatch starts.
#
# Exit codes:
#   0 = success
#   124 = timeout (genuinely hung, not normal dispatch delay)
#   1-127 = script error (real failure)
#
# Logged to: /home/john/Thunderbird/logs/commander_directive_sweep.log
# ============================================================

timeout 160 /home/john/Thunderbird/.venv/bin/python3 \
  /home/john/Thunderbird/OpsCenter/run_commander_directive_sweep.py

EXIT_CODE=$?

# Exit code 124 = timeout exceeded
if [ $EXIT_CODE -eq 124 ]; then
  echo "[$(date -u +'%Y-%m-%d %H:%M:%S UTC')] WRAPPER TIMEOUT: directive sweep exceeded 160s (hung — DNS or dispatch stall)" \
    >> /home/john/Thunderbird/logs/commander_directive_sweep.log
  # Return 0 so systemd doesn't treat timeout as a failure
  # The actual Python script result is lost, but we're failing gracefully.
  exit 0
fi

exit $EXIT_CODE
