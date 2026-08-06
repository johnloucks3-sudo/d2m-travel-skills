#!/usr/bin/env python3
"""
centrav_read_fares.py — READ-ONLY Centrav fare reader (no fill, no submit).

WHY READ-ONLY (hard-won 2026-08-06, ATO-006-08): Centrav's search form is
JS-rendered on load; scripted fill→submit against it pushes healthy tabs into
'error report id' 500 states (proven repeatedly). The RELIABLE contract is to
READ fares from a tab a human already navigated to a rendered search.

USAGE — the tab must already be on a Centrav fare-results page (human-driven):
  python3 scripts/centrav_read_fares.py --borrow <tab_id> --session <sid>
  python3 scripts/centrav_read_fares.py --session <sid>   # read current tab

Reads the rendered fare matrix (Consolidator/NDC/Published) from body.innerText.
No navigation, no form, no submit, no reload. Tab is returned on exit.

Exit: 0 = fares read, 1 = no fares, 2 = no session / error page.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

BSK = "/home/john/.local/bin/bsk"


def run_bsk(*args, timeout=30) -> str:
    r = subprocess.run([BSK, *args], capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip()[:200])
    return r.stdout


def read_fares(session: str) -> dict:
    js = (
        "(()=>{var t=document.body.innerText;"
        "var px=(t.match(/\\$[\\s]?[0-9][0-9,]+/g)||[])"
        ".map(function(x){return parseFloat(x.replace(/[^0-9.]/g,''))})"
        ".filter(function(v){return v>=50});"
        "function grab(s){var i=t.indexOf(s);if(i<0)return null;"
        "var seg=t.slice(i,i+250);var m=seg.match(/\\$[\\s]?[0-9][0-9,]+/g);"
        "return m?m.slice(0,8):[];}"
        "return JSON.stringify({url:location.href,"
        "err:t.indexOf('error report')>-1||t.indexOf('Something went wrong')>-1,"
        "has_login:t.indexOf('Login to your Account')>-1,"
        "consolidator:grab('Consolidator'),"
        "ndc:grab('NDC'),"
        "published:grab('Published Fares'),"
        "all_prices:px.slice(0,20),"
        "route:(t.match(/DEN[^A-Z]{0,3}VCE|DEN\\s*[-–]\\s*VCE|\\b[A-Z]{3}\\s*[-–]\\s*[A-Z]{3}\\b/)||[''])[0]"
        "})})()"
    )
    raw = run_bsk("evaluate", js, "--session", session, timeout=20).strip()
    try:
        return json.loads(raw)
    except Exception:
        return {"parse_error": raw[:200]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--session", required=True)
    ap.add_argument("--borrow", default="", help="tab_id to borrow, read, and return")
    args = ap.parse_args()

    owned = bool(args.borrow)
    if owned:
        try:
            run_bsk("tab", "borrow", args.borrow, "--session", args.session)
        except Exception as e:
            print(f"borrow failed: {e}", file=sys.stderr)
            return 2

    try:
        data = read_fares(args.session)
        print(json.dumps(data, indent=2))
        if data.get("err") or data.get("has_login"):
            return 2
        if data.get("all_prices") or data.get("consolidator"):
            return 0
        return 1
    finally:
        if owned:
            try:
                run_bsk("tab", "return", args.borrow, "--session", args.session)
            except Exception:
                pass


if __name__ == "__main__":
    sys.exit(main())
