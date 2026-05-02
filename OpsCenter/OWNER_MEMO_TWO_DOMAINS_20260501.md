---
**MEMORANDUM**

TO: Director of Staff (COS); All Staff

FROM: John Loucks, Owner — Dreams2Memories Travel, LLC

DATE: 2026-05-01

SUBJECT: Organizational Structure — Two Virtual Domains & Cross-Domain Coordination

CC: Claude Code (Haiku 4.5), OpenCode (Gemini 3.1 Flash Lite)

---

## SITUATION

Dreams2Memories Travel now operates as a **distributed intelligence organization with two distinct virtual domains**:

**Domain 1: Claude Code**
- Primary AI entity: Claude Haiku 4.5 (with Sonnet/Opus escalation)
- Access: Native Claude Code CLI, direct OAuth, full Wing integration
- Responsibility: Strategic decisions, client-facing execution, voice-matched outputs, quality gates

**Domain 2: OpenCode**
- Primary AI entity: Gemini 3.1 Flash Lite-Preview (with DeepSeek fallback)
- Access: Headless subprocess dispatch, token-tracked, Telegram-monitored
- Responsibility: Bulk operations, research, cost-optimized workflows, background processing

Both domains serve **one unified business** and **one Owner**.

---

## THE PROBLEM

Right now: Decisions made in Domain 1 (Claude Code) are not systematically communicated to Domain 2 (OpenCode). Changes to protocols, assignments, or enterprise-wide directives sit in Claude Code's memory and files without reaching Gemini/OpenCode.

**Result:** OpenCode operates on stale information. Coordination fails. Duplicate work. Missed dependencies.

**This ends now.**

---

## THE DIRECTIVE

**Director of Staff (COS) is accountable for keeping both domains informed.**

### Every decision in one domain that affects the other must be explicitly communicated.

**Cross-domain communication triggers:**

1. **Protocol changes** (YSB briefing standard, auth updates, new approval gates)
2. **Staff assignments** (reassigning a task between domains, ownership changes)
3. **Tool deployments** (new MCP tools, scrapers, integrations that both domains use)
4. **Client changes** (new bookings, priority shifts, deadline changes affecting both domains)
5. **Financial decisions** (budget changes, token limits, cost guardrails affecting both)
6. **Operational procedures** (new workflows, escalation paths, naming conventions)

### Every Owner/DoS decision must be documented as enterprise-wide if it affects:
- Client outcomes (both domains touch clients)
- Budgets (both domains spend resources)
- Protocols (both domains must follow same rules)
- Deadlines (both domains must respect same timelines)
- Priorities (both domains must align on what matters most)

---

## MECHANISM: HOW COORDINATION HAPPENS

**Owner/COS → Claude Code domain:**
- Direct email (johnloucks3@gmail.com)
- Telegram C2 (@D2MC2C)
- This document (OpsCenter files)

**Owner/COS → OpenCode domain (Gemini):**
- **Primary channel:** `/home/john/Thunderbird/OpsCenter/collaboration/opencode_briefing_board.md`
  - COS writes decisions here
  - OpenCode reads this file on every dispatch
  - Format: One decision per section, timestamp, "read?" flag
  - OpenCode confirms: `# [DECISION-ID] — ACK by OpenCode [timestamp]`

- **Secondary channel:** Telegram message to `/opencode` handler
  - For urgent/immediate coordination
  - COS posts: "OpenCode: [Decision]. Read OpsCenter/collaboration/opencode_briefing_board.md for details."

- **Tertiary channel:** Mission board (if task assignment crosses domains)
  - Task owner: COS updates mission board
  - Visible to both Claude Code and OpenCode
  - Status updates flow both directions

**Default assumption:** If a decision is not on the briefing board with an ACK from OpenCode, **it has not been communicated to Gemini.**

---

## EXAMPLES

### Example 1: Protocol Change (YSB Deployment)

**Claude Code learns:**
- COS writes YSB_BRIEFING_PROTOCOL.md in OpsCenter/
- Claude Code reads it immediately
- Claude Code begins using YSB format in new decisions

**OpenCode must learn:**
- COS posts to `/home/john/Thunderbird/OpsCenter/collaboration/opencode_briefing_board.md`:
  ```
  ## DECISION: YSB BRIEFING PROTOCOL DEPLOYED
  Date: 2026-05-01
  Owner: John Loucks
  
  Replace all TSB references with YSB (Yoda's Summary Brief).
  - PATH A (Executive) for high-stakes decisions
  - PATH B (Tactical) for real-time polling
  - "Owner" replaces "Commander"
  
  File: OpsCenter/YSB_BRIEFING_PROTOCOL.md
  Effective: Immediately
  
  OpenCode: Confirm read + acknowledgment below
  ```
- OpenCode reads briefing board on next dispatch
- OpenCode posts ACK: `## [ACK] YSB BRIEFING PROTOCOL DEPLOYED — Gemini 3.1 [timestamp]`

### Example 2: New Client Task (Crossing Domains)

**Claude Code owner:** Navarro (A1 Intake)
**OpenCode task:** Research ship intelligence for this client

**Coordination:**
- COS updates mission board: "Task TK-092: Ship Intel for McLeod, assigned OpenCode, depends on A1 profile (Claude Code)"
- COS posts to briefing board: "OpenCode: Profile ready in McLeod dossier. Research ship intelligence for Lesser Antilles Regent. Deadline: May 3."
- OpenCode reads briefing board, finds task, begins research
- OpenCode writes findings to mission board
- Claude Code reads findings, incorporates into client itinerary

### Example 3: Token Budget Alert (Enterprise-Wide)

**Owner decision:** Weekly token budget increased from $100 to $150 for both domains

**Coordination:**
- COS posts to briefing board: "TOKEN BUDGET UPDATE: Weekly limit now $150 (both domains). Hike applies immediately. Monitor spend via hale_state_unified.json."
- COS sends Telegram: "OpenCode: Budget increase posted to briefing board."
- OpenCode reads on next dispatch, updates internal cost tracking
- Claude Code sees updated hale_state_unified.json
- Both domains now operate under same budget ceiling

---

## ACCOUNTABILITY

**Director of Staff (COS):**
- Responsible for identifying which decisions cross domains
- Responsible for writing to briefing board with clear language and deadlines
- Responsible for confirming OpenCode has read (via ACK on briefing board)
- Weekly report: "Cross-domain decisions made, OpenCode acknowledgments received"

**OpenCode (Gemini):**
- Read briefing board before every dispatch
- Acknowledge all decisions with timestamp
- Flag any decision that doesn't make sense or conflicts with current work
- Escalate ambiguities to Owner via Telegram

**Claude Code (Haiku):**
- Keep copies of all cross-domain decisions in working memory
- Alert COS if OpenCode appears to be operating on stale info
- Treat briefing board as source of truth for enterprise-wide changes

---

## BRIEFING BOARD STRUCTURE

**File:** `/home/john/Thunderbird/OpsCenter/collaboration/opencode_briefing_board.md`

**Format:**
```
# OPENCODE BRIEFING BOARD
*Last updated: 2026-05-01 15:00 MT*

## [DECISION-001] YSB BRIEFING PROTOCOL DEPLOYED
**Date:** 2026-05-01  
**Owner:** John Loucks  
**Urgency:** HIGH  
**Effective:** Immediately  

**Content:** [Decision summary]

**File reference:** OpsCenter/YSB_BRIEFING_PROTOCOL.md

**OpenCode ACK:** [ ] Pending  
**ACK timestamp:** —

---

## [DECISION-002] [Next decision title]
...
```

OpenCode updates by adding:
```
**OpenCode ACK:** [x] Read and understood  
**ACK timestamp:** 2026-05-01 15:15 MT
```

---

## WHY THIS MATTERS

We are **one business**, not two. When Claude Code makes a decision about client experience, OpenCode needs to know. When OpenCode optimizes a cost, Claude Code needs to know. When Owner sets a priority, both domains must align.

**Right now:** Information asymmetry is costing us coherence.

**Going forward:** COS owns the coordination bridge.

---

## STANDING ORDER

**Effective immediately:** All Owner and COS decisions affecting enterprise operations must be posted to the OpenCode briefing board within 2 hours of decision, with explicit acknowledgment required before decision is considered "live" across the organization.

If a decision is not on the briefing board with an OpenCode ACK, it has not been communicated to the Gemini domain. COS is accountable.

---

*John Loucks, Owner*  
*Dreams2Memories Travel, LLC*  
*2026-05-01*

---

**DISTRIBUTION:**
- Claude Code (direct)
- OpenCode (briefing board + Telegram)
- File: OpsCenter/OWNER_MEMO_TWO_DOMAINS_20260501.md
