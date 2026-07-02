#!/usr/bin/env python3
"""
CI Rapid-Repair Warehouse — WORKED EXAMPLES (reference templates)
Dreams2Memories Travel, LLC · Thunderbird Wing · Sterling (A7) · 2026-07-02

TWO templates that build agents copy to author the other 46 capabilities:

  1. SAFE          : `dani-identity-layer`  — idempotent systemd restart.
                     repair() apply-path WRAPS the EXISTING, TESTED body
                     `repair_dani_identity_layer` BY IMPORT (advisor #4:
                     wrap by import, single source, no drift).

  2. DESTRUCTIVE   : `credential-keepalive` (creds-file-missing mode) —
                     credential recreation. Demonstrates that a DESTRUCTIVE
                     capability STAGES and NEVER auto-applies, even when
                     run_capability is called with apply=True. The runner
                     ignores apply for DESTRUCTIVE and writes a staged token.

PRESERVE-INTERNALS RULE: we do NOT rewrite the tested repair bodies. We import
them and call them only on the apply=True path — which, for the SAFE example,
the runner may invoke; for the DESTRUCTIVE example, the runner NEVER invokes.
"""

from __future__ import annotations

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
)

# Import the EXISTING, TESTED repair bodies. This is the single source of truth
# for the apply-path — we wrap, we do not copy.
from core.ci.ci_auto_repair_engine import (
    repair_dani_identity_layer,
    repair_credential_keepalive,
)


# ============================================================================
# TEMPLATE 1 — SAFE : dani-identity-layer  (systemd restart, idempotent)
# ============================================================================

_DANI_UNIT = "thunderbird-telegram-gw.service"
_DANI_PROBE = "ci_probe_dani_identity_layer.py"


@repair_capability(
    "dani-identity-layer",
    risk_tier=RiskTier.SAFE,
    sources=[
        "output/ci_repair/research_domain_recipes.md §3.7",
        "core/ci/ci_auto_repair_engine.py::repair_dani_identity_layer",
    ],
    verify_settle_seconds=3,
)
def _dani_identity_layer():
    def explore() -> FailureContext:
        # READ-ONLY: probe state + is-active signal. Never mutates.
        ctx = probe_context("dani-identity-layer", _DANI_PROBE,
                            extra_signals={"unit_active": systemctl_is_active(_DANI_UNIT)})
        return ctx

    def assess(ctx: FailureContext) -> AssessResult:
        # No side effects. Distinguish the SAFE restart mode from the
        # DESTRUCTIVE token-revoked mode (Dembe §3.7).
        stderr = (ctx.probe_stderr or "").lower()
        if "401" in stderr or "unauthorized" in stderr or '"ok":false' in stderr:
            # bot token invalid/revoked -> needs @BotFather rotation -> MANUAL
            return AssessResult(
                mode="bot_token_revoked",
                repairable=False,
                effective_tier=RiskTier.DESTRUCTIVE,
                reason="Telegram getMe 401 / ok:false — token rotation needs Commander @BotFather",
            )
        # default: service stopped/crashed -> idempotent restart
        return AssessResult(
            mode="service_stopped",
            repairable=True,
            effective_tier=RiskTier.SAFE,
            reason="gateway service inactive/crashed — idempotent restart",
        )

    def repair(mode: str, apply: bool = False) -> RepairPlan:
        plan = RepairPlan(
            skill_id="dani-identity-layer",
            mode=mode,
            actions=[f"systemctl --user restart {_DANI_UNIT}",
                     f"wait 3s; systemctl --user is-active {_DANI_UNIT}"],
        )
        if not apply:
            return plan  # DRY-RUN: plan only, mutate nothing
        # APPLY path: call the EXISTING TESTED body (wrap, don't rewrite).
        plan.applied = True
        plan.apply_ok = bool(repair_dani_identity_layer())
        return plan

    def verify() -> ProbeState:
        # Independent ground truth — re-run the skill's own probe.
        return run_probe(_DANI_PROBE)

    return explore, assess, repair, verify


# ============================================================================
# TEMPLATE 2 — DESTRUCTIVE : credential-keepalive (creds-file recreation)
# ============================================================================
# This capability represents the DESTRUCTIVE mode of credential-keepalive:
# the OAuth credentials file is missing and would have to be re-created /
# re-authenticated (Dembe §2.1, risk class DESTRUCTIVE / MANUAL-ONLY).
#
# The runner ALWAYS stages this — apply=True is ignored. The apply-path below
# is wired to the existing tested body but the runner never reaches it for a
# DESTRUCTIVE tier. It exists only so the confirm-consumer (integrate phase)
# has a real action to execute after one-touch human confirmation.

_CRED_PROBE = "ci_probe_credential_keepalive.py"


@repair_capability(
    "credential-keepalive",
    risk_tier=RiskTier.DESTRUCTIVE,  # DESTRUCTIVE baseline -> always staged
    sources=[
        "output/ci_repair/research_domain_recipes.md §2.1",
        "core/ci/ci_auto_repair_engine.py::repair_credential_keepalive",
    ],
)
def _credential_keepalive():
    def explore() -> FailureContext:
        from pathlib import Path
        cred = Path.home() / ".claude" / ".credentials.json"
        ctx = probe_context("credential-keepalive", _CRED_PROBE,
                            extra_signals={"claude_credentials_present": cred.exists()})
        return ctx

    def assess(ctx: FailureContext) -> AssessResult:
        # TWO distinct DESTRUCTIVE outcomes — the template shows the difference
        # every author must understand:
        #   repairable=False  -> runner returns NOT_REPAIRABLE (nothing to stage;
        #                        pure escalation — no wing action exists).
        #   repairable=True   -> runner STAGES a real action + one-touch token
        #                        (a fix exists but is too dangerous to auto-fire).
        cred_present = ctx.signals.get("claude_credentials_present", True)
        if not cred_present:
            # credentials file missing -> cannot regenerate autonomously; NOTHING
            # to stage. This escalates as NOT_REPAIRABLE, not STAGED.
            return AssessResult(
                mode="credentials_file_missing",
                repairable=False,
                effective_tier=RiskTier.DESTRUCTIVE,
                reason="~/.claude/.credentials.json missing — Commander must re-auth Claude Code",
            )
        # A real, executable destructive action exists (token rotation/keepalive
        # kick under credential context) -> repairable=True so the runner STAGES
        # it for one-touch confirm rather than auto-firing. This is the branch
        # that demonstrates the staging safety gate.
        return AssessResult(
            mode="credential_rotation",
            repairable=True,
            effective_tier=RiskTier.DESTRUCTIVE,
            reason="executable but credential-touching — stage for one-touch human confirm",
        )

    def repair(mode: str, apply: bool = False) -> RepairPlan:
        plan = RepairPlan(
            skill_id="credential-keepalive",
            mode=mode,
            actions=[
                "restart claude-oauth-keepalive.timer",
                "restart johnloucks3-oauth-keepalive.timer",
                "restart d2mconcierge-oauth-keepalive.timer",
                "(if creds file missing) Commander re-authenticates Claude Code — MANUAL",
            ],
        )
        if not apply:
            return plan  # DRY-RUN
        # Apply-path wired to tested body. For DESTRUCTIVE tier the runner NEVER
        # reaches here; the confirm-consumer calls it post-confirmation.
        plan.applied = True
        plan.apply_ok = bool(repair_credential_keepalive())
        return plan

    def verify() -> ProbeState:
        return run_probe(_CRED_PROBE)

    return explore, assess, repair, verify
