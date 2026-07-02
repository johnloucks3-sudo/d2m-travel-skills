"""CI health/currency engine — the meta CI tool.
Runs each registry entry's probe, computes razor-sharp status, applies the
replacement-trigger override, records history, writes the dashboard, and
returns page-worthy degradations.
"""
from __future__ import annotations
import fcntl
import json
import logging
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from core.ci.registry import load_registry, razor_sharp_status, DEFAULT_REGISTRY
from core.ci.replacement import needs_replacement

logger = logging.getLogger(__name__)

DASHBOARD = Path("/home/john/Thunderbird/output/CI_DASHBOARD.md")
HISTORY_DIR = Path("/home/john/Thunderbird/config/ci_history")
PROBE_TIMEOUT = 60
HISTORY_KEEP = 50  # entries retained per skill

_ICON = {"RAZOR_SHARP": "🟢", "DULL": "🟡", "RED": "🔴", "REPLACE": "🔁"}


def _try_repair(skill_id: str, probe_cmd: str, client_affecting: bool = False) -> tuple[bool, str]:
    """
    Attempt autonomous repair of a RED CI skill. Fires immediately on RED — no threshold.
    Returns (repaired, detail).

    CUTOVER 2026-07-02 (Sterling A7): this path is routed through the SAFE
    safety-contract runner (core.ci.repairs.schema.run_capability) with the SAME
    conservative armed-tier policy as the heartbeat path — single-sourced from
    config/ci_rapid_repair_policy.json. It NO LONGER calls the raw
    ci_auto_repair_engine.run_repair (which fired ungated destructive functions).

        SAFE (effective)         -> auto-applied + verify-after -> (True, "auto-repaired")
        CAUTION/DESTRUCTIVE      -> STAGED (one-touch confirm)  -> (False, "staged:<token>")
        anti-flap blocked        -> (False, "<reason>")

    A STAGED outcome returns repaired=False so the caller keeps the skill RED on
    the dashboard until an operator confirms the staged token — the honest state.
    """
    try:
        # Both live repair paths (this + the heartbeat) go through rapid_repair so
        # the tier policy has ONE source of truth. Lazy import to keep ci_health
        # importable even if the warehouse has a transient import problem.
        from core.ci.repairs.rapid_repair import _load_policy
        from core.ci.repairs.schema import run_capability, Decision, REGISTRY
        # Ensure capabilities are registered (clusters register on import).
        import core.ci.repairs.rapid_repair  # noqa: F401  (imports all clusters)
        from core.notify.hale_notify import notify_hale, notify_sterling
    except Exception as e:
        logger.warning("Safe-repair modules unavailable: %s", e)
        return False, f"repair import failed: {e}"

    if skill_id not in REGISTRY:
        logger.warning("[CI-REPAIR] %s RED but NO RepairSpec — no autonomous action", skill_id)
        return False, "no-capability"

    armed = _load_policy()
    logger.info("[CI-REPAIR] %s RED — safe runner (armed=%s)", skill_id, sorted(armed))
    try:
        r = run_capability(skill_id, apply=True, armed_tiers=armed)
    except Exception as e:
        logger.error("[CI-REPAIR] %s safe runner exception: %s", skill_id, e)
        return False, f"repair-error: {e}"

    if r.decision == Decision.AUTO_APPLIED and r.verify_after.value == "GREEN":
        logger.info("[CI-REPAIR] %s RECOVERED autonomously (safe runner)", skill_id)
        try:
            notify_hale(skill_id, "ci-sweep-repair", "RED→GREEN autonomously (SAFE)",
                        repaired=True, client_affecting=False)
        except Exception:
            pass
        return True, "auto-repaired"

    if r.decision == Decision.STAGED:
        logger.warning("[CI-REPAIR] %s STAGED (%s) token=%s — awaiting one-touch confirm",
                       skill_id, r.risk_tier.value, r.staged_token)
        try:
            notify_sterling(skill_id, f"CI {skill_id} STAGED ({r.risk_tier.value}) "
                            f"token={r.staged_token} — confirm to apply")
        except Exception:
            pass
        return False, f"staged:{r.staged_token}"

    if r.decision == Decision.SKIPPED_HEALTHY:
        # Runner's independent explore saw GREEN — treat as recovered.
        return True, "already-green"

    # Applied-but-not-green, blocked, not-repairable, error -> escalate.
    logger.warning("[CI-REPAIR] %s not auto-recovered (%s: %s) — escalating",
                   skill_id, r.decision.value, r.note)
    try:
        if client_affecting:
            notify_hale(skill_id, "ci-sweep", f"RED — {r.decision.value} (client-affecting)",
                        repaired=False, client_affecting=True)
        else:
            notify_sterling(skill_id, f"CI {skill_id} {r.decision.value}: {r.note[:150]}")
    except Exception:
        pass
    return False, f"{r.decision.value.lower()}"


def run_probe(cmd: str) -> tuple[bool, str, int, bool]:
    """Return (ok, detail, duration_ms, timed_out)."""
    t0 = time.monotonic()
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                           timeout=PROBE_TIMEOUT, cwd="/home/john/Thunderbird")
        ms = int((time.monotonic() - t0) * 1000)
        return (r.returncode == 0, (r.stdout or r.stderr)[:200], ms, False)
    except subprocess.TimeoutExpired:
        ms = int((time.monotonic() - t0) * 1000)
        return (False, f"probe timeout {PROBE_TIMEOUT}s", ms, True)
    except Exception as e:
        ms = int((time.monotonic() - t0) * 1000)
        return (False, str(e)[:200], ms, False)


def _history_path(skill_id: str) -> Path:
    return HISTORY_DIR / f"{skill_id}.jsonl"


def _append_history(skill_id: str, entry: dict) -> list[dict]:
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    p = _history_path(skill_id)
    with open(p, "a+") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.seek(0)
        lines = f.read().splitlines()
        lines.append(json.dumps(entry))
        lines = lines[-HISTORY_KEEP:]
        f.seek(0); f.truncate()
        f.write("\n".join(lines) + "\n")
    return [json.loads(l) for l in lines if l.strip()]


def _read_history(skill_id: str) -> list[dict]:
    p = _history_path(skill_id)
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def sweep(registry_path: Path = DEFAULT_REGISTRY, update_verified: bool = True) -> list[dict]:
    reg = load_registry(registry_path)
    policy = reg.get("replacement_policy", {})
    now = datetime.now(timezone.utc)
    results = []
    for s in reg["skills"]:
        probe_ok, detail, ms, timed_out = run_probe(s["health_probe"])

        # Attempt autonomous repair immediately on RED (no threshold — sweep runs infrequently)
        if not probe_ok and update_verified:
            repaired, repair_detail = _try_repair(
                s["id"], s["health_probe"],
                client_affecting=s.get("client_affecting", False)
            )
            if repaired:
                probe_ok = True
                detail = repair_detail
                ms = 0
                timed_out = False

        if probe_ok and update_verified:
            s["last_verified"] = now.isoformat()

        if update_verified:
            history = _append_history(s["id"], {
                "ts": now.isoformat(), "ok": probe_ok, "duration_ms": ms, "timed_out": timed_out})
            # Zero-workaround enforcement: a standing workaround counts as a failure.
            if s.get("active_workaround"):
                history = _append_history(s["id"], {
                    "ts": now.isoformat(), "ok": False, "duration_ms": 0,
                    "timed_out": False, "reason": "active_workaround"})
        else:
            history = _read_history(s["id"])

        status = razor_sharp_status(s, probe_ok, now)
        replace_reason = None
        if policy:
            repl, reason = needs_replacement(history, s.get("latency_sla_ms", 10**9), policy, now)
            if repl:
                status = "REPLACE"
                replace_reason = reason

        results.append({"id": s["id"], "name": s["name"], "status": status,
                        "probe_ok": probe_ok, "detail": detail, "duration_ms": ms,
                        "keeper": s["keeper"], "ci_tool": s["ci_tool"],
                        "fallback": s["fallback"], "replace_reason": replace_reason,
                        "active_workaround": s.get("active_workaround")})
    if update_verified:
        with open(registry_path, "w") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            f.write(json.dumps(reg, indent=2) + "\n")
    return results


def degradations(results: list[dict]) -> list[dict]:
    return [r for r in results if r["status"] in ("RED", "DULL", "REPLACE")]


def write_dashboard(results: list[dict]) -> Path:
    now = datetime.now(timezone.utc).isoformat()
    workarounds = sum(1 for r in results if r.get("active_workaround"))
    lines = [f"# CI DASHBOARD — {now}", "",
             f"**Active workarounds: {workarounds} (target: 0)**", "",
             "| Skill | Status | Probe | ms | CI Tool | Keeper |",
             "|---|---|---|---|---|---|"]
    for r in results:
        lines.append(f"| {r['name']} | {_ICON.get(r['status'],'?')} {r['status']} | "
                     f"{'ok' if r['probe_ok'] else 'FAIL'} | {r['duration_ms']} | "
                     f"`{r['ci_tool']}` | {r['keeper']} |")
        if r.get("replace_reason"):
            lines.append(f"|  ↳ REPLACE: {r['replace_reason']} | | | | | |")
    DASHBOARD.parent.mkdir(parents=True, exist_ok=True)
    DASHBOARD.write_text("\n".join(lines) + "\n")
    return DASHBOARD
