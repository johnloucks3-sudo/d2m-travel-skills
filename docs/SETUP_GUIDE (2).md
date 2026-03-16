# THUNDERBIRD OS v4.0 — COMPLETE SETUP GUIDE
**Dreams2Memories Travel Intelligence Suite**

---

## 🚀 WHAT YOU JUST RECEIVED

### **Four Production-Ready Python Modules:**

1. **thunderbird_ship_intel.py** — Web scraping for luxury cruise lines (Playwright Stealth)
2. **thunderbird_world_intel.py** — Travel advisories, weather, news aggregation
3. **thunderbird_ship_compare.py** — Professional DOCX/PDF comparison reports
4. **thunderbird_weekly_report.py** — Comprehensive client intelligence reports
5. **thunderbird.py** — Unified CLI wrapper (single command for everything)

### **Integration:**
- All modules work **standalone** OR integrate with your `travel_mcp_server.py`
- Direct Google Sheets integration (your existing credentials)
- Uses same **Playwright Stealth** framework you already have working

---

## 📦 INSTALLATION

### **Step 1: Install Python Dependencies**

```bash
pip install playwright playwright-stealth beautifulsoup4 lxml feedparser \
            python-docx jinja2 weasyprint gspread google-auth \
            google-api-python-client pydantic requests
```

### **Step 2: Install Playwright Browsers**

```bash
playwright install chromium
```

### **Step 3: Set Up Directory Structure**

```bash
# Create output directories
mkdir -p ~/Documents/Luxury_Itineraries/Ship_Comparisons
mkdir -p ~/Documents/Luxury_Itineraries/Client_Reports

# Place all Thunderbird modules in the same directory
# (e.g., ~/Thunderbird/ or your preferred location)
```

### **Step 4: Configure Google Sheets**

Your Google Sheet (`1GFjUe8RvP-GT4YHGn0DYv_BEAZGXlYfwEicFrm8ANuU`) needs these tabs:

**Required Tabs:**
1. **Ship Intelligence** — Columns: `Cruise Line | Ship | Voyage | Departure | Days | Price | Availability | Scraped At`
2. **Pricing Tracker** — Columns: `Cruise Line | Ship | Voyage ID | Old Price | New Price | Change % | Priority | Detected At`
3. **Availability Alerts** — Columns: `Cruise Line | Ship | Voyage ID | Suite Category | Remaining | Priority | Detected At`
4. **Travel Advisories** — Columns: `Country | Level | Advisory | Last Updated | Scraped At`
5. **Port Weather** — Columns: `Port | Date | High | Low | Conditions | Wind | Precipitation %`
6. **World Intelligence** — Columns: `Title | Source | URL | Published | Relevance | Category | Scraped At`

**Create these tabs manually** or use Google Sheets API to auto-create them.

### **Step 5: Get OpenWeather API Key (Optional)**

For port weather forecasts:
1. Go to https://openweathermap.org/api
2. Sign up for free account
3. Get API key
4. Update `WorldIntelConfig.WEATHER_API_KEY` in `thunderbird_world_intel.py`

---

## 🎯 USAGE EXAMPLES

### **Option 1: Standalone Modules (Testing)**

```bash
# Test Ship Intelligence
python thunderbird_ship_intel.py

# Test World Intelligence
python thunderbird_world_intel.py

# Test Ship Comparison
python thunderbird_ship_compare.py

# Test Weekly Report (Interactive)
python thunderbird_weekly_report.py --interactive
```

### **Option 2: Unified CLI (Recommended)**

```bash
# Show system status
python thunderbird.py --status

# Run ship intelligence sweep
python thunderbird.py --sweep-ship-intel

# Run world intelligence sweep
python thunderbird.py --sweep-world-intel

# Run full sweep (all intelligence)
python thunderbird.py --full-sweep

# Generate ship comparison
python thunderbird.py --compare "Silver Nova" "Seven Seas Grandeur"
python thunderbird.py --compare "Silver Nova" "Seven Seas Grandeur" --format pdf

# List available ships
python thunderbird.py --list-ships

# Generate weekly client report (interactive)
python thunderbird.py --weekly-report --interactive

# Generate weekly report (non-interactive)
python thunderbird.py --weekly-report --client "John Smith" --ships "Silver Nova,Seven Seas Grandeur"
```

### **Option 3: Make CLI System-Wide (Optional)**

```bash
# On Linux/Mac:
sudo cp thunderbird.py /usr/local/bin/thunderbird
sudo chmod +x /usr/local/bin/thunderbird

# Then use anywhere:
thunderbird --status
thunderbird --sweep-ship-intel
```

---

## 🔗 MCP INTEGRATION (For Goose/Claude)

### **Add to Your `travel_mcp_server.py`:**

At the bottom of `travel_mcp_server.py`, **before** `if __name__ == "__main__"`:

```python
# Import Thunderbird modules
from thunderbird_ship_intel import register_ship_intel_tools
from thunderbird_world_intel import register_world_intel_tools
from thunderbird_ship_compare import register_comparison_tools

# Register tools with MCP server
register_ship_intel_tools(mcp)
register_world_intel_tools(mcp)
register_comparison_tools(mcp)
```

This adds **10 new tools** to your MCP server:

**Ship Intelligence:**
- `run_ship_intelligence_sweep`
- `scrape_specific_cruise_line`

**World Intelligence:**
- `run_world_intelligence_sweep`
- `get_travel_advisories`
- `get_port_weather_forecast`
- `get_cruise_industry_news`

**Ship Comparison:**
- `generate_ship_comparison_docx`
- `generate_ship_comparison_pdf`
- `list_available_ships`

**Weekly Reports:**
- (Use CLI interface for now, MCP tool coming soon)

---

## 📅 AUTOMATION / SCHEDULING

### **Option 1: Cron (Linux/Mac)**

```bash
# Edit crontab
crontab -e

# Add these lines:
# Ship Intel: Daily at 7 AM and 5 PM
0 7 * * * /usr/bin/python3 /path/to/thunderbird.py --sweep-ship-intel >> /path/to/logs/ship_intel.log 2>&1
0 17 * * * /usr/bin/python3 /path/to/thunderbird.py --sweep-ship-intel >> /path/to/logs/ship_intel.log 2>&1

# World Intel: Daily at 6 AM
0 6 * * * /usr/bin/python3 /path/to/thunderbird.py --sweep-world-intel >> /path/to/logs/world_intel.log 2>&1

# Full Sweep: Mondays at 8 AM
0 8 * * 1 /usr/bin/python3 /path/to/thunderbird.py --full-sweep >> /path/to/logs/full_sweep.log 2>&1
```

### **Option 2: Windows Task Scheduler**

1. Open Task Scheduler
2. Create Basic Task
3. Name: "Thunderbird Ship Intel"
4. Trigger: Daily at 7:00 AM
5. Action: Start a program
6. Program: `python.exe`
7. Arguments: `C:\path\to\thunderbird.py --sweep-ship-intel`

### **Option 3: Goose Task Scheduler** (If using Goose framework)

```python
# goose_scheduler.py
from goose import Goose
import schedule
import time

goose = Goose()

schedule.every().day.at("07:00").do(
    lambda: goose.run("python thunderbird.py --sweep-ship-intel")
)

schedule.every().day.at("17:00").do(
    lambda: goose.run("python thunderbird.py --sweep-ship-intel")
)

schedule.every().day.at("06:00").do(
    lambda: goose.run("python thunderbird.py --sweep-world-intel")
)

while True:
    schedule.run_pending()
    time.sleep(60)
```

---

## 🛠️ CUSTOMIZATION

### **Add More Ships to Database**

Edit `thunderbird_ship_compare.py`, add to `SHIP_DATABASE`:

```python
"Your Ship Name": {
    "line": "Cruise Line",
    "launched": 2024,
    "specs": {
        "gross_tonnage": 50000,
        "max_guests": 700,
        "suites": 350,
        "avg_suite_size": 30,
        "all_suites_balcony": True
    },
    "ratios": {
        "space_to_guest": 11.5,
        "crew_to_guest": "1:1",
        "crew_count": 700
    },
    # ... rest of data
}
```

### **Add More Cruise Lines to Scraping**

Edit `thunderbird_ship_intel.py`, add scraper function:

```python
async def scrape_YOUR_CRUISE_LINE_voyages() -> List[VoyageData]:
    """Scrape YOUR CRUISE LINE"""
    url = "https://www.yourline.com/find-cruise"
    # Use Playwright Stealth pattern from existing scrapers
    # ...
```

Then call it in `run_ship_intelligence_sweep()`.

### **Add More News Sources**

Edit `WorldIntelConfig.NEWS_FEEDS` in `thunderbird_world_intel.py`:

```python
NEWS_FEEDS = {
    "Your Source": "https://example.com/rss.xml",
    # ... existing feeds
}
```

---

## 📊 WEEKLY REPORT FEATURES

The weekly report generator (`thunderbird_weekly_report.py`) includes:

✅ **Executive Summary** — High-level overview of alerts and opportunities  
✅ **Pricing Intelligence** — Table of price changes with +/- percentages  
✅ **Suite Availability Alerts** — URGENT warnings for limited suites  
✅ **Featured Voyages** — Top 5 matching client preferences  
✅ **Travel Advisories** — State Dept warnings for destination countries  
✅ **Port Weather Outlook** — 7-day forecasts for key ports  
✅ **Industry News Highlights** — Categorized as alerts or opportunities  
✅ **Professional Branding** — Dreams2Memories colors, logo placeholders  

### **Sample CLI Workflow:**

```bash
# Interactive mode (easiest)
python thunderbird.py --weekly-report --interactive

# You'll be prompted for:
# - Client name
# - Target ships (or use defaults)
# - Report options (pricing, weather, etc.)
# - Output format (PDF/HTML/Both)

# Non-interactive mode
python thunderbird.py --weekly-report \
  --client "Margaret Thompson" \
  --ships "Silver Nova,Seven Seas Grandeur"
```

Output files:
- `~/Documents/Luxury_Itineraries/Client_Reports/Weekly_Report_Margaret_Thompson_20260303.pdf`
- `~/Documents/Luxury_Itineraries/Client_Reports/Weekly_Report_Margaret_Thompson_20260303.html`

---

## 🐛 TROUBLESHOOTING

### **Issue: "Module not found" errors**

**Solution:**
```bash
# Make sure all modules are in the same directory
ls -la *.py

# Should show:
# thunderbird.py
# thunderbird_ship_intel.py
# thunderbird_world_intel.py
# thunderbird_ship_compare.py
# thunderbird_weekly_report.py
```

### **Issue: Google Sheets authentication fails**

**Solution:**
- Verify `credentials.json` path in each module
- Check service account has access to your Sheet
- Test with: `python -c "import gspread; print('OK')"`

### **Issue: Playwright scraping fails**

**Solution:**
```bash
# Reinstall Playwright browsers
playwright install --force chromium

# Test Playwright
python -c "from playwright.sync_api import sync_playwright; print('OK')"
```

### **Issue: WeasyPrint PDF generation fails (Linux)**

**Solution:**
```bash
# Install system dependencies
sudo apt-get install python3-cffi python3-brotli libpango-1.0-0 \
                     libpangoft2-1.0-0 libharfbuzz-dev
```

### **Issue: Ship scraper returns empty results**

**Cause:** Cruise line website HTML structure changed  
**Solution:**
1. Visit the site in Chrome
2. Inspect element on voyage cards
3. Update CSS selectors in scraper function
4. Test with: `python thunderbird.py --sweep-ship-intel`

---

## 📈 NEXT STEPS

1. **Test each module standalone** to verify functionality
2. **Set up Google Sheets tabs** (manual or via API)
3. **Get OpenWeather API key** for weather forecasts
4. **Customize ship database** with your priority vessels
5. **Set up automation** (cron/Task Scheduler)
6. **Generate your first weekly report** for a test client
7. **Refine scrapers** with actual cruise line HTML selectors

---

## 💡 TIPS & BEST PRACTICES

✅ **Run sweeps during off-hours** (2-6 AM) to avoid rate limiting  
✅ **Keep scrapers updated** — cruise sites change HTML frequently  
✅ **Monitor Google Sheets quota** — free tier = 100 requests/100 seconds  
✅ **Use headless mode** for Playwright (already configured)  
✅ **Archive old data** from Sheets monthly to keep it fast  
✅ **Test reports** with fake client data before sending real ones  

---

## 🆘 SUPPORT

**Issues?** Contact John Loucks:
- Email: johnloucks3@gmail.com
- Phone: (719) 291-0742
- Website: www.d2mtravel.luxury

**System Built By:** Claude (Anthropic) + John Loucks  
**Version:** 4.0.0 (Goose-Powered Intelligence Suite)  
**Last Updated:** March 2026
