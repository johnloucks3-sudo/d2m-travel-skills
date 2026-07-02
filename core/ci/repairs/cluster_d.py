#!/usr/bin/env python3
"""
CI Rapid-Repair Warehouse — Cluster D: Fare / Travel-Data
Dreams2Memories Travel, LLC · Thunderbird Wing · Sterling (A7) · 2026-07-02

Four skills (§4.1–4.4, research_domain_recipes.md):
  fare-watch-centrav    CAUTION baseline (session relogin); assess() raises to
                        DESTRUCTIVE + repairable=False on reCAPTCHA signal
  fare-watch-ita        SAFE (idempotent playwright install firefox)
  fare-watch-amadeus    DESTRUCTIVE; repairable=False (DORMANT — Commander API keys)
  supertimer-bot-health SAFE (idempotent service restart)

NON-BREAKING: new file only.  Uses warehouse-private state.
Wrap pattern: repair(apply=True) calls the EXISTING tested body from
ci_auto_repair_engine.py by import — no copy, no drift.

Signed: Sterling-fleet D · 2026-07-02
"""

from __future__ import annotations

import glob
from pathlib import Path

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

# Import the EXISTING, TESTED repair bodies — wrap by import (advisor rule #4).
# repair(apply=True) calls these; the runner decides whether to call repair at all.
from core.ci.ci_auto_repair_engine import (
    repair_fare_watch_centrav,
    repair_fare_watch_ita,
    repair_fare_watch_amadeus,
    repair_supertimer_bot_health,
)

# ---------------------------------------------------------------------------
# Probe filenames (exact basenames from config/ci_registry.json health_probe)
# run_probe() prepends scripts/ — wrong name returns UNKNOWN silently.
# ---------------------------------------------------------------------------
_CENTRAV_PROBE = "ci_probe_fare_watch_centrav.py"
_ITA_PROBE = "ci_probe_fare_watch_ita.py"
_AMADEUS_PROBE = "ci_probe_fare_watch_amadeus.py"
_SUPERTIMER_PROBE = "ci_probe_supertimer_health.py"   # NOT ci_probe_supertimer_bot_health.py

_SUPERTIMER_UNIT = "thunderbird-supertimer.service"
_THUNDERBIRD_ROOT = Path("/home/john/Thunderbird")


# ============================================================================
# 4.1  fare-watch-centrav — Flight Fare Watch (Centrav B2B)
# Baseline: CAUTION (session relogin is auto-appliable + notify)
# assess() raises to DESTRUCTIVE + repairable=False on reCAPTCHA signal
# Registry SLA: 300 000 ms — timeout generous at 360s
# ============================================================================

@repair_capability(
    "fare-watch-centrav",
    risk_tier=RiskTier.CAUTION,   # MUST be CAUTION, not DESTRUCTIVE — runner can auto-apply
    sources=[
        "output/ci_repair/research_domain_recipes.md §4.1",
        "core/ci/ci_auto_repair_engine.py::repair_fare_watch_centrav",
        "config/ci_registry.json fare-watch-centrav",
    ],
    timeout_seconds=360,
    max_attempts=2,
    backoff_min_seconds=5.0,
    backoff_max_seconds=30.0,
    verify_settle_seconds=8,
)
def _fare_watch_centrav():

    def explore() -> FailureContext:
        # READ-ONLY: run the probe, capture stderr/stdout for assess signals.
        # Also record last_check.json staleness as an extra signal.
        last_check = _THUNDERBIRD_ROOT / "OpsCenter" / "fare_watches" / "last_check.json"
        ctx = probe_context(
            "fare-watch-centrav",
            _CENTRAV_PROBE,
            extra_signals={"last_check_exists": last_check.exists()},
            timeout=45,
        )
        return ctx

    def assess(ctx: FailureContext) -> AssessResult:
        # No side effects. Two modes, one escalation lane.
        stderr = (ctx.probe_stderr or "").lower()

        # Explicit reCAPTCHA / CAPTCHA block: Commander must re-auth via Firefox.
        # Escalate to DESTRUCTIVE + repairable=False (staging has no executable action).
        if "captcha" in stderr or "recaptcha" in stderr:
            return AssessResult(
                mode="recaptcha_block",
                repairable=False,
                effective_tier=RiskTier.DESTRUCTIVE,
                reason=(
                    "Centrav reCAPTCHA detected — Commander must re-authenticate manually "
                    "via Firefox; no automated fix exists"
                ),
            )

        # Default: Centrav laravel_session expired → re-login via centrav_session_relogin.py.
        # This is the common case; effective tier stays CAUTION (auto-apply + notify).
        return AssessResult(
            mode="session_expired",
            repairable=True,
            effective_tier=RiskTier.CAUTION,
            reason="Centrav laravel_session dead — idempotent relogin will restore session",
        )

    def repair(mode: str, apply: bool = False) -> RepairPlan:
        plan = RepairPlan(
            skill_id="fare-watch-centrav",
            mode=mode,
            actions=[
                "Run scripts/centrav_session_relogin.py (restores laravel_session cookie)",
                "Probe scripts/ci_probe_fare_watch_centrav.py — expect GREEN",
                "Verify OpsCenter/fare_watches/last_check.json is fresh (<25h)",
            ],
        )
        if not apply:
            return plan  # DRY-RUN
        # APPLY: call EXISTING tested body. Mode is not passed in — body takes no args.
        plan.applied = True
        plan.apply_ok = bool(repair_fare_watch_centrav())
        return plan

    def verify() -> ProbeState:
        return run_probe(_CENTRAV_PROBE, timeout=45)

    return explore, assess, repair, verify


# ============================================================================
# 4.2  fare-watch-ita — Flight Fare Watch (ITA Matrix / Playwright Firefox)
# Baseline: SAFE — playwright install firefox is fully idempotent
# Registry SLA: 600 000 ms — playwright download can be slow; timeout 420s
# ============================================================================

@repair_capability(
    "fare-watch-ita",
    risk_tier=RiskTier.SAFE,
    sources=[
        "output/ci_repair/research_domain_recipes.md §4.2",
        "core/ci/ci_auto_repair_engine.py::repair_fare_watch_ita",
        "config/ci_registry.json fare-watch-ita",
    ],
    timeout_seconds=420,
    max_attempts=2,
    backoff_min_seconds=5.0,
    backoff_max_seconds=30.0,
    verify_settle_seconds=5,
)
def _fare_watch_ita():

    def explore() -> FailureContext:
        # READ-ONLY: probe + check Firefox binary presence.
        ff_pattern = str(
            Path.home() / ".cache" / "ms-playwright" / "firefox-*" / "firefox" / "firefox"
        )
        ff_present = len(glob.glob(ff_pattern)) > 0
        ctx = probe_context(
            "fare-watch-ita",
            _ITA_PROBE,
            extra_signals={"firefox_binary_present": ff_present},
            timeout=30,
        )
        return ctx

    def assess(ctx: FailureContext) -> AssessResult:
        # No side effects. Two modes, both SAFE.
        ff_present = ctx.signals.get("firefox_binary_present", True)
        stderr = (ctx.probe_stderr or "").lower()

        if not ff_present or "browsernotfound" in stderr or "browser not found" in stderr:
            return AssessResult(
                mode="firefox_binary_missing",
                repairable=True,
                effective_tier=RiskTier.SAFE,
                reason="Firefox Playwright binary absent — idempotent install will restore it",
            )

        # ITA UI change (selector mismatch) is a STATEFUL / Whetstone issue.
        # Probe would show 0 fares or parse error; we cannot auto-fix a UI change.
        if "selector" in stderr or "0 fares" in stderr or "parse" in stderr:
            return AssessResult(
                mode="ita_selector_mismatch",
                repairable=False,
                effective_tier=RiskTier.CAUTION,
                reason=(
                    "ITA Matrix UI may have changed — selector update needed; "
                    "route to Whetstone for script revision"
                ),
            )

        # Default: browser binary missing (most common red) or generic failure.
        return AssessResult(
            mode="firefox_binary_missing",
            repairable=True,
            effective_tier=RiskTier.SAFE,
            reason="Firefox Playwright binary absent or stale — reinstall",
        )

    def repair(mode: str, apply: bool = False) -> RepairPlan:
        plan = RepairPlan(
            skill_id="fare-watch-ita",
            mode=mode,
            actions=[
                "Run .venv/bin/playwright install firefox (idempotent)",
                "Verify ~/.cache/ms-playwright/firefox-*/firefox/firefox exists",
                "Re-probe scripts/ci_probe_fare_watch_ita.py — expect GREEN",
            ],
        )
        if not apply:
            return plan  # DRY-RUN
        plan.applied = True
        plan.apply_ok = bool(repair_fare_watch_ita())
        return plan

    def verify() -> ProbeState:
        return run_probe(_ITA_PROBE, timeout=30)

    return explore, assess, repair, verify


# ============================================================================
# 4.3  fare-watch-amadeus — Flight Fare Watch (Amadeus API)
# Baseline: DESTRUCTIVE — repairable=False (DORMANT; keys are a Commander action)
# assess() always returns repairable=False: no wing action exists to obtain API keys.
# The wrapped repair body only *checks* key presence — it cannot obtain them.
# Registry: active_workaround = "DORMANT — awaiting Commander API keys"
# ============================================================================

@repair_capability(
    "fare-watch-amadeus",
    risk_tier=RiskTier.DESTRUCTIVE,
    sources=[
        "output/ci_repair/research_domain_recipes.md §4.3",
        "core/ci/ci_auto_repair_engine.py::repair_fare_watch_amadeus",
        "config/ci_registry.json fare-watch-amadeus (DORMANT note)",
    ],
    timeout_seconds=60,
    max_attempts=1,
    verify_settle_seconds=5,
)
def _fare_watch_amadeus():

    def explore() -> FailureContext:
        import os
        # READ-ONLY: check .env and environment for key presence.
        env_file = _THUNDERBIRD_ROOT / ".env"
        env_content = env_file.read_text() if env_file.exists() else ""
        keys_in_file = (
            "AMADEUS_CLIENT_ID=" in env_content
            and "AMADEUS_CLIENT_SECRET=" in env_content
        )
        keys_in_env = bool(os.environ.get("AMADEUS_CLIENT_ID")) and bool(
            os.environ.get("AMADEUS_CLIENT_SECRET")
        )
        ctx = probe_context(
            "fare-watch-amadeus",
            _AMADEUS_PROBE,
            extra_signals={
                "keys_in_env_file": keys_in_file,
                "keys_in_environment": keys_in_env,
            },
            timeout=30,
        )
        return ctx

    def assess(ctx: FailureContext) -> AssessResult:
        # No side effects. Two observable modes — both repairable=False.
        keys_in_file = ctx.signals.get("keys_in_env_file", False)
        keys_in_env = ctx.signals.get("keys_in_environment", False)
        has_keys = keys_in_file or keys_in_env

        # Even if keys are present but probe is RED (token cache corrupt, rate limit),
        # the existing repair body only checks key presence — it cannot obtain or rotate
        # real Amadeus credentials. Both paths require Commander or Whetstone action.

        if not has_keys:
            return AssessResult(
                mode="amadeus_keys_dormant",
                repairable=False,
                effective_tier=RiskTier.DESTRUCTIVE,
                reason=(
                    "AMADEUS_CLIENT_ID / AMADEUS_CLIENT_SECRET absent — "
                    "Commander must obtain Amadeus Self-Service API keys; no wing auto-fix"
                ),
            )

        # Keys present but probe still RED (token cache, rate limit, env mismatch).
        # The wrapped body would verify keys but cannot fix an expired token cache
        # without the production credential context — escalate.
        return AssessResult(
            mode="amadeus_probe_red_with_keys",
            repairable=False,
            effective_tier=RiskTier.DESTRUCTIVE,
            reason=(
                "Amadeus keys present but probe RED — token cache corrupt, rate limit, "
                "or env/hostname mismatch; route to Whetstone for manual refresh"
            ),
        )

    def repair(mode: str, apply: bool = False) -> RepairPlan:
        # The plan documents what the wing CAN do (verify key presence) and what
        # requires Commander. apply=True is only reachable if a future assess()
        # branch adds repairable=True — which this version intentionally omits.
        plan = RepairPlan(
            skill_id="fare-watch-amadeus",
            mode=mode,
            actions=[
                "(COMMANDER ACTION) Obtain Amadeus Self-Service prod API keys "
                "from developers.amadeus.com — AMADEUS_CLIENT_ID + AMADEUS_CLIENT_SECRET",
                "Add keys to /home/john/Thunderbird/.env",
                "Run scripts/amadeus_fare_watch.py --health-check to verify token fetch",
                "Confirm >=1 fare watch in DB (core/fare_watch/fare_watch.db) for prod routes",
            ],
        )
        if not apply:
            return plan  # DRY-RUN
        # Apply-path: call existing body (key-presence check only).
        # Runner never reaches this for DESTRUCTIVE tier — here for integrate-phase
        # confirm-consumer, which may call it post-Commander action.
        plan.applied = True
        plan.apply_ok = bool(repair_fare_watch_amadeus())
        return plan

    def verify() -> ProbeState:
        return run_probe(_AMADEUS_PROBE, timeout=30)

    return explore, assess, repair, verify


# ============================================================================
# 4.4  supertimer-bot-health — Supertimer Bot Health
# Baseline: SAFE — service restart is idempotent; Firefox install adds if missing.
# assess() distinguishes service-down (SAFE restart) from Firefox-missing (SAFE install)
# and from crash-loop / persistent cascade (CAUTION → Whetstone).
# Registry: consecutive_failure_threshold = 10; client_affecting = true
# Probe name: ci_probe_supertimer_health.py (NOT ci_probe_supertimer_bot_health.py)
# ============================================================================

@repair_capability(
    "supertimer-bot-health",
    risk_tier=RiskTier.SAFE,
    sources=[
        "output/ci_repair/research_domain_recipes.md §4.4",
        "core/ci/ci_auto_repair_engine.py::repair_supertimer_bot_health",
        "config/ci_registry.json supertimer-bot-health",
    ],
    timeout_seconds=60,
    max_attempts=2,
    backoff_min_seconds=3.0,
    backoff_max_seconds=20.0,
    verify_settle_seconds=5,
)
def _supertimer_bot_health():

    def explore() -> FailureContext:
        # READ-ONLY: probe + service active check + Firefox binary presence.
        ff_pattern = str(
            Path.home() / ".cache" / "ms-playwright" / "firefox-*" / "firefox" / "firefox"
        )
        ff_present = len(glob.glob(ff_pattern)) > 0
        unit_active = systemctl_is_active(_SUPERTIMER_UNIT)
        ctx = probe_context(
            "supertimer-bot-health",
            _SUPERTIMER_PROBE,
            extra_signals={
                "unit_active": unit_active,
                "firefox_binary_present": ff_present,
            },
            timeout=30,
        )
        return ctx

    def assess(ctx: FailureContext) -> AssessResult:
        # No side effects.
        unit_active = ctx.signals.get("unit_active", False)
        ff_present = ctx.signals.get("firefox_binary_present", True)
        stderr = (ctx.probe_stderr or "").lower()

        # Service not running — idempotent restart is the right action.
        if not unit_active:
            return AssessResult(
                mode="service_stopped",
                repairable=True,
                effective_tier=RiskTier.SAFE,
                reason=f"{_SUPERTIMER_UNIT} inactive/failed — idempotent restart",
            )

        # Firefox binary missing — idempotent playwright install.
        # This was the root-cause of the Jun 28 cascade (client_bot 299 failures).
        if not ff_present or "browsernotfound" in stderr or "firefox" in stderr:
            return AssessResult(
                mode="firefox_binary_missing",
                repairable=True,
                effective_tier=RiskTier.SAFE,
                reason=(
                    "Firefox Playwright binary absent — ita_fare_watch_poll + "
                    "booking_monitor crash without it; idempotent playwright install"
                ),
            )

        # Bot crash-loop / consecutive failure storm: service active but bots failing
        # at high rate. A restart may help but the root cause is application-level.
        # Raise to CAUTION so operator is notified before auto-apply.
        if "consecutive" in stderr or "cascade" in stderr or "failure" in stderr:
            return AssessResult(
                mode="bot_crash_loop",
                repairable=True,
                effective_tier=RiskTier.CAUTION,
                reason=(
                    "Bot failure storm detected while service is active — "
                    "restart may flush stuck state; Whetstone should inspect journalctl"
                ),
            )

        # Default: service active but probe RED for unknown reason — try restart.
        return AssessResult(
            mode="service_stopped",
            repairable=True,
            effective_tier=RiskTier.SAFE,
            reason="Supertimer probe RED; service restart as first-response",
        )

    def repair(mode: str, apply: bool = False) -> RepairPlan:
        plan = RepairPlan(
            skill_id="supertimer-bot-health",
            mode=mode,
            actions=[
                f"systemctl --user restart {_SUPERTIMER_UNIT}",
                "wait 2s; systemctl --user is-active thunderbird-supertimer.service",
                "If firefox_binary_missing: .venv/bin/playwright install firefox",
                "Re-probe scripts/ci_probe_supertimer_health.py — expect GREEN",
                "(If crash-loop persists) journalctl --user -u thunderbird-supertimer.service -n 50 "
                "→ route to Whetstone",
            ],
        )
        if not apply:
            return plan  # DRY-RUN
        plan.applied = True
        plan.apply_ok = bool(repair_supertimer_bot_health())
        return plan

    def verify() -> ProbeState:
        return run_probe(_SUPERTIMER_PROBE, timeout=30)

    return explore, assess, repair, verify
