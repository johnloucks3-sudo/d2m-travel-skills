# GOOSE MCP BRIDGE — Full Thunderbird Tool Access
## Quick Reference for Goose Sessions

---

## What This Is (ARCHITECTURE V3)
Goose now possesses the 60 core D2M tools natively via Streamable HTTP (Port 8766). `mcp_bridge.sh` is now exclusively a fallback wrapper to give Goose CLI access to the remaining **heavy TESS and database tools** — the same tools Claude uses natively. One-shot CLI calls, JSON in/JSON out.

## Location
```
/home/john/Thunderbird/mcp_bridge.sh
```

## Usage

### List Tools
```bash
# All 292 tools
/home/john/Thunderbird/mcp_bridge.sh --list

# Filter by keyword
/home/john/Thunderbird/mcp_bridge.sh --list gmail
/home/john/Thunderbird/mcp_bridge.sh --list dossier
/home/john/Thunderbird/mcp_bridge.sh --list intel
```

### Call a Tool
```bash
# No args (tool uses defaults)
/home/john/Thunderbird/mcp_bridge.sh system_health_check

# With args (JSON object)
/home/john/Thunderbird/mcp_bridge.sh system_health_check '{"format":"json"}'

# Gmail search
/home/john/Thunderbird/mcp_bridge.sh gmail_search_messages '{"query":"from:julie","max_results":5}'

# Read a Gmail message
/home/john/Thunderbird/mcp_bridge.sh gmail_read_message '{"message_id":"abc123"}'

# Drive search
/home/john/Thunderbird/mcp_bridge.sh drive_search '{"query":"Westbrook dossier"}'

# Create draft (d2mconcierge@gmail.com)
/home/john/Thunderbird/mcp_bridge.sh gmail_create_draft '{"to":"someone@email.com","subject":"Test","body":"Hello"}'

# World intel sweep
/home/john/Thunderbird/mcp_bridge.sh run_world_intelligence_sweep '{}'

# Morning briefing
/home/john/Thunderbird/mcp_bridge.sh send_morning_briefing '{}'

# Dossier operations
/home/john/Thunderbird/mcp_bridge.sh list_trip_dossiers '{}'
/home/john/Thunderbird/mcp_bridge.sh scan_dossiers '{}'

# Innovation scan
/home/john/Thunderbird/mcp_bridge.sh innovation_daily_scan '{}'

# Ship intel
/home/john/Thunderbird/mcp_bridge.sh run_ship_intelligence_sweep '{}'

# Calendar
/home/john/Thunderbird/mcp_bridge.sh calendar_list_events '{"days_ahead":7}'

# Keep notes
/home/john/Thunderbird/mcp_bridge.sh keep_search_notes '{"query":"booking"}'

# Tasks
/home/john/Thunderbird/mcp_bridge.sh list_tasks '{}'
```

## Output Format
Every call returns JSON:
```json
{
  "status": "success",
  "tool": "tool_name",
  "result": { ... }
}
```

On error:
```json
{
  "status": "error",
  "tool": "tool_name",
  "error": "description"
}
```

## Tool Categories (Key Groups)

| Category | Tools | Examples |
|----------|-------|---------|
| Gmail | 16 | gmail_search_messages, gmail_create_draft, gmail_send_email, gmail_read_message |
| Drive | 9 | drive_search, drive_upload_file, drive_list_files |
| Calendar | 3 | calendar_list_events, calendar_sync_bookings |
| Keep | 5 | keep_search_notes, keep_create_note |
| Tasks | 6 | list_tasks, create_task, complete_task |
| Dossiers | 6 | list_trip_dossiers, scan_dossiers, create_trip_dossier_tool |
| Intel | 12 | run_world_intelligence_sweep, innovation_daily_scan, run_ship_intelligence_sweep |
| Flights | 8 | search_flights, compare_flights, track_flight_fr24 |
| Hotels | 6 | search_hotels, check_hotel_rates, compare_hotels |
| Tours | 6 | search_tours, search_viator_excursions, search_getyourguide_excursions |
| Client Email | 4 | draft_client_email, send_client_email, email_score_draft |
| Bookings | 5 | reconcile_booking_tool, extract_booking_from_pdf |
| TESS | 12 | tess_list_clients, tess_search_bookings, tess_get_commissions |
| Learning | 7 | learning_list_rules, learning_extract, learning_capture_diff |
| Memory | 3 | wing_memory_add, wing_memory_search, wing_memory_stats |
| Voice | 6 | voice_ledger_list, voice_ledger_add |
| Personas | 3 | list_personas, consult_persona, store_persona_memory |
| A2A | 7 | a2a_ask, a2a_broadcast, a2a_create_task |
| Outside Agents | 7 | oa_status, oa_browse, oa_scrape_commissions |
| Briefing | 1 | send_morning_briefing |
| Health | 1 | system_health_check |

## Important Rules
- **Email send gate still applies.** Don't send emails to external addresses without Commander approval.
- **d2mconcierge@gmail.com** is the ops account. All drafts go there.
- **johnloucks3@gmail.com** is receive-only for Commander. Intel/briefs send there freely.
- All tools return JSON. Parse with `jq` if needed.

## Troubleshooting
```bash
# Tool not found? Check exact name:
/home/john/Thunderbird/mcp_bridge.sh --list <keyword>

# Bad JSON args?
# Args must be valid JSON object: '{"key":"value"}'
# No args = empty object: '{}'

# Import error? Activate venv:
source /home/john/Thunderbird/.venv/bin/activate
```
