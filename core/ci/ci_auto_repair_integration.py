#!/usr/bin/env python3
"""
Integration point: Auto-repair wired into infra_bot heartbeat.
This module is called by infra_bot after each health scan.

CUTOVER 2026-07-02 (Sterling A7) — SAFETY CONTRACT MADE REAL
------------------------------------------------------------
BEFORE: this spawned core/ci/ci_auto_repair_engine.py, whose main() fired ALL
        raw repair_ functions unattended on every RED heartbeat — INCLUDING
        destructive ones (source-file rewrites, settings.json edits, registry
        recreation) with NO tier gate. That was the keystone hazard.

AFTER:  this spawns core/ci/repairs/rapid_repair.py (run_all_red), the SAFE path:
        explore -> assess -> tier-gate -> dry-run-by-default -> verify-after,
        with a CONSERVATIVE armed-tier policy (SAFE auto / CAUTION+DESTRUCTIVE
        staged for one-touch confirm) and a durable cross-spawn anti-flap gate.

The old engine file is KEPT INTACT — its repair_ bodies are imported by the
warehouse capabilities. It is simply no longer the unattended entry point.

Non-blocking: rapid_repair runs up to 48 probes (up to 60s each) + verify-settle
sleeps. We spawn it DETACHED (Popen, start_new_session=True) so the infra_bot
heartbeat never blocks. Everything is wrapped so ANY error is logged and returns
gracefully — this MUST NEVER crash the heartbeat.
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime

THUNDERBIRD_ROOT = Path("/home/john/Thunderbird")
VENV_PY = str(THUNDERBIRD_ROOT / ".venv" / "bin" / "python3")
RAPID_REPAIR = THUNDERBIRD_ROOT / "core" / "ci" / "repairs" / "rapid_repair.py"
AUTO_REPAIR_LOG = THUNDERBIRD_ROOT / "logs" / "ci_auto_repair_integration.log"


def trigger_auto_repair():
    """
    Called by infra_bot after health scan. Spawns the SAFE rapid-repair dispatch
    DETACHED (non-blocking). Returns True if the spawn succeeded, False on any
    error — never raises, so the heartbeat is protected.
    """
    try:
        py = VENV_PY if Path(VENV_PY).exists() else sys.executable
        proc = subprocess.Popen(
            [py, str(RAPID_REPAIR)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=str(THUNDERBIRD_ROOT),
            start_new_session=True,
        )
        with open(AUTO_REPAIR_LOG, "a") as f:
            f.write(f"{datetime.now().isoformat()} [INTEGRATION] "
                    f"SAFE rapid-repair spawned (PID {proc.pid}) — "
                    f"{RAPID_REPAIR}\n")
        return True
    except Exception as e:
        try:
            with open(AUTO_REPAIR_LOG, "a") as f:
                f.write(f"{datetime.now().isoformat()} [INTEGRATION] "
                        f"ERROR spawning rapid-repair: {e}\n")
        except Exception:
            pass
        return False


if __name__ == "__main__":
    trigger_auto_repair()
