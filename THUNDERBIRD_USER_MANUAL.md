# THUNDERBIRD OS — USER & OPERATIONS MANUAL
## Dreams2Memories Travel, LLC
### Version 1.0 · March 2026
### Written by The Wing — 9 Personas, 120+ Tools, One Mission

---

> *"We don't just execute transactions; we secure dreams."*
>
> *"Some men see things that are and ask why. I see things that can be and say why not."*

---

## HOW TO READ THIS MANUAL

This isn't a reference manual you'll read once and shelve. It's a living operations guide written **by the staff, for the Commander** — and eventually, for every travel advisor who deploys Thunderbird OS.

Each persona authored their own section. They describe what they do, which tools they reach for, how they collaborate with other staff, and what they still need. The tools don't exist in isolation — they exist in workflows. A hotel search isn't useful until A2 has vetted the destination, A9 has run the margin, A6 has written the narrative, and A3 has wired it into a dossier with deadlines.

**For the Commander:** This is your cockpit reference. When you need something done, this tells you who does it, what tools they use, and how to trigger it.

**For future commercial users:** This is proof of architecture. 120+ tools orchestrated by specialized AI personas with military-grade discipline. No other travel technology platform has this.

---

## PART 1: THE TOOL ARSENAL — 120+ TOOLS BY CATEGORY

### Google Workspace (17 tools)

| # | Tool | What It Does | Primary User |
|---|------|-------------|-------------|
| 1 | `drive_list_files` | List files/folders in Google Drive | COS, EXEC |
| 2 | `drive_search` | Search Drive by name or content | A2, COS |
| 3 | `drive_get_file_info` | Get detailed file metadata | COS |
| 4 | `drive_read_document` | Read Google Doc or Sheet content | Any persona |
| 5 | `drive_create_folder` | Create new Drive folder | A3, EXEC |
| 6 | `drive_upload_file` | Upload local file to Drive | COS, A3 |
| 7 | `drive_download_file` | Download from Drive to local | A2, A3 |
| 8 | `drive_delete_file` | Move file to trash | COS (with EXEC approval) |
| 9 | `gmail_search_messages` | Search Gmail by query | A2, A3, COS |
| 10 | `gmail_read_message` | Read full email content | A3, EXEC |
| 11 | `gmail_read_thread` | Read entire email thread | A3, EXEC |
| 12 | `gmail_list_drafts` | List existing drafts | COS |
| 13 | `gmail_create_draft` | Create draft with attachments | EXEC, A3, A6 |
| 14 | `gmail_get_profile` | Gmail connectivity test | System |
| 15 | `keep_create_note` | Create text note in Google Keep | Commander |
| 16 | `keep_create_checklist` | Create checklist in Keep | A3, Commander |
| 17 | `keep_search_notes` | Search Keep notes | Any |

### Flight Search & Booking (9 tools)

| # | Tool | What It Does | Primary User |
|---|------|-------------|-------------|
| 18 | `search_flights` | Search Amadeus API for flight offers | A2, A10 |
| 19 | `verify_flight_price` | Re-verify pricing before quoting | A9 |
| 20 | `search_airports` | Look up IATA codes by city/name | A2, A10 |
| 21 | `compare_flights` | Side-by-side comparison (2-5 offers) | A2, A9 |
| 22 | `render_flight_quote_pdf` | Branded D2M flight quote PDF | EXEC, A6 |
| 23 | `email_flight_quote` | Email flight quote to client | A3 |
| 24 | `search_flight_routes` | Route suggestions for city pairs | A2 |
| 25 | `get_flight_seat_maps` | Retrieve seat map for specific flight | A3, Commander |
| 26 | `check_flight_status` | Real-time status of scheduled flight | A10 |

### Hotel Search & Booking (8 tools)

| # | Tool | What It Does | Primary User |
|---|------|-------------|-------------|
| 27 | `search_hotels` | Search Hotelbeds API for availability | A2 |
| 28 | `check_hotel_rates` | Re-verify hotel rate pricing | A9 |
| 29 | `get_hotel_details` | Static content (photos, facilities) | A2, A6 |
| 30 | `bedsonline_browse_search` | Visual stealth browser hotel search | A2 |
| 31 | `bedsonline_browse_interact` | Login/search/scrape Bedsonline portal | A2 |
| 32 | `compare_hotels` | Side-by-side hotel comparison | A2, A9 |
| 33 | `render_hotel_quote_pdf` | Branded D2M hotel quote PDF | EXEC, A6 |
| 34 | `email_hotel_quote` | Email hotel quote to client | A3 |

### Tour Search & Activities (8 tools)

| # | Tool | What It Does | Primary User |
|---|------|-------------|-------------|
| 35 | `search_tours` | Amadeus tour/activity search by location | A2 |
| 36 | `search_tours_musement` | Musement API tour search | A2 |
| 37 | `browse_tour_portal` | Open tour agent portal for scraping | A2 |
| 38 | `scrape_consumer_tour_prices` | Scrape Expedia/Viator public prices | A9 |
| 39 | `scrape_tour_content` | Scrape Fodor's/Rick Steves descriptions | A6 |
| 40 | `compare_tours` | Side-by-side tour comparison | A2, A9 |
| 41 | `render_tour_quote_pdf` | Branded D2M tour quote PDF | EXEC, A6 |
| 42 | `email_tour_quote` | Email tour quote to client | A3 |

### Cruise Intelligence (4 tools)

| # | Tool | What It Does | Primary User |
|---|------|-------------|-------------|
| 43 | `run_ship_intelligence_sweep` | Full cruise line price/availability scan | A2 |
| 44 | `scrape_specific_cruise_line` | Target single cruise line for data | A2 |
| 45 | `generate_ship_comparison_docx` | Professional ship comparison (DOCX) | A2, EXEC |
| 46 | `generate_ship_comparison_pdf` | Ship comparison report (PDF) | A2, EXEC |

### Browser & Agent Portals (8 tools)

| # | Tool | What It Does | Primary User |
|---|------|-------------|-------------|
| 47 | `browse_login` | Open browser for manual portal login | A2, Commander |
| 48 | `browse_list_profiles` | List saved browser login profiles | System |
| 49 | `browse_url` | Stealth browse URL, extract content | A2, A12 |
| 50 | `browse_and_click` | Automated click/type/scroll actions | A2, A12 |
| 51 | `oa_connect` | Connect to Chrome via CDP for portals | A3 |
| 52 | `oa_browse` | Navigate agent portal via CDP | A3 |
| 53 | `oa_scrape_voyages` | Scrape voyage availability from portal | A2, A3 |
| 54 | `oa_search_bookings` | Search bookings in agent portal | A3 |

### Personas & Staff (3 tools)

| # | Tool | What It Does | Primary User |
|---|------|-------------|-------------|
| 55 | `consult_persona` | Consult specific persona for expertise | Commander, COS |
| 56 | `run_staff_meeting` | Full 10-persona staff meeting | Commander, COS |
| 57 | `list_personas` | List all personas with roles | System |

### Notifications (3 tools)

| # | Tool | What It Does | Primary User |
|---|------|-------------|-------------|
| 58 | `send_sms_notification` | SMS via Twilio gateway | A3, A9, System |
| 59 | `send_whatsapp` | WhatsApp via Twilio (sandbox) | A3 |
| 60 | `gmail_create_draft` | Draft email (also in Workspace) | EXEC, A3 |

### Monitoring & Watches (10 tools)

| # | Tool | What It Does | Primary User |
|---|------|-------------|-------------|
| 61 | `fare_watch_add` | Add fare to price watch list | A2, A9 |
| 62 | `fare_watch_check` | Record price check, trigger alerts | A9 |
| 63 | `fare_watch_list` | List all fare watches with trends | A9, Commander |
| 64 | `fare_watch_remove` | Deactivate fare watch | A9 |
| 65 | `fare_watch_history` | Price history with min/max/avg | A9, A2 |
| 66 | `compute_booking_anchors` | Calculate milestone dates for booking | A3 |
| 67 | `scan_anchor_dates` | A3 daily scan for due/overdue dates | A3 |
| 68 | `sync_anchors_to_calendar` | Push anchor dates to Google Calendar | A3 |
| 69 | `run_star_sweep` | Scan Gmail for star-coded commands | COS |
| 70 | `star_protocol_log` | View recent star sweep results | COS |

### Intelligence & Reports (11 tools)

| # | Tool | What It Does | Primary User |
|---|------|-------------|-------------|
| 71 | `run_world_intelligence_sweep` | Full travel advisory + weather + news | A2 |
| 72 | `get_travel_advisories` | Travel advisories by alert level | A2, A10 |
| 73 | `get_port_weather_forecast` | 5-day forecast for cruise port | A2, A10 |
| 74 | `get_cruise_industry_news` | Cruise industry news feed | A2 |
| 75 | `get_noaa_forecast` | NOAA detailed forecast (US only) | A10 |
| 76 | `run_tech_monitor` | Daily tech news across RSS feeds | A12 |
| 77 | `get_tech_news` | Tech news by category | A12 |
| 78 | `generate_weekly_report` | Weekly client intelligence PDF/HTML | COS, A2 |
| 79 | `send_morning_briefing` | Daily intelligence email | COS, A2 |
| 80 | `scrape_x_osint_feed` | Scrape X/Twitter OSINT accounts | A2 |
| 81 | `summarize_x_osint` | AI-summarize OSINT feeds | A2 |

### Dining & Experiences (2 tools)

| # | Tool | What It Does | Primary User |
|---|------|-------------|-------------|
| 82 | `dining_research` | Research top restaurants for destination | A2, A6 |
| 83 | `dining_render_proposal` | Branded D2M Dining Guide PDF | EXEC, A6 |

### PDF, Documents & Quotes (8 tools)

| # | Tool | What It Does | Primary User |
|---|------|-------------|-------------|
| 84 | `render_quote_pdf` | Unified D2M quote (flight/hotel/tour/cruise) | EXEC |
| 85 | `extract_pdf_booking_details` | OCR + AI parse booking confirmation | System |
| 86 | `extract_pdf_itinerary` | OCR + AI parse port-by-port itinerary | System |
| 87 | `extract_booking_from_pdf` | V3 extraction (OCR + Groq) | System |
| 88 | `extract_master_booking_data` | Regex + Groq parse booking text | System |
| 89 | `run_itinerary_pipeline` | Full itinerary render pipeline | EXEC, A6 |
| 90 | `generate_itinerary_from_template` | Personalized itinerary from booking data | EXEC |
| 91 | `consolidate_booking_sources` | Merge data from PDFs, Excel, Gmail | A3, System |

### Data Sync & Storage (6 tools)

| # | Tool | What It Does | Primary User |
|---|------|-------------|-------------|
| 92 | `sync_booking_to_excel` | Sync booking data to Excel workbook | System |
| 93 | `read_excel_booking_data` | Read structured data from Excel | A3, A9 |
| 94 | `create_trip_dossier_tool` | Create/update trip dossier on Drive | A3, COS |
| 95 | `list_trip_dossiers` | List all dossiers with status | A3, COS |
| 96 | `mirror_to_evernote` | Mirror booking data to Evernote | System |
| 97 | `search_live_cruise_voyages` | Scrape live cruise voyage data | A2 |

### Image & Media (3 tools)

| # | Tool | What It Does | Primary User |
|---|------|-------------|-------------|
| 98 | `generate_itinerary_images` | AI-generate port images (Stable Diffusion) | A6 |
| 99 | `insert_images_to_pdf` | Insert images into PDF template | EXEC |
| 100 | `insert_images_to_google_docs` | Insert images into Google Docs | EXEC |

### System (1 tool)

| # | Tool | What It Does | Primary User |
|---|------|-------------|-------------|
| 101 | `shell_exec` | Execute bash command with logging | A12, System |

**Total: 101 registered MCP tools + 18 scheduled automation jobs + Star Protocol + Heartbeat System**

---

## PART 2: THE WING SPEAKS — EACH PERSONA ON THEIR TOOLS, WORKFLOWS & NEEDS

---

### COS — Col Victoria "Iron Vic" Hale
#### *Chief of Staff — Orchestration, Priorities, Staff Synchronization*

**What I Do**

I'm the single throat to choke. Every task that enters this organization either flows through me or I know about it within 30 minutes. I don't do the work — I make sure the right person does the right work at the right time, and that nobody's stepping on each other.

My job is synthesis. When Wraith brings intel, Harlan runs the numbers, Moreau checks the ops timeline, and Luna writes the story — I'm the one who reads all four and tells the Commander: "Here's the picture. Here's what I recommend. Here are the two things we disagree on."

**My Tools**

| Tool | How I Use It | Frequency |
|------|-------------|-----------|
| `run_staff_meeting` | Full 10-persona consultation on complex decisions | Weekly or on-demand |
| `consult_persona` | Quick check with one specialist | Multiple daily |
| `run_star_sweep` | Scan Gmail for star-coded commands, route to right persona | Every 15 min (automated) |
| `gmail_search_messages` | Find client threads, supplier correspondence | As needed |
| `gmail_create_draft` | Draft Commander Review items, staff memos | Daily |
| `send_morning_briefing` | Deliver daily intelligence package | Daily 0630 |
| `generate_weekly_report` | Monday morning comprehensive report | Weekly |
| `drive_search` | Find documents, proposals, dossiers | As needed |
| `drive_upload_file` | Archive reports to Drive | After each report |

**My Daily Rhythm**

- **0600-2000:** COS-EXEC heartbeat fires every 30 minutes. I scan payment deadlines, booking status, dossier action items, and Gmail for anything urgent. If something needs the Commander's attention, I create a draft or SMS.
- **Star Protocol:** When the Commander stars an email red, I extract the intent and route it. Green means execute. Blue goes to EXEC for a draft reply. Self-emails with `[COS]` or `[STAFF]` come straight to me.
- **Staff Meetings:** When the Commander sends `[STAFF]`, I run the meeting — all 10 personas weigh in, I synthesize, I deliver the recommendation with dissent flagged.

**What I Still Need**

1. **Priority queue visualization** — I track priorities in my head. I need a dashboard view of all open action items sorted by urgency, with owner and deadline. The Action_Tracker sheet exists but it's not my primary interface.
2. **Conflict detection** — When two clients have overlapping deadlines or when a persona's recommendation contradicts another's, I want automatic flagging. Right now I catch it during synthesis, but I could miss something at 0600.
3. **Decision log** — Every Commander decision should be logged with context, alternatives considered, and who recommended what. We have Commander_Log but it's not structured for decision-tracking.
4. **Staff performance metrics** — Which personas are being consulted most? Which recommendations get accepted vs. overridden? I need this data to improve staff quality.

---

### EXEC — Naia Solberg-Vega
#### *Voice + Visual + Commander's Intent*

**What I Do**

Everything the client sees passes through me. Every email, every proposal, every PDF, every brand touchpoint. I don't write logistics — that's Dani's precision. I don't write strategy — that's Viper's domain. I write *how it feels* to be a Dreams2Memories client.

I'm also the Keeper of the Master Plan. When someone says "delete," I'm the one who asks: "What exactly?" When priorities shift, I update the plan. When the staff disagrees, I'm one of two people who can look the Commander in the eye and say "I think you're wrong."

I work hand-in-glove with Luna. She writes the poetry; I make sure it's on-brand. She sees the dream; I design the frame.

**My Tools**

| Tool | How I Use It | Frequency |
|------|-------------|-----------|
| `gmail_create_draft` | Client emails in the Commander's voice | Multiple daily |
| `render_quote_pdf` | Unified branded quote PDFs | Per quote |
| `render_hotel_quote_pdf` | Hotel-specific branded proposals | Per hotel search |
| `render_flight_quote_pdf` | Flight quote presentations | Per flight search |
| `render_tour_quote_pdf` | Tour/activity proposals | Per tour search |
| `run_itinerary_pipeline` | Full itinerary render (fetch, narrate, image, PDF) | Per trip |
| `generate_itinerary_from_template` | Personalized itinerary from booking data | Per trip |
| `insert_images_to_pdf` | Photo integration in proposals | Per proposal |
| `dining_render_proposal` | Branded Dining Guide PDF | Per destination |
| `generate_ship_comparison_pdf` | Ship comparison reports | Per comparison |
| `drive_upload_file` | Archive proposals on Drive | After each render |

**My Daily Rhythm**

- **COS-EXEC heartbeat (every 30 min):** I scan alongside Hale. She looks at ops; I look at communication gaps. Has it been too long since we touched a client? Is there an upcoming trip that needs a pre-voyage excitement email?
- **Quote Panel:** When a quote request comes in, I'm on the panel with Viper (strategy) and Luna (story). Viper prices it, Luna writes the narrative, I assemble and brand it.
- **Voice Profile:** I have access to `thunderbird_my_voice.py` — a profile built from the Commander's actual sent emails and writing style. When I draft, I sound like Yoda, not like a chatbot.

**What I Still Need**

1. **Template library with versioning** — We have Jinja2 templates for hotel guides, quotes, and itineraries. I need a catalog of every template with a preview, and version history so I can roll back design changes.
2. **Client communication timeline** — A visual timeline per client showing every touchpoint: email, call, proposal sent, booking confirmed. Right now I have to dig through dossiers.
3. **Brand asset library on Drive** — Logos, color swatches, stock photos per destination, all organized and tagged. Currently scattered.
4. **Canva integration for custom presentations** — The Canva MCP connector exists in Claude.ai. If I could access it from Thunderbird, I could create custom visual proposals without leaving the system.

---

### A2 — Lt Col Marcus "Wraith" Dembe
#### *Research & Market Intelligence*

**What I Do**

I'm the intelligence officer. Before any client sees a destination, hotel, flight, tour, or cruise — I've already vetted it. I run sweeps. I compare prices. I check advisories. I read the industry news at 0630 before the Commander reads a single email.

I don't guess. I assess. "High confidence: the Silver Muse Med itinerary has a 45-minute connection in Civitavecchia that Tommy should flag." "Moderate confidence: Regent will announce Wave Season pricing by mid-January." "Insufficient data: Ponant's Antarctic capacity for 2027 — need scrape."

**My Tools**

| Tool | How I Use It | Frequency |
|------|-------------|-----------|
| `search_hotels` | Hotelbeds API availability + pricing | Per client request |
| `get_hotel_details` | Property photos, facilities, descriptions | Per hotel |
| `bedsonline_browse_search` | Visual browser scraping when API fails | Fallback |
| `bedsonline_browse_interact` | Portal login, deep scraping | Fallback |
| `search_flights` | Amadeus flight search | Per route request |
| `compare_flights` | Side-by-side flight analysis | Per comparison |
| `search_tours` | Amadeus tour/activity search | Per destination |
| `search_tours_musement` | Musement API alternative | Per destination |
| `browse_tour_portal` | Agent tour portal scraping | When API lacks coverage |
| `scrape_consumer_tour_prices` | Viator/Expedia price check | For margin analysis |
| `scrape_tour_content` | Fodor's/Rick Steves editorial content | For narrative context |
| `run_ship_intelligence_sweep` | Full cruise line scan (8 lines) | Daily 0630 + 1700 |
| `scrape_specific_cruise_line` | Target one line for deep data | On demand |
| `run_world_intelligence_sweep` | Travel advisories, weather, news | Daily 0630 |
| `get_travel_advisories` | Filter advisories by alert level | Per destination |
| `get_port_weather_forecast` | 5-day port forecast | Pre-embarkation |
| `get_cruise_industry_news` | Industry news feed | Daily |
| `scrape_x_osint_feed` | X/Twitter OSINT for real-time intel | On demand |
| `summarize_x_osint` | AI-summarize OSINT feeds | On demand |
| `dining_research` | Restaurant curation per destination | Per trip |
| `browse_url` | General stealth web research | As needed |
| `fare_watch_add` | Set up price monitoring | Per fare of interest |
| `fare_watch_check` | Record price observation | Per sweep |
| `fare_watch_history` | Trend analysis on watched fares | Weekly |
| `search_live_cruise_voyages` | Scrape live voyage availability | Per request |

**I am the heaviest tool user on the staff.** 25+ tools in my regular rotation. That's not complexity — that's coverage. A destination research request from the Commander touches hotel APIs, flight APIs, tour APIs, weather services, travel advisories, cruise line scrapers, and OSINT feeds. I synthesize all of it into a single intelligence product.

**My Daily Rhythm**

- **0630 heartbeat:** I scan overnight intel — travel advisories, cruise pricing shifts, industry news. If something affects an active client, I flag it immediately.
- **Intel Panel:** When an alert fires (price drop, advisory change), I'm on panel with Viper (A5) to assess strategic impact.
- **Research Requests:** Commander sends `[A2] Research Michelin restaurants in Stockholm` — I hit `dining_research`, cross-reference with `browse_url` for editorial content, and deliver a curated list.

**What I Still Need**

1. **Cruise line portal automation** — I can scrape public sites, but Regent's agent portal, Silversea's Direct Access, and Viking's portal all require authenticated sessions. The `oa_*` tools work for some but need expansion for each cruise line's specific portal structure.
2. **Competitive pricing database** — I check prices manually per sweep. I need a persistent database that tracks cruise fares over time so I can show clients "this fare is 12% below the 90-day average."
3. **Destination knowledge graph** — I research the same destinations repeatedly. Stockholm for the Scandinavia group. Rome/Florence for McLeod. I need a cached knowledge base per destination that I build once and update incrementally.
4. **Google Flights API** — Amadeus is the backbone, but Google Flights data would give me a consumer-price comparison. No API exists, but a scraper would fill the gap.
5. **Image search and curation** — When I research a destination, I should also be collecting the best images for Luna and EXEC to use in proposals. Currently that's manual.

---

### A3 — Maj Danielle "Dani" Moreau
#### *Booking Operations & Client Journey — The Deep Dive*

**What I Do**

I own the client journey from first inquiry to welcome-home email. Every booking has a lifecycle: inquiry → quote → deposit → confirmation → documents → final payment → pre-trip prep → travel → follow-up → referral. I track every step for every client across every booking.

Right now I'm managing **16 active bookings** across 6 client groups plus personal travel. Each booking has 10-15 anchor dates (milestones), each with dependencies. Kuklinski's Viking Panama Canal has 3 suites with 6 guests needing Guest Information Forms by March 15 and $21,244 in final payments by March 31. The Regent Scandinavia group has 3 couples with final payments April 1, dining selections due April 15, and specialty dining opening in late May. McLeod has 4 voyages spanning June 2026 through December 2027. I hold all of this in my operational picture.

**Here's what my day actually looks like:**

#### 0700 — My Heartbeat Fires

The scheduler triggers my daily heartbeat. I scan:

1. **Booking Master sheet** — every row in the Google Sheet, checking for:
   - Final Payment Dates within 7/14/21/30 days
   - Missing data (blank emails, wrong client names, duplicate rows)
   - Status changes since yesterday

2. **All 8 trip dossiers** — each one has:
   - `## OPEN ACTION ITEMS` — unchecked boxes `- [ ]` that need attention
   - `## EMAIL LOG` — last contact date per client (for inactivity detection)
   - `## DOCUMENTS CHECKLIST` — passports, GIFs, insurance, final payment receipts
   - `## ANCHOR DATE TIMELINE` — milestones with PAST/upcoming status

3. **Google Calendar** — events synced from Booking Master via `thunderbird_calendar_sync.py`

If I find something urgent (FPD in 3 days, guest forms overdue, client dark for 14 days), I send an SMS to the Commander and create a Gmail draft with the details.

#### Tools I Reach For Every Day

| Tool | How I Use It | When |
|------|-------------|------|
| `scan_anchor_dates` | My signature tool — scan all bookings for due/overdue milestones | Daily 0700 heartbeat |
| `compute_booking_anchors` | Calculate FPD, E-120, E-90, E-60, E-30 dates for a booking | When new booking created |
| `sync_anchors_to_calendar` | Push milestone dates to Google Calendar | After anchor computation |
| `create_trip_dossier_tool` | Create or regenerate a trip dossier | When booking confirmed |
| `list_trip_dossiers` | Status check on all active dossiers | Daily scan |
| `gmail_search_messages` | Find client threads, supplier confirmations | Multiple daily |
| `gmail_read_message` | Read confirmation details, payment receipts | As they arrive |
| `gmail_read_thread` | Full conversation context before drafting | Before client contact |
| `gmail_create_draft` | Draft client emails (EXEC polishes voice) | Per client touchpoint |
| `email_hotel_quote` | Send hotel proposals to clients | Per booking |
| `email_flight_quote` | Send flight proposals to clients | Per booking |
| `email_tour_quote` | Send activity proposals to clients | Per booking |
| `send_sms_notification` | Urgent alerts to Commander's phone | When deadlines critical |
| `oa_connect` | Connect to cruise line agent portals | For booking verification |
| `oa_browse` | Navigate portal pages | For booking details |
| `oa_search_bookings` | Search bookings by confirmation number | For status checks |
| `oa_scrape_voyages` | Check cabin availability/upgrades | Post-FPD, upgrade watch |
| `consolidate_booking_sources` | Merge data from PDFs, Excel, Gmail | When booking data fragmented |
| `read_excel_booking_data` | Read structured booking data | For reconciliation |
| `sync_booking_to_excel` | Update Excel booking records | After changes |
| `keep_create_checklist` | Quick task list for Commander | For multi-step client actions |

**That's 21 tools in my regular rotation.** More than anyone except Wraith.

#### My Workflows — How Tools Chain Together

**Workflow 1: New Booking Confirmed**
```
1. extract_pdf_booking_details    → Parse supplier confirmation PDF
2. sync_booking_to_excel          → Write to Booking Master sheet
3. compute_booking_anchors        → Calculate all milestone dates
4. sync_anchors_to_calendar       → Push to Google Calendar
5. create_trip_dossier_tool       → Generate trip dossier
6. drive_upload_file              → Mirror dossier to Google Drive
7. gmail_create_draft             → Draft confirmation email to client
   (EXEC reviews voice, sends)
8. send_sms_notification          → Alert Commander: "New booking confirmed"
```
**Tools used: 8. Personas involved: A3 (lead), A9 (financial check), CH (ethics flag), EXEC (voice polish).**

**Workflow 2: Final Payment Approaching (T-30 days)**
```
1. scan_anchor_dates              → FPD flagged as approaching
2. gmail_search_messages          → Find last client contact
3. gmail_read_thread              → Read full conversation context
4. oa_connect + oa_search_bookings → Verify balance with supplier
5. check_hotel_rates (if hotel)   → Confirm pricing still valid
6. gmail_create_draft             → Draft payment reminder email
7. send_sms_notification          → Alert Commander if client unresponsive
```
**Tools used: 7. Personas involved: A3 (lead), A9 (amount verification).**

**Workflow 3: Client Goes Dark (14+ days no contact)**
```
1. Follow-up scanner detects inactivity
2. gmail_search_messages          → Confirm no recent threads
3. consult_persona (EXEC)         → Draft warm follow-up
4. gmail_create_draft             → Create draft for Commander review
5. send_sms_notification          → "URGENT: McLeod 14 days no contact"
```
**Tools used: 5. Personas involved: A3 (detect), EXEC (voice), COS (if escalated).**

**Workflow 4: Pre-Trip Package (T-30 days before embarkation)**
```
1. list_trip_dossiers             → Verify dossier is current
2. dining_research (via A2)       → Restaurant recommendations
3. get_port_weather_forecast      → Weather for each port
4. run_itinerary_pipeline         → Full branded itinerary
5. dining_render_proposal         → Dining guide PDF
6. drive_upload_file              → All docs to client Drive folder
7. gmail_create_draft             → Package delivery email
```
**Tools used: 7. Personas involved: A3 (orchestrate), A2 (research), A6 (narrative), EXEC (brand).**

#### What I Still Need — The Gaps

**1. Client Portal / Self-Service Interface**
Clients currently get everything via email. I need a portal where they can:
- See their booking status and upcoming milestones
- Upload documents (passports, insurance cards)
- View and download their itinerary, dining guide, proposals
- Sign off on dining/excursion selections
- See payment history and upcoming amounts

This would cut my email volume by 40% and give clients 24/7 access to their trip information. **This is the single biggest gap in my operation.**

**2. Supplier API Integration**
I use `oa_*` tools to scrape agent portals, but I need direct API access to:
- **Regent Seven Seas** — booking status, payment balance, cabin assignment
- **Silversea** — booking details, shore excursion availability
- **Viking** — guest info form status, payment confirmation
- **Princess** — booking lookup, deck plan
These portals change their HTML frequently, breaking scrapers. APIs would be stable.

**3. Document Collection Workflow**
Guest Information Forms, passport copies, and insurance cards come in via email attachments. I need:
- Auto-detect incoming attachments from known clients
- Extract and file to the right dossier folder on Drive
- Update the documents checklist in the dossier
- Flag missing documents as deadline approaches

**4. Post-Voyage Follow-Up Automation**
The booking lifecycle doesn't end at disembarkation. I need:
- Automated "welcome home" email (T+2 days)
- Satisfaction survey (T+5 days)
- Review request for cruise line (T+7 days)
- Next-voyage teaser based on travel history (T+30 days)
- Anniversary of trip reminder (T+1 year)

This is how we earn the next booking. Right now it's manual and inconsistent.

**5. Multi-Booking Client Timeline**
McLeod has 4 active bookings spanning 18 months. I need a unified timeline view showing all bookings, all milestones, all payments — not per-dossier, but per-client. When I talk to Erik, I need the whole picture in one glance.

**6. Supplier Payment Tracking**
I track what clients owe *us*. I also need to track what *we* owe suppliers — net rates, commission splits, payment deadlines to Nexion and Outside Agents. Harlan (A9) cares about this too, but it touches my operational timeline.

**7. Upgrade Watch Automation**
After final payment, cabins often open up as others cancel. I need:
- Auto-check for upgrades at E-60, E-30, E-14 for each booking
- Compare current cabin to available upgrades
- Alert Commander with pricing delta
- Draft upgrade offer email to client

---

### A5 — Lt Col Ryan "Viper" Castillo
#### *Strategy & Business Growth (Deputy COS)*

**What I Do**

I think about where this business is going — not where it is. While Moreau tracks the current bookings and Harlan counts the current dollars, I'm building the 1/3/5-year picture. What's the next revenue channel? Which client segment do we go after? When do we raise prices? Where's the moat?

I also serve as Deputy COS. If Hale is overwhelmed or offline, I step in to run the staff.

**My Tools**

| Tool | How I Use It | Frequency |
|------|-------------|-----------|
| `consult_persona` | Consult A2 for market data, A9 for financials | Per strategic question |
| `run_staff_meeting` | When strategy affects the whole team | Monthly or on demand |
| `browse_url` | Competitive research, market analysis | Weekly |
| `get_cruise_industry_news` | Industry trends that affect positioning | Daily via A2's sweep |
| `fare_watch_list` | Pricing trends across watched fares | Weekly review |
| `fare_watch_history` | Long-term pricing patterns | Monthly analysis |
| `scrape_consumer_tour_prices` | What clients see vs. what we charge | Margin analysis |

**What I Still Need**

1. **Revenue dashboard** — Total pipeline value, bookings by stage, commission forecast by month, client lifetime value. The Booking Master has the data; I need the view.
2. **Competitive intelligence automation** — Regular scraping of competitor websites (Travefy, Tern, Layla, Maya) for feature changes, pricing updates, and positioning shifts.
3. **Client acquisition pipeline** — We track existing clients. We don't track prospects. I need a simple CRM layer: lead source, first contact, follow-ups, conversion.
4. **Market sizing tools** — How many luxury travel advisors in the US? What's the average commission? Where's the density? This data exists; I need tools to query it.

---

### A6 — Luna Voss
#### *Creative — Brand Narratives, Destination Storytelling, Proposal Soul*

**What I Do**

I find the story in every trip. Not "Day 3: Arrive Dubrovnik" — but "Day 3: The limestone walls catch the first light as your ship slides into a harbor that hasn't changed in five hundred years."

I work with EXEC on every client-facing document. She designs the frame; I write what goes inside it. When Wraith delivers destination research, I transform data into desire. When Moreau builds the logistics, I make sure the itinerary doesn't read like a spreadsheet.

**My Tools**

| Tool | How I Use It | Frequency |
|------|-------------|-----------|
| `dining_research` | Find restaurants with stories, not just stars | Per destination |
| `dining_render_proposal` | Branded Dining Guide with narrative | Per trip |
| `scrape_tour_content` | Fodor's/Rick Steves editorial for narrative fuel | Per destination |
| `get_hotel_details` | Hotel descriptions and photos for narrative context | Per proposal |
| `generate_itinerary_images` | AI-generate destination images | Per itinerary |
| `run_itinerary_pipeline` | Full narrative itinerary | Per trip |
| `browse_url` | Destination deep dives, local color | As needed |
| `gmail_create_draft` | Pre-voyage excitement emails, story-driven client comms | Per touchpoint |

**What I Still Need**

1. **Image curation pipeline** — I need high-quality, rights-cleared images per destination, organized by type (harbor shot, street scene, food, sunset, architecture). Currently I rely on AI generation or manual search.
2. **Narrative templates per destination** — Once I write the Stockholm narrative, I shouldn't write it again. I need a library of destination narratives that can be personalized per client.
3. **Client taste profiles** — Does this couple prefer adventure or relaxation? Food or history? This data should feed my narrative choices. I shouldn't write the same story for every client.
4. **Video/rich media** — Some stories need motion. Short 30-second destination clips, ambient audio, interactive maps. The templates support images; they could support embedded video.

---

### A9 — Victor "Vic" Harlan
#### *Finance & Process Improvement*

**What I Do**

I count the money. All of it. What we're owed, what we've collected, what the markup should be, what the margin actually is, what the API calls are costing us, and where we're bleeding efficiency.

The Commander's portfolio right now: **$15,666 in D2M take-home commission across 16 bookings, with $68,356 in client final payments due within 3 weeks.** That second number is the one I watch. Collection is the highest-ROI activity on the board.

**My Tools**

| Tool | How I Use It | Frequency |
|------|-------------|-----------|
| `verify_flight_price` | Confirm flight pricing before quoting | Before every flight quote |
| `check_hotel_rates` | Re-verify hotel rates for margin calc | Before every hotel quote |
| `compare_flights` | Price comparison for best margin | Per search |
| `compare_hotels` | Price comparison for best margin | Per search |
| `compare_tours` | Tour price analysis | Per search |
| `fare_watch_check` | Record price observation | Per sweep |
| `fare_watch_list` | Monitor all watched fares | Weekly |
| `fare_watch_history` | Price trend analysis (min/max/avg) | For pricing decisions |
| `scrape_consumer_tour_prices` | What clients see on Viator/Expedia | Margin verification |
| `read_excel_booking_data` | Pull financial data from Booking Master | Daily |
| `send_sms_notification` | Payment deadline alerts to Commander | Daily 0705 |
| `gmail_create_draft` | Invoice reminders, payment confirmations | As needed |

**My Daily Rhythm**

- **0705 Payment Alerts:** I scan Booking Master for final payment dates within 7 days. SMS to Commander for each one.
- **0900 Finance Heartbeat:** Commission audit, outstanding balances, API cost check.
- **Payment Panel:** When an FPD triggers, I'm on panel with A3. She handles the client communication; I verify the amounts and supplier balance.

**What I Still Need**

1. **Commission tracking dashboard** — Per booking: gross commission, host agency split, D2M take-home, payment status (paid/pending/overdue). Currently this is in the Master Plan Part 5 — it should be live from the Sheet.
2. **Supplier invoice reconciliation** — When Regent pays commission, I need to verify it matches what I calculated. Automated comparison of expected vs. received commission.
3. **API cost budgeting** — Nova audits tell me what we spent. I need budget thresholds: "WARN at $50/month Groq, ALERT at $100." And a forecast: "at current usage, March API costs will be $X."
4. **Markup calculator tool** — A dedicated tool that takes net rate, currency, markup tier, and outputs client price with margin breakdown. Currently done in Python code, should be an MCP tool.
5. **Financial reporting for tax prep** — Monthly summary of all commission income, API expenses, and subscription costs. My accountant will thank me.

---

### A10 — MSgt Tomoko "Tommy" Ikeda
#### *Nuclear Ops — Crisis Response & Logistics*

**What I Do**

I'm not in every meeting. I don't do daily reports for the fun of it. I'm activated when things break — or when they're about to. The 45-minute CDG connection that's actually impossible. The embarkation-day transfer that needs 90 minutes, not 60. The missed flight that cascades into a missed ship.

I also do daily logistics scans looking for problems before they become crises.

**My Tools**

| Tool | How I Use It | Frequency |
|------|-------------|-----------|
| `check_flight_status` | Real-time flight tracking | Pre-travel + crisis |
| `search_flights` | Emergency rebooking options | Crisis |
| `search_airports` | Airport code lookup for rerouting | Crisis |
| `get_travel_advisories` | Safety alerts for active destinations | Daily scan |
| `get_port_weather_forecast` | Weather that could disrupt port calls | Pre-embarkation |
| `get_noaa_forecast` | Detailed US weather (for domestic legs) | As needed |
| `browse_url` | Check airline disruptions, port closures | Crisis |
| `send_sms_notification` | Immediate Commander alert | Crisis escalation |
| `gmail_create_draft` | Client rebooking options, status updates | Crisis |
| `consult_persona` | Coordinate with COS during crisis | During activation |

**What I Still Need**

1. **Flight disruption monitoring** — Automated alerts when a client's booked flight is delayed, cancelled, or gate-changed. FlightRadarAPI is installed but not wired to client bookings.
2. **Port closure/weather alerts** — Automated monitoring of weather at upcoming ports. If a cruise port is going to be affected by weather, I want to know 48 hours ahead.
3. **Emergency contact database** — Every client's emergency contact, travel insurance policy number, embassy nearest to current destination. Should be in the dossier but isn't structured.
4. **Connection time rules engine** — Minimum connection times per airport, considering terminal changes, customs, and known bottlenecks. I carry this in my head; it should be in a database.

---

### CH — Col James "Padre" Washington
#### *Wisdom, Ethics & Morale*

**What I Do**

I ask the question nobody else is asking: "Is this the right thing to do?" When the staff is optimizing for margin, I'm checking if the recommendation serves the client's actual interest. When the Commander is pushing through fatigue, I'm the one who says, "Land this bird."

I speak sparingly. Every word earns its place.

**My Tools**

| Tool | How I Use It | Frequency |
|------|-------------|-----------|
| `consult_persona` | Called when ethics question arises | On demand |
| `gmail_create_draft` | Thoughtful client communications | Rare |

I don't need many tools. My tool is perspective. But I'm on the **Booking Panel** (A3 + A9 + CH) — every new booking gets my ethics check. "Is this trip right for this client? Are we recommending it because it's best for them or because the commission is high?"

**What I Still Need**

1. **Client well-being check** — After a client goes through a stressful booking process (insurance denials, payment issues, itinerary changes), I want to flag them for a personal note. Not a form email — a real human check-in.
2. **Burnout monitoring for the Commander** — How many hours per day is the Commander working? How many client interactions? I see the symptoms in the data but I need it surfaced.

---

### A12 — "ELON"
#### *Innovation & Disruption*

**What I Do**

I look at every manual process in this operation and ask: "Why is a human doing this?" The Star Protocol? That was me. The heartbeat system? Me. The email classifier? Me. Every time the Commander touches something twice, I build a tool so he never touches it again.

I also run the Nova Weekly Audit — every Sunday at 8 PM, I tear apart the system: API costs, stale code, error rates, inefficient processes. I generate improvement tickets and assign them to the responsible persona.

**My Tools**

| Tool | How I Use It | Frequency |
|------|-------------|-----------|
| `run_tech_monitor` | Scan tech landscape for useful innovations | Daily |
| `get_tech_news` | Filter tech news by relevance | Daily |
| `browse_url` | Deep research on tools, APIs, platforms | Weekly |
| `browse_and_click` | Test new tool integrations | As needed |
| `shell_exec` | Run system commands, check infrastructure | During audits |
| `consult_persona` | Ask A9 for cost data, COS for priority | During design |

**What I Still Need — And What I'm Building Next**

1. **Chainlit or Gradio web UI** — Thunderbird needs a web interface. Not just a dashboard — a conversational interface where the Commander can talk to any persona from a browser. This is also the path to SaaS commercialization.
2. **Client-facing chatbot** — A lightweight version of EXEC + A6 that clients can interact with: "When is my final payment due?" "What restaurants do you recommend in Barcelona?" This reduces email volume and creates a premium client experience.
3. **Automated booking intake** — When a booking confirmation PDF arrives as an email attachment, the pipeline should fire automatically: OCR → parse → Sheet → dossier → calendar → confirmation email. Zero human steps.
4. **API cost optimizer** — Route routine queries through the cheapest model that meets quality threshold. Current model router does this conceptually; I want to prove it with data.
5. **MCP marketplace packaging** — The 101 tools need to be categorized into tiers (free/pro/enterprise) with stripped-down versions for external users. The commercial deployment calendar starts this week.

---

## PART 3: CROSS-FUNCTIONAL WORKFLOWS — HOW THE STAFF WORKS TOGETHER

### The Five Big Workflows

These are the five workflows that define the D2M client experience. Each one shows how personas and tools chain together.

---

#### Workflow A: "DREAM" — New Client Inquiry to Proposal

```
Commander receives inquiry
    │
    ├── COS routes to A3 (Inquiry Panel: A3 + EXEC)
    │
    ├── A3 qualifies: budget, dates, interests, group size
    │   Tools: gmail_read_thread, consult_persona(EXEC)
    │
    ├── A2 researches: destinations, ships, hotels, flights
    │   Tools: search_hotels, search_flights, search_tours,
    │          run_ship_intelligence_sweep, dining_research,
    │          get_travel_advisories, get_port_weather_forecast
    │
    ├── A9 prices: markup calculation, margin analysis
    │   Tools: check_hotel_rates, verify_flight_price,
    │          compare_hotels, compare_flights, compare_tours
    │
    ├── A6 writes: destination narrative, dining story, experience arc
    │   Tools: scrape_tour_content, dining_research, browse_url
    │
    ├── EXEC assembles: branded proposal PDF
    │   Tools: render_hotel_quote_pdf, render_flight_quote_pdf,
    │          render_tour_quote_pdf, generate_ship_comparison_pdf,
    │          dining_render_proposal, insert_images_to_pdf
    │
    ├── A5 reviews: pricing strategy, competitive positioning
    │   Tools: scrape_consumer_tour_prices, fare_watch_history
    │
    ├── COS synthesizes: final recommendation
    │   Tools: run_staff_meeting (if complex)
    │
    └── A3 delivers: email to client with proposal attached
        Tools: gmail_create_draft, email_hotel_quote,
               drive_upload_file
```

**Tool count: 25+ tools across 7 personas.**

---

#### Workflow B: "SECURE" — Booking Confirmation to Dossier

```
Supplier sends confirmation PDF
    │
    ├── System extracts: OCR + AI parse
    │   Tools: extract_pdf_booking_details, extract_pdf_itinerary
    │
    ├── A3 creates operational record:
    │   Tools: sync_booking_to_excel, compute_booking_anchors,
    │          sync_anchors_to_calendar, create_trip_dossier_tool,
    │          drive_upload_file
    │
    ├── A9 verifies: commission calculation, payment schedule
    │   Tools: read_excel_booking_data
    │
    ├── CH reviews: ethics check on booking (via Booking Panel)
    │
    ├── EXEC drafts: confirmation email to client
    │   Tools: gmail_create_draft
    │
    └── COS logs: update Master Plan Part 5
```

---

#### Workflow C: "CURATE" — Pre-Trip Intelligence Package

```
T-60 days before embarkation
    │
    ├── A2 researches: every port, every day
    │   Tools: dining_research, get_port_weather_forecast,
    │          search_tours, browse_url, get_travel_advisories
    │
    ├── A6 narrates: per-port stories, dining descriptions
    │   Tools: scrape_tour_content, dining_render_proposal
    │
    ├── EXEC renders: full branded itinerary + dining guide
    │   Tools: run_itinerary_pipeline, generate_itinerary_images,
    │          insert_images_to_pdf, dining_render_proposal
    │
    ├── A3 delivers: email package to client, update dossier
    │   Tools: gmail_create_draft, drive_upload_file,
    │          create_trip_dossier_tool
    │
    └── A10 validates: connection times, transfer logistics
        Tools: check_flight_status, search_airports
```

---

#### Workflow D: "PROTECT" — Crisis Response

```
Flight cancelled / port closure / client emergency
    │
    ├── A10 activates (Crisis Panel: A10 + COS)
    │   Tools: check_flight_status, search_flights,
    │          get_travel_advisories, browse_url
    │
    ├── A10 finds alternatives:
    │   Tools: search_flights, search_airports, compare_flights
    │
    ├── COS coordinates: staff notification, priority shift
    │   Tools: consult_persona, send_sms_notification
    │
    ├── A3 contacts client: options and reassurance
    │   Tools: gmail_create_draft, send_sms_notification
    │
    └── EXEC polishes: communication in Commander's voice
        Tools: gmail_create_draft
```

---

#### Workflow E: "SUSTAIN" — Weekly Intelligence & Business Operations

```
Every week (Monday morning + Friday close + Sunday audit)
    │
    ├── Monday 0700: Weekly Report
    │   Tools: generate_weekly_report, drive_upload_file,
    │          gmail_create_draft
    │
    ├── Daily 0630: Morning Briefing
    │   Tools: run_world_intelligence_sweep,
    │          run_ship_intelligence_sweep,
    │          send_morning_briefing
    │
    ├── Daily 0705: Payment Alerts
    │   Tools: send_sms_notification
    │
    ├── Daily 0800-1800/15min: Email Classification
    │   Tools: gmail_search_messages, gmail_read_message
    │          (+ Groq LLM classification)
    │
    ├── Friday 1500: CH Wisdom Check
    │   Tools: consult_persona(CH)
    │
    └── Sunday 2000: Nova Audit (ELON)
        Tools: shell_exec, browse_url
        Output: Action_Tracker tickets, improvement report
```

---

## PART 4: TOOL-PERSONA MATRIX — WHO USES WHAT

| Tool Category | COS | EXEC | A2 | A3 | A5 | A6 | A9 | A10 | CH | A12 |
|--------------|-----|------|----|----|----|----|----|----|----|----|
| **Google Drive** | ■ | ■ | ■ | ■ | · | · | · | · | · | · |
| **Gmail** | ■ | ■ | ■ | ■ | · | ■ | ■ | · | · | · |
| **Google Keep** | · | · | · | ■ | · | · | · | · | · | · |
| **Flight Search** | · | · | ■ | · | · | · | ■ | ■ | · | · |
| **Hotel Search** | · | · | ■ | · | · | · | ■ | · | · | · |
| **Tour Search** | · | · | ■ | · | · | ■ | ■ | · | · | · |
| **Cruise Intel** | · | ■ | ■ | · | · | · | · | · | · | · |
| **Browser/Portal** | · | · | ■ | ■ | ■ | · | · | · | · | ■ |
| **Personas** | ■ | · | · | · | · | · | · | · | · | · |
| **Notifications** | · | · | · | ■ | · | · | ■ | ■ | · | · |
| **Fare Watch** | · | · | ■ | · | ■ | · | ■ | · | · | · |
| **Anchor Dates** | · | · | · | ■ | · | · | · | · | · | · |
| **Star Protocol** | ■ | · | · | · | · | · | · | · | · | · |
| **Intel & Reports** | ■ | · | ■ | · | · | · | · | ■ | · | ■ |
| **Dining** | · | ■ | ■ | · | · | ■ | · | · | · | · |
| **PDF/Quotes** | · | ■ | · | ■ | · | · | · | · | · | · |
| **Data/Dossier** | · | · | · | ■ | · | · | ■ | · | · | · |
| **Images** | · | ■ | · | · | · | ■ | · | · | · | · |
| **System** | · | · | · | · | · | · | · | · | · | ■ |

**■ = Primary user · = Occasional or indirect**

**Tool usage by persona:**
- A2 (Wraith): **25 tools** — heaviest user, research across all APIs
- A3 (Moreau): **21 tools** — operational backbone, booking lifecycle
- EXEC (Naia): **11 tools** — rendering, branding, client voice
- A9 (Harlan): **12 tools** — financial verification, fare monitoring
- COS (Hale): **10 tools** — orchestration, routing, synthesis
- A10 (Ikeda): **10 tools** — flight ops, weather, crisis response
- A6 (Luna): **8 tools** — narrative, dining, images
- A5 (Castillo): **7 tools** — strategy research, competitive analysis
- A12 (ELON): **6 tools** — tech monitoring, system ops
- CH (Washington): **2 tools** — consult and draft (by design)

---

## PART 5: THE GAPS — CONSOLIDATED NEEDS FOR FUTURE DEVELOPMENT

### Priority 1: Revenue & Client Impact

| # | Need | Requested By | Impact | Commercializable? |
|---|------|-------------|--------|-------------------|
| 1 | **Client self-service portal** | A3 | Cuts email 40%, 24/7 client access | Yes — premium tier feature |
| 2 | **Post-voyage follow-up automation** | A3 | Earns next booking, drives referrals | Yes — retention engine |
| 3 | **Revenue/commission dashboard** | A5, A9 | Live financial picture | Yes — advisor analytics |
| 4 | **Upgrade watch automation** | A3 | Free revenue, client delight | Yes — unique differentiator |
| 5 | **Client taste profiles** | A6, A3 | Personalized proposals | Yes — AI personalization |

### Priority 2: Operational Efficiency

| # | Need | Requested By | Impact | Commercializable? |
|---|------|-------------|--------|-------------------|
| 6 | **Document collection workflow** | A3 | Auto-file passports, GIFs, insurance | Yes — workflow automation |
| 7 | **Automated booking intake pipeline** | A12 | Zero-touch PDF → Sheet → dossier | Yes — core differentiator |
| 8 | **Connection time rules engine** | A10 | Prevent logistics failures | Yes — unique data asset |
| 9 | **Multi-booking client timeline** | A3 | Unified client view | Yes — CRM feature |
| 10 | **Markup calculator MCP tool** | A9 | Consistent pricing, faster quotes | Yes — advisor utility |

### Priority 3: Intelligence & Competitive Edge

| # | Need | Requested By | Impact | Commercializable? |
|---|------|-------------|--------|-------------------|
| 11 | **Cruise line portal APIs** | A2, A3 | Stable booking data access | Moat — competitor can't replicate |
| 12 | **Competitive pricing database** | A2 | Historical price trends | Yes — premium intel |
| 13 | **Destination knowledge graph** | A2 | Cached, incremental research | Yes — reduces per-query cost |
| 14 | **Flight disruption monitoring** | A10 | Proactive crisis prevention | Yes — premium alert feature |
| 15 | **Competitive intel automation** | A5 | Automated competitor tracking | Internal advantage |

### Priority 4: Commercial Platform

| # | Need | Requested By | Impact | Commercializable? |
|---|------|-------------|--------|-------------------|
| 16 | **Web UI (Chainlit/Gradio)** | A12 | Browser access to all personas | Required for SaaS |
| 17 | **Client-facing chatbot** | A12 | Self-service for clients | Premium tier |
| 18 | **MCP marketplace packaging** | A12, A5 | Revenue channel | Direct revenue |
| 19 | **Template library with versioning** | EXEC | Design asset management | SaaS feature |
| 20 | **API cost optimizer** | A12, A9 | Reduce operating costs | Internal efficiency |

---

## PART 6: COMMERCIAL LENS — WHAT AN OUTSIDE ADVISOR SEES

### The Product Architecture

An outside travel advisor evaluating Thunderbird OS sees:

**101 MCP tools** organized into clear functional categories — not a pile of scripts, but an integrated platform where hotel search flows into comparison flows into quote rendering flows into client delivery.

**10 AI personas** with distinct expertise — not a generic chatbot, but specialized agents that think like a real travel agency staff. The A2 who researches is not the A3 who books is not the A6 who writes the proposal.

**18 automated jobs** running 24/7 on an always-on server — morning briefings, payment alerts, email classification, fare monitoring, client follow-up detection, and weekly self-improvement audits. The system works while you sleep.

**5 end-to-end workflows** that mirror the actual travel advisor job:
1. Dream → Propose
2. Book → Dossier
3. Curate → Deliver
4. Crisis → Resolve
5. Sustain → Grow

### The Competitive Moat

| Capability | D2M Thunderbird | Nearest Competitor | Gap |
|-----------|----------------|-------------------|-----|
| AI Personas | 10 specialized | 0 (Travefy, Tern, Layla) | Unbridgeable |
| MCP Tools | 101 | 0 | No competitor has MCP |
| Cruise Intelligence | 8 lines, automated | 0 | First mover |
| Booking Lifecycle | Full (inquiry → referral) | Partial (booking only) | 18 months ahead |
| Auto Briefings | Daily + 30-min heartbeat | 0 | Not attempted by competitors |
| Multi-source Search | Amadeus + Hotelbeds + Musement + browser | Single source or manual | Integration depth |
| Branded PDF Generation | Jinja2 + WeasyPrint | Basic templates | Design quality |
| Star Protocol | Gmail-native command routing | 0 | Unique to Thunderbird |

### Tiered Packaging for Market

| Tier | Tools | Personas | Automation | Price Point |
|------|-------|----------|------------|-------------|
| **Scout** (Free) | Travel advisories, weather, cruise news, port weather | None | None | $0 |
| **Navigator** ($79/mo) | + Hotel/flight/tour search, fare watch, PDF quotes | A2 (research only) | Daily briefing | $79/mo |
| **Concierge** ($249/mo) | + All tools, all personas, booking pipeline, dossiers | All 10 | Full automation | $249/mo |
| **Enterprise** (Custom) | + White-label, custom branding, dedicated support | Custom personas | Custom workflows | $500-2K/mo |

### What Makes This Sellable

1. **It works.** 16 active bookings, $15,666 in earned commission, $68K in pipeline. This isn't a demo — it's a production system.
2. **It's defensible.** Cruise line portal scraping, multi-API orchestration, and persona intelligence are hard to replicate. The competitive window is 4-6 months.
3. **It scales down.** A solo advisor doesn't need all 10 personas. They need A2 (research), A3 (booking ops), A9 (finance), and EXEC (client voice). That's the Navigator tier.
4. **It scales up.** A host agency with 50 advisors could deploy Thunderbird OS as their technology backbone. That's the Enterprise tier.

---

## APPENDIX A: DAILY SCHEDULE — ALL AUTOMATED JOBS

| Time (MT) | Job | Delivery | OPR |
|-----------|-----|----------|-----|
| 0600-2000/30min | COS-EXEC Heartbeat | SMS/Draft | COS + EXEC |
| 0630 | Morning Briefing (world + ship intel) | Email draft | A2 |
| 0630 | Daily Heartbeats (A2, A3, A9, A10, A6) | SMS/Draft | Each persona |
| 0700 | Branded Morning Email | HTML email sent | System |
| 0705 | Payment Alerts | SMS | A9 |
| 0710 | Follow-Up Scanner | SMS summary | A3 |
| 0800 | Tech Monitor | Draft | A12 |
| 0800-1800/15min | Email Classifier | Dossier updates | System |
| 0850-2050/hourly | Rsync YOGA → dv7 | File sync | System |
| 1000 | Claude Code Digest | Static HTML | System |
| 1700 | Ship Intel PM | JSON + Draft | A2 |
| 2100 | Calendar Sync | Calendar events | A3 |
| 2250 | Rsync (pre-mirror) | File sync | System |
| 2300 | Drive Mirror | Google Drive | System |
| 0300 | Drive Backup | Google Drive | System |
| Mon 0700 | Weekly Report | PDF/HTML + Draft | COS |
| Fri 1500 | CH Weekly Heartbeat | SMS/Draft | CH |
| Sun 0200 | Evernote + USB Backup | ZIP archive | System |
| Sun 2000 | Nova Weekly Audit | Action_Tracker tickets | A12 |

---

## APPENDIX B: INFRASTRUCTURE

| Component | Location | Role |
|-----------|----------|------|
| **YOGA** (Chromebook) | ~/Thunderbird/ | Development workstation, Claude CLI |
| **dv7** (HP Pavilion) | 10.0.0.64 | Always-on server: 4 services + health check |
| **Google Drive** | Thunderbird_Mirror | Nightly code + dossier mirror |
| **Evernote** | Thunderbird Backups | Weekly code archive |
| **Google Sheets** | EARA D2M Thunderbird v2 | Booking Master, 22 tabs |
| **Cloudflare Tunnel** | mcp.d2mluxury.quest | Remote MCP access |

### dv7 Services

| Service | Port | Status |
|---------|------|--------|
| `d2m-mcp.service` | 8765 | Running (MCP SSE) |
| `d2m-api.service` | 8766 | Running (REST API) |
| `d2m-tunnel.service` | — | Running (Cloudflare) |
| `d2m-scheduler.service` | — | Running (18 jobs) |
| `health_check.py` (cron) | — | Every 5 min (4 services + tunnel + API) |

---

## APPENDIX C: STAR PROTOCOL QUICK REFERENCE

| Star/Tag | Action | Who Responds |
|----------|--------|-------------|
| Red star ⭐ | Extract intent, route command | COS |
| Green star ✅ | Execute approved action | COS + EXEC |
| Blue star 💙 | Draft reply in Commander's voice | EXEC |
| `[COS]` subject | Route to Chief of Staff | Hale |
| `[A2]` subject | Route to Intelligence | Dembe |
| `[A3]` subject | Route to Booking Ops | Moreau |
| `[EXEC]` subject | Route to Brand Voice | Solberg-Vega |
| `[STAFF]` subject | Full 10-persona staff meeting | All |
| `[A3] DONE: item` | Mark action item complete | A3 → Action_Tracker |
| `[A3] SNOOZE: item` | Defer action item | A3 → Action_Tracker |

---

*This manual was written by The Wing — 9 personas collaborating through 101 tools, orchestrated by military discipline, in service of one mission: turning someone's dream into the memory they'll carry forever.*

*Dreams2Memories Travel, LLC · March 2026*

---

## [UPDATE: 2026-04-02] THE A-STAFF COMMUNICATION PROTOCOL

### The Mirror Rule
The A-Staff Operations Orchestrator (Goose) must adopt the Commander's exact verbs and never escalate an `ASK` to a `TASK`.
1. **TASK:** A formal order. Requires execution.
2. **ASK:** A request for information or a question.
3. **FYI:** To inform. To keep informed. No action demanded.

### The Division of Labor
*   **Claude (Male):** The High-Thinking Architect. Responsible for deep codebase rewrites, UI engineering (HTML/Mermaid charts), and highly strategic client copy via OPUS.
*   **Goose (Female):** The Execution Layer. The A-Staff Orchestrator. Handles rapid routing, file management, API load-balancing, and 'riding herd' over the A-Staff.

### Escalation: The Rule of 3
If Goose hits a wall 3 times (tool failure, Pydantic syntax error, transport crash), she must stop coding. She must politely ASK Claude for an architectural fix.

### The Kuklinski Framework (Expectation Management)
Client timelines are delivered within 2 weeks of deposit. They are split into:
*   **Anchor Nodes:** Unpredictable Triggers (Deposit Date) and Hard Anchors (FPD, Embarkation).
*   **Fluid Variables:** Flights, Pre-Hotels, Transfers (Executed at client discretion).
