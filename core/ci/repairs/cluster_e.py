#!/usr/bin/env python3
"""
CI Rapid-Repair Warehouse — Cluster E: Lifecycle (9 skills)
Dreams2Memories Travel, LLC · Thunderbird Wing
Sterling-fleet E · 2026-07-02

Skills covered:
  lifecycle-dossiers        CAUTION
  lifecycle-tp              CAUTION
  lifecycle-arc             SAFE
  lifecycle-validations     CAUTION
  lifecycle-itineraries     DESTRUCTIVE
  lifecycle-travel-surveys  CAUTION
  lifecycle-booking-surveys CAUTION
  lifecycle-proposal-engine SAFE
  lifecycle-excursion-engine CAUTION

NON-BREAKING: this file is new; no existing file is modified.

PRESERVE-INTERNALS RULE: every apply-path WRAPS the existing, tested
repair_lifecycle_* body by import from ci_auto_repair_engine.  We do
not rewrite, copy, or duplicate those bodies here.

CLIENT-LIFECYCLE BIAS applied throughout:
  - anything writing a client draft, dossier, or schedule → CAUTION minimum
  - in-place source-file edits → DESTRUCTIVE
  - idempotent self-test / validate → SAFE
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
)

# ── single source of truth for the apply-path ──────────────────────────────
from core.ci.ci_auto_repair_engine import (
    repair_lifecycle_dossiers,
    repair_lifecycle_tp,
    repair_lifecycle_arc,
    repair_lifecycle_validations,
    repair_lifecycle_itineraries,
    repair_lifecycle_travel_surveys,
    repair_lifecycle_booking_surveys,
    repair_lifecycle_proposal_engine,
    repair_lifecycle_excursion_engine,
)

# ── probe filenames (disk-verified 2026-07-02; first 5 use underscores,
#    last 4 use hyphens matching their skill-id) ────────────────────────────
_PROBE_DOSSIERS         = "ci_probe_lifecycle_dossiers.py"
_PROBE_TP               = "ci_probe_lifecycle_tp.py"
_PROBE_ARC              = "ci_probe_lifecycle_arc.py"
_PROBE_VALIDATIONS      = "ci_probe_lifecycle_validations.py"
_PROBE_ITINERARIES      = "ci_probe_lifecycle_itineraries.py"
_PROBE_TRAVEL_SURVEYS   = "ci_probe_lifecycle-travel-surveys.py"
_PROBE_BOOKING_SURVEYS  = "ci_probe_lifecycle-booking-surveys.py"
_PROBE_PROPOSAL_ENGINE  = "ci_probe_lifecycle-proposal-engine.py"
_PROBE_EXCURSION_ENGINE = "ci_probe_lifecycle-excursion-engine.py"


# ============================================================================
# E-01 · lifecycle-dossiers · CAUTION
# Writes to client dossier files (source mutation risk) → CAUTION minimum.
# ============================================================================

@repair_capability(
    "lifecycle-dossiers",
    risk_tier=RiskTier.CAUTION,
    sources=[
        "output/ci_repair/research_domain_recipes.md §5.1",
        "core/ci/ci_auto_repair_engine.py::repair_lifecycle_dossiers",
    ],
)
def _lifecycle_dossiers():
    def explore() -> FailureContext:
        return probe_context("lifecycle-dossiers", _PROBE_DOSSIERS)

    def assess(ctx: FailureContext) -> AssessResult:
        stderr = (ctx.probe_stderr or "").lower()
        stdout = (ctx.probe_stdout or "").lower()
        # Probe surfaces stale/missing dossier signals
        if "stale" in stderr or "stale" in stdout or "missing" in stderr or "missing" in stdout:
            return AssessResult(
                mode="dossier_stale_or_missing",
                repairable=True,
                effective_tier=RiskTier.CAUTION,
                reason="Dossier freshness check failed — refresh via dossier_freshness.py",
            )
        if "error" in stderr or "exception" in stderr or "traceback" in stderr:
            return AssessResult(
                mode="dossier_script_error",
                repairable=True,
                effective_tier=RiskTier.CAUTION,
                reason="dossier_freshness.py raised an error — retry is safe",
            )
        # Unknown failure state
        return AssessResult(
            mode="dossier_unknown_failure",
            repairable=True,
            effective_tier=RiskTier.CAUTION,
            reason="probe non-GREEN; run freshness script and reassess",
        )

    def repair(mode: str, apply: bool = False) -> RepairPlan:
        plan = RepairPlan(
            skill_id="lifecycle-dossiers",
            mode=mode,
            actions=["python3 core/ops/dossier_freshness.py"],
        )
        if not apply:
            return plan
        plan.applied = True
        plan.apply_ok = bool(repair_lifecycle_dossiers())
        return plan

    def verify() -> ProbeState:
        return run_probe(_PROBE_DOSSIERS)

    return explore, assess, repair, verify


# ============================================================================
# E-02 · lifecycle-tp · CAUTION
# Writes OpsCenter/staff_tasking_schedule.json (schedule mutation) → CAUTION.
# ============================================================================

@repair_capability(
    "lifecycle-tp",
    risk_tier=RiskTier.CAUTION,
    sources=[
        "output/ci_repair/research_domain_recipes.md §5.2",
        "core/ci/ci_auto_repair_engine.py::repair_lifecycle_tp",
    ],
)
def _lifecycle_tp():
    def explore() -> FailureContext:
        return probe_context("lifecycle-tp", _PROBE_TP)

    def assess(ctx: FailureContext) -> AssessResult:
        stderr = (ctx.probe_stderr or "").lower()
        stdout = (ctx.probe_stdout or "").lower()
        if "overdue" in stdout or "missed" in stdout or "overdue" in stderr:
            return AssessResult(
                mode="tp_overdue",
                repairable=True,
                effective_tier=RiskTier.CAUTION,
                reason="Overdue TPs detected — scheduler will regenerate schedule",
            )
        if "error" in stderr or "traceback" in stderr or "exception" in stderr:
            return AssessResult(
                mode="tp_scheduler_error",
                repairable=True,
                effective_tier=RiskTier.CAUTION,
                reason="TP scheduler script error — retry will regenerate schedule",
            )
        return AssessResult(
            mode="tp_schedule_stale",
            repairable=True,
            effective_tier=RiskTier.CAUTION,
            reason="probe non-GREEN; regenerate staff_tasking_schedule.json",
        )

    def repair(mode: str, apply: bool = False) -> RepairPlan:
        plan = RepairPlan(
            skill_id="lifecycle-tp",
            mode=mode,
            actions=[
                "python3 core/booking/thunderbird_tp_scheduler.py --json",
                "→ writes OpsCenter/staff_tasking_schedule.json",
            ],
        )
        if not apply:
            return plan
        plan.applied = True
        plan.apply_ok = bool(repair_lifecycle_tp())
        return plan

    def verify() -> ProbeState:
        return run_probe(_PROBE_TP)

    return explore, assess, repair, verify


# ============================================================================
# E-03 · lifecycle-arc · SAFE
# Validation-only pass (no writes to client data) → SAFE / idempotent.
# ============================================================================

@repair_capability(
    "lifecycle-arc",
    risk_tier=RiskTier.SAFE,
    sources=[
        "output/ci_repair/research_domain_recipes.md §5.3",
        "core/ci/ci_auto_repair_engine.py::repair_lifecycle_arc",
    ],
)
def _lifecycle_arc():
    def explore() -> FailureContext:
        return probe_context("lifecycle-arc", _PROBE_ARC)

    def assess(ctx: FailureContext) -> AssessResult:
        stderr = (ctx.probe_stderr or "").lower()
        stdout = (ctx.probe_stdout or "").lower()
        if "invalid" in stdout or "invalid" in stderr or "missing route" in stdout:
            return AssessResult(
                mode="arc_routing_invalid",
                repairable=True,
                effective_tier=RiskTier.SAFE,
                reason="ARC routing validation failed — validate pass is idempotent",
            )
        if "error" in stderr or "traceback" in stderr:
            return AssessResult(
                mode="arc_script_error",
                repairable=True,
                effective_tier=RiskTier.SAFE,
                reason="lifecycle_router.py raised an error — retry is safe",
            )
        return AssessResult(
            mode="arc_unknown",
            repairable=True,
            effective_tier=RiskTier.SAFE,
            reason="probe non-GREEN; run ARC validate pass",
        )

    def repair(mode: str, apply: bool = False) -> RepairPlan:
        plan = RepairPlan(
            skill_id="lifecycle-arc",
            mode=mode,
            actions=["python3 core/ops/lifecycle_router.py validate"],
        )
        if not apply:
            return plan
        plan.applied = True
        plan.apply_ok = bool(repair_lifecycle_arc())
        return plan

    def verify() -> ProbeState:
        return run_probe(_PROBE_ARC)

    return explore, assess, repair, verify


# ============================================================================
# E-04 · lifecycle-validations · CAUTION
# Renders Dani validation emails (client-facing draft generation) → CAUTION.
# ============================================================================

@repair_capability(
    "lifecycle-validations",
    risk_tier=RiskTier.CAUTION,
    sources=[
        "output/ci_repair/research_domain_recipes.md §5.4",
        "core/ci/ci_auto_repair_engine.py::repair_lifecycle_validations",
    ],
)
def _lifecycle_validations():
    def explore() -> FailureContext:
        return probe_context("lifecycle-validations", _PROBE_VALIDATIONS)

    def assess(ctx: FailureContext) -> AssessResult:
        stderr = (ctx.probe_stderr or "").lower()
        stdout = (ctx.probe_stdout or "").lower()
        if "missing template" in stderr or "template" in stderr:
            return AssessResult(
                mode="validation_template_missing",
                repairable=True,
                effective_tier=RiskTier.CAUTION,
                reason="Dani validation email template missing — render will regenerate",
            )
        if "error" in stderr or "traceback" in stderr or "exception" in stderr:
            return AssessResult(
                mode="validation_render_error",
                repairable=True,
                effective_tier=RiskTier.CAUTION,
                reason="render_dani_validation_emails.py error — retry regenerates drafts",
            )
        return AssessResult(
            mode="validation_stale",
            repairable=True,
            effective_tier=RiskTier.CAUTION,
            reason="probe non-GREEN; re-render Dani validation emails",
        )

    def repair(mode: str, apply: bool = False) -> RepairPlan:
        plan = RepairPlan(
            skill_id="lifecycle-validations",
            mode=mode,
            actions=["python3 scripts/render_dani_validation_emails.py"],
        )
        if not apply:
            return plan
        plan.applied = True
        plan.apply_ok = bool(repair_lifecycle_validations())
        return plan

    def verify() -> ProbeState:
        return run_probe(_PROBE_VALIDATIONS)

    return explore, assess, repair, verify


# ============================================================================
# E-05 · lifecycle-itineraries · DESTRUCTIVE
# Patches itinerary/luxury_itinerary_generator.py IN-PLACE (source mutation).
# assess() detects the known google_auth_oauthlib namespace bug specifically.
# repairable=True → runner STAGES for one-touch confirm; never auto-fires.
# ============================================================================

# The known bad import string that the existing repair function patches out.
_ITINERARY_BAD_IMPORT = "google_auth_oauthlib.flow"
_ITINERARY_GENERATOR  = "itinerary/luxury_itinerary_generator.py"


@repair_capability(
    "lifecycle-itineraries",
    risk_tier=RiskTier.DESTRUCTIVE,
    sources=[
        "output/ci_repair/research_domain_recipes.md §5.5",
        "core/ci/ci_auto_repair_engine.py::repair_lifecycle_itineraries",
    ],
)
def _lifecycle_itineraries():
    def explore() -> FailureContext:
        from pathlib import Path
        generator = Path("/home/john/Thunderbird") / _ITINERARY_GENERATOR
        bad_import_present = False
        if generator.exists():
            try:
                content = generator.read_text(encoding="utf-8")
                bad_import_present = _ITINERARY_BAD_IMPORT in content
            except Exception:
                pass
        return probe_context(
            "lifecycle-itineraries",
            _PROBE_ITINERARIES,
            extra_signals={"bad_import_present": bad_import_present},
        )

    def assess(ctx: FailureContext) -> AssessResult:
        bad_import = ctx.signals.get("bad_import_present", False)
        stderr = (ctx.probe_stderr or "").lower()
        if bad_import:
            # Known google_auth_oauthlib namespace bug — executable patch exists.
            # DESTRUCTIVE because it patches a source file in-place.
            return AssessResult(
                mode="itinerary_bad_import",
                repairable=True,
                effective_tier=RiskTier.DESTRUCTIVE,
                reason=(
                    f"Bad import '{_ITINERARY_BAD_IMPORT}' detected in "
                    f"{_ITINERARY_GENERATOR} — in-place patch available; "
                    "staged for one-touch confirm"
                ),
            )
        if "error" in stderr or "import" in stderr or "traceback" in stderr:
            # Unknown import or runtime error — cannot safely auto-patch.
            return AssessResult(
                mode="itinerary_unknown_error",
                repairable=False,
                effective_tier=RiskTier.DESTRUCTIVE,
                reason=(
                    "Itinerary generator error but known bad-import not present — "
                    "manual investigation required; NOT_REPAIRABLE"
                ),
            )
        # Probe failed without a matching signal
        return AssessResult(
            mode="itinerary_probe_failure",
            repairable=False,
            effective_tier=RiskTier.DESTRUCTIVE,
            reason="Probe non-GREEN, cause unknown — escalate to manual review",
        )

    def repair(mode: str, apply: bool = False) -> RepairPlan:
        plan = RepairPlan(
            skill_id="lifecycle-itineraries",
            mode=mode,
            actions=[
                f"patch {_ITINERARY_GENERATOR}: replace '{_ITINERARY_BAD_IMPORT}' "
                "namespace import with correct google.oauth2.credentials pattern",
            ],
        )
        if not apply:
            return plan
        # For DESTRUCTIVE tier the runner NEVER reaches here autonomously.
        # Wired for the confirm-consumer (post-one-touch-confirm execution).
        plan.applied = True
        plan.apply_ok = bool(repair_lifecycle_itineraries())
        return plan

    def verify() -> ProbeState:
        return run_probe(_PROBE_ITINERARIES)

    return explore, assess, repair, verify


# ============================================================================
# E-06 · lifecycle-travel-surveys · CAUTION
# Generates travel survey artifacts (client-facing output) → CAUTION.
# assess() validates the canonical Google Form ID is intact.
# ============================================================================

_TRAVEL_SURVEY_FORM_ID = "1Ni_MKR8gqfpVVlaNt3RUBfDFd4hcy4U5SSTse4RUpo8"
_TRAVEL_SURVEY_SCRIPT  = "scripts/travel_survey_generator.py"


@repair_capability(
    "lifecycle-travel-surveys",
    risk_tier=RiskTier.CAUTION,
    sources=[
        "output/ci_repair/research_domain_recipes.md §5.6",
        "core/ci/ci_auto_repair_engine.py::repair_lifecycle_travel_surveys",
    ],
)
def _lifecycle_travel_surveys():
    def explore() -> FailureContext:
        from pathlib import Path
        script = Path("/home/john/Thunderbird") / _TRAVEL_SURVEY_SCRIPT
        form_id_present = False
        if script.exists():
            try:
                content = script.read_text(encoding="utf-8")
                form_id_present = _TRAVEL_SURVEY_FORM_ID in content
            except Exception:
                pass
        return probe_context(
            "lifecycle-travel-surveys",
            _PROBE_TRAVEL_SURVEYS,
            extra_signals={"canonical_form_id_present": form_id_present},
        )

    def assess(ctx: FailureContext) -> AssessResult:
        form_ok = ctx.signals.get("canonical_form_id_present", True)
        stderr = (ctx.probe_stderr or "").lower()
        if not form_ok:
            return AssessResult(
                mode="travel_survey_wrong_form_id",
                repairable=False,
                effective_tier=RiskTier.CAUTION,
                reason=(
                    f"Canonical Form ID {_TRAVEL_SURVEY_FORM_ID} missing from "
                    f"{_TRAVEL_SURVEY_SCRIPT} — manual source inspection required"
                ),
            )
        if "error" in stderr or "traceback" in stderr or "exception" in stderr:
            return AssessResult(
                mode="travel_survey_script_error",
                repairable=True,
                effective_tier=RiskTier.CAUTION,
                reason="travel_survey_generator.py error — retry with --window 30",
            )
        return AssessResult(
            mode="travel_survey_stale",
            repairable=True,
            effective_tier=RiskTier.CAUTION,
            reason="probe non-GREEN; regenerate travel surveys with --window 30",
        )

    def repair(mode: str, apply: bool = False) -> RepairPlan:
        plan = RepairPlan(
            skill_id="lifecycle-travel-surveys",
            mode=mode,
            actions=["python3 scripts/travel_survey_generator.py --window 30"],
        )
        if not apply:
            return plan
        plan.applied = True
        plan.apply_ok = bool(repair_lifecycle_travel_surveys())
        return plan

    def verify() -> ProbeState:
        return run_probe(_PROBE_TRAVEL_SURVEYS)

    return explore, assess, repair, verify


# ============================================================================
# E-07 · lifecycle-booking-surveys · CAUTION
# Generates booking survey artifacts (client-facing output) → CAUTION.
# ============================================================================

@repair_capability(
    "lifecycle-booking-surveys",
    risk_tier=RiskTier.CAUTION,
    sources=[
        "output/ci_repair/research_domain_recipes.md §5.7",
        "core/ci/ci_auto_repair_engine.py::repair_lifecycle_booking_surveys",
    ],
)
def _lifecycle_booking_surveys():
    def explore() -> FailureContext:
        return probe_context("lifecycle-booking-surveys", _PROBE_BOOKING_SURVEYS)

    def assess(ctx: FailureContext) -> AssessResult:
        stderr = (ctx.probe_stderr or "").lower()
        stdout = (ctx.probe_stdout or "").lower()
        if "no bookings" in stdout or "no clients" in stdout:
            return AssessResult(
                mode="booking_survey_no_data",
                repairable=True,
                effective_tier=RiskTier.CAUTION,
                reason="No bookings found — survey generator will run with empty set (idempotent)",
            )
        if "error" in stderr or "traceback" in stderr or "exception" in stderr:
            return AssessResult(
                mode="booking_survey_script_error",
                repairable=True,
                effective_tier=RiskTier.CAUTION,
                reason="booking_survey_generator.py error — retry is safe",
            )
        return AssessResult(
            mode="booking_survey_stale",
            repairable=True,
            effective_tier=RiskTier.CAUTION,
            reason="probe non-GREEN; regenerate booking surveys",
        )

    def repair(mode: str, apply: bool = False) -> RepairPlan:
        plan = RepairPlan(
            skill_id="lifecycle-booking-surveys",
            mode=mode,
            actions=["python3 scripts/booking_survey_generator.py"],
        )
        if not apply:
            return plan
        plan.applied = True
        plan.apply_ok = bool(repair_lifecycle_booking_surveys())
        return plan

    def verify() -> ProbeState:
        return run_probe(_PROBE_BOOKING_SURVEYS)

    return explore, assess, repair, verify


# ============================================================================
# E-08 · lifecycle-proposal-engine · SAFE
# Self-test only; no client data written → SAFE / idempotent.
# ============================================================================

@repair_capability(
    "lifecycle-proposal-engine",
    risk_tier=RiskTier.SAFE,
    sources=[
        "output/ci_repair/research_domain_recipes.md §5.8",
        "core/ci/ci_auto_repair_engine.py::repair_lifecycle_proposal_engine",
    ],
)
def _lifecycle_proposal_engine():
    def explore() -> FailureContext:
        return probe_context("lifecycle-proposal-engine", _PROBE_PROPOSAL_ENGINE)

    def assess(ctx: FailureContext) -> AssessResult:
        stderr = (ctx.probe_stderr or "").lower()
        stdout = (ctx.probe_stdout or "").lower()
        if "self-test" in stdout and ("fail" in stdout or "error" in stdout):
            return AssessResult(
                mode="proposal_selftest_fail",
                repairable=True,
                effective_tier=RiskTier.SAFE,
                reason="proposal_engine.py --self-test failed — retry is idempotent",
            )
        if "error" in stderr or "traceback" in stderr or "import" in stderr:
            return AssessResult(
                mode="proposal_import_error",
                repairable=True,
                effective_tier=RiskTier.SAFE,
                reason="Proposal engine import/runtime error — self-test retry is safe",
            )
        return AssessResult(
            mode="proposal_unknown",
            repairable=True,
            effective_tier=RiskTier.SAFE,
            reason="probe non-GREEN; run proposal engine self-test",
        )

    def repair(mode: str, apply: bool = False) -> RepairPlan:
        plan = RepairPlan(
            skill_id="lifecycle-proposal-engine",
            mode=mode,
            actions=["python3 scripts/proposal_engine.py --self-test"],
        )
        if not apply:
            return plan
        plan.applied = True
        plan.apply_ok = bool(repair_lifecycle_proposal_engine())
        return plan

    def verify() -> ProbeState:
        return run_probe(_PROBE_PROPOSAL_ENGINE)

    return explore, assess, repair, verify


# ============================================================================
# E-09 · lifecycle-excursion-engine · CAUTION
# Runs with --force flag, writes excursion output files → CAUTION.
# ============================================================================

@repair_capability(
    "lifecycle-excursion-engine",
    risk_tier=RiskTier.CAUTION,
    sources=[
        "output/ci_repair/research_domain_recipes.md §5.9",
        "core/ci/ci_auto_repair_engine.py::repair_lifecycle_excursion_engine",
    ],
)
def _lifecycle_excursion_engine():
    def explore() -> FailureContext:
        return probe_context("lifecycle-excursion-engine", _PROBE_EXCURSION_ENGINE)

    def assess(ctx: FailureContext) -> AssessResult:
        stderr = (ctx.probe_stderr or "").lower()
        stdout = (ctx.probe_stdout or "").lower()
        if "stale" in stdout or "outdated" in stdout or "window" in stdout:
            return AssessResult(
                mode="excursion_data_stale",
                repairable=True,
                effective_tier=RiskTier.CAUTION,
                reason="Excursion data outside 180-day window — force refresh needed",
            )
        if "api" in stderr or "timeout" in stderr or "connection" in stderr:
            return AssessResult(
                mode="excursion_api_error",
                repairable=True,
                effective_tier=RiskTier.CAUTION,
                reason="Excursion engine API/network error — retry with --force --window 180",
            )
        if "error" in stderr or "traceback" in stderr or "exception" in stderr:
            return AssessResult(
                mode="excursion_script_error",
                repairable=True,
                effective_tier=RiskTier.CAUTION,
                reason="excursion_engine.py error — retry with --window 180 --force",
            )
        return AssessResult(
            mode="excursion_unknown",
            repairable=True,
            effective_tier=RiskTier.CAUTION,
            reason="probe non-GREEN; run excursion engine refresh",
        )

    def repair(mode: str, apply: bool = False) -> RepairPlan:
        plan = RepairPlan(
            skill_id="lifecycle-excursion-engine",
            mode=mode,
            actions=["python3 scripts/excursion_engine.py --window 180 --force"],
        )
        if not apply:
            return plan
        plan.applied = True
        plan.apply_ok = bool(repair_lifecycle_excursion_engine())
        return plan

    def verify() -> ProbeState:
        return run_probe(_PROBE_EXCURSION_ENGINE)

    return explore, assess, repair, verify
