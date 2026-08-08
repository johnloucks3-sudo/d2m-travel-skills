# STACK FRESHNESS — Readiness Ladder Report
*Generated 2026-08-08T12:16:15.642255+00:00 · mode `daily` · ADVISORY (read-only)*

SO: `SO_READINESS_LADDER_FRESHNESS_20260621.md` — v1 RECOMMENDS demotions; executes nothing.

## Init-Context Footprint (§2)

**31,128 tokens** of Active-Duty auto-load (target ≤ 15,000) → **RED**

| Auto-load file | est tokens |
|---|---|
| `/home/john/Thunderbird/Personas/hale_cos.md` | 12,228 |
| `/home/john/Thunderbird/hale_state.json` | 7,068 |
| `/home/john/Thunderbird/hale_brief.md` | 6,385 |
| `/home/john/.claude/projects/-home-john-Thunderbird/memory/MEMORY.md` | 4,643 |
| `/home/john/Thunderbird/OpsCenter/session_context_latest.md` | 803 |

## Inventory & Recommended Tiers

1376 scripts + 579 systemd units = **1955 items**

| Recommended tier | count |
|---|---|
| ACTIVE DUTY | 1634 |
| a) NATIONAL GUARD | 153 |
| b) RESERVE | 155 |
| c) RETIRED-ACTIVE-RESERVE | 13 |
| d) RETIRED COMPLETELY | 0 |

Demotion candidates: **321** · actionable this `daily`: **0**

## Top Demotion Candidates (coldest first)

| Item | Kind | → Tier | Age | Reason |
|---|---|---|---|---|
| `scripts/create_html_drafts.py` | script | c) RETIRED-ACTIVE-RESERVE | 140.6d | orphan (0 inbound refs) + cold 141d |
| `scripts/draft_ten_weeks_later.py` | script | c) RETIRED-ACTIVE-RESERVE | 139.6d | orphan (0 inbound refs) + cold 140d |
| `~/.config/systemd/user/claude-process-watch.service` | unit | c) RETIRED-ACTIVE-RESERVE | — | ExecStart target missing: /home/john/Thunderbird/scripts/claude_process_watch.py — orphan unit |
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
| `OpsCenter/notify_commander.sh` | script | b) RESERVE | 131.5d | orphan (0 inbound refs) + cold 132d |
| `OpsCenter/create_tokyo_draft.py` | script | b) RESERVE | 130.5d | orphan (0 inbound refs) + cold 131d |
| `OpsCenter/atomic_dossier_commit.py` | script | b) RESERVE | 129.0d | orphan (0 inbound refs) + cold 129d |
| `OpsCenter/a7_email_scorer.py` | script | b) RESERVE | 128.6d | orphan (0 inbound refs) + cold 129d |
| `OpsCenter/api_test.py` | script | b) RESERVE | 128.5d | orphan (0 inbound refs) + cold 129d |
| `OpsCenter/keep_to_drive_sync.py` | script | b) RESERVE | 128.5d | orphan (0 inbound refs) + cold 129d |
| `OpsCenter/tool_validator.py` | script | b) RESERVE | 128.5d | orphan (0 inbound refs) + cold 129d |
| `OpsCenter/drive_to_evernote_sync.py` | script | b) RESERVE | 123.6d | orphan (0 inbound refs) + cold 124d |
| `OpsCenter/scrub_calendar.py` | script | b) RESERVE | 123.6d | orphan (0 inbound refs) + cold 124d |
| `core/crewai/example_loucks_crew.py` | script | b) RESERVE | 123.6d | orphan (0 inbound refs) + cold 124d |
| `OpsCenter/log_scanner.py` | script | b) RESERVE | 120.4d | orphan (0 inbound refs) + cold 120d |
| `core/scheduling/health_monitor.py` | script | b) RESERVE | 120.4d | orphan (0 inbound refs) + cold 120d |

*Thresholds (days since last activity): NG≥14 · Reserve≥44 · Retired-reserve≥134 · Retired-complete≥224. Demotion requires 0 inbound refs AND cold. Protected/referenced/fresh stay ACTIVE.*
