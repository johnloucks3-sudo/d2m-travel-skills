#!/usr/bin/env python3
"""
Credentials Health Check — Auto-audit all Wing credentials.
============================================================
Dreams2Memories Travel, LLC | Thunderbird Wing

Checks validity of all credential/cookie files. Alerts via Telegram D2MC2C
for expired or near-expiry client-affecting credentials.

Outputs to:
  - stdout (plain text summary)
  - OpsCenter/state/credentials_health.json  (machine-readable for brief)
  - logs/credentials_health.log              (append log)

Run:
  python3 scripts/credentials_health_check.py           # check + alert
  python3 scripts/credentials_health_check.py --quiet   # no Telegram
  python3 scripts/credentials_health_check.py --json    # JSON output only

SO 2026-06-04: All credentials need keepalive coverage. Centrav + Regent
are client-affecting — expired = no B2B quotes, no portal access.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────

THUNDERBIRD = Path(__file__).resolve().parent.parent
CREDS_DIR = THUNDERBIRD / "creds"
STATE_DIR = THUNDERBIRD / "OpsCenter" / "state"
LOG_DIR = THUNDERBIRD / "logs"
STATE_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

HEALTH_STATE = STATE_DIR / "credentials_health.json"
OVERNIGHT_LOG = STATE_DIR / "overnight_ops_log.json"
ALERT_DEDUP = STATE_DIR / "credentials_alert_dedup.json"

MT = timezone(timedelta(hours=-6))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s CREDS %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(str(LOG_DIR / "credentials_health.log"), mode="a"),
    ],
)
log = logging.getLogger("creds_health")

# ── Credential catalog ─────────────────────────────────────────────────────────
# Format: name → {file, type, client_affecting, alert_hours_ahead, notes}

CREDENTIALS = {
    "centrav_cookies": {
        "file": CREDS_DIR / "centrav_cookies.json",
        "type": "cookies",
        "client_affecting": True,
        "alert_hours_ahead": 2,  # tightened 2026-07-04 — was 48h vs ~7h natural rotation window, alerted every run
        "notes": "B2B flight pricing. Expired = no wholesale quotes. Needs OTP reauth.",
        "reauth_cmd": "python3 scripts/portal_keepalive.py --portal centrav",
        # A7 2026-06-11: laravel_session is the auth gate. Prior shortest-expiry logic
        # picked _gat_gtag analytics cookie (21h) — same session, same expiry group.
        # Real fix: check laravel_session directly.
        "auth_cookie_names": ["laravel_session"],
        "auth_domain": "centrav.com",
    },
    "regent_cookies": {
        "file": CREDS_DIR / "regent_cookies.json",
        "type": "cookies",
        "client_affecting": True,
        "alert_hours_ahead": 2,  # tightened 2026-07-04 — was 48h vs ~7h natural rotation window, alerted every run
        "notes": "Regent portal (direct D2M account). Ely/Nichols/Furlow/McLeod bookings.",
        "reauth_cmd": "python3 scripts/portal_keepalive.py --portal regent_direct",
        "timer": "portal-keepalive.timer",
        # A7 2026-06-11: ASPXAUTH is the auth gate (httpOnly, www.rssc.com, ~24h TTL).
        # Prior shortest-expiry logic picked _hjSession_1263849 (HotJar analytics, expired)
        # or ASP.NET_SessionId with a pre-epoch corrupt timestamp (-494774h) — both wrong.
        "auth_cookie_names": ["ASPXAUTH"],
        "auth_domain": "rssc.com",
    },
    "regent_cookies_oa": {
        "file": CREDS_DIR / "regent_cookies_oa.json",
        "type": "cookies",
        "client_affecting": True,
        "alert_hours_ahead": 2,  # tightened 2026-07-04 — was 48h vs ~7h natural rotation window, alerted every run
        "notes": "Regent portal (OA account). Loucks + McLeod OA bookings.",
        "reauth_cmd": "python3 scripts/portal_keepalive.py --portal regent_oa",
        "timer": "portal-keepalive.timer",
        "auth_cookie_names": ["ASPXAUTH"],   # A7 2026-06-11: same gate as regent_direct
        "auth_domain": "rssc.com",
    },
    "gmail_token": {
        "file": CREDS_DIR / "gmail_token.json",
        "type": "oauth_token",
        "client_affecting": True,
        "alert_hours_ahead": 24,
        "notes": "d2mconcierge Gmail. Critical — all Wing email operations.",
        "reauth_cmd": "systemctl --user restart claude-oauth-keepalive.timer",
    },
    "johnloucks3_token": {
        "file": CREDS_DIR / "johnloucks3_token.json",
        "type": "oauth_token",
        "client_affecting": True,
        "alert_hours_ahead": 24,
        "notes": "Commander Gmail (johnloucks3). Internal send path.",
        "reauth_cmd": "python3 api/thunderbird_google_auth.py --authorize-headless",
    },
    "perx_cookies": {
        "file": CREDS_DIR / "perx_cookies.json",
        "type": "cookies",
        # 2026-07-04: NOT client-affecting. Perx is a pricing-intel scraper session
        # (Silversea rate recon), not a login the Commander performs and not on any
        # client-send path. Flagging it CLIENT drove the "3 client alerts" doomsday.
        "client_affecting": False,
        "alert_hours_ahead": 24,
        "notes": "Perx.com — Silversea agent rate INTEL scraping (Westbrook recon). Non-client, auto-keepalive.",
        "reauth_cmd": "python3 scripts/perx_session_keepalive.py",
        "timer": "d2m-perx-session-keepalive.timer",
    },
    "room_res_cookies": {
        "file": CREDS_DIR / "room_res_cookies.json",
        "type": "cookies",
        "client_affecting": False,
        "alert_hours_ahead": 24,
        "notes": "Room-res hotel booking.",
        "reauth_cmd": "playwright: navigate room-res.com → login → export cookies",
    },
}

# ── Cookie expiry check ────────────────────────────────────────────────────────

def _check_cookies(cookie_file: Path, auth_cookie_names: list = None, auth_domain: str = None) -> dict:
    """Check cookie file for expiry against the auth-gate cookie.

    Bug fixed 2026-06-11 (Sterling/A7): prior logic used shortest-expiring cookie,
    which picked analytics/tracking cookies (e.g. _hjSession_1263849 HotJar, or
    ASP.NET_SessionId with a pre-epoch corrupt timestamp) and reported false EXPIRED
    when the actual auth token (ASPXAUTH, laravel_session) was healthy.

    Priority order:
      1. Named auth cookies (auth_cookie_names) scoped to auth_domain.
      2. Shortest-expiring httpOnly cookie from auth_domain.
      3. Shortest-expiring non-beacon cookie from auth_domain.
      4. Shortest-expiring non-beacon cookie across all domains (legacy fallback).

    Cookies with expiry > 10 years out are tracking beacons — skipped.
    Cookies with expiry before year 2000 are corrupt stored values — skipped.
    """
    now = time.time()
    TEN_YEARS = 10 * 365 * 24 * 3600
    EPOCH_2000 = 946684800.0

    try:
        data = json.loads(cookie_file.read_text())
    except Exception as e:
        return {"status": "error", "reason": f"Cannot read: {e}", "expires_in_hours": None}

    cookies = data if isinstance(data, list) else data.get("cookies", [])

    if not cookies:
        return {"status": "empty", "reason": "No cookies found", "expires_in_hours": None}

    def _domain_match(cookie_domain, target_domain):
        if not target_domain:
            return True
        d = (cookie_domain or "").lstrip(".")
        t = target_domain.lstrip(".")
        return d == t or d.endswith("." + t)

    def _is_beacon(exp):
        return exp is not None and exp > (now + TEN_YEARS)

    # Analytics / rate-limiter cookies are NEVER the auth gate. They carry tiny
    # TTLs by design (_gat = 1 min) so they read as "expired" almost always —
    # the source of the room_res_cookies false doomsday (2026-07-04). Skip by name.
    _ANALYTICS_PREFIXES = ("_gat", "_ga", "_gid", "_hjSession", "_hjAbsolute",
                           "_fbp", "__utm", "_dc_gtm", "sailthru_")

    def _is_analytics(name):
        n = (name or "").lower()
        return any(n.startswith(p.lower()) for p in _ANALYTICS_PREFIXES)

    def _result(exp, name, label=""):
        delta = (exp - now) / 3600
        if delta < 0:
            return {
                "status": "expired",
                "reason": f"Expired {abs(delta):.1f}h ago (cookie: {name}{label})",
                "expires_in_hours": delta,
            }
        return {
            "status": "valid",
            "reason": f"Expires in {delta:.1f}h (cookie: {name}{label})",
            "expires_in_hours": delta,
        }

    # Pass 1: named auth cookies on auth_domain
    if auth_cookie_names and auth_domain:
        for c in cookies:
            name = c.get("name", "")
            exp = c.get("expires", c.get("expiry"))
            if name.upper() in [n.upper() for n in auth_cookie_names]:
                if _domain_match(c.get("domain", ""), auth_domain):
                    if exp is None or exp <= 0:
                        return {
                            "status": "session_only",
                            "reason": f"Auth cookie {name} is session-only (no persistent expiry).",
                            "expires_in_hours": 0,
                        }
                    return _result(exp, name, " [auth-gate]")

    # Pass 2: shortest httpOnly from auth_domain
    best_exp = None
    best_name = None
    if auth_domain:
        for c in cookies:
            if not c.get("httpOnly"):
                continue
            if not _domain_match(c.get("domain", ""), auth_domain):
                continue
            exp = c.get("expires", c.get("expiry"))
            if not exp or exp < EPOCH_2000 or _is_beacon(exp) or _is_analytics(c.get("name", "")):
                continue
            if best_exp is None or exp < best_exp:
                best_exp = exp
                best_name = c.get("name", "?")
    if best_exp is not None:
        return _result(best_exp, best_name, " [httpOnly+domain]")

    # Pass 3: shortest non-beacon from auth_domain
    best_exp = None
    best_name = None
    if auth_domain:
        for c in cookies:
            if not _domain_match(c.get("domain", ""), auth_domain):
                continue
            exp = c.get("expires", c.get("expiry"))
            if not exp or exp < EPOCH_2000 or _is_beacon(exp) or _is_analytics(c.get("name", "")):
                continue
            if best_exp is None or exp < best_exp:
                best_exp = exp
                best_name = c.get("name", "?")
    if best_exp is not None:
        return _result(best_exp, best_name, " [domain-scoped]")

    # Pass 4: legacy fallback — shortest non-beacon, all domains
    best_exp = None
    best_name = None
    session_only = True
    for c in cookies:
        exp = c.get("expires", c.get("expiry", -1))
        name = c.get("name", "?")
        if exp is None or exp <= 0:
            continue
        session_only = False
        if exp < EPOCH_2000 or _is_beacon(exp) or _is_analytics(name):
            continue
        if best_exp is None or exp < best_exp:
            best_exp = exp
            best_name = name

    if best_exp is None:
        if session_only:
            return {
                "status": "session_only",
                "reason": "All cookies are session-only (no persistent expiry). Likely invalid.",
                "expires_in_hours": 0,
            }
        return {"status": "unknown", "reason": "No valid expiry timestamps found", "expires_in_hours": None}

    return _result(best_exp, best_name)


def _check_oauth_token(token_file: Path) -> dict:
    """Check OAuth token file for expiry."""
    now = time.time()

    try:
        data = json.loads(token_file.read_text())
    except Exception as e:
        return {"status": "error", "reason": f"Cannot read: {e}", "expires_in_hours": None}

    expiry_str = data.get("expiry", data.get("token_expiry", ""))
    if not expiry_str:
        # Has a refresh token — will auto-refresh on use
        if data.get("refresh_token"):
            return {"status": "valid", "reason": "Has refresh_token — will auto-refresh", "expires_in_hours": 9999}
        return {"status": "unknown", "reason": "No expiry or refresh_token found", "expires_in_hours": None}

    try:
        expiry_str_clean = expiry_str.rstrip("Z").split(".")[0]
        from datetime import datetime
        exp_dt = datetime.fromisoformat(expiry_str_clean).replace(tzinfo=timezone.utc)
        delta_hours = (exp_dt.timestamp() - now) / 3600
    except Exception:
        return {"status": "unknown", "reason": f"Cannot parse expiry: {expiry_str}", "expires_in_hours": None}

    if delta_hours < 0:
        if data.get("refresh_token"):
            return {"status": "valid", "reason": f"Access token expired but has refresh_token (auto-refreshes)", "expires_in_hours": 9999}
        return {"status": "expired", "reason": f"Token expired {abs(delta_hours):.1f}h ago, no refresh_token", "expires_in_hours": delta_hours}

    # A short-lived access token with a refresh_token present is healthy at any
    # remaining hour count — that's how OAuth access tokens normally behave
    # (e.g. gmail_token cycles ~hourly). Fixed 2026-07-04: this used to report
    # raw delta_hours even with refresh_token present, which perpetually tripped
    # alert_hours_ahead=24 and fired a Telegram alert on every 5-min run.
    if data.get("refresh_token"):
        return {"status": "valid", "reason": f"Expires in {delta_hours:.1f}h — has refresh_token (auto-refreshes)", "expires_in_hours": 9999}

    return {"status": "valid", "reason": f"Expires in {delta_hours:.1f}h", "expires_in_hours": delta_hours}


# ── Main check ─────────────────────────────────────────────────────────────────

def run_check() -> dict:
    """Run full credential check. Returns results dict."""
    now_str = datetime.now(MT).isoformat()
    results = {"checked_at": now_str, "credentials": {}}
    alerts = []

    for name, spec in CREDENTIALS.items():
        cfile = spec["file"]

        if not cfile.exists():
            result = {"status": "missing", "reason": "File not found", "expires_in_hours": None}
        elif spec["type"] == "cookies":
            # Pass auth_cookie_names + auth_domain if defined — checks the actual
            # session gate instead of the shortest/longest-lived cookie. A7 2026-06-11.
            result = _check_cookies(
                cfile,
                auth_cookie_names=spec.get("auth_cookie_names"),
                auth_domain=spec.get("auth_domain"),
            )
        elif spec["type"] == "oauth_token":
            result = _check_oauth_token(cfile)
        else:
            result = {"status": "unknown", "reason": "Unknown type", "expires_in_hours": None}

        result["client_affecting"] = spec["client_affecting"]
        result["notes"] = spec["notes"]
        result["reauth_cmd"] = spec["reauth_cmd"]
        results["credentials"][name] = result

        status = result["status"]
        exp_hours = result.get("expires_in_hours")
        alert_ahead = spec["alert_hours_ahead"]

        needs_alert = (
            status in ("expired", "missing", "error", "session_only")
            or (status == "valid" and exp_hours is not None and exp_hours < alert_ahead and exp_hours != 9999)
        )

        if needs_alert:
            alerts.append({
                "name": name,
                "status": status,
                "client_affecting": spec["client_affecting"],
                "reason": result["reason"],
                "reauth_cmd": spec["reauth_cmd"],
            })
            log.warning(f"{'🔴 CLIENT' if spec['client_affecting'] else '🟡'} {name}: {status} — {result['reason']}")
        else:
            log.info(f"✅ {name}: {result['reason'][:80]}")

    results["alerts"] = alerts
    results["alert_count"] = len(alerts)
    results["client_affecting_alerts"] = [a for a in alerts if a["client_affecting"]]

    return results


def save_state(results: dict):
    """Write health state to OpsCenter/state/ for brief pickup."""
    HEALTH_STATE.write_text(json.dumps(results, indent=2))
    log.info(f"Health state written to {HEALTH_STATE}")

    # Append to overnight ops log
    existing = []
    if OVERNIGHT_LOG.exists():
        try:
            existing = json.loads(OVERNIGHT_LOG.read_text())
        except Exception:
            existing = []

    entry = {
        "ts": results["checked_at"],
        "event": "credentials_health_check",
        "alert_count": results["alert_count"],
        "client_alerts": len(results["client_affecting_alerts"]),
        "details": [f"{a['name']}: {a['status']}" for a in results["alerts"]],
    }
    # STATE-CHANGE ONLY (2026-07-04): the check runs every ~4 min. Appending an
    # identical entry every run is what rendered the morning brief's wall of 30
    # red "credentials_health_check" lines — the doomsday the Commander sees.
    # Only append when the alert signature changes vs the last entry; otherwise
    # just refresh the last entry's timestamp so the brief shows one current line.
    signature = sorted(entry["details"])
    last_sig = sorted(existing[-1]["details"]) if existing else None
    if existing and last_sig == signature:
        existing[-1]["ts"] = entry["ts"]
    else:
        existing.append(entry)
    # Keep last 30 entries
    OVERNIGHT_LOG.write_text(json.dumps(existing[-30:], indent=2))


def send_telegram_alerts(results: dict):
    """Send D2MC2C alert for client-affecting credential failures.

    ONE AND DONE (fixed 2026-07-04 — Commander directive, Silver/A7): this ran
    on a 5-min timer and fired an identical Telegram push every single run for
    any credential whose alert_hours_ahead exceeds its normal rotation window
    (regent_cookies/regent_cookies_oa: 48h threshold on a ~7h auto-refreshing
    cookie — perpetually "about to expire" by design, never actually a
    problem). That was the flood hitting the Commander's phone/laptop.
    Fix: alert once per (name, status) — same alert never repeats until it
    either clears (credential recovers) or changes to a new status. No ack
    needed; these are self-healing, no Commander action required.
    """
    client_alerts = results["client_affecting_alerts"]

    dedup_state = {}
    if ALERT_DEDUP.exists():
        try:
            dedup_state = json.loads(ALERT_DEDUP.read_text())
        except Exception:
            dedup_state = {}

    new_alerts = [a for a in client_alerts if f"{a['name']}|{a['status']}" not in dedup_state]

    if not new_alerts:
        return

    try:
        import sys
        sys.path.insert(0, str(THUNDERBIRD))
        # 2026-07-04: was importing send_telegram_message (does not exist) —
        # every alert crashed on import AND the dedup key was written BEFORE the
        # send, so a real alert was recorded "sent" then silently lost. Now:
        # correct send fn, and dedup keys are committed ONLY after a successful
        # send, so a crash lets the next run retry instead of swallowing it.
        from OpsCenter.hale_telegram_reporter import send_to_commander

        lines = ["🔴 CREDENTIAL ALERT — Client-affecting credentials expired/expiring\n"]
        for a in new_alerts:
            lines.append(f"⛔ {a['name']}: {a['status']}")
            lines.append(f"   {a['reason']}")
            lines.append(f"   Fix: {a['reauth_cmd']}\n")

        sent = send_to_commander("\n".join(lines), message_type="alert", urgent=True)
        if not sent:
            log.warning("Telegram send returned False — not deduped, will retry next run")
            return
        for a in new_alerts:
            dedup_state[f"{a['name']}|{a['status']}"] = datetime.now(MT).isoformat()
        ALERT_DEDUP.write_text(json.dumps(dedup_state, indent=2))
        log.info(f"D2MC2C alert sent for {len(new_alerts)} NEW client-affecting credential alert(s)")
    except Exception as e:
        log.warning(f"Telegram alert failed (not deduped — will retry next run): {e}")


def print_summary(results: dict):
    """Print human-readable summary."""
    print(f"\n{'='*60}")
    print(f"CREDENTIALS HEALTH CHECK — {results['checked_at']}")
    print(f"{'='*60}")

    for name, r in results["credentials"].items():
        icon = "✅" if r["status"] == "valid" else "🔴" if r["client_affecting"] else "🟡"
        print(f"{icon} {name:30s} {r['status']:12s} {r['reason'][:50]}")

    print(f"\nTotal alerts: {results['alert_count']}")
    if results["client_affecting_alerts"]:
        print(f"Client-affecting: {len(results['client_affecting_alerts'])} — D2MC2C ALERTED")
    print("="*60)


# ── Entry point ────────────────────────────────────────────────────────────────

def _prune_dedup(results: dict):
    """Clear dedup entries for anything no longer alerting, unconditionally,
    every run — not just when send_telegram_alerts fires.

    Fixed 2026-07-04 (flagged by fix-telegram-noise-batch2 during the same
    session's portal_live_probe.py fix): the prune used to live inside
    send_telegram_alerts(), which only runs when client_affecting_alerts is
    non-empty. If ALL credentials recovered at once, the function never ran,
    stale dedup keys lingered, and a later re-failure with the same
    name+status would be wrongly suppressed as "already sent."
    """
    if not ALERT_DEDUP.exists():
        return
    try:
        dedup_state = json.loads(ALERT_DEDUP.read_text())
    except Exception:
        return
    active_names = {a["name"] for a in results["client_affecting_alerts"]}
    pruned = {k: v for k, v in dedup_state.items() if k.split("|", 1)[0] in active_names}
    if pruned != dedup_state:
        ALERT_DEDUP.write_text(json.dumps(pruned, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Credentials health check")
    parser.add_argument("--quiet", action="store_true", help="Suppress Telegram alerts")
    parser.add_argument("--json", action="store_true", dest="json_out", help="JSON output only")
    args = parser.parse_args()

    results = run_check()
    save_state(results)
    _prune_dedup(results)

    if args.json_out:
        print(json.dumps(results, indent=2))
        return 0

    print_summary(results)

    if not args.quiet and results["client_affecting_alerts"]:
        send_telegram_alerts(results)

    return 1 if results["client_affecting_alerts"] else 0


if __name__ == "__main__":
    sys.exit(main())
