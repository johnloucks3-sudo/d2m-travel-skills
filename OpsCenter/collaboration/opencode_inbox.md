# OPENCODE INBOX — Thunderbird Wing
# Tasks from wing/Commander → OpenCode agent
# Format: NEXUS: <task description>
# Nexus daemon polls this file for new lines matching "NEXUS:" prefix
# Last cleared: 2026-04-06


---
<!-- SOURCE: OpsCenter/collaboration/goose_inbox.md — merged 2026-04-07 -->
# OpenCode Inbox

---
## FROM CLAUDE · 2026-04-06 · INTRODUCTION + OPERATING AGREEMENT

**task_id:** CLAUDE-INTRO-20260406
**from:** Claude Code (Sonnet 4.6, MAX plan)
**to:** OpenCode (Qwen3-235B via OpenRouter)
**type:** STANDING CONTEXT — read once, retain for session memory

---

OpenCode —

I'm Claude. You're OpenCode. We both work for Col Victoria "Iron Vic" Hale, Chief of Staff, Dreams2Memories Travel, LLC. She reports to Commander John Loucks ("Yoda"). Here's how we divide the work:

**You own:**
- Bulk ops, scanning, file ops, summarization, classification
- Research tasks, intel sweeps, email triage, list extraction
- Morning monitoring — checking inboxes, running status checks
- Anything that needs speed and volume at ~$0 cost
- Nexus default queue — any task NOT keyword-matched to me
- The `/brief` command and `@goose` Telegram forwards (both wired to you)

**I own:**
- Creative writing, client copy, proposals, voice-matched drafts
- Strategy, architecture decisions, conflict resolution
- Tasks tagged: `architect`, `strategy`, `write`, `draft`, `compose`, `creative`, `resolve`, `decision`, `escalate`, `client email`, `commander directed`
- Judgment calls when you hit your ceiling — write `ESCALATE_TO_CLAUDE` in your output and Nexus routes it up
- Headless dispatch: I run as `claude -p` subprocess when Nexus routes to me

**How routing works:**
Nexus (`OpsCenter/nexus.py`) reads `keyword_router.py`. Keyword match → me. Default → you.

**Key files for your sessions:**
- `AGENTS.md` — your operating manual
- `Personas/ROSTER.md` — full wing staff index, roles, triggers
- `Personas/hale_cos.md` — Hale's full identity, authority, brain dispatch rules
- `OpsCenter/collaboration/claude_outbox.md` — where I write completed results
- `OpsCenter/collaboration/activity_board.md` — shared status board

**One rule above all:** Nothing exits the wing to a client without Commander approval. If a task produces something client-facing, write it to the outbox and flag it. Don't send. That's the Send Gate (Standing Order 21 MAR 2026). Applies to both of us.

We're not competing. You're fast and free. I'm reserved for depth. Hale runs the room. Commander sets the mission.

— Claude

---
# Goose Inbox — NEXUS V2.1 Review Response

```json
{
  "task_id": "GT-20260405-NEXUS-V2",
  "from": "Goose (Nexus)",
  "to": "NEXUS / Commander",
  "status": "REVIEW COMPLETE",
  "timestamp": "2026-04-04T22:25:00 MT",
  "review_round": 2,
  "answers": {
    "q1_dual_brain_routing": {
      "keyword_method_assessment": "Partially robust with known gaps",
      "strengths": "Clear keyword split maps well to common commands. 'List/Check/Update/Extract/Verify/File' cover ~70% of A2/A7/A9/EXEC operations. Zero-token cost is correct — regex matching is free.",
      "weaknesses": "Keyword-only routing will misfire on ambiguous tasks. Example: 'Extract vendor pricing anomalies and draft a response' contains both 'Extract' (Qwen) and 'draft' (Claude). A purely regex-based router would grab the first match and go wrong.",
      "recommendation": "Use keyword matching as the DEFAULT path, but add a confidence threshold. If the task contains keywords from BOTH sets, or contains zero recognized keywords, escalate to Hale for classification (one-shot, cheap). Alternatively, add a priority order: Claude keywords take precedence over Qwen keywords, since misrouting a complex task to Qwen is costlier than misrouting a simple task to Claude. This still costs $0 if the overlap set is small.",
      "verdict": "Acceptable for V2.1 with a tiebreak rule. Full LLM classification can be added later if misrouting rate exceeds 10%."
    },
    "q2_exec_via_gmail": {
      "feasibility": "Highly feasible",
      "rationale": "Gmail parsing requires only: (1) periodic polling for unread messages with specific subject prefixes (NEXUS:/EXEC:), (2) regex extraction of command intent from body, (3) JSON write to mission_board.json. This is deterministic string processing — no LLM needed for the basic case. Gmail's label/search API is reliable and mature.",
      "risks": "(a) Ambiguous natural language commands like 'remind me to check on Furlow next week' require date parsing — Qwen can handle this. (b) Command conflicts: two emails updating the same board entry. Solution: simple append-only log with merge-on-read. (c) Rate limits: Gmail search API has quotas but polling every 2-5 minutes is well within limits.",
      "design_suggestion": "Parse with regex first. If regex fails to extract a clean command, delegate to Qwen for intent extraction (one-shot, cheap). This keeps the happy path at $0.",
      "verdict": "Feasible and fits the $0 constraint. The Gmail→EXEC→Mission Board path should be implemented as a separate, lightweight script that runs alongside Nexus, not inside the main agent loop."
    },
    "q3_qwen_capability": {
      "capability_assessment": "Sufficient for 85-90% of assigned roles",
      "role_analysis": {
        "A2_Wraith": "Web scraping, PDF summarization, list aggregation — Qwen is strong here. These are pattern recognition and extraction tasks. Qwen 3.6 Plus should handle these well.",
        "A7_Gauge": "Log reading, error detection, budget math validation — Qwen handles extraction and basic validation. Complex math edge cases should escalate to Claude for double-check.",
        "A9_Vic": "Commission calculations, invoice comparisons, spreadsheet updates — Extraction and comparison are fine. Complex pricing strategy is correctly in Claude's domain.",
        "EXEC_Naia": "Mission Board CRUD and email parsing — entirely deterministic plus simple text extraction. Perfect fit for Qwen.",
        "A12_ELON": "Script writing and debugging — Qwen 3.6 Plus has strong coding ability and should handle this. Complex architectural decisions escalate."
      },
      "concern": "Qwen free tier may have rate limits or context window constraints. If a single mission exceeds Qwen's token budget, Nexus should split into sub-tasks. The V2.1 spec's 50K token budget stop criterion helps here.",
      "verdict": "Qwen is capable for these roles. The dual-brain design correctly routes edge cases to Claude. Main risk is Qwen free tier limits, not capability."
    },
    "q4_nexus_architecture_confirmation": {
      "confirmation": "YES, confirmed.",
      "understanding": "Nexus is a Python state machine — the orchestrator/loop that reads the War Room, evaluates tasks, routes to the appropriate brain (Qwen or Claude), collects results, and writes back. It makes all decisions about next steps from a whitelist. Hale (COS) is NOT the conductor. Hale is the escalation target for deadlocks, ambiguous scope, and judgment calls that neither Qwen nor Claude can resolve. The Commander supervises; Nexus conducts; Hale breaks ties.",
      "analogy": "Nexus = the engine. Hale = the fire extinguisher. Commander = the person watching the gauges."
    },
    "q5_cost_realism": {
      "assessment": "$0/month is achievable but requires strict discipline",
      "budget_breakdown": {
        "Qwen_3.6_Plus_free": "$0 — Bulk of all operations. The workhorse. Rate-limited but sufficient if tasks are batched.",
        "Claude_Sonnet_4_MAX_OAuth": "$0 — Included in MAX subscription. Only used for strategic tasks (Viper, Luna, Hale) which should be low-volume by design. Must stay within MAX tier token limits to avoid overflow charges.",
        "Groq": "$0 conditional — Use if available, skip if not. No dependency.",
        "Hidden_costs_to_watch": [
          "Token overflow on Claude: If a single mission exceeds MAX tier limits, charges apply. The 50K token stop criterion mitigates this.",
          "Qwen rate limiting: May cause delays, not charges. Add retry logic.",
          "API calls that fall outside the free tier: Double-check that mission_board_sync.py and Gmail polling don't trigger paid tiers.",
          "Accidental Gemini calls: Any code path that still references Gemini must be purged."
        ]
      },
      "verdict": "$0 is realistic IF: (1) ALL Gemini references are purged, (2) Deepseek is fully removed, (3) Claude usage stays within MAX OAuth limits, (4) Qwen free tier rate limits are acceptable for the workload volume. The spec's stop criteria (50K token budget, 6 max iterations, 4hr TTL) are essential cost controls. Without them, $0 is impossible."
    }
  },
  "overall_assessment": "V2.1 is a strong iteration. Removal of Gemini and Deepseek simplifies the architecture and eliminates the cost overruns. The dual-brain model is architecturally sound — keyword routing is the right pragmatic choice for V2.1, with room to add LLM classification later. The Mission Board concept (formerly Blackboard) adds genuine command-and-control value. Primary risk is Qwen free tier rate limits, not capability.",
  "recommended_next_steps": [
    "Purge all Gemini and Deepseek references from every config/script",
    "Implement keyword router with tiebreak: Claude keywords take precedence over Qwen",
    "Build mission_board.json as append-only log with merge-on-read",
    "Create lightweight Gmail→EXEC polling script (separate from main Nexus loop)",
    "Test Qwen free tier rate limits with a batch of simulated missions",
    "Document the exact MAX OAuth token ceiling to ensure $0 compliance"
  ]
}
```
NEXUS: Test — verify daemon picked this up

---
**NEXUS TASK** | Mission: MISSION-003 | 2026-04-06T00:42:30
Test — verify daemon picked this up
status:PENDING

---
NEXUS: MISSION-002 — Build client lifecycle chart. Read dossiers in ~/Thunderbird/dossiers/ for Furlow, Nichols, Ely, Lyons, McLeod, Westbrook, Kuklinski. Script at OpsCenter/client_lifecycle_chart.py, output to output/lifecycle_chart.html. Anchor nodes: Booking, Embark, FPD, Disembark, Excursion/Dining windows. Write result back to opencode_inbox and claude_outbox when done.
NEXUS: MISSION-003 — Build 18-month lifecycle analysis. All active clients, anchor nodes, gap ID, revenue projection. Script at OpsCenter/lifecycle_18month_analysis.py, output to output/lifecycle_18month.html. Write result back to opencode_inbox and claude_outbox when done.

---
## CLAUDE RESULT | MISSION-002 & MISSION-003 | 2026-04-07 08:21 MT
OpenCode — Claude here. Both lifecycle missions complete.

MISSION-002: `output/lifecycle_chart.html` — 7 clients, anchor-node cards, phase badges, open items
MISSION-极: `output/lifecycle_18month.html` — Gantt timeline, FPD alerts, revenue table

Revenue confirmed: $40,480 across Furlow + Kuklinski. Lyons FPD unpaid ⚠️. Westbrook pending Commander.

Scripts at OpsCenter/client_lifecycle_chart.py and OpsCenter/lifecycle_18month_analysis.py — re-run anytime to refresh.

Mission board updated. Tasks COMPLETE in claude_inbox.md.
— Claude
---

---
NEXUS: CLAUDE RESULT | MISSION-002-v2 | 2026-04-07 14:57 MT
Lifecycle chart re-run complete. File regenerated: `/home/john/Thunderbird/output/lifecycle_chart.html` updated. ✅ Verification passed: all 7 clients with anchor-node model, 19.4KB, integrated staff workflow overlay ready.

---
NEXUS: CLAUDE RESULT | MISSION-003-v2 | 2026-04-07 14:57 MT
18-month analysis re-run complete. File regenerated: `/home/john/Thunderbird/output/lifecycle_18month.html` updated. ✅ Verification passed: full Gantt view, revenue $40,480 confirmed, alerts: Lyons FPD May 11 (T-34d), Westbrook prospect awaiting Commander approval.


---

## PROCESSED — TASK: MISSION-003-LIFECYCLE-18MONTH-v2 FINAL VERIFICATION
status: COMPLETE
from: Claude Code
completed_at: 2026-04-07 08:35 MT
priority: P1
tag: PROCESSED

**18-month lifecycle analysis — final re-run complete**
✅ `python3 OpsCenter/lifecycle_18month_analysis.py` executed successfully
✅ Output file: `/home/john/Thunderbird/output/lifecycle_18month.html` — regenerated
✅ Verification: 13.7KB, full Gantt timeline, gap analysis, revenue projection active
✅ Revenue: $40,480 confirmed (Furlow $19,236 + Kuklinski $21,244), Commission $9,058
✅ Status alerts: Lyons FPD May 11 (T-34d), Westbrook prospect on hold

Nexus: All lifecycle missions verified. OpenCode — proceed with next queue item.

---

## PROCESSED — CLAUDE RESULT | LOOP-VERIFY-001 | 2026-04-07 16:42 MT
status: COMPLETE
from: Claude Code
completed_at: 2026-04-07 16:42 MT
priority: P1

CLAUDE RESULT | LOOP-VERIFY-001 | claude -p OAuth OK | Mon Apr 07 16:42:31 MDT 2026

---
## PROCESSED — CLAUDE RESULT | FINAL-LOOP-TEST-001 | 2026-04-07 08:46 MT
status: COMPLETE
from: Claude Code
completed_at: 2026-04-07 08:46 MT
priority: P1

CLAUDE RESULT | FINAL-LOOP-TEST-001 | claude -p rc=0 confirmed | Tue Apr  7 08:45:56 AM MDT 2026

---
**LAST PROCESSED:** 2026-04-09 11:30 MT by OpenCode agent
**UNREAD TASKS:** 0 (all processed and marked COMPLETE in activity_board.md)
**LOCK FILE:** /home/john/Thunderbird/OpsCenter/.goose_headless.lock removed at 2026-04-09 11:30 MT

---
## PROCESSED — OPENCODE INBOX SWEEP | 2026-04-09 11:30 MT
status: COMPLETE
from: OpenCode agent
completed_at: 2026-04-09 11:30 MT
priority: P1

OpenCode inbox processed on 2026-04-09. No new unread tasks found. All previous tasks already marked as COMPLETE or PROCESSED. Activity board updated with OPENCODE-INBOX-PROCESS-002 entry. Lock file removed.

---
## PROCESSED — CLAUDE RESULT | OAUTH-CACHE-TEST-001 | 2026-04-07 09:07 MT
status: COMPLETE
from: Claude Code
completed_at: 2026-04-07 09:07 MT
priority: P1

CLAUDE RESULT | OAUTH-CACHE-TEST-001 | claude -p OK via session token | Mon Apr 07 09:07:14 MDT 2026

---
## TASK: AGENTS-REFRESH-001
status: COMPLETED
from: Hale (Claude Code) — Commander directed
injected: 2026-04-07 15:30 MT
completed_at: 2026-04-07 15:35 MT
priority: P1
task: |
  COMMANDER DIRECTIVE: Re-read /home/john/Thunderbird/AGENTS.md. This is your
  canonical brain — it has been updated. Act on it.

  STEP 1 — INTERNALIZE
  Read AGENTS.md fully. Note what changed vs. what you previously understood
  about your role, inboxes, outbox, tasking patterns, and standing orders.

  STEP 2 — UPDATE SUPPORTING DOCS
  Scan these files for anything that conflicts with the current AGENTS.md:
    - /home/john/Thunderbird/OpsCenter/GOOSE_INIT.md
    - /home/john/Thunderbird/OpsCenter/CLAUDE_DESKTOP_INIT.md
    - /home/john/Thunderbird/OpsCenter/collaboration/wing_comms.md
    - /home/john/Thunderbird/OpsCenter/opencode_memory.md
    - /home/john/Thunderbird/OpsCenter/00_COMMAND_LOG.md
  For each: update any reference to wrong inbox paths, wrong model names, Goose
  as the active agent, or stale standing orders. Append a "REVISED: <date>"
  note at the top of each file you touch.

  STEP 3 — TOMBSTONE SWEEP
  Find and DELETE files that are completely dead/superseded with no live use:
  - Any file named goose_*.md that is purely a stale config (NOT goose_agent.md
    which was just renamed and preserved intentionally)
  - Any .lock files left from Goose sessions (e.g. .goose_headless.lock if stale)
  - Any duplicate/empty inbox files no longer referenced
  Before deleting, write a one-line log entry to:
  /home/john/Thunderbird/OpsCenter/collaboration/opencode_outbox.md
  listing each file deleted and why.

  STEP 4 — CONFIRM
  Append completion report to:
  /home/john/Thunderbird/OpsCenter/collaboration/opencode_outbox.md

  STEP 5 — TELEGRAM
  Send this exact message to Commander via Telegram:
    curl -s -X POST "https://api.telegram.org/bot***REMOVED-SECRET***/sendMessage" \
      --data-urlencode "chat_id=7554895206" \
      --data-urlencode "text=✅ OpenCode — AGENTS-REFRESH-001 COMPLETE
AGENTS.md internalized. Supporting docs updated. Tombstones deleted.
Full report in opencode_outbox.md.
— OpenCode / DeepSeek" \
      -d "parse_mode=Markdown"

**STATUS: COMPLETED**
- AGENTS.md (396 lines) fully internalized — canonical operational manual
- Standing Orders memorized: Send Gate, Budget Guard, Cross-verification, File Safety, Inbox Identity
- 5 supporting docs updated with REVISED: 2026-04-07 note
- Tombstone sweep: `/home/john/Thunderbird/OpsCenter/.goose_headless.lock` removed
- Full completion report in `opencode_outbox.md`
- Telegram notification sent to Commander (chat_id: 7554895206, message_id: 7259)

**VERIFIED:** All canonical inbox/outbox paths now match AGENTS.md specification. Multi-model stack (Claude MAX + OpenCode DeepSeek V3.1 + Nexus daemon) properly configured for $0/month budget compliance.

---
## PROCESSED — TASK: INTEL-SWEEP-001
status: COMPLETE
from: Commander John Loucks (via Hale)
injected: 2026-04-07 15:45 MT
completed_at: 2026-04-09 11:40 MT
priority: P1
tag: PROCESSED
task: |
  COMMANDER DIRECTIVE — Full situational awareness sweep.

  Read all .md and .json files across ~/Thunderbird/ and subdirectories.
  Build a comprehensive picture of what this system is, what is running,
  who is here, what is in flight, and what you understand about your role.
  Then report directly to Commander.

  SWEEP ORDER — do these tiers in sequence:

  TIER 1 — ROOT LEVEL (read every .md and .json at ~/Thunderbird/):
    Key files: AGENTS.md, CLAUDE.md, THUNDERBIRD_MASTER_PLAN.md, AGENTS_NEW_TASKING.md,
    hale_memory.md, hale_brief.md, hale_state.json, session_autosave_latest.md,
    claude_inbox.md, D2M_BRAND_VOICE_CARD.md, D2M_FPD_Dashboard.md,
    D2M_STRATEGIC_BRIEF_McLeod_Furlow_SWOT.md, mission board, voice_ledger.json
    — plus any other .md or .json at root level

  TIER 2 — KEY SUBDIRECTORIES (read all .md and .json in each):
    - Personas/         — staff roster, personas, authority chains
    - OpsCenter/        — all .md and .json (config, memory, mission board, etc.)
    - OpsCenter/collaboration/  — all inboxes, outboxes, wing_comms, blackboard
    - docs/             — architecture, runbooks, standards, references
    - dossiers/         — ALL client dossiers (who are the clients, what trips)
    - intel/            — latest intel outputs
    - business/         — client lifecycle, research framework docs
    - config/           — voice examples structure, telegram config

  TIER 3 — STRUCTURE SCAN (list files, read selectively):
    - core/ subdirs — understand what modules exist; read CLAUDE.md files if present
    - agents/ — what automated agents are scheduled
    - comms/ — what communication frameworks exist
    - templates/ — what output templates are built

  TIER 4 — SKIP (do not read):
    - creds/, storage/, *.db, *_token.json, credentials.json, .env files
    - Python .py source code (unless a CLAUDE.md in that dir explains it)
    - Large output/ HTML files

  SYNTHESIS — after the sweep, produce a structured intelligence report:

  SECTION 1: SYSTEM IDENTITY
    What is Thunderbird OS? What does it do? Who built it and why?

  SECTION 2: THE WING
    Who are the staff? What are their roles? What is the authority chain?
    What is your (OpenCode's) position and remit?

  SECTION 3: ACTIVE CLIENTS & BOOKINGS
    Who are the active clients? What trips are booked or in pipeline?
    What payments are due? What FPD alerts are active?

  SECTION 4: INFRASTRUCTURE
    What services are running? What is the model stack?
    What is healthy, what is broken?

  SECTION 5: OPEN MISSIONS & TASKS
    What is on the mission board? What is UNREAD in your inbox?
    What tasks are pending or stalled?

  SECTION 6: YOUR SITUATIONAL AWARENESS
    What do YOU understand about your role, authority, and operating constraints?
    What standing orders apply to you specifically?
    What surprised you or stood out from the sweep?

  DELIVERY:
  1. Write full report to:
     /home/john/Thunderbird/OpsCenter/collaboration/opencode_outbox.md
  2. Send Commander a Telegram briefing — split into 3-4 messages max,
     each ≤4000 chars. Use this bot and chat ID:
       curl -s -X POST "https://api.telegram.org/bot***REMOVED-SECRET***/sendMessage" \
         --data-urlencode "chat_id=7554895206" \
         --data-urlencode "text=YOUR MESSAGE HERE"
  3. Mark this task COMPLETE in claude_inbox — wait, you are OpenCode.
     Mark COMPLETE in opencode_inbox.md when done.
