#!/usr/bin/env python3
"""
portal_live_probe.py — Live Session Verification Engine
Dreams2Memories Travel, LLC · 2026-06-19

The Gap This Closes:
  keepalive_supervisor.py reads STATE FILES — cookie expiry timestamps.
  A cookie can say "27h remaining" while the server has invalidated the session.
  Commander hits the wall, spends 20 min re-authing. Unacceptable.

  This script PROVES sessions by hitting real authenticated endpoints.
  If the endpoint returns a login redirect → session is dead → auto-heal → alert.

Critical Portals:
  centrav     — https://www.centrav.com/  (cookie: laravel_session)
  regent_d2m  — https://www.rssc.com/agent/default.aspx (cookie: ASPXAUTH, d2m)
  regent_oa   — https://www.rssc.com/agent/default.aspx (cookie: ASPXAUTH, oa)
  perx        — https://www.perx.com/account/ (cookie: session)
  tess        — JWT bearer via stored token

Run:
  python3 scripts/portal_live_probe.py          # probe all, auto-heal, alert on failure
  python3 scripts/portal_live_probe.py --dry-run # probe only, no heal, no alert
  python3 scripts/portal_live_probe.py --portal centrav  # one portal

Exit codes:
  0 = all probes passed
  1 = one or more probes failed (and auto-heal also failed)
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

THUNDERBIRD = Path(__file__).parent.parent
CREDS_DIR = THUNDERBIRD / "creds"
STATE_FILE = THUNDERBIRD / "OpsCenter" / "state" / "portal_live_health.json"
ALERT_DEDUP_FILE = THUNDERBIRD / "OpsCenter" / "state" / "portal_probe_alert_dedup.json"
LOGS_DIR = THUNDERBIRD / "logs"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("portal-probe")

# ---------------------------------------------------------------------------
# Portal definitions — endpoint, cookie file, login-detect string, heal cmd
# ---------------------------------------------------------------------------
PORTALS = {
    "centrav": {
        "url": "https://www.centrav.com/",
        "cookie_file": CREDS_DIR / "centrav_cookies.json",
        "login_indicators": ["login", "trust", "sign-in"],
        # SUPPRESSED (RT-CENTRAV-SPAWN 2026-08-09): heal_cmd intentionally omitted.
        # Commander 2026-08-07 killed all airfare session keep-alives except Skybird —
        # this probe ran every 10 min (d2m-portal-live-probe.timer) and called
        # centrav_session_relogin.py unconditionally on every DEAD reading with no
        # suppression check, which was one of the drivers of the Chrome/relogin spawn
        # loop. Probe still runs and reports DEAD/ALIVE; it no longer auto-heals.
        "heal_timeout": 120,
        "manual_cmd": "python3 scripts/centrav_session_relogin.py",
        "client_affecting": True,
        "note": "B2B flight pricing. Dead = no wholesale quotes. Auto-heal suppressed 2026-08-07 — Centrav on-demand only.",
    },
    # regent_d2m / regent_oa REMOVED from automated probe scope 2026-07-16 (Commander
    # directive): Regent cookies are on-demand only (browser-based capability covers
    # it when needed) — no daily fare-check login requirement, so no automated
    # probe/heal/page cycle. Consistent with the client_affecting=False policy already
    # set in credentials_health_check.py on 2026-07-10. Manual probe still possible via
    # scripts/rssc_session_keepalive.py directly if ever needed.
    "perx": {
        "url": "https://www.perx.com/account/",
        "cookie_file": CREDS_DIR / "perx_cookies.json",
        "login_indicators": ["login", "signin", "account/login"],
        "heal_cmd": [sys.executable, str(THUNDERBIRD / "scripts" / "perx_session_keepalive.py")],
        "heal_timeout": 90,
        "manual_cmd": "python3 scripts/perx_session_keepalive.py",
        "client_affecting": True,
        "note": "Perx.com — Silversea agent rate access.",
        # Perx /account/ ALWAYS 302s to /login/ even with valid session (JS-rendered auth).
        # HTTP probe is unreliable. Use cookie expiry check instead.
        "use_cookie_expiry_check": True,
        "cookie_expiry_min_seconds": 300,
    },
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def _load_cookies(cookie_file: Path) -> dict:
    """Load cookies from JSON file → requests-compatible dict."""
    if not cookie_file.exists():
        return {}
    try:
        raw = json.loads(cookie_file.read_text())
        if isinstance(raw, list):
            return {c["name"]: c["value"] for c in raw if "name" in c and "value" in c}
        if isinstance(raw, dict):
            return {k: v for k, v in raw.items() if isinstance(v, str)}
    except Exception:
        pass
    return {}


def _probe_cookie_expiry(name: str, cfg: dict) -> dict:
    """Check portal health via cookie expiry timestamps (for sites that always redirect on HTTP)."""
    import time as _time
    cookie_file: Path = cfg["cookie_file"]
    if not cookie_file.exists():
        return {"status": "NO_COOKIES", "alive": False, "reason": "Cookie file missing"}
    try:
        raw = json.loads(cookie_file.read_text())
        cookies = raw if isinstance(raw, list) else []
    except Exception:
        return {"status": "NO_COOKIES", "alive": False, "reason": "Cookie file unreadable"}

    # Find sessionid
    sess = next((c for c in cookies if c.get("name") == "sessionid"
                 and cfg["cookie_file"].name.split("_")[0] in c.get("domain", "").lower()
                 + name.lower()), None)
    if sess is None:
        # Try any matching domain
        sess = next((c for c in cookies if c.get("name") == "sessionid"), None)
    if sess is None:
        return {"status": "DEAD", "alive": False, "reason": "No sessionid cookie found"}

    expiry = sess.get("expires") or sess.get("expiry", -1)
    min_sec = cfg.get("cookie_expiry_min_seconds", 300)

    if expiry and expiry > 0:
        remaining = expiry - _time.time()
        if remaining < min_sec:
            return {"status": "DEAD", "alive": False,
                    "reason": f"sessionid expires in {remaining:.0f}s (< {min_sec}s threshold)"}
        return {"status": "ALIVE", "alive": True,
                "reason": f"sessionid valid for {remaining/3600:.1f}h more"}
    # Session cookie (no expiry) — assume alive (will fail when Playwright login is needed)
    return {"status": "ALIVE", "alive": True, "reason": "sessionid present (session cookie, no expiry)"}


def probe_portal(name: str, cfg: dict) -> dict:
    """Hit the portal endpoint. Return {status, final_url, alive, reason}."""
    # Some portals (e.g. Perx) always redirect to login even with valid session cookies.
    # For these, use cookie expiry check instead of HTTP probe.
    if cfg.get("use_cookie_expiry_check"):
        return _probe_cookie_expiry(name, cfg)

    cookies = _load_cookies(cfg["cookie_file"])
    if not cookies:
        return {"status": "NO_COOKIES", "alive": False, "reason": f"Cookie file missing or empty: {cfg['cookie_file'].name}"}

    try:
        sess = requests.Session()
        for k, v in cookies.items():
            sess.cookies.set(k, v)
        resp = sess.get(cfg["url"], headers=HEADERS, timeout=15, allow_redirects=True)
        final_url = resp.url.lower()
        body_sample = resp.text[:2000].lower()

        dead = any(ind in final_url or ind in body_sample for ind in cfg["login_indicators"])
        if dead:
            return {"status": "DEAD", "alive": False, "reason": f"Login page detected — final_url: {resp.url[:80]}",
                    "http_status": resp.status_code}
        return {"status": "ALIVE", "alive": True, "reason": f"HTTP {resp.status_code}, URL ok",
                "http_status": resp.status_code}
    except requests.exceptions.Timeout:
        return {"status": "TIMEOUT", "alive": False, "reason": "Request timed out after 15s"}
    except Exception as e:
        return {"status": "ERROR", "alive": False, "reason": str(e)[:120]}


def heal_portal(name: str, cfg: dict) -> bool:
    """Run the auto-heal command. Return True if it succeeded."""
    cmd = cfg.get("heal_cmd")
    if not cmd:
        return False
    log.info(f"[{name}] Auto-healing — {' '.join(str(c) for c in cmd)}")
    try:
        result = subprocess.run(cmd, timeout=cfg.get("heal_timeout", 90),
                                capture_output=True, text=True, cwd=str(THUNDERBIRD))
        if result.returncode == 0:
            log.info(f"[{name}] Heal succeeded")
            return True
        log.warning(f"[{name}] Heal returned rc={result.returncode}: {result.stderr[-200:]}")
        return False
    except subprocess.TimeoutExpired:
        log.warning(f"[{name}] Heal timed out")
        return False
    except Exception as e:
        log.warning(f"[{name}] Heal error: {e}")
        return False


def _telegram_alert(message: str):
    """Page Commander on Telegram."""
    try:
        env_file = THUNDERBIRD / ".env"
        env = {}
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if "=" in line and not line.strip().startswith("#"):
                    k, _, v = line.partition("=")
                    env[k.strip()] = v.strip().strip('"').strip("'")
        token = env.get("TELEGRAM_BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN", "")
        chat_id = env.get("TELEGRAM_COMMANDER_ID") or os.environ.get("TELEGRAM_COMMANDER_ID", "")
        if not token or not chat_id:
            log.warning("Telegram not configured — alert not sent")
            return
        import urllib.request, urllib.parse
        payload = json.dumps({"chat_id": chat_id, "text": message}).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=payload, headers={"Content-Type": "application/json"}, method="POST")
        urllib.request.urlopen(req, timeout=5)
        log.info("Telegram alert sent")
    except Exception as e:
        log.warning(f"Telegram alert failed: {e}")


def run_probes(portals_to_check: list[str], dry_run: bool = False) -> int:
    """Probe, heal, alert. Returns number of failed portals."""
    now = datetime.now(timezone.utc).isoformat()
    results = {}
    failures = []

    for name in portals_to_check:
        cfg = PORTALS.get(name)
        if not cfg:
            log.warning(f"Unknown portal: {name}")
            continue

        log.info(f"[{name}] Probing {cfg['url']}")
        probe = probe_portal(name, cfg)
        results[name] = {**probe, "probed_at": now, "client_affecting": cfg["client_affecting"]}

        if probe["alive"]:
            log.info(f"[{name}] ✅ ALIVE")
        else:
            log.warning(f"[{name}] ❌ DEAD — {probe['reason']}")
            if not dry_run:
                healed = heal_portal(name, cfg)
                if healed:
                    # Verify again after heal
                    recheck = probe_portal(name, cfg)
                    results[name]["healed"] = True
                    results[name]["status"] = recheck["status"]
                    results[name]["alive"] = recheck["alive"]
                    if recheck["alive"]:
                        log.info(f"[{name}] ✅ Heal verified — session live")
                    else:
                        log.warning(f"[{name}] Heal ran but session still dead")
                        failures.append((name, cfg, probe))
                else:
                    results[name]["healed"] = False
                    failures.append((name, cfg, probe))
            else:
                failures.append((name, cfg, probe))

    # Write state
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    state = {
        "checked_at_utc": now,
        "overall": "ALIVE" if not failures else "DEGRADED",
        "portals_checked": len(portals_to_check),
        "failures": len(failures),
        "results": results,
    }
    if not dry_run:
        STATE_FILE.write_text(json.dumps(state, indent=2))

    # Alert if failures remain — ONE AND DONE dedup (2026-07-04, Silver/A7).
    # Mirrors scripts/credentials_health_check.py send_telegram_alerts(). This ran on
    # a 10-min timer and re-paged D2MC2C every run for as long as any portal stayed
    # broken (the single biggest repeat-noise contributor per the noise audit). Now:
    # alert once per (portal, status). The dedup state is pruned every non-dry run to
    # exactly the currently-failing set, so a portal that recovers drops its key and a
    # later failure — including a failing→healthy→failing flip — pages fresh, while an
    # ongoing failure stays silent after the first page.
    if not dry_run:
        dedup_state = {}
        if ALERT_DEDUP_FILE.exists():
            try:
                dedup_state = json.loads(ALERT_DEDUP_FILE.read_text())
            except Exception:
                dedup_state = {}

        active_names = {name for name, _, _ in failures}
        dedup_state = {k: v for k, v in dedup_state.items() if k.split("|", 1)[0] in active_names}

        new_failures = []
        for name, cfg, probe in failures:
            key = f"{name}|{probe['status']}"
            if key not in dedup_state:
                new_failures.append((name, cfg, probe))
                dedup_state[key] = now

        ALERT_DEDUP_FILE.parent.mkdir(parents=True, exist_ok=True)
        ALERT_DEDUP_FILE.write_text(json.dumps(dedup_state, indent=2))

        if new_failures:
            alert_lines = ["🚨 PORTAL LIVE PROBE — Session Failure(s)"]
            for name, cfg, probe in new_failures:
                alert_lines.append(f"\n❌ {name}: {probe['reason']}")
                alert_lines.append(f"   Manual fix: {cfg['manual_cmd']}")
            alert_lines.append("\nAuto-heal attempted — failed. Commander action required.")
            _telegram_alert("\n".join(alert_lines))

    return len(failures)


def main():
    parser = argparse.ArgumentParser(description="Live portal session probe")
    parser.add_argument("--portal", help="Single portal name to probe")
    parser.add_argument("--dry-run", action="store_true", help="Probe only, no heal, no alert, no write")
    args = parser.parse_args()

    to_check = [args.portal] if args.portal else list(PORTALS.keys())
    failed = run_probes(to_check, dry_run=args.dry_run)
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
