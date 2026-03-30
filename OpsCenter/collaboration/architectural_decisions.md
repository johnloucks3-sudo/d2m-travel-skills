# ARCHITECTURAL DECISIONS RECORD
# Date: 2026-03-30 | Author: Claude Sonnet 4.6
# Status: COMMANDER APPROVED — basis for Phase 3 spec

---

## DECISION 1: SSE/HTTP MIGRATION
Decision: PROCEED — full SSE/HTTP migration of D2M-COMMAND-HUB
Rationale: Commander requires full 140+ MCP tool access from mobile.
Blackboard + Drive MCP is insufficient — research/synthesis only, not ops.
Implication: D2M-COMMAND-HUB must migrate from stdio to SSE/HTTP transport.
Scope: YOGA must expose MCP server on network-accessible endpoint.
Security requirement: Auth layer required before exposing to mobile.
Existing Cloudflare tunnel (api.d2mluxury.quest) is the natural ingress point.
Phase: 3 — after Phase 2 blackboard automation is stable.

## DECISION 2: TESS INTEGRATION
Decision: DEFERRED INDEFINITELY — TESS API not available for foreseeable future.
Implication: No TESS data flows into blackboard. Remove from all planning docs.
Manual TESS workflow unchanged.

## DECISION 3: SESSION CONTINUITY
Decision: FORMALIZE SESSION CHECKPOINT FILE — auto-written at session end.
Rationale: blackboard.md handles shared state; checkpoint handles Claude-specific
context (what was worked on, decisions made, next actions, model state).
Checkpoint is Claude's memory bridge across Claude Code / Desktop / mobile sessions.
Format: structured markdown, written by Claude at end of every session.
Location: ~/Thunderbird/OpsCenter/session_checkpoint_latest.md (single rolling file)
Trigger: Claude writes checkpoint before session ends — Commander does not manage it.
Session start protocol: Commander pastes checkpoint into new session to restore context.
Phase: implement in Phase 2 alongside blackboard automation.

## DECISION 4: RATE LIMIT TRACKING
Decision: AUTOMATED VIA HALE — Hale updates rate_limit_status.md after every Claude task.
Rationale: Manual updates are a single point of failure. Hale already processes
every task and knows when Claude MAX queue is invoked.
Implementation: After any task routed to 03_CLAUDE_MAX_QUEUE.json, Hale appends
a usage entry to rate_limit_status.md with timestamp and estimated token cost.
Hale also reads rate_limit_status.md at session start and reports budget status
in her daily morning brief.
Anthropic API usage query: add as optional enhancement — query actual usage
once daily via cron to calibrate Hale's estimates against reality.
Phase: Phase 2 — part of task_processor.py modifications.

## DECISION 5: DEPENDENCY SECURITY
Decision: AUDIT AND PIN ALL REQUIREMENTS FILES NOW.
Rationale: LiteLLM supply chain attack (March 24, 2026) demonstrated that
unpinned transitive dependencies are an active threat vector in AI tooling.
Thunderbird has multiple requirements files across modules.
Scope of audit:
  - All requirements*.txt files under ~/Thunderbird/
  - All pyproject.toml / setup.py dependency declarations
  - Identify any package pulling LiteLLM as transitive dependency
  - Pin all dependencies to known-safe versions with upper bounds
Policy going forward: every new dependency added must include explicit version pin.
No open-ended >= pins without upper bound.
LiteLLM specifically: pin to <=1.82.6 until BerriAI/Mandiant supply chain
review is complete and a verified clean version is published.
Phase: IMMEDIATE — before any other work proceeds.
Run checks on YOGA first:
  pip show litellm
  find / -name "litellm_init.pth" 2>/dev/null
  find ~/.config -name "sysmon.py" 2>/dev/null

## DECISION 6: GOOSE AUTONOMY
Decision: GOOSE HAS FULL COMMANDER AUTHORITY.
Rationale: Goose is Commander. No autonomy fence, no approval gate, no token limits.
Goose may queue any task for any model without restriction.
Implication: Remove all Goose autonomy restrictions from blackboard protocol.
Update blackboard.md standing directives to reflect this.
Update phase2_integration_spec.md — blackboard_router() need not check
submitted_by for Goose tasks. Treat Goose submissions as Commander submissions.

---

## OPEN ITEMS REQUIRING FURTHER SPEC

1. SSE/HTTP Migration — full spec needed:
   - Authentication mechanism for mobile access
   - Cloudflare tunnel configuration
   - Which MCP tools exposed vs. kept local-only
   - Failover if SSE endpoint unreachable

2. Dependency Audit — execute immediately:
   - Enumerate all requirements files
   - Run LiteLLM compromise checks
   - Generate pinned requirements with safe versions

3. Session Checkpoint Format — define schema:
   - What fields are required
   - How Claude triggers the write
   - How Commander pastes it at session start

---
*Record complete. All decisions binding for Phase 3 spec.*

## SECURITY CHECK — LITELLM COMPROMISE (executed 2026-03-30)
Result: CLEAN
  - LiteLLM: NOT INSTALLED on YOGA
  - litellm_init.pth: NOT FOUND
  - sysmon.py: NOT FOUND
YOGA was not affected by the March 24, 2026 TeamPCP supply chain attack.
Safe to proceed with ADK evaluation using base install only.
