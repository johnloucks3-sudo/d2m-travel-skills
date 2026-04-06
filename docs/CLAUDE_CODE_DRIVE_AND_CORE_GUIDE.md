# CLAUDE CODE — Drive Map & Core Module Reference
## Thunderbird OS | Dreams2Memories Travel, LLC | 2026-04-06

This file supplements CLAUDE.md with Drive folder IDs and the full core module registry
so Claude Code can navigate Drive and the codebase without searching.

---

## GOOGLE DRIVE MAP

### D2M Root: `1KA_b2flnBHTYVRgl3U7erTFIv_aMH9cb`

**Active Business Folders:**

| Folder | ID | Use |
|--------|----|-----|
| Bookings | `1nsqh8_rztIDibEISeAd4MNCbPIfpPlXF` | Active booking files |
| Clients | `124wzwnaV2hKQbVCbyx724ZBSc0HAuf0O` | Per-client folders |
| Cruise_Research | `156BFSr75JsLF9pWJj6t5du8I5Uw915eH` | Cruise line research |
| D2M Trip Dossiers | `1QbbW4hapyfgG6c6Iv94OxtjhySuf2zou` | Canonical dossier mirror |
| Finance | `1b5zfTNsJBlvz-OcMsJ9tUmU5Sm_uEt6s` | Financial records |
| Flights | `1M30QiARzIDrfj4nOqCD73mYmcz8KTzMj` | Flight booking files |
| Insurance | `1YbH3MIf4jJRqs3fuJ85PlC90IhTpYfuD` | Insurance docs |
| Marketing | `11tOP0yql2kaihxEDBvAQUKQ_YHAbbJCY` | Marketing materials |
| OA Onboarding and Info | `1uBXZS-0Y41IZTGOi0ZvBlI6_O7CjAr8P` | Outside Agent onboarding |
| Partnerships | `1ho55LvlzDlA87CmEjyVBHuHizgYFQxBn` | Partner relationships |
| Photos | `1VemZAPBCoaSVkOP3Cpo__OiyWQhkUHHH` | Ship/destination photos |
| Service_Agreements | `1qYFXD1hIdTB1ZG16TcmIhezTvBF4Q8JP` | Service agreements |

**Thunderbird Operational Folders:**

| Folder | ID | Use |
|--------|----|-----|
| Thunderbird_Bookings | `1N3oSIWhsEbcaxK89Axz5rt6ZPehrfkzE` | Processed booking confirmations |
| Thunderbird_Bookings_Vault | `12-PZh6pZ1SFBXC_RkNs7pumHfA_2dqIi` | Raw booking PDF archive |
| Thunderbird_Proposals | `1g2AlDLEjd71cIL-T0HfIh2ytatPBCgVn` | Client-facing proposals/quotes |
| Thunderbird_Templates | `1-zJlm-I8eLQfkYtSbE3Wd2fmKb3-MSk5` | Forms, schemas, itinerary masters |
| Thunderbird_AI_Visuals | `16ZLqRO2864VlS2cTc5SdnreUMsl8M7Pj` | AI-generated images |
| Thunderbird_Visuals | `1OMC35GXKVNSGC37eBixPfFmGTPYgUJQX` | Ship photos, brand imagery |
| Thunderbird_Knowledge_Base | `1MjjbqQVnzMYpHyAtNu-zZej-1mXhHkGk` | SOPs, strategy, reference |
| Thunderbird_Intel | `1joXoapQQjnGsKzxxvpDhZnO6czlCQGqj` | Ship intel, world intel, briefs |
| Thunderbird_Finance | `1k2-DOzj5GEN6hjIlMND19hk4fQhUq-Tm` | Invoices, commission tracking |
| Thunderbird_Commercial_Ops | `1xigsZQiHeh0WZ0JRN0qWzbWxhoBWmt2D` | Agent portals, supplier agreements |
| Thunderbird_Client_Files | `1l3WIjh2aL_fKEuDITmCIgQysfKVDNMUx` | Per-client subfolders |

**Top-Level Drive Folders (outside D2M):**

| Folder | ID | Use |
|--------|----|-----|
| D2M AI Trust Documents | `1TswMbvu9xFkT21XOnhBFpmRTEyef2SWS` | AI governance docs |
| D2M Commander Review | `1dsJTlT3luBt8CiaHN5YCBsXqkDUBsRdg` | Commander review queue |
| D2M Email Templates | `10vsSoLkn3A6uh0t0_sQ-89rSUwzGPgrV` | Email template library |
| D2M Output | `17LVU5NIsIi8lnZ9_iWMGZhfxSVaHF38L` | Generated output files |
| Thunderbird_Itineraries | `1OPejUdV6EnZj6d8pwyJmnUv5-YIwMh0t` | Final itinerary PDFs |
| 01_PROCESSED_BOOKINGS | `1N4EDLSeYq_uv2E9LwkolUbNoCurK1Mcf` | Processed booking archive |
| Generated_Briefs | `1suix7nbozUWjgOysrXspMQA3qxUlt7Jz` | Morning/intel briefs |
| Guest_Forms | `1BXLi6J57_7wHAnZqmH6tGXFOq2ArVewn` | Guest profile forms |
| Travel_Agent_Invoices | `1AMnum_wuNOdmXM7jzwQFtSD_j1GHStjz` | Commission invoices |
| Ship_Deck_Plans | `1L9_-04FLBO6hfIzncbwN_pnjTxV02d0Y` | Ship deck PDFs |

**Client Folders (inside Thunderbird_Client_Files):**

| Client | ID |
|--------|----|
| Loucks, John A III | `174sAduc7mdM9iHtjsg5p_WKjt6oER2Yd` |
| Kuklinski, Kyle | `13UC6D_1oq1_XgWiiHGFFHUXMdqV_4Iye` |
| McLeod, Erik | `1uw4BDWPu3q-HG4ETL6gsMpAxM3vlETUh` |
| Furlow, John Charles | `14wfPo6HurWaOKrlCzFWhD_kf15Pvgl0d` |
| Ely, Alfred | `1fTRMpPemTcuXE-XGCiHpZMrhrs1oyA5N` |
| Nichols, Larry | `1mlNmCJ3Rs-HS5IftzGmaW-Dra6ydQFdE` |
| Westbrook, Ronald L | `1hkJvLp0_O_HGpv8ffWQIODUXdDGfDXPh` |

**MCP Tool -> Folder Routing:**

| Tool Output | Target Folder | Folder Name |
|-------------|---------------|-------------|
| `render_hotel_quote_pdf` | `1g2AlDLEjd71cIL-T0HfIh2ytatPBCgVn` | Thunderbird_Proposals |
| `extract_pdf_booking_details` | `1N3oSIWhsEbcaxK89Axz5rt6ZPehrfkzE` | Thunderbird_Bookings |
| `run_ship_intelligence_sweep` | `1joXoapQQjnGsKzxxvpDhZnO6czlCQGqj` | Thunderbird_Intel |
| `run_world_intelligence_sweep` | `1joXoapQQjnGsKzxxvpDhZnO6czlCQGqj` | Thunderbird_Intel |
| `generate_weekly_report` | `1k2-DOzj5GEN6hjIlMND19hk4fQhUq-Tm` | Thunderbird_Finance |
| `generate_itinerary_images` | `16ZLqRO2864VlS2cTc5SdnreUMsl8M7Pj` | Thunderbird_AI_Visuals |
| Raw booking PDFs | `12-PZh6pZ1SFBXC_RkNs7pumHfA_2dqIi` | Thunderbird_Bookings_Vault |
| Client-specific files | Look up by client name | Thunderbird_Client_Files/* |

**Auth:** OAuth (`drive_token.json`) primary, service account (`credentials.json`) fallback.

---

## CORE MODULE REGISTRY (~/Thunderbird/core/)

### core/ai_infra/ — AI Infrastructure & Inter-Agent
- `thunderbird_a2a.py` (14KB) / `thunderbird_a2a_protocol.py` (39KB) — A2A protocol
- `thunderbird_personas.py` (52KB) — Full persona engine
- `thunderbird_persona_memory.py` (15KB) — Persona memory persistence
- `thunderbird_shared_memory.py` (12KB) — Cross-agent shared memory
- `thunderbird_switchblade.py` (31KB) — Multi-model switchblade router
- `thunderbird_crewai.py` (19KB) — CrewAI integration
- `thunderbird_allm_sync.py` (5KB) — All-LLM synchronization

### core/booking/ — Booking & Client Management
- `thunderbird_tess.py` (48KB) — TESS booking system integration
- `thunderbird_concierge_monitor.py` (61KB) — Concierge workflow monitor
- `thunderbird_commission_recon.py` (30KB) — Commission reconciliation
- `thunderbird_reconciliation.py` (32KB) — Financial reconciliation
- `thunderbird_dossier.py` (26KB) — Dossier CRUD operations
- `thunderbird_dossier_scanner.py` (12KB) — Proactive dossier gap detection
- `thunderbird_booking_monitor.py` (11KB) — Booking status change detection
- `thunderbird_files_api.py` (14KB) — Files API
- `thunderbird_guest_forms.py` (20KB) / `thunderbird_guest_intake.py` (8KB)
- `thunderbird_pdf_ingest.py` (8KB) — PDF booking extraction

### core/client/ — Client Intelligence
- `thunderbird_validation.py` (47KB) — Data validation engine
- `thunderbird_recipient_profiles.py` (26KB) — Recipient profile manager
- `thunderbird_auto_enrich.py` (20KB) — Auto-enrich client profiles
- `thunderbird_context.py` (12KB) — Client context builder
- `thunderbird_data_confidence.py` (12KB) — Data quality scoring
- `thunderbird_quote_render.py` (9KB) — Price quote renderer
- `thunderbird_response_library.py` (12KB) — Response template library
- `thunderbird_followup_reminders.py` (8KB) — Follow-up reminders
- `thunderbird_survey.py` (15KB) — Client survey system

### core/communication/ — Telegram, SMS, WhatsApp
- `thunderbird_telegram_c2.py` (73KB) — Telegram C2 bot (main)
- `thunderbird_telegram_tools_sdk.py` (65KB) — SDK-based tools
- `thunderbird_telegram.py` (44KB) — Client-facing Telegram bot
- `thunderbird_telegram_tools.py` (27KB) — Tool integrations
- `thunderbird_telegram_fmt.py` (11KB) — Message formatting
- `thunderbird_sms.py` (2KB) / `thunderbird_sms_monitor.py` (18KB)
- `thunderbird_whatsapp.py` (1.6KB)

### core/email/ — Gmail & Email Intelligence
- `thunderbird_gmail.py` (82KB) — Gmail API wrapper (largest module)
- `thunderbird_email_intel.py` (64KB) — Email intelligence extraction
- `thunderbird_dani_engine.py` (51KB) — Dani 3-phase engine
- `thunderbird_commander_inbox.py` (42KB) — Commander inbox processing
- `thunderbird_dani_email.py` (40KB) — Dani email composition
- `thunderbird_email_classifier.py` (34KB) — Email classification
- `thunderbird_email_maintenance.py` (27KB) — Email maintenance
- `thunderbird_sentience.py` (26KB) — Email sentience/learning
- `thunderbird_dani_voice.py` (20KB) — Dani voice matching
- `thunderbird_inbox_cleanup_daily.py` (16KB) — Daily inbox cleanup
- `thunderbird_presend_evaluator.py` (10KB) — Pre-send quality check
- `thunderbird_dani_poe_bot.py` (6KB)

### core/intel/ — Intelligence & Research
- `thunderbird_world_intel.py` (39KB) — World intel aggregator
- `thunderbird_intel_digest.py` (34KB) — Intel digest compiler
- `thunderbird_incubator.py` (31KB) — AI Incubator pipeline
- `thunderbird_intel_crew.py` (27KB) — Intel crew orchestration
- `thunderbird_tech_monitor.py` (26KB) — Tech news monitoring
- `thunderbird_academic_scanner.py` (22KB) — Academic travel research
- `thunderbird_ship_intel.py` (18KB) — Ship intelligence scraper
- `thunderbird_price_monitor.py` (19KB) — Cruise price monitoring
- `thunderbird_fb_cruise_digest.py` (20KB) — Facebook cruise digest
- `thunderbird_competitive_surveillance.py` (15KB) — Competitor tracking
- `thunderbird_innovation_scanner.py` (22KB) — Innovation scan
- `thunderbird_grok_osint.py` (9KB) / `thunderbird_x_osint.py` (5KB)
- `thunderbird_nightly_tech_harvest.py` (7KB) — Nightly tech harvest

### core/mcp/ — MCP Servers & Connectors
- `travel_mcp_server.py` (50KB) — Main MCP server, 120+ tools
- `thunderbird_mcp_connector.py` (32KB) — MCP client connector
- `thunderbird_mcp_gateway.py` (6KB) — MCP HTTP gateway
- `goose_mcp_proxy.py` (5KB) / `goose_mcp_server.py` (7KB)

### core/ops/ — Operations & Dashboards
- `thunderbird_grant_compiler.py` (30KB) — Grant application compiler
- `thunderbird_nova.py` (29KB) — Nova operations engine
- `thunderbird_dashboard.py` (29KB) — Operations dashboard
- `thunderbird_usage_monitor.py` (11KB) — API usage monitoring
- `thunderbird_monthly_archive.py` (12KB) — Monthly archive rotation
- `thunderbird_autopilot.py` (7KB) — Autopilot mode
- `thunderbird_v3.py` (13KB) — V3 legacy engine

### core/crewai/ — CrewAI Orchestration
- `agent_loader.py` / `crew_runner.py` / `llm_router.py` / `task_router.py`

---

## INFRASTRUCTURE QUICK REF

- **YOGA:** 192.168.1.198 — primary server, all services
- **Chromebook:** 100.115.92.196 — field kit
- **Domains:** mcp.d2mluxury.quest / api.d2mluxury.quest / portal.d2mluxury.quest
- **Service account:** dreams2memories@d2m-python-pipeline.iam.gserviceaccount.com
- **MCP Failure:** Retry once -> alternate tool -> alert Commander
