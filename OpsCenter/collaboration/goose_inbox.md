# ⛔ TOMBSTONE — 2026-04-07
# This file is DEPRECATED. Do not write here.
# See AGENTS.md for canonical paths:
#   claude_inbox  → /home/john/Thunderbird/claude_inbox.md
#   claude_outbox → /home/john/Thunderbird/OpsCenter/collaboration/claude_outbox.md
#   opencode_inbox→ /home/john/Thunderbird/OpsCenter/collaboration/opencode_inbox.md
# ─────────────────────────────────────────────
# ARCHIVED CONTENT BELOW (read-only)
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
