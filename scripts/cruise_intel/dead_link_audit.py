#!/usr/bin/env python3
"""
Dead Link Audit — MISSION-072
=============================
A7 Sterling build. Audits the outbound links emitted by the T2 cruise
intel report (generate_report.py LINE_URLS), plus the supplier cookie
files the scrapers depend on. Produces a dead-link report.

Scope (per tasking):
  1. HTTP-check every URL in generate_report.py's LINE_URLS map.
  2. Test Centrav / Bedsonline cookie presence.
  3. Flag CruisePlum as Commander-creds-blocked (do not guess).

This is READ + REPORT only. It does NOT modify generate_report.py.
Confirmed-dead URLs are surfaced for a human-approved patch.

Usage:
  python3 scripts/cruise_intel/dead_link_audit.py
  python3 scripts/cruise_intel/dead_link_audit.py --json out.json
  python3 scripts/cruise_intel/dead_link_audit.py --timeout 15
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from generate_report import LINE_URLS  # noqa: E402  (single source of truth)

THUNDERBIRD = Path(__file__).resolve().parent.parent.parent
CREDS_DIR = THUNDERBIRD / "creds"

# Cookie files the cruise-intel / fare scrapers actually depend on at runtime.
# Centrav is a wired dependency (creds/centrav_cookies.json, used by
# fare_watch_centrav.py + centrav_session_auto_keepalive.py).
COOKIE_TARGETS = {
    "Centrav": CREDS_DIR / "centrav_cookies.json",
}

# Sources named in the tasking but NOT wired as a runtime dependency on this
# system. Bedsonline has no scraper and no cookie file — only 2026-05-15
# screenshots. Reporting it as a "missing file" would be a manufactured red;
# the accurate finding is that it is not a live dependency.
NOT_WIRED = {
    "Bedsonline": "No Bedsonline scraper or cookie file on this system "
                  "(only 2026-05-15 screenshots). Not a wired runtime "
                  "dependency — nothing to keep alive. Not in report FLAG_MAP.",
}

# Sources that require Commander-supplied credentials — flag, never guess.
CREDS_BLOCKED = {
    "CruisePlum": "Requires Commander login credentials. Cannot audit autonomously.",
}

# Browser-like UA — many cruise-line sites 403 a bare urllib UA.
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def check_url(url: str, timeout: int) -> dict:
    """HEAD-then-GET probe. Returns status dict."""
    def _probe(method: str) -> tuple[int | None, str]:
        try:
            req = urllib.request.Request(
                url, method=method, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status, resp.geturl()
        except urllib.error.HTTPError as e:
            return e.code, url
        except Exception as e:
            return None, str(e)

    code, info = _probe("HEAD")
    # Some servers reject HEAD (405) — retry with GET before judging dead.
    if code in (405, 403, None):
        gcode, ginfo = _probe("GET")
        if gcode is not None:
            code, info = gcode, ginfo

    if code is None:
        verdict = "DEAD"      # no response at all
    elif code < 400:
        verdict = "OK"
    elif code in (401, 403):
        verdict = "BLOCKED"   # alive but gated (bot wall / login) — not dead
    elif code == 404 or code == 410:
        verdict = "DEAD"
    else:
        verdict = f"WARN_{code}"
    return {"url": url, "http": code, "verdict": verdict, "detail": info}


def audit_links(timeout: int) -> list[dict]:
    results = []
    for line, urls in sorted(LINE_URLS.items()):
        own_url, secondary_url = urls
        for role, url in (("line_site", own_url), ("secondary", secondary_url)):
            r = check_url(url, timeout)
            r["line"] = line
            r["role"] = role
            results.append(r)
    return results


def audit_cookies() -> list[dict]:
    results = []
    for name, path in COOKIE_TARGETS.items():
        if not path.exists():
            results.append({"source": name, "path": str(path),
                            "present": False, "note": "cookie file MISSING"})
            continue
        try:
            data = json.loads(path.read_text())
            n = len(data) if isinstance(data, list) else len(data.get("cookies", []))
            mtime = datetime.fromtimestamp(
                path.stat().st_mtime, tz=timezone.utc).isoformat()
            results.append({"source": name, "path": str(path), "present": True,
                            "cookie_count": n, "last_modified": mtime})
        except Exception as e:
            results.append({"source": name, "path": str(path), "present": True,
                            "note": f"present but unreadable: {e}"})
    return results


def main() -> None:
    ap = argparse.ArgumentParser(description="Dead-link audit for cruise intel report (M-072)")
    ap.add_argument("--timeout", type=int, default=12, help="HTTP timeout seconds")
    ap.add_argument("--json", help="Write full results to this JSON path")
    args = ap.parse_args()

    print("=" * 64)
    print("DEAD LINK AUDIT — MISSION-072")
    print(f"Generated: {datetime.now(timezone.utc).isoformat()}")
    print(f"Source: generate_report.py LINE_URLS ({len(LINE_URLS)} lines)")
    print("=" * 64)

    links = audit_links(args.timeout)
    cookies = audit_cookies()

    dead = [r for r in links if r["verdict"] == "DEAD"]
    blocked = [r for r in links if r["verdict"] == "BLOCKED"]
    warn = [r for r in links if r["verdict"].startswith("WARN")]
    ok = [r for r in links if r["verdict"] == "OK"]

    print(f"\n-- LINK RESULTS: {len(links)} checked — "
          f"{len(ok)} OK · {len(blocked)} BLOCKED · {len(warn)} WARN · {len(dead)} DEAD --")
    for r in links:
        flag = {"OK": "  ", "DEAD": "🔴", "BLOCKED": "🔒"}.get(r["verdict"], "⚠️ ")
        print(f"  {flag} [{r['verdict']:>8}] {r['line']:<28} {r['role']:<10} "
              f"HTTP {r['http']}  {r['url']}")

    if dead:
        print("\n🔴 CONFIRMED DEAD (patch LINE_URLS in generate_report.py):")
        for r in dead:
            print(f"   - {r['line']} ({r['role']}): {r['url']}  → HTTP {r['http']}")

    print("\n-- COOKIE PRESENCE --")
    for c in cookies:
        if not c["present"]:
            print(f"  🔴 {c['source']:<12} MISSING  ({c['path']})")
        elif "note" in c:
            print(f"  ⚠️  {c['source']:<12} {c['note']}")
        else:
            print(f"  ✅ {c['source']:<12} {c['cookie_count']} cookies, "
                  f"modified {c['last_modified']}")

    print("\n-- CREDS-BLOCKED SOURCES (flag, do not guess) --")
    for name, reason in CREDS_BLOCKED.items():
        print(f"  🔒 {name}: {reason}")

    print("\n-- NOT WIRED (named in tasking, no runtime dependency — informational) --")
    for name, reason in NOT_WIRED.items():
        print(f"  ℹ️  {name}: {reason}")

    if args.json:
        payload = {
            "generated": datetime.now(timezone.utc).isoformat(),
            "summary": {"ok": len(ok), "blocked": len(blocked),
                        "warn": len(warn), "dead": len(dead)},
            "links": links,
            "cookies": cookies,
            "creds_blocked": CREDS_BLOCKED,
            "not_wired": NOT_WIRED,
        }
        Path(args.json).write_text(json.dumps(payload, indent=2))
        print(f"\nJSON → {args.json}")

    # Exit non-zero only on genuinely DEAD links (BLOCKED/WARN are informational)
    sys.exit(1 if dead else 0)


if __name__ == "__main__":
    main()
