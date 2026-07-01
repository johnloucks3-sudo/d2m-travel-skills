#!/usr/bin/env python3
"""
CI Probe — lifecycle-proposal-engine
Exit 0 = GREEN, 1 = RED.
Final stdout line: GREEN/RED lifecycle-proposal-engine: <detail>
"""

import subprocess
import sys
from pathlib import Path

THUNDERBIRD = Path(__file__).parent.parent
ENGINE = THUNDERBIRD / "scripts" / "proposal_engine.py"
SELFTEST_OUTPUT = Path("/tmp/proposal_engine_selftest.html")
STATE_FILE = THUNDERBIRD / "OpsCenter" / "state" / "proposal_engine_state.json"


def fail(m):
    print(f"RED lifecycle-proposal-engine: {m}")
    sys.exit(1)


def main():
    # 1. Run self-test
    result = subprocess.run(
        [sys.executable, str(ENGINE), "--self-test"],
        capture_output=True,
        text=True,
        cwd=str(THUNDERBIRD),
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "no output").strip().replace("\n", " ")[:200]
        fail(f"self-test failed: {detail}")

    # 2. Check output file exists and is large enough
    if not SELFTEST_OUTPUT.exists():
        fail("output file missing: /tmp/proposal_engine_selftest.html")
    size = SELFTEST_OUTPUT.stat().st_size
    if size <= 1000:
        fail(f"output file too small: {size}B (need >1000)")

    # 3. Check state file was written
    if not STATE_FILE.exists():
        fail("state file not written: OpsCenter/state/proposal_engine_state.json")

    print(f"GREEN lifecycle-proposal-engine: self-test passed; output {size}B; state written")
    sys.exit(0)


if __name__ == "__main__":
    main()
