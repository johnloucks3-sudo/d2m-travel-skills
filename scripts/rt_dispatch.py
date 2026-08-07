#!/usr/bin/env python3
"""rt_dispatch.py — War Room seat dispatcher.

Standing models (Commander directive 2026-08-07):
  AG lane  -> gemini-3.6-flash-high   (Gemini 3.6 Flash)
  CC lane  -> claude-sonnet-4-6       (Claude Sonnet; "Sonnet 5" NOT yet exposed on agy/Poe)
Reports token usage per response (ESTIMATE: chars/4; exact usage not surfaced by agy).

Usage:
  rt_dispatch.py AG  "<prompt>" [--deliverable <path>]
  rt_dispatch.py CC  "<prompt>" [--deliverable <path>]
"""
import sys, subprocess, os, re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MODELS = {
    "AG": "gemini-3.6-flash-high",   # Gemini 3.6 Flash
    "CC": "claude-sonnet-4-6",       # Claude Sonnet 4.6 (closest to "Sonnet 5")
}

def est_tokens(text: str) -> int:
    return max(1, len(text) // 4)

def main():
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(1)
    lane = sys.argv[1].upper()
    prompt = sys.argv[2]
    model = MODELS.get(lane)
    if not model:
        print(f"unknown lane {lane!r}; use AG or CC"); sys.exit(1)
    deliv = ""
    if "--deliverable" in sys.argv:
        i = sys.argv.index("--deliverable")
        deliv = sys.argv[i + 1]
    args = [sys.executable, str(REPO / "core" / "relay" / "contact_ag.py"), prompt]
    if deliv:
        args += ["--deliverable", deliv]
    args += ["--from", "OC", "--tag", "RT-DISPATCH", "--model", model]
    r = subprocess.run(args, capture_output=True, text=True, timeout=900)
    out = (r.stdout or "") + ("\n[stderr]\n" + r.stderr[-800:] if r.returncode else "")
    tin, tout = est_tokens(prompt), est_tokens(out or "")
    print(f"[TOKEN] lane={lane} model={model} in≈{tin} out≈{tout} total≈{tin+tout}")
    print(out[-4000:])

if __name__ == "__main__":
    main()