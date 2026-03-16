"""
Dreams2Memories Weekly Client Intelligence Report Generator
============================================================

Generates comprehensive luxury cruise intelligence reports for clients:
- Targeted ship intelligence (specific ships they're interested in)
- Voyage availability and pricing
- Suite availability alerts
- Special offers and promotions
- Travel advisories for destinations
- Port weather forecasts
- Industry news highlights

Output formats: PDF + Email-ready HTML
CLI interface for easy report generation
"""

import json
import logging
import asyncio
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field
from jinja2 import Template
import weasyprint
import gspread
from google.oauth2 import service_account

# Import our intelligence modules
import sys
sys.path.append(str(Path(__file__).parent))

# ============================================================================
# CONFIGURATION
# ============================================================================

class ReportConfig:
    """Configuration for client report generation"""
    
    # Google Sheets
    SHEET_ID = "1GFjUe8RvP-GT4YHGn0DYv_BEAZGXlYfwEicFrm8ANuU"
    SERVICE_ACCOUNT_FILE = Path.home() / "Thunderbird" / "credentials.json"
    
    # Output
    OUTPUT_DIR = Path.home() / "Documents" / "Luxury_Itineraries" / "Client_Reports"
    
    # Branding
    COMPANY_NAME = "Dreams2Memories Travel"
    COMPANY_TAGLINE = "Curating Unforgettable Journeys"
    AGENT_NAME = "John Loucks"
    AGENT_TITLE = "Luxury Travel Tech Architect"
    AGENT_EMAIL = "johnloucks3@gmail.com"
    AGENT_PHONE = "(719) 291-0742"
    WEBSITE = "www.d2mtravel.luxury"
    
    # Report Defaults
    DEFAULT_SHIPS = ["Silver Nova", "Seven Seas Grandeur", "World Navigator"]
    DEFAULT_DESTINATIONS = ["Mediterranean", "Caribbean", "Arctic", "Antarctic"]

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# ============================================================================
# DATA MODELS
# ============================================================================

class ClientReportRequest(BaseModel):
    """Request model for generating client reports"""
    
    client_name: str = Field(..., description="Client name for personalization")
    client_email: Optional[str] = Field(None, description="Client email (for delivery)")
    
    # Intelligence filters
    target_ships: List[str] = Field(
        default_factory=lambda: ReportConfig.DEFAULT_SHIPS,
        description="Ships to monitor"
    )
    target_destinations: List[str] = Field(
        default_factory=lambda: ReportConfig.DEFAULT_DESTINATIONS,
        description="Regions of interest"
    )
    departure_date_range: Optional[Dict[str, str]] = Field(
        None,
        description="Date range: {'start': 'YYYY-MM-DD', 'end': 'YYYY-MM-DD'}"
    )
    
    # Report options
    include_pricing: bool = Field(True, description="Include pricing intelligence")
    include_availability: bool = Field(True, description="Include suite availability")
    include_advisories: bool = Field(True, description="Include travel advisories")
    include_weather: bool = Field(True, description="Include weather forecasts")
    include_news: bool = Field(True, description="Include industry news")
    include_tech_intel: bool = Field(True, description="Include Claude Code & technology intelligence")
    include_offers: bool = Field(True, description="Include special offers")
    
    output_format: str = Field("pdf", description="Output: 'pdf', 'html', or 'both'")

# ============================================================================
# DATA EXTRACTION FROM GOOGLE SHEETS
# ============================================================================

def get_sheets_client():
    """Initialize Google Sheets client"""
    creds = service_account.Credentials.from_service_account_file(
        str(ReportConfig.SERVICE_ACCOUNT_FILE),
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    return gspread.authorize(creds)

def extract_ship_intelligence(target_ships: List[str]) -> Dict[str, Any]:
    """Extract latest ship intelligence from Google Sheets"""
    try:
        gc = get_sheets_client()
        sheet = gc.open_by_key(ReportConfig.SHEET_ID)
        
        # Get Ship Intelligence data
        ws = sheet.worksheet("Ship Intelligence")
        records = ws.get_all_records()
        
        # Filter for target ships (last 7 days)
        seven_days_ago = datetime.now() - timedelta(days=7)
        filtered = []
        
        for record in records:
            ship_name = record.get('Ship', '')
            if any(target in ship_name for target in target_ships):
                # Check if recent
                scraped_at = record.get('Scraped At', '')
                try:
                    scraped_date = datetime.fromisoformat(scraped_at.split('T')[0])
                    if scraped_date >= seven_days_ago:
                        filtered.append(record)
                except:
                    pass
        
        return {
            "total_voyages": len(filtered),
            "ships_monitored": target_ships,
            "voyages": filtered[:10]  # Top 10 most recent
        }
    except Exception as e:
        logger.error(f"Error extracting ship intelligence: {str(e)}")
        return {"total_voyages": 0, "ships_monitored": target_ships, "voyages": []}

def extract_pricing_alerts(target_ships: List[str]) -> List[Dict]:
    """Extract pricing alerts from Google Sheets"""
    try:
        gc = get_sheets_client()
        sheet = gc.open_by_key(ReportConfig.SHEET_ID)
        
        ws = sheet.worksheet("Pricing Tracker")
        records = ws.get_all_records()
        
        # Filter for target ships (last 7 days, HIGH or CRITICAL priority)
        alerts = []
        for record in records:
            ship = record.get('Ship', '')
            priority = record.get('Priority', '')
            
            if any(target in ship for target in target_ships):
                if priority in ['HIGH', 'CRITICAL']:
                    alerts.append({
                        "ship": ship,
                        "voyage_id": record.get('Voyage ID', ''),
                        "old_price": record.get('Old Price', 0),
                        "new_price": record.get('New Price', 0),
                        "change_pct": record.get('Change %', 0),
                        "priority": priority
                    })
        
        return alerts[:5]  # Top 5 alerts
    except Exception as e:
        logger.error(f"Error extracting pricing alerts: {str(e)}")
        return []

def extract_availability_alerts(target_ships: List[str]) -> List[Dict]:
    """Extract suite availability alerts"""
    try:
        gc = get_sheets_client()
        sheet = gc.open_by_key(ReportConfig.SHEET_ID)
        
        ws = sheet.worksheet("Availability Alerts")
        records = ws.get_all_records()
        
        # Filter for URGENT alerts on target ships
        alerts = []
        for record in records:
            ship = record.get('Ship', '')
            priority = record.get('Priority', '')
            
            if any(target in ship for target in target_ships):
                if priority == 'URGENT':
                    alerts.append({
                        "ship": ship,
                        "voyage_id": record.get('Voyage ID', ''),
                        "suite_category": record.get('Suite Category', ''),
                        "suites_remaining": record.get('Remaining', 0),
                        "priority": priority
                    })
        
        return alerts[:5]
    except Exception as e:
        logger.error(f"Error extracting availability alerts: {str(e)}")
        return []

def extract_travel_advisories(destinations: List[str]) -> List[Dict]:
    """Extract relevant travel advisories"""
    try:
        gc = get_sheets_client()
        sheet = gc.open_by_key(ReportConfig.SHEET_ID)
        
        ws = sheet.worksheet("Travel Advisories")
        records = ws.get_all_records()
        
        # Filter for Level 2+ advisories in target regions
        advisories = []
        for record in records:
            country = record.get('Country', '')
            level = record.get('Level', 1)
            
            # Simple keyword matching (expand with better logic)
            if level >= 2:
                advisories.append({
                    "country": country,
                    "level": level,
                    "advisory": record.get('Advisory', '')
                })
        
        return advisories[:10]
    except Exception as e:
        logger.error(f"Error extracting advisories: {str(e)}")
        return []

def extract_port_weather(destinations: List[str]) -> List[Dict]:
    """Extract port weather forecasts"""
    try:
        gc = get_sheets_client()
        sheet = gc.open_by_key(ReportConfig.SHEET_ID)
        
        ws = sheet.worksheet("Port Weather")
        records = ws.get_all_records()
        
        # Get weather for next 7 days
        forecasts = []
        today = datetime.now().date()
        
        for record in records:
            port = record.get('Port', '')
            forecast_date = record.get('Date', '')
            
            try:
                fdate = datetime.strptime(forecast_date, '%Y-%m-%d').date()
                if today <= fdate <= today + timedelta(days=7):
                    forecasts.append({
                        "port": port,
                        "date": forecast_date,
                        "temp_high": record.get('High', 0),
                        "temp_low": record.get('Low', 0),
                        "conditions": record.get('Conditions', ''),
                        "precip_chance": record.get('Precipitation %', 0)
                    })
            except:
                pass
        
        return forecasts
    except Exception as e:
        logger.error(f"Error extracting weather: {str(e)}")
        return []

def extract_cruise_news() -> List[Dict]:
    """Extract high-relevance cruise news"""
    try:
        gc = get_sheets_client()
        sheet = gc.open_by_key(ReportConfig.SHEET_ID)

        ws = sheet.worksheet("World Intelligence")
        records = ws.get_all_records()

        # Get news from last 7 days, relevance >= 3
        news = []
        for record in records:
            relevance = record.get('Relevance', 0)
            if relevance >= 3:
                news.append({
                    "title": record.get('Title', ''),
                    "source": record.get('Source', ''),
                    "url": record.get('URL', ''),
                    "category": record.get('Category', ''),
                    "relevance": relevance
                })

        return news[:10]
    except Exception as e:
        logger.error(f"Error extracting news: {str(e)}")
        return []


def extract_tech_intel() -> List[Dict]:
    """Extract Claude Code & technology intelligence from Tech News Monitor tab"""
    try:
        gc = get_sheets_client()
        sheet = gc.open_by_key(ReportConfig.SHEET_ID)

        ws = sheet.worksheet("Tech News Monitor")
        records = ws.get_all_records()

        # Filter for CLAUDE_CODE_INTEL, AI_MODELS, MCP_AGENTS — last 7 days, relevance >= 5
        tech_categories = {"CLAUDE_CODE_INTEL", "AI_MODELS", "MCP_AGENTS"}
        seven_days_ago = datetime.now() - timedelta(days=7)
        items = []

        for record in records:
            category = record.get('Category', '')
            relevance = record.get('Relevance', 0)
            if category in tech_categories and relevance >= 5:
                try:
                    record_date = record.get('Date', '')
                    # Handle various date formats
                    if 'T' in str(record_date):
                        record_date = str(record_date).split('T')[0]
                    rdate = datetime.strptime(str(record_date)[:10], '%Y-%m-%d')
                    if rdate >= seven_days_ago:
                        items.append({
                            "title": record.get('Title', ''),
                            "source": record.get('Source', ''),
                            "url": record.get('URL', ''),
                            "category": category,
                            "relevance": relevance,
                            "keywords": record.get('Keywords', ''),
                            "priority": record.get('Priority', 'MEDIUM'),
                        })
                except (ValueError, TypeError):
                    pass

        # Sort by relevance descending
        items.sort(key=lambda x: x.get('relevance', 0), reverse=True)
        return items[:10]
    except Exception as e:
        logger.error(f"Error extracting tech intel: {str(e)}")
        return []

# ============================================================================
# HTML REPORT GENERATION
# ============================================================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        @page { size: A4; margin: 2cm; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            color: #333;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
        }
        .header {
            text-align: center;
            border-bottom: 3px solid #1f4788;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }
        .header h1 {
            color: #1f4788;
            margin: 0;
            font-size: 32pt;
        }
        .header .tagline {
            color: #666;
            font-style: italic;
            font-size: 14pt;
        }
        .header .date {
            color: #999;
            font-size: 11pt;
            margin-top: 10px;
        }
        
        .client-name {
            font-size: 18pt;
            color: #1f4788;
            margin-bottom: 20px;
        }
        
        h2 {
            color: #1f4788;
            border-bottom: 2px solid #355c9d;
            padding-bottom: 8px;
            margin-top: 35px;
            font-size: 20pt;
        }
        
        h3 {
            color: #355c9d;
            font-size: 16pt;
            margin-top: 25px;
        }
        
        .alert-box {
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin: 20px 0;
        }
        
        .alert-box.urgent {
            background: #f8d7da;
            border-left-color: #dc3545;
        }
        
        .alert-box.opportunity {
            background: #d1ecf1;
            border-left-color: #17a2b8;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 11pt;
        }
        
        th {
            background: #1f4788;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: bold;
        }
        
        td {
            border: 1px solid #ddd;
            padding: 10px;
        }
        
        tr:nth-child(even) {
            background: #f9f9f9;
        }
        
        .price-increase {
            color: #dc3545;
            font-weight: bold;
        }
        
        .price-decrease {
            color: #28a745;
            font-weight: bold;
        }
        
        .urgent-tag {
            background: #dc3545;
            color: white;
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 9pt;
            font-weight: bold;
        }
        
        .news-item {
            border-left: 3px solid #355c9d;
            padding-left: 15px;
            margin: 15px 0;
        }
        
        .news-item .title {
            font-weight: bold;
            color: #1f4788;
        }
        
        .news-item .source {
            color: #666;
            font-size: 10pt;
        }
        
        .footer {
            margin-top: 50px;
            padding-top: 20px;
            border-top: 2px solid #ddd;
            text-align: center;
            font-size: 10pt;
            color: #666;
        }
        
        .contact-info {
            margin-top: 15px;
            font-style: italic;
        }
        
        ul {
            list-style-type: none;
            padding-left: 0;
        }
        
        li:before {
            content: "✓ ";
            color: #1f4788;
            font-weight: bold;
            margin-right: 8px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{ company_name }}</h1>
        <div class="tagline">{{ tagline }}</div>
        <div class="date">Weekly Intelligence Report | {{ report_date }}</div>
    </div>
    
    <div class="client-name">Prepared for: {{ client_name }}</div>
    
    <!-- EXECUTIVE SUMMARY -->
    <h2>📊 Executive Summary</h2>
    <p>This week's intelligence covers <strong>{{ ship_count }}</strong> luxury vessels across your target portfolio. 
    We've identified <strong>{{ pricing_alert_count }}</strong> pricing movements and 
    <strong>{{ availability_alert_count }}</strong> suite availability alerts requiring immediate attention.</p>
    
    {% if urgent_alerts %}
    <div class="alert-box urgent">
        <strong>⚠️ URGENT ACTIONS REQUIRED:</strong>
        <ul>
        {% for alert in urgent_alerts %}
            <li>{{ alert }}</li>
        {% endfor %}
        </ul>
    </div>
    {% endif %}
    
    <!-- PRICING INTELLIGENCE -->
    {% if pricing_alerts %}
    <h2>💰 Pricing Intelligence</h2>
    <p>Notable pricing movements detected in the last 7 days:</p>
    <table>
        <tr>
            <th>Ship</th>
            <th>Voyage</th>
            <th>Previous</th>
            <th>Current</th>
            <th>Change</th>
            <th>Priority</th>
        </tr>
        {% for alert in pricing_alerts %}
        <tr>
            <td>{{ alert.ship }}</td>
            <td>{{ alert.voyage_id }}</td>
            <td>${{ "{:,.0f}".format(alert.old_price) }}</td>
            <td>${{ "{:,.0f}".format(alert.new_price) }}</td>
            <td class="{% if alert.change_pct > 0 %}price-increase{% else %}price-decrease{% endif %}">
                {{ "{:+.1f}".format(alert.change_pct) }}%
            </td>
            <td>
                {% if alert.priority == 'CRITICAL' %}
                <span class="urgent-tag">CRITICAL</span>
                {% else %}
                {{ alert.priority }}
                {% endif %}
            </td>
        </tr>
        {% endfor %}
    </table>
    {% endif %}
    
    <!-- SUITE AVAILABILITY -->
    {% if availability_alerts %}
    <h2>🛏️ Suite Availability Alerts</h2>
    <div class="alert-box urgent">
        <strong>Limited availability detected on premium suites:</strong>
    </div>
    <table>
        <tr>
            <th>Ship</th>
            <th>Voyage</th>
            <th>Suite Category</th>
            <th>Remaining</th>
        </tr>
        {% for alert in availability_alerts %}
        <tr>
            <td>{{ alert.ship }}</td>
            <td>{{ alert.voyage_id }}</td>
            <td>{{ alert.suite_category }}</td>
            <td><strong>{{ alert.suites_remaining }}</strong> <span class="urgent-tag">URGENT</span></td>
        </tr>
        {% endfor %}
    </table>
    {% endif %}
    
    <!-- VOYAGE OPPORTUNITIES -->
    {% if voyages %}
    <h2>⛴️ Featured Voyages</h2>
    <p>Top luxury cruise opportunities matching your preferences:</p>
    {% for voyage in voyages[:5] %}
    <div class="news-item">
        <div class="title">{{ voyage.get('Voyage', 'N/A') }}</div>
        <div class="source">
            {{ voyage.get('Ship', 'N/A') }} | 
            {{ voyage.get('Cruise Line', 'N/A') }} | 
            Departs: {{ voyage.get('Departure', 'N/A') }} | 
            Duration: {{ voyage.get('Days', 'N/A') }} days
            {% if voyage.get('Price') %}
            | From ${{ "{:,.0f}".format(voyage.get('Price', 0)) }}
            {% endif %}
        </div>
    </div>
    {% endfor %}
    {% endif %}
    
    <!-- TRAVEL ADVISORIES -->
    {% if advisories %}
    <h2>🌍 Travel Advisories</h2>
    <p>Current State Department advisories for regions on your watch list:</p>
    {% for advisory in advisories %}
    <div class="news-item">
        <div class="title">{{ advisory.country }} - Level {{ advisory.level }}</div>
        <div class="source">{{ advisory.advisory[:200] }}...</div>
    </div>
    {% endfor %}
    {% endif %}
    
    <!-- PORT WEATHER -->
    {% if weather %}
    <h2>🌤️ Port Weather Outlook (Next 7 Days)</h2>
    <table>
        <tr>
            <th>Port</th>
            <th>Date</th>
            <th>High/Low</th>
            <th>Conditions</th>
            <th>Rain %</th>
        </tr>
        {% for forecast in weather[:10] %}
        <tr>
            <td>{{ forecast.port }}</td>
            <td>{{ forecast.date }}</td>
            <td>{{ forecast.temp_high }}°C / {{ forecast.temp_low }}°C</td>
            <td>{{ forecast.conditions }}</td>
            <td>{{ forecast.precip_chance }}%</td>
        </tr>
        {% endfor %}
    </table>
    {% endif %}
    
    <!-- INDUSTRY NEWS -->
    {% if news %}
    <h2>📰 Industry Highlights</h2>
    {% for item in news %}
    <div class="news-item">
        <div class="title">{{ item.title }}</div>
        <div class="source">{{ item.source }} |
            {% if item.category == 'alert' %}🚨 Alert
            {% elif item.category == 'opportunity' %}💡 Opportunity
            {% else %}📌 News
            {% endif %}
        </div>
    </div>
    {% endfor %}
    {% endif %}

    <!-- TECH & CLAUDE CODE INTEL -->
    {% if tech_intel %}
    <h2>⚡ Technology & Claude Code Intel</h2>
    <p>AI platform updates, Claude Code tooling, and MCP ecosystem developments:</p>
    {% for item in tech_intel %}
    <div class="news-item">
        <div class="title">
            {% if item.url %}<a href="{{ item.url }}" style="color: #1f4788; text-decoration: none;">{{ item.title }}</a>
            {% else %}{{ item.title }}{% endif %}
        </div>
        <div class="source">
            {{ item.source }} |
            {% if item.category == 'CLAUDE_CODE_INTEL' %}🔧 Claude Code
            {% elif item.category == 'AI_MODELS' %}🤖 AI Models
            {% elif item.category == 'MCP_AGENTS' %}🔗 MCP/Agents
            {% else %}📌 Tech
            {% endif %}
            | Relevance: {{ item.relevance }}/10
            {% if item.priority == 'CRITICAL' %} | <span class="urgent-tag">CRITICAL</span>{% endif %}
        </div>
    </div>
    {% endfor %}
    {% endif %}

    <!-- FOOTER -->
    <div class="footer">
        <strong>{{ company_name }}</strong><br>
        {{ agent_name }}, {{ agent_title }}<br>
        <div class="contact-info">
            {{ agent_email }} | {{ agent_phone }}<br>
            {{ website }}
        </div>
        <p style="margin-top: 20px; font-size: 9pt;">
            This report is generated weekly and contains proprietary market intelligence.
            For personalized recommendations or to book any of the featured voyages,
            please contact us directly.
        </p>
    </div>
</body>
</html>
"""

def generate_html_report(request: ClientReportRequest) -> str:
    """Generate HTML report from gathered intelligence"""
    
    logger.info(f"📄 Generating report for {request.client_name}...")
    
    # Extract data from Google Sheets
    ship_intel = extract_ship_intelligence(request.target_ships)
    pricing_alerts = extract_pricing_alerts(request.target_ships) if request.include_pricing else []
    availability_alerts = extract_availability_alerts(request.target_ships) if request.include_availability else []
    advisories = extract_travel_advisories(request.target_destinations) if request.include_advisories else []
    weather = extract_port_weather(request.target_destinations) if request.include_weather else []
    news = extract_cruise_news() if request.include_news else []
    tech_intel = extract_tech_intel() if request.include_tech_intel else []
    
    # Build urgent alerts summary
    urgent_alerts = []
    if availability_alerts:
        urgent_alerts.append(f"Contact clients immediately: {len(availability_alerts)} premium suites selling out")
    if len([a for a in pricing_alerts if a['priority'] == 'CRITICAL']) > 0:
        urgent_alerts.append(f"Major pricing shifts detected on {len([a for a in pricing_alerts if a['priority'] == 'CRITICAL'])} voyages")
    
    # Render template
    template = Template(HTML_TEMPLATE)
    html = template.render(
        company_name=ReportConfig.COMPANY_NAME,
        tagline=ReportConfig.COMPANY_TAGLINE,
        report_date=datetime.now().strftime("%B %d, %Y"),
        client_name=request.client_name,
        agent_name=ReportConfig.AGENT_NAME,
        agent_title=ReportConfig.AGENT_TITLE,
        agent_email=ReportConfig.AGENT_EMAIL,
        agent_phone=ReportConfig.AGENT_PHONE,
        website=ReportConfig.WEBSITE,
        
        ship_count=len(request.target_ships),
        pricing_alert_count=len(pricing_alerts),
        availability_alert_count=len(availability_alerts),
        urgent_alerts=urgent_alerts,
        
        voyages=ship_intel['voyages'],
        pricing_alerts=pricing_alerts,
        availability_alerts=availability_alerts,
        advisories=advisories,
        weather=weather,
        news=news,
        tech_intel=tech_intel
    )
    
    return html

def generate_pdf_report(html_content: str, output_path: Path) -> bool:
    """Convert HTML to PDF using WeasyPrint"""
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        weasyprint.HTML(string=html_content).write_pdf(output_path)
        logger.info(f"✅ PDF saved: {output_path}")
        return True
    except Exception as e:
        logger.error(f"❌ PDF generation failed: {str(e)}")
        return False

# ============================================================================
# CLI INTERFACE
# ============================================================================

def interactive_report_builder():
    """Interactive CLI for building custom client reports"""
    
    print("="*70)
    print("  DREAMS2MEMORIES WEEKLY CLIENT INTELLIGENCE REPORT GENERATOR")
    print("="*70)
    print()
    
    # Client info
    client_name = input("Client Name: ").strip()
    client_email = input("Client Email (optional, press Enter to skip): ").strip() or None
    
    print("\n--- TARGET SHIPS ---")
    print("Default ships: Silver Nova, Seven Seas Grandeur, World Navigator")
    use_defaults = input("Use default ships? (Y/n): ").strip().lower()
    
    if use_defaults == 'n':
        ships_input = input("Enter ship names (comma-separated): ")
        target_ships = [s.strip() for s in ships_input.split(',')]
    else:
        target_ships = ReportConfig.DEFAULT_SHIPS
    
    print(f"\n✓ Monitoring {len(target_ships)} ships: {', '.join(target_ships)}")
    
    # Report options
    print("\n--- REPORT OPTIONS ---")
    include_pricing = input("Include pricing intelligence? (Y/n): ").strip().lower() != 'n'
    include_availability = input("Include suite availability? (Y/n): ").strip().lower() != 'n'
    include_advisories = input("Include travel advisories? (Y/n): ").strip().lower() != 'n'
    include_weather = input("Include port weather? (Y/n): ").strip().lower() != 'n'
    include_news = input("Include industry news? (Y/n): ").strip().lower() != 'n'
    
    # Output format
    print("\n--- OUTPUT FORMAT ---")
    print("[1] PDF only")
    print("[2] HTML only")
    print("[3] Both PDF and HTML")
    format_choice = input("Select (1-3): ").strip()
    
    output_format = "both"
    if format_choice == "1":
        output_format = "pdf"
    elif format_choice == "2":
        output_format = "html"
    
    # Build request
    request = ClientReportRequest(
        client_name=client_name,
        client_email=client_email,
        target_ships=target_ships,
        target_destinations=ReportConfig.DEFAULT_DESTINATIONS,
        include_pricing=include_pricing,
        include_availability=include_availability,
        include_advisories=include_advisories,
        include_weather=include_weather,
        include_news=include_news,
        output_format=output_format
    )
    
    # Generate report
    print("\n" + "="*70)
    print("GENERATING REPORT...")
    print("="*70 + "\n")
    
    html = generate_html_report(request)
    
    # Save outputs
    timestamp = datetime.now().strftime("%Y%m%d")
    safe_name = client_name.replace(' ', '_').replace('/', '-')
    
    output_files = []
    
    if output_format in ["html", "both"]:
        html_path = ReportConfig.OUTPUT_DIR / f"Weekly_Report_{safe_name}_{timestamp}.html"
        html_path.parent.mkdir(parents=True, exist_ok=True)
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html)
        output_files.append(str(html_path))
        logger.info(f"✅ HTML saved: {html_path}")
    
    if output_format in ["pdf", "both"]:
        pdf_path = ReportConfig.OUTPUT_DIR / f"Weekly_Report_{safe_name}_{timestamp}.pdf"
        generate_pdf_report(html, pdf_path)
        output_files.append(str(pdf_path))
    
    print("\n" + "="*70)
    print("✨ REPORT GENERATION COMPLETE ✨")
    print("="*70)
    print("\nGenerated files:")
    for file in output_files:
        print(f"  • {file}")
    print()

def cli_main():
    """Main CLI entry point"""
    
    parser = argparse.ArgumentParser(
        description="Dreams2Memories Weekly Client Intelligence Report Generator"
    )
    
    parser.add_argument(
        '--client',
        type=str,
        help='Client name'
    )
    
    parser.add_argument(
        '--ships',
        type=str,
        help='Comma-separated list of ship names'
    )
    
    parser.add_argument(
        '--format',
        choices=['pdf', 'html', 'both'],
        default='both',
        help='Output format'
    )
    
    parser.add_argument(
        '--interactive',
        action='store_true',
        help='Run in interactive mode'
    )
    
    args = parser.parse_args()
    
    if args.interactive or not args.client:
        interactive_report_builder()
    else:
        # Non-interactive mode
        target_ships = args.ships.split(',') if args.ships else ReportConfig.DEFAULT_SHIPS
        
        request = ClientReportRequest(
            client_name=args.client,
            target_ships=target_ships,
            output_format=args.format
        )
        
        html = generate_html_report(request)
        
        timestamp = datetime.now().strftime("%Y%m%d")
        safe_name = args.client.replace(' ', '_')
        
        if args.format in ["html", "both"]:
            html_path = ReportConfig.OUTPUT_DIR / f"Weekly_Report_{safe_name}_{timestamp}.html"
            html_path.parent.mkdir(parents=True, exist_ok=True)
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html)
            logger.info(f"✅ HTML: {html_path}")
        
        if args.format in ["pdf", "both"]:
            pdf_path = ReportConfig.OUTPUT_DIR / f"Weekly_Report_{safe_name}_{timestamp}.pdf"
            generate_pdf_report(html, pdf_path)

# ============================================================================
# MCP TOOL REGISTRATION
# ============================================================================

def register_weekly_report_tools(mcp):
    """Register weekly report tools with the MCP server."""
    from mcp.server.fastmcp import FastMCP

    @mcp.tool(
        name="generate_weekly_report",
        annotations={"title": "Generate Weekly Client Intelligence Report", "readOnlyHint": False},
    )
    async def generate_weekly_report(
        client_name: str = Field(..., description="Client name for personalization"),
        target_ships: Optional[List[str]] = Field(None, description="Ships to monitor (default: Silver Nova, Seven Seas Grandeur, World Navigator)"),
        target_destinations: Optional[List[str]] = Field(None, description="Regions of interest (default: Mediterranean, Caribbean, Arctic, Antarctic)"),
        output_format: str = Field("both", description="Output: 'pdf', 'html', or 'both'"),
        include_pricing: bool = Field(True, description="Include pricing intelligence"),
        include_availability: bool = Field(True, description="Include suite availability alerts"),
        include_advisories: bool = Field(True, description="Include travel advisories"),
        include_weather: bool = Field(True, description="Include port weather forecasts"),
        include_news: bool = Field(True, description="Include industry news"),
    ) -> str:
        """Generate a comprehensive weekly client intelligence report with pricing, availability, advisories, weather, and news."""
        try:
            request = ClientReportRequest(
                client_name=client_name,
                target_ships=target_ships or ReportConfig.DEFAULT_SHIPS,
                target_destinations=target_destinations or ReportConfig.DEFAULT_DESTINATIONS,
                output_format=output_format,
                include_pricing=include_pricing,
                include_availability=include_availability,
                include_advisories=include_advisories,
                include_weather=include_weather,
                include_news=include_news,
            )

            html = generate_html_report(request)

            timestamp = datetime.now().strftime("%Y%m%d")
            safe_name = client_name.replace(" ", "_").replace("/", "-")
            output_files = []

            if output_format in ["html", "both"]:
                html_path = ReportConfig.OUTPUT_DIR / f"Weekly_Report_{safe_name}_{timestamp}.html"
                html_path.parent.mkdir(parents=True, exist_ok=True)
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(html)
                output_files.append(str(html_path))

            if output_format in ["pdf", "both"]:
                pdf_path = ReportConfig.OUTPUT_DIR / f"Weekly_Report_{safe_name}_{timestamp}.pdf"
                generate_pdf_report(html, pdf_path)
                output_files.append(str(pdf_path))

            return json.dumps({"status": "success", "client": client_name, "files": output_files}, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e), "type": "report_error"})

    logger.info("Weekly Report tools registered successfully")


# ============================================================================
# STANDALONE EXECUTION
# ============================================================================

if __name__ == "__main__":
    cli_main()
