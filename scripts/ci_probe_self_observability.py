#!/usr/bin/env python3
"""
CI EFFICACY PROBE — Armed Overwatch (Self-Observability)
========================================================
Replaces `import core.ci.self_observability` (module-imports != sentinel-is-
watching). The overwatch's whole job is to detect silent failure — so it must
not itself fail silently. REDs if the sentinel's state file is missing or stale
(it stopped running), or unparseable. Importable-but-dead is the trap.
Exit 0 = healthy, 1 = degraded.
"""
import json
import sys
import time
from pathlib import Path

_REPO = Path.home() / "Thunderbird"
STATE = _REPO / "config" / "ci_sentinel_state.json"
STALE_HOURS = 3


def fail(m): print(f"RED self-observability: {m}"); sys.exit(1)


def main():
    # the module must at least import (the engine itself) — ensure repo on path
    sys.path.insert(0, str(_REPO))
    try:
        import core.ci.self_observability  # noqa: F401
    except Exception as e:
        fail(f"self_observability module import failed: {e}")
    if not STATE.exists():
        fail("no ci_sentinel_state.json — sentinel has never written state")
    age_h = (time.time() - STATE.stat().st_mtime) / 3600
    if age_h > STALE_HOURS:
        fail(f"stale: sentinel state {age_h:.1f}h old — overwatch stopped observing")
    try:
        watched = len(json.loads(STATE.read_text()))
    except Exception as e:
        fail(f"sentinel state unparseable: {e}")
    print(f"RAZOR_SHARP self-observability: sentinel live, {watched} services watched, {age_h:.1f}h old")
    sys.exit(0)


if __name__ == "__main__":
    main()
