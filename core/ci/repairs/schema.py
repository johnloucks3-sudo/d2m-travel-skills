#!/usr/bin/env python3
"""
CI Rapid-Repair Warehouse — SCHEMA & RUNNER
Dreams2Memories Travel, LLC · Thunderbird Wing · Sterling (A7) · 2026-07-02

This is the SAFETY-CONTRACT keystone. It runs ALONGSIDE the live engine
(core/ci/ci_auto_repair_engine.py) and does NOT change what auto-fires today.
The integrate phase does the cutover later.

The contract every repair capability MUST honor (baked into RepairSpec):

    explore()            READ-ONLY diagnosis  -> FailureContext   (NEVER mutates)
    assess(context)      classify failure MODE -> AssessResult     (no side effects)
    repair(mode,apply=)  the fix; DRY-RUN BY DEFAULT (apply=False = plan only)
    verify()             re-run the skill's probe independently -> GREEN/RED

    risk_tier            SAFE | CAUTION | DESTRUCTIVE
    bounded              timeout, max_attempts, backoff (tenacity),
                         circuit-breaker (pybreaker) + DURABLE anti-flap state
    sources[]            provenance from ELON/Dembe research

KEYSTONE HAZARD (advisor #1): the live engine is spawned FRESH per heartbeat
(integration.py -> subprocess.Popen per RED). In-memory pybreaker breakers reset
to zero every spawn, so fail_max never accumulates across invocations. Therefore
the REAL anti-flap gate is a DURABLE state file read at the top of run_capability.
pybreaker wraps the in-cycle attempts; the JSON file is the cross-spawn truth.

TIER GATE INVARIANT (advisor #2): the risk-tier decision lives in the RUNNER,
not in any RepairSpec. A DESTRUCTIVE capability is called ONLY with apply=False,
its plan + a staged-confirm token are written to the staging file, and apply=True
is NEVER passed to it. No RepairSpec and no caller can bypass this.

NON-BREAKING (advisor #7): this warehouse uses its OWN state files under
OpsCenter/. It does not read or write the live engine's .ci_repair_state.json.
"""

from __future__ import annotations

import json
import logging
import secrets
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

try:
    from tenacity import (
        retry,
        stop_after_attempt,
        wait_exponential,
        retry_if_result,
        RetryError,
    )
except Exception:  # pragma: no cover - tenacity is a hard dep, guarded for import safety
    retry = None

try:
    import pybreaker
except Exception:  # pragma: no cover
    pybreaker = None


# ============================================================================
# PATHS — warehouse-private (NON-BREAKING: never the live engine's state file)
# ============================================================================

THUNDERBIRD_ROOT = Path("/home/john/Thunderbird")
VENV_PY = str(THUNDERBIRD_ROOT / ".venv/bin/python3")

# Warehouse-private durable files. Distinct from the live engine's
# OpsCenter/.ci_repair_state.json so the two systems never collide.
WAREHOUSE_STATE = THUNDERBIRD_ROOT / "OpsCenter" / ".ci_repair_warehouse_state.json"
STAGED_REPAIRS = THUNDERBIRD_ROOT / "OpsCenter" / "ci_staged_repairs.jsonl"
WAREHOUSE_AUDIT = THUNDERBIRD_ROOT / "OpsCenter" / "ci_repair_warehouse_audit.jsonl"
WAREHOUSE_LOG = THUNDERBIRD_ROOT / "logs" / "ci_repair_warehouse.log"

WAREHOUSE_LOG.parent.mkdir(parents=True, exist_ok=True)
logger = logging.getLogger("ci_repair_warehouse")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    _h = logging.FileHandler(WAREHOUSE_LOG)
    _h.setFormatter(logging.Formatter("%(asctime)s [WAREHOUSE] %(levelname)s: %(message)s"))
    logger.addHandler(_h)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ============================================================================
# ENUMS
# ============================================================================


class RiskTier(str, Enum):
    """Auto-apply policy tier. DESTRUCTIVE is the fail-safe default for the unsure."""
    SAFE = "SAFE"            # idempotent restart/reinstall/cache-recreate -> auto-apply OK
    CAUTION = "CAUTION"      # session/cookie/token refresh -> auto-apply + notify
    DESTRUCTIVE = "DESTRUCTIVE"  # writes/deletes/rotates creds/recreates registries -> NEVER auto-apply


class ProbeState(str, Enum):
    GREEN = "GREEN"
    RED = "RED"
    UNKNOWN = "UNKNOWN"


class Decision(str, Enum):
    """What run_capability decided to do this cycle."""
    AUTO_APPLIED = "AUTO_APPLIED"          # SAFE/CAUTION executed
    STAGED = "STAGED"                      # DESTRUCTIVE proposal written, awaiting one-touch confirm
    DRY_RUN = "DRY_RUN"                    # apply=False requested; plan returned, nothing done
    SKIPPED_HEALTHY = "SKIPPED_HEALTHY"    # explore/verify shows already GREEN — don't repair what isn't broken
    BLOCKED_CIRCUIT = "BLOCKED_CIRCUIT"    # durable breaker OPEN — escalate, do not attempt
    BLOCKED_COOLDOWN = "BLOCKED_COOLDOWN"  # anti-flap window not elapsed
    NOT_REPAIRABLE = "NOT_REPAIRABLE"      # assess() says not repairable (e.g. MANUAL-ONLY mode)
    NO_CAPABILITY = "NO_CAPABILITY"        # skill has no registered RepairSpec
    ERROR = "ERROR"


# ============================================================================
# CONTEXT / RESULT DATACLASSES
# ============================================================================


@dataclass
class FailureContext:
    """Output of explore() — READ-ONLY diagnosis. Carries no mutation, only observed facts."""
    skill_id: str
    probe_state: ProbeState = ProbeState.UNKNOWN
    signals: dict[str, Any] = field(default_factory=dict)  # systemctl status, file exists, token expiry, stderr tail...
    probe_stderr: str = ""
    observed_at: str = field(default_factory=_now)

    def as_dict(self) -> dict:
        return {
            "skill_id": self.skill_id,
            "probe_state": self.probe_state.value,
            "signals": self.signals,
            "probe_stderr": self.probe_stderr[-2000:],
            "observed_at": self.observed_at,
        }


@dataclass
class AssessResult:
    """Output of assess() — classification, NO side effects."""
    mode: str                              # named failure mode from Dembe's recipe catalog
    repairable: bool                       # False -> MANUAL-ONLY / DORMANT / needs Commander
    effective_tier: RiskTier               # a skill can span tiers; assess() raises the effective one
    reason: str = ""

    def as_dict(self) -> dict:
        return {
            "mode": self.mode,
            "repairable": self.repairable,
            "effective_tier": self.effective_tier.value,
            "reason": self.reason,
        }


@dataclass
class RepairPlan:
    """Output of repair(mode, apply=False) — the planned actions, executed nothing."""
    skill_id: str
    mode: str
    actions: list[str] = field(default_factory=list)  # human-readable planned steps
    applied: bool = False
    apply_ok: Optional[bool] = None                   # set when apply=True actually runs

    def as_dict(self) -> dict:
        return {
            "skill_id": self.skill_id,
            "mode": self.mode,
            "actions": self.actions,
            "applied": self.applied,
            "apply_ok": self.apply_ok,
        }


@dataclass
class CapabilityResult:
    """Final result of run_capability — the whole closed loop for one skill."""
    skill_id: str
    decision: Decision
    risk_tier: RiskTier
    context: Optional[FailureContext] = None
    assess: Optional[AssessResult] = None
    plan: Optional[RepairPlan] = None
    verify_before: ProbeState = ProbeState.UNKNOWN
    verify_after: ProbeState = ProbeState.UNKNOWN
    staged_token: Optional[str] = None
    attempts: int = 0
    escalated: bool = False
    note: str = ""

    def as_dict(self) -> dict:
        return {
            "ts": _now(),
            "skill_id": self.skill_id,
            "decision": self.decision.value,
            "risk_tier": self.risk_tier.value,
            "verify_before": self.verify_before.value,
            "verify_after": self.verify_after.value,
            "staged_token": self.staged_token,
            "attempts": self.attempts,
            "escalated": self.escalated,
            "note": self.note,
            "context": self.context.as_dict() if self.context else None,
            "assess": self.assess.as_dict() if self.assess else None,
            "plan": self.plan.as_dict() if self.plan else None,
        }


# ============================================================================
# REPAIR SPEC + SELF-REGISTERING DECORATOR + REGISTRY
# ============================================================================

REGISTRY: dict[str, "RepairSpec"] = {}


@dataclass
class RepairSpec:
    """
    A typed repair capability. The four phases are callables; the metadata is
    the safety envelope. Build agents author one RepairSpec per skill by wrapping
    the existing repair_<skill> body as the repair() apply-path and writing a new
    read-only explore() + a side-effect-free assess().
    """
    skill_id: str
    risk_tier: RiskTier                    # DECLARED baseline tier; assess() may raise it, never lower auto-apply below it
    explore: Callable[[], FailureContext]
    assess: Callable[[FailureContext], AssessResult]
    repair: Callable[..., RepairPlan]      # signature: repair(mode: str, apply: bool = False) -> RepairPlan
    verify: Callable[[], ProbeState]
    sources: list[str] = field(default_factory=list)   # provenance from research

    # bounded execution
    timeout_seconds: int = 120
    max_attempts: int = 2                  # tenacity in-cycle retries
    backoff_min_seconds: float = 2.0
    backoff_max_seconds: float = 15.0

    # DURABLE anti-flap (cross-spawn — the real gate, see keystone note)
    circuit_fail_max: int = 3              # consecutive cross-spawn fails -> OPEN
    circuit_reset_seconds: int = 600       # OPEN cools to HALF-OPEN after this
    cooldown_seconds: int = 300            # min time between attempts per skill
    max_repairs_per_window: int = 3        # anti-flap: don't repair same skill > N times/window
    window_seconds: int = 3600

    verify_settle_seconds: int = 5         # wait before re-probe

    def __post_init__(self):
        if not isinstance(self.risk_tier, RiskTier):
            self.risk_tier = RiskTier(str(self.risk_tier))


def repair_capability(
    skill_id: str,
    risk_tier: RiskTier = RiskTier.DESTRUCTIVE,  # FAIL-SAFE default: unsure -> stage, don't auto-fire
    sources: Optional[list[str]] = None,
    **kwargs,
):
    """
    Self-registering decorator. Applied to a FACTORY that returns the four
    callables so a skill lives in one place with zero dict maintenance.

    Usage:
        @repair_capability("dani-identity-layer", risk_tier=RiskTier.SAFE,
                           sources=["research_domain_recipes.md 3.7"])
        def _dani():
            def explore() -> FailureContext: ...
            def assess(ctx) -> AssessResult: ...
            def repair(mode, apply=False) -> RepairPlan: ...
            def verify() -> ProbeState: ...
            return explore, assess, repair, verify
    """
    def decorator(factory: Callable[[], tuple]):
        explore, assess, repair, verify = factory()
        REGISTRY[skill_id] = RepairSpec(
            skill_id=skill_id,
            risk_tier=risk_tier,
            explore=explore,
            assess=assess,
            repair=repair,
            verify=verify,
            sources=sources or [],
            **kwargs,
        )
        return factory
    return decorator


# ============================================================================
# DURABLE STATE — the cross-spawn anti-flap gate (KEYSTONE)
# ============================================================================


def _load_state() -> dict:
    if WAREHOUSE_STATE.exists():
        try:
            return json.loads(WAREHOUSE_STATE.read_text())
        except Exception as e:
            logger.error(f"warehouse state load failed: {e}")
    return {}


def _save_state(state: dict) -> None:
    try:
        WAREHOUSE_STATE.parent.mkdir(parents=True, exist_ok=True)
        WAREHOUSE_STATE.write_text(json.dumps(state, indent=2))
    except Exception as e:
        logger.error(f"warehouse state save failed: {e}")


def _skill_state(state: dict, skill_id: str) -> dict:
    return state.setdefault(skill_id, {
        "consecutive_fails": 0,
        "last_attempt": None,
        "open_until": None,          # ISO ts; if in the future, breaker is OPEN
        "window_start": None,
        "window_count": 0,
    })


def _parse_ts(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None


def _circuit_open(sk: dict) -> bool:
    """Durable breaker: OPEN if open_until is in the future."""
    until = _parse_ts(sk.get("open_until"))
    if until is None:
        return False
    return datetime.now(timezone.utc) < until


def _cooldown_blocking(sk: dict, cooldown_seconds: int) -> bool:
    last = _parse_ts(sk.get("last_attempt"))
    if last is None:
        return False
    return (datetime.now(timezone.utc) - last).total_seconds() < cooldown_seconds


def _window_exceeded(sk: dict, max_per_window: int, window_seconds: int) -> bool:
    """Anti-flap: don't repair same skill > N times / window."""
    start = _parse_ts(sk.get("window_start"))
    now = datetime.now(timezone.utc)
    if start is None or (now - start).total_seconds() > window_seconds:
        return False  # window reset happens at record time
    return sk.get("window_count", 0) >= max_per_window


def _touch_window(sk: dict, spec: RepairSpec) -> None:
    """Stamp last_attempt + advance the rolling window. Used by EVERY outcome lane
    (apply, staged, not-repairable) so anti-flap gates cover all of them, not just apply."""
    now = datetime.now(timezone.utc)
    sk["last_attempt"] = now.isoformat()
    start = _parse_ts(sk.get("window_start"))
    if start is None or (now - start).total_seconds() > spec.window_seconds:
        sk["window_start"] = now.isoformat()
        sk["window_count"] = 1
    else:
        sk["window_count"] = sk.get("window_count", 0) + 1


def _record_attempt(state: dict, spec: RepairSpec, success: bool) -> None:
    sk = _skill_state(state, spec.skill_id)
    _touch_window(sk, spec)
    now = datetime.now(timezone.utc)
    if success:
        sk["consecutive_fails"] = 0
        sk["open_until"] = None
    else:
        sk["consecutive_fails"] = sk.get("consecutive_fails", 0) + 1
        if sk["consecutive_fails"] >= spec.circuit_fail_max:
            open_until = now.timestamp() + spec.circuit_reset_seconds
            sk["open_until"] = datetime.fromtimestamp(open_until, tz=timezone.utc).isoformat()
            logger.warning(
                f"DURABLE CIRCUIT OPEN: {spec.skill_id} "
                f"({sk['consecutive_fails']} consecutive fails) until {sk['open_until']}"
            )


def _any_open_token(skill_id: str, window_seconds: int) -> Optional[str]:
    """Any in-window unconfirmed staged token for this skill (mode-agnostic),
    so the early cooldown/window gates can surface it for operator clarity."""
    return _open_staged_token(skill_id, None, window_seconds)


def _open_staged_token(skill_id: str, mode: Optional[str], window_seconds: int) -> Optional[str]:
    """Anti-flood: return an existing UNCONFIRMED staged token for the same
    skill+mode within the window, so a persistently-RED DESTRUCTIVE skill does
    NOT emit a fresh token every heartbeat. None if no live token."""
    if not STAGED_REPAIRS.exists():
        return None
    now = datetime.now(timezone.utc)
    latest = None
    try:
        for line in STAGED_REPAIRS.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except Exception:
                continue
            if e.get("skill_id") != skill_id:
                continue
            if mode is not None and e.get("mode") != mode:
                continue
            if e.get("status") != "STAGED_AWAITING_CONFIRM":
                continue  # confirmed/consumed tokens don't suppress new staging
            ts = _parse_ts(e.get("ts"))
            if ts and (now - ts).total_seconds() <= window_seconds:
                latest = e.get("token")
    except Exception as ex:
        logger.error(f"staged-token dedup scan failed: {ex}")
    return latest


# ============================================================================
# AUDIT + STAGING
# ============================================================================


def _audit(result: CapabilityResult) -> None:
    try:
        WAREHOUSE_AUDIT.parent.mkdir(parents=True, exist_ok=True)
        with open(WAREHOUSE_AUDIT, "a") as f:
            f.write(json.dumps(result.as_dict()) + "\n")
    except Exception as e:
        logger.error(f"audit write failed: {e}")


def _stage_destructive(spec: RepairSpec, ctx: FailureContext,
                       assess: AssessResult, plan: RepairPlan) -> str:
    """
    Persist a DESTRUCTIVE proposal + one-touch confirm token to the staging file.
    NEVER executes. The confirm-consumer is built in the integrate phase.
    """
    token = f"CIRPR-{secrets.token_hex(6).upper()}"
    entry = {
        "ts": _now(),
        "token": token,
        "skill_id": spec.skill_id,
        "risk_tier": RiskTier.DESTRUCTIVE.value,
        "mode": assess.mode,
        "reason": assess.reason,
        "planned_actions": plan.actions,
        "context": ctx.as_dict(),
        "status": "STAGED_AWAITING_CONFIRM",
        "sources": spec.sources,
    }
    try:
        STAGED_REPAIRS.parent.mkdir(parents=True, exist_ok=True)
        with open(STAGED_REPAIRS, "a") as f:
            f.write(json.dumps(entry) + "\n")
        logger.warning(f"STAGED DESTRUCTIVE repair {spec.skill_id} token={token} (NOT executed)")
    except Exception as e:
        logger.error(f"staging write failed: {e}")
    return token


def _notify(msg: str) -> None:
    """CAUTION-tier notify hook. Integrate phase wires Telegram; here we log + audit."""
    logger.info(f"NOTIFY: {msg}")


# ============================================================================
# THE RUNNER — explore -> assess -> decide(by tier) -> repair -> verify-after
# ============================================================================


def run_capability(skill_id: str, apply: bool = False,
                   armed_tiers: Optional[set] = None) -> CapabilityResult:
    """
    Run the full safety-contract loop for one skill.

    apply=False (DEFAULT) : dry-run everywhere. Plan is computed and returned;
                            nothing mutates. This is the safe default.
    apply=True            : SAFE -> auto-apply; CAUTION -> auto-apply + notify;
                            DESTRUCTIVE -> ALWAYS staged (apply is IGNORED for
                            DESTRUCTIVE — the tier gate cannot be bypassed).

    armed_tiers (advisor #4 — the SAFE-only leak plug): an optional whitelist of
    tier NAMES ("SAFE"/"CAUTION") that are permitted to auto-apply. When set, a
    capability whose *effective* tier (after assess() may have raised it) is NOT
    in armed_tiers is STAGED instead of auto-applied — even if apply=True and the
    DECLARED tier was armed. This closes the leak where a declared-SAFE skill's
    assess() escalates to CAUTION and would otherwise auto-fire. When None
    (default, for direct/manual callers), the legacy behavior holds: apply=True
    auto-applies SAFE+CAUTION. DESTRUCTIVE is ALWAYS staged regardless.

    The durable circuit-breaker + cooldown + window gates are read from the
    warehouse state file at the TOP of this function, so they hold ACROSS the
    per-heartbeat spawn model that resets in-memory pybreaker state.
    """
    if skill_id not in REGISTRY:
        r = CapabilityResult(skill_id=skill_id, decision=Decision.NO_CAPABILITY,
                             risk_tier=RiskTier.DESTRUCTIVE,
                             note="no RepairSpec registered")
        _audit(r)
        return r

    spec = REGISTRY[skill_id]
    state = _load_state()
    sk = _skill_state(state, skill_id)

    # --- DURABLE anti-flap gates (KEYSTONE: enforced across spawns) ----------
    if _circuit_open(sk):
        r = CapabilityResult(skill_id=skill_id, decision=Decision.BLOCKED_CIRCUIT,
                             risk_tier=spec.risk_tier, escalated=True,
                             note=f"durable circuit OPEN until {sk.get('open_until')}")
        _audit(r)
        return r
    if _window_exceeded(sk, spec.max_repairs_per_window, spec.window_seconds):
        r = CapabilityResult(skill_id=skill_id, decision=Decision.BLOCKED_COOLDOWN,
                             risk_tier=spec.risk_tier, escalated=True,
                             staged_token=_any_open_token(skill_id, spec.window_seconds),
                             note=f"anti-flap window exceeded ({sk.get('window_count')} in window)")
        _audit(r)
        return r
    if _cooldown_blocking(sk, spec.cooldown_seconds):
        r = CapabilityResult(skill_id=skill_id, decision=Decision.BLOCKED_COOLDOWN,
                             risk_tier=spec.risk_tier,
                             staged_token=_any_open_token(skill_id, spec.window_seconds),
                             note=f"cooldown active ({spec.cooldown_seconds}s)")
        _audit(r)
        return r

    # --- EXPLORE (read-only) -------------------------------------------------
    try:
        ctx = spec.explore()
    except Exception as e:
        r = CapabilityResult(skill_id=skill_id, decision=Decision.ERROR,
                             risk_tier=spec.risk_tier, escalated=True,
                             note=f"explore() raised: {e}")
        _audit(r)
        return r

    result = CapabilityResult(skill_id=skill_id, decision=Decision.DRY_RUN,
                              risk_tier=spec.risk_tier, context=ctx)
    result.verify_before = ctx.probe_state

    # "Don't repair what isn't broken" — self-healed check
    if ctx.probe_state == ProbeState.GREEN:
        result.decision = Decision.SKIPPED_HEALTHY
        result.note = "probe GREEN on explore — skipping repair"
        _audit(result)
        return result

    # --- ASSESS (classify, no side effects) ----------------------------------
    try:
        assess = spec.assess(ctx)
    except Exception as e:
        result.decision = Decision.ERROR
        result.escalated = True
        result.note = f"assess() raised: {e}"
        _audit(result)
        return result
    result.assess = assess

    if not assess.repairable:
        # Escalation lane still consumes the anti-flap budget so a RED-by-design
        # skill (DORMANT / MANUAL-ONLY) does not escalate every single heartbeat.
        result.decision = Decision.NOT_REPAIRABLE
        result.escalated = True
        result.note = f"not repairable: {assess.reason}"
        _touch_window(sk, spec)
        _save_state(state)
        _audit(result)
        return result

    # Effective tier = max(declared baseline, assess-raised). Fail-safe: never
    # auto-apply below the declared tier; assess() may only escalate the tier.
    effective_tier = _max_tier(spec.risk_tier, assess.effective_tier)
    result.risk_tier = effective_tier

    # --- DECIDE by tier ------------------------------------------------------
    # Always compute the PLAN first (dry-run) — this mutates nothing.
    try:
        plan = spec.repair(assess.mode, apply=False)
    except Exception as e:
        result.decision = Decision.ERROR
        result.escalated = True
        result.note = f"repair(apply=False) raised: {e}"
        _audit(result)
        return result
    result.plan = plan

    # DESTRUCTIVE: ALWAYS stage, apply is IGNORED. Cannot be bypassed by code.
    if effective_tier == RiskTier.DESTRUCTIVE:
        # Anti-flood: if an unconfirmed token for this skill+mode already exists
        # in-window, do NOT emit another. Reuse it and consume the anti-flap budget.
        existing = _open_staged_token(spec.skill_id, assess.mode, spec.window_seconds)
        if existing:
            result.decision = Decision.BLOCKED_COOLDOWN
            result.staged_token = existing
            result.escalated = True
            result.note = f"DESTRUCTIVE already staged (token {existing}) — awaiting confirm, not re-staging"
        else:
            token = _stage_destructive(spec, ctx, assess, plan)
            result.decision = Decision.STAGED
            result.staged_token = token
            result.escalated = True
            result.note = "DESTRUCTIVE staged for one-touch confirm (apply ignored)"
        _touch_window(sk, spec)
        _save_state(state)
        _audit(result)
        return result

    # Caller only wants a plan.
    if not apply:
        result.decision = Decision.DRY_RUN
        result.note = "apply=False — plan returned, nothing executed"
        _audit(result)
        return result

    # ARMED-TIER GATE (advisor #4): if a whitelist was supplied and the EFFECTIVE
    # tier is not armed, STAGE instead of auto-applying. This catches a
    # declared-SAFE skill whose assess() raised the tier to CAUTION — apply=True
    # alone must not auto-fire it when the runner is armed SAFE-only.
    if armed_tiers is not None and effective_tier.value not in armed_tiers:
        existing = _open_staged_token(spec.skill_id, assess.mode, spec.window_seconds)
        if existing:
            result.decision = Decision.BLOCKED_COOLDOWN
            result.staged_token = existing
            result.escalated = True
            result.note = (f"{effective_tier.value} not in armed_tiers {sorted(armed_tiers)} "
                           f"— already staged (token {existing}), not re-staging")
        else:
            token = _stage_destructive(spec, ctx, assess, plan)
            result.decision = Decision.STAGED
            result.staged_token = token
            result.escalated = True
            result.note = (f"{effective_tier.value} not in armed_tiers {sorted(armed_tiers)} "
                           f"— staged for one-touch confirm (apply gated)")
        _touch_window(sk, spec)
        _save_state(state)
        _audit(result)
        return result

    # SAFE / CAUTION -> auto-apply (CAUTION notifies).
    if effective_tier == RiskTier.CAUTION:
        _notify(f"CAUTION auto-repair '{skill_id}' mode='{assess.mode}': {plan.actions}")

    applied_ok, attempts = _execute_with_retry(spec, assess.mode)
    result.attempts = attempts
    result.plan.applied = True
    result.plan.apply_ok = applied_ok

    # --- VERIFY-AFTER (independent probe re-run = ground truth) --------------
    time.sleep(spec.verify_settle_seconds)
    try:
        after = spec.verify()
    except Exception as e:
        after = ProbeState.UNKNOWN
        logger.error(f"verify() raised for {skill_id}: {e}")
    result.verify_after = after

    success = after == ProbeState.GREEN
    _record_attempt(state, spec, success)
    _save_state(state)

    if success:
        result.decision = Decision.AUTO_APPLIED
        result.note = "repaired + verified GREEN"
    else:
        result.decision = Decision.AUTO_APPLIED
        result.escalated = True
        result.note = f"applied but verify={after.value} — escalating"
    _audit(result)
    return result


def _max_tier(a: RiskTier, b: RiskTier) -> RiskTier:
    order = {RiskTier.SAFE: 0, RiskTier.CAUTION: 1, RiskTier.DESTRUCTIVE: 2}
    return a if order[a] >= order[b] else b


def _execute_with_retry(spec: RepairSpec, mode: str) -> tuple[bool, int]:
    """
    Execute repair(mode, apply=True) with tenacity in-cycle backoff.
    Returns (apply_ok, attempts). This is the IN-cycle retry; the DURABLE
    circuit breaker (cross-spawn) is enforced separately in run_capability.
    """
    attempts = {"n": 0}

    def _once() -> bool:
        attempts["n"] += 1
        plan = spec.repair(mode, apply=True)
        return bool(plan.apply_ok)

    if retry is None:  # tenacity unavailable — single attempt, still safe
        try:
            return _once(), attempts["n"]
        except Exception as e:
            logger.error(f"{spec.skill_id} repair raised: {e}")
            return False, attempts["n"]

    runner = retry(
        stop=stop_after_attempt(spec.max_attempts),
        wait=wait_exponential(min=spec.backoff_min_seconds, max=spec.backoff_max_seconds),
        retry=retry_if_result(lambda r: r is False),
        reraise=False,
    )(_once)

    try:
        ok = runner()
        return bool(ok), attempts["n"]
    except RetryError:
        return False, attempts["n"]
    except Exception as e:
        logger.error(f"{spec.skill_id} repair raised: {e}")
        return False, attempts["n"]


# ============================================================================
# SHARED HELPERS for capability authors (read-only probes etc.)
# ============================================================================


def systemctl_is_active(unit: str, user: bool = True) -> bool:
    """READ-ONLY: is a systemd unit active? For explore()."""
    cmd = ["systemctl"] + (["--user"] if user else []) + ["is-active", unit]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return r.stdout.strip() == "active"
    except Exception:
        return False


def run_probe(probe_filename: str, timeout: int = 45) -> ProbeState:
    """
    Independent probe re-run = ground truth for verify(). READ-ONLY by contract
    (CI probes are read-only). Returns GREEN on rc==0, RED otherwise.
    """
    probe = THUNDERBIRD_ROOT / "scripts" / probe_filename
    if not probe.exists():
        return ProbeState.UNKNOWN
    try:
        r = subprocess.run([VENV_PY, str(probe)], capture_output=True, timeout=timeout)
        return ProbeState.GREEN if r.returncode == 0 else ProbeState.RED
    except Exception:
        return ProbeState.RED


def probe_context(skill_id: str, probe_filename: str, extra_signals: Optional[dict] = None,
                  timeout: int = 45) -> FailureContext:
    """Convenience explore() body: run the probe read-only, capture stderr + signals."""
    probe = THUNDERBIRD_ROOT / "scripts" / probe_filename
    stderr = ""
    st = ProbeState.UNKNOWN
    if probe.exists():
        try:
            r = subprocess.run([VENV_PY, str(probe)], capture_output=True, text=True, timeout=timeout)
            st = ProbeState.GREEN if r.returncode == 0 else ProbeState.RED
            stderr = (r.stderr or "") + (r.stdout or "")
        except Exception as e:
            st = ProbeState.RED
            stderr = f"probe exception: {e}"
    return FailureContext(skill_id=skill_id, probe_state=st,
                          signals=extra_signals or {}, probe_stderr=stderr)


if __name__ == "__main__":
    # Self-test scaffold: list registered capabilities (worked examples register on import).
    # Ensure repo root is importable when run as a script.
    if str(THUNDERBIRD_ROOT) not in sys.path:
        sys.path.insert(0, str(THUNDERBIRD_ROOT))
    # NOTE: when this file is run as a script it loads as module "__main__",
    # while _worked_examples imports "core.ci.repairs.schema" — a SECOND module
    # identity. Registrations land in the canonical module's REGISTRY, so read
    # THAT one (this is a run-as-script artifact only; normal package import has
    # a single identity and works correctly — see _worked_examples proofs).
    try:
        import core.ci.repairs._worked_examples  # noqa: F401
        from core.ci.repairs.schema import REGISTRY as CANON_REGISTRY
    except Exception as _e:
        print(f"WARN: worked examples import failed: {_e}")
        CANON_REGISTRY = REGISTRY
    print(f"Registered capabilities: {len(CANON_REGISTRY)}")
    for sid, spec in sorted(CANON_REGISTRY.items()):
        print(f"  {sid:28s} tier={spec.risk_tier.value}")
    sys.exit(0)
