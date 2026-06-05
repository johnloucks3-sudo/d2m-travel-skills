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
        "alert_hours_ahead": 48,
        "notes": "B2B flight pricing. Expired = no wholesale quotes. Needs OTP reauth.",
        "reauth_cmd": "python3 scripts/centrav_reauth.py",
    },
    "regent_cookies": {
        "file": CREDS_DIR / "regent_cookies.json",
        "type": "cookies",
        "client_affecting": True,
        "alert_hours_ahead": 48,
        "notes": "Regent portal (direct D2M account). Ely/Nichols/Furlow/McLeod bookings.",
        "reauth_cmd": "python3 scripts/rssc_session_keepalive.py",
        "timer": "d2m-rssc-session-keepalive.timer",
    },
    "regent_cookies_oa": {
        "file": CREDS_DIR / "regent_cookies_oa.json",
        "type": "cookies",
        "client_affecting": True,
        "alert_hours_ahead": 48,
        "notes": "Regent portal (OA account). Loucks + McLeod OA bookings.",
        "reauth_cmd": "python3 scripts/rssc_session_keepalive.py --oa-only",
        "timer": "d2m-rssc-session-keepalive.timer",
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
        "client_affecting": True,
        "alert_hours_ahead": 24,
        "notes": "Perx.com — Silversea agent rate access (Westbrook connection).",
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

def _check_cookies(cookie_file: Path) -> dict:
    """Check cookie file for expiry. Returns status dict."""
    now = time.time()

    try:
        data = json.loads(cookie_file.read_text())
    except Exception as e:
        return {"status": "error", "reason": f"Cannot read: {e}", "expires_in_hours": None}

    cookies = data if isinstance(data, list) else data.get("cookies", [])

    if not cookies:
        return {"status": "empty", "reason": "No cookies found", "expires_in_hours": None}

    # Find the earliest-expiring meaningful cookie
    min_expiry = None
    min_name = None
    session_only = True  # True if all cookies are session-only (no expiry)

    for c in cookies:
        exp = c.get("expires", c.get("expiry", -1))
        name = c.get("name", "?")

        if exp is None or exp <= 0:
            continue  # session cookie or no-expiry

        session_only = False

        # Skip obviously stale cookies (expiry in the distant past might be intentional)
        if exp < 0:
            continue

        if min_expiry is None or exp < min_expiry:
            min_expiry = exp
            min_name = name

    if min_expiry is None:
        if session_only:
            # Session cookies expire when browser closes — treat as likely expired
            return {
                "status": "session_only",
                "reason": "All cookies are session-only (no persistent expiry). Likely invalid.",
                "expires_in_hours": 0,
            }
        return {"status": "unknown", "reason": "No expiry timestamps found", "expires_in_hours": None}

    delta_hours = (min_expiry - now) / 3600

    if delta_hours < 0:
        return {
            "status": "expired",
            "reason": f"Expired {abs(delta_hours):.1f}h ago (cookie: {min_name})",
            "expires_in_hours": delta_hours,
        }
    else:
        return {
            "status": "valid",
            "reason": f"Expires in {delta_hours:.1f}h (cookie: {min_name})",
            "expires_in_hours": delta_hours,
        }


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
            result = _check_cookies(cfile)
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
    existing.append(entry)
    # Keep last 30 entries
    OVERNIGHT_LOG.write_text(json.dumps(existing[-30:], indent=2))


def send_telegram_alerts(results: dict):
    """Send D2MC2C alert for client-affecting credential failures."""
    client_alerts = results["client_affecting_alerts"]
    if not client_alerts:
        return

    try:
        import sys
        sys.path.insert(0, str(THUNDERBIRD))
        from OpsCenter.thunderbird_telegram_gw import send_telegram_message

        lines = ["🔴 CREDENTIAL ALERT — Client-affecting credentials expired/expiring\n"]
        for a in client_alerts:
            lines.append(f"⛔ {a['name']}: {a['status']}")
            lines.append(f"   {a['reason']}")
            lines.append(f"   Fix: {a['reauth_cmd']}\n")

        msg = "\n".join(lines)
        send_telegram_message(msg)
        log.info(f"D2MC2C alert sent for {len(client_alerts)} client-affecting credential(s)")
    except Exception as e:
        log.warning(f"Telegram alert failed: {e}")


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

def main():
    parser = argparse.ArgumentParser(description="Credentials health check")
    parser.add_argument("--quiet", action="store_true", help="Suppress Telegram alerts")
    parser.add_argument("--json", action="store_true", dest="json_out", help="JSON output only")
    args = parser.parse_args()

    results = run_check()
    save_state(results)

    if args.json_out:
        print(json.dumps(results, indent=2))
        return 0

    print_summary(results)

    if not args.quiet and results["client_affecting_alerts"]:
        send_telegram_alerts(results)

    return 1 if results["client_affecting_alerts"] else 0


if __name__ == "__main__":
    sys.exit(main())
