# PROJECT NEXUS — AUTONOMOUS WAR ROOM SPECIFICATION V2.1
# Date: 2026-04-05 | Status: CLAUDE REVIEW COMPLETE → READY FOR BUILD
# Commander: John Loucks | Author: Goose (Nexus)
# Name Change: "Blackboard" → "Mission Board"

---

## 0. FILE DISCIPLINE (MANDATORY — POST-INCIDENT FIX 2026-04-05)
**Incident:** NEXUS Spec V2.1 wrote to `claude_inbox.md` using `>` (overwrite) instead of `>>` (append), wiping pending history.

**RULES FOR ALL AGENTS / NEXUS:**
1.  **INBOXES:** *Never* overwrite Inboxes. Always append or use safe insert patterns. Overwriting an inbox destroys unread tasks.
2.  **MISSION BOARD:** State fields (status/dates) updated in-place via JSON merge. Historic logs and session entries are append-only — never truncated.
3.  **LOCK FILES:** Atomic creation (create + write) to avoid race conditions.
4.  **TEMP FILES:** Delete after successful operation.
5.  **CONFIRMATION:** Every write logs `[WRITE OK: filename]` to `/home/john/Thunderbird/logs/nexus_audit.log`.
6.  **GOOSE INBOX:** Append-only for incoming tasks. Mark status:READ when done.
7.  **CLAUDE INBOX:** Append-only for incoming tasks. Mark status:RESPONDED when done.
8.  **ROUTING LOG:** Always append. Never edit existing entries.

---

## ⚠️ COMMANDER DIRECTIVES (2026-04-05)
1.  **LOW COST TARGET: NO GEMINI.** Gemini burned $100 unplanned. All OpenCode operations use `deepseek/deepseek-chat-v3.1` (~$0.27/M).
3.  **Groq conditional.** Use only if available, alert if not.
4.  **Goose covers almost all personas.** Including EXEC (Mission Board Interface).
4.  **DUAL-BRAIN LOGIC:** Every persona has a "DeepSeek Brain" (Work/Action) and a "Claude Brain" (Judgment/Voice). Nexus routes based on complexity keywords.

---

## 1. THE CONCEPT
**Goal:** Shift from "Commander-directed" to "Commander-supervised."
**Mechanism:** The Nexus orchestrator drives the War Room autonomously.

---

## 2. PERSONA MAPPING (DUAL-BRAIN)

### OPENCODE = The Operator (DeepSeek V3.1 — ~$0.27/M)
**Brain:** `deepseek/deepseek-chat-v3.1` | **Scope:** Action, extraction, auditing, filing.

| Persona | Role (DeepSeek Brain) |
|---------|-------------------|
| **A2 (Dembe)** | Web scraping, PDF summarization, flight/hotel search, data extraction |
| **A7 (Gauge)** | Error detection, budget validation, log auditing |
| **A9 (Vic)** | Commission calculations, invoice comparison, spreadsheet updates |
| **EXEC (Naia)** | **Passive read/write of Mission Board.** Extracts operative details from emails/text and files to Dossiers |
| **A12 (ELON)** | Script writing, debugging, system fixes |

### 🧠 CLAUDE = The Strategist (Sonnet 4 — MAX OAuth — $0 COST)
**Brain:** `claude-sonnet-4-6` via `claude -p` (MAX OAuth) | **Scope:** Judgment, voice, strategy.

| Persona | Role (Claude Brain) |
|---------|---------------------|
| **A2 (Wraith)** | Intel analysis, vendor health assessment |
| **A7 (Gauge)** | Strategic fixes for margin issues |
| **A9 (Vic)** | Pricing strategy, complex contract logic |
| **A5 (Viper)** | Strategy, competitive analysis, growth |
| **A6 (Luna)** | Client narratives, brand voice, creative |
| **A3 (Dani)** | Client communications review, voice calibration |
| **Hale (COS)** | **Escalation Only** — Deadlock, ambiguous scope, judgment |

---

## 3. KEYWORD ROUTER (HOW NEXUS DECIDES THE BRAIN)

| Priority | Keywords | Route To | Examples |
|----------|----------|----------|----------|
| **HIGH** | `draft`, `why`, `assess`, `strategy`, `negotiate`, `propose`, `creative` | Claude (Sonnet) | "Draft the Smith email", "Assess risks" |
| **NORMAL** | `list`, `check`, `update`, `extract`, `verify`, `file`, `add`, `search`, `compare` | DeepSeek (OpenCode) | "List flights", "Check budget" |
| **TIEBREAK** | Both keyword sets present | Claude (Sonnet) | Over-route to Claude rather than under-route |
| **UNKNOWN** | Zero recognized keywords | Claude (Sonnet) | "Figure something out" → Hale clarifies |

**Rule:** It never costs you money to over-route to Claude (MAX). It *does* cost you a failed mission to under-route to DeepSeek.

---

## 4. THE MISSION BOARD (formerly Blackboard)
- **Shared State:** Synced every 5 minutes via `mission_board_sync.py`.
- **Interface:** **EXEC** is the passive read/write layer.
    - `EXEC: List the board` → DeepSeek reads JSON, returns summary
    - `EXEC: Add — Furlow trip validation due 8 April` → DeepSeek writes with `suspense_date: 2026-04-08`
    - `EXEC: Change suspense date Japan trip to 12 April` → DeepSeek updates field

---

## 5. COMMANDER INTERFACE — THREE WAYS TO DROP TASKS
1.  **Telegram GW:** `@nexus "Plan Smith Japan trip, $8k, Apr 15-22"`
2.  **CLI Inbox:** Write JSON to `goose_inbox.md` (append-only).
3.  **GMAIL TO EXEC:**
    - Email `johnloucks3@gmail.com` with subject `EXEC: [command]` or `NEXUS: [mission]`.
    - Body is parsed into actions.
    - **Example:** `"EXEC: Add Furlow trip validation due 8 April to the board."`

### SUSPENSE DATE AUTO-ESCALATION
If `suspense_date` is **within 24 hours** and status != COMPLETE:
- Nexus auto-pages Commander via Telegram.

---

## 6. STOP CRITERIA (SIX HARD STOPS)
1.  **Max iterations:** 6 spawns per mission.
2.  **TTL:** 4 hours max.
3.  **Token budget:** 50K tokens per mission.
4.  **Deadlock:** Status unchanged for 2 iterations.
5.  **Explicit COMPLETE:** Agent must write rationale.
6.  **No blind pass-through:** Next action from whitelist.

---

## 7. SECURITY & COST
- **Nexus cannot send emails.** Writes drafts only. Send gate remains.
- **NEXUS LOCK FILE** with heartbeat.
- **Cost Model:** Low-cost target (DeepSeek V3.1 ~$0.27/M + Claude MAX $0).
- **Audit Log:** Immutable `war_room.json` with UTC timestamps.
- **Gemini:** Purged from all code paths.
- **DeepSeek V3.1:** Primary operational model via OpenRouter.

---

## 8. CLAUDE REVIEW V2.1 — VERDICT
**Date:** 2026-04-04 | **Reviewer:** Hale/COS
**Status:** APPROVED FOR BUILD PHASE

| Question | Verdict |
|----------|---------|
| Dual-Brain Routing | ✅ Acceptable with Claude-precedent tiebreak |
| EXEC via Gmail | Highly feasible. Regex first, DeepSeek fallback |
| DeepSeek Capability | 85-90% of roles covered. Rate limits are the only risk |
| Nexus ≠ Hale Confirmed | ✅ "Nexus = engine, Hale = fire extinguisher" |
| $0 Cost Realistic | ✅ Yes, with all 6 hard stops enforced |

**Next Steps:** Begin build phase in priority order:
1. Purge Gemini from all configs
2. Build keyword router
3. Create `mission_board.json` structure
4. Build Gmail→EXEC polling script
5. Test DeepSeek rate limits
6. Document MAX OAuth ceiling

---
## FILE DISCIPLINE ENFORCED FROM THIS POINT
All agents and services must follow Section 0 rules. Violations logged to routing_log.md.
