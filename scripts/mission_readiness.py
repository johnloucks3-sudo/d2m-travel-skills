#!/usr/bin/env python3
"""
mission_readiness.py — Thunderbird Wing Mission Readiness Check
Single command: GO/NO-GO per operation type with proof.

Usage:
  python3 scripts/mission_readiness.py          # full report
  python3 scripts/mission_readiness.py --json   # JSON output
  python3 scripts/mission_readiness.py --brief  # one-line per op

Exit codes:
  0 = ALL_GREEN  (all critical systems GO)
  1 = DEGRADED   (some non-critical portals down, ops possible)
  2 = CRITICAL   (booking or TESS down — ops blocked)
"""

import json
import sys
import subprocess
import argparse
from datetime import datetime, timezone
from pathlib import Path

THUNDERBIRD = Path("/home/john/Thunderbird")
CREDS_DIR = THUNDERBIRD / "creds"
LOG_FILE = THUNDERBIRD / "logs" / "mission_readiness.log"

# Map portal → operations it supports
OPERATION_PORTALS = {
    "BOOKING": {
        "critical": ["tess"],
        "supporting": ["room_res", "centrav"],
        "desc": "Client booking, TESS CRM, hotel/air reservations",
    },
    "CRUISE_RESEARCH": {
        "critical": ["regent_direct", "silversea"],
        "supporting": ["agent_universe", "seabourn", "windstar"],
        "desc": "Cruise pricing, availability, competitive intel",
    },
    "FLIGHT_RESEARCH": {
        "critical": ["centrav"],
        "supporting": [],
        "desc": "B2B wholesale airfare, group pricing",
    },
    "PRICE_WATCH": {
        "critical": ["centrav", "regent_direct"],
        "supporting": ["silversea", "agent_universe"],
        "desc": "Fare watch, price alerts, booking monitoring",
    },
    "HOTEL_RESEARCH": {
        "critical": ["room_res"],
        "supporting": ["kensington"],
        "desc": "Hotel availability, group rates",
    },
    "INTEL_SCAN": {
        "critical": ["agent_universe"],
        "supporting": ["regent_direct", "silversea", "magtap"],
        "desc": "Promotions, competitive scan, market intel",
    },
    "INSURANCE": {
        "critical": ["agentmax"],
        "supporting": [],
        "desc": "Allianz travel insurance quoting",
    },
    "TRANSFERS": {
        "critical": [],
        "supporting": ["kensington"],
        "desc": "Ground transfer pricing (Kiwitaxi/Blacklane)",
    },
    "TA_RATE_SIGNAL": {
        "critical": ["perx"],
        "supporting": [],
        "desc": "Perx interline rates — leading indicator: heavy Perx discounts = TA rates incoming",
    },
}


def load_cookies(path: Path) -> list:
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text())
    except Exception:
        return []


def cookie_status(cookies: list) -> dict:
    """Return {status, expires_ts, hours_left}."""
    now = datetime.now(timezone.utc).timestamp()
    best = None
    for c in cookies:
        if not isinstance(c, dict):
            continue
        exp = c.get("expires")
        if exp and exp > (now + 3600):
            if best is None or exp > best:
                best = exp

    if best is None:
        # Cookies without 'expires' field are session-only (browser handles expiry)
        no_expiry_count = sum(1 for c in cookies if isinstance(c, dict) and "expires" not in c)
        session_count = sum(1 for c in cookies if isinstance(c, dict) and c.get("expires", 1) <= 0)
        if no_expiry_count > 0 or session_count > 0:
            return {"status": "SESSION", "expires_ts": None, "hours_left": None}
        return {"status": "MISSING", "expires_ts": None, "hours_left": None}

    hours = (best - now) / 3600
    if hours < 4:
        status = "STALE"
    elif hours < 48:
        status = "WARN"
    else:
        status = "OK"
    return {"status": status, "expires_ts": best, "hours_left": round(hours, 1)}


def check_tess() -> dict:
    """Verify TESS token with a live API call."""
    try:
        result = subprocess.run(
            ["python3", "-c", """
import sys
sys.path.insert(0, '/home/john/Thunderbird')
from core.booking.thunderbird_tess import TessClient
import asyncio
async def check():
    c = TessClient()
    try:
        r = await c.get_company_info()
        return {"status": "OK", "company": r.get("name", "?"), "user_id": r.get("userId")}
    except Exception as e:
        return {"status": "FAIL", "error": str(e)}
print(__import__('json').dumps(asyncio.run(check())))
"""],
            capture_output=True, text=True, timeout=15,
            cwd=str(THUNDERBIRD)
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout.strip())
    except Exception as e:
        pass

    # Fallback: check token file directly
    token_path = THUNDERBIRD / "tess_token.json"
    if token_path.exists():
        try:
            t = json.loads(token_path.read_text())
            # Field may be 'expires_at' (seconds) or 'expiresAt' (ms)
            exp = t.get("expires_at") or t.get("expiresAt", 0)
            now = datetime.now(timezone.utc).timestamp()
            # Detect ms vs seconds (ms values > year 2100 in seconds)
            if exp > 1e12:
                exp = exp / 1000
            if exp > now:
                mins = round((exp - now) / 60)
                return {"status": "OK", "source": "token_file", "expires_min": mins}
            return {"status": "EXPIRED", "source": "token_file"}
        except Exception:
            pass

    return {"status": "UNKNOWN"}


def get_portal_statuses() -> dict:
    """Get status for all portals managed by portal_keepalive."""
    portal_cookie_files = {
        "centrav": CREDS_DIR / "centrav_cookies.json",
        "agent_universe": CREDS_DIR / "agent_universe_cookies.json",
        "room_res": CREDS_DIR / "room_res_cookies.json",
        "silversea": CREDS_DIR / "silversea_cookies.json",
        "seabourn": CREDS_DIR / "seabourn_cookies.json",
        "windstar": CREDS_DIR / "windstar_cookies.json",
        "princess": CREDS_DIR / "princess_cookies.json",
        "carnival": CREDS_DIR / "carnival_cookies.json",
        "kensington": CREDS_DIR / "kensington_cookies.json",
        "agentmax": CREDS_DIR / "agentmax_cookies.json",
        "globus": CREDS_DIR / "globus_cookies.json",
        "atlas": CREDS_DIR / "atlas_cookies.json",
        "explora": CREDS_DIR / "explora_cookies.json",
        "magtap": CREDS_DIR / "magtap_cookies.json",
        "regent_direct": CREDS_DIR / "regent_cookies.json",
        "regent_oa": CREDS_DIR / "regent_cookies_oa.json",
        "perx": CREDS_DIR / "perx_cookies.json",
        "vtg": CREDS_DIR / "vtg_cookies.json",
        "blacklane": CREDS_DIR / "blacklane_cookies.json",
    }
    statuses = {}
    for name, path in portal_cookie_files.items():
        cookies = load_cookies(path)
        if not cookies:
            # Check perx format (nested cookies key)
            if path.exists():
                try:
                    raw = json.loads(path.read_text())
                    if isinstance(raw, dict) and "cookies" in raw:
                        cookies = raw["cookies"]
                except Exception:
                    pass
        if not cookies:
            statuses[name] = {"status": "MISSING"}
        else:
            statuses[name] = cookie_status(cookies)
    return statuses


def is_portal_live(portal_name: str, statuses: dict) -> bool:
    """Return True if portal is usable (OK, SESSION, WARN)."""
    if portal_name == "tess":
        return False  # handled separately
    s = statuses.get(portal_name, {}).get("status", "MISSING")
    return s in ("OK", "SESSION", "WARN")


def assess_operation(op_name: str, op_config: dict, portal_statuses: dict, tess_status: dict) -> dict:
    """Return {verdict, critical_down, supporting_down}."""
    critical_down = []
    supporting_down = []

    for p in op_config["critical"]:
        if p == "tess":
            if tess_status.get("status") not in ("OK",):
                critical_down.append("tess")
        elif not is_portal_live(p, portal_statuses):
            critical_down.append(p)

    for p in op_config["supporting"]:
        if not is_portal_live(p, portal_statuses):
            supporting_down.append(p)

    if critical_down:
        verdict = "NO-GO"
    elif supporting_down:
        verdict = "DEGRADED"
    else:
        verdict = "GO"

    return {
        "verdict": verdict,
        "critical_down": critical_down,
        "supporting_down": supporting_down,
    }


def format_status_icon(status: str) -> str:
    return {
        "OK": "✅",
        "SESSION": "🔄",
        "WARN": "⚠️",
        "STALE": "🔴",
        "MISSING": "❌",
        "EXPIRED": "❌",
        "FAIL": "❌",
        "UNKNOWN": "❓",
        "DEGRADED": "⚠️",
        "GO": "✅ GO",
        "NO-GO": "❌ NO-GO",
    }.get(status, status)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--brief", action="store_true")
    args = parser.parse_args()

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M MDT")

    # Gather data
    portal_statuses = get_portal_statuses()
    tess_status = check_tess()

    # Assess each operation
    op_results = {}
    for op_name, op_config in OPERATION_PORTALS.items():
        op_results[op_name] = assess_operation(op_name, op_config, portal_statuses, tess_status)

    # Overall verdict
    verdicts = [r["verdict"] for r in op_results.values()]
    if "NO-GO" in verdicts:
        overall = "CRITICAL"
        exit_code = 2
    elif "DEGRADED" in verdicts:
        overall = "DEGRADED"
        exit_code = 1
    else:
        overall = "ALL_GREEN"
        exit_code = 0

    if args.json:
        print(json.dumps({
            "timestamp": now_str,
            "overall": overall,
            "tess": tess_status,
            "portals": portal_statuses,
            "operations": op_results,
        }, indent=2))
        sys.exit(exit_code)

    if args.brief:
        print(f"THUNDERBIRD READINESS [{overall}] — {now_str}")
        for op, result in op_results.items():
            icon = format_status_icon(result["verdict"])
            print(f"  {op:<20} {icon}")
        sys.exit(0)  # reporting only — NO-GO status is informational, not a task failure

    # Full report
    print(f"\n{'='*60}")
    print(f"  THUNDERBIRD MISSION READINESS — {now_str}")
    print(f"  Overall: {overall}")
    print(f"{'='*60}")

    # TESS status
    t_icon = "✅" if tess_status.get("status") == "OK" else "❌"
    t_detail = ""
    if tess_status.get("expires_min"):
        t_detail = f" ({tess_status['expires_min']} min remaining)"
    elif tess_status.get("error"):
        t_detail = f" — {tess_status['error'][:50]}"
    print(f"\n  TESS CRM  {t_icon}  {tess_status.get('status','?')}{t_detail}")

    # Operations
    print(f"\n  OPERATIONS:")
    for op_name, result in op_results.items():
        v = result["verdict"]
        icon = format_status_icon(v)
        desc = OPERATION_PORTALS[op_name]["desc"]
        print(f"  {op_name:<20} {icon:<12} {desc}")
        if result["critical_down"]:
            print(f"    {'':20} ⛔ BLOCKED: {', '.join(result['critical_down'])}")
        if result["supporting_down"]:
            print(f"    {'':20} ⚠️  degraded: {', '.join(result['supporting_down'])}")

    # Portal detail
    print(f"\n  PORTAL SESSIONS:")
    for name, s in sorted(portal_statuses.items()):
        status = s.get("status", "?")
        icon = format_status_icon(status)
        hours = s.get("hours_left")
        detail = f"{hours:.0f}h" if hours else status
        print(f"    {name:<22} {icon}  {detail}")

    # Issues requiring action
    missing_creds = [n for n, s in portal_statuses.items() if s.get("status") == "MISSING"]
    stale = [n for n, s in portal_statuses.items() if s.get("status") == "STALE"]

    if missing_creds or stale:
        print(f"\n  ACTION REQUIRED:")
        if stale:
            print(f"    🔴 STALE (refresh now): {', '.join(stale)}")
        if missing_creds:
            print(f"    ❌ NO COOKIES (need login): {', '.join(missing_creds)}")

    print(f"\n{'='*60}\n")

    # Log to file
    LOG_FILE.parent.mkdir(exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(f"{now_str} | {overall} | TESS:{tess_status.get('status','?')} | "
                f"NOGO:{[op for op,r in op_results.items() if r['verdict']=='NO-GO']} | "
                f"STALE:{stale}\n")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
