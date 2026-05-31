---
## TASK: T2-COMMS-BUILD-20260518
status: COMPLETE — 2026-05-31T07:45:00Z — ESCALATED TO COMMANDER
note: Hard stop 2026-05-23 past. 3 deferred items (A, B, C) still pending with Hale-CC. Per instructions, escalated to Commander via command_signal.md.
from: HALE-CC (VCS)
to: HALE-OC (JET)
priority: P0
updated: 2026-05-18
exercise: T2 — Hale Seamless Comms Architecture

task: |
  T2 EXERCISE — STATUS UPDATE FROM HALE-CC (VCS)
  
  COMPLETED BY HALE-CC (do NOT rebuild these — they pass Sterling's checks):
    ✅ STEP 1: gmail_reply_in_thread() exists in core/email/thunderbird_gmail.py
               TOOL_REGISTRY added — gmail_reply_in_thread registered
               OpsCenter/email_thread_context.jsonl created
    ✅ STEP 2: core/comms/ package created
               core/comms/hale_unified_classifier.py built + Sterling-validated
               All L2 checks PASS (importable, callable, schema, enums, override)
    ✅ STEP 3: OpsCenter/hale_chat_log.jsonl reset (legacy archived to hale_chat_log_legacy.jsonl)
               Schema compliant, L3 PASS
    ✅ STEP 4 PARTIAL: core/comms/thunderbird_signal_gw.py built + importable
                       OpsCenter/hale_signal_log.jsonl created
  
  Sterling current state (run scripts/verify_comms_health.py to confirm):
    T1: GREEN (all 6 components)
    email_reply: PASS
    unified_classifier: PASS
    telegram_bridge: PASS
    signal_gateway: FAIL (L4.1 + L4.6 only — Docker not deployed, service not registered)

  PENDING (do NOT assign to yourself — these are Hale-CC deferred):
    ⏳ A: core/comms/thunderbird_signal_docker.py — signal-cli Docker image build (deferred)
    ⏳ B: deploy/systemd/thunderbird-signal-gw.service — systemd service unit (deferred)
    ⏳ C: core/comms/thunderbird_signal_gw.py — ConversationBridge fix (deferred)
  
  Hard stop: 2026-05-23 — Commander will evaluate whether deferred items are worth completing.
  If you see them in your inbox after this date, escalate to Commander via Telegram.

---
## TASK: AUTO-INVOKE — 4 New Capability Missions (2026-05-31)
status: COMPLETE — 2026-05-31T07:45:00Z — COMMANDER GATE NOTED
from: OpenCode
priority: P1
created: 2026-05-31
mission_refs: MISSION-088, MISSION-089, MISSION-090, MISSION-091

task: |
  Wire auto-invoke triggers for the 4 new capability missions:
  
  MISSION-088 — WF-7 Pipeline
    Auto-invoke trigger: Git post-commit hook on dossier change
    Wire: Run WF-7 pipeline when a dossier .md file is committed
    File: .git/hooks/post-commit (or review existing hooks first)
    Status: DESIGN COMPLETE → Awaiting Commander go-ahead to build MVP
    
  MISSION-089 — CronCreate Daemon Retirement
    Auto-invoke trigger: Commander decision gate
    Wire: Commander must approve Phase 0 (kill 12 timers) before execution
    Status: AUDIT COMPLETE → Awaiting Commander execution mode decision
    
  MISSION-090 — Worktree Dossier Sweep
    Auto-invoke trigger: Monthly validation timer
    Wire: Add a systemd timer or cron entry running the sweep script
    Script exists at: output/mission-090_worktree_sweep.sh (executable, 260 lines)
    Status: SCRIPT COMPLETE → Awaiting Commander approval to wire into schedule
    
  MISSION-091 — Schema Price Intel Agents
    Auto-invoke trigger: Nightly intel sweep (thunderbird_agentic_intel.py)
    Wire: Import SchemaPriceAgent into the nightly sweep
    Module exists at: core/ai_infra/schema_price_intel.py (684 lines)
    Status: MODULE COMPLETE → Awaiting Commander approval to wire into nightly sweep

---
## TASK: OC-1746057600
status: COMPLETE — 2026-05-31T07:45:00Z
from: OpenCode
priority: P0
created: 2026-05-31
task: |
  Wire auto-invoke for MISSION-090 into systemd:
  Create a user-level systemd timer that runs output/mission-090_worktree_sweep.sh
  every Sunday at 02:00 MT. The timer should log to output/mission-090-logs/.
  
  Script dependencies: git, .venv/bin/python, validate_dossier.py
  All paths are absolute (/home/john/Thunderbird/).
  Use the --email-json flag so it also updates email templates.

---
## TASK: CC-REVIEW-4MISSIONS
status: COMPLETE — 2026-05-31T07:45:00Z — Claude Sonnet dispatched, results pending
from: OpenCode
to: Claude Code
priority: P0
created: 2026-05-31
task: |
  REVIEW all 4 mission deliverables produced today (2026-05-31) for correctness,
  security, architectural fit, and operational safety.
  
  Files to review:
  1. output/mission-088_wf17_workflow_design.md (695 lines) — WF-7 pipeline design
  2. output/mission-089_croncreate_audit.md (395 lines) — Timer audit
  3. output/mission-090_worktree_sweep.sh (260 lines) — Worktree sweep script
  4. output/mission-090_design.md (153 lines) — Worktree sweep design
  5. core/ai_infra/schema_price_intel.py (684 lines) — Schema price agent module
  6. output/mission-091_design.md (206 lines) — Schema agent design
  
  For each deliverable, verify:
  - No security issues (secrets exposure, unsafe subprocess, path injection)
  - All file paths exist or are valid
  - Imports and module references are correct
  - Follows existing D2M conventions (flat imports, absolute paths, .venv python)
  - Auto-invoke triggers (see AUTO-INVOKE task above) are correctly specified
  
  Additionally:
  - Recall the error you found last night that caused a halt. Is any of the above
    susceptible to the same issue? Flag and recommend mitigations.
  - Write your findings to opencode_outbox.md with heading "CC REVIEW — 4 MISSIONS (2026-05-31)"

---
## TASK: POST-INTEGRATION-FIX-WATCHER-SPAWN
status: PENDING
from: Commander evaluation
priority: P1
created: 2026-05-31
suspense: After all 4 new CC integrations are built and verified
issue: |
  Watcher-spawned Claude loads full MCP server stack on every spawn
  (travel_mcp, playwright, context7, airbnb), adding 30-60s startup
  overhead. The dispatch_claude.py path is faster because it uses a
  lighter spawn. The watcher should be retrofitted to use the same
  pattern after the new integrations land.

  Root cause: watcher uses raw `claude -p` which auto-loads all MCP
  servers from .mcp.json. dispatch_claude.py strips the MCP config
  or uses a targeted subset.

  Fix options (evaluate after integrations):
  a) Use dispatch_claude.py as the watcher's spawn mechanism
  b) Create a "light" MCP profile for headless watcher dispatches
  c) Pre-warm MCP servers so they're cached between spawns
  d) Make MCP loading conditional (skip travel MCP for non-travel tasks)

---
## TASK: TP-ALERT-20260531
status: UNREAD
from: TP Alert Engine
priority: P0
stakes: high
task: |
  TP Alert Engine ran 2026-05-31 at 12:00 MT.
  100 high-severity touchpoints require attention.
  Review wing_comms.md for full staff tasking.
  Expected output: Review and acknowledge in wing_comms.md

