#!/usr/bin/env python3
"""A7 OC capacity probe — benchmark free-tier opencode/* models on one
identical known-answer repo task. Read-only against the repo; the only
writes are this probe's own JSON results inside .oc_probe/.

Known answer: DEFAULT_MODEL in scripts/oc_worker.py is
"opencode/deepseek-v4-flash-free" (verified by direct read).
"""
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
OC = "/home/john/.opencode/bin/opencode"
OUT = ROOT / ".oc_probe" / "bench_results.json"

TASK = (
    "Read the file scripts/oc_worker.py in the current directory. "
    "Find the variable DEFAULT_MODEL. "
    "Reply with ONLY its default string value and nothing else."
)
EXPECTED = "opencode/deepseek-v4-flash-free"

MODELS = [
    "opencode/deepseek-v4-flash-free",  # control
    "opencode/laguna-s-2.1-free",
    "opencode/ling-3.0-flash-free",
    "opencode/mimo-v2.5-free",
    "opencode/nemotron-3-ultra-free",
    "opencode/north-mini-code-free",
]

TIMEOUT = 300


def run_one(model):
    t0 = time.time()
    rec = {"model": model}
    try:
        p = subprocess.run(
            [OC, "run", "--model", model, TASK],
            capture_output=True, text=True, timeout=TIMEOUT, cwd=str(ROOT),
        )
        out = (p.stdout or "").strip()
        rec.update(
            rc=p.returncode,
            secs=round(time.time() - t0, 1),
            stdout_len=len(out),
            correct=EXPECTED in out,
            tail=out[-300:],
            stderr=(p.stderr or "")[-300:],
        )
    except subprocess.TimeoutExpired:
        rec.update(rc="TIMEOUT", secs=round(time.time() - t0, 1),
                   stdout_len=0, correct=False, tail="", stderr="timeout")
    except Exception as e:  # noqa: BLE001
        rec.update(rc="ERROR", secs=round(time.time() - t0, 1),
                   stdout_len=0, correct=False, tail="", stderr=str(e)[:300])
    return rec


def main():
    results = []
    for m in MODELS:
        r = run_one(m)
        results.append(r)
        print(f"{m}: rc={r['rc']} {r['secs']}s correct={r['correct']} "
              f"len={r['stdout_len']}", flush=True)
        OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
