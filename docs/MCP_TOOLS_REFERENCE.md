# Thunderbird OS — MCP Tools Reference

## dreams2memories (Travel Pipeline)

### Browsing & Search
- `browse_url` / `browse_and_click`
- `bedsonline_browse_search` / `bedsonline_browse_interact`

### Hotels
- `search_hotels` / `get_hotel_details`
- `check_hotel_rates`

### Cruises
- `search_live_cruise_voyages`
- `list_available_ships`
- `check_cabin_availability`
- `scrape_specific_cruise_line`

### Bookings & Data
- `extract_booking_from_pdf` / `extract_pdf_booking_details`
- `extract_pdf_itinerary`
- `extract_master_booking_data`
- `read_excel_booking_data`
- `sync_booking_to_excel`
- `consolidate_booking_sources`

### Document Generation
- `generate_itinerary_from_template`
- `generate_itinerary_images`
- `generate_ship_comparison_docx` / `generate_ship_comparison_pdf`
- `generate_weekly_report`
- `insert_images_to_google_docs` / `insert_images_to_pdf`
- `run_itinerary_pipeline`

### Google Drive
- `drive_list_files` / `drive_search`
- `drive_read_document` / `drive_get_file_info`
- `drive_create_folder` / `drive_upload_file`
- `drive_download_file` / `drive_move_file`

### Intelligence
- `run_ship_intelligence_sweep`
- `run_world_intelligence_sweep`
- `run_tech_monitor`
- `get_cruise_industry_news` / `get_tech_news`
- `get_travel_advisories`
- `get_port_weather_forecast`

---

## Canva (Design)

### Design
- `generate-design` / `generate-design-structured`
- `create-design-from-candidate`
- `get-design` / `search-designs`
- `resize-design` / `merge-designs`

### Editing
- `start-editing-transaction`
- `perform-editing-operations`
- `commit-editing-transaction` / `cancel-editing-transaction`

### Content
- `get-design-content` / `get-design-pages`
- `get-presenter-notes` / `get-design-thumbnail`

### Assets & Export
- `get-assets` / `upload-asset-from-url`
- `export-design` / `get-export-formats`

### Folders
- `create-folder` / `search-folders`
- `list-folder-items` / `move-item-to-folder`

### Comments
- `comment-on-design` / `list-comments`
- `list-replies` / `reply-to-comment`

### Other
- `import-design-from-url`
- `list-brand-kits`
- `resolve-shortlink`
- `request-outline-review`

---

## Gmail
- `gmail_get_profile`
- `gmail_search_messages` / `gmail_read_message` / `gmail_read_thread`
- `gmail_list_drafts` / `gmail_create_draft`

---

## Google Calendar
- `gcal_list_calendars` / `gcal_list_events`
- `gcal_get_event` / `gcal_create_event`
- `gcal_update_event` / `gcal_delete_event`
- `gcal_respond_to_event`
- `gcal_find_meeting_times` / `gcal_find_my_free_time`
