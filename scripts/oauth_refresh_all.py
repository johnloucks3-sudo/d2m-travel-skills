#!/usr/bin/env python3
"""oauth_refresh_all.py — consolidated, idempotent OAuth/keepalive refresher.

Runs every refresh mechanism SEQUENTIALLY (never parallel — avoids token
endpoint rate limits and cross-writes), captures rc/time, and writes a single
health record to OpsCenter/keepalive_health.json. Consolidation of the OAuth/
token keepalive pile (RT-KEEPALIVES AG/CC plan).

Mechanisms (existing, reused — this is an orchestrator, not new refresh logic):
  johnloucks3-oauth   scripts/johnloucks3_mcp_oauth_refresh.py
  d2mconcierge-oauth  scripts/d2mconcierge_mcp_oauth_refresh.py
  claude-oauth        hooks/claude_oauth_keepalive.sh
  tess-token          scripts/tess_token_keepalive.py
Usage: oauth_refresh_all.py [--timeout N]
"""
import json
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
HEALTH = REPO / "OpsCenter" / "keepalive_health.json"
STEPS = [
    ("johnloucks3-oauth",  [sys.executable, str(REPO / "scripts" / "johnloucks3_mcp_oauth_refresh.py")]),
    ("d2mconcierge-oauth", [sys.executable, str(REPO / "scripts" / "d2mconcierge_mcp_oauth_refresh.py")]),
    ("claude-oauth",       ["/bin/bash", str(REPO / "hooks" / "claude_oauth_keepalive.sh")]),
    ("tess-token",         [sys.executable, str(REPO / "scripts" / "tess_token_keepalive.py")]),
]

def main() -> int:
    timeout = int(sys.argv[sys.argv.index("--timeout") + 1]) if "--timeout" in sys.argv else 240
    MT = timezone(timedelta(hours=-6))
    results = {}
    for name, cmd in STEPS:
        t0 = time.time()
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            ok = r.returncode == 0
            results[name] = {"rc": r.returncode, "s": round(time.time() - t0, 1),
                             "out": (r.stdout or "").strip()[-120:], "ok": ok}
        except subprocess.TimeoutExpired:
            results[name] = {"rc": "timeout", "s": timeout, "out": "", "ok": False}
        except Exception as e:
            results[name] = {"rc": "err", "s": round(time.time() - t0, 1), "out": str(e)[:120], "ok": False}
    health = {"ts": datetime.now(MT).isoformat(timespec="seconds"), "results": results,
              "all_ok": all(v["ok"] for v in results.values())}
    HEALTH.write_text(json.dumps(health, indent=1))
    print(json.dumps(health, indent=1))
    return 0 if health["all_ok"] else 1

if __name__ == "__main__":
    sys.exit(main())