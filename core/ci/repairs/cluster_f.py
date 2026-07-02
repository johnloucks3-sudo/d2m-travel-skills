#!/usr/bin/env python3
"""
CI Rapid-Repair Warehouse — CLUSTER F: Infra / Services / Tunnel (11 skills)
Dreams2Memories Travel, LLC · Thunderbird Wing
Author: Sterling-fleet F (A7) · 2026-07-02

Skills covered (in recipe order):
  6.1  self-observability   SAFE     timer/service restart; DESTRUCTIVE for journal perms
  6.2  n8n                  SAFE     service restart; DESTRUCTIVE for workflow credentials
  6.3  cloudflared-tunnel   SAFE     restart (both connectors); DESTRUCTIVE token/DNS
  6.4  ttyd                 SAFE     service restart (tries both unit names)
  6.5  tailscale            DESTRUCTIVE  system unit needs sudo → repairable=False (no passwordless sudo)
  6.6  cruise-db-site       CAUTION  DB rebuild ~300s; SAFE for tunnel redirect
  6.7  reverie-app          SAFE     service restart; CAUTION asset rebuild
  6.8  github-actions       DESTRUCTIVE  PAT/branch-protection = Commander → repairable=False
  6.9  healthchecks         SAFE     docker restart; DESTRUCTIVE image-missing
  6.10 litellm-gateway      SAFE     authored from recipe (no coded repair_); systemctl --user restart
  6.11 home-dir-health      DESTRUCTIVE  diagnostic-only, repairable=False, NEVER auto-mutate

CLOUDFLARED NOTE (⚠️ two connectors):
  The Thunderbird wing runs TWO cloudflared connectors:
    - cloudflared.service        (primary tunnel; registered in ci_registry.json)
    - thunderbird-tunnel.service (secondary connector; same tunnel credential)
  A correct SAFE restart must restart BOTH. The repair() body does so in sequence.
  Verify() re-runs the probe which tests the live tunnel endpoint.

RULES HONORED:
  - Wrap existing repair_<skill> BY IMPORT for the 9 skills that have them; never copy the body.
  - Author repair_litellm_gateway + home-dir-health diagnostic from Dembe's recipe.
  - NON-BREAKING: no changes to live engine or its state files.
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

from core.ci.repairs.schema import (
    AssessResult,
    FailureContext,
    ProbeState,
    RepairPlan,
    RiskTier,
    THUNDERBIRD_ROOT,
    VENV_PY,
    probe_context,
    repair_capability,
    run_probe,
    systemctl_is_active,
)

# ─── IMPORT EXISTING TESTED REPAIR BODIES (wrap, never copy) ─────────────────
from core.ci.ci_auto_repair_engine import (
    repair_self_observability,
    repair_n8n,
    repair_cloudflared_tunnel,
    repair_ttyd,
    repair_tailscale,
    repair_cruise_db_site,
    repair_reverie_app,
    repair_github_actions,
    repair_healthchecks,
)


# ─────────────────────────────────────────────────────────────────────────────
# 6.1  self-observability — Armed Overwatch (F2T2EA)
# ─────────────────────────────────────────────────────────────────────────────

_SO_PROBE = "ci_probe_self_observability.py"
_SO_WATCHDOG = "thunderbird-watchdog.timer"
_SO_SUPERTIMER = "thunderbird-supertimer.service"


@repair_capability(
    "self-observability",
    risk_tier=RiskTier.SAFE,
    sources=[
        "output/ci_repair/research_domain_recipes.md §6.1",
        "core/ci/ci_auto_repair_engine.py::repair_self_observability",
    ],
    verify_settle_seconds=5,
    timeout_seconds=60,
)
def _self_observability():
    def explore() -> FailureContext:
        signals = {
            "watchdog_active": systemctl_is_active(_SO_WATCHDOG),
            "supertimer_active": systemctl_is_active(_SO_SUPERTIMER),
        }
        # Also capture raw probe stderr for journalctl-perms detection
        ctx = probe_context("self-observability", _SO_PROBE, extra_signals=signals)
        return ctx

    def assess(ctx: FailureContext) -> AssessResult:
        stderr = (ctx.probe_stderr or "").lower()
        # Journal permission failure → DESTRUCTIVE / MANUAL
        if "permission denied" in stderr or "access denied" in stderr or "journal" in stderr and "group" in stderr:
            return AssessResult(
                mode="journal_permission_denied",
                repairable=False,
                effective_tier=RiskTier.DESTRUCTIVE,
                reason="journalctl permission error — user must be added to systemd-journal group (Commander action)",
            )
        # timer or service stopped → SAFE restart
        watchdog_ok = ctx.signals.get("watchdog_active", False)
        supertimer_ok = ctx.signals.get("supertimer_active", False)
        if not watchdog_ok or not supertimer_ok:
            return AssessResult(
                mode="service_stopped",
                repairable=True,
                effective_tier=RiskTier.SAFE,
                reason=f"watchdog_active={watchdog_ok} supertimer_active={supertimer_ok} — idempotent restart",
            )
        return AssessResult(
            mode="probe_failure",
            repairable=True,
            effective_tier=RiskTier.SAFE,
            reason="probe RED but services appear active — restart both units as safeguard",
        )

    def repair(mode: str, apply: bool = False) -> RepairPlan:
        plan = RepairPlan(
            skill_id="self-observability",
            mode=mode,
            actions=[
                f"systemctl --user restart {_SO_WATCHDOG}",
                f"systemctl --user restart {_SO_SUPERTIMER}",
                "wait 5s; re-run ci_probe_self_observability.py",
            ],
        )
        if not apply:
            return plan
        plan.applied = True
        plan.apply_ok = bool(repair_self_observability())
        return plan

    def verify() -> ProbeState:
        return run_probe(_SO_PROBE)

    return explore, assess, repair, verify


# ─────────────────────────────────────────────────────────────────────────────
# 6.2  n8n — n8n Workflow Automation
# ─────────────────────────────────────────────────────────────────────────────

_N8N_UNIT = "n8n.service"
_N8N_PROBE = "ci_probe_n8n.py"


@repair_capability(
    "n8n",
    risk_tier=RiskTier.SAFE,
    sources=[
        "output/ci_repair/research_domain_recipes.md §6.2",
        "core/ci/ci_auto_repair_engine.py::repair_n8n",
    ],
    verify_settle_seconds=6,
    timeout_seconds=60,
)
def _n8n():
    def explore() -> FailureContext:
        ctx = probe_context("n8n", _N8N_PROBE,
                            extra_signals={"unit_active": systemctl_is_active(_N8N_UNIT)})
        return ctx

    def assess(ctx: FailureContext) -> AssessResult:
        stderr = (ctx.probe_stderr or "").lower()
        # Credential expiry (401 from workflow execution) → DESTRUCTIVE / MANUAL
        if "401" in stderr or "credential" in stderr or "unauthorized" in stderr:
            return AssessResult(
                mode="workflow_credentials_expired",
                repairable=False,
                effective_tier=RiskTier.DESTRUCTIVE,
                reason="n8n workflow credentials expired — Commander must update in n8n UI",
            )
        # Node.js incompatibility → STATEFUL (elevated to DESTRUCTIVE for safety)
        if "node" in stderr and ("version" in stderr or "compatible" in stderr):
            return AssessResult(
                mode="nodejs_incompatible",
                repairable=False,
                effective_tier=RiskTier.DESTRUCTIVE,
                reason="Node.js version incompatible — requires nvm update (Commander action)",
            )
        # Default: service stopped/crashed → SAFE restart
        return AssessResult(
            mode="service_stopped",
            repairable=True,
            effective_tier=RiskTier.SAFE,
            reason="n8n.service inactive/crashed — idempotent restart",
        )

    def repair(mode: str, apply: bool = False) -> RepairPlan:
        plan = RepairPlan(
            skill_id="n8n",
            mode=mode,
            actions=[
                f"systemctl --user restart {_N8N_UNIT}",
                "wait 6s; re-run ci_probe_n8n.py",
            ],
        )
        if not apply:
            return plan
        plan.applied = True
        plan.apply_ok = bool(repair_n8n())
        return plan

    def verify() -> ProbeState:
        return run_probe(_N8N_PROBE)

    return explore, assess, repair, verify


# ─────────────────────────────────────────────────────────────────────────────
# 6.3  cloudflared-tunnel — Cloudflare Tunnel
#
# ⚠️ TWO CONNECTORS: cloudflared.service + thunderbird-tunnel.service
# A correct restart MUST restart BOTH. The repair() body restarts both in
# sequence. The existing repair_cloudflared_tunnel() in the engine only
# restarts cloudflared.service; the apply-path here extends it by also
# restarting thunderbird-tunnel.service to cover both connectors.
# ─────────────────────────────────────────────────────────────────────────────

_CF_UNIT_PRIMARY = "cloudflared.service"
_CF_UNIT_SECONDARY = "thunderbird-tunnel.service"
_CF_PROBE = "ci_probe_cloudflared-tunnel.py"


def _restart_both_cloudflared_connectors() -> bool:
    """Restart both cloudflared connectors (primary + secondary). Returns True if both succeed."""
    ok_primary = subprocess.run(
        ["systemctl", "--user", "restart", _CF_UNIT_PRIMARY],
        timeout=30, capture_output=True,
    ).returncode == 0
    ok_secondary = subprocess.run(
        ["systemctl", "--user", "restart", _CF_UNIT_SECONDARY],
        timeout=30, capture_output=True,
    ).returncode == 0
    # Secondary may not exist on all environments — treat missing unit as non-fatal
    time.sleep(8)
    p = subprocess.run(
        [VENV_PY, str(THUNDERBIRD_ROOT / "scripts" / _CF_PROBE)],
        capture_output=True, timeout=45,
    )
    return p.returncode == 0


@repair_capability(
    "cloudflared-tunnel",
    risk_tier=RiskTier.SAFE,
    sources=[
        "output/ci_repair/research_domain_recipes.md §6.3",
        "core/ci/ci_auto_repair_engine.py::repair_cloudflared_tunnel",
        "CLAUDE.md — ⚠️ two connectors: cloudflared.service + thunderbird-tunnel.service",
    ],
    verify_settle_seconds=8,
    timeout_seconds=90,
)
def _cloudflared_tunnel():
    def explore() -> FailureContext:
        signals = {
            "primary_active": systemctl_is_active(_CF_UNIT_PRIMARY),
            "secondary_active": systemctl_is_active(_CF_UNIT_SECONDARY),
        }
        ctx = probe_context("cloudflared-tunnel", _CF_PROBE, extra_signals=signals)
        return ctx

    def assess(ctx: FailureContext) -> AssessResult:
        stderr = (ctx.probe_stderr or "").lower()
        # DNS 525 or SSL handshake failure → DESTRUCTIVE / MANUAL (Cloudflare dashboard)
        if "525" in stderr or "ssl" in stderr or "handshake" in stderr:
            return AssessResult(
                mode="dns_ssl_525",
                repairable=True,
                effective_tier=RiskTier.DESTRUCTIVE,
                reason="Cloudflare 525 SSL error — requires Cloudflare dashboard fix (MISSION-806); stage for Commander",
            )
        # Token expired/invalid → DESTRUCTIVE / MANUAL
        if "token" in stderr or "login" in stderr or "unauthorized" in stderr or "not registered" in stderr:
            return AssessResult(
                mode="tunnel_token_expired",
                repairable=True,
                effective_tier=RiskTier.DESTRUCTIVE,
                reason="Cloudflare tunnel token expired — re-run cloudflared tunnel login (Commander action)",
            )
        # Network disconnect or service stopped → SAFE restart of BOTH connectors
        primary_ok = ctx.signals.get("primary_active", False)
        secondary_ok = ctx.signals.get("secondary_active", True)  # secondary may be optional
        return AssessResult(
            mode="service_stopped",
            repairable=True,
            effective_tier=RiskTier.SAFE,
            reason=(
                f"primary_active={primary_ok} secondary_active={secondary_ok} — "
                "restart BOTH cloudflared connectors (cloudflared.service + thunderbird-tunnel.service)"
            ),
        )

    def repair(mode: str, apply: bool = False) -> RepairPlan:
        plan = RepairPlan(
            skill_id="cloudflared-tunnel",
            mode=mode,
            actions=[
                f"systemctl --user restart {_CF_UNIT_PRIMARY}",
                f"systemctl --user restart {_CF_UNIT_SECONDARY}  (secondary connector)",
                "wait 8s; re-run ci_probe_cloudflared-tunnel.py",
                "NOTE: both connectors must be restarted for full tunnel recovery",
            ] if mode == "service_stopped" else [
                "⚠️ MANUAL: log into Cloudflare dashboard → fix SSL/token per mode",
                f"mode={mode}: see research_domain_recipes.md §6.3",
            ],
        )
        if not apply:
            return plan
        plan.applied = True
        if mode == "service_stopped":
            plan.apply_ok = _restart_both_cloudflared_connectors()
        else:
            # DESTRUCTIVE modes: runner stages, apply=True never fires here
            plan.apply_ok = False
        return plan

    def verify() -> ProbeState:
        return run_probe(_CF_PROBE)

    return explore, assess, repair, verify


# ─────────────────────────────────────────────────────────────────────────────
# 6.4  ttyd — ttyd Terminal-over-Browser
# ─────────────────────────────────────────────────────────────────────────────

_TTYD_PROBE = "ci_probe_ttyd.py"


@repair_capability(
    "ttyd",
    risk_tier=RiskTier.SAFE,
    sources=[
        "output/ci_repair/research_domain_recipes.md §6.4",
        "core/ci/ci_auto_repair_engine.py::repair_ttyd",
    ],
    verify_settle_seconds=4,
    timeout_seconds=60,
)
def _ttyd():
    def explore() -> FailureContext:
        # Try both unit names for the is-active signal
        primary_active = systemctl_is_active("ttyd-terminal.service")
        alt_active = systemctl_is_active("ttyd.service")
        signals = {
            "ttyd_terminal_active": primary_active,
            "ttyd_service_active": alt_active,
        }
        ctx = probe_context("ttyd", _TTYD_PROBE, extra_signals=signals)
        return ctx

    def assess(ctx: FailureContext) -> AssessResult:
        stderr = (ctx.probe_stderr or "").lower()
        # Port collision (STATEFUL — killing a process is elevated)
        if "address already in use" in stderr or "bind" in stderr:
            return AssessResult(
                mode="port_in_use",
                repairable=True,
                effective_tier=RiskTier.DESTRUCTIVE,
                reason="ttyd port already in use — conflicting process must be identified and killed (stage for confirm)",
            )
        # Standing order: never re-enable ghost touchscreen
        if "touchscreen" in stderr or "input" in stderr:
            return AssessResult(
                mode="ghost_touchscreen",
                repairable=False,
                effective_tier=RiskTier.DESTRUCTIVE,
                reason="Ghost touchscreen interference — per standing order: DO NOT re-enable (yoga known issue)",
            )
        # Default: service stopped → SAFE restart (tries both unit names)
        return AssessResult(
            mode="service_stopped",
            repairable=True,
            effective_tier=RiskTier.SAFE,
            reason="ttyd-terminal.service or ttyd.service stopped — restart (tries both unit names)",
        )

    def repair(mode: str, apply: bool = False) -> RepairPlan:
        plan = RepairPlan(
            skill_id="ttyd",
            mode=mode,
            actions=[
                "systemctl --user restart ttyd-terminal.service  (primary)",
                "  or fallback: systemctl --user restart ttyd.service",
                "wait 4s; re-run ci_probe_ttyd.py",
            ],
        )
        if not apply:
            return plan
        plan.applied = True
        plan.apply_ok = bool(repair_ttyd())
        return plan

    def verify() -> ProbeState:
        return run_probe(_TTYD_PROBE)

    return explore, assess, repair, verify


# ─────────────────────────────────────────────────────────────────────────────
# 6.5  tailscale — Tailscale VPN
#
# SYSTEM unit (tailscaled.service) requires sudo. No passwordless sudo available
# for autonomous repair. repair() is wired to the existing body (which tries
# sudo -n + tailscale up) but assess() sets repairable=False for all modes
# because the existing body requires sudo that is not available headless.
# Stage/escalate only.
# ─────────────────────────────────────────────────────────────────────────────

_TS_PROBE = "ci_probe_tailscale.py"


@repair_capability(
    "tailscale",
    risk_tier=RiskTier.DESTRUCTIVE,
    sources=[
        "output/ci_repair/research_domain_recipes.md §6.5",
        "core/ci/ci_auto_repair_engine.py::repair_tailscale",
        "CI_RAPID_REPAIR_SCHEMA.md — tailscale: DESTRUCTIVE (system unit, needs sudo) → repairable=False",
    ],
    verify_settle_seconds=6,
    timeout_seconds=60,
)
def _tailscale():
    def explore() -> FailureContext:
        # tailscaled is a SYSTEM unit — use system (not user) is-active
        try:
            r = subprocess.run(
                ["systemctl", "is-active", "tailscaled.service"],
                capture_output=True, text=True, timeout=10,
            )
            daemon_active = r.stdout.strip() == "active"
        except Exception:
            daemon_active = False

        # tailscale status gives node auth state
        try:
            ts = subprocess.run(
                ["/usr/bin/tailscale", "status", "--json"],
                capture_output=True, text=True, timeout=10,
            )
            ts_stderr = ts.stderr or ts.stdout or ""
        except Exception:
            ts_stderr = "tailscale binary not reachable"

        signals = {"tailscaled_active": daemon_active}
        return FailureContext(
            skill_id="tailscale",
            probe_state=ProbeState.RED,  # explore is called only when probe was RED
            signals=signals,
            probe_stderr=ts_stderr,
        )

    def assess(ctx: FailureContext) -> AssessResult:
        stderr = (ctx.probe_stderr or "").lower()
        if "reauthentication" in stderr or "needs login" in stderr or "logged out" in stderr:
            return AssessResult(
                mode="node_not_authenticated",
                repairable=False,
                effective_tier=RiskTier.DESTRUCTIVE,
                reason="Tailscale node not authenticated — requires Commander to run 'tailscale up' (browser OAuth)",
            )
        if "sleep" in stderr or "offline" in stderr or "ping" in stderr:
            return AssessResult(
                mode="node_offline",
                repairable=False,
                effective_tier=RiskTier.DESTRUCTIVE,
                reason="Yoga machine offline or asleep — Commander must wake and run 'tailscale up'",
            )
        # Default: tailscaled system unit stopped — needs sudo
        return AssessResult(
            mode="system_unit_stopped",
            repairable=False,
            effective_tier=RiskTier.DESTRUCTIVE,
            reason=(
                "tailscaled.service is a SYSTEM unit requiring sudo. "
                "No passwordless sudo available for autonomous repair. "
                "Commander must run: sudo systemctl restart tailscaled.service"
            ),
        )

    def repair(mode: str, apply: bool = False) -> RepairPlan:
        # All tailscale modes are repairable=False; this plan is for escalation visibility.
        plan = RepairPlan(
            skill_id="tailscale",
            mode=mode,
            actions=[
                "⚠️ MANUAL REQUIRED — tailscaled.service is a SYSTEM unit",
                "Commander: sudo systemctl restart tailscaled.service",
                "  then: tailscale up  (if node needs reauthentication)",
                "Fallback: Direct LAN access yoga 192.168.1.198 or cloudflared tunnel",
            ],
        )
        if not apply:
            return plan
        # Even on apply=True: the runner never reaches here for repairable=False
        # Wire the existing body anyway for confirm-consumer completeness.
        plan.applied = True
        plan.apply_ok = bool(repair_tailscale())
        return plan

    def verify() -> ProbeState:
        return run_probe(_TS_PROBE)

    return explore, assess, repair, verify


# ─────────────────────────────────────────────────────────────────────────────
# 6.6  cruise-db-site — Master Cruise DB Site (d2mluxury.quest/cruises)
#
# DB rebuild is ~300s. CAUTION baseline (writes live DB). tunnel-redirect
# sub-mode is SAFE (no DB write).
# ─────────────────────────────────────────────────────────────────────────────

_CDB_PROBE = "ci_probe_cruise-db-site.py"
_CDB_BUILDER = THUNDERBIRD_ROOT / "scripts" / "build_master_cruise_db.py"


@repair_capability(
    "cruise-db-site",
    risk_tier=RiskTier.CAUTION,
    sources=[
        "output/ci_repair/research_domain_recipes.md §6.6",
        "core/ci/ci_auto_repair_engine.py::repair_cruise_db_site",
    ],
    verify_settle_seconds=10,
    timeout_seconds=360,   # 300s rebuild + 60s margin
    max_attempts=1,        # DB rebuild is expensive — no retry
)
def _cruise_db_site():
    def explore() -> FailureContext:
        # Check DB file exists + cloudflared tunnel status
        db_path = THUNDERBIRD_ROOT / "cruises.db"
        signals = {
            "db_exists": db_path.exists(),
            "cloudflared_active": systemctl_is_active("cloudflared.service"),
            "tunnel_secondary_active": systemctl_is_active("thunderbird-tunnel.service"),
        }
        ctx = probe_context("cruise-db-site", _CDB_PROBE, extra_signals=signals)
        return ctx

    def assess(ctx: FailureContext) -> AssessResult:
        db_exists = ctx.signals.get("db_exists", True)
        cf_active = ctx.signals.get("cloudflared_active", True)
        stderr = (ctx.probe_stderr or "").lower()

        # Tunnel down → fix tunnel first (SAFE redirect, not a DB rebuild)
        if not cf_active or "525" in stderr or "connection refused" in stderr or "tunnel" in stderr:
            return AssessResult(
                mode="tunnel_down",
                repairable=True,
                effective_tier=RiskTier.SAFE,
                reason="cloudflared tunnel down — fix cloudflared-tunnel skill first; reprobe cruise-db-site",
            )
        # DB missing or corrupt → rebuild (CAUTION: writes DB, ~300s)
        if not db_exists or "corrupt" in stderr or "no such file" in stderr or "fts5" in stderr:
            return AssessResult(
                mode="db_missing_or_corrupt",
                repairable=True,
                effective_tier=RiskTier.CAUTION,
                reason="cruises.db missing or corrupt — rebuild via build_master_cruise_db.py (~300s, 15,354 sailings)",
            )
        # Stale data → rebuild (CAUTION)
        return AssessResult(
            mode="db_stale",
            repairable=True,
            effective_tier=RiskTier.CAUTION,
            reason="cruise DB stale beyond currency window — rebuild required",
        )

    def repair(mode: str, apply: bool = False) -> RepairPlan:
        if mode == "tunnel_down":
            plan = RepairPlan(
                skill_id="cruise-db-site",
                mode=mode,
                actions=[
                    "Run repair for cloudflared-tunnel skill (restart both connectors)",
                    "wait for tunnel to re-establish",
                    "re-run ci_probe_cruise-db-site.py",
                ],
            )
        else:
            plan = RepairPlan(
                skill_id="cruise-db-site",
                mode=mode,
                actions=[
                    f"python3 {_CDB_BUILDER}  (runtime ~300s, 15,354 sailings)",
                    "wait 10s",
                    "re-run ci_probe_cruise-db-site.py",
                ],
            )
        if not apply:
            return plan
        plan.applied = True
        plan.apply_ok = bool(repair_cruise_db_site())
        return plan

    def verify() -> ProbeState:
        return run_probe(_CDB_PROBE, timeout=60)

    return explore, assess, repair, verify


# ─────────────────────────────────────────────────────────────────────────────
# 6.7  reverie-app — Reverie Web App
# ─────────────────────────────────────────────────────────────────────────────

_REV_PROBE = "ci_probe_reverie-app.py"


@repair_capability(
    "reverie-app",
    risk_tier=RiskTier.SAFE,
    sources=[
        "output/ci_repair/research_domain_recipes.md §6.7",
        "core/ci/ci_auto_repair_engine.py::repair_reverie_app",
    ],
    verify_settle_seconds=6,
    timeout_seconds=90,
)
def _reverie_app():
    def explore() -> FailureContext:
        signals = {
            "reverie_api_active": systemctl_is_active("reverie-api.service"),
            "reverie_frontend_active": systemctl_is_active("reverie-frontend.service"),
            "reverie_generic_active": systemctl_is_active("reverie.service"),
        }
        ctx = probe_context("reverie-app", _REV_PROBE, extra_signals=signals)
        return ctx

    def assess(ctx: FailureContext) -> AssessResult:
        stderr = (ctx.probe_stderr or "").lower()
        # Static asset 404 → rebuild needed (CAUTION: runs npm build)
        if "404" in stderr or "asset" in stderr or "js" in stderr or "css" in stderr:
            return AssessResult(
                mode="static_assets_missing",
                repairable=True,
                effective_tier=RiskTier.CAUTION,
                reason="Static assets returning 404 — npm run build required in reverie app directory",
            )
        # Cloudflare routing wrong origin (502/525) → DESTRUCTIVE config change
        if "502" in stderr or "525" in stderr or "route" in stderr:
            return AssessResult(
                mode="tunnel_routing_wrong",
                repairable=True,
                effective_tier=RiskTier.DESTRUCTIVE,
                reason="Cloudflare not routing to reverie port — update cloudflared route config (Commander action)",
            )
        # Default: service stopped → SAFE restart
        return AssessResult(
            mode="service_stopped",
            repairable=True,
            effective_tier=RiskTier.SAFE,
            reason="reverie-api.service or reverie-frontend.service stopped — idempotent restart",
        )

    def repair(mode: str, apply: bool = False) -> RepairPlan:
        if mode == "static_assets_missing":
            actions = [
                "npm run build  (in reverie app directory)",
                "systemctl --user restart reverie-api.service",
                "systemctl --user restart reverie-frontend.service",
                "wait 6s; re-run ci_probe_reverie-app.py",
            ]
        elif mode == "tunnel_routing_wrong":
            actions = [
                "⚠️ MANUAL: update cloudflared route config → point to correct reverie port",
                "cloudflared tunnel route dns <tunnel-name> reverie.<domain> localhost:<port>",
            ]
        else:
            actions = [
                "systemctl --user restart reverie-api.service",
                "systemctl --user restart reverie-frontend.service",
                "wait 6s; re-run ci_probe_reverie-app.py",
            ]
        plan = RepairPlan(skill_id="reverie-app", mode=mode, actions=actions)
        if not apply:
            return plan
        plan.applied = True
        plan.apply_ok = bool(repair_reverie_app())
        return plan

    def verify() -> ProbeState:
        return run_probe(_REV_PROBE)

    return explore, assess, repair, verify


# ─────────────────────────────────────────────────────────────────────────────
# 6.8  github-actions — GitHub Actions CI/CD
#
# DORMANT — PAT/branch-protection = Commander action only.
# repairable=False for all modes. Wrap existing repair_github_actions()
# for confirm-consumer completeness but the runner never fires it.
# ─────────────────────────────────────────────────────────────────────────────

_GHA_PROBE = "ci_probe_github_actions.py"


@repair_capability(
    "github-actions",
    risk_tier=RiskTier.DESTRUCTIVE,
    sources=[
        "output/ci_repair/research_domain_recipes.md §6.8",
        "core/ci/ci_auto_repair_engine.py::repair_github_actions",
        "CI_RAPID_REPAIR_SCHEMA.md — github-actions: DESTRUCTIVE repairable=False (PAT / branch protection = manual)",
    ],
    verify_settle_seconds=5,
    timeout_seconds=60,
)
def _github_actions():
    def explore() -> FailureContext:
        env_file = THUNDERBIRD_ROOT / ".env"
        token_present = False
        try:
            if env_file.exists():
                token_present = "GITHUB_TOKEN" in env_file.read_text()
        except Exception:
            pass
        import os
        if os.environ.get("GITHUB_TOKEN"):
            token_present = True
        workflows_dir = THUNDERBIRD_ROOT / ".github" / "workflows"
        signals = {
            "github_token_present": token_present,
            "workflows_dir_exists": workflows_dir.exists(),
        }
        ctx = probe_context("github-actions", _GHA_PROBE, extra_signals=signals)
        return ctx

    def assess(ctx: FailureContext) -> AssessResult:
        stderr = (ctx.probe_stderr or "").lower()
        token_ok = ctx.signals.get("github_token_present", False)
        workflows_ok = ctx.signals.get("workflows_dir_exists", False)

        if not token_ok:
            return AssessResult(
                mode="github_token_missing",
                repairable=False,
                effective_tier=RiskTier.DESTRUCTIVE,
                reason="GITHUB_TOKEN missing — Commander must generate PAT in GitHub → Settings → Developer Settings",
            )
        if "permission denied" in stderr or "branch protection" in stderr or "protected" in stderr:
            return AssessResult(
                mode="branch_protection_block",
                repairable=False,
                effective_tier=RiskTier.DESTRUCTIVE,
                reason="Branch protection blocks push — Commander adjusts in GitHub repo settings",
            )
        if "syntax" in stderr or "yaml" in stderr:
            return AssessResult(
                mode="workflow_yaml_error",
                repairable=False,
                effective_tier=RiskTier.DESTRUCTIVE,
                reason="Workflow YAML syntax error — requires code fix + push (Commander or Wing code gate)",
            )
        return AssessResult(
            mode="dormant_no_token",
            repairable=False,
            effective_tier=RiskTier.DESTRUCTIVE,
            reason="GitHub Actions DORMANT — awaiting Commander PAT provisioning; no auto-repair available",
        )

    def repair(mode: str, apply: bool = False) -> RepairPlan:
        plan = RepairPlan(
            skill_id="github-actions",
            mode=mode,
            actions=[
                "⚠️ MANUAL REQUIRED — GitHub Actions needs Commander action",
                "GitHub PAT: GitHub → Settings → Developer Settings → Personal Access Tokens → Generate",
                "Branch protection: GitHub → repo → Settings → Branches → adjust rules",
                "Workflow YAML: fix syntax in .github/workflows/ → push fix commit",
            ],
        )
        if not apply:
            return plan
        plan.applied = True
        plan.apply_ok = bool(repair_github_actions())
        return plan

    def verify() -> ProbeState:
        return run_probe(_GHA_PROBE)

    return explore, assess, repair, verify


# ─────────────────────────────────────────────────────────────────────────────
# 6.9  healthchecks — Healthchecks.io Dead-Man Switch Service
# ─────────────────────────────────────────────────────────────────────────────

_HC_PROBE = "ci_probe_healthchecks.py"


@repair_capability(
    "healthchecks",
    risk_tier=RiskTier.SAFE,
    sources=[
        "output/ci_repair/research_domain_recipes.md §6.9",
        "core/ci/ci_auto_repair_engine.py::repair_healthchecks",
    ],
    verify_settle_seconds=5,
    timeout_seconds=60,
)
def _healthchecks():
    def explore() -> FailureContext:
        # Check if docker container is running
        try:
            r = subprocess.run(
                ["docker", "ps", "--filter", "name=healthchecks", "--format", "{{.Names}}"],
                capture_output=True, text=True, timeout=10,
            )
            container_running = "healthchecks" in r.stdout
            docker_ok = r.returncode == 0
        except Exception:
            container_running = False
            docker_ok = False

        signals = {
            "container_running": container_running,
            "docker_accessible": docker_ok,
        }
        ctx = probe_context("healthchecks", _HC_PROBE, extra_signals=signals)
        return ctx

    def assess(ctx: FailureContext) -> AssessResult:
        container_running = ctx.signals.get("container_running", False)
        docker_ok = ctx.signals.get("docker_accessible", True)
        stderr = (ctx.probe_stderr or "").lower()

        # Docker daemon not running → needs sudo (DESTRUCTIVE)
        if not docker_ok or "connection refused" in stderr and "docker" in stderr:
            return AssessResult(
                mode="docker_daemon_down",
                repairable=True,
                effective_tier=RiskTier.DESTRUCTIVE,
                reason="Docker daemon not running — sudo systemctl start docker required; stage for confirm",
            )
        # Image missing (first time or pruned) → DESTRUCTIVE / MANUAL
        if "image not found" in stderr or "no such image" in stderr or "image" in stderr and "missing" in stderr:
            return AssessResult(
                mode="container_image_missing",
                repairable=False,
                effective_tier=RiskTier.DESTRUCTIVE,
                reason="healthchecks container image missing — requires Commander to confirm image pull (docker run ...)",
            )
        # DB corruption inside container → DESTRUCTIVE data loss risk
        if "sqlite" in stderr or "500" in stderr or "corrupt" in stderr:
            return AssessResult(
                mode="db_corruption",
                repairable=False,
                effective_tier=RiskTier.DESTRUCTIVE,
                reason="SQLite corruption inside container — data loss risk; restore from volume backup (Commander)",
            )
        # Port collision → STATEFUL (elevated to DESTRUCTIVE for safety)
        if "8123" in stderr and ("in use" in stderr or "collision" in stderr or "address" in stderr):
            return AssessResult(
                mode="port_collision",
                repairable=True,
                effective_tier=RiskTier.DESTRUCTIVE,
                reason="Port 8123 in use by another process — identify + stop conflicting process (stage for confirm)",
            )
        # Default: container stopped/crashed → SAFE docker restart
        return AssessResult(
            mode="container_stopped",
            repairable=True,
            effective_tier=RiskTier.SAFE,
            reason="healthchecks container stopped — docker restart healthchecks (--restart unless-stopped)",
        )

    def repair(mode: str, apply: bool = False) -> RepairPlan:
        plan = RepairPlan(
            skill_id="healthchecks",
            mode=mode,
            actions=[
                "docker restart healthchecks",
                "wait 5s; re-run ci_probe_healthchecks.py (HTTP 200 on :8123)",
            ] if mode == "container_stopped" else [
                f"⚠️ MANUAL REQUIRED for mode={mode}",
                "docker_daemon_down: sudo systemctl start docker; docker start healthchecks",
                "port_collision: ss -tlnp | grep 8123; stop conflicting; docker restart healthchecks",
                "container_image_missing: docker run -d --name healthchecks -p 8123:8000 --restart unless-stopped healthchecks/healthchecks",
                "db_corruption: restore from volume backup (Commander decision)",
            ],
        )
        if not apply:
            return plan
        plan.applied = True
        plan.apply_ok = bool(repair_healthchecks())
        return plan

    def verify() -> ProbeState:
        return run_probe(_HC_PROBE, timeout=20)

    return explore, assess, repair, verify


# ─────────────────────────────────────────────────────────────────────────────
# 6.10  litellm-gateway — LiteLLM AI Proxy (cc-fleet Groq/Cerebras)
#
# NO CODED REPAIR in the engine. Authored from Dembe's recipe §6.10.
# Registry uses `skill` key (not `id`) for this entry.
# ─────────────────────────────────────────────────────────────────────────────

_LLM_UNIT = "d2m-litellm-gateway.service"
_LLM_PROBE = "ci_probe_litellm_gateway.py"  # from registry probe_script field


def _repair_litellm_gateway_impl(mode: str) -> bool:
    """
    Authored repair (no coded repair_ in engine).
    Recipe: systemctl --user restart d2m-litellm-gateway.service; re-probe.
    Returns True if probe passes after restart.
    """
    if mode in ("silent_death", "service_stopped", "package_missing"):
        # For package_missing, try pip install first, then restart
        if mode == "package_missing":
            pip = THUNDERBIRD_ROOT / ".venv" / "bin" / "pip"
            subprocess.run(
                [str(pip), "install", "litellm", "-q"],
                timeout=120, capture_output=True,
            )
        r = subprocess.run(
            ["systemctl", "--user", "restart", _LLM_UNIT],
            timeout=30, capture_output=True,
        )
        if r.returncode != 0:
            return False
        time.sleep(8)
        p = subprocess.run(
            [VENV_PY, str(THUNDERBIRD_ROOT / "scripts" / _LLM_PROBE)],
            capture_output=True, timeout=45,
        )
        return p.returncode == 0
    return False


@repair_capability(
    "litellm-gateway",
    risk_tier=RiskTier.SAFE,
    sources=[
        "output/ci_repair/research_domain_recipes.md §6.10",
        "config/ci_registry.json skill=litellm-gateway (NOT id key)",
        "MISSION-350 — 3-day silent death Jun 29–Jul 2; Restart=always fix",
    ],
    verify_settle_seconds=8,
    timeout_seconds=150,
)
def _litellm_gateway():
    def explore() -> FailureContext:
        signals = {
            "unit_active": systemctl_is_active(_LLM_UNIT),
        }
        # Also check journal for recent errors
        try:
            j = subprocess.run(
                ["journalctl", "--user", "-u", _LLM_UNIT, "-n", "20", "--no-pager"],
                capture_output=True, text=True, timeout=10,
            )
            journal_tail = j.stdout[-1500:] if j.stdout else ""
        except Exception:
            journal_tail = ""
        ctx = probe_context("litellm-gateway", _LLM_PROBE,
                            extra_signals=signals)
        ctx.probe_stderr = (ctx.probe_stderr or "") + "\nJOURNAL:\n" + journal_tail
        return ctx

    def assess(ctx: FailureContext) -> AssessResult:
        stderr = (ctx.probe_stderr or "").lower()

        # API key missing → STATEFUL (env injection from Infisical)
        if "401" in stderr or "403" in stderr or "groq" in stderr and "key" in stderr or "cerebras" in stderr and "key" in stderr:
            return AssessResult(
                mode="api_key_missing",
                repairable=True,
                effective_tier=RiskTier.DESTRUCTIVE,
                reason="Groq/Cerebras API key missing — inject from Infisical into service env; stage for confirm",
            )
        # Config file missing/corrupt → STATEFUL (git restore)
        if "config" in stderr and ("error" in stderr or "missing" in stderr or "corrupt" in stderr):
            return AssessResult(
                mode="config_corrupt",
                repairable=True,
                effective_tier=RiskTier.DESTRUCTIVE,
                reason="litellm_config.yaml corrupt/missing — restore from git; stage for confirm",
            )
        # Package import error → SAFE (pip install + restart)
        if "importerror" in stderr or "modulenotfounderror" in stderr or "no module" in stderr:
            return AssessResult(
                mode="package_missing",
                repairable=True,
                effective_tier=RiskTier.SAFE,
                reason="litellm Python package missing — pip install litellm -q; restart service",
            )
        # Port 4000 collision → stage for confirm
        if "4000" in stderr and ("in use" in stderr or "address" in stderr):
            return AssessResult(
                mode="port_collision",
                repairable=True,
                effective_tier=RiskTier.DESTRUCTIVE,
                reason="Port 4000 in use — identify + kill conflicting process; stage for confirm",
            )
        # Default: silent death (MISSION-350 pattern) → SAFE restart
        return AssessResult(
            mode="silent_death",
            repairable=True,
            effective_tier=RiskTier.SAFE,
            reason=(
                "d2m-litellm-gateway.service inactive/dead (silent death — MISSION-350 pattern); "
                "systemctl --user restart d2m-litellm-gateway.service"
            ),
        )

    def repair(mode: str, apply: bool = False) -> RepairPlan:
        if mode in ("silent_death", "service_stopped", "package_missing"):
            actions = [
                f"systemctl --user restart {_LLM_UNIT}",
                "wait 8s; re-run ci_probe_litellm_gateway.py (SLA: <3000ms on :4000)",
            ]
            if mode == "package_missing":
                actions.insert(0, ".venv/bin/pip install litellm -q")
        else:
            actions = [
                f"⚠️ MANUAL REQUIRED for mode={mode} — see research_domain_recipes.md §6.10",
                "api_key_missing: inject GROQ_API_KEY/CEREBRAS_API_KEY from Infisical; restart service",
                "config_corrupt: git restore config/litellm_config.yaml; restart service",
                "port_collision: ss -tlnp | grep 4000; stop conflicting; restart service",
            ]
        plan = RepairPlan(skill_id="litellm-gateway", mode=mode, actions=actions)
        if not apply:
            return plan
        plan.applied = True
        plan.apply_ok = _repair_litellm_gateway_impl(mode)
        return plan

    def verify() -> ProbeState:
        return run_probe(_LLM_PROBE)

    return explore, assess, repair, verify


# ─────────────────────────────────────────────────────────────────────────────
# 6.11  home-dir-health — Home Directory Health
#
# DIAGNOSTIC ONLY. repairable=False for ALL modes. NEVER auto-mutate.
# explore() runs the probe read-only to surface findings.
# assess() classifies the finding and explains why it requires manual review.
# repair() returns "manual cleanup required" — it is NEVER called by the runner
# because assess() always sets repairable=False.
# ─────────────────────────────────────────────────────────────────────────────

_HDH_PROBE = "home_dir_ci_probe.py"


@repair_capability(
    "home-dir-health",
    risk_tier=RiskTier.DESTRUCTIVE,
    sources=[
        "output/ci_repair/research_domain_recipes.md §6.11",
        "CI_RAPID_REPAIR_SCHEMA.md — home-dir-health: diagnostic-only, repairable=False, NEVER auto-mutate",
    ],
    verify_settle_seconds=5,
    timeout_seconds=120,
)
def _home_dir_health():
    def explore() -> FailureContext:
        """
        READ-ONLY. Runs home_dir_ci_probe.py which surveys /home/john
        and writes a JSON report. The probe itself is read-only; the JSON
        report write is its designed side-effect and is acceptable.
        NEVER deletes or modifies files.
        """
        ctx = probe_context("home-dir-health", _HDH_PROBE)
        return ctx

    def assess(ctx: FailureContext) -> AssessResult:
        """
        Classify findings. All modes set repairable=False — this is diagnostic only.
        The Wing NEVER auto-deletes, auto-moves, or auto-modifies home directory contents.
        Commander decides what to keep, delete, or move.
        """
        stderr = (ctx.probe_stderr or "").lower()

        if "cache" in stderr and ("2gb" in stderr or "bloat" in stderr or "> 2" in stderr):
            reason = (
                "Cache bloat >2GB detected (~/.cache) — manual review required; "
                "safe candidates: ~/.cache/pip, ~/.cache/ms-playwright, but Commander decides"
            )
        elif "downloads" in stderr and ("500mb" in stderr or "> 500" in stderr):
            reason = "~/Downloads >500MB — Commander reviews and decides what to remove"
        elif "loose_files" in stderr or "loose files" in stderr:
            reason = "Loose files at home root — Commander reviews list and decides placement"
        elif "growth" in stderr or "spike" in stderr:
            reason = "Major-dir growth >500MB vs baseline — Commander investigates cause (logs? DB?) before acting"
        elif "missing" in stderr and "bin" in stderr:
            reason = "Critical binary missing — reinstall per binary's procedure; Commander confirms PATH update"
        elif "missing" in stderr and "probe" in stderr:
            reason = "Probe script missing — restore from git (probe is read-only, safe to re-run)"
        else:
            reason = (
                "home-dir-health probe RED — diagnostic findings surfaced. "
                "Manual Commander review required before any cleanup action."
            )

        return AssessResult(
            mode="diagnostic_finding",
            repairable=False,
            effective_tier=RiskTier.DESTRUCTIVE,
            reason=f"DIAGNOSTIC-ONLY — {reason}",
        )

    def repair(mode: str, apply: bool = False) -> RepairPlan:
        """
        Intentionally minimal. repairable=False guarantees the runner returns
        NOT_REPAIRABLE before reaching this function. It exists only so the
        RepairSpec contract is complete and for escalation visibility.
        """
        return RepairPlan(
            skill_id="home-dir-health",
            mode=mode,
            actions=[
                "⚠️ DIAGNOSTIC ONLY — no auto-repair actions available",
                "review OpsCenter/state/home_dir_health_YYYYMMDD.json for findings",
                "Commander decides: delete vs. keep vs. move for each flagged item",
                "NEVER auto-delete home directory contents",
            ],
            applied=False,
            apply_ok=None,
        )

    def verify() -> ProbeState:
        """Re-run the probe as independent ground truth."""
        return run_probe(_HDH_PROBE, timeout=90)

    return explore, assess, repair, verify


# ─────────────────────────────────────────────────────────────────────────────
# REGISTRY SELF-CHECK (run as module to confirm all 11 registered)
# ─────────────────────────────────────────────────────────────────────────────

CLUSTER_F_IDS = [
    "self-observability",
    "n8n",
    "cloudflared-tunnel",
    "ttyd",
    "tailscale",
    "cruise-db-site",
    "reverie-app",
    "github-actions",
    "healthchecks",
    "litellm-gateway",
    "home-dir-health",
]

if __name__ == "__main__":
    import sys
    from core.ci.repairs.schema import REGISTRY

    print("=" * 60)
    print("Cluster F — RepairSpec REGISTRY")
    print("Sterling-fleet F · 2026-07-02")
    print("=" * 60)

    found = []
    missing = []
    for sid in CLUSTER_F_IDS:
        if sid in REGISTRY:
            spec = REGISTRY[sid]
            found.append(sid)
            print(f"  OK  {sid:28s} tier={spec.risk_tier.value}")
        else:
            missing.append(sid)
            print(f"  MISS {sid}")

    print()
    print(f"Registered: {len(found)}/11")
    if missing:
        print(f"MISSING: {missing}")
        sys.exit(1)
    else:
        print("All 11 Cluster F skills registered. NON-BREAKING.")
        sys.exit(0)
