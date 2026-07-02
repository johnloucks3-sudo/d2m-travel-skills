#!/usr/bin/env python3
"""
CI Rapid-Repair Warehouse — Cluster C: AI-Dispatch / Routing / MCP (7 skills)
Dreams2Memories Travel, LLC · Thunderbird Wing
Author: Sterling-fleet C (A7) · 2026-07-02

Skills authored here (6):
  headless-dispatch     SAFE (timer/binary) / DESTRUCTIVE repairable=False (creds missing)
  litellm-routing       SAFE (pip install)  / DESTRUCTIVE repairable=False (API key absent)
  mcp-registry          SAFE (idempotent mcpServers key add)
  opencode-integration  SAFE (service restart / chmod+x binary)
  tech-adoption         SAFE (cache recreate)
  client-path-canary    SAFE (registry recreate)

dani-identity-layer (the 7th Cluster C skill) is the SAFE worked example in
_worked_examples.py, which is imported below so it registers into the shared
REGISTRY before this module adds its own capabilities.  This module does NOT
re-decorate dani-identity-layer — to avoid the silent-overwrite hazard
documented in CI_RAPID_REPAIR_SCHEMA.md §3 authoring caution #1.

NON-BREAKING: new file only.  ci_auto_repair_engine.py is unchanged.
Probe filenames sourced from config/ci_registry.json (basename only — schema
helpers prepend scripts/ automatically).

Sources per skill:
  §3.1 headless-dispatch     → research_domain_recipes.md §3.1
  §3.2 litellm-routing       → research_domain_recipes.md §3.2
  §3.3 mcp-registry          → research_domain_recipes.md §3.3
  §3.4 opencode-integration  → research_domain_recipes.md §3.4
  §3.5 tech-adoption         → research_domain_recipes.md §3.5
  §3.6 client-path-canary    → research_domain_recipes.md §3.6
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

# Bring dani-identity-layer (and credential-keepalive) into the shared REGISTRY.
# MUST import before our own @repair_capability decorators so REGISTRY is
# populated with the worked examples before we add Cluster C entries.
import core.ci.repairs._worked_examples  # noqa: F401  — dani owned here, NOT re-decorated

from core.ci.repairs.schema import (
    AssessResult,
    FailureContext,
    ProbeState,
    RepairPlan,
    RiskTier,
    REGISTRY,
    probe_context,
    repair_capability,
    run_probe,
    systemctl_is_active,
    THUNDERBIRD_ROOT,
    VENV_PY,
)

# Import the EXISTING, TESTED repair bodies — wrap by import, single source,
# no drift.  The apply=True path calls these; the runner never passes apply=True
# for DESTRUCTIVE specs (so only SAFE-mode specs ever reach these bodies live).
from core.ci.ci_auto_repair_engine import (
    repair_headless_dispatch,
    repair_litellm_routing,
    repair_mcp_registry,
    repair_opencode_integration,
    repair_tech_adoption,
    repair_client_path_canary,
)

# ---------------------------------------------------------------------------
# Probe filenames (basename only — run_probe / probe_context prepend scripts/)
# Taken directly from config/ci_registry.json health_probe values.
# ---------------------------------------------------------------------------
_PROBE_HEADLESS    = "ci_probe_headless_dispatch.py"
_PROBE_LITELLM     = "ci_probe_litellm_routing.py"
_PROBE_MCP         = "ci_probe_mcp_registry.py"
_PROBE_OPENCODE    = "ci_probe_opencode_integration.py"
_PROBE_TECH        = "ci_probe_tech_harvest.py"       # NB: NOT ci_probe_tech_adoption.py
_PROBE_CANARY      = "ci_probe_client_path_canary.py"


# ============================================================================
# 3.1  headless-dispatch
#      SAFE   : timer/binary failure  → restart oauth-keepalive.timer (idempotent)
#      DESTR  : creds file missing    → NOT_REPAIRABLE (no wing action; Commander
#                                       must re-auth Claude Code manually)
# ============================================================================

@repair_capability(
    "headless-dispatch",
    risk_tier=RiskTier.SAFE,
    sources=[
        "output/ci_repair/research_domain_recipes.md §3.1",
        "core/ci/ci_auto_repair_engine.py::repair_headless_dispatch",
    ],
    timeout_seconds=60,
    verify_settle_seconds=5,
)
def _headless_dispatch():
    def explore() -> FailureContext:
        cred_file = Path.home() / ".claude" / ".credentials.json"
        claude_bin = Path("/home/john/.local/bin/claude")
        binary_ok = False
        if claude_bin.exists():
            try:
                r = subprocess.run(
                    [str(claude_bin), "--version"],
                    capture_output=True, text=True, timeout=10,
                )
                binary_ok = r.returncode == 0
            except Exception:
                pass
        ctx = probe_context(
            "headless-dispatch",
            _PROBE_HEADLESS,
            extra_signals={
                "cred_file_present": cred_file.exists(),
                "binary_present":    claude_bin.exists(),
                "binary_responds":   binary_ok,
                "timer_active":      systemctl_is_active("claude-oauth-keepalive.timer"),
            },
        )
        return ctx

    def assess(ctx: FailureContext) -> AssessResult:
        if not ctx.signals.get("cred_file_present", True):
            # Credentials file gone → no wing action exists.
            return AssessResult(
                mode="creds_file_missing",
                repairable=False,
                effective_tier=RiskTier.DESTRUCTIVE,
                reason=(
                    "~/.claude/.credentials.json missing — "
                    "Commander must re-authenticate Claude Code manually"
                ),
            )
        # Timer stopped, binary unresponsive, or probe RED → SAFE restart.
        return AssessResult(
            mode="timer_or_binary_failure",
            repairable=True,
            effective_tier=RiskTier.SAFE,
            reason=(
                "claude-oauth-keepalive.timer stopped or binary unresponsive "
                "— idempotent timer restart"
            ),
        )

    def repair(mode: str, apply: bool = False) -> RepairPlan:
        plan = RepairPlan(
            skill_id="headless-dispatch",
            mode=mode,
            actions=[
                "systemctl --user restart claude-oauth-keepalive.timer",
                "verify ~/.claude/.credentials.json exists",
                "verify /home/john/.local/bin/claude --version responds",
            ],
        )
        if not apply:
            return plan
        plan.applied = True
        plan.apply_ok = bool(repair_headless_dispatch())
        return plan

    def verify() -> ProbeState:
        return run_probe(_PROBE_HEADLESS)

    return explore, assess, repair, verify


# ============================================================================
# 3.2  litellm-routing
#      SAFE   : package missing / import error → pip install litellm (idempotent)
#      DESTR  : API key absent (401 in probe)  → NOT_REPAIRABLE (key must be set
#                                                by Commander in .env / Infisical)
# ============================================================================

@repair_capability(
    "litellm-routing",
    risk_tier=RiskTier.SAFE,
    sources=[
        "output/ci_repair/research_domain_recipes.md §3.2",
        "core/ci/ci_auto_repair_engine.py::repair_litellm_routing",
    ],
    timeout_seconds=120,    # pip install can take ~90s
    verify_settle_seconds=5,
)
def _litellm_routing():
    def explore() -> FailureContext:
        # Check whether litellm is importable in the venv and capture any
        # 401 / api-key-absent signals from the probe stderr.
        import_ok = False
        try:
            r = subprocess.run(
                [VENV_PY, "-c", "import litellm; print('OK')"],
                capture_output=True, text=True, timeout=15,
            )
            import_ok = r.returncode == 0 and "OK" in r.stdout
        except Exception:
            pass
        ctx = probe_context(
            "litellm-routing",
            _PROBE_LITELLM,
            extra_signals={"litellm_importable": import_ok},
        )
        return ctx

    def assess(ctx: FailureContext) -> AssessResult:
        stderr = (ctx.probe_stderr or "").lower()
        if "401" in stderr or "api key" in stderr or "apikey" in stderr or "unauthorized" in stderr:
            # API key absent or invalid → nothing the wing can do autonomously.
            return AssessResult(
                mode="api_key_missing",
                repairable=False,
                effective_tier=RiskTier.DESTRUCTIVE,
                reason=(
                    "LiteLLM returned 401 / API key missing — "
                    "Commander must set key in .env or Infisical"
                ),
            )
        # Package not installed or import broken → pip install is idempotent.
        return AssessResult(
            mode="package_missing_or_import_error",
            repairable=True,
            effective_tier=RiskTier.SAFE,
            reason="litellm package absent or import broken — pip install litellm",
        )

    def repair(mode: str, apply: bool = False) -> RepairPlan:
        plan = RepairPlan(
            skill_id="litellm-routing",
            mode=mode,
            actions=[
                ".venv/bin/pip install litellm -q --timeout=60",
                "verify: python3 -c 'import litellm; print(\"OK\")'",
            ],
        )
        if not apply:
            return plan
        plan.applied = True
        plan.apply_ok = bool(repair_litellm_routing())
        return plan

    def verify() -> ProbeState:
        return run_probe(_PROBE_LITELLM)

    return explore, assess, repair, verify


# ============================================================================
# 3.3  mcp-registry
#      SAFE   : mcpServers key absent from ~/.claude/settings.json → idempotent add
#      (No DESTRUCTIVE mode: corrupt JSON falls through to SAFE recreate;
#       no credential exposure; the schema change is a no-op if key already exists.)
# ============================================================================

_SETTINGS_FILE = Path.home() / ".claude" / "settings.json"

@repair_capability(
    "mcp-registry",
    risk_tier=RiskTier.SAFE,
    sources=[
        "output/ci_repair/research_domain_recipes.md §3.3",
        "core/ci/ci_auto_repair_engine.py::repair_mcp_registry",
    ],
    timeout_seconds=30,
    verify_settle_seconds=3,
)
def _mcp_registry():
    def explore() -> FailureContext:
        settings_ok = False
        has_key = False
        if _SETTINGS_FILE.exists():
            try:
                data = json.loads(_SETTINGS_FILE.read_text())
                settings_ok = True
                has_key = "mcpServers" in data
            except Exception:
                pass  # JSON corrupt → settings_ok stays False
        ctx = probe_context(
            "mcp-registry",
            _PROBE_MCP,
            extra_signals={
                "settings_file_exists": _SETTINGS_FILE.exists(),
                "settings_json_valid":  settings_ok,
                "mcp_servers_key_present": has_key,
            },
        )
        return ctx

    def assess(ctx: FailureContext) -> AssessResult:
        # All failure modes are SAFE-IDEMPOTENT: add the missing key or
        # recreate the settings file.  HTTP 406 on /mcp is a known-good
        # sentinel per the registry note — the probe handles it correctly.
        return AssessResult(
            mode="mcp_servers_key_missing_or_settings_corrupt",
            repairable=True,
            effective_tier=RiskTier.SAFE,
            reason=(
                "mcpServers key absent or settings.json corrupt — "
                "idempotent key add / file recreate"
            ),
        )

    def repair(mode: str, apply: bool = False) -> RepairPlan:
        plan = RepairPlan(
            skill_id="mcp-registry",
            mode=mode,
            actions=[
                "read ~/.claude/settings.json (create {} if absent)",
                "add 'mcpServers: {}' key if not present (no-op if already there)",
                "write back settings.json",
            ],
        )
        if not apply:
            return plan
        plan.applied = True
        plan.apply_ok = bool(repair_mcp_registry())
        return plan

    def verify() -> ProbeState:
        return run_probe(_PROBE_MCP)

    return explore, assess, repair, verify


# ============================================================================
# 3.4  opencode-integration
#      SAFE   : service stopped / binary not executable → restart + chmod +x
#      (No DESTRUCTIVE mode: API key errors are not reported by the probe as
#       401 signals here — model-quota exhaustion routes to SAFE STATEFUL notify
#       path in the engine body, not a credential rotation.)
# ============================================================================

_OPENCODE_SERVICE = "opencode-spsa-monitor.service"

@repair_capability(
    "opencode-integration",
    risk_tier=RiskTier.SAFE,
    sources=[
        "output/ci_repair/research_domain_recipes.md §3.4",
        "core/ci/ci_auto_repair_engine.py::repair_opencode_integration",
    ],
    timeout_seconds=60,
    verify_settle_seconds=5,
)
def _opencode_integration():
    def explore() -> FailureContext:
        spsa_active = systemctl_is_active(_OPENCODE_SERVICE)
        # Check binary presence
        opencode_bin = Path.home() / ".opencode" / "bin" / "opencode"
        binary_in_home = opencode_bin.exists()
        # Also try PATH
        in_path = False
        try:
            r = subprocess.run(
                ["which", "opencode"], capture_output=True, text=True, timeout=5,
            )
            in_path = r.returncode == 0
        except Exception:
            pass
        ctx = probe_context(
            "opencode-integration",
            _PROBE_OPENCODE,
            extra_signals={
                "spsa_monitor_active": spsa_active,
                "binary_in_home_dir":  binary_in_home,
                "binary_in_path":      in_path,
            },
        )
        return ctx

    def assess(ctx: FailureContext) -> AssessResult:
        return AssessResult(
            mode="service_stopped_or_binary_not_executable",
            repairable=True,
            effective_tier=RiskTier.SAFE,
            reason=(
                f"opencode-spsa-monitor.service inactive or binary not executable "
                f"— service restart + chmod +x"
            ),
        )

    def repair(mode: str, apply: bool = False) -> RepairPlan:
        plan = RepairPlan(
            skill_id="opencode-integration",
            mode=mode,
            actions=[
                "chmod +x ~/.opencode/bin/opencode (if present)",
                f"systemctl --user restart {_OPENCODE_SERVICE}",
                "verify opencode --version responds rc=0",
            ],
        )
        if not apply:
            return plan
        plan.applied = True
        plan.apply_ok = bool(repair_opencode_integration())
        return plan

    def verify() -> ProbeState:
        return run_probe(_PROBE_OPENCODE)

    return explore, assess, repair, verify


# ============================================================================
# 3.5  tech-adoption
#      SAFE   : harvest cache file missing or corrupt → recreate empty stub
#               (writing a minimal JSON stub is idempotent / no data loss)
# ============================================================================

_HARVEST_FILE = (
    THUNDERBIRD_ROOT / "intel" / "thunderbird_nightly_tech_harvest_latest.json"
)

@repair_capability(
    "tech-adoption",
    risk_tier=RiskTier.SAFE,
    sources=[
        "output/ci_repair/research_domain_recipes.md §3.5",
        "core/ci/ci_auto_repair_engine.py::repair_tech_adoption",
    ],
    timeout_seconds=90,    # probe re-runs harvest which may take time
    verify_settle_seconds=5,
)
def _tech_adoption():
    def explore() -> FailureContext:
        file_exists = _HARVEST_FILE.exists()
        json_valid = False
        item_count = 0
        if file_exists:
            try:
                data = json.loads(_HARVEST_FILE.read_text())
                json_valid = True
                item_count = len(data.get("items", []))
            except Exception:
                pass
        ctx = probe_context(
            "tech-adoption",
            _PROBE_TECH,
            extra_signals={
                "harvest_file_exists": file_exists,
                "harvest_json_valid":  json_valid,
                "harvest_item_count":  item_count,
            },
        )
        return ctx

    def assess(ctx: FailureContext) -> AssessResult:
        return AssessResult(
            mode="harvest_cache_missing_or_corrupt",
            repairable=True,
            effective_tier=RiskTier.SAFE,
            reason=(
                "tech harvest cache missing or JSON corrupt — "
                "recreate empty stub and re-run probe"
            ),
        )

    def repair(mode: str, apply: bool = False) -> RepairPlan:
        plan = RepairPlan(
            skill_id="tech-adoption",
            mode=mode,
            actions=[
                f"mkdir -p {_HARVEST_FILE.parent}",
                f'create {_HARVEST_FILE} with {{"ts": "<now>", "items": []}} if missing',
                "re-run ci_probe_tech_harvest.py to populate cache",
            ],
        )
        if not apply:
            return plan
        plan.applied = True
        plan.apply_ok = bool(repair_tech_adoption())
        return plan

    def verify() -> ProbeState:
        return run_probe(_PROBE_TECH)

    return explore, assess, repair, verify


# ============================================================================
# 3.6  client-path-canary
#      SAFE   : registry file missing or corrupt → create empty stub (idempotent)
# ============================================================================

_CANARY_FILE = THUNDERBIRD_ROOT / "config" / "client_path_canary_registry.json"

@repair_capability(
    "client-path-canary",
    risk_tier=RiskTier.SAFE,
    sources=[
        "output/ci_repair/research_domain_recipes.md §3.6",
        "core/ci/ci_auto_repair_engine.py::repair_client_path_canary",
    ],
    timeout_seconds=30,
    verify_settle_seconds=3,
)
def _client_path_canary():
    def explore() -> FailureContext:
        file_exists = _CANARY_FILE.exists()
        json_valid = False
        if file_exists:
            try:
                json.loads(_CANARY_FILE.read_text())
                json_valid = True
            except Exception:
                pass
        ctx = probe_context(
            "client-path-canary",
            _PROBE_CANARY,
            extra_signals={
                "registry_file_exists": file_exists,
                "registry_json_valid":  json_valid,
            },
        )
        return ctx

    def assess(ctx: FailureContext) -> AssessResult:
        return AssessResult(
            mode="registry_missing_or_corrupt",
            repairable=True,
            effective_tier=RiskTier.SAFE,
            reason=(
                "client-path canary registry absent or corrupt — "
                'create empty {"canary_tools": [], "updated": "<now>"}'
            ),
        )

    def repair(mode: str, apply: bool = False) -> RepairPlan:
        plan = RepairPlan(
            skill_id="client-path-canary",
            mode=mode,
            actions=[
                f"mkdir -p {_CANARY_FILE.parent}",
                f'write {_CANARY_FILE}: {{"canary_tools": [], "updated": "<now>"}} if missing/corrupt',
                "verify JSON parses cleanly",
            ],
        )
        if not apply:
            return plan
        plan.applied = True
        plan.apply_ok = bool(repair_client_path_canary())
        return plan

    def verify() -> ProbeState:
        return run_probe(_PROBE_CANARY)

    return explore, assess, repair, verify


# ============================================================================
# Module self-test  (python3 -m core.ci.repairs.cluster_c)
# ============================================================================

if __name__ == "__main__":
    import sys
    print(f"REGISTRY contains {len(REGISTRY)} capabilities:")
    for sid, spec in sorted(REGISTRY.items()):
        print(f"  {sid:30s}  tier={spec.risk_tier.value}")

    cluster_c_ids = {
        "headless-dispatch",
        "litellm-routing",
        "mcp-registry",
        "opencode-integration",
        "tech-adoption",
        "client-path-canary",
        "dani-identity-layer",
    }
    missing = cluster_c_ids - set(REGISTRY)
    if missing:
        print(f"\nFAIL — missing Cluster C skills: {missing}", file=sys.stderr)
        sys.exit(1)
    print(f"\nAll 7 Cluster C skills present. dani-identity-layer: owned by _worked_examples, not re-decorated.")
    sys.exit(0)
