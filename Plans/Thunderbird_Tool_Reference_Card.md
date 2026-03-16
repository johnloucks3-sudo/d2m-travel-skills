# Thunderbird OS — 53-Tool Reference Card
## Dreams2Memories Travel, LLC
### Updated: 2026-03-05

---

## GOOGLE DRIVE (8 tools)

| Tool | What It Does | How to Activate |
|------|-------------|-----------------|
| `drive_list_files` | Lists files/folders in Drive with optional type filter (folder, doc, sheet, pdf, image). Supports pagination up to 500 results. | "List my Drive files" or "Show folders in [folder ID]" |
| `drive_search` | Searches Drive by file name or full-text content. Escapes queries safely. | "Search Drive for Silversea confirmation" |
| `drive_get_file_info` | Gets detailed metadata for a specific file — owner, permissions, size, dates, web link. | "Get info on this Drive file [ID]" |
| `drive_read_document` | Reads content of a Google Doc or Sheet. Exports as text, HTML, or CSV. | "Read the booking spreadsheet [ID]" |
| `drive_create_folder` | Creates a new folder in Drive, optionally inside a parent folder. | "Create a folder called Furlow_2026 in the vault" |
| `drive_upload_file` | Uploads a local file to Drive with auto-detected MIME type. Resumable upload for large files. | "Upload output/quote.pdf to Drive" |
| `drive_download_file` | Downloads a file from Drive to local. Auto-exports Google Docs to PDF, Sheets to XLSX. | "Download this file [ID] to ~/Thunderbird/output/" |
| `drive_move_file` | Moves a file to a different folder and/or renames it. | "Move this file to the Furlow folder" |

---

## GMAIL (6 tools)

| Tool | What It Does | How to Activate |
|------|-------------|-----------------|
| `gmail_get_profile` | Returns email address, total messages/threads. Great connectivity test. | "Test Gmail connection" or "Check my Gmail profile" |
| `gmail_search_messages` | Searches Gmail using standard query syntax (from:, subject:, has:attachment, etc.). Returns summaries with headers. | "Search Gmail for emails from Silversea" |
| `gmail_read_message` | Reads full email content by message ID. Lists attachments without downloading. Truncates at 30K chars. | "Read this email [message ID]" |
| `gmail_read_thread` | Reads all messages in a conversation thread. Shows full back-and-forth. | "Show me the full thread [thread ID]" |
| `gmail_list_drafts` | Lists existing Gmail drafts with subject, recipient, and snippet preview. | "Show my Gmail drafts" |
| `gmail_create_draft` | Creates a draft email (plain text). Supports CC/BCC and reply-to-thread. NEVER sends — you review first. | "Draft an email to [client] about their booking" |

---

## FLIGHTS (6 tools)

| Tool | What It Does | How to Activate |
|------|-------------|-----------------|
| `search_flights` | Searches Amadeus for flight offers. Filters by cabin class, nonstop, max price. Returns net + D2M markup pricing. | "Search flights DEN to NRT on April 1" |
| `verify_flight_price` | Re-confirms flight pricing before quoting. Prices are volatile — always verify. | "Verify this flight offer before I quote it" |
| `search_airports` | Looks up IATA codes by city/airport name. Use before flight search. | "What's the airport code for Tokyo?" |
| `compare_flights` | Side-by-side comparison of 2-5 flight offers with Best Price and Fewest Stops badges. | "Compare these three flight options" |
| `render_flight_quote_pdf` | Generates branded PDF with flight cards, comparison table, and recommendation. | "Create a flight quote PDF for the Furlows" |
| `email_flight_quote` | Creates Gmail draft with HTML flight summary and optional PDF attachment. | "Email the flight quote to [client email]" |

---

## HOTELS (8 tools)

| Tool | What It Does | How to Activate |
|------|-------------|-----------------|
| `search_hotels` | Searches Hotelbeds API by destination code, lat/lon, or hotel codes. Filters by stars, price, board type. | "Search hotels in Palma for June 15-20" |
| `check_hotel_rates` | Re-verifies hotel rate pricing using rate keys from search. Required when rateType is RECHECK. | "Verify this hotel rate before quoting" |
| `get_hotel_details` | Gets hotel content — description, photos, facilities, address, coordinates. From Hotelbeds Content API. | "Get details for hotel code 12345" |
| `compare_hotels` | Side-by-side comparison of hotel options with pricing and features. | "Compare these three hotels" |
| `bedsonline_browse_search` | Opens Bedsonline portal in stealth browser, logs in, searches hotels visually. Takes screenshots. | "Search Bedsonline for hotels in Barcelona" |
| `bedsonline_browse_interact` | Continues interacting with an open Bedsonline session — click elements, navigate. | "Click on the first hotel result" |
| `render_hotel_quote_pdf` | Generates branded PDF hotel quote with photos, rates, and comparison. | "Create a hotel quote PDF for the Smiths" |
| `email_hotel_quote` | Creates Gmail draft with hotel summary and optional PDF attachment. | "Email the hotel quote to [client]" |

---

## TOURS & ACTIVITIES (8 tools) — NEW

| Tool | What It Does | How to Activate |
|------|-------------|-----------------|
| `search_tours` | Searches Amadeus Tours & Activities API by lat/lon coordinates. Returns pricing with D2M markup. 894 results for Paris alone. | "Search tours near Paris" or "Find activities in Rome" |
| `search_tours_musement` | Scrapes Musement's public site for tours by city. Good European/global coverage. | "Search Musement for tours in Barcelona" |
| `browse_tour_portal` | Opens a VISIBLE browser to an agent portal. Pauses for you to log in manually, then searches and scrapes results. | "Open ProjectExpedition" or "Browse TAAP for Rome tours" |
| `scrape_consumer_tour_prices` | Headless scrape of Expedia and/or Viator public pricing. Use to compare agent net vs. consumer price. | "Check Expedia prices for Paris tours" |
| `scrape_tour_content` | Scrapes Fodor's and Rick Steves for expert recommendations. Validates tour quality and finds hidden gems. | "What does Rick Steves recommend in Florence?" |
| `compare_tours` | Side-by-side comparison of 2-10 tours with Best Value and Highest Rated badges. Shows savings vs. consumer pricing. | "Compare these tour options side by side" |
| `render_tour_quote_pdf` | Generates branded PDF with tour cards, photos, comparison table, logo, headshot, and slogan. | "Create a tour quote PDF for the Johnsons" |
| `email_tour_quote` | Creates Gmail draft with tour summary table and optional PDF attachment. Uses OAuth Gmail. | "Email the tour quote to [client]" |

---

## CRUISE INTELLIGENCE (5 tools)

| Tool | What It Does | How to Activate |
|------|-------------|-----------------|
| `list_available_ships` | Lists all cruise ships/lines in the intelligence database. | "What ships do we track?" |
| `search_live_cruise_voyages` | Stealth browser scrapes cruise line websites for live voyage listings. | "Search Silversea voyages" |
| `check_cabin_availability` | Scrapes a specific voyage page for cabin categories and live pricing. | "Check cabins on this Silversea voyage" |
| `scrape_specific_cruise_line` | Targeted scrape of a specific cruise line's website for pricing/availability. | "Scrape Regent Seven Seas for Alaska" |
| `run_ship_intelligence_sweep` | Runs a full intelligence sweep across targeted cruise lines. Compares pricing and availability. | "Run a ship intel sweep" |

---

## SHIP COMPARISON (2 tools)

| Tool | What It Does | How to Activate |
|------|-------------|-----------------|
| `generate_ship_comparison_docx` | Generates a DOCX report comparing two or more cruise ships side by side. | "Compare Silver Nova vs Seven Seas Grandeur" |
| `generate_ship_comparison_pdf` | Same comparison but rendered as a branded PDF. | "Create a ship comparison PDF" |

---

## WORLD INTELLIGENCE (3 tools)

| Tool | What It Does | How to Activate |
|------|-------------|-----------------|
| `get_travel_advisories` | Fetches current travel advisories for a destination. Safety levels, warnings, entry requirements. | "Any advisories for Japan?" |
| `get_port_weather_forecast` | Gets weather forecasts for cruise ports on specific dates. | "What's the weather in Santorini in June?" |
| `get_cruise_industry_news` | Scrapes latest cruise industry news from trade sources. | "What's new in the cruise industry?" |

---

## BOOKING PIPELINE (4 tools)

| Tool | What It Does | How to Activate |
|------|-------------|-----------------|
| `extract_booking_from_pdf` | OCR + Groq LLM extraction of booking data from cruise PDFs. Optionally pushes to Google Sheets. | "Extract booking from this PDF" |
| `extract_master_booking_data` | Parses raw booking text with regex + LLM for supplier, client, cost, dates. | "Parse this booking text" |
| `run_itinerary_pipeline` | Full pipeline: PDF -> extract -> images -> Google Docs itinerary. | "Run the itinerary pipeline for [booking]" |
| `generate_weekly_report` | Generates automated weekly summary of bookings, activity, and revenue. | "Generate this week's report" |

---

## BROWSER & UTILITIES (3 tools)

| Tool | What It Does | How to Activate |
|------|-------------|-----------------|
| `browse_url` | Opens any URL in a stealth browser and returns page text. General-purpose web scraping. | "Browse this URL and tell me what's there" |
| `browse_and_click` | Navigates to a URL and clicks a specific element. For multi-step web interactions. | "Go to this page and click the search button" |
| `run_tech_monitor` | Scrapes technology news relevant to travel tech. Digest format. | "What's new in travel tech?" |

---

## QUICK COUNTS

| Category | Tools |
|----------|-------|
| Google Drive | 8 |
| Gmail | 6 |
| Flights (Amadeus) | 6 |
| Hotels (Hotelbeds) | 8 |
| Tours & Activities | 8 |
| Cruise Intel | 5 |
| Ship Comparison | 2 |
| World Intel | 3 |
| Booking Pipeline | 4 |
| Browser & Utilities | 3 |
| **TOTAL** | **53** |
