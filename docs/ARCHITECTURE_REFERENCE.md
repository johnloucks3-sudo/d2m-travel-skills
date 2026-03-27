# Thunderbird OS — Architecture Reference

## Component Table

| Component | Description |
|-----------|-------------|
| MCP Server | `travel_mcp_server.py` — 120+ tools, Google Workspace, browser, search |
| REST API | `thunderbird_api.py` — FastAPI gateway, 40+ endpoints including IOC modules |
| Telegram C2 | `thunderbird_telegram_c2.py` — Commander-only: /hale /dani /sss /scan /learn /voice /inbox |
| Telegram Client | `thunderbird_telegram.py` — Client-facing Dani bot, COS review gate |
| Dani Engine | `thunderbird_dani_engine.py` — 3-phase: Aggregate → Artist → Advocate |
| Learning Compiler | `thunderbird_learning.py` — Captures diffs, extracts principles, injects into personas |
| Voice Ledger | `thunderbird_voice_ledger.py` — Per-client/tier voice rules, feeds Dani/EXEC/A6 |
| Staff Summary Sheet | `thunderbird_sss.py` — USAF AF1768 formal coordination, CONCUR/NON-CONCUR |
| Dossier Scanner | `thunderbird_dossier_scanner.py` — Proactive gap detection, morning briefing alerts |
| Commander Inbox | `thunderbird_commander_inbox.py` — Scans johnloucks3, classifies, tasks, drafts replies |
| Client Portal | `portal/server.py` — Magic link auth, trip dashboard, contact form (:8780) |
| Template Engine | Jinja2 → WeasyPrint PDF. Hotel guide, proposals, quotes. See `templates/CLAUDE.md` |
| Batch Runner | `thunderbird_batch_run.py` — Off-peak Claude Code headless tasks, 13 batch jobs |
| n8n Workflows | `deploy/n8n/` — 16 automation workflows, scheduled triggers → API → Telegram |
| D2M Drive Vault | TITAN_BOOKINGS_VAULT — canonical booking archive |

## Infrastructure

**YOGA** (192.168.1.198) is primary — runs all services, Claude CLI, MCP :8765, REST :8766, cloudflared.
**Domains:** `mcp.d2mluxury.quest` · `api.d2mluxury.quest` · `portal.d2mluxury.quest` (:8780)
**Service account:** `dreams2memories@d2m-python-pipeline.iam.gserviceaccount.com`

## MCP Failure Playbook

Retry once → try alternate tool → alert John with error + next steps. Don't spin.
Google API quota: wait 60s, retry once, then alert.
