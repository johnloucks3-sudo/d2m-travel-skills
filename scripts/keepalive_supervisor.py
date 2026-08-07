#!/usr/bin/env python3
"""
keepalive_supervisor.py — Meta-watchdog for ALL Thunderbird Wing keepalives.
MISSION-211 (Commander P0 MUST, 2026-06-11). Sterling (A7).

PROBLEM
  The wing's credential/session keepalives choke silently — Centrav session
  lapses, the fare-watch auth-errors (kuklinski-flights-ric-pty), timers go
  stale and nobody notices. There was no supervisor over the supervisors.

WHAT THIS IS
  A fast, LLM-free, ops-only meta-watchdog that checks every keepalive in
  ISOLATION and NEVER chokes. It SUPERVISES the keepalives — it does not run
  them. Heavyweight actions (browser logins, OAuth refreshes) stay in their
  own timers; this script reads their state and self-heals only what is safe.

THE LOAD-BEARING PROPERTY: NEVER CHOKE
  - Every per-item check runs inside its own try/except.
  - Every external call (systemctl, optional service start) has a hard
    subprocess timeout. A timeout is recorded as UNKNOWN — never a hang.
  - NO browser is launched here. Centrav health is DERIVED from state files
    (fare_watches/last_check.json + centrav_session.json mtime), because
    launching Firefox in the check loop is exactly how a watchdog hangs.
  - One failing credential cannot block the others. Total runtime is bounded
    to a few seconds.

SELF-HEAL (conservative)
  - A timer that is EXPECTED-ACTIVE but found dead/inactive -> restart it
    (systemctl --user restart <unit>.timer). Idempotent.
  - A credential whose backing keepalive is auto-renewable and looks stale ->
    optionally kick its .service once (bounded). Off by default unless --heal-services.
  - Centrav -> NEVER auto-healed (reCAPTCHA + email-OTP, a human gate).
    Escalate with the EXACT, verified re-auth command instead.
  - Staged / not-installed units (d2m-centrav-warm, M-200 pending) are NEVER
    started or enabled. They are reported as NOT_INSTALLED / staged.

ESCALATE, NEVER SILENT-FAIL
  Credentials that need human re-auth get a clear alert written into the health
  state file (and a dedicated escalations list) with the exact command to run.
  The morning brief / Telegram read OpsCenter/keepalive_health.json.

HEALTH STATE
  Writes a GREEN/YELLOW/RED-per-item summary to OpsCenter/keepalive_health.json
  (atomic write). Overall status is the worst per-item status.

RAILS
  - No external sends. No git. No model calls. Does not touch the 6 protected
    email/relay files. Does not touch mission_board.json.

Exit codes:
  0  overall GREEN or YELLOW (informational)
  1  overall RED (something needs attention / escalation written)
  (The script itself never raises out — RED is a result, not a crash.)

Usage:
  .venv/bin/python scripts/keepalive_supervisor.py            # check + self-heal timers
  .venv/bin/python scripts/keepalive_supervisor.py --dry-run  # check only, no heal, no write-heal
  .venv/bin/python scripts/keepalive_supervisor.py --no-heal  # check + write health, never heal
  .venv/bin/python scripts/keepalive_supervisor.py --heal-services  # also kick stale auto-renew services
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
HEALTH_FILE = ROOT / "OpsCenter" / "keepalive_health.json"
FARE_WATCH_STATE = ROOT / "OpsCenter" / "fare_watches" / "last_check.json"
CENTRAV_SESSION = ROOT / "core" / "travel" / "data" / "centrav_session.json"
CENTRAV_PROFILE = ROOT / "core" / "travel" / "data" / "centrav_ff_profile"

# Hard per-call timeout for any subprocess (systemctl, service kick). Bounded.
SYSTEMCTL_TIMEOUT_S = 8
SERVICE_KICK_TIMEOUT_S = 25  # only used with --heal-services; bounded regardless

GREEN, YELLOW, RED, UNKNOWN = "GREEN", "YELLOW", "RED", "UNKNOWN"
_SEVERITY = {GREEN: 0, YELLOW: 1, UNKNOWN: 2, RED: 3}


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ---------------------------------------------------------------------------
# Registry — grounded in `systemctl --user list-timers` + the actual unit files
# inspected 2026-06-11. expected_state drives whether self-heal is allowed.
# ---------------------------------------------------------------------------
@dataclass
class Item:
    name: str                     # logical name
    kind: str                     # "timer" | "credential-cookie"
    unit: str | None = None       # systemd --user timer unit (with .timer)
    service: str | None = None    # backing .service (for optional kick)
    expected_state: str = "active"  # "active" | "staged" | "not_installed"
    interval_min: int | None = None  # expected run cadence; for staleness flag
    cred_file: Path | None = None    # backing credential/cookie file to stat
    cred_max_age_min: int | None = None  # flag YELLOW if file older than this
    # If set, read this JSON path (dot-notation) for a unix expiry instead of mtime.
    # Supports "_ms" suffix for millisecond epochs. Token-expiry beats file-age.
    expiry_json_path: str | None = None
    expiry_unit: str = "s"  # "s" | "ms"
    expiry_warn_min: int = 15  # YELLOW if token expires within this many minutes
    auto_renewable: bool = True   # can a .service kick refresh it? (False = human gate)
    reauth_cmd: str | None = None # EXACT human re-auth command if it needs one
    note: str = ""


REGISTRY: list[Item] = [
    Item(
        name="claude-oauth-keepalive", kind="timer",
        unit="claude-oauth-keepalive.timer", service="claude-oauth-keepalive.service",
        expected_state="active", interval_min=90,
        cred_file=Path.home() / ".claude" / ".credentials.json",
        expiry_json_path="claudeAiOauth.expiresAt", expiry_unit="ms", expiry_warn_min=10,
        auto_renewable=True,
        note="Claude MAX OAuth — auto-refresh. Freshness judged by token expiresAt, "
             "not file mtime (keepalive only rewrites the file on actual refresh).",
    ),
    Item(
        name="tess-token-keepalive", kind="timer",
        unit="tess-token-keepalive.timer", service="tess-token-keepalive.service",
        expected_state="active", interval_min=90,
        auto_renewable=True,
        reauth_cmd="python3 thunderbird_tess.py --authorize",
        note="TESS CRM token — auto-refresh; human re-auth if refresh token dead.",
    ),
    Item(
        name="johnloucks3-oauth-keepalive", kind="timer",
        unit="johnloucks3-oauth-keepalive.timer", service="johnloucks3-oauth-keepalive.service",
        expected_state="active", interval_min=90,
        auto_renewable=True, note="johnloucks3 MCP Gmail OAuth refresh.",
    ),
    Item(
        name="d2mconcierge-oauth-keepalive", kind="timer",
        unit="d2mconcierge-oauth-keepalive.timer", service="d2mconcierge-oauth-keepalive.service",
        expected_state="active", interval_min=45,
        cred_file=ROOT / "config" / "persona_gmail_token.json", cred_max_age_min=90,
        auto_renewable=True, note="d2mconcierge MCP Gmail OAuth refresh.",
    ),
    Item(
        name="d2m-ita-fare-watch", kind="timer",
        unit="d2m-ita-fare-watch.timer", service="d2m-ita-fare-watch.service",
        expected_state="active", interval_min=1440,  # daily 05:30
        auto_renewable=True, note="ITA login-free daily fare poll (MISSION-206).",
    ),
    # --- Credential/cookie items NOT backed by a self-healable auto-renew ---
    # RETIRED 2026-07-16 (Commander order): all site-session keepalives shut
    # down — Centrav warm, portal-keepalive, perx, silversea, live-probe.
    # Air-fare data continues via login-free polls (d2m-ita-fare-watch).
]


# ---------------------------------------------------------------------------
# Bounded systemd reads — every call has a hard timeout; timeout => UNKNOWN.
# ---------------------------------------------------------------------------
def _systemctl_show(unit: str) -> dict | None:
    """Return parsed properties for a --user unit, or None on any failure/timeout."""
    try:
        r = subprocess.run(
            ["systemctl", "--user", "show", unit,
             "-p", "ActiveState,SubState,LastTriggerUSec,NextElapseUSecRealtime,"
                   "Result,UnitFileState,LoadState"],
            capture_output=True, text=True, timeout=SYSTEMCTL_TIMEOUT_S,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        return None
    props: dict[str, str] = {}
    for line in (r.stdout or "").splitlines():
        if "=" in line:
            k, _, v = line.partition("=")
            props[k] = v
    return props or None


def _usec_to_dt(usec_str: str | None) -> datetime | None:
    """Parse systemd LastTriggerUSec.

    `systemctl show` renders this as a human timestamp, e.g.
    'Thu 2026-06-11 16:57:03 MDT' (NOT raw microseconds). Empty string means
    'never triggered'. We parse the timestamp form; raw-usec is a fallback.
    """
    if not usec_str or not usec_str.strip():
        return None
    s = usec_str.strip()
    # Fallback: raw microseconds-since-epoch (older systemd / scripted output).
    if s.isdigit():
        usec = int(s)
        return datetime.fromtimestamp(usec / 1_000_000, tz=timezone.utc) if usec > 0 else None
    # Human form: 'Thu 2026-06-11 16:57:03 MDT'. Drop weekday + tz abbrev, parse,
    # then attach the local tz offset (tz abbrevs aren't reliably parseable).
    try:
        parts = s.split()
        if len(parts) >= 3:
            date_part, time_part = parts[1], parts[2]
            naive = datetime.strptime(f"{date_part} {time_part}", "%Y-%m-%d %H:%M:%S")
            # Interpret as local wall-clock, convert to aware UTC.
            local = naive.astimezone()
            return local.astimezone(timezone.utc)
    except Exception:
        return None
    return None


def _file_age_min(p: Path | None) -> float | None:
    try:
        if p is None or not p.exists():
            return None
        return (time.time() - p.stat().st_mtime) / 60.0
    except Exception:
        return None


def _token_expiry_min(item: "Item") -> float | None:
    """Minutes until token expiry from a JSON field (dot-notation), or None.

    Negative => already expired. None => could not read (caller falls back to mtime).
    """
    if not (item.cred_file and item.expiry_json_path):
        return None
    try:
        data = json.loads(item.cred_file.read_text())
        for key in item.expiry_json_path.split("."):
            data = data[key]
        val = float(data)
        if item.expiry_unit == "ms":
            val /= 1000.0
        return (val - time.time()) / 60.0
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Per-item evaluation. Each call is fully isolated by the caller's try/except.
# ---------------------------------------------------------------------------
@dataclass
class Result:
    name: str
    status: str = UNKNOWN
    detail: str = ""
    expected_state: str = "active"
    timer_active: bool | None = None
    last_run_utc: str | None = None
    age_since_run_min: float | None = None
    interval_min: int | None = None
    cred_age_min: float | None = None
    token_expires_in_min: float | None = None
    healed: list[str] = field(default_factory=list)
    escalation: dict | None = None


def _centrav_health(item: Item) -> Result:
    """Derive Centrav health WITHOUT launching a browser.

    Authoritative down-signal: the fare-watch already records an auth_error for
    kuklinski-flights-ric-pty when the Centrav session is dead. Combine that with
    the session.json mtime. No Playwright here.
    """
    res = Result(name=item.name, expected_state=item.expected_state,
                 interval_min=item.interval_min)
    age = _file_age_min(item.cred_file)
    res.cred_age_min = round(age, 1) if age is not None else None

    # Guard: if the fare-watch state file itself is stale (its own timer may have
    # died), do NOT trust its verdict — a stale snapshot gives a false GREEN/RED.
    # The fare-watch runs daily; flag if the snapshot is >36h old.
    fw_age = _file_age_min(FARE_WATCH_STATE)
    fw_stale = fw_age is not None and fw_age > 36 * 60

    auth_error = False
    fw_detail = ""
    try:
        if FARE_WATCH_STATE.exists() and not fw_stale:
            fw = json.loads(FARE_WATCH_STATE.read_text())
            results = fw.get("results", {}) or {}
            for wid, r in results.items():
                if isinstance(r, dict) and r.get("status") == "auth_error":
                    auth_error = True
                    fw_detail = f"fare-watch '{wid}': {r.get('error', 'auth_error')[:120]}"
                    break
            if not auth_error:
                for w in fw.get("warnings", []) or []:
                    if "centrav" in str(w).lower() and "auth" in str(w).lower():
                        auth_error = True
                        fw_detail = str(w)[:160]
                        break
    except Exception as e:
        fw_detail = f"(could not read fare-watch state: {e})"

    if auth_error:
        res.status = RED
        res.detail = f"Centrav session DEAD — {fw_detail}"
        res.escalation = {
            "credential": "centrav-session",
            "reason": "Centrav session expired; auto-login impossible (reCAPTCHA + email-OTP).",
            "action_required": "HUMAN re-auth",
            "command": item.reauth_cmd,
        }
        return res

    # Fare-watch snapshot is stale (its own timer may be dead) — can't trust the
    # auth signal either way. Report UNKNOWN rather than a false GREEN/RED.
    if fw_stale:
        res.status = UNKNOWN
        res.detail = (f"Fare-watch snapshot is {fw_age/60:.0f}h old (>36h) — cannot "
                      f"confirm Centrav auth from a stale source. Check d2m-ita-fare-watch timer.")
        sess = (f"session file {age:.0f}min old" if age is not None else "no session file")
        res.detail += f" ({sess})"
        return res

    # No auth error recorded. Judge by session file freshness.
    if age is None:
        res.status = YELLOW
        res.detail = "No centrav_session.json present — never logged in, or session cleared."
        res.escalation = {
            "credential": "centrav-session",
            "reason": "No Centrav session file found.",
            "action_required": "HUMAN re-auth (first login)",
            "command": item.reauth_cmd,
        }
    elif item.cred_max_age_min and age > item.cred_max_age_min:
        res.status = YELLOW
        res.detail = (f"Centrav session file is {age:.0f}min old (TTL ~{item.cred_max_age_min}min) "
                      f"but no auth_error yet — warm-ping timer would refresh it (M-200 staged).")
    else:
        res.status = GREEN
        res.detail = f"Centrav session fresh ({age:.0f}min old), no fare-watch auth errors."
    return res


def _timer_health(item: Item, heal: bool, heal_services: bool) -> Result:
    res = Result(name=item.name, expected_state=item.expected_state,
                 interval_min=item.interval_min)

    props = _systemctl_show(item.unit) if item.unit else None

    # Not-installed / staged units: report, never heal.
    load_state = (props or {}).get("LoadState", "")
    unit_file_state = (props or {}).get("UnitFileState", "")
    if item.expected_state == "not_installed" or load_state == "not-found":
        res.status = GREEN if item.expected_state == "not_installed" else YELLOW
        res.detail = (f"Unit not installed (staged/pending — {item.note}). "
                      f"Not started, not enabled (by design).")
        return res
    if props is None:
        res.status = UNKNOWN
        res.detail = "systemctl read failed or timed out — cannot determine timer state."
        return res

    active = props.get("ActiveState", "") == "active"
    res.timer_active = active
    last_dt = _usec_to_dt(props.get("LastTriggerUSec"))
    if last_dt:
        res.last_run_utc = last_dt.isoformat()
        age = (now_utc() - last_dt).total_seconds() / 60.0
        res.age_since_run_min = round(age, 1)

    # Credential freshness (independent signal, if configured).
    # Prefer in-token expiry over file mtime when an expiry path is set, because
    # some keepalives only rewrite the file on an ACTUAL refresh (mtime lies).
    cred_age = _file_age_min(item.cred_file)
    res.cred_age_min = round(cred_age, 1) if cred_age is not None else None
    expiry_min = _token_expiry_min(item)
    if expiry_min is not None:
        res.token_expires_in_min = round(expiry_min, 1)

    # ---- Decide status + self-heal ----
    if not active:
        res.status = RED
        res.detail = f"Timer INACTIVE ({props.get('ActiveState','?')}/{props.get('SubState','?')})."
        if heal and item.unit:
            ok = _restart_timer(item.unit)
            res.healed.append(f"restart {item.unit}: {'OK' if ok else 'FAILED'}")
            if ok:
                # Re-read to confirm.
                p2 = _systemctl_show(item.unit)
                if p2 and p2.get("ActiveState") == "active":
                    res.status = YELLOW
                    res.detail += " Restarted — now active (verify next cycle)."
                    res.timer_active = True
        if res.status == RED and not res.escalation and item.reauth_cmd and not item.auto_renewable:
            res.escalation = {
                "credential": item.name, "reason": res.detail,
                "action_required": "HUMAN re-auth", "command": item.reauth_cmd,
            }
        return res

    # Timer is active. Check staleness vs expected interval (grace = 2x interval).
    stale = False
    if item.interval_min and res.age_since_run_min is not None:
        grace = item.interval_min * 2 + 10
        stale = res.age_since_run_min > grace
    # Credential staleness: token-expiry path wins when present, else file-age.
    if expiry_min is not None:
        cred_stale = expiry_min < item.expiry_warn_min
        cred_stale_detail = (f"token expires in {expiry_min:.0f}min "
                             f"(warn <{item.expiry_warn_min}min)")
    else:
        cred_stale = bool(item.cred_max_age_min and cred_age is not None
                          and cred_age > item.cred_max_age_min)
        cred_stale_detail = (f"credential file is {cred_age:.0f}min old "
                             f"(expected <{item.cred_max_age_min}min)"
                             if cred_age is not None else "credential file absent")

    if stale:
        res.status = YELLOW
        res.detail = (f"Timer active but last run {res.age_since_run_min:.0f}min ago "
                      f"(expected ~{item.interval_min}min). Possibly missed cycles.")
        if heal_services and item.service:
            ok = _kick_service(item.service)
            res.healed.append(f"kick {item.service}: {'OK' if ok else 'FAILED'}")
    elif cred_stale:
        res.status = YELLOW
        res.detail = (f"Timer healthy but {cred_stale_detail}. May need a refresh kick.")
        if heal_services and item.service:
            ok = _kick_service(item.service)
            res.healed.append(f"kick {item.service}: {'OK' if ok else 'FAILED'}")
    elif res.age_since_run_min is None and item.interval_min:
        # Active but NEVER triggered (LastTriggerUSec empty). A daily timer that
        # never fires would otherwise pass forever — UNKNOWN is more honest than GREEN.
        res.status = UNKNOWN
        res.detail = ("Timer active but has NEVER triggered (no last-run timestamp). "
                      "Likely only ran on-demand, or boot-delay not yet elapsed — "
                      "verify it fires on its next scheduled cycle.")
    else:
        res.status = GREEN
        run_str = f"{res.age_since_run_min:.0f}min ago" if res.age_since_run_min is not None else "n/a"
        exp = (f"; token ~{expiry_min:.0f}min to expiry" if expiry_min is not None else "")
        res.detail = (f"Timer active; last run {run_str}; "
                      f"result={props.get('Result','ok')}{exp}.")
    return res


def _restart_timer(unit: str) -> bool:
    try:
        r = subprocess.run(
            ["systemctl", "--user", "restart", unit],
            capture_output=True, text=True, timeout=SYSTEMCTL_TIMEOUT_S,
        )
        return r.returncode == 0
    except (subprocess.TimeoutExpired, Exception):
        return False


def _kick_service(service: str) -> bool:
    """Bounded one-shot service start. Used only under --heal-services."""
    try:
        r = subprocess.run(
            ["systemctl", "--user", "start", service],
            capture_output=True, text=True, timeout=SERVICE_KICK_TIMEOUT_S,
        )
        return r.returncode == 0
    except (subprocess.TimeoutExpired, Exception):
        return False


def evaluate(item: Item, heal: bool, heal_services: bool) -> Result:
    """Fully isolated per-item evaluation — never raises out."""
    try:
        if item.name == "centrav-session":
            return _centrav_health(item)
        if item.kind == "timer":
            return _timer_health(item, heal, heal_services)
        # Generic credential-cookie (none currently besides centrav).
        res = Result(name=item.name, expected_state=item.expected_state)
        age = _file_age_min(item.cred_file)
        res.cred_age_min = round(age, 1) if age is not None else None
        if age is None:
            res.status = YELLOW
            res.detail = "Credential file absent."
        elif item.cred_max_age_min and age > item.cred_max_age_min:
            res.status = YELLOW
            res.detail = f"Credential file {age:.0f}min old (>{item.cred_max_age_min})."
        else:
            res.status = GREEN
            res.detail = f"Credential fresh ({age:.0f}min old)."
        return res
    except Exception as e:
        # NEVER CHOKE: one item's exception is contained as UNKNOWN.
        return Result(name=item.name, status=UNKNOWN,
                      detail=f"check raised, contained: {e}",
                      expected_state=item.expected_state)


def _atomic_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2))
    tmp.replace(path)


def main() -> int:
    ap = argparse.ArgumentParser(description="Keepalive meta-watchdog (MISSION-211)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Check only — no heal, no health-file write.")
    ap.add_argument("--no-heal", action="store_true",
                    help="Check + write health, but never restart/kick anything.")
    ap.add_argument("--heal-services", action="store_true",
                    help="Also kick stale auto-renewable services (bounded). Default off.")
    args = ap.parse_args()

    heal = not (args.dry_run or args.no_heal)
    heal_services = args.heal_services and heal

    t0 = time.time()
    log(f"keepalive_supervisor start  (heal={heal}, heal_services={heal_services}, "
        f"dry_run={args.dry_run})")

    results: list[Result] = []
    for item in REGISTRY:
        r = evaluate(item, heal, heal_services)
        results.append(r)
        flag = {GREEN: "🟢", YELLOW: "🟡", RED: "🔴", UNKNOWN: "⚪"}[r.status]
        log(f"  {flag} {r.name:<28} {r.status:<7} {r.detail}")
        for h in r.healed:
            log(f"       ↳ heal: {h}")
        if r.escalation:
            log(f"       ↳ ESCALATE: {r.escalation['command']}")

    overall = GREEN
    for r in results:
        if _SEVERITY[r.status] > _SEVERITY[overall]:
            overall = r.status

    escalations = [r.escalation for r in results if r.escalation]
    elapsed = round(time.time() - t0, 2)

    payload = {
        "generated_utc": now_utc().isoformat(),
        "generated_mt": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z"),
        "overall_status": overall,
        "elapsed_seconds": elapsed,
        "heal_enabled": heal,
        "heal_services_enabled": heal_services,
        "counts": {
            "GREEN": sum(1 for r in results if r.status == GREEN),
            "YELLOW": sum(1 for r in results if r.status == YELLOW),
            "RED": sum(1 for r in results if r.status == RED),
            "UNKNOWN": sum(1 for r in results if r.status == UNKNOWN),
        },
        "items": [asdict(r) for r in results],
        "escalations": escalations,
        "_note": ("Brief/Telegram read overall_status + escalations. Centrav re-auth is a "
                  "human gate (reCAPTCHA/OTP) — never auto-healed; the command is exact."),
    }

    log(f"OVERALL: {overall}  ({payload['counts']})  in {elapsed}s")
    if escalations:
        log(f"ESCALATIONS PENDING: {len(escalations)} — see {HEALTH_FILE}")
        for e in escalations:
            log(f"   • {e['credential']}: {e['command']}")

    if not args.dry_run:
        try:
            _atomic_write(HEALTH_FILE, payload)
            log(f"health written → {HEALTH_FILE}")
        except Exception as e:
            log(f"WARN — could not write health file (non-fatal): {e}")

    # Deadman heartbeat — supervisor alive marker (RT-KEEPALIVES deadman local)
    try:
        subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1] / "scripts" / "deadman_ping.py"),
                        "keepalive-supervisor"], timeout=20,
                       capture_output=True)
    except Exception:
        pass

    return 1 if overall == RED else 0


if __name__ == "__main__":
    sys.exit(main())
