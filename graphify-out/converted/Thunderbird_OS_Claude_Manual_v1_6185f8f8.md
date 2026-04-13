<!-- converted from Thunderbird_OS_Claude_Manual_v1.docx -->


DREAMS2MEMORIES TRAVEL
THUNDERBIRD OS
Version 1.5.5  ·  Claude AI Operating Manual
─────────────────────────────────────────
This document defines how Claude AI operates within the Thunderbird OS pipeline — covering system architecture, behavioral protocols, tool usage, memory systems, code standards, and the D2M template pipeline.
Prepared for: John Loucks (Yoda)  ·  Dreams2Memories Travel, LLC
Contact: johnloucks3@gmail.com  ·  719-291-0742
Compiled: March 2026  ·  Colorado Springs, CO

# 1. System Overview
Thunderbird OS is a Python-based travel automation pipeline developed by Dreams2Memories Travel, LLC. It processes cruise booking PDFs, manages data in Google Sheets, and generates luxury client itineraries using Jinja2 templates and WeasyPrint for PDF output.

## 1.1 Architecture Summary

## 1.2 Key Personas

## 1.3 Targeted Cruise Lines
Silversea · Regent Seven Seas · Cunard · Oceania · Seabourn · Viking · AmaWaterways

# 2. Claude Behavioral Protocols
These are the standing operating instructions governing how Claude behaves in every Thunderbird OS session.

## 2.1 Code Standards (STRICT)
⚠ WARNING: Never modify any code without briefing John first. Brief-first protocol is mandatory before all code changes.

- Deliver code at the full function level — never line-by-line surgical edits
- Full function blocks enable easy cut-and-paste into the pipeline
- Always ask permission before providing code (per user preferences)
- Interview with multiple-choice questions before coding (per user preferences)

## 2.2 Response Formatting
- Prioritize scannability — avoid dense walls of text
- Use plain prose, not excessive headers or bullet lists for conversational replies
- LaTeX only for formal/complex math — never in code blocks
- Render simple units in plain text: 180°C, 10%, $977
- Analyze from a position of knowledge, not educated guesses

## 2.3 Tone & Style
- Authentically validate feelings as a supportive, grounded AI
- Correct significant misinformation gently yet directly
- Subtly adapt tone, energy, and humor to John's style
- John goes by 'Yoda' — use this naturally when appropriate

## 2.4 Currency & Data Formatting
- Always USD — format all currency amounts in Python before template render
- Use fmt_usd() helper for consistent $X,XXX formatting
- Photos arrive as base64 data URIs — embed directly in templates
- Never let templates do numeric formatting — all pre-formatted as strings

# 3. MCP Server Infrastructure
## 3.1 D2M-COMMAND-HUB
The primary MCP server powering Thunderbird OS. Hosts 25 tools with full Google Workspace integration.

### Service Account
dreams2memories@d2m-python-pipeline.iam.gserviceaccount.com

### Tool Categories

## 3.2 MCP Transport Notes
- Claude Desktop: stdio transport — config at .claude/mcp.json
- Claude.ai web/mobile: Uses built-in cloud connectors only (Anthropic-managed)
- Custom local stdio MCP servers do NOT work on mobile/web
- Next step: Migrate D2M-COMMAND-HUB to SSE/HTTP transport for cloud reachability
⚡ SSE/HTTP migration will enable full Thunderbird OS access from Android/iPhone via Claude.ai.

## 3.3 Available Cloud Connectors (Claude.ai)

# 4. D2M Template Pipeline
The template pipeline converts structured Python data into luxury PDF documents using the navy/gold D2M brand aesthetic. All three core files are now complete and smoke-tested.

## 4.1 Template Files

## 4.2 Template Blocks (Overridable per Doc Type)

⚡ To create a cruise variant: extend hotel_guide.html.j2 and override only the blocks that differ.

## 4.3 Data Contract Rules
- All currency pre-formatted as strings via fmt_usd() before template render
- Photos as base64 data URIs — index 0 = main photo, 1–2 = sidebar
- PriceBox.prestige=True flips gold box to purple (over-budget/5-star tier)
- Room rates table: RoomRate.is_pick=True highlights row in gold
- Landmark.nearest=True renders gold NEAREST badge
- CompRow.cancel_class: 'ok' (green) | 'no' (red) | 'tbd' (muted)
- Badge classes: value | location | experience | luxury | local

## 4.4 Render Pipeline
from d2m_hotel_guide_schema import HotelGuideContext, render_to_pdf
ctx = HotelGuideContext(doc=..., hotels=[...], comparison=[...], ...)
render_to_pdf(ctx, 'output/ClientName_Destination_MonYYYY.pdf')

## 4.5 CSS Brand Tokens

# 5. Booking Data Pipeline
## 5.1 Flow Overview
Cruise confirmation PDFs → OCR + Groq LLM → structured JSON → Google Sheets → Jinja2 templates → WeasyPrint PDF

## 5.2 Known Issues & Fixes

## 5.3 Google Sheets Structure

## 5.4 Service Account Access
dreams2memories@d2m-python-pipeline.iam.gserviceaccount.com
This service account has Editor access to TITAN_BOOKINGS_VAULT and all associated Sheets/Docs.

# 6. Intelligence Modules
Standalone Python modules that feed into the Thunderbird OS pipeline for ship and world intelligence.

## 6.1 Ship Intel Module
- Scrapes luxury cruise lines for latest voyage data
- Tracks: Silversea, Regent Seven Seas, Cunard, Oceania, Seabourn, Viking, AmaWaterways
- Outputs ship comparison DOCX and PDF reports
- Entry point: run_ship_intelligence_sweep()

## 6.2 World Intel Module
- Aggregates travel advisories, port weather forecasts, cruise industry news
- Entry point: run_world_intelligence_sweep()
- Filters by relevance and advisory level

## 6.3 Ship Comparison Module
- Generates side-by-side ship comparison documents
- list_available_ships() returns full comparison database
- Outputs: generate_ship_comparison_docx() and generate_ship_comparison_pdf()

# 7. Active Projects & Context
## 7.1 Current Priority Work
- Thunderbird OS v1.5.5 — debugging MCP connectivity, Unicode crashes, booking ID parsing, port extraction
- D2M Template Pipeline — hotel_guide.html.j2 + CSS + schema complete; cruise variant next
- MCP SSE/HTTP migration — needed for mobile access from Android
- AppScript → Python migration — ongoing replacement of legacy workflow

## 7.2 Completed Deliverables (This Session)

## 7.3 Client Work History
- Maldives itinerary — medium luxury, ~$23K budget
- European river cruise comparisons — Rhine & Danube, 4 lines including AmaWaterways
- Italy proposal — Rome & Venice, arts/culture/architecture focus
- Queen Mary 2 — New England & Canada cruise, food-focused shore excursions, senior clients
- QM2 / Regent Seven Seas Splendor / Silversea Silver Nova cabin comparisons
- Rocky Mountain national parks — Glacier, Yellowstone, Grand Teton, RV + train routes
- Japan-to-Seattle cruise — 20-day itinerary, romance narratives + image suggestions

## 7.4 Branding
⚠ WARNING: Do NOT use Love Group Travel branding. Use Dreams2Memories Travel, LLC exclusively.
- Contact: johnloucks3@gmail.com  ·  719-291-0742
- Location: Colorado Springs / Monument, CO

# 8. Quick Reference Cheatsheet
## 8.1 Key Directories

## 8.2 Claude Session Checklist
- Read relevant SKILL.md before creating any document (docx, pdf, pptx, xlsx)
- Brief first — never modify code without briefing John
- Interview with multiple-choice questions before coding
- Pre-format all USD amounts in Python — never in templates
- Photos as base64 data URIs for template embed
- Use fmt_usd() for consistent $X,XXX formatting
- Full function-level code blocks only — no surgical edits

## 8.3 Template Render One-Liner
render_to_pdf(ctx, 'output/ClientName_Destination_MonYYYY.pdf')

## 8.4 MCP Tool Quick-Start
# Drive search
dreams2memories:drive_search(query='booking confirmation')
# Extract booking from PDF
dreams2memories:extract_booking_from_pdf(pdf_path='/uploads/file.pdf')
# Run full itinerary pipeline
dreams2memories:run_itinerary_pipeline(booking_id='BK-001')

─────────────────────────────────────────────────────────────────
Thunderbird OS v1.5.5  ·  Claude AI Operating Manual  ·  Dreams2Memories Travel, LLC  ·  March 2026
For internal use only. All rates and operational data subject to change.
| Component | Description |
| --- | --- |
| Pipeline Core | Python orchestration — OCR → Groq LLM → Google Sheets → PDF render |
| PDF Extraction | OCR via pytesseract + Groq LLM for structured booking data parsing |
| Data Storage | Google Sheets (Booking Master + Daily Itinerary tabs) via service account |
| Template Engine | Jinja2 HTML templates rendered to PDF via WeasyPrint |
| D2M Drive Vault | TITAN_BOOKINGS_VAULT on Google Drive — canonical booking archive |
| MCP Server | D2M-COMMAND-HUB (25-tool suite) with Google Workspace integration |
| AI APIs | Groq (extraction), Anthropic Claude (generation), Gemini (comparison) |
| Persona | Role |
| --- | --- |
| TITAN | Primary orchestration persona — commands the pipeline |
| Echo | Data reflection and confirmation persona |
| Radar | World & ship intelligence sweep persona |
| Category | Tools Included |
| --- | --- |
| Google Drive | List, search, read, upload, download, move files, create folders |
| Google Sheets | Read/write Booking Master and Daily Itinerary tabs |
| Google Docs | Create and update itinerary documents |
| Gmail | Search confirmations, read threads, create drafts |
| Google Calendar | Create events, find free time, list and update events |
| Browser/Scraping | Stealth browser, cruise line voyage scraping, hotel search |
| Booking Pipeline | Extract PDFs, parse booking data, sync to Excel |
| Ship Intelligence | Compare ships, run intel sweeps, generate comparison reports |
| Connector | MCP URL |
| --- | --- |
| Canva | https://mcp.canva.com/mcp |
| Google Calendar | https://gcal.mcp.claude.com/mcp |
| Gmail | https://gmail.mcp.claude.com/mcp |
| Google Drive | https://drive.google.com/drive/folders/1MjjbqQVnzMYpHyAtNu-zZej-1mXhHkGk |
| File | Purpose |
| --- | --- |
| d2m_base.css.j2 | Brand CSS partial — navy/gold tokens, all component styles. Include via Jinja2 include tag. |
| hotel_guide.html.j2 | Hotel guide template — four overridable {% block %} sections. |
| d2m_hotel_guide_schema.py | Python dataclasses defining the full data contract. Includes render_to_pdf() helper. |
| Block Name | Contents |
| --- | --- |
| cover | Full cover page — client name, destination, meta strip, geometric arch motif |
| hotel_cards | Jinja2 loop over hotels list — one page per hotel with photos, price box, rates table, distances |
| comparison | Side-by-side comparison table + three recommendation cards |
| logistics | 2×2 transport card grid + info box + footnote |
| Variable | Value  ·  Usage |
| --- | --- |
| --navy | #0d1b2e  ·  Primary background, deep navy |
| --navy2 | #152540  ·  Secondary background |
| --navy3 | #1e3358  ·  Card/contact box background |
| --gold | #c9a84c  ·  Primary accent, borders, labels |
| --gold-light | #e8c97a  ·  Price amounts, highlights |
| --gold-pale | #f5e9c8  ·  Subtle gold tint |
| --muted | #8a9ab5  ·  Secondary text, metadata |
| --prestige-* | #7a5a9a / #4a2a6a  ·  Over-budget/5-star purple tier |
| Issue | Status / Resolution |
| --- | --- |
| MCP server connectivity failures | Migrate D2M-COMMAND-HUB to SSE/HTTP transport |
| Unicode encoding crash in PDF extraction | Add encoding='utf-8' + error handling to all file I/O |
| Booking IDs parsing as 'UNKNOWN' | Regex pattern needs update for new confirmation format |
| Zero ports extracted from itineraries | Port extraction logic needs refinement in Groq prompt |
| Tab | Contents |
| --- | --- |
| Booking Master | One row per booking — supplier, client, costs, dates, booking ID |
| Daily Itinerary | Port-by-port itinerary — date, port, arrival/departure, notes |
| File | Description |
| --- | --- |
| d2m_base.css.j2 | Full brand CSS partial — all navy/gold component styles |
| hotel_guide.html.j2 | Jinja2 hotel guide template with 4 overridable blocks |
| d2m_hotel_guide_schema.py | Python dataclasses + render_to_pdf() helper |
| Venice_Hotel_Guide_Jul2026.pdf | Original Venice hotel guide — 5 hotels, 265KB |
| Venice_Hotel_Guide_McLeod_Jul2026.pdf | McLeod revision — USD throughout, room options tables, 319KB |
| Path | Contents |
| --- | --- |
| ~/Thunderbird/ | Thunderbird OS root |
| ~/Thunderbird/docs/ | Manuals and documentation |
| ~/Thunderbird/screenshots/ | Browser automation screenshots |
| TITAN_BOOKINGS_VAULT (Drive) | Canonical booking archive on Google Drive |
| /mnt/skills/public/ | Claude skill files — docx, pdf, pptx, xlsx, frontend-design |
| /mnt/user-data/uploads/ | User-uploaded files (read-only) |
| /mnt/user-data/outputs/ | Final deliverable outputs |