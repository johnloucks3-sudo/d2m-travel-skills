# STACK FRESHNESS — Readiness Ladder Report
*Generated 2026-06-21T14:05:04.882890+00:00 · mode `weekly` · ADVISORY (read-only)*

SO: `SO_READINESS_LADDER_FRESHNESS_20260621.md` — v1 RECOMMENDS demotions; executes nothing.

## Init-Context Footprint (§2)

**19,079 tokens** of Active-Duty auto-load (target ≤ 15,000) → **RED**

| Auto-load file | est tokens |
|---|---|
| `/home/john/Thunderbird/Personas/hale_cos.md` | 9,667 |
| `/home/john/.claude/projects/-home-john-Thunderbird/memory/MEMORY.md` | 3,929 |
| `/home/john/Thunderbird/hale_state.json` | 3,508 |
| `/home/john/Thunderbird/hale_brief.md` | 1,206 |
| `/home/john/Thunderbird/OpsCenter/session_context_latest.md` | 767 |

## Inventory & Recommended Tiers

1045 scripts + 400 systemd units = **1445 items**

| Recommended tier | count |
|---|---|
| ACTIVE DUTY | 1191 |
| a) NATIONAL GUARD | 159 |
| b) RESERVE | 89 |
| c) RETIRED-ACTIVE-RESERVE | 6 |
| d) RETIRED COMPLETELY | 0 |

Demotion candidates: **254** · actionable this `weekly`: **159**

## Actionable This Cadence (weekly)

| Item | → Tier | Age | Reason |
|---|---|---|---|
| `OpsCenter/claude_haiku_supervisor.py` | a) NATIONAL GUARD | 32.7d | orphan (0 inbound refs) + cold 33d |
| `OpsCenter/claude_token_refresh_daemon.py` | a) NATIONAL GUARD | 32.7d | orphan (0 inbound refs) + cold 33d |
| `OpsCenter/examples_headless_grok_integration.py` | a) NATIONAL GUARD | 20.7d | orphan (0 inbound refs) + cold 21d |
| `OpsCenter/force_send_audit.py` | a) NATIONAL GUARD | 32.7d | orphan (0 inbound refs) + cold 33d |
| `OpsCenter/keyword_router_test.py` | a) NATIONAL GUARD | 20.7d | orphan (0 inbound refs) + cold 21d |
| `OpsCenter/mass_summarizer.py` | a) NATIONAL GUARD | 22.7d | orphan (0 inbound refs) + cold 23d |
| `OpsCenter/send_audit_email.py` | a) NATIONAL GUARD | 32.7d | orphan (0 inbound refs) + cold 33d |
| `OpsCenter/sonnet_prefilter.py` | a) NATIONAL GUARD | 20.8d | orphan (0 inbound refs) + cold 21d |
| `OpsCenter/task_audit_log.py` | a) NATIONAL GUARD | 32.7d | orphan (0 inbound refs) + cold 33d |
| `OpsCenter/test_hale_unified_brain.py` | a) NATIONAL GUARD | 32.7d | orphan (0 inbound refs) + cold 33d |
| `OpsCenter/thunderbird_tts.py` | a) NATIONAL GUARD | 38.4d | orphan (0 inbound refs) + cold 38d |
| `agents/thunderbird_audio_briefing.py` | a) NATIONAL GUARD | 32.7d | orphan (0 inbound refs) + cold 33d |
| `api/thunderbird_cdp_lock.py` | a) NATIONAL GUARD | 26.9d | orphan (0 inbound refs) + cold 27d |
| `api/thunderbird_mag_suite.py` | a) NATIONAL GUARD | 26.5d | orphan (0 inbound refs) + cold 27d |
| `api/thunderbird_odysseus_cdp.py` | a) NATIONAL GUARD | 26.5d | orphan (0 inbound refs) + cold 27d |
| `api/thunderbird_tln_cruisecomplete.py` | a) NATIONAL GUARD | 26.5d | orphan (0 inbound refs) + cold 27d |
| `core/ai_infra/adapters/base.py` | a) NATIONAL GUARD | 32.7d | orphan (0 inbound refs) + cold 33d |
| `core/ai_infra/adapters/claude_max_oauth.py` | a) NATIONAL GUARD | 27.0d | orphan (0 inbound refs) + cold 27d |
| `core/ai_infra/adapters/opencode_nemotron.py` | a) NATIONAL GUARD | 32.7d | orphan (0 inbound refs) + cold 33d |
| `core/ai_infra/adapters/openrouter_breakglass.py` | a) NATIONAL GUARD | 32.7d | orphan (0 inbound refs) + cold 33d |
| `core/ai_infra/adapters/poe_polyglot.py` | a) NATIONAL GUARD | 31.0d | orphan (0 inbound refs) + cold 31d |
| `core/ai_infra/claude_async_pool.py` | a) NATIONAL GUARD | 22.9d | orphan (0 inbound refs) + cold 23d |
| `core/ai_infra/intel_connectors/bedsonline_connector.py` | a) NATIONAL GUARD | 23.4d | orphan (0 inbound refs) + cold 23d |
| `core/ai_infra/intel_connectors/centrav_connector.py` | a) NATIONAL GUARD | 23.4d | orphan (0 inbound refs) + cold 23d |
| `core/ai_infra/intel_connectors/cruisebound_connector.py` | a) NATIONAL GUARD | 24.4d | orphan (0 inbound refs) + cold 24d |
| `core/ai_infra/intel_connectors/icruise_connector.py` | a) NATIONAL GUARD | 24.4d | orphan (0 inbound refs) + cold 24d |
| `core/ai_infra/intel_connectors/regent_connector.py` | a) NATIONAL GUARD | 23.4d | orphan (0 inbound refs) + cold 23d |
| `core/ai_infra/intel_connectors/tess_connector.py` | a) NATIONAL GUARD | 22.9d | orphan (0 inbound refs) + cold 23d |
| `core/ai_infra/intel_connectors/viking_connector.py` | a) NATIONAL GUARD | 15.6d | orphan (0 inbound refs) + cold 16d |
| `core/ai_infra/intel_connectors/vtg_connector.py` | a) NATIONAL GUARD | 24.4d | orphan (0 inbound refs) + cold 24d |
| `core/ai_infra/python_executor_wrapper.py` | a) NATIONAL GUARD | 37.7d | orphan (0 inbound refs) + cold 38d |
| `core/ai_infra/router_chains.py` | a) NATIONAL GUARD | 20.8d | orphan (0 inbound refs) + cold 21d |
| `core/ai_infra/router_classifier.py` | a) NATIONAL GUARD | 32.7d | orphan (0 inbound refs) + cold 33d |
| `core/ai_infra/router_cost_gates.py` | a) NATIONAL GUARD | 32.7d | orphan (0 inbound refs) + cold 33d |
| `core/ai_infra/router_health.py` | a) NATIONAL GUARD | 32.7d | orphan (0 inbound refs) + cold 33d |
| `core/ai_infra/router_setup.py` | a) NATIONAL GUARD | 20.8d | orphan (0 inbound refs) + cold 21d |
| `core/ai_infra/router_telemetry.py` | a) NATIONAL GUARD | 32.7d | orphan (0 inbound refs) + cold 33d |
| `core/ai_infra/unified_router.py` | a) NATIONAL GUARD | 20.8d | orphan (0 inbound refs) + cold 21d |
| `core/communication/thunderbird_email_c2.py` | a) NATIONAL GUARD | 32.7d | orphan (0 inbound refs) + cold 33d |
| `core/communication/thunderbird_telegram_health_check.py` | a) NATIONAL GUARD | 38.7d | orphan (0 inbound refs) + cold 39d |
| `core/cost_dashboard/collectors/_state.py` | a) NATIONAL GUARD | 20.8d | orphan (0 inbound refs) + cold 21d |
| `core/cost_dashboard/collectors/poe_browser_scraper.py` | a) NATIONAL GUARD | 32.7d | orphan (0 inbound refs) + cold 33d |
| `core/cost_dashboard/collectors/poe_cookie_scraper.py` | a) NATIONAL GUARD | 32.7d | orphan (0 inbound refs) + cold 33d |
| `core/cost_dashboard/collectors/poe_realtime.py` | a) NATIONAL GUARD | 32.7d | orphan (0 inbound refs) + cold 33d |
| `core/cost_dashboard/collectors/poe_realtime_tracker.py` | a) NATIONAL GUARD | 32.7d | orphan (0 inbound refs) + cold 33d |
| `core/cost_dashboard/collectors/zen_limits_query.py` | a) NATIONAL GUARD | 20.8d | orphan (0 inbound refs) + cold 21d |
| `core/cost_dashboard/seed_plan.py` | a) NATIONAL GUARD | 32.7d | orphan (0 inbound refs) + cold 33d |
| `core/hale/brief_email_sender.py` | a) NATIONAL GUARD | 32.7d | orphan (0 inbound refs) + cold 33d |
| `core/mcp/scripts/run_headless_claude_scan.py` | a) NATIONAL GUARD | 32.7d | orphan (0 inbound refs) + cold 33d |
| `core/ops/session_checkpoint.py` | a) NATIONAL GUARD | 22.9d | orphan (0 inbound refs) + cold 23d |
| `core/ops/thunderbird_spsa_opencode.py` | a) NATIONAL GUARD | 32.7d | orphan (0 inbound refs) + cold 33d |
| `core/ops/zen_check.py` | a) NATIONAL GUARD | 22.9d | orphan (0 inbound refs) + cold 23d |
| `core/scheduling/monthly_validation.py` | a) NATIONAL GUARD | 20.8d | orphan (0 inbound refs) + cold 21d |
| `core/test_phase3b_integration.py` | a) NATIONAL GUARD | 37.8d | orphan (0 inbound refs) + cold 38d |
| `scripts/ai_metrics_health.py` | a) NATIONAL GUARD | 32.7d | orphan (0 inbound refs) + cold 33d |
| `scripts/audit_mag_mysite.py` | a) NATIONAL GUARD | 22.9d | orphan (0 inbound refs) + cold 23d |
| `scripts/build_opus_prompt.py` | a) NATIONAL GUARD | 32.7d | orphan (0 inbound refs) + cold 33d |
| `scripts/build_spencer_docx.py` | a) NATIONAL GUARD | 15.4d | orphan (0 inbound refs) + cold 15d |
| `scripts/create_ai_metrics_sheet.py` | a) NATIONAL GUARD | 32.7d | orphan (0 inbound refs) + cold 33d |
| `scripts/create_crystal_drafts.py` | a) NATIONAL GUARD | 32.7d | orphan (0 inbound refs) + cold 33d |
| `scripts/create_kuklinski_flights_draft.py` | a) NATIONAL GUARD | 20.8d | orphan (0 inbound refs) + cold 21d |
| `scripts/create_silversea_drafts.py` | a) NATIONAL GUARD | 32.7d | orphan (0 inbound refs) + cold 33d |
| `scripts/discover_viator_klook.py` | a) NATIONAL GUARD | 26.9d | orphan (0 inbound refs) + cold 27d |
| `scripts/dispatch_mission_batch.py` | a) NATIONAL GUARD | 20.8d | orphan (0 inbound refs) + cold 21d |
| `scripts/drive_folder_monitor.py` | a) NATIONAL GUARD | 22.9d | orphan (0 inbound refs) + cold 23d |
| `scripts/ely_darrow_dining_june1_automation.py` | a) NATIONAL GUARD | 20.8d | orphan (0 inbound refs) + cold 21d |
| `scripts/fetch_commander_sent_emails.py` | a) NATIONAL GUARD | 32.7d | orphan (0 inbound refs) + cold 33d |
| `scripts/fix_mission_board.py` | a) NATIONAL GUARD | 32.7d | orphan (0 inbound refs) + cold 33d |
| `scripts/furlow_dining_june1_automation.py` | a) NATIONAL GUARD | 20.8d | orphan (0 inbound refs) + cold 21d |
| `scripts/generate_brand_kit.py` | a) NATIONAL GUARD | 26.8d | orphan (0 inbound refs) + cold 27d |
| `scripts/gmail_read.py` | a) NATIONAL GUARD | 37.8d | orphan (0 inbound refs) + cold 38d |
| `scripts/gmail_read_thread_all.py` | a) NATIONAL GUARD | 37.8d | orphan (0 inbound refs) + cold 38d |
| `scripts/gmail_search.py` | a) NATIONAL GUARD | 37.8d | orphan (0 inbound refs) + cold 38d |
| `scripts/gmail_snippets.py` | a) NATIONAL GUARD | 37.8d | orphan (0 inbound refs) + cold 38d |
| `scripts/hale_email_ooda.py` | a) NATIONAL GUARD | 32.7d | orphan (0 inbound refs) + cold 33d |
| `scripts/m061_regent_nodriver.py` | a) NATIONAL GUARD | 23.7d | orphan (0 inbound refs) + cold 24d |
| `scripts/m061_stealth_probe.py` | a) NATIONAL GUARD | 23.7d | orphan (0 inbound refs) + cold 24d |
| `scripts/m061_viking_login_test.py` | a) NATIONAL GUARD | 23.7d | orphan (0 inbound refs) + cold 24d |
| `scripts/nginx-vhosts-watchdog.sh` | a) NATIONAL GUARD | 25.7d | orphan (0 inbound refs) + cold 26d |
| `scripts/nichols_dining_june1_automation.py` | a) NATIONAL GUARD | 20.8d | orphan (0 inbound refs) + cold 21d |
| `scripts/preprocess_emails_for_opus.py` | a) NATIONAL GUARD | 32.7d | orphan (0 inbound refs) + cold 33d |
| `scripts/read_gmail_message.py` | a) NATIONAL GUARD | 37.8d | orphan (0 inbound refs) + cold 38d |
| `scripts/reauth_full_scopes.py` | a) NATIONAL GUARD | 20.8d | orphan (0 inbound refs) + cold 21d |
| `scripts/render_and_draft_group3.py` | a) NATIONAL GUARD | 32.7d | orphan (0 inbound refs) + cold 33d |
| `scripts/render_dani_showcase_email.py` | a) NATIONAL GUARD | 32.7d | orphan (0 inbound refs) + cold 33d |
| `scripts/search_al_ely.py` | a) NATIONAL GUARD | 37.8d | orphan (0 inbound refs) + cold 38d |
| `scripts/search_seat_policy.py` | a) NATIONAL GUARD | 37.8d | orphan (0 inbound refs) + cold 38d |
| `scripts/send_crystal_emails_final.py` | a) NATIONAL GUARD | 32.7d | orphan (0 inbound refs) + cold 33d |
| `scripts/send_crystal_full.py` | a) NATIONAL GUARD | 32.7d | orphan (0 inbound refs) + cold 33d |
| `scripts/send_glitzy_manual.py` | a) NATIONAL GUARD | 32.7d | orphan (0 inbound refs) + cold 33d |
| `scripts/send_lifecycle_summary.py` | a) NATIONAL GUARD | 32.7d | orphan (0 inbound refs) + cold 33d |
| `scripts/spawn_commission_audit.py` | a) NATIONAL GUARD | 32.7d | orphan (0 inbound refs) + cold 33d |
| `scripts/test_headout_url.py` | a) NATIONAL GUARD | 26.9d | orphan (0 inbound refs) + cold 27d |
| `~/.config/systemd/user/a7-daily-audit.timer` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/apify-mcp.service` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/cost-openrouter.timer` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/d-thunderbird-timer-self-audit.timer` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/d2m-api.service` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/d2m-daily-executor.service` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/d2m-daily-executor.timer` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/d2m-dani-email.timer` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/d2m-dca-den.timer` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/d2m-email-ingest.timer` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/d2m-flowise.service` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/d2m-healthcheck.timer` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/d2m-incubator-evening-review.timer` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/d2m-intel-digest.timer` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/d2m-intel-telegram.timer` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/d2m-llm-proxy.service` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/d2m-morning-briefing.timer` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/d2m-openwebui.service` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/d2m-preflight.timer` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/d2m-star-protocol.timer` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/d2m-zfold-test.timer` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/foursquare-mcp.service` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/goose-gateway.service` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/goose-mcp-http.service` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/goose-telegram.service` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/hale-brief-generate.timer` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/hale-brief-generator.service` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/hale-brief-generator.timer` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/hale-daemon.timer` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/hale-hourly-summary.timer` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/hale-morning-brief.service` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/hale-morning-brief.timer` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/hale-phase2-visuals.timer` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/kuklinski-jul15-trigger.service` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/kuklinski-jul15-trigger.timer` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/lifecycle-calendar-engine.service` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/lifecycle-calendar-engine.timer` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/metronome-daily.service` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/metronome-daily.timer` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/n8n.service` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/poe-auth-check.service` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/poe-auth-check.timer` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/reverie-api.service` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/tess-keepalive.timer` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/thunderbird-ai-metrics.timer` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/thunderbird-boot-recovery.service` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/thunderbird-boot-recovery.timer` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/thunderbird-commander-directive-sweep.service` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/thunderbird-commander-directive-sweep.timer` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/thunderbird-harlan-daily.timer` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/thunderbird-harlan-weekly.timer` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/thunderbird-heartbeat.service` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/thunderbird-heartbeat.timer` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/thunderbird-innovation-scan-weekly.timer` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/thunderbird-opscenter-test.timer` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/thunderbird-qdrant.service` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/thunderbird-rsync.timer` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/thunderbird-sentinel.service` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/thunderbird-sentinel.timer` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/thunderbird-spsa-eod-brief.timer` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/thunderbird-spsa-weekly-brief.timer` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/thunderbird-telegram-c2.service` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/thunderbird-telegram-health.timer` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/thunderbird-timer-self-audit.service` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/thunderbird-timer-self-audit.timer` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |
| `~/.config/systemd/user/yelp-mcp.service` | a) NATIONAL GUARD | — | unit disabled (installed, not active) — load-on-demand candidate |

## Top Demotion Candidates (coldest first)

| Item | Kind | → Tier | Age | Reason |
|---|---|---|---|---|
| `~/.config/systemd/user/cost-openrouter.service` | unit | c) RETIRED-ACTIVE-RESERVE | — | ExecStart target missing: /home/john/Thunderbird/core/cost_dashboard/collectors/openrouter.py — orphan unit |
| `~/.config/systemd/user/d2m-dca-den.service` | unit | c) RETIRED-ACTIVE-RESERVE | — | ExecStart target missing: /home/john/d2m-dca-den/run_daily.sh — orphan unit |
| `~/.config/systemd/user/d2m-intel-telegram.service` | unit | c) RETIRED-ACTIVE-RESERVE | — | ExecStart target missing: /home/john/Thunderbird//home/john/Thunderbird/core/communication/thunderbird_intel_telegram.py — orphan unit |
| `~/.config/systemd/user/d2m-telegram.service` | unit | c) RETIRED-ACTIVE-RESERVE | — | ExecStart target missing: /home/john/Thunderbird/thunderbird_telegram.py — orphan unit |
| `~/.config/systemd/user/thunderbird-hooks.service` | unit | c) RETIRED-ACTIVE-RESERVE | — | ExecStart target missing: /home/john/Thunderbird/Thunderbird/thunderbird_hooks_receiver.py — orphan unit |
| `~/.config/systemd/user/thunderbird-watch-officer.service` | unit | c) RETIRED-ACTIVE-RESERVE | — | ExecStart target missing: /home/john/Thunderbird/OpsCenter/watch_officer_groq.sh — orphan unit |
| `scripts/render_nancy_lyons_email.py` | script | b) RESERVE | 97.0d | orphan (0 inbound refs) + cold 97d |
| `scripts/create_html_drafts.py` | script | b) RESERVE | 92.6d | orphan (0 inbound refs) + cold 93d |
| `scripts/draft_ten_weeks_later.py` | script | b) RESERVE | 91.6d | orphan (0 inbound refs) + cold 92d |
| `scripts/render_dani_validation_emails.py` | script | b) RESERVE | 87.6d | orphan (0 inbound refs) + cold 88d |
| `OpsCenter/notify_commander.sh` | script | b) RESERVE | 83.6d | orphan (0 inbound refs) + cold 84d |
| `OpsCenter/create_tokyo_draft.py` | script | b) RESERVE | 82.6d | orphan (0 inbound refs) + cold 83d |
| `OpsCenter/atomic_dossier_commit.py` | script | b) RESERVE | 81.1d | orphan (0 inbound refs) + cold 81d |
| `OpsCenter/a7_email_scorer.py` | script | b) RESERVE | 80.7d | orphan (0 inbound refs) + cold 81d |
| `OpsCenter/api_test.py` | script | b) RESERVE | 80.6d | orphan (0 inbound refs) + cold 81d |
| `OpsCenter/keep_to_drive_sync.py` | script | b) RESERVE | 80.6d | orphan (0 inbound refs) + cold 81d |
| `OpsCenter/pinecone_connector.py` | script | b) RESERVE | 80.6d | orphan (0 inbound refs) + cold 81d |
| `OpsCenter/tool_validator.py` | script | b) RESERVE | 80.6d | orphan (0 inbound refs) + cold 81d |
| `OpsCenter/drive_to_evernote_sync.py` | script | b) RESERVE | 75.7d | orphan (0 inbound refs) + cold 76d |
| `OpsCenter/gmail_exec_poller.py` | script | b) RESERVE | 75.7d | orphan (0 inbound refs) + cold 76d |
| `OpsCenter/scrub_calendar.py` | script | b) RESERVE | 75.7d | orphan (0 inbound refs) + cold 76d |
| `core/crewai/example_loucks_crew.py` | script | b) RESERVE | 75.7d | orphan (0 inbound refs) + cold 76d |
| `OpsCenter/log_scanner.py` | script | b) RESERVE | 72.5d | orphan (0 inbound refs) + cold 72d |
| `core/scheduling/health_monitor.py` | script | b) RESERVE | 72.5d | orphan (0 inbound refs) + cold 72d |
| `scripts/create_afa_lifecycle_draft.py` | script | b) RESERVE | 72.5d | orphan (0 inbound refs) + cold 72d |

*Thresholds (days since last activity): NG≥14 · Reserve≥44 · Retired-reserve≥134 · Retired-complete≥224. Demotion requires 0 inbound refs AND cold. Protected/referenced/fresh stay ACTIVE.*
