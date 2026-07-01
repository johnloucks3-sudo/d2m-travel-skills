#!/usr/bin/env python3
"""
CI EFFICACY PROBE — Lifecycle Arc Dispatch Router
==================================================
Dreams2Memories Travel, LLC · CI razor-sharp doctrine (SO 2026-06-20)

Checks:
  1. core/ops/lifecycle_decision_trees.yaml exists (arc definitions present)
  2. core/ops/lifecycle_router.py validate returns no VALIDATION ERRORS
     (uses subprocess to avoid yaml import — stdlib+requests only)
  3. core/travel/data/arc_*.json — reports last dispatch age (informational,
     not a RED trigger; dispatch frequency depends on active campaigns)

Probe does NOT re-run the engine. The repair function re-runs it.
Exit 0 = GREEN (yaml valid + router healthy). Exit 1 = RED.
"""
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

THUNDERBIRD_ROOT = Path("/home/john/Thunderbird")
VENV_PY = str(THUNDERBIRD_ROOT / ".venv" / "bin" / "python3")
DECISION_TREES = THUNDERBIRD_ROOT / "core" / "ops" / "lifecycle_decision_trees.yaml"
LIFECYCLE_ROUTER = THUNDERBIRD_ROOT / "core" / "ops" / "lifecycle_router.py"
ARC_DATA_DIR = THUNDERBIRD_ROOT / "core" / "travel" / "data"
ID = "lifecycle-arc"


def fail(m: str) -> None:
    print(f"RED {ID}: {m}")
    sys.exit(1)


def main() -> None:
    # ── CHECK 1: Decision trees yaml exists ─────────────────────────────────
    if not DECISION_TREES.exists():
        fail(
            f"lifecycle_decision_trees.yaml missing at {DECISION_TREES} — "
            "arc routing definitions absent; no arc dispatch possible"
        )

    yaml_size = DECISION_TREES.stat().st_size
    if yaml_size < 500:
        fail(
            f"lifecycle_decision_trees.yaml is suspiciously small ({yaml_size} bytes) — "
            "may be empty or truncated"
        )

    # ── CHECK 2: Router validate passes ─────────────────────────────────────
    if not LIFECYCLE_ROUTER.exists():
        fail(
            f"lifecycle_router.py missing at {LIFECYCLE_ROUTER} — "
            "arc routing engine absent"
        )

    try:
        result = subprocess.run(
            [VENV_PY, str(LIFECYCLE_ROUTER), "validate"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(THUNDERBIRD_ROOT),
        )
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        if result.returncode != 0:
            fail(
                f"lifecycle_router.py validate exited {result.returncode} — "
                f"router health failure. stdout: {stdout[:200]}. stderr: {stderr[:200]}"
            )

        if "VALIDATION ERRORS" in stdout or "VALIDATION ERRORS" in stderr:
            fail(
                f"lifecycle_router.py validate reports VALIDATION ERRORS — "
                f"arc definitions broken. stdout: {stdout[:300]}"
            )

        if "Error" in stdout or "Traceback" in stderr:
            fail(
                f"lifecycle_router.py validate output contains errors. "
                f"stdout: {stdout[:200]}. stderr: {stderr[:200]}"
            )

    except subprocess.TimeoutExpired:
        fail("lifecycle_router.py validate timed out after 30s")
    except Exception as e:
        fail(f"Failed to run lifecycle_router.py validate: {e}")

    # ── CHECK 3: Last arc dispatch (informational) ────────────────────────
    last_dispatch_info = "no arc_*.json files found (no dispatch yet or different output dir)"
    if ARC_DATA_DIR.exists():
        arc_files = sorted(
            ARC_DATA_DIR.glob("arc_*.json"),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        if arc_files:
            latest = arc_files[0]
            now = datetime.now(tz=timezone.utc)
            mtime = datetime.fromtimestamp(latest.stat().st_mtime, tz=timezone.utc)
            age_h = (now - mtime).total_seconds() / 3600
            last_dispatch_info = (
                f"last dispatch: {latest.name} ({age_h:.0f}h ago — informational only)"
            )

    print(
        f"GREEN {ID}: decision_trees.yaml valid ({yaml_size}B); "
        f"router validate passed; {last_dispatch_info}"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
