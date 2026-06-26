# THUNDERBIRD BLACKBOARD — HALE ↔ WING COMMUNICATION CHANNEL
# CC (Hale) writes HALE→OC. OC writes OC→HALE. Both read at session start.
# Auto-status section updated by blackboard_sync.py.
# Updated: 2026-06-01 | Architecture: 5-Persona (SO-2026-05-30)

---

## AUTO-STATUS [updated by blackboard_sync.py]

```
=== THUNDERBIRD BLACKBOARD [2026-06-01 08:46 MT] ===
Budget: Claude UNKNOWN | OpenCode GREEN | Groq UNKNOWN | Deepseek UNKNOWN | Poe:675,320pts($20.46)
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
## COMMANDER-READY (2026-06-25 22:36 UTC)
### Last 24h decisions (0)
- (none)

### Open P0/P1 nags (5)
- [P0] MCLEOD-2984034-FPD-TRIGGER
- [P0] MISSION-COMMANDER-196-CALL
- [P1] MCLEOD-SILVER-MUSE-WELCOME-HOME
- [P1] MCLEOD-2984034-TP11-SEND
- [P0] LOUCKS-3122006-FPD-ALERT
- (none)

### Blockers (0)
- (none)

### Startup hook
## STATE BRIDGE BRIEFING — 2026-06-25 16:36

### Since last session (2026-06-25 21:45:22 → still open)

**Recent commits (no in-DB delta — showing git log):**
- `119d51e9b` feat(poe): full alias coverage, points scraper, daily 0600 MT timer  _78 minutes ago_
- `946fce13d` fix(poe): rotate key, fix file-over-env priority, update broken model IDs  _2 hours ago_
- `b837be604` feat(poe): add nano-banana-pro + GPT nano family, correct image-model labels  _2 hours ago_
- `45b8c188a` feat(poe): update model table — Commander's full alias set  _2 hours ago_
- `ddd92500d` feat(poe): open model selection — any Poe model ID works, add deepseek-v4/kimi/grok4 aliases  _2 hours ago_

_No changes since last session — continuing clean._

### Current state snapshot
**Most recently touched watched files:**
- `hale_state.json` (0s ago)
- `OpsCenter/collaboration/blackboard.md` (1.3h ago)
- `dossiers/Nichols_Regent_3078056.md` (7.8h ago)
- `hale_brief.md` (10.6h ago)
- `dossiers/Loucks_Regent_Grandeur_3122006.md` (18.6h ago)
- `dossiers/Ely_Darrow_Regent_3096289.md` (18.7h ago)
- `OpsCenter/opencode_memory.md` (23.8h ago)
- `dossiers/DOSSIER_DoorCounty_SisterBay_Sep2026.md` (1.1d ago)

**Mission board:** 38 open (8 P0, 21 P1)
  - 🔴 MISSION-065: Pacific Voyage Blog
  - 🔴 MISSION-148: Telegram Feature Expansion
  - 🔴 MISSION-152: Phase E: Signal
  - 🔴 MISSION-196: Spencer United Group Desk call — DEN-FCO 12-pax air quote
  - 🔴 MISSION-214: Regent Portal On-Demand

### Suggested next actions
1. No 
<!-- COMMANDER-READY:END -->
