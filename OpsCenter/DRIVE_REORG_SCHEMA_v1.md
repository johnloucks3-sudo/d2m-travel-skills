# THUNDERBIRD DRIVE REORGANIZATION SCHEMA v1.0
## COL Victoria "Iron Vic" Hale, COS — 2026-04-04

> *"Before the reorg: 18.5 GB scattered. After: clean hierarchy, deduplicated, archived."*

---

## CURRENT TOPOGRAPHY

```
/home/john/
├── Thunderbird/          ████████████ 12 GB  (Main OS)
│   ├── backups/          ███ 685 MB
│   ├── browser_profiles/ ██ 479 MB  
│   ├── reverie/          ██ 452 MB
│   ├── output/           █  193 MB
│   ├── screenshots/      █  168 MB
│   ├── thunderbird_p*zip █  140 MB
│   ├── logs/             .7 68 MB
│   ├── archive/          .5 46 MB
│   ├── __pycache__       .5 4.7 MB
│   ├── persona_memory/   .1 1.3 MB
│   └── [267 .py files scattered at root]
│
├── D2M/                  ██████ 6.5 GB  (Business Documents)
│
├── Personal/              █ 269 MB  (Private/Non-D2M)
│
├── playground-venv/       █ 151 MB  (Python environments)
├── .cache/               █  (system cache, unmanaged)
├── Downloads/            .3 31 MB  (download staging)
├── Documents/            .1 6.5 MB  (system docs folder)
└── Pictures/             .1 712 KB  (images)
```

## PROPOSED ARCHITECTURE

```
/home/john/
│
├── Thunderbird/                    ← THE OPERATING SYSTEM (12 GB → ~11 GB after cleanup)
│   ├── .env                         # Environment config
│   ├── .git/                        # Version control
│   │
│   ├── core/                        ← 267 Python files → organized by domain
│   │   ├── email/                   # Gmail, email intelligence, draft creation
│   │   │   ├── thunderbird_gmail.py         # Gmail MCP module
│   │   │   ├── thunderbird_dani_email.py    # Dani's email sweep
│   │   │   ├── thunderbird_commander_inbox.py # Commander inbox scanner
│   │   │   ├── thunderbird_email_intel.py   # Email intelligence
│   │   │   ├── thunderbird_email_maintenance.py # Email maintenance engine (NEW)
│   │   │   └── thunderbird_email_classifier.py
│   │   ├── mcp/                     # MCP servers and connectors
│   │   │   ├── thunderbird_mcp_connector.py
│   │   │   ├── thunderbird_mcp_gateway.py
│   │   │   ├── goose_mcp_server.py
│   │   │   ├── goose_mcp_proxy.py
│   │   │   └── travel_mcp_server.py
│   │   ├── booking/                 # Booking management, TESS integration
│   │   │   ├── thunderbird_tess.py
│   │   │   ├── thunderbird_dossier.py
│   │   │   ├── thunderbird_guest_forms.py
│   │   │   └── thunderbird_reconciliation.py
│   │   ├── intel/                   # Research, OSINT, monitoring
│   │   │   ├── thunderbird_world_intel.py
│   │   │   ├── thunderbird_competitive_surveillance.py
│   │   │   ├── thunderbird_incubator.py
│   │   │   ├── thunderbird_innovation_scanner.py
│   │   │   ├── thunderbird_price_monitor.py
│   │   │   ├── thunderbird_tech_monitor.py
│   │   │   └── thunderbird_academic_scanner.py
│   │   ├── communication/           # Telegram, SMS, notifications, voice
│   │   │   ├── thunderbird_telegram_c2.py
│   │   │   ├── thunderbird_telegram_tools.py
│   │   │   ├── thunderbird_telegram_pager.py
│   │   │   ├── thunderbird_sms.py
│   │   │   ├── thunderbird_whatsapp.py
│   │   │   └── thunderbird_dani_voice.py
│   │   ├── client/                  # Client-facing tools, quotes, proposals
│   │   │   ├── thunderbird_validation.py
│   │   │   ├── thunderbird_quote_render.py
│   │   │   ├── thunderbird_presend_evaluator.py
│   │   │   ├── thunderbird_survey.py
│   │   │   └── thunderbird_followup_reminders.py
│   │   ├── learning/                # Learning compiler, context packs
│   │   │   ├── thunderbird_learning.py
│   │   │   ├── thunderbird_conversation_learner.py
│   │   │   ├── thunderbird_conversation_state.py
│   │   │   └── context_engineering/
│   │   ├── scheduling/              # Scheduler, calendar, reminders
│   │   │   ├── thunderbird_scheduler.py
│   │   │   ├── thunderbird_calendar_sync.py
│   │   │   ├── thunderbird_anchor_dates.py
│   │   │   └── thunderbird_fpd_alert.py
│   │   ├── watchtower/              # Monitoring, health checks, alerting
│   │   │   ├── thunderbird_tasking_watcher.py    # File watcher v3
│   │   │   ├── thunderbird_heartbeat.py
│   │   │   ├── thunderbird_health.py
│   │   │   ├── thunderbird_overwatch.py
│   │   │   └── git_commit_alert.py
│   │   ├── ai_infra/                # CrewAI, A2A, personas, multi-agent
│   │   │   ├── thunderbird_a2a.py
│   │   │   ├── thunderbird_personas.py
│   │   │   ├── thunderbird_persona_memory.py
│   │   │   ├── thunderbird_crewai.py
│   │   │   ├── thunderbird_switchblade.py
│   │   │   └── crewai_bridge/
│   │   ├── travel/                  # Travel search, booking APIs
│   │   │   ├── thunderbird_flight_search.py
│   │   │   ├── thunderbird_hotel_search.py
│   │   │   ├── thunderbird_tour_search.py
│   │   │   ├── thunderbird_dining.py
│   │   │   └── thunderbird_transfers.py
│   │   └── ops/                     # OpsCenter, dispatchers, utilities
│   │       ├── OpsCenter/           # All dispatcher and routine scripts
│   │       ├── thunderbird_backup_verify.py
│   │       └── thunderbird_monthly_archive.py
│   │
│   ├── data/                        ← DATA & STATE
│   │   ├── dossiers/                # Client dossiers (30 files)
│   │   ├── persona_memory/          # Persona memory files
│   │   ├── email_conditioning/      # Email routing JSON configs
│   │   ├── config/                  # System configuration
│   │   └── intel/                   # Intel scans (87 files)
│   │
│   ├── archive/                     ← ARCHIVED CODE (46 MB)
│   │   └── [29 legacy/deprecated files - do not delete]
│   │
│   ├── storage/                     ← LARGE STATIC ASSETS (moved here)
│   │   ├── backups/                 # 685 MB — moved from root
│   │   ├── browser_profiles/        # 479 MB — moved from root  
│   │   ├── reverie/                 # 452 MB - moved from root
│   │   ├── output/                  # 193 MB — generated PDFs/HTML
│   │   ├── screenshots/             # 168 MB — automation screenshots
│   │   ├── logs/                    # 68 MB — system logs
│   │   └── cache/                   # 28 MB — temp cache
│   │
│   ├── review/                      ← COMMANDER REVIEW QUEUE
│   │   └── [All .md assessments synced here by rule]
│   │
│   ├── docs/                        ← DOCUMENTATION (1.9 MB)
│   │   ├── CLAUDE.md                # Core prompt
│   │   ├── THUNDERBIRD_MASTER_PLAN.md
│   │   └── [34 doc files]
│   │
│   └── deploy/                      ← DEPLOYMENT
│       ├── systemd/                 # .service and .timer files
│       └── deploy scripts
│
├── D2M/                            ← BUSINESS DOCUMENTS (6.5 GB)
│   ├── contracts/                   # Client agreements, vendor contracts
│   ├── invoices/                    # Financial records
│   ├── marketing/                   # Brand assets, marketing materials
│   └── clients/                     # Per-client document folders
│
├── Personal/                       ← PRIVATE (269 MB)
│   └── Credentials/                # Personal credential store
│
└── scratch/                        ← TEMPORARY / SANDBOX
    ├── temp_*.py                    # All temp scripts moved here
    ├── test_*.py
    └── playground-venv/             # Python venvs
```

## REORG STRATEGY

### Phase 1: CREATE HIERARCHY (1 min)
```bash
mkdir -p Thunderbird/core/{email,mcp,booking,intel,communication,client,learning,scheduling,watchtower,ai_infra,travel,ops}
mkdir -p Thunderbird/storage/{backups,browser_profiles,reverie,output,screenshots,logs,cache}
mkdir -p Thunderbird/review
mkdir -p Thunderbird/deploy/systemd
```

### Phase 2: MOVE LARGE ASSETS (non-breaking)
```bash
mv Thunderbird/backups/* Thunderbird/storage/backups/
mv Thunderbird/browser_profiles/* Thunderbird/storage/browser_profiles/
mv Thunderbird/reverie/* Thunderbird/storage/reverie/
mv Thunderbird/output/* Thunderbird/storage/output/
mv Thunderbird/screenshots/* Thunderbird/storage/screenshots/
```

### Phase 3: ORGANIZE PYTHON FILES (domain sort)
```bash
# Email
mv thunderbird_gmail.py thunderbird_dani_email.py thunderbird_commander_inbox.py thunderbird_email_intel.py thunderbird_email_maintenance.py thunderbird_email_classifier.py thunderbird_inbox_cleanup_daily.py core/email/

# MCP
mv thunderbird_mcp_connector.py thunderbird_mcp_gateway.py goose_mcp_server.py goose_mcp_proxy.py travel_mcp_server.py core/mcp/

# Watchtower
mv thunderbird_tasking_watcher.py thunderbird_heartbeat.py thunderbird_health.py thunderbird_overwatch.py git_commit_alert.py core/watchtower/

# etc.
```

### Phase 4: SYMLINKS (zero-break)
After moving, create symlinks at root for any imports that depend on original paths.
Systemd service files updated to point to new locations.

### Phase 5: CLEANUP
- Delete `__pycache__/` (4.7 MB — regenerates)
- Archive old zip files
- Move temp scripts to `scratch/`
- Clean up Downloads

## IMPACT

| Metric | Before | After |
|--------|--------|-------|
| Python files at root | 267 | ~5 |
| Directory depth | 2 levels | 3-4 levels (organized) |
| Import path clarity | All at root | By domain |
| Storage organization | Mixed | Separated code/data/assets |
| Commander visibility | Partial | Full (review/ dir) |
| Systemd paths | .venv (broken) | /usr/bin/python3 (fixed) |

---
*Schema v1.0 — Hale, COS | Awaiting Commander approval*
