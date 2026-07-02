#!/usr/bin/env python3
"""
CI Rapid-Repair Warehouse — Cluster G: Data-Stores / Comms / Identity
Dreams2Memories Travel, LLC · Thunderbird Wing
Author: Sterling (A7) · Sterling-fleet G · 2026-07-02

Skills:
  qdrant            SAFE (docker start) / DESTRUCTIVE (volume/dim mismatch)
  email-handling    SAFE (timer restart) / DESTRUCTIVE (creds file missing)
  gdrive-mx         SAFE (probe IS the repair — token refresh + live list)
  evernote-mx       CAUTION (backup script triggers token refresh) / DESTRUCTIVE (SDK EOL)
  klaviyo-canary    SAFE (deps install) / DESTRUCTIVE (API key missing)

PROTECTED-FILE GUARANTEE (SO 2026-06-08):
  email-handling repair NEVER modifies the 6 protected scanner/relay files:
    OpsCenter/run_commander_directive_sweep.py
    OpsCenter/dispatch_and_email.py
    OpsCenter/email_task_ingest.py
    core/email/thunderbird_commander_inbox.py
    OpsCenter/relay_send.py
    core/relay/wing_relay.py
  Timer restarts and credential presence checks ONLY.

PRESERVE-INTERNALS RULE: all apply-paths wrap existing, tested repair_<skill>
bodies by import — no drift, no duplication.

NON-BREAKING: new file only. No modifications to schema.py, ci_auto_repair_engine.py,
or any existing cluster file.
"""

from __future__ import annotations

import subprocess

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

# Import the EXISTING, TESTED repair bodies — wrap, never rewrite.
from core.ci.ci_auto_repair_engine import (
    repair_qdrant,
    repair_email_handling,
    repair_gdrive_mx,
    repair_evernote_mx,
    repair_klaviyo_canary,
)


# ============================================================================
# G.1 — qdrant   SAFE (docker start) / DESTRUCTIVE (volume/dim mismatch)
# ============================================================================
#
# Two distinct failure modes from Dembe §7.1:
#   "docker_stopped"     — docker start qdrant; idempotent; SAFE auto-apply
#   "volume_or_dim"      — data-loss risk (dim mismatch / missing volume);
#                          stage for one-touch human confirm; DESTRUCTIVE
#
# The existing repair_qdrant() body covers the SAFE mode (docker start + probe).
# DESTRUCTIVE mode is staged only — the confirm-consumer calls repair_qdrant()
# post-confirmation with awareness that manual volume/index rebuild follows.

_QDRANT_PROBE = "ci_probe_qdrant.py"
_QDRANT_HOST = "http://localhost:6333"


@repair_capability(
    "qdrant",
    risk_tier=RiskTier.SAFE,       # declared baseline; assess() raises to DESTRUCTIVE when needed
    sources=[
        "output/ci_repair/research_domain_recipes.md §7.1",
        "core/ci/ci_auto_repair_engine.py::repair_qdrant",
        "config/ci_registry.json id=qdrant",
    ],
    timeout_seconds=90,
    max_attempts=2,
    verify_settle_seconds=5,
)
def _qdrant():
    def explore() -> FailureContext:
        # READ-ONLY: run probe + capture docker ps + collections HTTP signal.
        # Never mutates. Extra signals inform assess() mode selection.
        docker_running = False
        collection_missing = False
        dim_mismatch = False

        try:
            dp = subprocess.run(
                ["docker", "ps", "--filter", "name=qdrant", "--format", "{{.Names}}"],
                capture_output=True, text=True, timeout=10,
            )
            docker_running = "qdrant" in dp.stdout
        except Exception:
            pass

        if docker_running:
            try:
                import urllib.request
                with urllib.request.urlopen(
                    f"{_QDRANT_HOST}/collections/thunderbird_memories", timeout=5
                ) as resp:
                    collection_missing = resp.status == 404
            except Exception as e:
                err = str(e).lower()
                if "404" in err:
                    collection_missing = True
                elif "dimension" in err or "dim" in err or "mismatch" in err:
                    dim_mismatch = True

        ctx = probe_context(
            "qdrant", _QDRANT_PROBE,
            extra_signals={
                "docker_running": docker_running,
                "collection_missing": collection_missing,
                "dim_mismatch": dim_mismatch,
            },
        )
        return ctx

    def assess(ctx: FailureContext) -> AssessResult:
        # No side effects. Route to the right tier based on observed signals.
        stderr = (ctx.probe_stderr or "").lower()
        sigs = ctx.signals

        # Dimension mismatch or missing volume = data at risk → DESTRUCTIVE
        dim = sigs.get("dim_mismatch") or "dimension" in stderr or "mismatch" in stderr
        # Volume missing: container starts but collections empty (not just stopped)
        docker_up_no_data = (
            sigs.get("docker_running") and sigs.get("collection_missing")
        )
        if dim or docker_up_no_data:
            return AssessResult(
                mode="volume_or_dim",
                repairable=True,
                effective_tier=RiskTier.DESTRUCTIVE,
                reason=(
                    "Vector dimension mismatch or Docker volume missing — "
                    "collection recreate/re-index required; data-loss risk; "
                    "stage for one-touch human confirm."
                ),
            )

        # Docker daemon not running → DESTRUCTIVE (needs sudo)
        daemon_err = "cannot connect" in stderr or "docker daemon" in stderr
        if daemon_err and not sigs.get("docker_running"):
            return AssessResult(
                mode="docker_daemon_down",
                repairable=False,
                effective_tier=RiskTier.DESTRUCTIVE,
                reason="Docker daemon not running — needs sudo systemctl start docker; MANUAL-ONLY",
            )

        # Default: container stopped → SAFE idempotent docker start
        return AssessResult(
            mode="docker_stopped",
            repairable=True,
            effective_tier=RiskTier.SAFE,
            reason="Qdrant container stopped — idempotent docker start qdrant",
        )

    def repair(mode: str, apply: bool = False) -> RepairPlan:
        if mode == "volume_or_dim":
            plan = RepairPlan(
                skill_id="qdrant",
                mode=mode,
                actions=[
                    "MANUAL: verify Docker volume mount (-v /path/qdrant_storage:/qdrant/storage)",
                    "If volume intact: docker start qdrant; re-run ci_probe_qdrant.py",
                    "If dim mismatch: docker stop qdrant; DELETE collection thunderbird_memories; "
                    "re-create with correct embedding dimensions; re-index all memories via "
                    "core/memory/qdrant_memory.py; docker start qdrant",
                    "Restore from backup if volume is missing",
                ],
            )
            # apply=True is NEVER reached for DESTRUCTIVE — runner stages + ignores apply.
            # Wired here for the confirm-consumer (integrate phase).
            if apply:
                plan.applied = True
                plan.apply_ok = bool(repair_qdrant())
            return plan

        # docker_stopped (SAFE)
        plan = RepairPlan(
            skill_id="qdrant",
            mode=mode,
            actions=[
                "docker start qdrant",
                "wait 5s",
                "run ci_probe_qdrant.py — verify /collections returns 200 + thunderbird_memories present",
            ],
        )
        if not apply:
            return plan
        plan.applied = True
        plan.apply_ok = bool(repair_qdrant())
        return plan

    def verify() -> ProbeState:
        return run_probe(_QDRANT_PROBE)

    return explore, assess, repair, verify


# ============================================================================
# G.2 — email-handling   SAFE (timer restart) / DESTRUCTIVE (creds file)
# ============================================================================
#
# ⚠️ PROTECTED-FILE CONSTRAINT (SO 2026-06-08):
#   Repair ONLY restarts OAuth keepalive timers and checks cred file presence.
#   It NEVER reads, writes, or modifies the 6 protected scanner/relay files.
#
# Failure modes (Dembe §7.2):
#   "timer_stopped"     — restart d2mconcierge-oauth-keepalive or
#                         johnloucks3-oauth-keepalive timers; SAFE idempotent
#   "creds_file_missing"— credentials JSON absent; Commander OAuth re-consent
#                         required; NOT repairable autonomously; DESTRUCTIVE

_EMAIL_PROBE = "ci_probe_email_handling.py"
_EMAIL_TIMERS = [
    "d2mconcierge-oauth-keepalive.timer",
    "johnloucks3-oauth-keepalive.timer",
]


@repair_capability(
    "email-handling",
    risk_tier=RiskTier.SAFE,      # declared baseline; assess() raises when creds absent
    sources=[
        "output/ci_repair/research_domain_recipes.md §7.2",
        "core/ci/ci_auto_repair_engine.py::repair_email_handling",
        "config/ci_registry.json id=email-handling",
        "standing_orders/SO_EMAIL_SCANNER_PROTECT_20260608.md (6 protected files)",
    ],
    timeout_seconds=60,
    max_attempts=2,
    verify_settle_seconds=4,
)
def _email_handling():
    # Paths to the 6 protected files — repair must never touch these.
    _PROTECTED = {
        THUNDERBIRD_ROOT / "OpsCenter" / "run_commander_directive_sweep.py",
        THUNDERBIRD_ROOT / "OpsCenter" / "dispatch_and_email.py",
        THUNDERBIRD_ROOT / "OpsCenter" / "email_task_ingest.py",
        THUNDERBIRD_ROOT / "core" / "email" / "thunderbird_commander_inbox.py",
        THUNDERBIRD_ROOT / "OpsCenter" / "relay_send.py",
        THUNDERBIRD_ROOT / "core" / "relay" / "wing_relay.py",
    }

    def explore() -> FailureContext:
        # READ-ONLY: timer states + credential presence. Never mutates.
        # Protected files not read; only credential JSON paths checked.
        from pathlib import Path

        cred_paths = [
            Path.home() / ".gmail-mcp" / "d2mconcierge" / "credentials.json",
            Path.home() / ".gmail-mcp" / "johnloucks3" / "credentials.json",
            THUNDERBIRD_ROOT / "config" / "persona_gmail_token.json",
            THUNDERBIRD_ROOT / "creds" / "gmail_token.json",
        ]
        creds_found = [str(p) for p in cred_paths if p.exists()]

        timer_states = {t: systemctl_is_active(t) for t in _EMAIL_TIMERS}

        ctx = probe_context(
            "email-handling", _EMAIL_PROBE,
            extra_signals={
                "creds_found": creds_found,
                "creds_present": len(creds_found) > 0,
                "timer_states": timer_states,
                "any_timer_down": not all(timer_states.values()),
            },
        )
        return ctx

    def assess(ctx: FailureContext) -> AssessResult:
        sigs = ctx.signals

        # No credentials at all → Commander must re-run OAuth consent flow
        if not sigs.get("creds_present", True):
            return AssessResult(
                mode="creds_file_missing",
                repairable=False,
                effective_tier=RiskTier.DESTRUCTIVE,
                reason=(
                    "Gmail credentials JSON absent for all accounts — "
                    "Commander must re-run OAuth consent flow (cannot regenerate autonomously)"
                ),
            )

        # One or more timers stopped → idempotent restart; SAFE
        # (This is the path repair_email_handling() in the engine addresses via
        #  credential presence check; timer restart is the targeted fix here.)
        return AssessResult(
            mode="timer_stopped",
            repairable=True,
            effective_tier=RiskTier.SAFE,
            reason=(
                "Gmail OAuth keepalive timer(s) stopped — "
                "restart d2mconcierge-oauth-keepalive and/or johnloucks3-oauth-keepalive timers"
            ),
        )

    def repair(mode: str, apply: bool = False) -> RepairPlan:
        if mode == "creds_file_missing":
            plan = RepairPlan(
                skill_id="email-handling",
                mode=mode,
                actions=[
                    "MANUAL: Commander re-runs OAuth consent flow for affected Gmail account",
                    "Re-authenticate d2mconcierge at ~/.gmail-mcp/d2mconcierge/",
                    "Re-authenticate johnloucks3 at ~/.gmail-mcp/johnloucks3/",
                    "Refresh config/persona_gmail_token.json via scripts/gmail_token_refresh.py",
                    "NOTE: the 6 protected scanner/relay files are NOT touched by this repair",
                ],
            )
            # Runner never reaches apply=True for DESTRUCTIVE; wired for confirm-consumer.
            if apply:
                plan.applied = True
                plan.apply_ok = bool(repair_email_handling())
            return plan

        # timer_stopped (SAFE): restart timers + verify cred presence
        # ⚠️ Protected files are NEVER modified — timer restart only.
        plan = RepairPlan(
            skill_id="email-handling",
            mode=mode,
            actions=[
                "systemctl --user restart d2mconcierge-oauth-keepalive.timer",
                "systemctl --user restart johnloucks3-oauth-keepalive.timer",
                "verify at least one Gmail credentials JSON is present",
                "run ci_probe_email_handling.py",
                "NOTE: 6 protected scanner/relay files are NOT touched",
            ],
        )
        if not apply:
            return plan
        # Apply: restart timers, then delegate to the existing tested body for
        # cred-presence verification. Timer restart is the new targeted layer.
        try:
            for timer in _EMAIL_TIMERS:
                subprocess.run(
                    ["systemctl", "--user", "restart", timer],
                    capture_output=True, timeout=15,
                )
        except Exception:
            pass
        plan.applied = True
        plan.apply_ok = bool(repair_email_handling())
        return plan

    def verify() -> ProbeState:
        return run_probe(_EMAIL_PROBE)

    return explore, assess, repair, verify


# ============================================================================
# G.3 — gdrive-mx   SAFE (probe IS the repair)
# ============================================================================
#
# Per Dembe §7.3: "Probe itself IS the repair (refresh + live list);
# re-run scripts/ci_probe_gdrive-mx.py"
#
# The existing repair_gdrive_mx() body implements exactly this pattern
# (re-runs the probe script). Only repairable mode is token refresh (SAFE).
# Credentials-file-missing is MANUAL-ONLY.

_GDRIVE_PROBE = "ci_probe_gdrive-mx.py"


@repair_capability(
    "gdrive-mx",
    risk_tier=RiskTier.SAFE,
    sources=[
        "output/ci_repair/research_domain_recipes.md §7.3",
        "core/ci/ci_auto_repair_engine.py::repair_gdrive_mx",
        "config/ci_registry.json id=gdrive-mx",
    ],
    timeout_seconds=60,
    max_attempts=2,
    verify_settle_seconds=5,
)
def _gdrive_mx():
    def explore() -> FailureContext:
        # READ-ONLY: probe run captures token state + API reachability.
        from pathlib import Path
        import os
        cred_paths = [
            Path.home() / ".config" / "gcloud" / "credentials.json",
            Path.home() / ".gdrive" / "credentials.json",
        ]
        creds_found = any(p.exists() for p in cred_paths)
        env_cred = bool(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))

        ctx = probe_context(
            "gdrive-mx", _GDRIVE_PROBE,
            extra_signals={
                "creds_file_found": creds_found or env_cred,
            },
        )
        return ctx

    def assess(ctx: FailureContext) -> AssessResult:
        stderr = (ctx.probe_stderr or "").lower()

        # Credentials file missing → MANUAL re-auth
        creds_found = ctx.signals.get("creds_file_found", True)
        if not creds_found or "filenotfounderror" in stderr or "no such file" in stderr:
            return AssessResult(
                mode="creds_missing",
                repairable=False,
                effective_tier=RiskTier.DESTRUCTIVE,
                reason=(
                    "Google Drive credentials file missing — "
                    "Commander must re-run Drive OAuth consent flow"
                ),
            )

        # Quota exceeded → wait only, no auto-repair
        if "quotaexceeded" in stderr or "quota" in stderr:
            return AssessResult(
                mode="quota_exceeded",
                repairable=False,
                effective_tier=RiskTier.CAUTION,
                reason=(
                    "Drive API quota exceeded — wait 24h for quota reset; "
                    "no autonomous repair action available"
                ),
            )

        # Default: token expired → probe re-run IS the repair (SAFE)
        return AssessResult(
            mode="token_expired",
            repairable=True,
            effective_tier=RiskTier.SAFE,
            reason="OAuth token expired — probe re-run triggers refresh + live list verification",
        )

    def repair(mode: str, apply: bool = False) -> RepairPlan:
        plan = RepairPlan(
            skill_id="gdrive-mx",
            mode=mode,
            actions=[
                "re-run scripts/ci_probe_gdrive-mx.py (probe triggers token refresh + live list)",
                "verify Drive API returns ≥1 file entry",
            ],
        )
        if not apply:
            return plan
        plan.applied = True
        plan.apply_ok = bool(repair_gdrive_mx())
        return plan

    def verify() -> ProbeState:
        return run_probe(_GDRIVE_PROBE)

    return explore, assess, repair, verify


# ============================================================================
# G.4 — evernote-mx   CAUTION (backup/token refresh) / DESTRUCTIVE (SDK EOL)
# ============================================================================
#
# Dembe §7.4 + summary table §47:
#   "backup script STATEFUL; SDK EOL MANUAL" / "Whetstone REPLACE trigger"
#
# Two modes:
#   "token_or_rate"   — re-run backup script (triggers token refresh); CAUTION
#                       (writes data; notify before auto-fire)
#   "sdk_eol"         — Evernote v1 API EOL / deprecated endpoints;
#                       NOT repairable; DESTRUCTIVE (Whetstone REPLACE trigger)

_EVERNOTE_PROBE = "ci_probe_evernote-mx.py"


@repair_capability(
    "evernote-mx",
    risk_tier=RiskTier.CAUTION,   # declared baseline: backup script writes data
    sources=[
        "output/ci_repair/research_domain_recipes.md §7.4",
        "core/ci/ci_auto_repair_engine.py::repair_evernote_mx",
        "config/ci_registry.json id=evernote-mx",
    ],
    timeout_seconds=180,
    max_attempts=2,
    verify_settle_seconds=8,
)
def _evernote_mx():
    def explore() -> FailureContext:
        # READ-ONLY: probe run + check backup script presence.
        backup_exists = (THUNDERBIRD_ROOT / "api" / "thunderbird_evernote_backup.py").exists()
        ctx = probe_context(
            "evernote-mx", _EVERNOTE_PROBE,
            extra_signals={"backup_script_exists": backup_exists},
        )
        return ctx

    def assess(ctx: FailureContext) -> AssessResult:
        stderr = (ctx.probe_stderr or "").lower()

        # SDK EOL / deprecated API markers → NOT repairable; Whetstone REPLACE
        eol_signals = (
            "404" in stderr
            or "deprecated" in stderr
            or "eol" in stderr
            or "edamnotfoundexception" in stderr
            or "not found" in stderr
        )
        if eol_signals:
            return AssessResult(
                mode="sdk_eol",
                repairable=False,
                effective_tier=RiskTier.DESTRUCTIVE,
                reason=(
                    "Evernote v1 API deprecated endpoint detected — "
                    "Whetstone REPLACE trigger: evaluate Notion/Obsidian migration; MANUAL-ONLY"
                ),
            )

        # Import error → missing deps; SAFE-IDEMPOTENT pip install
        if "importerror" in stderr or "modulenot" in stderr or "no module" in stderr:
            return AssessResult(
                mode="import_error",
                repairable=True,
                effective_tier=RiskTier.SAFE,
                reason="Evernote SDK import error — pip install evernote3 or evernote-sdk-python3",
            )

        # Auth expired or rate limit → backup script re-run triggers token refresh; CAUTION
        return AssessResult(
            mode="token_or_rate",
            repairable=True,
            effective_tier=RiskTier.CAUTION,
            reason=(
                "Evernote token expired or rate limit — "
                "re-run backup script (triggers token refresh); notifying before auto-fire"
            ),
        )

    def repair(mode: str, apply: bool = False) -> RepairPlan:
        if mode == "import_error":
            plan = RepairPlan(
                skill_id="evernote-mx",
                mode=mode,
                actions=[
                    ".venv/bin/pip install evernote3 -q",
                    "verify: python3 -c \"import evernote\"",
                    "re-run ci_probe_evernote-mx.py",
                ],
            )
            if not apply:
                return plan
            plan.applied = True
            try:
                subprocess.run(
                    [str(THUNDERBIRD_ROOT / ".venv/bin/pip"),
                     "install", "evernote3", "-q", "--timeout=60"],
                    capture_output=True, timeout=90,
                )
            except Exception:
                pass
            plan.apply_ok = bool(repair_evernote_mx())
            return plan

        # token_or_rate (CAUTION): backup script re-run
        plan = RepairPlan(
            skill_id="evernote-mx",
            mode=mode,
            actions=[
                "re-run api/thunderbird_evernote_backup.py (triggers Evernote token refresh)",
                "wait 5s",
                "re-run ci_probe_evernote-mx.py",
            ],
        )
        if not apply:
            return plan
        plan.applied = True
        plan.apply_ok = bool(repair_evernote_mx())
        return plan

    def verify() -> ProbeState:
        return run_probe(_EVERNOTE_PROBE)

    return explore, assess, repair, verify


# ============================================================================
# G.5 — klaviyo-canary   SAFE (deps) / DESTRUCTIVE (API key missing)
# ============================================================================
#
# Dembe §7.5 + summary table §48:
#   "deps SAFE; API key MANUAL" / "Commander Klaviyo UI"
#
# Two modes:
#   "import_error"   — pip install requests; SAFE idempotent
#   "api_key_missing"— API key invalid/expired/absent; Commander Klaviyo UI;
#                      NOT repairable autonomously; DESTRUCTIVE (stages)

_KLAVIYO_PROBE = "ci_probe_klaviyo_canary.py"


@repair_capability(
    "klaviyo-canary",
    risk_tier=RiskTier.SAFE,     # declared baseline; assess() raises when API key absent
    sources=[
        "output/ci_repair/research_domain_recipes.md §7.5",
        "core/ci/ci_auto_repair_engine.py::repair_klaviyo_canary",
        "config/ci_registry.json id=klaviyo-canary",
    ],
    timeout_seconds=60,
    max_attempts=2,
    verify_settle_seconds=4,
)
def _klaviyo_canary():
    def explore() -> FailureContext:
        # READ-ONLY: probe run + env/file API key presence check.
        import os
        from pathlib import Path

        env_file = THUNDERBIRD_ROOT / ".env"
        env_content = ""
        if env_file.exists():
            try:
                env_content = env_file.read_text()
            except Exception:
                pass

        key_present = (
            "KLAVIYO_API_KEY" in env_content
            or bool(os.environ.get("KLAVIYO_API_KEY"))
        )

        script_exists = (THUNDERBIRD_ROOT / "scripts" / "klaviyo_canary.py").exists()

        ctx = probe_context(
            "klaviyo-canary", _KLAVIYO_PROBE,
            extra_signals={
                "api_key_present": key_present,
                "script_exists": script_exists,
            },
        )
        return ctx

    def assess(ctx: FailureContext) -> AssessResult:
        stderr = (ctx.probe_stderr or "").lower()
        sigs = ctx.signals

        # API key absent or 401 → DESTRUCTIVE / MANUAL-ONLY
        key_absent = not sigs.get("api_key_present", True)
        auth_fail = "401" in stderr or "unauthorized" in stderr or "invalid_key" in stderr
        if key_absent or auth_fail:
            return AssessResult(
                mode="api_key_missing",
                repairable=True,    # A real staged action: "regenerate via Klaviyo UI"
                effective_tier=RiskTier.DESTRUCTIVE,
                reason=(
                    "Klaviyo API key absent or invalid — "
                    "Commander must regenerate in Klaviyo account settings UI; "
                    "stage for one-touch confirm"
                ),
            )

        # Import/script error → pip install; SAFE
        if (
            not sigs.get("script_exists")
            or "importerror" in stderr
            or "no module" in stderr
        ):
            return AssessResult(
                mode="import_error",
                repairable=True,
                effective_tier=RiskTier.SAFE,
                reason="Klaviyo script missing or import error — pip install requests; verify script",
            )

        # Rate limit → safe wait + backoff
        if "429" in stderr or "rate" in stderr:
            return AssessResult(
                mode="rate_limit",
                repairable=True,
                effective_tier=RiskTier.SAFE,
                reason="Klaviyo API rate limit (429) — exponential backoff; probe will self-recover",
            )

        # Default fallback: deps check
        return AssessResult(
            mode="import_error",
            repairable=True,
            effective_tier=RiskTier.SAFE,
            reason="Unknown failure; attempting deps install as baseline repair",
        )

    def repair(mode: str, apply: bool = False) -> RepairPlan:
        if mode == "api_key_missing":
            plan = RepairPlan(
                skill_id="klaviyo-canary",
                mode=mode,
                actions=[
                    "MANUAL: Commander logs into Klaviyo account → Settings → API Keys",
                    "Regenerate or create Private API Key with full access",
                    "Update KLAVIYO_API_KEY in /home/john/Thunderbird/.env",
                    "Re-run ci_probe_klaviyo_canary.py to verify",
                ],
            )
            # Runner NEVER reaches apply=True for DESTRUCTIVE — wired for confirm-consumer.
            if apply:
                plan.applied = True
                plan.apply_ok = bool(repair_klaviyo_canary())
            return plan

        if mode == "rate_limit":
            plan = RepairPlan(
                skill_id="klaviyo-canary",
                mode=mode,
                actions=[
                    "wait — Klaviyo rate limit window passes automatically",
                    "re-run ci_probe_klaviyo_canary.py after ≥60s",
                ],
            )
            if not apply:
                return plan
            import time
            time.sleep(60)
            plan.applied = True
            plan.apply_ok = bool(repair_klaviyo_canary())
            return plan

        # import_error (SAFE): pip install + verify
        plan = RepairPlan(
            skill_id="klaviyo-canary",
            mode=mode,
            actions=[
                ".venv/bin/pip install requests -q",
                "verify: python3 -c \"import requests\"",
                "re-run ci_probe_klaviyo_canary.py",
            ],
        )
        if not apply:
            return plan
        try:
            subprocess.run(
                [str(THUNDERBIRD_ROOT / ".venv/bin/pip"),
                 "install", "requests", "-q", "--timeout=60"],
                capture_output=True, timeout=90,
            )
        except Exception:
            pass
        plan.applied = True
        plan.apply_ok = bool(repair_klaviyo_canary())
        return plan

    def verify() -> ProbeState:
        return run_probe(_KLAVIYO_PROBE)

    return explore, assess, repair, verify


# ============================================================================
# SELF-TEST (python3 core/ci/repairs/cluster_g.py)
# ============================================================================

if __name__ == "__main__":
    import sys
    # Ensure repo root importable
    if str(THUNDERBIRD_ROOT) not in sys.path:
        sys.path.insert(0, str(THUNDERBIRD_ROOT))

    # Force module import under canonical package path so REGISTRY is the same
    # object that the decorator writes to.
    try:
        import importlib
        importlib.import_module("core.ci.repairs.cluster_g")
        from core.ci.repairs.schema import REGISTRY as CANON_REGISTRY
    except Exception as e:
        print(f"WARN: canonical import path failed: {e}")
        from core.ci.repairs.schema import REGISTRY as CANON_REGISTRY

    cluster_g_ids = {"qdrant", "email-handling", "gdrive-mx", "evernote-mx", "klaviyo-canary"}
    present = {sid: spec for sid, spec in CANON_REGISTRY.items() if sid in cluster_g_ids}

    print(f"\nCluster G — RepairSpec REGISTRY ({len(present)}/5 skills registered):")
    for sid in sorted(cluster_g_ids):
        if sid in present:
            spec = present[sid]
            print(f"  OK  {sid:20s}  tier={spec.risk_tier.value}")
        else:
            print(f"  MISSING  {sid}")

    missing = cluster_g_ids - set(present.keys())
    if missing:
        print(f"\nFAIL: missing skills: {missing}")
        sys.exit(1)

    print("\nAll 5 Cluster G capabilities registered. Sterling-fleet G · 2026-07-02")
    sys.exit(0)
