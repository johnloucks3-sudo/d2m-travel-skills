# STACK FRESHNESS — Readiness Ladder Report
*Generated 2026-07-28T12:16:06.771675+00:00 · mode `daily` · ADVISORY (read-only)*

SO: `SO_READINESS_LADDER_FRESHNESS_20260621.md` — v1 RECOMMENDS demotions; executes nothing.

## Init-Context Footprint (§2)

**30,762 tokens** of Active-Duty auto-load (target ≤ 15,000) → **RED**

| Auto-load file | est tokens |
|---|---|
| `/home/john/Thunderbird/Personas/hale_cos.md` | 12,228 |
| `/home/john/Thunderbird/hale_state.json` | 7,401 |
| `/home/john/Thunderbird/hale_brief.md` | 5,332 |
| `/home/john/.claude/projects/-home-john-Thunderbird/memory/MEMORY.md` | 4,976 |
| `/home/john/Thunderbird/OpsCenter/session_context_latest.md` | 824 |

## Inventory & Recommended Tiers

1446 scripts + 529 systemd units = **1975 items**

| Recommended tier | count |
|---|---|
| ACTIVE DUTY | 1597 |
| a) NATIONAL GUARD | 208 |
| b) RESERVE | 159 |
| c) RETIRED-ACTIVE-RESERVE | 11 |
| d) RETIRED COMPLETELY | 0 |

Demotion candidates: **378** · actionable this `daily`: **0**

## Top Demotion Candidates (coldest first)

| Item | Kind | → Tier | Age | Reason |
|---|---|---|---|---|
| `~/.config/systemd/user/cost-openrouter.service` | unit | c) RETIRED-ACTIVE-RESERVE | — | ExecStart target missing: /home/john/Thunderbird/core/cost_dashboard/collectors/openrouter.py — orphan unit |
| `~/.config/systemd/user/cost-poe.service` | unit | c) RETIRED-ACTIVE-RESERVE | — | ExecStart target missing: /home/john/Thunderbird/core/cost_dashboard/collectors/poe_usage.py — orphan unit |
| `~/.config/systemd/user/d2m-dca-den.service` | unit | c) RETIRED-ACTIVE-RESERVE | — | ExecStart target missing: /home/john/d2m-dca-den/run_daily.sh — orphan unit |
| `~/.config/systemd/user/d2m-intel-telegram.service` | unit | c) RETIRED-ACTIVE-RESERVE | — | ExecStart target missing: /home/john/Thunderbird//home/john/Thunderbird/core/communication/thunderbird_intel_telegram.py — orphan unit |
| `~/.config/systemd/user/d2m-telegram.service` | unit | c) RETIRED-ACTIVE-RESERVE | — | ExecStart target missing: /home/john/Thunderbird/thunderbird_telegram.py — orphan unit |
| `~/.config/systemd/user/kuklinski-jul15-trigger.service` | unit | c) RETIRED-ACTIVE-RESERVE | — | ExecStart target missing: /home/john/Thunderbird/OpsCenter/kuklinski_jul15_creative_chain_trigger.py — orphan unit |
| `~/.config/systemd/user/mcleod-daily-brief.service` | unit | c) RETIRED-ACTIVE-RESERVE | — | ExecStart target missing: /home/john/Thunderbird/scripts/mcleod_daily_itinerary.py — orphan unit |
| `~/.config/systemd/user/poe-auth-check.service` | unit | c) RETIRED-ACTIVE-RESERVE | — | ExecStart target missing: /home/john/Thunderbird/scripts/check_poe_health.py — orphan unit |
| `~/.config/systemd/user/poe-burn-monitor.service` | unit | c) RETIRED-ACTIVE-RESERVE | — | ExecStart target missing: /home/john/Thunderbird/core/cost_dashboard/daemons/poe_burn_monitor.py — orphan unit |
| `~/.config/systemd/user/thunderbird-hooks.service` | unit | c) RETIRED-ACTIVE-RESERVE | — | ExecStart target missing: /home/john/Thunderbird/Thunderbird/thunderbird_hooks_receiver.py — orphan unit |
| `~/.config/systemd/user/thunderbird-watch-officer.service` | unit | c) RETIRED-ACTIVE-RESERVE | — | ExecStart target missing: /home/john/Thunderbird/OpsCenter/watch_officer_groq.sh — orphan unit |
| `scripts/create_html_drafts.py` | script | b) RESERVE | 129.6d | orphan (0 inbound refs) + cold 130d |
| `scripts/draft_ten_weeks_later.py` | script | b) RESERVE | 128.6d | orphan (0 inbound refs) + cold 129d |
| `OpsCenter/notify_commander.sh` | script | b) RESERVE | 120.5d | orphan (0 inbound refs) + cold 121d |
| `OpsCenter/create_tokyo_draft.py` | script | b) RESERVE | 119.5d | orphan (0 inbound refs) + cold 120d |
| `OpsCenter/atomic_dossier_commit.py` | script | b) RESERVE | 118.0d | orphan (0 inbound refs) + cold 118d |
| `OpsCenter/a7_email_scorer.py` | script | b) RESERVE | 117.6d | orphan (0 inbound refs) + cold 118d |
| `OpsCenter/api_test.py` | script | b) RESERVE | 117.5d | orphan (0 inbound refs) + cold 118d |
| `OpsCenter/keep_to_drive_sync.py` | script | b) RESERVE | 117.5d | orphan (0 inbound refs) + cold 118d |
| `OpsCenter/tool_validator.py` | script | b) RESERVE | 117.5d | orphan (0 inbound refs) + cold 118d |
| `OpsCenter/drive_to_evernote_sync.py` | script | b) RESERVE | 112.6d | orphan (0 inbound refs) + cold 113d |
| `OpsCenter/scrub_calendar.py` | script | b) RESERVE | 112.6d | orphan (0 inbound refs) + cold 113d |
| `core/crewai/example_loucks_crew.py` | script | b) RESERVE | 112.6d | orphan (0 inbound refs) + cold 113d |
| `OpsCenter/log_scanner.py` | script | b) RESERVE | 109.4d | orphan (0 inbound refs) + cold 109d |
| `core/scheduling/health_monitor.py` | script | b) RESERVE | 109.4d | orphan (0 inbound refs) + cold 109d |

*Thresholds (days since last activity): NG≥14 · Reserve≥44 · Retired-reserve≥134 · Retired-complete≥224. Demotion requires 0 inbound refs AND cold. Protected/referenced/fresh stay ACTIVE.*
