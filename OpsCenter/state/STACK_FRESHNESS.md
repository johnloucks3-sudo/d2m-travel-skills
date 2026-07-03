# STACK FRESHNESS — Readiness Ladder Report
*Generated 2026-07-03T12:15:22.399903+00:00 · mode `daily` · ADVISORY (read-only)*

SO: `SO_READINESS_LADDER_FRESHNESS_20260621.md` — v1 RECOMMENDS demotions; executes nothing.

## Init-Context Footprint (§2)

**23,517 tokens** of Active-Duty auto-load (target ≤ 15,000) → **RED**

| Auto-load file | est tokens |
|---|---|
| `/home/john/Thunderbird/Personas/hale_cos.md` | 9,994 |
| `/home/john/.claude/projects/-home-john-Thunderbird/memory/MEMORY.md` | 5,855 |
| `/home/john/Thunderbird/hale_state.json` | 4,772 |
| `/home/john/Thunderbird/hale_brief.md` | 2,056 |
| `/home/john/Thunderbird/OpsCenter/session_context_latest.md` | 839 |

## Inventory & Recommended Tiers

1143 scripts + 453 systemd units = **1596 items**

| Recommended tier | count |
|---|---|
| ACTIVE DUTY | 1311 |
| a) NATIONAL GUARD | 157 |
| b) RESERVE | 115 |
| c) RETIRED-ACTIVE-RESERVE | 13 |
| d) RETIRED COMPLETELY | 0 |

Demotion candidates: **285** · actionable this `daily`: **0**

## Top Demotion Candidates (coldest first)

| Item | Kind | → Tier | Age | Reason |
|---|---|---|---|---|
| `~/.config/systemd/user/cost-openrouter.service` | unit | c) RETIRED-ACTIVE-RESERVE | — | ExecStart target missing: /home/john/Thunderbird/core/cost_dashboard/collectors/openrouter.py — orphan unit |
| `~/.config/systemd/user/cost-poe.service` | unit | c) RETIRED-ACTIVE-RESERVE | — | ExecStart target missing: /home/john/Thunderbird/core/cost_dashboard/collectors/poe_usage.py — orphan unit |
| `~/.config/systemd/user/d2m-dca-den.service` | unit | c) RETIRED-ACTIVE-RESERVE | — | ExecStart target missing: /home/john/d2m-dca-den/run_daily.sh — orphan unit |
| `~/.config/systemd/user/d2m-intel-telegram.service` | unit | c) RETIRED-ACTIVE-RESERVE | — | ExecStart target missing: /home/john/Thunderbird//home/john/Thunderbird/core/communication/thunderbird_intel_telegram.py — orphan unit |
| `~/.config/systemd/user/d2m-tasking-watcher.service` | unit | c) RETIRED-ACTIVE-RESERVE | — | ExecStart target missing: /home/john/Thunderbird/OpsCenter/thunderbird_tasking_watcher.py — orphan unit |
| `~/.config/systemd/user/d2m-telegram.service` | unit | c) RETIRED-ACTIVE-RESERVE | — | ExecStart target missing: /home/john/Thunderbird/thunderbird_telegram.py — orphan unit |
| `~/.config/systemd/user/kuklinski-jul15-trigger.service` | unit | c) RETIRED-ACTIVE-RESERVE | — | ExecStart target missing: /home/john/Thunderbird/OpsCenter/kuklinski_jul15_creative_chain_trigger.py — orphan unit |
| `~/.config/systemd/user/mcleod-daily-brief.service` | unit | c) RETIRED-ACTIVE-RESERVE | — | ExecStart target missing: /home/john/Thunderbird/scripts/mcleod_daily_itinerary.py — orphan unit |
| `~/.config/systemd/user/poe-auth-check.service` | unit | c) RETIRED-ACTIVE-RESERVE | — | ExecStart target missing: /home/john/Thunderbird/scripts/check_poe_health.py — orphan unit |
| `~/.config/systemd/user/poe-burn-monitor.service` | unit | c) RETIRED-ACTIVE-RESERVE | — | ExecStart target missing: /home/john/Thunderbird/core/cost_dashboard/daemons/poe_burn_monitor.py — orphan unit |
| `~/.config/systemd/user/reverie-api.service` | unit | c) RETIRED-ACTIVE-RESERVE | — | ExecStart target missing: /home/john/Thunderbird/storage/reverie/api/.venv_new/bin/uvicorn — orphan unit |
| `~/.config/systemd/user/thunderbird-hooks.service` | unit | c) RETIRED-ACTIVE-RESERVE | — | ExecStart target missing: /home/john/Thunderbird/Thunderbird/thunderbird_hooks_receiver.py — orphan unit |
| `~/.config/systemd/user/thunderbird-watch-officer.service` | unit | c) RETIRED-ACTIVE-RESERVE | — | ExecStart target missing: /home/john/Thunderbird/OpsCenter/watch_officer_groq.sh — orphan unit |
| `scripts/render_nancy_lyons_email.py` | script | b) RESERVE | 108.9d | orphan (0 inbound refs) + cold 109d |
| `scripts/create_html_drafts.py` | script | b) RESERVE | 104.6d | orphan (0 inbound refs) + cold 105d |
| `scripts/draft_ten_weeks_later.py` | script | b) RESERVE | 103.6d | orphan (0 inbound refs) + cold 104d |
| `OpsCenter/notify_commander.sh` | script | b) RESERVE | 95.5d | orphan (0 inbound refs) + cold 96d |
| `OpsCenter/create_tokyo_draft.py` | script | b) RESERVE | 94.5d | orphan (0 inbound refs) + cold 95d |
| `OpsCenter/atomic_dossier_commit.py` | script | b) RESERVE | 93.0d | orphan (0 inbound refs) + cold 93d |
| `OpsCenter/a7_email_scorer.py` | script | b) RESERVE | 92.6d | orphan (0 inbound refs) + cold 93d |
| `OpsCenter/api_test.py` | script | b) RESERVE | 92.5d | orphan (0 inbound refs) + cold 93d |
| `OpsCenter/keep_to_drive_sync.py` | script | b) RESERVE | 92.5d | orphan (0 inbound refs) + cold 93d |
| `OpsCenter/pinecone_connector.py` | script | b) RESERVE | 92.5d | orphan (0 inbound refs) + cold 93d |
| `OpsCenter/tool_validator.py` | script | b) RESERVE | 92.5d | orphan (0 inbound refs) + cold 93d |
| `OpsCenter/drive_to_evernote_sync.py` | script | b) RESERVE | 87.6d | orphan (0 inbound refs) + cold 88d |

*Thresholds (days since last activity): NG≥14 · Reserve≥44 · Retired-reserve≥134 · Retired-complete≥224. Demotion requires 0 inbound refs AND cold. Protected/referenced/fresh stay ACTIVE.*
