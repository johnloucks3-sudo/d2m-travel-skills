# THUNDERBIRD OS — GOOSE-POWERED ARCHITECTURE
**Dreams2Memories Travel Intelligence Suite**  
**Version:** 4.0 (Python Migration from AppScript)  
**Target Platform:** Goose AI Agent Framework  
**Owner:** John Loucks | Love Group Travel

---

## EXECUTIVE OVERVIEW

You currently have **AppScript-based intelligence modules** running in Google Sheets that provide:
1. **Ship Intelligence** — AIS tracking, pricing alerts, availability monitoring
2. **Ship Comparison** — Head-to-head luxury cruise reports (Google Docs output)
3. **World Intel** — Destination news, travel advisories, competitive analysis

**The Migration Goal:** Convert these to **Python modules** running via **Goose** for:
- Superior scraping capabilities (Playwright vs. UrlFetchApp)
- Local execution control (no 6-minute AppScript timeout)
- Better AI model integration (Groq, Gemini, OpenAI without API quota battles)
- Professional PDF/DOCX generation (WeasyPrint, python-docx)
- Direct file system access for your `G:\TITAN_BOOKINGS_VAULT`

---

## MODULE BREAKDOWN

### **MODULE 1: SHIP INTEL (Playwright Web Scraper)**
**AppScript Source:** `dreams2memories_ship_intelligence.gs`  
**Purpose:** Monitor luxury cruise lines for:
- New ship launches
- Pricing changes (±5% thresholds)
- Suite availability (URGENT alerts at <3 remaining)
- Itinerary updates
- AIS position tracking (CruiseMapper, Cruising Earth)

**Target Sites:**
```
Regent Seven Seas: rssc.com
Silversea: silversea.com
Viking Ocean: vikingcruises.com
Seabourn: seabourn.com
Atlas Ocean Voyages: atlasoceanvoyages.com
Oceania: oceaniacruises.com
```

**Python Implementation:**
```python
# thunderbird_ship_intel.py
# Uses: Playwright, BeautifulSoup4, gspread
# Outputs: Google Sheets ("Ship Intel" tab)
# Schedule: Daily 7AM/5PM via cron or Goose task scheduler
```

**Key Features:**
- **Stealth Scraping:** Rotate user agents, randomize delays
- **Sheet Integration:** Direct writes to your Google Sheet (service account auth)
- **Alert System:** Email via Gmail API when pricing/availability triggers fire
- **AIS Tracking:** Parse CruiseMapper HTML for lat/long/ETA data

---

### **MODULE 2: WORLD INTEL (News & Advisories)**
**AppScript Source:** `Intel_Command` (Section 20)  
**Purpose:** Aggregate intelligence on:
- Destination news (port strikes, political events, natural disasters)
- US State Department travel advisories
- Weather forecasts (API integration)
- Competitive cruise line news

**Python Implementation:**
```python
# thunderbird_world_intel.py
# Uses: requests, feedparser (RSS), State Dept API
# Outputs: Google Sheets ("World Intel" tab) + email briefings
```

**Data Sources:**
```
State Dept Travel Advisories: travel.state.gov/content/travel/en/traveladvisories
Weather: OpenWeather API or NOAA
News: RSS feeds (Cruise Critic, Seatrade Cruise News)
Google News API: Custom search for port cities
```

---

### **MODULE 3: SHIP COMPARISON (Report Generator)**
**AppScript Source:** `D2M_Ship_Data` + `D2M_Ship_Compare`  
**Purpose:** Generate client-facing comparison reports:
- Silver Nova vs. Seven Seas Grandeur
- Regent Splendor vs. Silversea Cloud
- Viking Ocean vs. Oceania Riviera

**Python Implementation:**
```python
# thunderbird_ship_compare.py
# Uses: python-docx, Jinja2, weasyprint
# Outputs: DOCX + PDF reports (G:\TITAN_BOOKINGS_VAULT\Ship_Comparisons\)
```

**Ship Database:** JSON file with all specs from `SHIP_DATABASE` constant  
**Template:** Jinja2 template for professional DOCX layout  
**Delivery:** Auto-email to clients OR save to Drive folder

---

## GOOSE INTEGRATION STRATEGY

### **What is Goose?**
Goose is an AI agent framework that can:
- Run Python scripts on a schedule
- Integrate with MCP (Model Context Protocol) servers
- Maintain persistent memory between sessions
- Execute complex multi-step workflows

### **Goose Workflow Architecture**
```
┌─────────────────────────────────────────────────────┐
│              GOOSE ORCHESTRATOR                     │
│  (Central coordinator running on your machine)      │
└──────────┬─────────────┬─────────────┬──────────────┘
           │             │             │
    ┌──────▼──────┐ ┌───▼────────┐ ┌──▼──────────────┐
    │ SHIP INTEL  │ │ WORLD INTEL│ │ SHIP COMPARISON │
    │  (Scraper)  │ │  (News/API)│ │  (Report Gen)   │
    └──────┬──────┘ └───┬────────┘ └──┬──────────────┘
           │             │             │
    ┌──────▼─────────────▼─────────────▼──────────────┐
    │         GOOGLE SHEETS WAREHOUSE                 │
    │  (Tabs: Ship Intel, World Intel, Comparisons)   │
    └─────────────────────────────────────────────────┘
```

---

## FILE STRUCTURE

```
G:\TITAN_BOOKINGS_VAULT\
├── Thunderbird_Core\
│   ├── thunderbird_ship_intel.py        # Module 1
│   ├── thunderbird_world_intel.py       # Module 2
│   ├── thunderbird_ship_compare.py      # Module 3
│   ├── ship_database.json               # Vessel specs (from SHIP_DATABASE)
│   ├── config.yaml                      # API keys, Sheet IDs, email config
│   └── requirements.txt                 # Python dependencies
│
├── Templates\
│   ├── ship_comparison_template.docx    # Jinja2 DOCX template
│   ├── world_intel_email.html           # Daily briefing template
│   └── ship_intel_alert.html            # Pricing/availability alert template
│
├── Output\
│   ├── Ship_Comparisons\                # Generated PDFs/DOCX
│   ├── Intel_Reports\                   # Daily/weekly summaries
│   └── Logs\                            # Execution logs
│
└── credentials.json                     # Google service account (existing)
```

---

## DEPENDENCIES

```txt
# Core
python>=3.11
goose-ai                  # AI agent framework

# Web Scraping
playwright>=1.40.0
beautifulsoup4>=4.12.0
lxml>=4.9.0

# Google Integration
gspread>=5.12.0
google-auth>=2.25.0
google-api-python-client>=2.110.0

# AI Models
openai>=1.6.0             # For Gemini via OpenAI SDK
groq>=0.4.0               # For Llama 3.3

# Document Generation
python-docx>=1.1.0
jinja2>=3.1.2
weasyprint>=60.0          # HTML → PDF

# Data Processing
pandas>=2.1.0
requests>=2.31.0
feedparser>=6.0.10        # RSS parsing

# Utilities
pyyaml>=6.0.1             # Config management
schedule>=1.2.0           # Task scheduling fallback
```

---

## CONFIGURATION (config.yaml)

```yaml
# Dreams2Memories Travel Configuration
company:
  name: "Dreams2Memories Travel"
  website: "www.d2mtravel.luxury"
  email: "johnloucks3@gmail.com"
  phone: "(719) 291-0742"

google:
  sheet_id: "1GFjUe8RvP-GT4YHGn0DYv_BEAZGXlYfwEicFrm8ANuU"
  service_account: "G:/TITAN_BOOKINGS_VAULT/credentials.json"
  drive_folder_id: "1V_iUoy5oXs8RxY5S4-2QSHTXueGircnQ"  # Titan Art

api_keys:
  gemini: "***REMOVED-SECRET***"
  groq: "***REMOVED-SECRET***"
  pexels: "***REMOVED-SECRET***"
  google_search_api: "***REMOVED-SECRET***"
  google_cx_id: "c521728142cd34117"

ship_intel:
  tracking_url_cruisemapper: "https://www.cruisemapper.com"
  tracking_url_cruisingearth: "https://www.cruisingearth.com"
  alert_thresholds:
    urgent_suites_remaining: 3
    warning_price_increase_pct: 5
    critical_availability: 0
  priority_vessels:
    - "Silver Nova"
    - "Seven Seas Grandeur"
    - "World Navigator"
    - "World Traveller"
    - "World Voyager"

world_intel:
  state_dept_api: "https://travel.state.gov/content/travel/en/traveladvisories/traveladvisories.html"
  weather_api: "https://api.openweathermap.org/data/2.5/forecast"
  news_sources:
    - "https://www.cruisecritic.com/news/feed/"
    - "https://www.seatrade-cruise.com/rss.xml"

output:
  base_dir: "G:/TITAN_BOOKINGS_VAULT/Output"
  comparisons_dir: "Ship_Comparisons"
  intel_reports_dir: "Intel_Reports"
  logs_dir: "Logs"
```

---

## EXECUTION SCHEDULE (Goose Tasks)

```python
# goose_scheduler.py
# Run this file to set up Goose task automation

from goose import Goose
import schedule
import time

goose = Goose()

# Daily 7AM: Ship Intelligence Sweep
schedule.every().day.at("07:00").do(
    goose.run_task, "thunderbird_ship_intel.py"
)

# Daily 5PM: Ship Intelligence Sweep (Second pass)
schedule.every().day.at("17:00").do(
    goose.run_task, "thunderbird_ship_intel.py"
)

# Daily 6AM: World Intelligence Briefing
schedule.every().day.at("06:00").do(
    goose.run_task, "thunderbird_world_intel.py"
)

# On-demand: Ship Comparison (CLI trigger)
# goose run thunderbird_ship_compare.py --ship1="Silver Nova" --ship2="Seven Seas Grandeur"

while True:
    schedule.run_pending()
    time.sleep(60)
```

---

## MIGRATION PRIORITY

### **Phase 1: Foundation (Week 1)**
1. ✅ Set up Python environment + Goose installation
2. ✅ Convert `SHIP_DATABASE` to `ship_database.json`
3. ✅ Build `config.yaml` from existing credentials
4. ✅ Test Google Sheets write access (gspread)

### **Phase 2: Ship Intel Module (Week 2)**
1. Build Playwright scraper for Regent Seven Seas
2. Test pricing/availability extraction
3. Implement email alert system (Gmail API)
4. Expand to Silversea, Viking, Seabourn

### **Phase 3: World Intel Module (Week 3)**
1. Build State Dept API scraper
2. RSS feed parser for cruise news
3. Weather API integration
4. Daily briefing email generator

### **Phase 4: Ship Comparison Module (Week 4)**
1. Build Jinja2 DOCX template
2. PDF generation pipeline (WeasyPrint)
3. CLI interface for on-demand reports
4. Auto-archival to Google Drive

---

## QUESTIONS FOR NEXT STEPS

1. **Do you have Goose installed locally?** If not, I'll provide installation instructions.
2. **Preferred execution environment?** Windows (WSL2), native Linux, or Docker?
3. **Email delivery preference?** Gmail API (requires OAuth) or SMTP (simpler but less secure)?
4. **Priority order for modules?** Ship Intel → World Intel → Comparison? Or different order?
5. **Do you want a unified CLI dashboard** (like `thunderbird --status`) or separate scripts?

---

**Next Action:** Let me know your answers, and I'll start building the Python modules with full code examples, ready to run on Goose.
