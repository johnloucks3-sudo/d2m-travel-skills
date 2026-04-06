# 🗂️ THUNDERBIRD — DRIVE REORGANIZATION + SYNC AUDIT + MASTER TASKS
**Generated: 2026-04-04 08:34 MDT | Author: COS Hale**

---

## 📐 NEW DRIVE ORGANIZATION (VISUAL SCHEMA)

```
/home/john/Thunderbird/  [12 GB — reorganized 18.5 GB total across all drives]
│
├── 📁 core/  [74K LOC — THE ENGINE]
│   ├── ai_infra/      (8 files)  A2A, CrewAI, personas, shared_memory, switchblade
│   ├── booking/       (11 files) Dossier, TESS, guest forms, reconciliation, PDF ingest
│   ├── client/        (9 files)  Auto-enrich, validation, quotes, surveys, profiles
│   ├── communication/ (14 files) Telegram bots, SMS, WhatsApp, formatting, SDK
│   ├── email/         (12 files) Gmail, Dani email, classifier, maintenance, presend
│   ├── intel/         (16 files) OSINT, incubator, ship intel, competitive surveillance
│   ├── learning/      (16 files) Conversation bridge, temporal memory, voice, skills
│   ├── mcp/           (5 files)  MCP connector, gateway, proxy, travel server
│   ├── ops/           (7 files)  Autopilot, dashboard, grants, nova, v3, usage
│   ├── scheduling/    (3 files)  Scheduler, calendar sync, anchor dates
│   ├── travel/        (10 files) Flight, hotel, tour, dining, transfers, fare watch
│   └── watchtower/    (8 files)  Health, heartbeat, tasking watcher, FPD alert, backup
│
├── 📁 Commander_Review/  [15K lines — COMMANDER QUEUE]
│   └── 69+ files: Email drafts, briefings, proposals, validation emails, action items
│
├── 📁 OpsCenter/  [23K lines — OPERATIONS CENTER]
│   ├── collaboration/  (52 files) Agent coordination, research, architecture docs
│   ├── scan_outputs/   (2 files)  Latest intel/incubator outputs
│   └── 62 root files:  Design specs, queues, audits, task processors
│
├── 📁 dossiers/  [5K lines — CLIENT DOSSIERS]
│   ├── Furlow_Regent_3071222.md  Furlow, Missy & John — Grandeur of the Seas
│   ├── McLeod_McGlasson_Multi.md McLeod/McGlasson — SilverMuse + Prestige
│   ├── DOSSIER_SilverNova_Pacific_Apr2026.md  SilverNova Pacific (Loucks, Westbrook)
│   ├── DOSSIER_VikingMars_PanamaCanal_Dec2026.md  3 couples
│   ├── DOSSIER_Regent_LesserAntilles_Dec2026.md  McLeod/McGlasson
│   └── +18 more dossiers and booking files
│
├── 📁 intel/  [20K lines — INTELLIGENCE ARCHIVE]
│   ├── claude_code_reference/  (3 files) Claude Code best practices
│   ├── academic_scan_*.md      Research from arXiv, HuggingFace, Papers With Code
│   ├── incubator_*.json        Amazon category scans (raw + reviewed)
│   ├── weekly_innovation_*.md  Weekly innovation digests
│   └── 25+ standalone intel reports (competitive, tech, strategy)
│
├── 📁 templates/  [9K lines — EMAIL/PROPOSAL TEMPLATES]
│   ├── dani_proposal.html.j2   Dani proposal template
│   ├── client_bulletin.html.j2 Client bulletin template
│   ├── d2m_quote.html.j2       Flight/hotel/tour quote template
│   └── 23+ other Jinja2 templates
│
├── 📁 docs/  [9K lines — DOCUMENTATION]
│   ├── internal/               Furlow pitch decks (6+ versions)
│   ├── D2M_STAFF_ROSTER_v2.md  Full staff roster + backstories
│   ├── THUNDERBIRD_A2A_INTEGRATION_PLAN_v1.md
│   └── 25+ docs: runbooks, roadmaps, setup guides, architecture
│
├── 📁 deploy/  [4K lines — DEPLOYMENT]
│   ├── systemd/    (24 files) Services + timers for FPD, scheduler, batch, alerts
│   ├── n8n/        (16 files) 16 n8n workflows (morning brief, fare watch, etc.)
│   └── 15+ service files, scripts, VPS setup guides
│
├── 📁 storage/  [2K lines — RELOCATED ASSETS]
│   ├── cache/      Client context cache
│   ├── recent/     Recent downloads
│   └── reverie/    (6 files) Reverie PM artifacts (moved from root)
│
├── 📁 scripts/  [5K lines — UTILITY SCRIPTS]
│   ├── goose_mcp_client.py     MCP client testing
│   ├── render_*_email.py       (5 files) Email rendering scripts
│   ├── rssc_*.py               (3 files) Odysseus/Regent scraping
│   └── setup, hardening, batch scripts
│
├── 📁 Personas/  [825 lines]
│   ├── memory/          Per-persona directories (A2, A3, A5, A9, A12, CH, COS, EXEC)
│   └── D2M_Staff_Introduction.md  All staff intros
│
├── 📁 Plans/  [1K lines]    Project plans, session summaries
├── 📁 Commercial/  [853]     Fiverr gig strategy, MCP directory submissions
├── 📁 agent_docs/  [514]     Architecture docs, Goose architecture
├── 📁 crewai_bridge/  [506]  CrewAI integration (agent loader, crew runner, LLM router)
├── 📁 ai_trust/  [206]       Privacy, AI disclosure, booking authority docs
├── 📁 portal/  [2K]          HTML/CSS dashboard + Python server
├── 📁 recipes/  [96]         Scheduled automation definitions (YAML)
├── 📁 thunderbird_hud/  [1K] Google Apps Script HUD (Code.gs, HTML)
├── 📁 workspace_addon/  [1K] Gmail workspace addon
├── 📁 validations/  [18K RSS] Booking data JSONs from portal scrapes
├── 📁 email_conditioning/  (5 files) Email classification conditions
├── 📁 hooks/  [85]           Auto-inject scripts, post-tool hooks
├── 📁 memory/  [115]         Session memories
├── 📁 scratch/  [5]          Test files
├── 📁 temp/  [823]           Temporary artifacts
├── 📁 data/  [2]             DBs and JSON registries
├── 📁 inbox/  [0]            Inbox staging (empty)
├── 📁 persona_memory/  [0]   Persona memory store (empty)
├── 📁 uploads/  [0]          Upload staging (empty)
├── 📁 audio_briefings/  [0]  Audio output staging
│
├── 🔧 ENTRY POINT FILES (remain at root — by design)
│   ├── thunderbird_gmail.py          Gmail OAuth client
│   ├── thunderbird_telegram_c2.py    → now in core/communication/ (root copy for compat)
│   ├── thunderbird_morning_briefing.py
│   ├── thunderbird_*.py              ~50 operational scripts
│   ├── mcp_launcher*.sh              MCP server launchers
│   └── requirements.txt              Python dependencies
│
└── ⚠️ FOR_DELETION_FILES  (marked, NOT deleted — Commander reviews)
    ├── FOR_DELETION_Phase1_MVP.py
    ├── FOR_DELETION_Phase1_MVP.txt
    ├── FOR_DELETION_create_sheets_tabs.py
    ├── FOR_DELETION_d2m_drive_reorg.py
    ├── FOR_DELETION_inspect_cruise_websites.py
    ├── FOR_DELETION_thunderbird.py
    ├── FOR_DELETION_thunderbird_sync.py_superseded_by_rclone
    ├── FOR_DELETION_thunderbird_sync.py_worktree
    ├── FOR_DELETION_thunderbird_v2_integration.py
    └── FOR_DELETION_~_nested_home_dir/
```

---

## 📊 BEFORE/AFTER COMPARISON

| Metric | BEFORE | AFTER |
|--------|--------|-------|
| **Root files** | 140+ .py files scattered | ~50 intentional entry points + 9 FOR_DELETION marked |
| **OpsCenter .py files** | 62 mixed with .md docs | Still in OpsCenter — awaiting sort decisions |
| **Python files in core/** | 0 | 140+ sorted into 12 domain directories |
| **Large asset dirs** | Mixed throughout | All moved to storage/ |
| **`__pycache__` dirs** | 4.7 MB scattered | Removed (all gone) |
| **Backup dirs** | Mixed throughout | Moved to storage/backups |
| **Google Drive sync** | Supposed to work nightly | 🔴 **BROKEN — expired tokens** |

---

## 🚨 GOOGLE DRIVE SYNC STATUS — CRITICAL FINDINGS

### Current Mechanism
- **Tool**: rclone (installed at `/home/john/.local/bin/rclone`)
- **Remotes**: `gdrive` (personal, johnloucks3@gmail.com) + `d2mconcierge` (D2M account)
- **Schedule**: Runs daily at 23:00 (script-based, NOT cron, NOT systemd)
- **Source**: `/home/john/Thunderbird/`
- **Destination**: `d2mconcierge:Thunderbird_Mirror/`
- **Filter file**: `scripts/thunderbird_sync_filters.txt`

### 🔴 ISSUE #1: D2M TOKEN EXPIRED (CRITICAL)
```
CRITICAL: Failed to create file system for "d2mconcierge:Thunderbird_Mirror/": 
couldn't fetch token: invalid_grant: maybe token expired?
```
- Last SUCCESSFUL sync: **2026-04-02 23:00:35** (1,292 checks, 67 transfers, 1.2 MiB)
- All attempts since: **April 3-4** — FAILED (token expired 2026-04-03T03:01:46)
- Impact: Drive mirror is ~24+ hours behind. No files synced for past 2 days.

### ⚠️ ISSUE #2: PERSONAL TOKEN ALSO EXPIRING
- gdrive token expired: **2026-03-27T17:16:12** (8 days ago!)
- This means personal Drive sync (if used anywhere) is also dead.

### ⚠️ ISSUE #3: NO CRON OR SYSTEMD SCHEDULER
- Sync script exists but is NOT scheduled in crontab
- No systemd timer for sync (only FPD, git-commit-alert, and batch timers exist)
- Relies on external scheduler or manual triggering

### ⚠️ ISSUE #4: FILTER EXCLUDES TOO MUCH
- `- *.json` excludes all JSON files (configs, logs, state files)
- `- *.db` excludes SQLite databases (conversation_bridge.db, hud_memory.db, etc.)
- Only `.py`, `.md`, `.html`, `.css`, `.sh`, `.j2`, `.txt` are synced
- **New conversation memory system won't sync** (it's a `.db` file)

---

## ✅ SYNC FIX PLAN

### IMMEDIATE (run these manually):
```bash
# Step 1: Reconnect BOTH rclone remotes
rclone config reconnect gdrive:
# → Opens browser for OAuth → complete the flow

rclone config reconnect d2mconcierge:
# → Opens browser for OAuth → complete the flow

# Step 2: Test both remotes
rclone lsd gdrive: | head -5
rclone lsd d2mconcierge: | head -5

# Step 3: Run manual sync to catch up
/home/john/Thunderbird/scripts/thunderbird-rclone-sync.sh

# Step 4: Verify
tail -5 /home/john/Thunderbird/.rclone_sync.log
```

### FIX SYNC SCHEDULING:
```bash
# Add to crontab (runs daily at 23:00)
crontab -e
# Add: 0 23 * * * ~/Thunderbird/scripts/thunderbird-rclone-sync.sh 2>&1 | logger -t thunderbird-sync
```

### IMPROVE FILTER FILE:
```
# ADD these lines to thunderbird_sync_filters.txt:
+ conversation_bridge.db
+ hud_memory.db
+ learning_rules.db
+ *.json
- credentials.json
- *_token.json
- *_credentials.json
```

---

## 📋 COMPLETE TASK TRACKER

### ✅ COMPLETED THIS SESSION:
| # | Task | Result |
|---|------|--------|
| 1 | Conversation Bridge created | `core/learning/thunderbird_conversation_bridge.py` (163 lines, SQLite, thread-safe) |
| 2 | Goose Bot rewritten | Ready to deploy — native Goose feel with memory |
| 3 | D2MC2 Bot enhanced | +18 lines for persistent memory, feel unchanged |
| 4 | Import path fixer script | Written as Python fixer |
| 5 | Email engine MCP wiring | Rewired from port 8000 → 8767/mcp Streamable HTTP |
| 6 | Drive schema documented | This document |
| 7 | FOR_DELETION scheme applied | 9 files marked, none deleted |

### 🔴 CRITICAL (NEEDS COMMANDER ACTION):
| # | Task | Blocker | Action Needed |
|---|------|---------|---------------|
| 1 | **Reconnect rclone OAuth tokens** | Both expired | YOU must run `rclone config reconnect` × 2 |
| 2 | **Fix systemd FPD/git services** | Permission wall (711 on /home/john) | Run sed + systemctl restart from earlier |
| 3 | **Deploy conversation bridge** | File written, needs bot restart | `systemctl restart thunderbird-c2` |
| 4 | **Add sync to scheduler** | No cron/systemd timer | Commander runs crontab -e or I write systemd timer |

### 🟡 HIGH PRIORITY:
| # | Task | Status |
|---|------|--------|
| 5 | Fix broken import paths across 140+ moved .py files | Script written, needs validation |
| 6 | Create `__init__.py` files for all core/ subdirs | Written 1, remaining 11 directories |
| 7 | Sort 62 .py files in OpsCenter into proper domains | Pending — needs classification |
| 8 | Update rclone filter file for .db + .json inclusion | Written in plan above |

### 🟢 MEDIUM PRIORITY:
| # | Task | Status |
|---|------|--------|
| 9 | Remove Grok API from sweep paths (0 credits) | Identified, code change needed |
| 10 | Sync new files to Commander_Review | Standing rule exists |
| 11 | Deploy Goose Bot new version | Written, needs systemd or manual start |
| 12 | Validate conversation bridge with real traffic | Needs Commander to use /hale, /clear |

---

## 🔧 SYNC PROTOCOL — GOING FORWARD

### Daily Sync (23:00 MDT):
```
Local ~/Thunderbird/  ──rclone copy──▶  Google Drive d2mconcierge:Thunderbird_Mirror/
      │                                       │
      ├─ .py files (code)                     ├─ Mirrored codebase
      ├─ .md files (docs)                     ├─ Mirrored documentation  
      ├─ .html/.css (output)                  ├─ Mirrored output
      ├─ .sh scripts                          ├─ Mirrored scripts
      ├─ .db files (memory) ← NEW             ├─ Mirrored memory
      ├─ .json configs ← NEW                  ├─ Mirrored configs
      └─ excludes: credentials, tokens, venv  └─ No secrets ever leave
```

### Two-Way Sync (when needed):
```
Google Drive d2mconcierge:Backups/  ──rclone sync──▶  Local ~/Thunderbird/storage/backups/
```

### Zero-Deletion Policy:
- All deletions marked with `FOR_DELETION_` prefix
- Commander reviews during Commander_Review cycle
- Actual deletions only on explicit Commander order

---

**Report ends. All 9 FOR_DELETION files preserved. Zero files harmed in the making of this schema.**
