#!/usr/bin/env python3
"""
scripts/generic_remediate.py — generic long-tail auto-remediation, fired by
systemd's own OnFailure= directive on ANY --user unit, curated or not.
Dreams2Memories Travel, LLC · Thunderbird Wing · built 2026-07-09

WHY THIS EXISTS (external research, ELON + Whetstone converged 2026-07-09):
  Lane 1 (core/ci/repairs/schema.py) only repairs the 53 skills registered in
  config/ci_registry.json. Lane 2 (crash_reporter.py, restart_flap_detector.py)
  detects failures fleet-wide but never remediates, and restart_flap_detector's
  24h/7d journalctl scan is a BATCH signal — a fast crash-loop that exhausts
  systemd's own StartLimitBurst can go unremediated for hours before the next
  scan even notices. systemd's OnFailure= is a REAL-TIME, per-unit, zero-config
  signal that already exists on every unit this fleet runs — this script is
  the dispatch target for that signal, closing the long-tail gap without a new
  daemon, new backend, or new dependency (see docs/superpowers/specs/
  2026-07-09-self-healing-architecture-reverse-engineered.md, adoption note).

WHAT IT DOES (bounded, single retry, then escalate — no framework, no rules
engine, matches Whetstone's complexity-for-its-own-sake guardrail):
  1. Durable per-unit cooldown (JSON state file) — at most ONE remediation
     attempt per unit per COOLDOWN_SECONDS, so a persistently-broken unit
     does not retry-storm.
  2. `systemctl --user reset-failed <unit>` + `systemctl --user start <unit>`.
  3. Settle, then verify via `systemctl --user is-active <unit>` — independent
     re-check, never trust the start command's own exit code alone.
  4. Open/assess/close a Hale Orchestrator Plan recording the attempt +
     verified outcome — this is the ledger-only integration; the remediation
     decision itself is made entirely above, orchestrator only records it.
  5. If cooldown blocks, or the verified re-check is not active: escalate to
     Sterling (existing notify_sterling channel) — never silently give up.

Wired via a systemd template unit (thunderbird-generic-remediate@.service,
%i = failed unit name) referenced from a GLOBAL drop-in
(~/.config/systemd/user/service.d/onfailure-remediate.conf) so every current
and future --user .service unit gets OnFailure= coverage with ZERO
per-service registration — this is the "zero-config, zero-new-deps" property
that made this the adopted candidate over Monit/Sensu/StackStorm/EDA.

USAGE (systemd calls this, but it's a normal CLI for manual testing):
  python3 scripts/generic_remediate.py <failed-unit-name>
"""
from __future__ import annotations

import json
import logging
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
STATE_FILE = ROOT / "logs" / "generic_remediate_state.json"
COOLDOWN_SECONDS = 3600  # at most one attempt per unit per hour
SETTLE_SECONDS = 5
# ADDED 2026-07-16 (hot-window triage): the cooldown throttles FREQUENCY but
# never capped TOTAL attempts -- a unit with a genuinely unfixable target
# (e.g. d2m-factbook-refresh.service, whose recipes/factbook_refresh.yaml
# simply didn't exist) retried once an hour for 7 straight days (~135
# attempts) with no escalation past the routine per-attempt Sterling notify.
# Once a unit crosses this many CONSECUTIVE failed remediation attempts,
# stop trying entirely and escalate once, distinctly, instead of retrying
# forever into the same wall.
MAX_CONSECUTIVE_FAILURES = 5

# Units already owned by Lane 1 (core/ci/repairs/cluster_*.py repair() bodies
# restart these directly, under their own tiered SAFE/CAUTION/DESTRUCTIVE gate
# + anti-flap state). This mechanism is for the LONG TAIL outside that set —
# firing on a Lane-1-owned unit too would let two independent remediation
# systems race the same unit (the exact conflict Whetstone flagged during the
# 2026-07-09 adoption review, see docs/superpowers/specs/
# 2026-07-09-self-healing-architecture-reverse-engineered.md addendum).
# Regenerate via:
#   grep -ohE "[a-zA-Z0-9_.-]+\.(service|timer)" config/ci_registry.json \
#     core/ci/repairs/cluster_*.py core/ci/ci_auto_repair_engine.py | sort -u
LANE1_OWNED_UNITS = frozenset({
    "claude-oauth-keepalive.timer", "cloudflared.service", "cruise-db-refresh.service",
    "d2mconcierge-oauth-keepalive.timer", "d2m-inbox-triage.timer", "d2m-litellm-gateway.service",
    "d2m-qdrant-reindex.timer", "docker.service", "johnloucks3-oauth-keepalive.timer",
    "n8n.service", "oauth-keepalive.timer", "opencode-spsa-monitor.service",
    "reverie-api.service", "reverie-frontend.service", "reverie.service", "tailscaled.service",
    "thunderbird-supertimer.service", "thunderbird-telegram-gw.service",
    "thunderbird-tunnel.service", "thunderbird-watchdog.timer", "ttyd.service",
    "ttyd-terminal.service",
})

# Units that intentionally exit 1 as their OWN alert signal (not a crash) and
# already do their own Telegram alerting with dedup (e.g. credentials_health_
# check.py's ALERT_DEDUP). Escalating these to Sterling on top of that is
# redundant noise, not a new finding -- found 2026-07-10 investigating a
# Telegram flood: hale-credential-check fired "failed again within cooldown
# window" ~20x/day for a genuine-but-already-tracked Regent cookie expiry
# (MISSION-820/1563, needs Commander manual portal re-auth) that a restart
# can never fix. Restarting these units is also pointless -- the "failure"
# is a data condition, not a process crash -- so they skip remediation
# entirely, same as Lane-1-owned units, but for a different reason.
SELF_ALERTING_UNITS = frozenset({
    "d2m-icelandair-warm.service",  # Session expiry (data condition); restart cannot fix; escalates separately to Sterling with manual re-login prompt
    "hale-credential-check.service",
    "d2m-factbook-refresh.service",  # OAuth token missing (structural), restart can't fix
    "drkonqi-coredump-pickup.service",  # KDE crash pickup; exits 1 because drkonqi-coredump-launcher@.service is intentionally masked (commit 0252479e0). Restart can't fix — structural.
})

logging.basicConfig(
    filename=ROOT / "logs" / "generic_remediate.log",
    level=logging.INFO,
    format="%(asctime)s [generic_remediate] %(message)s",
)
logger = logging.getLogger("generic_remediate")


def _load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            return {}
    return {}


def _save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def _cooldown_blocking(state: dict, unit: str) -> bool:
    last = state.get(unit, {}).get("last_attempt")
    if not last:
        return False
    try:
        last_dt = datetime.fromisoformat(last)
    except Exception:
        return False
    return (datetime.now(timezone.utc) - last_dt).total_seconds() < COOLDOWN_SECONDS


def _run(cmd: list[str], timeout: int = 20) -> tuple[bool, str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode == 0, (r.stdout or r.stderr).strip()
    except Exception as e:
        return False, str(e)


def _is_active(unit: str) -> bool:
    """FIXED 2026-07-10: a Type=oneshot unit (most of this fleet's timer-
    triggered services) goes to 'inactive' immediately after a SUCCESSFUL
    run unless RemainAfterExit=yes is set -- so 'is-active' always reported
    False for oneshot units regardless of real outcome, causing permanent
    false escalation to Sterling and 'recovered' never once being True for
    this unit type. Found via a real production incident (d2m-airfare-scan
    restart storm, see output/ci_remediation/fix_d2m-airfare-scan_service.md)
    while investigating why this fleet-wide mechanism kept escalating.
    'is-failed' negated is the correct check: a long-running unit that
    should be 'active' AND a oneshot unit that completed cleanly both
    report is-failed=False; only a genuine failure reports True."""
    ok, out = _run(["systemctl", "--user", "is-failed", unit])
    return out.strip() != "failed"


def _escalate(unit: str, reason: str) -> None:
    try:
        from core.notify.hale_notify import notify_sterling
        notify_sterling(f"generic-remediate:{unit}", reason)
    except Exception as e:
        logger.error("escalation notify failed for %s: %s", unit, e)


def _log_remediation_plan(unit: str, status: str, note: str) -> None:
    """Ledger-only Hale Orchestrator entry — records the verified outcome,
    never gates the remediation decision above (already made by this point).
    status is 'met' (verified active), 'missed' (attempted, not recovered),
    or 'unverified' (deferred to Lane 1 — nothing checked here by design)."""
    try:
        from core.ops.hale_orchestrator import open_plan, assess_plan, close_plan
        plan = open_plan(
            task_summary=f"generic long-tail remediation: {unit} -> {note}",
            tier="trivial",
            criteria=[f"{unit} verified active after remediation attempt"],
        )
        result = assess_plan(plan, {plan.criteria[0]: status}, notes=note)
        close_plan(result)
    except Exception as e:
        logger.error("orchestrator logging failed for %s: %s", unit, e)


def _is_self_alerting(unit: str) -> bool:
    """Same suffix-agnostic match as _is_lane1_owned -- systemd's %i strips
    .service/.timer, SELF_ALERTING_UNITS stores full names."""
    if unit in SELF_ALERTING_UNITS:
        return True
    for owned in SELF_ALERTING_UNITS:
        if owned.rsplit(".", 1)[0] == unit:
            return True
    return False


def _is_lane1_owned(unit: str) -> bool:
    """FIXED 2026-07-10: systemd's %i template specifier strips the type
    suffix (.service/.timer) from the instance name, but LANE1_OWNED_UNITS
    stores full names WITH suffixes. A bare 'in' check against argv silently
    never matched in real production dispatch (only in manual testing where
    the full name was typed by hand) — the exclusion guard was non-functional
    end-to-end despite passing its own unit tests (which called remediate()
    directly with a full suffixed name, never through the real %i path).
    Found via a live cascade of failed thunderbird-generic-remediate@ units."""
    if unit in LANE1_OWNED_UNITS:
        return True
    for owned in LANE1_OWNED_UNITS:
        if owned.rsplit(".", 1)[0] == unit:
            return True
    return False


def remediate(unit: str) -> int:
    """Returns 0 on verified recovery, 1 otherwise (mirrors a systemd
    oneshot exit-code convention; nothing currently consumes this exit code,
    it's for manual/test invocation clarity)."""
    if not unit:
        logger.error("no unit argument provided")
        return 1

    # Self-exclusion guard (added 2026-07-16): the fleet-wide onfailure-
    # remediate.conf drop-in applies to THIS template unit too. When we exit 1
    # on a non-recoverable target, systemd fires another instance of us whose
    # %i is "thunderbird-generic-remediate@<original-unit>". That second
    # instance restarts the first (which is now in cooldown, exits 1), and the
    # cycle repeats — the "10 errors/10min" cascade observed with tess-token-
    # keepalive. Returning 0 here breaks the loop without touching the
    # onfailure-remediate.conf drop-in itself.
    if unit.startswith("thunderbird-generic-remediate"):
        logger.info("%s: self-referential remediation guard — skipping", unit)
        return 0

    if _is_lane1_owned(unit):
        note = "deferred to Lane 1 (CI Repair Warehouse already owns this unit's remediation)"
        logger.info("%s: %s", unit, note)
        _log_remediation_plan(unit, "unverified", note)
        return 0

    if _is_self_alerting(unit):
        note = "self-alerting unit (own Telegram dedup) -- skipping redundant Sterling escalation"
        logger.info("%s: %s", unit, note)
        _log_remediation_plan(unit, "unverified", note)
        return 0

    state = _load_state()
    unit_state = state.get(unit, {})
    consecutive_failures = unit_state.get("consecutive_failures", 0)

    if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
        if not unit_state.get("circuit_broken_escalated"):
            _escalate(
                unit,
                f"{unit}: CIRCUIT BREAKER TRIPPED after {consecutive_failures} consecutive failed "
                f"remediation attempts — this is very likely an unfixable target (missing file, dead "
                f"config, etc.), not a transient fault. No further automatic attempts will be made. "
                f"Fix the underlying cause or retire the unit, then reset the counter."
            )
            unit_state["circuit_broken_escalated"] = True
            state[unit] = unit_state
            _save_state(state)
        note = f"circuit breaker open ({consecutive_failures} consecutive failures) — not re-attempting"
        logger.warning("%s: %s", unit, note)
        # Deliberate non-attempt, not a failed attempt — 'unverified' keeps the
        # ledger's FAIL count meaning "attempted and did not recover" (the real
        # FAIL was already logged when the actual attempt failed).
        # Return 0: exiting 1 here would mark THIS remediate unit failed, which
        # triggers the OnFailure drop-in again (self-referential chain caught by the
        # guard but still generates noise — root cause of the 42-error storm on
        # browser-bridge 2026-07-25).
        _log_remediation_plan(unit, "unverified", note)
        return 0

    if _cooldown_blocking(state, unit):
        note = f"cooldown active ({COOLDOWN_SECONDS}s) — not re-attempting"
        logger.warning("%s: %s", unit, note)
        _escalate(unit, f"{unit} failed again within cooldown window — needs manual attention")
        _log_remediation_plan(unit, "unverified", note)  # skip, not a failed attempt
        # Return 0: intentional non-retry is not a script failure; returning 1 here
        # causes systemd to fire OnFailure again on the remediate unit itself,
        # amplifying every cooldown-blocked trigger into a self-referential storm.
        return 0

    logger.info("%s: attempting generic remediation (reset-failed + start)", unit)
    _run(["systemctl", "--user", "reset-failed", unit])
    start_ok, start_detail = _run(["systemctl", "--user", "start", unit])

    time.sleep(SETTLE_SECONDS)
    recovered = _is_active(unit)  # independent re-check — never trust start_ok alone

    consecutive_failures = 0 if recovered else consecutive_failures + 1
    state[unit] = {
        "last_attempt": datetime.now(timezone.utc).isoformat(),
        "recovered": recovered,
        "consecutive_failures": consecutive_failures,
        "circuit_broken_escalated": False if recovered else unit_state.get("circuit_broken_escalated", False),
    }
    _save_state(state)

    note = "recovered — verified active" if recovered else f"start attempted (ok={start_ok}) but not verified active"
    logger.info("%s: %s", unit, note)
    _log_remediation_plan(unit, "met" if recovered else "missed", note)

    if not recovered:
        _escalate(unit, f"{unit} entered failed state; generic remediation attempted but "
                        f"unit is NOT verified active afterward — needs manual attention "
                        f"({consecutive_failures}/{MAX_CONSECUTIVE_FAILURES} consecutive failures)")
        return 1
    return 0


def main() -> None:
    unit = sys.argv[1] if len(sys.argv) > 1 else ""
    sys.exit(remediate(unit))


if __name__ == "__main__":
    main()
