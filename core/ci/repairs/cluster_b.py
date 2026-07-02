#!/usr/bin/env python3
"""
CI Rapid-Repair Warehouse — Cluster B: Credentials / Secrets / PII
Dreams2Memories Travel, LLC · Thunderbird Wing · Sterling-fleet B · 2026-07-02

Three skills:
  credential-keepalive  — SAFE (timer restart) / DESTRUCTIVE (creds file)
                          ALREADY the worked example in _worked_examples.py.
                          This module imports that module so its registration
                          lives in the REGISTRY; we do NOT re-decorate it here.
  pii-governance        — SAFE (deps/scanner) / DESTRUCTIVE-MANUAL (breach)
  infisical             — SAFE (docker restart) / DESTRUCTIVE-MANUAL (token/sudo)

NON-BREAKING: new file only. _worked_examples.py and ci_auto_repair_engine.py
are untouched.

Duplicate-registration contract
────────────────────────────────
REGISTRY is a plain dict; a duplicate `@repair_capability("credential-keepalive")`
call here would silently overwrite the worked-example entry — losing its
provenance and violating the "no double-registration" invariant. Therefore:

    import core.ci.repairs._worked_examples  # noqa: F401

...pulls credential-keepalive (and dani-identity-layer) into the REGISTRY via
the worked-example decorator, and cluster_b.py owns pii-governance and
infisical only. Any caller that imports only cluster_b still sees all three
Cluster B skills because _worked_examples is imported unconditionally below.

Tier logic
──────────────────────────────────────────────────────────────────────────────
Both pii-governance and infisical declare risk_tier=SAFE so the SAFE restart
path can auto-apply without a stage gate.  assess() raises effective_tier to
DESTRUCTIVE + repairable=False for manual-only modes — those route to
NOT_REPAIRABLE (escalate), never STAGED, because there is no wing action to
stage.  _max_tier() cannot lower the tier below the declared baseline, so a
SAFE declaration is never downgraded.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

# ── Worked-example import (credential-keepalive lives here) ──────────────────
# Must precede pii/infisical decorators so that if this module is the first
# import, the REGISTRY already holds the worked-example entries before we add
# pii-governance and infisical.  dani-identity-layer also lands here — expected.
import core.ci.repairs._worked_examples  # noqa: F401  # credential-keepalive owned here by reference

# ── Schema primitives ─────────────────────────────────────────────────────────
from core.ci.repairs.schema import (
    AssessResult,
    FailureContext,
    ProbeState,
    RepairPlan,
    RiskTier,
    probe_context,
    repair_capability,
    run_probe,
    systemctl_is_active,
    THUNDERBIRD_ROOT,
    VENV_PY,
)

# ── Existing tested repair bodies (wrap by import — single source of truth) ───
from core.ci.ci_auto_repair_engine import (
    repair_pii_governance,
    repair_infisical,
)

# ─────────────────────────────────────────────────────────────────────────────
# Cluster B, Skill 2 — pii-governance
# Baseline tier: SAFE (running the scanner / pip-installing deps is idempotent)
# Raised to DESTRUCTIVE + repairable=False for breach (no wing action exists).
# ─────────────────────────────────────────────────────────────────────────────

_PII_PROBE = "ci_probe_pii_governance.py"
_PII_SCANNER = THUNDERBIRD_ROOT / "core" / "ai_infra" / "pii_scanner.py"


@repair_capability(
    "pii-governance",
    risk_tier=RiskTier.SAFE,
    sources=[
        "output/ci_repair/research_domain_recipes.md §2.2",
        "core/ci/ci_auto_repair_engine.py::repair_pii_governance",
        "core/ai_infra/pii_scanner.py",
    ],
    timeout_seconds=60,
    max_attempts=2,
    cooldown_seconds=300,
    verify_settle_seconds=5,
)
def _pii_governance():
    def explore() -> FailureContext:
        """READ-ONLY: probe + scanner presence check. Never mutates."""
        scanner_present = _PII_SCANNER.exists()
        # Check if spaCy model is loadable (read-only test)
        spacy_ok = False
        try:
            r = subprocess.run(
                [VENV_PY, "-c", "import spacy; spacy.load('en_core_web_sm'); print('OK')"],
                capture_output=True, text=True, timeout=15,
            )
            spacy_ok = r.returncode == 0
        except Exception:
            spacy_ok = False

        ctx = probe_context(
            "pii-governance",
            _PII_PROBE,
            extra_signals={
                "scanner_present": scanner_present,
                "spacy_model_loadable": spacy_ok,
            },
        )
        return ctx

    def assess(ctx: FailureContext) -> AssessResult:
        """Side-effect-free classification. Raises to DESTRUCTIVE for breach."""
        stderr = (ctx.probe_stderr or "").lower()

        # Fence bypass / active breach detected → MANUAL-ONLY; no wing action
        if "breach" in stderr or "pii sent" in stderr or "fence bypass" in stderr:
            return AssessResult(
                mode="pii_fence_breach",
                repairable=False,
                effective_tier=RiskTier.DESTRUCTIVE,
                reason=(
                    "PII fence breach detected — Sterling incident review required; "
                    "PII rotation may be needed. No autonomous wing action."
                ),
            )

        # Scanner missing → deps install is SAFE-IDEMPOTENT (repair body handles gracefully)
        if not ctx.signals.get("scanner_present", True):
            return AssessResult(
                mode="scanner_missing",
                repairable=True,
                effective_tier=RiskTier.SAFE,
                reason="pii_scanner.py absent — deps install + scanner restore required",
            )

        # spaCy model missing → pip download is SAFE-IDEMPOTENT
        if not ctx.signals.get("spacy_model_loadable", True):
            return AssessResult(
                mode="spacy_model_missing",
                repairable=True,
                effective_tier=RiskTier.SAFE,
                reason="spaCy en_core_web_sm not loaded — `python -m spacy download en_core_web_sm`",
            )

        # Default: scanner present but probe RED → re-run scanner (SAFE)
        if ctx.probe_state == ProbeState.RED:
            return AssessResult(
                mode="scanner_error",
                repairable=True,
                effective_tier=RiskTier.SAFE,
                reason="probe RED with scanner present — re-run scanner to restore GREEN",
            )

        # Unrecognized mode: fail-safe to DESTRUCTIVE (will NOT_REPAIRABLE if False)
        return AssessResult(
            mode="unknown",
            repairable=False,
            effective_tier=RiskTier.DESTRUCTIVE,
            reason="unrecognized failure mode — escalate to Sterling for manual review",
        )

    def repair(mode: str, apply: bool = False) -> RepairPlan:
        """Dry-run by default. apply=True wraps the tested repair body."""
        plan = RepairPlan(
            skill_id="pii-governance",
            mode=mode,
            actions=[
                f"Run {VENV_PY} core/ai_infra/pii_scanner.py --detect --json on test input",
                "If scanner missing: pip install spacy phonenumbers -q in .venv",
                "If spaCy model missing: python -m spacy download en_core_web_sm",
                "Re-run ci_probe_pii_governance.py to verify GREEN",
            ],
        )
        if not apply:
            return plan  # DRY-RUN: plan only, mutates nothing

        # Apply path: call the single tested source of truth
        plan.applied = True
        plan.apply_ok = bool(repair_pii_governance())
        return plan

    def verify() -> ProbeState:
        """Independent ground truth — re-run the skill's own probe."""
        return run_probe(_PII_PROBE)

    return explore, assess, repair, verify


# ─────────────────────────────────────────────────────────────────────────────
# Cluster B, Skill 3 — infisical
# Baseline tier: SAFE (docker restart is idempotent)
# Raised to DESTRUCTIVE + repairable=False for token rotation, docker daemon
# down (needs sudo), and DB corrupt (manual restore).
# ─────────────────────────────────────────────────────────────────────────────

_INFISICAL_PROBE = "ci_probe_infisical.py"


@repair_capability(
    "infisical",
    risk_tier=RiskTier.SAFE,
    sources=[
        "output/ci_repair/research_domain_recipes.md §2.3",
        "core/ci/ci_auto_repair_engine.py::repair_infisical",
    ],
    timeout_seconds=90,
    max_attempts=2,
    cooldown_seconds=300,
    verify_settle_seconds=10,  # give infisical containers time to settle
)
def _infisical():
    def explore() -> FailureContext:
        """READ-ONLY: docker ps + daemon check. Never mutates."""
        # Is the Docker daemon responding? (read-only query)
        docker_daemon_ok = False
        try:
            r = subprocess.run(
                ["docker", "info"], capture_output=True, text=True, timeout=10,
            )
            docker_daemon_ok = r.returncode == 0
        except Exception:
            docker_daemon_ok = False

        # Is the infisical container running?
        infisical_running = False
        try:
            r = subprocess.run(
                ["docker", "ps", "--filter", "name=infisical", "--format", "{{.Names}}"],
                capture_output=True, text=True, timeout=10,
            )
            infisical_running = "infisical" in r.stdout
        except Exception:
            infisical_running = False

        # Is the system docker.service active? (read-only — user=False for system unit)
        docker_service_active = systemctl_is_active("docker.service", user=False)

        ctx = probe_context(
            "infisical",
            _INFISICAL_PROBE,
            extra_signals={
                "docker_daemon_ok": docker_daemon_ok,
                "docker_service_active": docker_service_active,
                "infisical_container_running": infisical_running,
            },
        )
        return ctx

    def assess(ctx: FailureContext) -> AssessResult:
        """Side-effect-free classification. Raises to DESTRUCTIVE for manual modes."""
        stderr = (ctx.probe_stderr or "").lower()

        # Docker daemon down → needs sudo systemctl start docker — MANUAL-ONLY
        if not ctx.signals.get("docker_daemon_ok", True):
            return AssessResult(
                mode="docker_daemon_down",
                repairable=False,
                effective_tier=RiskTier.DESTRUCTIVE,
                reason=(
                    "Docker daemon not responding — `sudo systemctl start docker` required; "
                    "needs system-level privilege, not wing-autonomous."
                ),
            )

        # Machine identity token expired → Commander UI action — MANUAL-ONLY
        if "401" in stderr or "unauthorized" in stderr or "token expired" in stderr:
            return AssessResult(
                mode="token_expired",
                repairable=False,
                effective_tier=RiskTier.DESTRUCTIVE,
                reason=(
                    "Infisical machine identity token expired — Commander must rotate "
                    "via Infisical UI. No autonomous wing action."
                ),
            )

        # DB/volume corrupt → manual restore — MANUAL-ONLY
        if "500" in stderr or "volume" in stderr or "corrupt" in stderr:
            return AssessResult(
                mode="db_corrupt",
                repairable=False,
                effective_tier=RiskTier.DESTRUCTIVE,
                reason=(
                    "Infisical container returning 500 or volume error — manual backup "
                    "restore required. No autonomous wing action."
                ),
            )

        # Container stopped but daemon is healthy → docker restart is SAFE-IDEMPOTENT
        if not ctx.signals.get("infisical_container_running", True):
            return AssessResult(
                mode="container_stopped",
                repairable=True,
                effective_tier=RiskTier.SAFE,
                reason="infisical container not running — docker restart (idempotent)",
            )

        # Probe RED with container running → probe-level failure, attempt restart
        if ctx.probe_state == ProbeState.RED:
            return AssessResult(
                mode="probe_red_container_running",
                repairable=True,
                effective_tier=RiskTier.SAFE,
                reason="probe RED with container present — restart infisical stack",
            )

        # Unrecognized mode: fail-safe to DESTRUCTIVE, escalate
        return AssessResult(
            mode="unknown",
            repairable=False,
            effective_tier=RiskTier.DESTRUCTIVE,
            reason="unrecognized Infisical failure mode — escalate to Sterling",
        )

    def repair(mode: str, apply: bool = False) -> RepairPlan:
        """Dry-run by default. apply=True wraps the tested repair body."""
        plan = RepairPlan(
            skill_id="infisical",
            mode=mode,
            actions=[
                "docker restart infisical-postgres",
                "docker restart infisical-redis",
                "docker restart infisical",
                "sleep 8s for container settle",
                f"Re-run {_INFISICAL_PROBE} to verify GREEN",
            ],
        )
        if not apply:
            return plan  # DRY-RUN: plan only, mutates nothing

        # Apply path: call the single tested source of truth
        plan.applied = True
        plan.apply_ok = bool(repair_infisical())
        return plan

    def verify() -> ProbeState:
        """Independent ground truth — re-run the skill's own probe."""
        return run_probe(_INFISICAL_PROBE)

    return explore, assess, repair, verify
