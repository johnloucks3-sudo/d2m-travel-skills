"""Self-Observability Sentinel — watch the SCREAMING, not the heartbeat.

The 10-hour blind spot (2026-06-20): 136 timers + health-checks + watchdogs, yet
3 services crash-looped ~78,000 errors with zero indicator — because every monitor
asked "is it active?" (liveness). A crash-looping service answers yes. This watches
restart-count + journal error-rate instead, and on breach DISPATCHES AN AUTONOMOUS
FIXER (headless Hale/Claude with CI authority) — it does NOT page the Commander.
Commander is told only when the fixer cannot fix it (sudo / spend / client-send).

Pure logic here is unit-tested; scan() + dispatch_remediation() are the integration.
"""
from __future__ import annotations
import json
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

STATE_PATH = Path("/home/john/Thunderbird/config/ci_sentinel_state.json")
DISPATCH_CLAUDE = "/home/john/Thunderbird/OpsCenter/dispatch_claude.py"
OUTPUT_DIR = Path("/home/john/Thunderbird/output/ci_remediation")

# Thresholds (a service breaching ANY of these is "screaming")
RESTART_THRESHOLD = 5          # restarts in the unit's lifetime counter delta
ERROR_THRESHOLD = 100          # journal error/warning lines in the window
ERROR_WINDOW_MIN = 10
DISPATCH_COOLDOWN_MIN = 30     # don't re-dispatch a fixer for the same unit within this


# ---------- pure, testable logic ----------

def classify(nrestarts: int, errors: int,
             restart_threshold: int = RESTART_THRESHOLD,
             error_threshold: int = ERROR_THRESHOLD) -> list[str]:
    """Return breach reasons; empty list = healthy."""
    reasons = []
    if nrestarts >= restart_threshold:
        reasons.append(f"{nrestarts} restarts (>= {restart_threshold})")
    if errors >= error_threshold:
        reasons.append(f"{errors} errors in {ERROR_WINDOW_MIN}min (>= {error_threshold})")
    return reasons


def should_dispatch(unit: str, state: dict, now: datetime,
                    cooldown_min: int = DISPATCH_COOLDOWN_MIN) -> bool:
    """True unless a fixer was dispatched for this unit within the cooldown."""
    last = state.get(unit, {}).get("last_dispatch")
    if not last:
        return True
    dt = datetime.fromisoformat(last)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (now - dt) >= timedelta(minutes=cooldown_min)


def is_escalation(agent_output: str) -> bool:
    """True if the alert agent reported it could NOT fix autonomously."""
    return "ESCALATE TO COMMANDER" in (agent_output or "").upper()


# ---------- multispectral sensor bands (ISR) ----------
# Each band reads ONE spectrum from a unit's reading dict and reports a breach.
# Fusion across bands is what single-band liveness monitoring missed for 10 hours.

def band_restarts(r: dict) -> tuple[bool, str]:
    # Use restarts SINCE last scan (delta), not cumulative NRestarts — a one-time
    # historical 50k must not perma-trigger. recent >= threshold = a live crash loop.
    n = r.get("restarts_recent", r.get("nrestarts", 0))
    return (n >= RESTART_THRESHOLD, f"{n} restarts since last scan (>= {RESTART_THRESHOLD})")


def band_error_rate(r: dict) -> tuple[bool, str]:
    e = r.get("errors", 0)
    return (e >= ERROR_THRESHOLD, f"{e} errors/{ERROR_WINDOW_MIN}min (>= {ERROR_THRESHOLD})")


_BAD_RESULTS = {"exit-code", "signal", "core-dump", "timeout", "watchdog",
                "start-limit-hit", "oom-kill"}


def band_failed_state(r: dict) -> tuple[bool, str]:
    st = r.get("active_state", "")
    res = r.get("result", "")
    # "exec-condition"/"protocol" = systemd intentionally skipped it (Condition* not met) — NOT a failure.
    bad = st == "failed" or res in _BAD_RESULTS
    return (bad, f"unit state={st or '?'} result={res or '?'}")


def band_port_conflict(r: dict) -> tuple[bool, str]:
    # The band that would have caught grace + ttyd. Even ONE bind failure is a breach.
    p = r.get("port_conflicts", 0)
    return (p >= 1, f"{p}x 'Address already in use' (port conflict)")


# The multispectral array — add a band = add a sensor. Order = report order.
BANDS = [
    ("restarts", band_restarts),
    ("error-rate", band_error_rate),
    ("failed-state", band_failed_state),
    ("port-conflict", band_port_conflict),
]


def fuse(reading: dict) -> list[str]:
    """Run every band over a unit's reading; return all tripped-band reasons (empty = clean)."""
    reasons = []
    for name, fn in BANDS:
        tripped, why = fn(reading)
        if tripped:
            reasons.append(f"[{name}] {why}")
    return reasons


# ---------- integration ----------

import fcntl

BASELINE_PATH = Path("/home/john/Thunderbird/config/ci_restart_baseline.json")


def _load_state() -> dict:
    if STATE_PATH.exists():
        try:
            with open(STATE_PATH, "r") as f:
                fcntl.flock(f, fcntl.LOCK_SH)
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_PATH, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(json.dumps(state, indent=2) + "\n")


def _load_baseline() -> dict:
    try:
        return json.loads(BASELINE_PATH.read_text())
    except Exception:
        return {}


def _save_baseline(b: dict) -> None:
    try:
        BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
        BASELINE_PATH.write_text(json.dumps(b) + "\n")
    except Exception:
        pass


def _nrestarts(unit: str) -> int:
    try:
        r = subprocess.run(["systemctl", "--user", "show", unit, "-p", "NRestarts", "--value"],
                           capture_output=True, text=True, timeout=10)
        return int((r.stdout or "0").strip() or "0")
    except Exception:
        return 0


def _journal(unit: str, window_min: int = ERROR_WINDOW_MIN) -> str:
    try:
        r = subprocess.run(
            ["journalctl", "--user", "-u", unit, "--since", f"{window_min} min ago", "--no-pager"],
            capture_output=True, text=True, timeout=15)
        return r.stdout or ""
    except Exception:
        return ""


def _error_count(unit: str, journal: str | None = None) -> int:
    out = journal if journal is not None else _journal(unit)
    return sum(1 for ln in out.splitlines()
               if any(k in ln for k in ("Error", "error", "ERROR", "Traceback",
                                        "unrecognized", "FAILURE", "Failed"))
               and "HTTP/1." not in ln)   # exclude uvicorn access-log lines (HTTP 4xx/5xx are responses, not errors)


def _port_conflicts(unit: str, journal: str | None = None) -> int:
    out = journal if journal is not None else _journal(unit)
    return sum(1 for ln in out.splitlines()
               if "Address already in use" in ln or "Errno 98" in ln)


def _unit_state(unit: str) -> tuple[str, str]:
    try:
        r = subprocess.run(["systemctl", "--user", "show", unit,
                            "-p", "ActiveState", "-p", "Result", "--value"],
                           capture_output=True, text=True, timeout=10)
        vals = [v.strip() for v in (r.stdout or "").splitlines() if v.strip()]
        active = vals[0] if len(vals) > 0 else ""
        result = vals[1] if len(vals) > 1 else ""
        return active, result
    except Exception:
        return "", ""


def _list_units() -> list[str] | None:
    """Return the service list, or None on systemctl FAILURE (NOT empty list).
    None is critical: an empty 'all clean' on a failed query is the exact blind
    spot this tool exists to prevent."""
    try:
        r = subprocess.run(["systemctl", "--user", "list-units", "--type=service",
                            "--all", "--no-legend", "--plain", "--no-pager"],
                           capture_output=True, text=True, timeout=15)
        if r.returncode != 0:
            return None
        units = [ln.split()[0] for ln in (r.stdout or "").splitlines()
                 if ln.strip() and ln.split()[0].endswith(".service")]
        return units if units else None  # zero services = systemctl is lying; treat as failure
    except Exception:
        return None


def _reading(unit: str) -> dict:
    """Collect ALL spectra for one unit (the multispectral ISR snapshot)."""
    j = _journal(unit)
    active, result = _unit_state(unit)
    return {
        "unit": unit,
        "nrestarts": _nrestarts(unit),
        "errors": _error_count(unit, j),
        "port_conflicts": _port_conflicts(unit, j),
        "active_state": active,
        "result": result,
    }


class OverwatchBlind(RuntimeError):
    """systemctl/journalctl query failed — the watcher is blind. Never silently 'clean'."""


def scan() -> list[dict]:
    """OVERWATCH — multispectral sweep of all user services. Returns fused breaches.
    Raises OverwatchBlind if the sensor (systemctl) failed — callers must escalate,
    NOT treat as clean."""
    units = _list_units()
    if units is None:
        raise OverwatchBlind("systemctl --user list-units failed — overwatch is blind")
    baseline = _load_baseline()
    new_baseline = {}
    breaches = []
    for unit in units:
        r = _reading(unit)
        cur = r["nrestarts"]
        prior = baseline.get(unit, cur)            # first sight: delta 0 (no historical false-trigger)
        r["restarts_recent"] = max(0, cur - prior)  # restarts since last scan
        new_baseline[unit] = cur
        reasons = fuse(r)
        if reasons:
            breaches.append({**r, "reasons": reasons})
    _save_baseline(new_baseline)
    return breaches


def assess(unit: str) -> dict:
    """ASSESS (BDA) — re-read the unit's spectra after a repair. Verify the strike
    achieved the effect; do NOT trust the agent's self-report. resolved=True only
    if every band is now clean. Uses restart-DELTA vs the saved baseline so a fixed
    service (no NEW restarts) reads clean even if cumulative NRestarts is still high."""
    r = _reading(unit)
    baseline = _load_baseline().get(unit, r["nrestarts"])
    r["restarts_recent"] = max(0, r["nrestarts"] - baseline)
    residual = fuse(r)
    return {"unit": unit, "resolved": not residual, "residual": residual, "reading": r}


ALERT_TIER = "sonnet"          # the alert bird's capability (fix-grade reasoning)
QRA_FLIGHT_SIZE = 3            # max scrambles per sentinel cycle (a storm waits its turn)
MANAGED_STRIKE_TIMEOUT_S = 300  # hard cap on a managed strike (< 10-min timer) — CRIT-2


def _fix_prompt(breach: dict) -> str:
    unit = breach["unit"]
    return (
        f"You are Hale (CI remediation, Whetstone lane), scrambled on ALERT by the "
        f"Self-Observability Sentinel. A service is crash-looping / error-spiking:\n"
        f"  unit: {unit}\n  restarts: {breach['nrestarts']}\n  errors(10min): {breach['errors']}\n"
        f"  reasons: {'; '.join(breach['reasons'])}\n\n"
        f"You have CI execution authority per standing_orders/SO_CI_RAZOR_SHARP_20260620.md: "
        f"refresh/revise/restart/fix infra immediately, NO Commander gate. Do exactly what a "
        f"capable engineer would:\n"
        f"1. journalctl --user -u {unit} -n 80 --no-pager  (read the actual error)\n"
        f"2. systemctl --user cat {unit}  (inspect the unit/ExecStart)\n"
        f"3. Diagnose ROOT CAUSE (bad config, port conflict, stale token, quoting bug, etc.)\n"
        f"4. FIX it (edit config/unit, daemon-reload, restart). Then run "
        f"`systemctl --user reset-failed {unit}` to clear the cumulative restart counter "
        f"(REQUIRED — otherwise the watcher re-triggers on the stale count). VERIFY the loop stopped.\n"
        f"5. Append a short entry to hale_decisions.md.\n"
        f"CONSTRAINTS: do NOT modify the 6 protected email/relay files; do NOT spend money; "
        f"do NOT send client email. If the fix REQUIRES sudo (system unit), a purchase, or a "
        f"client send — STOP and put the exact phrase 'ESCALATE TO COMMANDER: <reason>' on its "
        f"own line. Otherwise fix it autonomously and report what you did in 3-5 lines."
    )


def arm_alert(tier: str = ALERT_TIER) -> dict:
    """Warm the alert bird — pre-create the managed agent so the first strike is
    instant (no cold start). Idempotent: WingAgentClient caches the agent id."""
    try:
        from core.ai_infra.managed_agent_client import WingAgentClient
        agent_id = WingAgentClient()._get_or_create_agent(tier)
        return {"armed": True, "tier": tier, "agent_id": agent_id}
    except Exception as e:
        return {"armed": False, "error": str(e)}


def dispatch_remediation(breach: dict) -> dict:
    """Scramble the alert bird (Managed Agent, on the pad) — synchronous, instant.
    QRA posture: the managed agent is pre-armed; run_task strikes in ~seconds, no
    cold headless spawn. Returns the strike result; escalates to Commander ONLY if
    the agent reports it cannot fix (sudo/spend/client-send). Falls back to a cold
    headless spawn if the managed API is unavailable (slow strike beats no strike)."""
    unit = breach["unit"]
    prompt = _fix_prompt(breach)
    # Primary: scramble the managed-agent alert bird (fast) — under a HARD wall-clock
    # timeout so a hung managed API can never wedge the oneshot sentinel (CRIT-2).
    try:
        import concurrent.futures
        from core.ai_infra.managed_agent_client import WingAgentClient

        def _strike():
            return WingAgentClient().run_task(prompt, tier=ALERT_TIER, label=f"ci-fix-{unit}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            res = ex.submit(_strike).result(timeout=MANAGED_STRIKE_TIMEOUT_S)
        output = res.get("output", "")
        return {"unit": unit, "dispatched": True, "via": "managed_alert",
                "escalate": is_escalation(output), "cost_usd": res.get("cost_usd"),
                "output": output[:1200]}
    except Exception as e:
        # Fallback: cold headless spawn (detached). Slower, $0 MAX, but it still strikes.
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        out = OUTPUT_DIR / f"fix_{unit.replace('.', '_')}.md"
        try:
            proc = subprocess.Popen(
                ["python3", DISPATCH_CLAUDE, "--task", f"ci-fix-{unit}",
                 "--output", str(out), "--prompt", prompt + f"\nWRITE your report to {out}",
                 "--model", "sonnet"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            return {"unit": unit, "dispatched": True, "via": "headless_fallback",
                    "managed_error": str(e), "pid": proc.pid, "report": str(out),
                    "escalate": False}
        except Exception as e2:
            return {"unit": unit, "dispatched": False, "error": f"managed:{e} headless:{e2}"}


HALE_AWARENESS_LOG = Path("/home/john/Thunderbird/OpsCenter/ci_awareness.jsonl")


def notify_hale(event: str, unit: str, detail: str) -> None:
    """Make the ACCOUNTABLE owner (Hale) aware. Commander directive 2026-06-20:
    Hale owns the entire CI process and retains responsibility even when the task
    is delegated/automated — so every engage + escalate is logged to a feed Hale
    reads in the OODA Observe phase + morning brief. Awareness is non-negotiable;
    the 10-hour blind spot happened because nothing reached the accountable party."""
    try:
        HALE_AWARENESS_LOG.parent.mkdir(parents=True, exist_ok=True)
        rec = {"ts": datetime.now(timezone.utc).isoformat(),
               "event": event, "unit": unit, "detail": detail[:500]}
        with open(HALE_AWARENESS_LOG, "a") as fh:
            fh.write(json.dumps(rec) + "\n")
    except Exception:
        pass  # awareness logging must never break the kill chain


def escalate_to_commander(unit: str, detail: str) -> bool:
    """Page the Commander — ONLY when the alert agent could not fix it."""
    msg = (f"🔧→🚨 CI auto-fix could not resolve {unit} autonomously.\n{detail[:400]}\n"
           f"Needs you (likely sudo / spend / client-send).")
    try:
        from OpsCenter.wing_page import page
        page("commander", msg)
        return True
    except Exception:
        try:
            from core.relay.wing_relay import relay_send  # best-effort secondary
            relay_send("CC", msg)
            return True
        except Exception:
            return False
