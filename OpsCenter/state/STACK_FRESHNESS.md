# STACK FRESHNESS — Readiness Ladder Report
*Generated 2026-06-24T12:15:18.508342+00:00 · mode `daily` · ADVISORY (read-only)*

SO: `SO_READINESS_LADDER_FRESHNESS_20260621.md` — v1 RECOMMENDS demotions; executes nothing.

## Init-Context Footprint (§2)

**19,719 tokens** of Active-Duty auto-load (target ≤ 15,000) → **RED**

| Auto-load file | est tokens |
|---|---|
| `/home/john/Thunderbird/Personas/hale_cos.md` | 9,667 |
| `/home/john/.claude/projects/-home-john-Thunderbird/memory/MEMORY.md` | 4,365 |
| `/home/john/Thunderbird/hale_state.json` | 3,670 |
| `/home/john/Thunderbird/hale_brief.md` | 1,205 |
| `/home/john/Thunderbird/OpsCenter/session_context_latest.md` | 810 |

## Inventory & Recommended Tiers

996 scripts + 412 systemd units = **1408 items**

| Recommended tier | count |
|---|---|
| ACTIVE DUTY | 1169 |
| a) NATIONAL GUARD | 143 |
| b) RESERVE | 83 |
| c) RETIRED-ACTIVE-RESERVE | 13 |
| d) RETIRED COMPLETELY | 0 |

Demotion candidates: **239** · actionable this `daily`: **0**

## Top Demotion Candidates (coldest first)

| Item | Kind | → Tier | Age | Reason |
|---|---|---|---|---|
| `~/.config/systemd/user/cost-openrouter.service` | unit | c) RETIRED-ACTIVE-RESERVE | — | ExecStart target missing: /home/john/Thunderbird/core/cost_dashboard/collectors/openrouter.py — orphan unit |
| `~/.config/systemd/user/cost-poe.service` | unit | c) RETIRED-ACTIVE-RESERVE | — | ExecStart target missing: /home/john/Thunderbird/core/cost_dashboard/collectors/poe_usage.py — orphan unit |
| `~/.config/systemd/user/d2m-dca-den.service` | unit | c) RETIRED-ACTIVE-RESERVE | — | ExecStart target missing: /home/john/d2m-dca-den/run_daily.sh — orphan unit |
| `~/.config/systemd/user/d2m-intel-telegram.service` | unit | c) RETIRED-ACTIVE-RESERVE | — | ExecStart target missing: /home/john/Thunderbird//home/john/Thunderbird/core/communication/thunderbird_intel_telegram.py — orphan unit |
| `~/.config/systemd/user/d2m-telegram.service` | unit | c) RETIRED-ACTIVE-RESERVE | — | ExecStart target missing: /home/john/Thunderbird/thunderbird_telegram.py — orphan unit |
| `~/.config/systemd/user/kuklinski-jul15-trigger.service` | unit | c) RETIRED-ACTIVE-RESERVE | — | ExecStart target missing: /home/john/Thunderbird/OpsCenter/kuklinski_jul15_creative_chain_trigger.py — orphan unit |
| `~/.config/systemd/user/mapbox-mcp.service` | unit | c) RETIRED-ACTIVE-RESERVE | — | ExecStart target missing: /home/john/Thunderbird/mcps/mapbox/node_modules/.bin/mcp-server — orphan unit |
| `~/.config/systemd/user/mcleod-daily-brief.service` | unit | c) RETIRED-ACTIVE-RESERVE | — | ExecStart target missing: /home/john/Thunderbird/scripts/mcleod_daily_itinerary.py — orphan unit |
| `~/.config/systemd/user/poe-auth-check.service` | unit | c) RETIRED-ACTIVE-RESERVE | — | ExecStart target missing: /home/john/Thunderbird/scripts/check_poe_health.py — orphan unit |
| `~/.config/systemd/user/poe-burn-monitor.service` | unit | c) RETIRED-ACTIVE-RESERVE | — | ExecStart target missing: /home/john/Thunderbird/core/cost_dashboard/daemons/poe_burn_monitor.py — orphan unit |
| `~/.config/systemd/user/reverie-api.service` | unit | c) RETIRED-ACTIVE-RESERVE | — | ExecStart target missing: /home/john/Thunderbird/storage/reverie/api/.venv_new/bin/uvicorn — orphan unit |
| `~/.config/systemd/user/thunderbird-hooks.service` | unit | c) RETIRED-ACTIVE-RESERVE | — | ExecStart target missing: /home/john/Thunderbird/Thunderbird/thunderbird_hooks_receiver.py — orphan unit |
| `~/.config/systemd/user/thunderbird-watch-officer.service` | unit | c) RETIRED-ACTIVE-RESERVE | — | ExecStart target missing: /home/john/Thunderbird/OpsCenter/watch_officer_groq.sh — orphan unit |
| `scripts/render_nancy_lyons_email.py` | script | b) RESERVE | 99.9d | orphan (0 inbound refs) + cold 100d |
| `scripts/create_html_drafts.py` | script | b) RESERVE | 95.6d | orphan (0 inbound refs) + cold 96d |
| `scripts/draft_ten_weeks_later.py` | script | b) RESERVE | 94.6d | orphan (0 inbound refs) + cold 95d |
| `scripts/render_dani_validation_emails.py` | script | b) RESERVE | 90.5d | orphan (0 inbound refs) + cold 91d |
| `OpsCenter/notify_commander.sh` | script | b) RESERVE | 86.5d | orphan (0 inbound refs) + cold 87d |
| `OpsCenter/create_tokyo_draft.py` | script | b) RESERVE | 85.5d | orphan (0 inbound refs) + cold 86d |
| `OpsCenter/atomic_dossier_commit.py` | script | b) RESERVE | 84.0d | orphan (0 inbound refs) + cold 84d |
| `OpsCenter/a7_email_scorer.py` | script | b) RESERVE | 83.6d | orphan (0 inbound refs) + cold 84d |
| `OpsCenter/api_test.py` | script | b) RESERVE | 83.5d | orphan (0 inbound refs) + cold 84d |
| `OpsCenter/keep_to_drive_sync.py` | script | b) RESERVE | 83.5d | orphan (0 inbound refs) + cold 84d |
| `OpsCenter/pinecone_connector.py` | script | b) RESERVE | 83.5d | orphan (0 inbound refs) + cold 84d |
| `OpsCenter/tool_validator.py` | script | b) RESERVE | 83.5d | orphan (0 inbound refs) + cold 84d |

*Thresholds (days since last activity): NG≥14 · Reserve≥44 · Retired-reserve≥134 · Retired-complete≥224. Demotion requires 0 inbound refs AND cold. Protected/referenced/fresh stay ACTIVE.*
