#!/usr/bin/env python3
"""ci_sweep.py — run the CI razor-sharp sweep, print/JSON, page on degradation.
Usage:
  python3 scripts/ci_sweep.py            # human table
  python3 scripts/ci_sweep.py --json     # machine output
  python3 scripts/ci_sweep.py --page     # page Whetstone/Commander on RED/DULL/REPLACE
  python3 scripts/ci_sweep.py --no-update # don't stamp last_verified / append history
"""
import argparse
import json
import sys
sys.path.insert(0, "/home/john/Thunderbird")
from core.ci.ci_health import sweep, degradations, write_dashboard

CLIENT_AFFECTING = {"portal-access", "credential-keepalive"}  # RED/REPLACE here → escalate to Commander


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--page", action="store_true")
    ap.add_argument("--no-update", action="store_true", help="don't stamp last_verified")
    args = ap.parse_args()

    results = sweep(update_verified=not args.no_update)
    write_dashboard(results)
    degraded = degradations(results)

    if args.json:
        print(json.dumps({"results": results, "degraded": degraded}, indent=2))
    else:
        for r in results:
            extra = f" — REPLACE: {r['replace_reason']}" if r.get("replace_reason") else ""
            print(f"{r['status']:12s} {r['name']}  (probe {'ok' if r['probe_ok'] else 'FAIL'}, {r['duration_ms']}ms){extra}")
        if degraded:
            print(f"\n⚠️ {len(degraded)} CI skill(s) not razor-sharp.")

    if args.page and degraded:
        try:
            from OpsCenter.wing_page import page  # existing pager
            client_red = [d for d in degraded if d["id"] in CLIENT_AFFECTING and d["status"] in ("RED", "REPLACE")]
            audience = "commander" if client_red else "whetstone"
            msg = "CI razor-sharp degradation:\n" + "\n".join(
                f"- {d['name']}: {d['status']}"
                + (f" ({d['replace_reason']})" if d.get("replace_reason") else "")
                + f" — fallback: {d['fallback']}"
                for d in degraded)
            page(audience, msg)
        except Exception as e:
            print(f"[page failed: {e}]", file=sys.stderr)

    return 1 if any(d["status"] in ("RED", "REPLACE") for d in degraded) else 0


if __name__ == "__main__":
    sys.exit(main())
