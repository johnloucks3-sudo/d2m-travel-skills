# Thunderbird OS — Architecture Reference
## Last updated: 2026-03-27

---

## System Components

| Component | File | Description |
|-----------|------|-------------|
| MCP Server | `travel_mcp_server.py` | 120+ tools, Google Workspace, browser, search · Port :8765 |
| REST API | `thunderbird_api.py` | FastAPI gateway, 40+ endpoints, IOC modules · Port :8766 |
| Telegram C2 | `thunderbird_telegram_c2.py` | Commander-only: /hale /dani /sss /scan /learn /voice /inbox |
| Telegram Client | `thunderbird_telegram.py` | Client-facing Dani bot, COS review gate |
| Dani Engine | `thunderbird_dani_engine.py` | 3-phase: Aggregate → Artist → Advocate |
| Learning Compiler | `thunderbird_learning.py` | Captures diffs, extracts principles, injects into personas |
| Voice Ledger | `thunderbird_voice_ledger.py` | Per-client/tier voice rules, feeds Dani/EXEC/A6 |
| Staff Summary Sheet | `thunderbird_sss.py` | USAF AF1768 formal coordination, CONCUR/NON-CONCUR |
| Dossier Scanner | `thunderbird_dossier_scanner.py` | Proactive gap detection, morning briefing alerts |
| Commander Inbox | `thunderbird_commander_inbox.py` | Scans johnloucks3, classifies, tasks, drafts replies |
| Client Portal | `portal/server.py` | Magic link auth, trip dashboard, contact form · Port :8780 |
| Template Engine | `templates/` | Jinja2 → WeasyPrint PDF. Hotel guide, proposals, quotes. See `templates/CLAUDE.md` |
| Batch Runner | `thunderbird_batch_run.py` | Off-peak Claude Code headless tasks, 13 batch jobs |
| n8n Workflows | `deploy/n8n/` | 16 automation workflows, scheduled triggers → API → Telegram |
| D2M Drive Vault | — | TITAN_BOOKINGS_VAULT — canonical booking archive |

---

## Infrastructure

- **YOGA** (192.168.1.198) — primary server: Claude CLI, MCP :8765, REST :8766, cloudflared
- **Chromebook** (100.115.92.196) — ChromeOS Linux container, isolated from home LAN
- **Cloudflare Tunnel** — bridges Chromebook to Yoga MCP
- **Domains:** `mcp.d2mluxury.quest` · `api.d2mluxury.quest` · `portal.d2mluxury.quest`
- **Service account:** `dreams2memories@d2m-python-pipeline.iam.gserviceaccount.com`
- **OS on Yoga:** openSUSE Tumbleweed (reinstalled March 2026)

---

## Agent Teams (Experimental)

Requires `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`.

- **Staff Meeting:** COS spawns A2/A3/A5/A9 in parallel → synthesizes unified brief
- **Client Research:** A2 intel + A3 logistics + A9 cost → EXEC proposal narrative
- Use for highest-complexity multi-domain work only; `consult_persona` MCP tool for lightweight queries

```
# From within a Claude Code session:
"Create a team with A2, A3, A9 to research Mediterranean options for the Kuklinski group"
claude --agent wing-coordinator
```

---

## Legacy Name Mapping

`TITAN` → COS · `Echo` → A3 · `Radar` → A2 · `A10/A4/A11` → COS
