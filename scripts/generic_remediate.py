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
    ok, out = _run(["systemctl", "--user", "is-active", unit])
    return out.strip() == "active"


def _escalate(unit: str, reason: str) -> None:
    try:
        from core.notify.hale_notify import notify_sterling
        notify_sterling(f"generic-remediate:{unit}", reason)
    except Exception as e:
        logger.error("escalation notify failed for %s: %s", unit, e)


def _log_remediation_plan(unit: str, recovered: bool, note: str) -> None:
    """Ledger-only Hale Orchestrator entry — records the verified outcome,
    never gates the remediation decision above (already made by this point)."""
    try:
        from core.ops.hale_orchestrator import open_plan, assess_plan, close_plan
        plan = open_plan(
            task_summary=f"generic long-tail remediation: {unit} -> {note}",
            tier="trivial",
            criteria=[f"{unit} verified active after remediation attempt"],
        )
        status = "met" if recovered else "missed"
        result = assess_plan(plan, {plan.criteria[0]: status}, notes=note)
        close_plan(result)
    except Exception as e:
        logger.error("orchestrator logging failed for %s: %s", unit, e)


def remediate(unit: str) -> int:
    """Returns 0 on verified recovery, 1 otherwise (mirrors a systemd
    oneshot exit-code convention; nothing currently consumes this exit code,
    it's for manual/test invocation clarity)."""
    if not unit:
        logger.error("no unit argument provided")
        return 1

    state = _load_state()

    if _cooldown_blocking(state, unit):
        note = f"cooldown active ({COOLDOWN_SECONDS}s) — not re-attempting"
        logger.warning("%s: %s", unit, note)
        _escalate(unit, f"{unit} failed again within cooldown window — needs manual attention")
        _log_remediation_plan(unit, False, note)
        return 1

    logger.info("%s: attempting generic remediation (reset-failed + start)", unit)
    _run(["systemctl", "--user", "reset-failed", unit])
    start_ok, start_detail = _run(["systemctl", "--user", "start", unit])

    time.sleep(SETTLE_SECONDS)
    recovered = _is_active(unit)  # independent re-check — never trust start_ok alone

    state[unit] = {"last_attempt": datetime.now(timezone.utc).isoformat(), "recovered": recovered}
    _save_state(state)

    note = "recovered — verified active" if recovered else f"start attempted (ok={start_ok}) but not verified active"
    logger.info("%s: %s", unit, note)
    _log_remediation_plan(unit, recovered, note)

    if not recovered:
        _escalate(unit, f"{unit} entered failed state; generic remediation attempted but "
                        f"unit is NOT verified active afterward — needs manual attention")
        return 1
    return 0


def main() -> None:
    unit = sys.argv[1] if len(sys.argv) > 1 else ""
    sys.exit(remediate(unit))


if __name__ == "__main__":
    main()
