#!/bin/bash
# Stop hook — CHIEF SILVER session-end check (2026-07-16, Commander directive:
# Silver mandatory + visible). Runs the deterministic internal-ops battery and
# logs the verdict to OpsCenter/silver_ledger.jsonl + hale_decisions.md.
# Never blocks session end.
cd /home/john/Thunderbird || exit 0
timeout 30 python3 -c "
from core.silver.gate import internal_ops_verdict, print_verdict
print_verdict(internal_ops_verdict())
" >> logs/silver_stop_check.log 2>&1
exit 0
