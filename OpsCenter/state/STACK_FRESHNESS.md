# STACK FRESHNESS — Readiness Ladder Report
*Generated 2026-07-31T12:16:21.588644+00:00 · mode `daily` · ADVISORY (read-only)*

SO: `SO_READINESS_LADDER_FRESHNESS_20260621.md` — v1 RECOMMENDS demotions; executes nothing.

## Init-Context Footprint (§2)

**30,032 tokens** of Active-Duty auto-load (target ≤ 15,000) → **RED**

| Auto-load file | est tokens |
|---|---|
| `/home/john/Thunderbird/Personas/hale_cos.md` | 12,228 |
| `/home/john/Thunderbird/hale_state.json` | 6,363 |
| `/home/john/Thunderbird/hale_brief.md` | 6,257 |
| `/home/john/.claude/projects/-home-john-Thunderbird/memory/MEMORY.md` | 4,386 |
| `/home/john/Thunderbird/OpsCenter/session_context_latest.md` | 796 |

## Inventory & Recommended Tiers

1486 scripts + 540 systemd units = **2026 items**

| Recommended tier | count |
|---|---|
| ACTIVE DUTY | 1641 |
| a) NATIONAL GUARD | 205 |
| b) RESERVE | 170 |
| c) RETIRED-ACTIVE-RESERVE | 10 |
| d) RETIRED COMPLETELY | 0 |

Demotion candidates: **385** · actionable this `daily`: **0**

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
| `~/.config/systemd/user/thunderbird-hooks.service` | unit | c) RETIRED-ACTIVE-RESERVE | — | ExecStart target missing: /home/john/Thunderbird/Thunderbird/thunderbird_hooks_receiver.py — orphan unit |
| `~/.config/systemd/user/thunderbird-watch-officer.service` | unit | c) RETIRED-ACTIVE-RESERVE | — | ExecStart target missing: /home/john/Thunderbird/OpsCenter/watch_officer_groq.sh — orphan unit |
| `scripts/create_html_drafts.py` | script | b) RESERVE | 132.6d | orphan (0 inbound refs) + cold 133d |
| `scripts/draft_ten_weeks_later.py` | script | b) RESERVE | 131.6d | orphan (0 inbound refs) + cold 132d |
| `OpsCenter/notify_commander.sh` | script | b) RESERVE | 123.5d | orphan (0 inbound refs) + cold 124d |
| `OpsCenter/create_tokyo_draft.py` | script | b) RESERVE | 122.5d | orphan (0 inbound refs) + cold 123d |
| `OpsCenter/atomic_dossier_commit.py` | script | b) RESERVE | 121.0d | orphan (0 inbound refs) + cold 121d |
| `OpsCenter/a7_email_scorer.py` | script | b) RESERVE | 120.6d | orphan (0 inbound refs) + cold 121d |
| `OpsCenter/api_test.py` | script | b) RESERVE | 120.5d | orphan (0 inbound refs) + cold 121d |
| `OpsCenter/keep_to_drive_sync.py` | script | b) RESERVE | 120.5d | orphan (0 inbound refs) + cold 121d |
| `OpsCenter/tool_validator.py` | script | b) RESERVE | 120.5d | orphan (0 inbound refs) + cold 121d |
| `OpsCenter/drive_to_evernote_sync.py` | script | b) RESERVE | 115.6d | orphan (0 inbound refs) + cold 116d |
| `OpsCenter/scrub_calendar.py` | script | b) RESERVE | 115.6d | orphan (0 inbound refs) + cold 116d |
| `core/crewai/example_loucks_crew.py` | script | b) RESERVE | 115.6d | orphan (0 inbound refs) + cold 116d |
| `OpsCenter/log_scanner.py` | script | b) RESERVE | 112.4d | orphan (0 inbound refs) + cold 112d |
| `core/scheduling/health_monitor.py` | script | b) RESERVE | 112.4d | orphan (0 inbound refs) + cold 112d |
| `scripts/create_d2m_draft_cc_commander.py` | script | b) RESERVE | 112.4d | orphan (0 inbound refs) + cold 112d |

*Thresholds (days since last activity): NG≥14 · Reserve≥44 · Retired-reserve≥134 · Retired-complete≥224. Demotion requires 0 inbound refs AND cold. Protected/referenced/fresh stay ACTIVE.*
