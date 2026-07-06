#!/usr/bin/env python3
"""
CI Rapid-Repair Warehouse — Cluster H: Comms Channel Coverage (3 skills)
Dreams2Memories Travel, LLC · Thunderbird Wing
Author: Hale (Claude Code) · 2026-07-06

Built same-day as the gap it closes. Commander: "Fix this terrible CI gap
and lack of proactive repair. Think like me." Root cause wasn't a missing
probe alone — it was that Telegram (a primary channel) had ZERO entries in
config/ci_registry.json despite core/monitoring/telegram_bot_healthcheck.py
already detecting a real failure that morning (Dani bot DEAD, SSL handshake
timeout). A working detector existed; it just never fed the CI/repair
system, so a RED never had a chance to trigger repair. This cluster gives
Telegram, AgentMail, and now the two Gmail accounts (the same class of gap,
found in the same audit — "other channels") a real RepairSpec each, so
detection is no longer the end of the story.

Skills authored here (3):
  telegram-relay   SAFE (idempotent gateway service restart) / DESTRUCTIVE
                   repairable=False if the bot token itself is invalid
  agentmail-health  DESTRUCTIVE repairable=False always — no local action can
                   fix a third-party vendor outage; this exists so an
                   AgentMail-wide failure is TRACKED and ESCALATED instead of
                   silently missing, same failure mode as the Telegram gap.
  gmail-accounts   SAFE (token refresh retry) / DESTRUCTIVE repairable=False
                   if the refresh itself fails (revoked grant — Commander
                   must re-consent). johnloucks3 + d2mconcierge accounts had
                   zero direct reachability coverage — "email-handling" only
                   checked a digest-generation script, not the accounts
                   themselves.
"""
from __future__ import annotations

import json
import subprocess

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
)

_PROBE_TELEGRAM = "ci_probe_telegram_relay.py"
_PROBE_AGENTMAIL_C2 = "ci_probe_c2_fabric_roundtrip.py"
_PROBE_GMAIL = "ci_probe_gmail_accounts.py"


# ============================================================================
# H.1  telegram-relay
#      SAFE   : gateway service down/bot unresponsive → idempotent service
#                restart (same pattern as headless-dispatch's oauth-keepalive
#                restart, Cluster C §3.1)
#      DESTR  : getMe returns ok=false with a real API error (e.g. token
#                revoked) → NOT_REPAIRABLE, Commander must issue a new token
# ============================================================================
@repair_capability(
    "telegram-relay",
    risk_tier=RiskTier.SAFE,
    sources=[
        "core/monitoring/telegram_bot_healthcheck.py (existing, pre-dates this repair spec)",
        "hale_decisions.md 2026-07-06 — CI gap incident",
    ],
)
def _telegram_relay():
    def explore() -> FailureContext:
        ctx = probe_context(
            "telegram-relay",
            _PROBE_TELEGRAM,
            extra_signals={
                "gateway_service_active": systemctl_is_active("thunderbird-telegram-gw.service"),
            },
        )
        return ctx

    def assess(ctx: FailureContext) -> AssessResult:
        detail = (ctx.probe_stderr or "").lower()
        if "token" in detail and ("invalid" in detail or "unauthorized" in detail or "401" in detail):
            return AssessResult(
                mode="token_invalid",
                repairable=False,
                effective_tier=RiskTier.DESTRUCTIVE,
                reason="Bot token appears invalid/revoked — Commander must "
                       "issue a new token via @BotFather and update .env",
            )
        return AssessResult(
            mode="service_or_transient_failure",
            repairable=True,
            effective_tier=RiskTier.SAFE,
            reason="Gateway service down or transient API failure (e.g. the "
                   "SSL-handshake-timeout pattern seen 2026-07-06) — idempotent "
                   "service restart",
        )

    def repair(mode: str, apply: bool = False) -> RepairPlan:
        plan = RepairPlan(
            skill_id="telegram-relay",
            mode=mode,
            actions=[
                "systemctl --user restart thunderbird-telegram-gw.service",
                "verify getMe on both D2MC2C and Dani bots",
            ],
        )
        if not apply:
            return plan
        plan.applied = True
        try:
            subprocess.run(
                ["systemctl", "--user", "restart", "thunderbird-telegram-gw.service"],
                timeout=30, check=True,
            )
            plan.apply_ok = True
        except Exception as e:
            plan.apply_ok = False
            plan.note = str(e)[:200]
        return plan

    def verify() -> ProbeState:
        return run_probe(_PROBE_TELEGRAM)

    return explore, assess, repair, verify


# ============================================================================
# H.2  c2-fabric-roundtrip (RepairSpec added — the registry entry already
#      existed from today's earlier build, but had NO RepairSpec, so a RED
#      here would have hit the exact same "no-capability" dead end Telegram
#      hit). DESTR always: no local service to restart for a third-party
#      vendor outage. This spec exists purely so a real AgentMail-wide
#      failure is TRACKED (history, REPLACE-threshold counting) and
#      ESCALATED to the Commander instead of silently missing.
# ============================================================================
@repair_capability(
    "c2-fabric-roundtrip",
    risk_tier=RiskTier.DESTRUCTIVE,
    sources=[
        "core/email/agentmail_client.py",
        "hale_decisions.md 2026-07-06 — CI gap incident",
    ],
)
def _agentmail_health():
    def explore() -> FailureContext:
        return probe_context("c2-fabric-roundtrip", _PROBE_AGENTMAIL_C2)

    def assess(ctx: FailureContext) -> AssessResult:
        return AssessResult(
            mode="vendor_outage_or_quota",
            repairable=False,
            effective_tier=RiskTier.DESTRUCTIVE,
            reason="No local action fixes an AgentMail-side outage or account "
                   "issue — escalate to Commander/Whetstone. This spec's value "
                   "is TRACKING (history + REPLACE-threshold), not auto-repair.",
        )

    def repair(mode: str, apply: bool = False) -> RepairPlan:
        return RepairPlan(
            skill_id="c2-fabric-roundtrip", mode=mode,
            actions=["No local repair possible — escalate to Commander/Whetstone"],
        )

    def verify() -> ProbeState:
        return run_probe(_PROBE_AGENTMAIL_C2)

    return explore, assess, repair, verify


# ============================================================================
# H.3  gmail-accounts
#      SAFE   : getProfile() failed but refresh_token is present → force a
#                token refresh retry (both accounts already auto-refresh
#                on expiry inside get_commander_credentials/get_persona_
#                credentials when refresh_token exists; this just forces
#                that path with force_refresh=True and re-tests)
#      DESTR  : refresh itself raises (grant revoked / invalid_grant) →
#                NOT_REPAIRABLE, Commander must re-authenticate via OAuth
# ============================================================================
@repair_capability(
    "gmail-accounts",
    risk_tier=RiskTier.SAFE,
    sources=[
        "api/thunderbird_google_auth.py (get_commander_credentials, get_persona_credentials)",
        "hale_decisions.md 2026-07-06 — CI gap incident, 'other channels' follow-up",
    ],
)
def _gmail_accounts():
    def explore() -> FailureContext:
        return probe_context("gmail-accounts", _PROBE_GMAIL)

    def assess(ctx: FailureContext) -> AssessResult:
        detail = (ctx.probe_stderr or "").lower()
        if "invalid_grant" in detail or "revoked" in detail or "unauthorized_client" in detail:
            return AssessResult(
                mode="grant_revoked",
                repairable=False,
                effective_tier=RiskTier.DESTRUCTIVE,
                reason="OAuth grant itself is revoked/invalid — Commander must "
                       "re-authenticate via the OAuth flow, no local fix exists",
            )
        return AssessResult(
            mode="stale_token_or_transient",
            repairable=True,
            effective_tier=RiskTier.SAFE,
            reason="Likely a stale access token — force a refresh retry using "
                   "the existing refresh_token (idempotent, same path both "
                   "accounts already use automatically on normal expiry)",
        )

    def repair(mode: str, apply: bool = False) -> RepairPlan:
        plan = RepairPlan(
            skill_id="gmail-accounts",
            mode=mode,
            actions=[
                "get_commander_credentials(force_refresh=True)",
                "get_persona_credentials(force_refresh=True)",
                "re-verify via ci_probe_gmail_accounts.py",
            ],
        )
        if not apply:
            return plan
        plan.applied = True
        try:
            import sys
            sys.path.insert(0, "/home/john/Thunderbird")
            sys.path.insert(0, "/home/john/Thunderbird/api")
            from thunderbird_google_auth import get_commander_credentials, get_persona_credentials

            get_commander_credentials(force_refresh=True)
            get_persona_credentials(force_refresh=True)
            plan.apply_ok = True
        except Exception as e:
            plan.apply_ok = False
            plan.note = str(e)[:200]
        return plan

    def verify() -> ProbeState:
        return run_probe(_PROBE_GMAIL)

    return explore, assess, repair, verify
