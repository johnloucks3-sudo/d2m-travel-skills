#!/usr/bin/env python3
"""Portal Session Manager — consolidated status + audit trail across the 5 named
portal families (Regent Direct, Regent OA, Centrav, TESS, Outside Agents/magtap,
Silversea).

This is a thin layer, NOT a second prober. Session health for cookie-based
portals is derived from the same cookie files and the same
`cookie_expiry_status()` logic that `scripts/portal_keepalive.py` already uses
(auth-gate aware, beacon-cookie aware). TESS health is derived from
`tess_token.json`. Refresh is never performed in-process — it is delegated to
the existing, backoff-guarded entrypoints (`scripts/portal_keepalive.py`,
`scripts/tess_token_keepalive.py`) as bounded subprocesses, so the lockout
guards those scripts already carry (auth-gate verification, capped exponential
backoff) stay authoritative. Running a second independent login path on its
own schedule is exactly the double-login/lockout risk portal_keepalive's
backoff guard exists to prevent — this module does not do that.

Outputs:
  OpsCenter/portal_session_status.json  — real-time snapshot, one entry/portal
  OpsCenter/portal_session_log.jsonl    — append-only audit trail (login,
                                           refresh, timeout, error events)

Usage:
  python3 core/portals/session_manager.py --status              # snapshot only, no refresh
  python3 core/portals/session_manager.py --check                # snapshot + delegate refresh where due
  python3 core/portals/session_manager.py --check --portal tess  # one portal only
  python3 core/portals/session_manager.py --check --dry-run      # compute + log intent, no subprocess calls
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
sys.path.insert(0, str(ROOT / "scripts"))

import portal_keepalive as pk  # noqa: E402  (reuses PORTALS registry, cookie_expiry_status, backoff)

STATUS_FILE = ROOT / "OpsCenter" / "portal_session_status.json"
LOG_FILE = ROOT / "OpsCenter" / "portal_session_log.jsonl"
TESS_TOKEN_FILE = ROOT / "tess_token.json"

REFRESH_THRESHOLD_HOURS = 24.0  # rolling window per Phase 4 spec
SUBPROCESS_TIMEOUT_S = 240      # bounded — a hung browser login must not hang the manager

# The 5 named portal families -> underlying tracked session key(s).
# Regent is one portal with two accounts (Direct + OA), tracked as two sessions.
TRACKED = {
    "regent_direct": {"kind": "cookie", "pk_key": "regent_direct", "label": "Regent Direct"},
    "regent_oa": {"kind": "cookie", "pk_key": "regent_oa", "label": "Regent OA"},
    "centrav": {"kind": "cookie", "pk_key": "centrav", "label": "Centrav B2B"},
    "tess": {"kind": "tess", "pk_key": None, "label": "TESS CRM"},
    "oa": {"kind": "cookie", "pk_key": "magtap", "label": "Outside Agents (TAP/MAGCRM/Odysseus)"},
    "silversea": {"kind": "cookie", "pk_key": "silversea", "label": "Silversea agency portal"},
}

REFRESH_DUE_STATUSES = {"EXPIRED", "STALE", "SESSION_ONLY"}


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2))
    tmp.replace(path)


def log_event(event: str, portal: str, detail: str = "", extra: dict | None = None) -> None:
    """Append one structured event to the JSONL audit trail. Never raises."""
    rec = {
        "ts_utc": now_utc().isoformat(),
        "event": event,       # login | refresh | timeout | error | status
        "portal": portal,
        "detail": detail,
    }
    if extra:
        rec.update(extra)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a") as f:
            f.write(json.dumps(rec) + "\n")
    except Exception:
        pass  # audit-trail failure must never break the health check


def _cookie_status(pk_key: str) -> dict:
    portal = pk.PORTALS[pk_key]
    cookies = pk.load_cookies(portal["cookie_file"])
    status = pk.cookie_expiry_status(
        cookies,
        auth_cookie_names=portal.get("auth_cookie_names"),
        auth_domain=portal.get("auth_domain"),
    )
    status["source"] = str(portal["cookie_file"])
    return status


def _tess_status() -> dict:
    if not TESS_TOKEN_FILE.exists():
        return {"status": "SESSION_ONLY", "hours_left": None, "source": str(TESS_TOKEN_FILE),
                 "detail": "no tess_token.json on disk"}
    try:
        data = json.loads(TESS_TOKEN_FILE.read_text())
        expires_at = float(data.get("expires_at"))
    except Exception as e:
        return {"status": "SESSION_ONLY", "hours_left": None, "source": str(TESS_TOKEN_FILE),
                 "detail": f"could not read expires_at: {e}"}
    hours_left = (expires_at - time.time()) / 3600.0
    status = "EXPIRED" if hours_left < 0 else ("STALE" if hours_left < 1 else "OK")
    return {
        "status": status,
        "hours_left": round(hours_left, 1),
        "expires_at": datetime.fromtimestamp(expires_at, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "source": str(TESS_TOKEN_FILE),
    }


def get_status(name: str) -> dict:
    """Derive one portal's session status from existing on-disk state. Read-only."""
    cfg = TRACKED[name]
    if cfg["kind"] == "tess":
        result = _tess_status()
    else:
        result = _cookie_status(cfg["pk_key"])
    result["label"] = cfg["label"]
    return result


def _needs_refresh(status: dict) -> bool:
    if status.get("status") in REFRESH_DUE_STATUSES:
        return True
    hours_left = status.get("hours_left")
    return hours_left is not None and hours_left < REFRESH_THRESHOLD_HOURS


def _delegate_refresh(name: str, dry_run: bool) -> dict:
    """Invoke the existing, backoff-guarded refresh entrypoint as a bounded subprocess.

    Never opens a browser session directly — routes through portal_keepalive.py
    (cookie portals) or tess_token_keepalive.py (TESS) so their auth-gate check
    and exponential backoff stay in force. Returns a dict describing the outcome.
    """
    cfg = TRACKED[name]
    if cfg["kind"] == "tess":
        cmd = [sys.executable, str(ROOT / "scripts" / "tess_token_keepalive.py")]
    else:
        if pk.is_in_backoff(cfg["pk_key"]):
            log_event("refresh", name, "SKIP — portal_keepalive backoff window active; not attempting.")
            return {"attempted": False, "reason": "backoff"}
        cmd = [sys.executable, str(ROOT / "scripts" / "portal_keepalive.py"), "--portal", cfg["pk_key"]]

    if dry_run:
        log_event("refresh", name, f"DRY-RUN — would run: {' '.join(cmd)}")
        return {"attempted": False, "reason": "dry_run", "command": cmd}

    log_event("login", name, f"Delegating refresh: {' '.join(cmd)}")
    try:
        r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=SUBPROCESS_TIMEOUT_S)
        ok = r.returncode == 0
        log_event(
            "refresh" if ok else "error", name,
            f"delegated refresh returncode={r.returncode}",
            extra={"stderr_tail": (r.stderr or "")[-500:]},
        )
        return {"attempted": True, "returncode": r.returncode}
    except subprocess.TimeoutExpired:
        log_event("timeout", name, f"delegated refresh exceeded {SUBPROCESS_TIMEOUT_S}s bound")
        return {"attempted": True, "timed_out": True}
    except Exception as e:
        log_event("error", name, f"delegated refresh raised: {e}")
        return {"attempted": True, "error": str(e)}


def run(portals: list[str], do_refresh: bool, dry_run: bool) -> dict:
    snapshot = {}
    for name in portals:
        try:
            status = get_status(name)
        except Exception as e:
            status = {"status": "UNKNOWN", "hours_left": None, "detail": f"probe raised: {e}"}
        log_event("status", name, f"{status.get('status')} | {status.get('hours_left')}h left")

        refresh_result = None
        if do_refresh and _needs_refresh(status):
            refresh_result = _delegate_refresh(name, dry_run)
            if refresh_result.get("attempted"):
                # Re-derive status after a real refresh attempt so the snapshot reflects outcome.
                try:
                    status = get_status(name)
                except Exception:
                    pass

        snapshot[name] = {**status, "refresh_action": refresh_result}

    payload = {
        "generated_utc": now_utc().isoformat(),
        "generated_mt": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z"),
        "refresh_threshold_hours": REFRESH_THRESHOLD_HOURS,
        "portals": snapshot,
        "_note": "Derived from existing cookie/token state + portal_keepalive registry. "
                 "Refresh delegated to portal_keepalive.py / tess_token_keepalive.py — "
                 "this manager never opens its own browser session.",
    }
    _atomic_write_json(STATUS_FILE, payload)
    return payload


def main() -> int:
    global REFRESH_THRESHOLD_HOURS
    ap = argparse.ArgumentParser(description="Portal Session Manager (consolidated status + audit trail)")
    ap.add_argument("--status", action="store_true", help="Snapshot only — no refresh delegation.")
    ap.add_argument("--check", action="store_true", help="Snapshot + delegate refresh where due (default action).")
    ap.add_argument("--portal", choices=list(TRACKED.keys()), help="Scope to one tracked portal.")
    ap.add_argument("--dry-run", action="store_true", help="Compute + log intended refreshes, invoke nothing.")
    ap.add_argument("--refresh-threshold-hours", type=float, default=REFRESH_THRESHOLD_HOURS)
    args = ap.parse_args()

    REFRESH_THRESHOLD_HOURS = args.refresh_threshold_hours

    portals = [args.portal] if args.portal else list(TRACKED.keys())
    do_refresh = not args.status  # --check or bare invocation both refresh; --status never does

    payload = run(portals, do_refresh=do_refresh, dry_run=args.dry_run)

    for name, s in payload["portals"].items():
        flag = {"OK": "🟢", "GREEN": "🟢", "WARN": "🟡", "STALE": "🟠",
                "EXPIRED": "🔴", "SESSION_ONLY": "⚪", "UNKNOWN": "⚪"}.get(s.get("status"), "⚪")
        hrs = s.get("hours_left")
        print(f"  {flag} {TRACKED[name]['label']:<40} {s.get('status', '?'):<14} "
              f"{hrs if hrs is not None else '?'}h left")

    print(f"\nStatus written -> {STATUS_FILE}")
    print(f"Audit trail    -> {LOG_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
