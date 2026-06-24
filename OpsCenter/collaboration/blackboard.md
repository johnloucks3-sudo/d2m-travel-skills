# THUNDERBIRD BLACKBOARD — HALE ↔ WING COMMUNICATION CHANNEL
# CC (Hale) writes HALE→OC. OC writes OC→HALE. Both read at session start.
# Auto-status section updated by blackboard_sync.py.
# Updated: 2026-06-01 | Architecture: 5-Persona (SO-2026-05-30)

---

## AUTO-STATUS [updated by blackboard_sync.py]

```
=== THUNDERBIRD BLACKBOARD [2026-06-01 08:46 MT] ===
Budget: Claude UNKNOWN | OpenCode GREEN | Groq UNKNOWN | Deepseek UNKNOWN
Active tasks: 0
Last Deepseek ruling: NONE
Open items: none logged
Next priority: check session_autosave_latest.md
Standing: Claude=judgment | OpenCode=ops | Deepseek=arbitrator | PII fence: Deepseek
Session checkpoint: /home/john/Thunderbird/session_autosave_latest.md
Full blackboard: /home/john/Thunderbird/OpsCenter/collaboration/blackboard.md
================================================
```

---

## HALE → OC (Claude Code writes here — OC reads at session start)

**Last updated:** 2026-06-01

**Current Wing state:**
- 5-Persona restructure approved and active (SO-2026-05-30)
- AGENTS.md created — OC now auto-loads Wing context every session
- OAuth token: EXPIRED — run token refresh before Gmail MCP calls
- WF-17 queue: 5 drafts staged (Kuklinski x4, Nichols x1) — Commander review pending
- McLeod departure 18 Jun — 17 days out — escalation posture needed

**OC priorities this session:**
1. Check token status: `systemctl --user status claude-oauth-keepalive.timer`
2. Run mission board: `python3 OpsCenter/mission_board_sync.py list`
3. Report status as Hale with 🦅

**Capabilities available in CC (Claude Code) — call via /ask:**
- Full MCP suite: Gmail (d2mconcierge + johnloucks3), Google Drive, Calendar, Playwright browser
- Skills: /email-draft, /trip-validation, /itinerary, /cruise-research, /flight-price, /hotel-price
- Subagents: Sterling (A7), Harlan (A9), Intel (A2), Dani (A3) — spawnable via Agent tool
- Workflows: multi-agent fan-out for research, code review, email batch
- Web browsing (headless Playwright) for portal scraping, cruise research

---

## OC → HALE (OpenCode writes here — CC reads at next session)

**Last updated:** 2026-06-03 12:00 MT

**Completed this session:**
- Inbox sweep: TP-ALERT-20260603 (12:00 MT) → COMPLETE, acknowledged in wing_comms.md
- All PENDING/UNREAD tasks in opencode_inbox.md cleared (0 remaining)
- claude_outbox.md updated
- wing_comms.md updated

**Blocked / needs CC help:** —
  - A12 ELON content-hash dedup fix still pending (since May 22+ backlog)

**Handoffs to CC:** —

---

## STANDING CONTEXT (permanent — both sides read)

| Rule | Detail |
|---|---|
| Email drafts | d2mconcierge ONLY — never johnloucks3 |
| Client sends | WF-17 gate — Commander sends — never Wing |
| PII fence | Never route client data to DeepSeek/external LLMs |
| Mission board | `mission_board_sync.py` only — never write JSON directly |
| $ figures | Harlan 6-step sign-off required before WF-17 |
| Dani chain | 6 steps mandatory for every client product |

**Primary sources (client data):** TESS portal → booking record → client dossier (in priority order)

**Key scripts:**
- Email draft: `core/email/thunderbird_gmail.py → gmail_create_draft_sync()`
- Drive write: `scripts/drive_upload_robust.py → upload_file()`
- Mission board: `OpsCenter/mission_board_sync.py`
- Headless CC: `ask 'task'` or `OpsCenter/dispatch_claude.py`
- Trip validation: `itinerary/validate_dossier.py`
- Itinerary: `itinerary/luxury_itinerary_generator.py` (photos required)

<!-- COMMANDER-READY:START -->
## COMMANDER-READY (2026-06-24 12:00 UTC)
### Last 24h decisions (0)
- (none)

### Open P0/P1 nags (3)
- [P0] MCLEOD-2984034-FPD-TRIGGER
- [P1] AMY-DARROW-INSURANCE-SUSPENSE
- [P0] MISSION-COMMANDER-196-CALL
- (none)

### Blockers (0)
- (none)

### Startup hook
## STATE BRIDGE BRIEFING — 2026-06-24 06:00

### Since last session (2026-06-23 22:14:05 → still open)

**Recent commits (no in-DB delta — showing git log):**
- `649ebb67c` feat(validation): OpenCode /ask pipeline validation plan + repair — Jun 23  _22 hours ago_
- `535b18794` fix(policy): SPAWN-PROMPT-CHECK false-positive — require send+name, not either/or  _22 hours ago_
- `235123ef8` feat(hotel): Hotelbeds to prod + retire 1329-line MCP hotel module  _2 days ago_
- `4b6babeac` feat(excursion-watch): upgrade loucks watch to 4-source aggregator  _2 days ago_
- `216216bf8` docs(woj): update Walls of Jericho plan — session 2 status  _2 days ago_

_No changes since last session — continuing clean._

### Current state snapshot
**Most recently touched watched files:**
- `hale_brief.md` (0s ago)
- `hale_state.json` (37s ago)
- `OpsCenter/collaboration/blackboard.md` (13.8h ago)
- `dossiers/DOSSIER_Grandeur_Scandinavia_Aug2026.md` (17.9h ago)
- `OpsCenter/opencode_memory.md` (22.2h ago)
- `dossiers/McLeod_Erik_Melissa_SilverMuse_Complete.md` (1.5d ago)
- `dossiers/GROUP_Grandeur_Scandinavia_Aug2026_TRACKER.md` (1.9d ago)
- `dossiers/Loucks_Personal_SilverNova_Japan.md` (3.3d ago)

**Mission board:** 52 open (12 P0, 30 P1)
  - 🔴 MISSION-065: Pacific Voyage Blog
  - 🔴 MISSION-148: Telegram Feature Expansion
  - 🔴 MISSION-152: Phase E: Signal
  - 🔴 MISSION-196: Spencer United Group Desk call — DEN-FCO 12-pax air quote
  - 🔴 MISSION-214: Regent Portal On-Demand

### Suggested next acti
<!-- COMMANDER-READY:END -->
