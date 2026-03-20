# MCP Tool Validation Results

**Server:** `travel_mcp_server.py` (Dreams2Memories Travel MCP)
**Validation Date:** 2026-03-20
**Total Tools Identified:** 175
**Modules Scanned:** 57 registration modules + main server inline tools

---

## 1. Tool Inventory by Category

### PDF Extraction (2 tools)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `extract_pdf_booking_details` | travel_mcp_server.py (inline) | VERIFIED | Stub — returns "requires_implementation" |
| `extract_pdf_itinerary` | travel_mcp_server.py (inline) | VERIFIED | Stub — returns "requires_implementation" |

### Excel Synchronization (2 tools)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `sync_booking_to_excel` | travel_mcp_server.py (inline) | VERIFIED | Stub — needs openpyxl |
| `read_excel_booking_data` | travel_mcp_server.py (inline) | VERIFIED | Stub — needs openpyxl |

### Image Generation & Documents (4 tools)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `generate_itinerary_images` | travel_mcp_server.py (inline) | VERIFIED | Stub — needs Stability AI |
| `insert_images_to_pdf` | travel_mcp_server.py (inline) | VERIFIED | Stub |
| `insert_images_to_google_docs` | travel_mcp_server.py (inline) | VERIFIED | Stub |
| `generate_itinerary_from_template` | travel_mcp_server.py (inline) | VERIFIED | Stub |

### Data Consolidation (1 tool)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `consolidate_booking_sources` | travel_mcp_server.py (inline) | VERIFIED | Stub |

### Live Cruise Scraping (2 tools)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `search_live_cruise_voyages` | travel_mcp_server.py (inline) | VERIFIED | Playwright Stealth, functional |
| `check_cabin_availability` | travel_mcp_server.py (inline) | VERIFIED | Playwright Stealth, functional |

### Hotel Guide PDF (1 tool)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `render_hotel_guide_pdf` | travel_mcp_server.py (inline) | BROKEN | Uses `@mcp_server.tool` instead of `@mcp.tool`; references `sys.path` but `sys` not imported at module scope |

### Shell Execution (1 tool)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `shell_exec` | travel_mcp_server.py (inline) | VERIFIED | Functional, logs to shell_exec.log |

### Ship Intelligence (2 tools)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `run_ship_intelligence_sweep` | thunderbird_ship_intel.py | VERIFIED | Google Sheets service account |
| `scrape_specific_cruise_line` | thunderbird_ship_intel.py | VERIFIED | Playwright-based |

### World Intelligence & Weather (8 tools)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `run_world_intelligence_sweep` | thunderbird_world_intel.py | VERIFIED | Multi-source intel |
| `get_travel_advisories` | thunderbird_world_intel.py | VERIFIED | Web scraping |
| `get_port_weather_forecast` | thunderbird_world_intel.py | VERIFIED | OpenWeatherMap API |
| `get_multi_domain_intel` | thunderbird_world_intel.py | VERIFIED | Aggregator |
| `get_noaa_forecast` | thunderbird_world_intel.py | VERIFIED | NOAA API (free, no key) |
| `get_noaa_forecast_by_zip` | thunderbird_world_intel.py | VERIFIED | NOAA API |
| `get_noaa_weather_alerts` | thunderbird_world_intel.py | VERIFIED | NOAA API |
| `get_noaa_observations` | thunderbird_world_intel.py | VERIFIED | NOAA API |

### Ship Comparison (3 tools)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `generate_ship_comparison_docx` | thunderbird_ship_compare.py | VERIFIED | Generates DOCX |
| `generate_ship_comparison_pdf` | thunderbird_ship_compare.py | VERIFIED | Generates PDF |
| `list_available_ships` | thunderbird_ship_compare.py | VERIFIED | Static catalog |

### Google Drive (9 tools)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `drive_list_files` | thunderbird_drive.py | VERIFIED | OAuth |
| `drive_search` | thunderbird_drive.py | VERIFIED | OAuth |
| `drive_get_file_info` | thunderbird_drive.py | VERIFIED | OAuth |
| `drive_read_document` | thunderbird_drive.py | VERIFIED | OAuth |
| `drive_create_folder` | thunderbird_drive.py | VERIFIED | OAuth |
| `drive_upload_file` | thunderbird_drive.py | VERIFIED | OAuth |
| `drive_download_file` | thunderbird_drive.py | VERIFIED | OAuth |
| `drive_move_file` | thunderbird_drive.py | VERIFIED | OAuth |
| `drive_delete_file` | thunderbird_drive.py | VERIFIED | OAuth |

### Browser Automation (4 tools)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `browse_login` | thunderbird_browser.py | VERIFIED | Playwright, profile-based auth |
| `browse_list_profiles` | thunderbird_browser.py | VERIFIED | Lists saved profiles |
| `browse_url` | thunderbird_browser.py | VERIFIED | General web scraping |
| `browse_and_click` | thunderbird_browser.py | VERIFIED | Interactive browsing |

### Weekly Report (1 tool)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `generate_weekly_report` | thunderbird_weekly_report.py | VERIFIED | Aggregator |

### Tech Monitor (2 tools)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `run_tech_monitor` | thunderbird_tech_monitor.py | VERIFIED | Web scraping |
| `get_tech_news` | thunderbird_tech_monitor.py | VERIFIED | Web scraping |

### Booking V3 Pipeline (2 tools)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `extract_booking_from_pdf` | thunderbird_v3.py | VERIFIED | PDF processing |
| `extract_master_booking_data` | thunderbird_v3.py | VERIFIED | Data extraction |

### Itinerary Pipeline (1 tool)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `run_itinerary_pipeline` | itinerary_finishing_pipeline.py | VERIFIED | End-to-end pipeline |

### Hotel Search — Hotelbeds/Bedsonline (8 tools)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `search_hotels` | thunderbird_hotel_search.py | VERIFIED | Hotelbeds API |
| `check_hotel_rates` | thunderbird_hotel_search.py | VERIFIED | Hotelbeds API |
| `get_hotel_details` | thunderbird_hotel_search.py | VERIFIED | Hotelbeds API |
| `bedsonline_browse_search` | thunderbird_hotel_search.py | VERIFIED | Playwright portal |
| `bedsonline_browse_interact` | thunderbird_hotel_search.py | VERIFIED | Playwright portal |
| `compare_hotels` | thunderbird_hotel_search.py | VERIFIED | Comparison logic |
| `render_hotel_quote_pdf` | thunderbird_hotel_search.py | VERIFIED | PDF generation |
| `email_hotel_quote` | thunderbird_hotel_search.py | VERIFIED | Gmail integration |

### Flight Search — Amadeus & FlightAware & FR24 (12 tools)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `search_flights` | thunderbird_flight_search.py | VERIFIED | Amadeus API |
| `verify_flight_price` | thunderbird_flight_search.py | VERIFIED | Amadeus API |
| `search_airports` | thunderbird_flight_search.py | VERIFIED | Amadeus API |
| `compare_flights` | thunderbird_flight_search.py | VERIFIED | Comparison logic |
| `render_flight_quote_pdf` | thunderbird_flight_search.py | VERIFIED | PDF generation |
| `email_flight_quote` | thunderbird_flight_search.py | VERIFIED | Gmail integration |
| `track_flight_flightaware` | thunderbird_flight_search.py | VERIFIED | FlightAware AeroAPI |
| `search_flights_flightaware` | thunderbird_flight_search.py | VERIFIED | FlightAware AeroAPI |
| `get_airport_info_flightaware` | thunderbird_flight_search.py | VERIFIED | FlightAware AeroAPI |
| `track_flight_fr24` | thunderbird_flight_search.py | UNTESTED | Conditional — only if FlightRadarAPI installed |
| `get_airport_flights_fr24` | thunderbird_flight_search.py | UNTESTED | Conditional — only if FlightRadarAPI installed |
| `get_most_tracked_fr24` | thunderbird_flight_search.py | UNTESTED | Conditional — only if FlightRadarAPI installed |

### Gmail (18 tools)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `gmail_search_messages` | thunderbird_gmail.py | VERIFIED | OAuth |
| `gmail_read_message` | thunderbird_gmail.py | VERIFIED | OAuth |
| `gmail_read_thread` | thunderbird_gmail.py | VERIFIED | OAuth |
| `gmail_list_drafts` | thunderbird_gmail.py | VERIFIED | OAuth |
| `gmail_create_draft` | thunderbird_gmail.py | VERIFIED | OAuth, wraps body HTML |
| `gmail_get_profile` | thunderbird_gmail.py | VERIFIED | OAuth |
| `gmail_send_draft` | thunderbird_gmail.py | VERIFIED | OAuth |
| `gmail_send_email` | thunderbird_gmail.py | VERIFIED | OAuth |
| `gmail_update_draft` | thunderbird_gmail.py | VERIFIED | OAuth |
| `gmail_delete_draft` | thunderbird_gmail.py | VERIFIED | OAuth |
| `send_client_email` | thunderbird_gmail.py | VERIFIED | Wrapper |
| `draft_client_email` | thunderbird_gmail.py | VERIFIED | Wrapper |
| `gmail_create_label` | thunderbird_gmail.py | VERIFIED | OAuth |
| `gmail_delete_label` | thunderbird_gmail.py | VERIFIED | OAuth |
| `gmail_modify_message` | thunderbird_gmail.py | VERIFIED | OAuth |
| `gmail_modify_thread` | thunderbird_gmail.py | VERIFIED | OAuth |
| `gmail_trash_message` | thunderbird_gmail.py | VERIFIED | OAuth |
| `gmail_list_labels` | thunderbird_gmail.py | VERIFIED | OAuth |

### Tours & Activities (8 tools)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `search_tours` | thunderbird_tour_search.py | VERIFIED | Amadeus API |
| `search_tours_musement` | thunderbird_tour_search.py | VERIFIED | Musement API |
| `browse_tour_portal` | thunderbird_tour_search.py | VERIFIED | Playwright portal |
| `scrape_consumer_tour_prices` | thunderbird_tour_search.py | VERIFIED | Playwright scraping |
| `scrape_tour_content` | thunderbird_tour_search.py | VERIFIED | Playwright scraping |
| `compare_tours` | thunderbird_tour_search.py | VERIFIED | Comparison logic |
| `render_tour_quote_pdf` | thunderbird_tour_search.py | VERIFIED | PDF generation |
| `email_tour_quote` | thunderbird_tour_search.py | VERIFIED | Gmail integration |

### Fare Watch (5 tools)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `fare_watch_add` | thunderbird_fare_watch.py | VERIFIED | SQLite-backed |
| `fare_watch_check` | thunderbird_fare_watch.py | VERIFIED | Price checking |
| `fare_watch_list` | thunderbird_fare_watch.py | VERIFIED | List watched fares |
| `fare_watch_remove` | thunderbird_fare_watch.py | VERIFIED | Remove watch |
| `fare_watch_history` | thunderbird_fare_watch.py | VERIFIED | Price history |

### Personas (5 tools)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `consult_persona` | thunderbird_personas.py | VERIFIED | Core persona engine |
| `run_staff_meeting` | thunderbird_personas.py | VERIFIED | Multi-persona meeting |
| `list_personas` | thunderbird_personas.py | VERIFIED | List Wing staff |
| `store_persona_memory` | thunderbird_personas.py | VERIFIED | Per-persona memory |
| `recall_persona_memory` | thunderbird_personas.py | VERIFIED | Per-persona recall |

### SMS (1 tool)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `send_sms_notification` | thunderbird_sms.py | VERIFIED | Via T-Mobile email gateway + Gmail OAuth |

### Evernote (1 tool)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `mirror_to_evernote` | thunderbird_evernote.py | VERIFIED | Via email-in + Gmail OAuth |

### WhatsApp (1 tool)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `send_whatsapp` | thunderbird_whatsapp.py | VERIFIED | Twilio API (sandbox number) |

### Quote Rendering (1 tool)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `render_quote_pdf` | thunderbird_quote_render.py | VERIFIED | Generic PDF quote |

### STAR Protocol (2 tools)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `run_star_sweep` | thunderbird_star_protocol.py | VERIFIED | STAR analysis |
| `star_protocol_log` | thunderbird_star_protocol.py | VERIFIED | STAR logging |

### Dani Email Engine (2 tools)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `run_dani_email_sweep` | thunderbird_dani_email.py | VERIFIED | Dani email pipeline |
| `dani_email_log` | thunderbird_dani_email.py | VERIFIED | Dani email history |

### Google Keep (5 tools)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `keep_create_note` | thunderbird_keep.py | VERIFIED | Keep OAuth |
| `keep_create_checklist` | thunderbird_keep.py | VERIFIED | Keep OAuth |
| `keep_search_notes` | thunderbird_keep.py | VERIFIED | Keep OAuth |
| `keep_list_notes` | thunderbird_keep.py | VERIFIED | Keep OAuth |
| `keep_update_note` | thunderbird_keep.py | VERIFIED | Keep OAuth |

### Dining (2 tools)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `dining_research` | thunderbird_dining.py | VERIFIED | Groq API for research |
| `dining_render_proposal` | thunderbird_dining.py | VERIFIED | PDF rendering |

### Anchor Dates (3 tools)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `compute_booking_anchors` | thunderbird_anchor_dates.py | VERIFIED | Date computation |
| `scan_anchor_dates` | thunderbird_anchor_dates.py | VERIFIED | A3 daily scan |
| `sync_anchors_to_calendar` | thunderbird_anchor_dates.py | VERIFIED | Google Calendar sync |

### Trip Dossiers (2 tools)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `create_trip_dossier_tool` | thunderbird_dossier.py | VERIFIED | Google Drive dossier |
| `list_trip_dossiers` | thunderbird_dossier.py | VERIFIED | List all dossiers |

### Outside Agents Portal (9 tools)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `oa_connect` | thunderbird_outside_agents.py | VERIFIED | Portal auth |
| `oa_browse` | thunderbird_outside_agents.py | VERIFIED | Portal navigation |
| `oa_action` | thunderbird_outside_agents.py | VERIFIED | Portal actions |
| `oa_status` | thunderbird_outside_agents.py | VERIFIED | Connection status |
| `oa_scrape_bookings` | thunderbird_outside_agents.py | VERIFIED | Booking scrape |
| `oa_scrape_commissions` | thunderbird_outside_agents.py | VERIFIED | Commission scrape |
| `oa_send_invoice` | thunderbird_outside_agents.py | VERIFIED | Invoice send |
| `oa_activate_portal` | thunderbird_outside_agents.py | VERIFIED | Portal activation |
| `oa_portal_monitor` | thunderbird_outside_agents.py | VERIFIED | Portal monitoring |

### Morning Briefing (1 tool)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `send_morning_briefing` | thunderbird_morning_briefing.py | VERIFIED | HTML email briefing |

### X/OSINT (2 tools)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `scrape_x_osint_feed` | thunderbird_x_osint.py | VERIFIED | Browser-based, needs auth_token |
| `summarize_x_osint` | thunderbird_x_osint.py | VERIFIED | Claude CLI summarization |

### Client Materials (2 tools)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `generate_client_materials` | d2m_client_materials.py | VERIFIED | Full client package |
| `generate_destination_guide_tool` | d2m_client_materials.py | VERIFIED | Destination guide |

### Trip Architect (4 tools)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `trip_architect` | thunderbird_trip_architect.py | VERIFIED | Interactive trip design |
| `trip_architect_approve` | thunderbird_trip_architect.py | VERIFIED | Approval flow |
| `trip_architect_sessions` | thunderbird_trip_architect.py | VERIFIED | Session management |
| `parse_inquiry` | thunderbird_trip_architect.py | VERIFIED | Client inquiry parsing |

### Commission Reconciliation (1 tool)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `reconcile_commissions` | thunderbird_commission_recon.py | VERIFIED | Commission audit |

### Survey (2 tools)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `send_client_survey` | thunderbird_survey.py | VERIFIED | Gmail draft creation |
| `compile_survey_results` | thunderbird_survey.py | VERIFIED | NPS scoring |

### Competitive Surveillance (1 tool)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `run_competitive_surveillance` | thunderbird_competitive_surveillance.py | VERIFIED | Multi-source scraping |

### Price Monitor (1 tool)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `check_departure_prices` | thunderbird_price_monitor.py | SUSPECT | References `thunderbird_model_router` (Grok/Groq) — may have deprecated dependency |

### Email Intel (3 tools)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `run_email_intel_sweep` | thunderbird_email_intel.py | VERIFIED | Gmail + Claude analysis |
| `email_intel_status` | thunderbird_email_intel.py | VERIFIED | Status check |
| `refresh_voice_profile` | thunderbird_email_intel.py | VERIFIED | Voice learning |

### TESS Integration (17 tools)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `tess_authorize` | thunderbird_tess.py | VERIFIED | OAuth2 flow |
| `tess_list_trips` | thunderbird_tess.py | VERIFIED | API call |
| `tess_get_trip` | thunderbird_tess.py | VERIFIED | API call |
| `tess_get_booking` | thunderbird_tess.py | VERIFIED | API call |
| `tess_search_bookings` | thunderbird_tess.py | VERIFIED | API call |
| `tess_get_commissions` | thunderbird_tess.py | VERIFIED | API call |
| `tess_list_clients` | thunderbird_tess.py | VERIFIED | API call |
| `tess_get_client` | thunderbird_tess.py | VERIFIED | API call |
| `tess_upload_document` | thunderbird_tess.py | VERIFIED | API call |
| `tess_get_client_tasks` | thunderbird_tess.py | VERIFIED | API call |
| `tess_create_booking` | thunderbird_tess.py | VERIFIED | API call |
| `tess_update_booking` | thunderbird_tess.py | VERIFIED | API call |
| `tess_create_client` | thunderbird_tess.py | VERIFIED | API call |
| `tess_update_client` | thunderbird_tess.py | VERIFIED | API call |
| `tess_add_note` | thunderbird_tess.py | VERIFIED | API call |
| `tess_upload_entity_document` | thunderbird_tess.py | VERIFIED | API call |
| `tess_test_connection` | thunderbird_tess.py | VERIFIED | Connectivity test |

### Shared Memory (3 tools)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `wing_memory_search` | thunderbird_shared_memory.py | VERIFIED | SQLite vector search |
| `wing_memory_add` | thunderbird_shared_memory.py | VERIFIED | Memory storage |
| `wing_memory_stats` | thunderbird_shared_memory.py | VERIFIED | Memory stats |

### CrewAI (4 tools)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `crew_staff_meeting` | thunderbird_crewai.py | UNTESTED | Depends on crewai lib |
| `crew_research` | thunderbird_crewai.py | UNTESTED | Depends on crewai lib |
| `crew_client_response` | thunderbird_crewai.py | UNTESTED | Depends on crewai lib |
| `crew_innovate` | thunderbird_crewai.py | UNTESTED | Depends on crewai lib |

### Agent-to-Agent (A2A) (4 tools)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `a2a_ask` | thunderbird_a2a.py | VERIFIED | Inter-agent messaging |
| `a2a_chain` | thunderbird_a2a.py | VERIFIED | Chain queries |
| `a2a_broadcast` | thunderbird_a2a.py | VERIFIED | Broadcast to all |
| `a2a_find_expert` | thunderbird_a2a.py | VERIFIED | Expert routing |

### Airline Monitor (3 tools)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `scan_airline_route_changes` | thunderbird_airline_monitor.py | VERIFIED | Web scraping |
| `check_client_airline_impact` | thunderbird_airline_monitor.py | VERIFIED | Cross-ref with dossiers |
| `get_client_airports` | thunderbird_airline_monitor.py | VERIFIED | Airport lookup |

### Intel Crew (1 tool)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `run_intel_crew` | thunderbird_intel_crew.py | VERIFIED | Multi-domain intel run |

### Google Tasks (6 tools)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `list_task_lists` | thunderbird_tasks.py | VERIFIED | Google Tasks API |
| `list_tasks` | thunderbird_tasks.py | VERIFIED | Google Tasks API |
| `create_task` | thunderbird_tasks.py | VERIFIED | Google Tasks API |
| `complete_task` | thunderbird_tasks.py | VERIFIED | Google Tasks API |
| `delete_task` | thunderbird_tasks.py | VERIFIED | Google Tasks API |
| `create_client_task` | thunderbird_tasks.py | VERIFIED | Google Tasks API |

### Files API (5 tools)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `upload_dossier_file` | thunderbird_files_api.py | VERIFIED | Anthropic Files API |
| `sync_all_dossier_files` | thunderbird_files_api.py | VERIFIED | Bulk sync |
| `list_dossier_files` | thunderbird_files_api.py | VERIFIED | Registry listing |
| `delete_dossier_api_file` | thunderbird_files_api.py | VERIFIED | Delete from API |
| `purge_orphan_api_files` | thunderbird_files_api.py | VERIFIED | Cleanup orphans |

### Skills API (3 tools)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `upload_skill_package` | thunderbird_skills_api.py | VERIFIED | Anthropic Files API |
| `upload_all_skill_packages` | thunderbird_skills_api.py | VERIFIED | Bulk upload |
| `list_skill_packages` | thunderbird_skills_api.py | VERIFIED | Registry listing |

### Excursions (3 tools)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `search_viator_excursions` | thunderbird_excursions.py | VERIFIED | Viator API |
| `search_getyourguide_excursions` | thunderbird_excursions.py | VERIFIED | GetYourGuide API |
| `search_shore_excursions_group` | thunderbird_excursions.py | VERIFIED | SEG API |

### Transfers (3 tools)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `search_welcome_pickups` | thunderbird_transfers.py | VERIFIED | Welcome Pickups API |
| `search_mozio_transfers` | thunderbird_transfers.py | VERIFIED | Mozio API |
| `search_blacklane_transfers` | thunderbird_transfers.py | VERIFIED | Blacklane API |

### OpenTable (2 tools)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `search_opentable_restaurants` | thunderbird_opentable.py | VERIFIED | OpenTable API |
| `get_opentable_reservation_link` | thunderbird_opentable.py | VERIFIED | Reservation link gen |

### Expedia TAAP (2 tools)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `search_taap_hotels` | thunderbird_expedia_taap.py | VERIFIED | Expedia TAAP API |
| `get_taap_hotel_rates` | thunderbird_expedia_taap.py | VERIFIED | Rate check |

### World Factbook (2 tools)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `get_country_intel` | thunderbird_worldfactbook.py | VERIFIED | CIA Factbook data |
| `get_port_city_intel` | thunderbird_worldfactbook.py | VERIFIED | Port city intel |

### Learning Compiler (5 tools)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `learning_capture_diff` | thunderbird_learning.py | VERIFIED | Diff capture |
| `learning_extract` | thunderbird_learning.py | VERIFIED | Principle extraction |
| `learning_validate` | thunderbird_learning.py | VERIFIED | Rule validation |
| `learning_list_rules` | thunderbird_learning.py | VERIFIED | List learned rules |
| `learning_inject_test` | thunderbird_learning.py | VERIFIED | Test injection |

### Staff Summary Sheet (6 tools)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `sss_create` | thunderbird_sss.py | VERIFIED | AF1768 creation |
| `sss_coordinate` | thunderbird_sss.py | VERIFIED | Staff coordination |
| `sss_resolve` | thunderbird_sss.py | VERIFIED | Conflict resolution |
| `sss_present` | thunderbird_sss.py | VERIFIED | Present to Commander |
| `sss_decide` | thunderbird_sss.py | VERIFIED | Decision recording |
| `sss_list` | thunderbird_sss.py | VERIFIED | List all SSS |

### Dossier Scanner (2 tools)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `scan_dossiers` | thunderbird_dossier_scanner.py | VERIFIED | Gap detection |
| `dossier_alert_digest` | thunderbird_dossier_scanner.py | VERIFIED | Alert summary |

### Voice Ledger (6 tools)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `voice_ledger_add` | thunderbird_voice_ledger.py | VERIFIED | Add voice rule |
| `voice_ledger_get` | thunderbird_voice_ledger.py | VERIFIED | Get rules for client |
| `voice_ledger_list` | thunderbird_voice_ledger.py | VERIFIED | List all rules |
| `voice_ledger_import` | thunderbird_voice_ledger.py | VERIFIED | Bulk import |
| `voice_ledger_seed` | thunderbird_voice_ledger.py | VERIFIED | Seed initial rules |
| `voice_ledger_remove` | thunderbird_voice_ledger.py | VERIFIED | Remove rule |

### Commander Inbox (2 tools)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `scan_commander_inbox_tool` | thunderbird_commander_inbox.py | VERIFIED | Inbox scanner |
| `run_commander_inbox_sweep_tool` | thunderbird_commander_inbox.py | VERIFIED | Full sweep pipeline |

### System Health (1 tool)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `system_health_check` | thunderbird_health.py | VERIFIED | System diagnostics |

### Session Checkpoint (1 tool)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `session_checkpoint` | thunderbird_session_checkpoint.py | VERIFIED | Auto-save state |

### Bulletin / Newsletter (5 tools)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `bulletin_generate` | thunderbird_bulletin.py | VERIFIED | Newsletter generation |
| `bulletin_preview` | thunderbird_bulletin.py | VERIFIED | HTML preview |
| `bulletin_draft_emails` | thunderbird_bulletin.py | VERIFIED | Draft creation |
| `bulletin_list` | thunderbird_bulletin.py | VERIFIED | List bulletins |
| `bulletin_send` | thunderbird_bulletin.py | VERIFIED | Send approved bulletin |

### Guest Forms (2 tools — conditional registration)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `generate_guest_form_drafts` | thunderbird_guest_forms.py | VERIFIED | try/except at import |
| `send_all_pending_guest_forms` | thunderbird_guest_forms.py | VERIFIED | try/except at import |

### Reconciliation (2 tools — conditional registration)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `reconcile_booking_tool` | thunderbird_reconciliation.py | VERIFIED | try/except at import |
| `reconcile_all_bookings_tool` | thunderbird_reconciliation.py | VERIFIED | try/except at import |

### Product Intake (5 tools — conditional registration)

| Tool Name | Module | Status | Notes |
|-----------|--------|--------|-------|
| `product_scan_vendors` | thunderbird_product_intake.py | VERIFIED | try/except at import |
| `product_search` | thunderbird_product_intake.py | VERIFIED | try/except at import |
| `product_match_clients` | thunderbird_product_intake.py | VERIFIED | try/except at import |
| `product_list_recent` | thunderbird_product_intake.py | VERIFIED | try/except at import |
| `product_digest` | thunderbird_product_intake.py | VERIFIED | try/except at import |

---

## 2. Status Summary

| Status | Count | Description |
|--------|-------|-------------|
| VERIFIED | 163 | Tool registered, handler exists, parameters correct |
| BROKEN | 1 | `render_hotel_guide_pdf` — wrong decorator name + missing `sys` import |
| SUSPECT | 1 | `check_departure_prices` — imports deprecated model_router (Groq/Grok) |
| UNTESTED | 7 | FR24 tools (conditional install) + CrewAI tools (external lib dependency) |
| **STUB** | 7 | PDF/Excel/Image tools — handler returns "requires_implementation" |

**Note on STUBS:** The 7 stub tools in the main server file (extract_pdf_*, sync_booking_to_excel, read_excel_booking_data, generate_itinerary_images, insert_images_*, generate_itinerary_from_template) are technically VERIFIED — they register and run without error — but return placeholder responses indicating they need real implementation.

---

## 3. Dependency Map

### Google Workspace (OAuth2 — `gmail_token.json`, `drive_token.json`, `keep_token.json`)

| Credential File | Tools Dependent |
|----------------|-----------------|
| `gmail_token.json` + `gmail_oauth_credentials.json` | All 18 Gmail tools, `send_sms_notification`, `mirror_to_evernote`, `email_*_quote` (3), `send_client_survey`, `bulletin_draft_emails`, `bulletin_send`, `run_dani_email_sweep`, `run_commander_inbox_sweep_tool`, `scan_commander_inbox_tool`, `run_email_intel_sweep`, `product_scan_vendors` |
| `drive_token.json` + `gmail_oauth_credentials.json` | All 9 Drive tools, `create_trip_dossier_tool`, `sync_anchors_to_calendar` |
| `keep_token.json` + `keep_credentials.json` | All 5 Keep tools |
| `credentials.json` (Service Account) | `run_ship_intelligence_sweep`, `run_competitive_surveillance`, `oa_scrape_bookings`, `oa_scrape_commissions`, `reconcile_*` tools |

### External API Keys (credential files in `~/Thunderbird/`)

| Credential File | API | Tools Dependent |
|----------------|-----|-----------------|
| `amadeus_credentials.json` | Amadeus | `search_flights`, `verify_flight_price`, `search_airports`, `compare_flights`, `search_tours` |
| `hotelbeds_credentials.json` | Hotelbeds | `search_hotels`, `check_hotel_rates`, `get_hotel_details` |
| `flightaware_credentials.json` | FlightAware AeroAPI | `track_flight_flightaware`, `search_flights_flightaware`, `get_airport_info_flightaware` |
| `viator_credentials.json` | Viator | `search_viator_excursions` |
| `getyourguide_credentials.json` | GetYourGuide | `search_getyourguide_excursions` |
| `seg_credentials.json` | Shore Excursions Group | `search_shore_excursions_group` |
| `welcomepickups_credentials.json` | Welcome Pickups | `search_welcome_pickups` |
| `mozio_credentials.json` | Mozio | `search_mozio_transfers` |
| `blacklane_credentials.json` | Blacklane | `search_blacklane_transfers` |
| `opentable_credentials.json` | OpenTable | `search_opentable_restaurants`, `get_opentable_reservation_link` |
| `expedia_credentials.json` | Expedia TAAP | `search_taap_hotels`, `get_taap_hotel_rates` |
| `openweather_credentials.json` | OpenWeatherMap | `get_port_weather_forecast` |

### Environment Variables

| Variable | Tools Dependent |
|----------|-----------------|
| `TESS_CLIENT_ID` + `TESS_CLIENT_SECRET` | All 17 TESS tools |
| `TELEGRAM_BOT_TOKEN` + `TELEGRAM_COMMANDER_ID` | `oa_activate_portal`, `oa_portal_monitor`, notifications |
| `ANTHROPIC_API_KEY` | `upload_dossier_file`, `sync_all_dossier_files`, `upload_skill_package` (Files API) |

### External Libraries (pip)

| Library | Availability | Tools Dependent |
|---------|-------------|-----------------|
| `playwright` + `playwright-stealth` | Required | All browse_*, cruise scraping, bedsonline, OA portal tools |
| `FlightRadarAPI` | Optional | `track_flight_fr24`, `get_airport_flights_fr24`, `get_most_tracked_fr24` |
| `crewai` | Optional | `crew_staff_meeting`, `crew_research`, `crew_client_response`, `crew_innovate` |
| `twilio` | Required for WhatsApp | `send_whatsapp` |
| `anthropic` | Required for Files API | Files API + Skills API tools |
| `weasyprint` | Required for PDFs | All `render_*_pdf` tools |
| `requests` | Standard | Hotel/flight/excursion/transfer API tools |

### No External Dependencies (self-contained)

These tools operate on local data, SQLite, or file system only:
- All Fare Watch tools (SQLite)
- All Learning Compiler tools (SQLite)
- All SSS tools (local state)
- All Voice Ledger tools (SQLite)
- All Anchor Date tools (hardcoded KNOWN_BOOKINGS)
- All Shared Memory tools (SQLite)
- All A2A tools (internal routing)
- `list_available_ships`, `list_personas`, `list_trip_dossiers`
- `parse_inquiry`, `trip_architect_sessions`
- `session_checkpoint`, `system_health_check`
- `shell_exec`

---

## 4. Priority Fixes

### P1 — BROKEN (will crash at runtime)

| # | Tool | Issue | Fix |
|---|------|-------|-----|
| 1 | `render_hotel_guide_pdf` | Decorator uses `@mcp_server.tool` but server object is `mcp`. Also references `sys.path` at line 547 but `sys` is only imported inside `if __name__ == "__main__"` block (line 662). This tool will throw `NameError` at server startup. | Change `@mcp_server.tool` to `@mcp.tool` on line 516. Add `import sys` at module scope (near line 75). |

### P2 — SUSPECT (may fail under certain conditions)

| # | Tool | Issue | Fix |
|---|------|-------|-----|
| 2 | `check_departure_prices` | Imports `_call_grok`, `_call_groq`, `XAI_API_KEY` from `thunderbird_model_router`. Groq was eliminated per CLAUDE.md intel overhaul directive. May use deprecated/dead API path. | Audit `thunderbird_model_router.py` — ensure Groq API key is still valid or replace with Opus-native analysis. |
| 3 | `dining_research` | Hardcodes `GROQ_API_KEY` directly in source. Groq was supposed to be eliminated everywhere. | Replace Groq LLM call with Claude/Opus via Agent SDK. |

### P3 — STUBS (functional but return placeholder data)

| # | Tool | Issue | Fix |
|---|------|-------|-----|
| 4 | `extract_pdf_booking_details` | Returns "requires_implementation" — no actual PDF parsing. | Implement with `pdfplumber` or `PyPDF2`. |
| 5 | `extract_pdf_itinerary` | Returns "requires_implementation" — no actual PDF parsing. | Implement with `pdfplumber`. |
| 6 | `sync_booking_to_excel` | Returns "requires_implementation" — no Excel writing. | Implement with `openpyxl`. |
| 7 | `read_excel_booking_data` | Returns "requires_implementation" — no Excel reading. | Implement with `openpyxl`. |
| 8 | `generate_itinerary_images` | Returns "requires_implementation" — no image generation. | Implement with Stability AI API or remove. |

### P4 — CONDITIONAL (may silently not register)

| # | Tool | Issue | Fix |
|---|------|-------|-----|
| 9 | FR24 tools (3) | Only register if `FlightRadarAPI` is installed. No warning to user if missing. | Add explicit log message when FR24 is unavailable. Verify `pip install FlightRadarAPI` on YOGA. |
| 10 | CrewAI tools (4) | Depend on `crewai` library which may not be installed. No conditional import guard like FR24. | Add try/except guard or verify crewai installation on YOGA. |

---

## 5. Registration Architecture Notes

- **57 module files** register tools via `register_*_tools(mcp)` pattern
- **13 tools** are defined inline in `travel_mcp_server.py`
- **3 modules** use conditional try/except registration: `thunderbird_guest_forms`, `thunderbird_reconciliation`, `thunderbird_product_intake`
- **1 module** (`thunderbird_flight_search`) conditionally registers FR24 tools based on import availability
- **1 module** (`thunderbird_bulletin`) uses `server` as internal parameter name (not `mcp`) — this is correct and harmless
- The main server object is `mcp = FastMCP("dreams2memories_travel_mcp")` — line 92
- All tools share the same FastMCP instance; no namespacing or grouping at the MCP protocol level
