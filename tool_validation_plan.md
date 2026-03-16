# D2M Tool Validation Plan — 7-Day Sprint
## Dreams2Memories Travel, LLC
### Created: 2026-03-09

---

## Objective
Systematically test all 97 MCP tools over 7 days to establish confidence before monetization. Each tool gets a pass/fail with notes.

---

## Daily Schedule

### Day 1 — Google Drive & Docs (Est. 12-15 tools)
- [ ] list files in TITAN_BOOKINGS_VAULT
- [ ] search files by name
- [ ] read file contents
- [ ] upload a test file
- [ ] download a file
- [ ] move file between folders
- [ ] create folder
- [ ] create Google Doc
- [ ] update Google Doc
- [ ] list folders
- **Validation:** Round-trip test — upload → list → read → download → verify contents match

### Day 2 — Google Sheets (Est. 8-10 tools)
- [ ] read Booking Master tab
- [ ] write to Booking Master tab
- [ ] read Daily Itinerary tab
- [ ] write to Daily Itinerary tab
- [ ] read specific cell ranges
- [ ] write formatted data (USD, dates)
- [ ] verify fmt_usd() formatting in sheet output
- **Validation:** Write test row → read back → verify all fields match

### Day 3 — Gmail & Calendar (Est. 8-10 tools)
- [ ] search confirmations
- [ ] read threads
- [ ] create drafts
- [ ] list labels
- [ ] search by date range
- [ ] search by sender
- [ ] create calendar event
- [ ] find free time
- [ ] list events
- [ ] update event
- **Validation:** Create draft → find it → verify content; Create event → list → verify

### Day 4 — Browser & Scraping (Est. 10-12 tools)
- [ ] stealth Playwright browser launch
- [ ] navigate to URL
- [ ] take screenshot
- [ ] scrape cruise voyage data
- [ ] scrape pricing pages
- [ ] handle login flows
- [ ] extract structured data from pages
- **Validation:** Screenshot before/after; compare scraped data to manual check

### Day 5 — Hotel & Flight Search (Est. 12-15 tools)
- [ ] Hotelbeds API search
- [ ] rate check
- [ ] hotel details
- [ ] Bedsonline browser
- [ ] Amadeus flight search
- [ ] price verification
- [ ] airport lookup
- [ ] flight comparison
- [ ] quote generation
- **Validation:** Search known hotel/flight → verify price within expected range vs. supplier website

### Day 6 — Ship Intelligence & World Intel (Est. 12-15 tools)
- [ ] compare ships (e.g., Silver Nova vs. Seven Seas Grandeur)
- [ ] run intel sweep
- [ ] generate comparison report (DOCX/PDF)
- [ ] travel advisories check
- [ ] port weather lookup
- [ ] cruise industry news
- [ ] destination intelligence
- **Validation:** Generate comparison report → verify formatting, data accuracy, PDF renders

### Day 7 — Booking Pipeline, Reports & Integration Tests (Est. 15-20 tools)
- [ ] extract PDF booking confirmation
- [ ] parse booking data via Groq
- [ ] sync to Excel/Sheets
- [ ] weekly report generation
- [ ] tech monitor digest
- [ ] end-to-end: PDF → parse → Sheets → itinerary doc
- [ ] cross-tool integration: search Gmail confirmation → extract → write to Sheets → create calendar event
- **Validation:** Full pipeline test with real booking PDF; verify all downstream outputs

---

## Test Record Template

| Tool Name | Category | Input | Expected Output | Actual Output | Pass/Fail | Notes |
|-----------|----------|-------|-----------------|---------------|-----------|-------|
| drive_list | Drive | list VAULT | file list | | | |

---

## Success Criteria
- **Green (Monetize-ready):** 90%+ tools pass, all critical paths work
- **Yellow (Fix first):** 75-89% pass, some critical tools failing
- **Red (Not ready):** Below 75% or any pipeline-breaking failures

---

## Critical Paths (Must Pass)
1. Gmail → PDF extraction → Sheets (booking pipeline)
2. Hotel search → quote → client doc
3. Flight search → comparison → quote
4. Ship comparison → DOCX/PDF report
5. Drive upload/download round-trip
6. Calendar event creation from booking data

---

## Notes
- Test from YOGA (local) AND via mcp.d2mluxury.quest (remote) to validate both paths
- Log any latency issues (SSE vs stdio comparison)
- Document any tools that need API key refresh or auth updates
- Track which tools are most valuable for monetization pitch
