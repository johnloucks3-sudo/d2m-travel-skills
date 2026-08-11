# STACK FRESHNESS — Readiness Ladder Report
*Generated 2026-08-11T12:16:22.083621+00:00 · mode `daily` · ADVISORY (read-only)*

SO: `SO_READINESS_LADDER_FRESHNESS_20260621.md` — v1 RECOMMENDS demotions; executes nothing.

## Init-Context Footprint (§2)

**24,684 tokens** of Active-Duty auto-load (target ≤ 15,000) → **RED**

| Auto-load file | est tokens |
|---|---|
| `/home/john/Thunderbird/Personas/hale_cos.md` | 12,228 |
| `/home/john/Thunderbird/hale_brief.md` | 6,712 |
| `/home/john/.claude/projects/-home-john-Thunderbird/memory/MEMORY.md` | 4,820 |
| `/home/john/Thunderbird/hale_state.json` | 473 |
| `/home/john/Thunderbird/OpsCenter/session_context_latest.md` | 450 |

## Inventory & Recommended Tiers

1398 scripts + 599 systemd units = **1997 items**

| Recommended tier | count |
|---|---|
| ACTIVE DUTY | 1664 |
| a) NATIONAL GUARD | 168 |
| b) RESERVE | 152 |
| c) RETIRED-ACTIVE-RESERVE | 13 |
| d) RETIRED COMPLETELY | 0 |

Demotion candidates: **333** · actionable this `daily`: **0**

## Top Demotion Candidates (coldest first)

| Item | Kind | → Tier | Age | Reason |
|---|---|---|---|---|
| `scripts/create_html_drafts.py` | script | c) RETIRED-ACTIVE-RESERVE | 143.6d | orphan (0 inbound refs) + cold 144d |
| `scripts/draft_ten_weeks_later.py` | script | c) RETIRED-ACTIVE-RESERVE | 142.6d | orphan (0 inbound refs) + cold 143d |
| `OpsCenter/notify_commander.sh` | script | c) RETIRED-ACTIVE-RESERVE | 134.5d | orphan (0 inbound refs) + cold 135d |
| `~/.config/systemd/user/cost-openrouter.service` | unit | c) RETIRED-ACTIVE-RESERVE | — | ExecStart target missing: /home/john/Thunderbird/core/cost_dashboard/collectors/openrouter.py — orphan unit |
| `~/.config/systemd/user/cost-poe.service` | unit | c) RETIRED-ACTIVE-RESERVE | — | ExecStart target missing: /home/john/Thunderbird/core/cost_dashboard/collectors/poe_usage.py — orphan unit |
| `~/.config/systemd/user/d2m-dca-den.service` | unit | c) RETIRED-ACTIVE-RESERVE | — | ExecStart target missing: /home/john/d2m-dca-den/run_daily.sh — orphan unit |
| `~/.config/systemd/user/d2m-mcp-grok.service` | unit | c) RETIRED-ACTIVE-RESERVE | — | ExecStart target missing: /home/john/Thunderbird/core/mcp/grok_mcp_server.py — orphan unit |
| `~/.config/systemd/user/d2m-telegram.service` | unit | c) RETIRED-ACTIVE-RESERVE | — | ExecStart target missing: /home/john/Thunderbird/thunderbird_telegram.py — orphan unit |
| `~/.config/systemd/user/kuklinski-jul15-trigger.service` | unit | c) RETIRED-ACTIVE-RESERVE | — | ExecStart target missing: /home/john/Thunderbird/OpsCenter/kuklinski_jul15_creative_chain_trigger.py — orphan unit |
| `~/.config/systemd/user/poe-auth-check.service` | unit | c) RETIRED-ACTIVE-RESERVE | — | ExecStart target missing: /home/john/Thunderbird/scripts/check_poe_health.py — orphan unit |
| `~/.config/systemd/user/thunderbird-c2-sweep.service` | unit | c) RETIRED-ACTIVE-RESERVE | — | ExecStart target missing: /home/john/Thunderbird/scripts/c2_action_sweep.py — orphan unit |
| `~/.config/systemd/user/thunderbird-hooks.service` | unit | c) RETIRED-ACTIVE-RESERVE | — | ExecStart target missing: /home/john/Thunderbird/Thunderbird/thunderbird_hooks_receiver.py — orphan unit |
| `~/.config/systemd/user/thunderbird-watch-officer.service` | unit | c) RETIRED-ACTIVE-RESERVE | — | ExecStart target missing: /home/john/Thunderbird/OpsCenter/watch_officer_groq.sh — orphan unit |
| `OpsCenter/create_tokyo_draft.py` | script | b) RESERVE | 133.5d | orphan (0 inbound refs) + cold 134d |
| `OpsCenter/atomic_dossier_commit.py` | script | b) RESERVE | 132.0d | orphan (0 inbound refs) + cold 132d |
| `OpsCenter/a7_email_scorer.py` | script | b) RESERVE | 131.6d | orphan (0 inbound refs) + cold 132d |
| `OpsCenter/api_test.py` | script | b) RESERVE | 131.5d | orphan (0 inbound refs) + cold 132d |
| `OpsCenter/keep_to_drive_sync.py` | script | b) RESERVE | 131.5d | orphan (0 inbound refs) + cold 132d |
| `OpsCenter/tool_validator.py` | script | b) RESERVE | 131.5d | orphan (0 inbound refs) + cold 132d |
| `OpsCenter/drive_to_evernote_sync.py` | script | b) RESERVE | 126.6d | orphan (0 inbound refs) + cold 127d |
| `OpsCenter/scrub_calendar.py` | script | b) RESERVE | 126.6d | orphan (0 inbound refs) + cold 127d |
| `core/crewai/example_loucks_crew.py` | script | b) RESERVE | 126.6d | orphan (0 inbound refs) + cold 127d |
| `OpsCenter/log_scanner.py` | script | b) RESERVE | 123.4d | orphan (0 inbound refs) + cold 123d |
| `core/scheduling/health_monitor.py` | script | b) RESERVE | 123.4d | orphan (0 inbound refs) + cold 123d |
| `scripts/create_d2m_draft_cc_commander.py` | script | b) RESERVE | 123.4d | orphan (0 inbound refs) + cold 123d |

*Thresholds (days since last activity): NG≥14 · Reserve≥44 · Retired-reserve≥134 · Retired-complete≥224. Demotion requires 0 inbound refs AND cold. Protected/referenced/fresh stay ACTIVE.*
