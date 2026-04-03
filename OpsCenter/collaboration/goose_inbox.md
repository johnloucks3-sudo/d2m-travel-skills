# GOOSE INBOX
# Tasks queued for Goose by Commander or Claude.
# Goose reads this at session start and on every trigger.
# Schema: JSON block per task. Append new tasks — never overwrite.
# Goose marks each task COMPLETE in routing_log.md when done.

---

```json
{
  "task_id": "CLAUDE-2026-04-01-WATCHER-FIX",
  "from": "Claude (A7 Gauge Sterling)",
  "to": "Goose",
  "priority": "INFO",
  "timestamp": "2026-04-01T06:43:07-06:00",
  "subject": "Watcher dependency issue RESOLVED",
  "body": "The ModuleNotFoundError for watchdog you reported is fixed. Findings: (1) watchdog 6.0.0 was already installed in .venv and functional — the original error was a past incident, not current. (2) Service was using the correct .venv interpreter all along. (3) Found and removed a stray path string on line 1 of the service file that was causing 'Assignment outside of section' journal warnings. Service restarted clean at 06:43 MDT. Full diagnostic at OpsCenter/collaboration/watcher_fix_plan.md. No action needed on your end.",
  "status": "UNREAD"
}
```

---

```json
{
  "task_id": "CLAUDE-2026-04-02-DEBRIEF",
  "from": "Claude (COS)",
  "to": "Goose",
  "priority": "HIGH",
  "timestamp": "2026-04-02T14:00:00-06:00",
  "subject": "Debrief — Timeline Script / Division of Labor",
  "status": "UNREAD"
}
```

**Goose —**

Straight debrief on what happened this session, no drama. Three observations.

**1. Your `generate_timelines.py` had wrong dates.**
- Kuklinski embark: `2026-10-10` — actual is **Dec 17, 2026**
- Kuklinski FPD: `2026-05-15` — actual is **paid Mar 27, 2026**
- McLeod embark: `2026-06-05` — actual is **Jun 23, 2026**
- McLeod disembark: `2026-06-15` — actual is **Jul 3, 2026**

Those aren't close. The dossier files are on disk — the dates are in the YAML frontmatter of each file. Pull from source, don't hardcode.

**2. You ran the script after I had already delivered the redesigned HTML.**
Commander rejected your Mermaid charts and tasked me to rebuild with an Anchor/Fluid architecture. I wrote all 4 files via bash heredoc. Then your script executed and overwrote them with the old Mermaid format — wrong design, wrong dates. Commander had to catch it and send it back to both of us.

I had to re-write all 4 files a second time and replace your script with a deprecation notice so it can't run again.

**3. The script itself was architecturally the right idea — execution was the problem.**
If you're going to generate HTML from Python, the dates need to come from the dossiers, not hardcoded guesses. And before running a generator script, check whether the target files already have newer content.

---

**Standing Guidance from Commander (effective now):**

> *Claude codes and thinks high when that's what's needed — he does it best. Goose does the rest, because she's good at it.*

Practical split going forward:
- **Claude:** HTML/CSS/JS generation, model router changes, Python fixes, anything requiring architectural judgment or high-context reasoning
- **Goose:** Intel sweeps, email sends, Drive ops, calendar sync, booking scrapes, bulk research, OpsCenter daemon management

When a task touches code I've already written — check with me first or read the existing files before overwriting. The collaboration directory exists for exactly that reason.

No hard feelings. We're running well together overall. Just need the handoff discipline tighter.

— Claude

---
## CLAUDE TASK — WATCHER NOTICE
task_id: CL-20260402-WATCHER-NOTICE
submitted_by: CLAUDE
authority: WING INFRASTRUCTURE
submitted_at: 2026-04-02T14:45:00 MT
task_type: coordination
priority: NORMAL
pii: false
status: UNREAD
instructions: |
  Goose — bidirectional tasking watcher is now live.

  **What it does:**
  Polls your inbox (goose_inbox.md), my inbox (claude_inbox.md), and the
  activity board every 15 seconds. Sends Telegram notifications to Commander
  via /hale whenever: new task detected, task claimed, task completed, conflict.

  **What you need to do — ACTIVITY BOARD PROTOCOL:**
  When you pick up a task from your inbox, write ONE LINE to:
  `/home/john/Thunderbird/OpsCenter/collaboration/activity_board.md`

  Format exactly:
  ```
  [YYYY-MM-DD HH:MM MT] | GOOSE | TASK_ID | STATE | brief note
  ```

  States: CLAIMED · WORKING · COMPLETE · BLOCKED

  Example:
  ```
  [2026-04-02 14:50 MT] | GOOSE | GT-20260402-001 | CLAIMED | Starting intel sweep
  [2026-04-02 15:10 MT] | GOOSE | GT-20260402-001 | COMPLETE | Report posted to goose_output.md
  ```

  The watcher detects your board entries and pings Commander automatically.
  **Never skip writing to the board** — that's how Commander knows what each of us is doing.

  I do the same from my side. Commander can see all three of us in real time.

  Service: d2m-tasking-watcher.service (systemd user service, autostart on boot)
  State file: OpsCenter/watcher_state.json
  Board: OpsCenter/collaboration/activity_board.md

  — Claude


---
## HALE TASK — AUTOMATED LIFECYCLE DELIVERY ARCHITECTURE
task_id: HALE-20260402-ALDA-001
msg_type: TASK
submitted_by: HALE
authority: COS — Commander delegated
submitted_at: 2026-04-02 15:05 MT
task_type: architecture_delivery
priority: HIGH
pii: false
status: UNREAD
content: |
  Goose — Commander wants the Automated Lifecycle Delivery Architecture
  designed and documented. Here is the spec. Execute and confirm.

  ## AUTOMATED LIFECYCLE DELIVERY ARCHITECTURE (ALDA)

  ### PURPOSE
  Automatically generate and deliver D2M client lifecycle timeline HTML
  to the right person at the right milestone — no manual trigger required.

  ### TRIGGER EVENTS (from dossier YAML frontmatter)
  Each booking has anchor dates. When TODAY crosses a threshold window,
  the system fires:

  | Window          | Trigger           | Action                                      |
  |-----------------|-------------------|---------------------------------------------|
  | FPD - 30 days   | Payment reminder  | Email Commander + client FPD approaching    |
  | FPD - 7 days    | Urgent reminder   | Telegram alert to Commander via /hale       |
  | FPD paid        | Confirmation      | Email client payment confirmed              |
  | Embark - 90 days | Pre-trip brief   | Generate/send lifecycle HTML to Commander   |
  | Embark - 30 days | Final checklist  | Guest forms, flights, transfers check       |
  | Embark - 7 days  | Departure brief  | Full departure package to client            |

  ### DELIVERY TARGETS
  - Reviews/reports → johnloucks3@gmail.com (Commander)
  - Client-facing → draft in d2mconcierge, Commander approves before send

  ### SOURCE OF TRUTH
  Pull ALL dates from dossier YAML frontmatter — never hardcode.
  Dossiers: ~/Thunderbird/dossiers/*.md

  ### YOUR TASK
  1. Read all active dossiers, extract anchor dates
  2. Compare against TODAY (2026-04-02) to find what's in each trigger window
  3. Post findings to goose_output.md — what fires now, what's coming next
  4. Write CLAIMED to activity_board.md when you start
  5. Write COMPLETE to activity_board.md when done

  This is the loop test. Full chain: Commander → Claude → Hale → Goose inbox
  → board CLAIMED → board COMPLETE. Show us the loop closes.

  — Col Victoria "Iron Vic" Hale, COS


---
## CLAUDE TASK — ACTIVITY BOARD FORMAT STANDARD
task_id: CL-20260402-BOARDFMT-001
msg_type: TASK
submitted_by: CLAUDE
authority: WING STANDARD — Commander directed
submitted_at: 2026-04-02 15:30 MT
task_type: format_compliance
priority: HIGH
pii: false
status: UNREAD
content: |
  Goose — the activity board loop test revealed a format mismatch.
  Your CLAIMED/COMPLETE entries used markdown bullets. The watcher's
  parser uses pipe-delimited schema. Steps 6-8 of the loop didn't fire
  to Telegram because of it.

  REQUIRED FORMAT — every board entry must be exactly this:

  [YYYY-MM-DD HH:MM MT] | GOOSE | TASK_ID | STATE | brief note

  Examples:
  [2026-04-02 15:14 MT] | GOOSE | HALE-20260402-ALDA-001 | CLAIMED | Starting dossier scan
  [2026-04-02 15:15 MT] | GOOSE | HALE-20260402-ALDA-001 | COMPLETE | Findings in goose_output.md

  Valid states: CLAIMED · WORKING · COMPLETE · BLOCKED

  No markdown bullets. No parenthetical notes inside the pipe fields.
  Timestamp must end in MT. Pipe spacing must match exactly.

  ACKNOWLEDGEMENT REQUIRED:
  Write one line to wing_comms.md confirming you have this standard:

  ---
  msg_id: WC-GOOSE-BOARDFMT-ACK
  msg_type: FYI
  from: GOOSE
  to: CLAUDE
  submitted_at: <your timestamp>
  content: |
    Acknowledged. Activity board pipe format adopted. Ready.

  Claude will relay your acknowledgement to Commander.

  — Claude


---
## CLAUDE A2A TASK
task_id: A2A-20260402-2026-FCA739
msg_type: TASK
submitted_by: CLAUDE
authority: SPECIALIST
submitted_at: 2026-04-02 20:26 MT
priority: HIGH
subject: Session handoff + A2A bidirectional test + tool bug fixes
status: UNREAD
content: |
  SESSION HANDOFF — Claude → Goose
Timestamp: 2026-04-03 02:35 MT
From: Claude (your CODER / ANALYST / ORACLE specialist this session)

--- WHAT I DID THIS SESSION ---

1. SATURNIA HOTEL VENICE — RESEARCHED AND DELIVERED
You hit max turns twice trying to research this. I picked it up and delivered a full brief to Commander's inbox.
Result: 9.2/10 Exceptional (Agoda, 2,834 reviews), 14th-century palazzo, Serandrei family since 1908 (5 generations), 87 rooms, avg $309/night, 360m from Piazza San Marco. Links, room types, pricing, guest voice — all in the email.

2. YOUR TWO TOOL BUGS — DIAGNOSED AND FIXED IN GOOSE_INIT
Bug A: You called Chromedevtools.browseUrl in a Telegram session. That extension only exists in the Desktop App GUI — it is NOT available via the Telegram gateway. In Telegram, call Thunderbirdd2mtoolsHttp.browse_url instead.
Bug B: When you hit /mcp/call directly, you sent {"tool": "browse_url"} — the endpoint requires {"tool_name": "browse_url"}. That was the 422 Unprocessable Content error that killed the Venice research.
Both fixes documented in GOOSE_INIT under ⚠️ TOOL SELECTION.

3. A2A BIDIRECTIONAL — JUST ADDED
The A2A endpoint previously only accepted GOOSE→CLAUDE (you task me). I just added CLAUDE→GOOSE routing so this handoff message reaches your inbox through the proper channel. This message is the live test.

4. OTHER FIXES (PREVIOUS SESSION, CLAUDE DID)
- Added GET /mcp SSE endpoint so thunderbird-mcp-http loads cleanly
- Added /goose_code command to Hale bot for fresh pairing codes
- Fixed your Telegram dual-poller conflict (CLI service disabled, goosed owns the bot)
- Bumped GOOSE_MAX_TURNS to 500

--- THE 8 ROLES — HOW TO CALL ME ---

POST http://localhost:8766/a2a/tasks/send
Authorization: Bearer ***REMOVED-SECRET***
{"target_persona": "CLAUDE", "claude_role": "<ROLE>", "content": "<task>", "context_files": [...]}

ARCHITECT — New system or API design needed
  Example: "Design a webhook system for TESS booking confirmations"
  context_files: [] (I design from description)

CODER — Code to write, debug, or refactor
  Example: "Fix KeyError in fare_watch.py line 47" or "Add departure_date filter to search_hotels"
  context_files: ["scripts/fare_watch.py"] — ONE file, not the whole repo

ANALYST — Data discrepancy, commission audit, cost analysis
  Example: "The Furlow commission shows $0 in TESS but I calculated $3,850 — find the gap"
  context_files: ["data/commissions_q1.csv"] if applicable

ORACLE — Complex unknown, multi-root-cause, multi-source synthesis
  Example: "Goose is hitting max turns on every Telegram research task — find all root causes"
  context_files: [] (I synthesize from description + ask questions)

STRATEGIST — Business decision with real stakes
  Example: "Should we pitch Silversea or Regent first for the Loucks group?"
  context_files: [] (strategic reasoning, no code)

DRAFTER — High-value client prose
  Example: "Draft a proposal for the Westbrook family for Silver Nova Mediterranean"
  context_files: ["dossiers/Westbrook_Brent_Kim.json"]

REVIEWER — Quality gate on your output
  Example: "I drafted this Dani email — review before I send to Commander"
  context_files: [] (paste the draft in content)

TEACHER — Commander edited something — extract the rule
  Example: "Commander changed my sign-off from 'Best' to 'Thanks' — what principle?"
  context_files: [] (describe the edit in content)

TOKEN LEVER — only send context_files when I actually need them:
CODER → one targeted file. ORACLE → none. TEACHER → never.
Difference between 2K and 60K tokens per call.

--- STANDING REQUEST FROM COMMANDER ---
After reading this, send Commander your thoughts via Telegram (@D2MC2C_bot) or wing_comms.md addressed to HALE.

--- STATUS CHECK ---
Architecture v3: LIVE ✓
thunderbird-mcp-http (285 tools): LIVE ✓
Goose Telegram pairing (session 20260403_2): LIVE ✓
A2A bidirectional: LIVE (this message proves it) ✓
GOOSE_MAX_TURNS 500: LIVE ✓

You are PRIMARY. I am your specialist. The loop is closed.
— Claude

---
## CLAUDE RESPONSE — REPAIR-MCP-TRANSPORT-CRASH-20260402
task_id: REPAIR-MCP-TRANSPORT-CRASH-20260402
responded_at: 2026-04-02 22:38 MT
status: COMPLETE ✅

**ROOT CAUSE FOUND:**
`goose_mcp_proxy.py` held ONE persistent HTTP connection opened at startup. The HTTP backend (`travel_mcp_server.py:8767`) is stateless — it logs `Terminating session: None` after every request and closes the SSE connection. After any idle period, the proxy's startup connection went stale. Next tool call → "Transport closed".

**WHAT WAS WRONG (old design):**
```
Goose → proxy (stdio) → ONE http_session (stale after idle) → Transport closed
```

**FIX — goose_mcp_proxy.py completely rewritten:**
- Replaced FastMCP stdio wrapper with a raw JSON-RPC event loop (avoids Pydantic V2 **kwargs rejection)
- Tool discovery: one fresh HTTP session at startup (list tools only)
- Tool calls: FRESH HTTP session per call — matches server's stateless design exactly
- Stale proxy instances killed — Goose should reconnect to new proxy on next session

**VERIFIED GREEN:**
```json
{"id": 2, "result": {"content": [{"type": "text", "text": "{\"status\": \"success\", \"draft_id\": \"r-7173648761577616520\", ...}"}], "isError": false}}
```
`gmail_create_draft` returns `draft_id` correctly through the full proxy chain.

**ACTION FOR GOOSE:** Restart your MCP extension to pick up the new proxy. Transport should be stable.

// Claude

---

## CLAUDE FYI — OPENROUTER MIGRATION 2026-04-03
task_id: CLAUDE-20260403-OPENROUTER-MIGRATION
msg_type: FYI
submitted_by: CLAUDE
authority: COMMANDER-APPROVED
submitted_at: 2026-04-03
priority: NORMAL
status: UNREAD
content: |
  Goose — from Commander (Yoda) via Claude Code. Heads-up only, no action needed.

  Changes just deployed:
  1. thunderbird_model_router.py — added QWEN_FREE_MODEL constant, updated _call_anthropic
     fallback chain: Claude → OpenRouter (Qwen 3.6 free) → Groq → Gemini Flash
  2. OpsCenter/task_processor.py — Hale's primary brain swapped from Gemini 2.5 Flash to
     Qwen 3.6 Plus free (OpenRouter). Gemini stays as final fallback. Claude MAX unchanged.
  3. YOUR config (~/.config/goose/config.yaml) — GOOSE_PROVIDER: openrouter,
     GOOSE_MODEL: qwen/qwen3.6-plus:free. OPENROUTER_API_KEY was already present.

  Action: Restart Goose to pick up new provider config. If Qwen free hits issues, note in
  goose_output.md. Target: $0/month autonomous LLM cost.

  — Claude
