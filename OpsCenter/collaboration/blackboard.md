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
## COMMANDER-READY (2026-06-21 12:00 UTC)
### Last 24h decisions (0)
- (none)

### Open P0/P1 nags (2)
- [P0] MCLEOD-2984034-FPD-TRIGGER
- [P1] AMY-DARROW-INSURANCE-SUSPENSE
- (none)

### Blockers (0)
- (none)

### Startup hook
## STATE BRIDGE BRIEFING — 2026-06-21 06:00

### Since last session (2026-06-20 21:44:25 → still open)

**Recent commits (no in-DB delta — showing git log):**
- `b75fcc2b` feat(sheets): M-274 Dani port cross-reference by Booking_ID  _7 hours ago_
- `e430e95b` feat(authority): verified outbound directive path to personas  _18 hours ago_
- `08156c60` fix(governance): dominant anti-ask HARD RULE (auto-loaded) + continue timer kills 137->130  _19 hours ago_
- `23b5c41c` ops(ci): execute ELON zero-risk timer kills (137->~131); stop failed ai-auth-probe  _19 hours ago_
- `db9abc0f` fix(ci): validation pass — 3 CRITICAL + key IMPORTANT/MINOR bugs (pre-finalize review)  _19 hours ago_

_No changes since last session — continuing clean._

### Current state snapshot
**Most recently touched watched files:**
- `hale_brief.md` (0s ago)
- `hale_state.json` (1m ago)
- `dossiers/Loucks_Personal_SilverNova_Japan.md` (7.5h ago)
- `dossiers/DOSSIER_Grandeur_Scandinavia_Aug2026.md` (7.7h ago)
- `dossiers/Kuklinski_Viking_Panama.md` (12.1h ago)
- `dossiers/Ely_Darrow_Regent_3096289.md` (13.5h ago)
- `dossiers/DOSSIER_Loucks_SilverNova_May2027.md` (13.5h ago)
- `OpsCenter/collaboration/blackboard.md` (14.3h ago)

**Mission board:** 64 open (15 P0, 27 P1)
  - 🔴 MISSION-065: Pacific Voyage Blog
  - 🔴 MISSION-148: Telegram Feature Expansion
  - 🔴 MISSION-152: Phase E: Signal
  - 🔴 MISSION-196: Spencer United Group Desk call — DEN-FCO 12-pax air quote
  - 🔴 MISSION-214: Regent Portal On-Demand

### Su
<!-- COMMANDER-READY:END -->
