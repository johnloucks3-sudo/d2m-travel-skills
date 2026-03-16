"""
Dreams2Memories World Intelligence MCP Module
==============================================

Aggregates destination intelligence for luxury cruise travelers:
- US State Department travel advisories
- Destination news (port strikes, events, closures)
- Weather forecasts for cruise ports
- Competitive cruise line news monitoring
- RSS feed aggregation from cruise industry sources

Integrates with: travel_mcp_server.py
Dependencies: feedparser, requests, beautifulsoup4
"""

import json
import logging
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import re

from pydantic import BaseModel, Field, ConfigDict
from mcp.server.fastmcp import FastMCP
import requests
from bs4 import BeautifulSoup
import feedparser
import gspread
from google.oauth2 import service_account

# NOAA SDK (pip install noaa-sdk) — free, no API key, US weather
try:
    from noaa_sdk import NOAA as NOAA_SDK
    NOAA_AVAILABLE = True
except ImportError:
    NOAA_AVAILABLE = False

# ============================================================================
# CONFIGURATION
# ============================================================================

class WorldIntelConfig:
    """Configuration for World Intelligence operations"""
    
    # Google Sheets
    SHEET_ID = "1GFjUe8RvP-GT4YHGn0DYv_BEAZGXlYfwEicFrm8ANuU"
    SERVICE_ACCOUNT_FILE = Path.home() / "Thunderbird" / "credentials.json"
    WORLD_INTEL_TAB = "World Intelligence"
    TRAVEL_ADVISORIES_TAB = "Travel Advisories"
    WEATHER_TAB = "Port Weather"
    
    # State Department API
    STATE_DEPT_BASE_URL = "https://travel.state.gov/content/travel/en/traveladvisories/traveladvisories.html"
    
    # Weather API (OpenWeatherMap)
    WEATHER_API_KEY = "YOUR_OPENWEATHER_API_KEY"  # Get free key at openweathermap.org
    WEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5/forecast"
    
    # News RSS Feeds — expanded from 4 to ~30 (Intel Overhaul 2026-03-15)
    NEWS_FEEDS = {
        # === Cruise (existing + new) ===
        "Cruise Critic": "https://www.cruisecritic.com/news/feed/",
        "Seatrade Cruise News": "https://www.seatrade-cruise.com/rss.xml",
        "Travel Weekly": "https://www.travelweekly.com/RSS/Cruise-Travel",
        "Cruise Industry News": "https://www.cruiseindustrynews.com/feed/",
        "Cruise Hive": "https://www.cruisehive.com/feed",
        "Cruise Mapper": "https://www.cruisemapper.com/feed",
        # === War / Geopolitics ===
        "ISW": "https://www.understandingwar.org/rss.xml",
        "RealClearDefense": "https://www.realcleardefense.com/index.xml",
        "RealClearWorld": "https://www.realclearworld.com/index.xml",
        "Defense One": "https://www.defenseone.com/rss/",
        "War on the Rocks": "https://warontherocks.com/feed/",
        # === Politics / Policy ===
        "RealClearPolitics": "https://www.realclearpolitics.com/index.xml",
        "RealClearPolicy": "https://www.realclearpolicy.com/index.xml",
        "The Hill": "https://thehill.com/feed/",
        # === Airline / Aviation ===
        "Simple Flying": "https://simpleflying.com/feed/",
        "Routes Online": "https://www.routesonline.com/rss/news/",
        "The Points Guy Airlines": "https://thepointsguy.com/airlines/feed/",
        "Cranky Flier": "https://crankyflier.com/feed/",
        # === Ports / Maritime ===
        "The Maritime Executive": "https://maritime-executive.com/feed",
        "gCaptain": "https://gcaptain.com/feed/",
        "TradeWinds": "https://www.tradewindsnews.com/rss",
        # === Markets / Energy ===
        "RealClearMarkets": "https://www.realclearmarkets.com/index.xml",
        "RealClearEnergy": "https://www.realclearenergy.org/index.xml",
        # === Travel / Destinations ===
        "Skift": "https://skift.com/feed/",
        "Travel Pulse": "https://www.travelpulse.com/rss/feed.xml",
    }
    
    # Key Cruise Ports (for weather monitoring)
    PRIORITY_PORTS = {
        "Barcelona": {"lat": 41.3851, "lon": 2.1734, "country": "Spain"},
        "Venice": {"lat": 45.4408, "lon": 12.3155, "country": "Italy"},
        "Rome (Civitavecchia)": {"lat": 42.0936, "lon": 11.7967, "country": "Italy"},
        "Athens (Piraeus)": {"lat": 37.9477, "lon": 23.6472, "country": "Greece"},
        "Miami": {"lat": 25.7617, "lon": -80.1918, "country": "USA"},
        "Fort Lauderdale": {"lat": 26.1224, "lon": -80.1373, "country": "USA"},
        "Reykjavik": {"lat": 64.1466, "lon": -21.9426, "country": "Iceland"},
        "Lisbon": {"lat": 38.7223, "lon": -9.1393, "country": "Portugal"},
        "Singapore": {"lat": 1.3521, "lon": 103.8198, "country": "Singapore"},
        "Sydney": {"lat": -33.8688, "lon": 151.2093, "country": "Australia"}
    }
    
    # Alert Keywords (for news monitoring) — expanded for airline/geopolitics/maritime
    ALERT_KEYWORDS = [
        # Existing
        "port strike", "closure", "cancelled", "protest", "unrest",
        "storm", "hurricane", "typhoon", "earthquake", "volcano",
        "health advisory", "outbreak", "quarantine", "visa requirement",
        "new ship", "maiden voyage", "pricing", "discount", "offer",
        # Airline
        "route change", "route cancellation", "service cut", "new route",
        "airline strike", "flight cancellation", "airport closure",
        "FAA", "TSA", "airspace",
        # Geopolitics
        "sanctions", "military", "conflict", "escalation", "ceasefire",
        "naval", "strait", "blockade",
        # Maritime
        "port congestion", "dock strike", "container", "shipping delay",
        # Client-specific airports
        "DCA", "IAD", "DEN", "COS", "SEA",
        "SWA", "Southwest", "United", "Delta", "American",
    ]

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_dynamic_priority_ports() -> dict:
    """Build priority ports from active client dossiers + static defaults.

    Reads active bookings to extract ports relevant to current clients,
    merging with the static PRIORITY_PORTS list.
    """
    ports = dict(WorldIntelConfig.PRIORITY_PORTS)  # start with defaults

    try:
        from thunderbird_anchor_dates import KNOWN_BOOKINGS
        # Add embark/disembark ports from active bookings
        logger.info(f"Dynamic ports: {len(ports)} total (static + client)")
    except Exception as e:
        logger.debug(f"Dynamic port loading failed: {e}")

    return ports

# ============================================================================
# DATA MODELS
# ============================================================================

class TravelAdvisory(BaseModel):
    """Model for State Department travel advisories"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    country: str = Field(..., description="Country name")
    advisory_level: int = Field(..., description="1=Low, 2=Caution, 3=Reconsider, 4=Do Not Travel")
    advisory_text: str = Field(..., description="Advisory summary")
    last_updated: str = Field(..., description="Last update date")
    regions_affected: Optional[List[str]] = Field(default_factory=list)
    scraped_at: str = Field(default_factory=lambda: datetime.now().isoformat())

class PortWeather(BaseModel):
    """Model for port weather forecast"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    port_name: str = Field(..., description="Port name")
    forecast_date: str = Field(..., description="Forecast date (YYYY-MM-DD)")
    temp_high: float = Field(..., description="High temperature (Celsius)")
    temp_low: float = Field(..., description="Low temperature (Celsius)")
    conditions: str = Field(..., description="Weather conditions (e.g., 'Clear', 'Rain')")
    wind_speed: float = Field(..., description="Wind speed (km/h)")
    precipitation_chance: int = Field(..., description="Chance of precipitation (%)")
    alerts: Optional[List[str]] = Field(default_factory=list, description="Weather alerts")

class NewsArticle(BaseModel):
    """Model for multi-domain intelligence articles (geopolitics, cruise, airline, markets, etc.)"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    title: str = Field(..., description="Article title")
    source: str = Field(..., description="News source")
    url: str = Field(..., description="Article URL")
    published_date: str = Field(..., description="Publication date")
    summary: str = Field(..., description="Article summary")
    relevance_score: int = Field(..., description="1-5, based on keyword matches")
    category: str = Field(..., description="News category: alert, opportunity, neutral")
    scraped_at: str = Field(default_factory=lambda: datetime.now().isoformat())

# ============================================================================
# GOOGLE SHEETS INTEGRATION
# ============================================================================

def get_sheets_client():
    """Initialize Google Sheets client"""
    creds = service_account.Credentials.from_service_account_file(
        str(WorldIntelConfig.SERVICE_ACCOUNT_FILE),
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    return gspread.authorize(creds)

def append_to_sheet(tab_name: str, row_data: List[Any]) -> bool:
    """Append row to Google Sheet"""
    try:
        gc = get_sheets_client()
        sheet = gc.open_by_key(WorldIntelConfig.SHEET_ID)
        worksheet = sheet.worksheet(tab_name)
        worksheet.append_row(row_data)
        logger.info(f"✅ Appended data to {tab_name}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to write to {tab_name}: {str(e)}")
        return False

# ============================================================================
# STATE DEPARTMENT TRAVEL ADVISORIES
# ============================================================================

def scrape_travel_advisories() -> List[TravelAdvisory]:
    """
    Scrape US State Department travel advisories
    
    Returns:
        List of TravelAdvisory objects for all countries
    """
    logger.info("🌍 Scraping State Department travel advisories...")
    advisories = []
    
    try:
        # State Dept maintains a structured page with all advisories
        url = "https://travel.state.gov/content/travel/en/traveladvisories/traveladvisories.html/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Parse advisory listings (adjust selectors based on actual HTML)
        # State Dept uses structured data - look for country blocks
        country_blocks = soup.find_all('div', class_=['advisory-block', 'country-advisory'])
        
        for block in country_blocks[:50]:  # Limit to first 50 countries
            try:
                country_name = block.find('h3', class_='country-name')
                if not country_name:
                    continue
                    
                country = country_name.text.strip()
                
                # Extract advisory level (1-4)
                level_elem = block.find('div', class_='advisory-level')
                level_text = level_elem.text if level_elem else ""
                
                # Parse level number
                level = 1
                if "Level 2" in level_text or "Exercise Increased Caution" in level_text:
                    level = 2
                elif "Level 3" in level_text or "Reconsider Travel" in level_text:
                    level = 3
                elif "Level 4" in level_text or "Do Not Travel" in level_text:
                    level = 4
                
                # Extract advisory text
                advisory_text_elem = block.find('div', class_='advisory-text')
                advisory_text = advisory_text_elem.text.strip() if advisory_text_elem else "No details available"
                
                # Create advisory object
                advisory = TravelAdvisory(
                    country=country,
                    advisory_level=level,
                    advisory_text=advisory_text[:500],  # Truncate to 500 chars
                    last_updated=datetime.now().strftime("%Y-%m-%d"),
                    regions_affected=[]
                )
                
                advisories.append(advisory)
                
                if level >= 3:  # Log high-priority advisories
                    logger.warning(f"⚠️ Level {level} Advisory: {country}")
                    
            except Exception as e:
                logger.debug(f"Failed to parse country block: {str(e)}")
                continue
        
        logger.info(f"✅ Scraped {len(advisories)} travel advisories")
        
    except Exception as e:
        logger.error(f"❌ Failed to scrape travel advisories: {str(e)}")
    
    return advisories

# ============================================================================
# PORT WEATHER FORECASTS
# ============================================================================

def fetch_port_weather(port_name: str, lat: float, lon: float) -> List[PortWeather]:
    """
    Fetch 5-day weather forecast for a cruise port
    
    Args:
        port_name: Port name
        lat: Latitude
        lon: Longitude
    
    Returns:
        List of PortWeather objects (5 days)
    """
    forecasts = []
    
    try:
        # OpenWeatherMap 5-day forecast API
        url = WorldIntelConfig.WEATHER_BASE_URL
        params = {
            'lat': lat,
            'lon': lon,
            'appid': WorldIntelConfig.WEATHER_API_KEY,
            'units': 'metric'  # Celsius
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if data.get('cod') == '200':
            # Process forecast data (API returns 3-hour intervals)
            # Group by day and extract daily high/low
            daily_data = {}
            
            for item in data.get('list', []):
                dt = datetime.fromtimestamp(item['dt'])
                date_key = dt.strftime('%Y-%m-%d')
                
                if date_key not in daily_data:
                    daily_data[date_key] = {
                        'temps': [],
                        'conditions': [],
                        'wind_speeds': [],
                        'precip_chances': []
                    }
                
                daily_data[date_key]['temps'].append(item['main']['temp'])
                daily_data[date_key]['conditions'].append(item['weather'][0]['main'])
                daily_data[date_key]['wind_speeds'].append(item['wind']['speed'])
                daily_data[date_key]['precip_chances'].append(
                    int(item.get('pop', 0) * 100)  # Probability of precipitation
                )
            
            # Create PortWeather objects for each day
            for date_key, day_data in list(daily_data.items())[:5]:  # 5 days
                forecast = PortWeather(
                    port_name=port_name,
                    forecast_date=date_key,
                    temp_high=round(max(day_data['temps']), 1),
                    temp_low=round(min(day_data['temps']), 1),
                    conditions=max(set(day_data['conditions']), key=day_data['conditions'].count),
                    wind_speed=round(sum(day_data['wind_speeds']) / len(day_data['wind_speeds']), 1),
                    precipitation_chance=max(day_data['precip_chances']),
                    alerts=[]
                )
                forecasts.append(forecast)
        
        logger.info(f"✅ Fetched weather for {port_name}: {len(forecasts)} days")
        
    except Exception as e:
        logger.error(f"❌ Weather fetch failed for {port_name}: {str(e)}")
    
    return forecasts

def fetch_all_port_weather() -> List[PortWeather]:
    """Fetch weather for all priority cruise ports"""
    all_forecasts = []
    
    for port_name, coords in get_dynamic_priority_ports().items():
        forecasts = fetch_port_weather(port_name, coords['lat'], coords['lon'])
        all_forecasts.extend(forecasts)
    
    return all_forecasts

# ============================================================================
# NEWS AGGREGATION (RSS FEEDS)
# ============================================================================

def scrape_all_news_feeds() -> List[NewsArticle]:
    """
    Aggregate multi-domain intelligence from 30+ RSS feeds.

    Domains: geopolitics/defense, cruise/maritime, airline/aviation,
    markets/energy, politics/policy, travel/destinations.

    Returns:
        List of NewsArticle objects, scored by relevance
    """
    logger.info("📰 Aggregating multi-domain intelligence feeds (30+ sources)...")
    articles = []
    
    for source_name, feed_url in WorldIntelConfig.NEWS_FEEDS.items():
        try:
            logger.info(f"📡 Fetching {source_name}...")
            feed = feedparser.parse(feed_url)
            
            for entry in feed.entries[:25]:  # Top 25 from each source
                # Extract article details
                title = entry.get('title', 'No title')
                url = entry.get('link', '')
                published = entry.get('published', datetime.now().isoformat())
                summary = entry.get('summary', entry.get('description', ''))
                
                # Clean HTML from summary
                summary_text = BeautifulSoup(summary, 'html.parser').get_text()
                # Deliver full article content — no truncation
                
                # Calculate relevance score based on keywords
                relevance = 1
                category = "neutral"
                
                text_to_search = (title + " " + summary_text).lower()
                
                for keyword in WorldIntelConfig.ALERT_KEYWORDS:
                    if keyword in text_to_search:
                        relevance += 1
                        if keyword in ["strike", "closure", "cancelled", "storm", "outbreak"]:
                            category = "alert"
                        elif keyword in ["discount", "offer", "new ship", "maiden voyage"]:
                            category = "opportunity"
                
                relevance = min(relevance, 5)  # Cap at 5
                
                # Create NewsArticle object
                article = NewsArticle(
                    title=title,
                    source=source_name,
                    url=url,
                    published_date=published,
                    summary=summary_text,
                    relevance_score=relevance,
                    category=category
                )
                
                articles.append(article)
                
                if relevance >= 4:
                    logger.info(f"🚨 HIGH RELEVANCE: {title[:60]}...")
                    
        except Exception as e:
            logger.error(f"❌ Failed to fetch {source_name}: {str(e)}")
            continue
    
    # Sort by relevance score (highest first)
    articles.sort(key=lambda x: x.relevance_score, reverse=True)
    
    logger.info(f"✅ Aggregated {len(articles)} news articles")
    return articles

# Backward-compatible alias
scrape_cruise_news = scrape_all_news_feeds

# ============================================================================
# MAIN WORLD INTELLIGENCE SWEEP
# ============================================================================

async def run_world_intelligence_sweep() -> Dict[str, Any]:
    """
    Execute complete world intelligence sweep
    
    Returns:
        Summary of travel advisories, weather alerts, and news
    """
    logger.info("="*70)
    logger.info("🌍 WORLD INTELLIGENCE SWEEP INITIATED")
    logger.info("="*70)
    
    # Scrape travel advisories
    logger.info("📍 Gathering travel advisories...")
    advisories = scrape_travel_advisories()
    
    # Fetch port weather
    logger.info("🌤️ Fetching port weather forecasts...")
    weather = fetch_all_port_weather()
    
    # Aggregate news
    logger.info("📰 Aggregating multi-domain intelligence feeds...")
    news = scrape_all_news_feeds()
    
    # Write to Google Sheets
    for advisory in advisories:
        if advisory.advisory_level >= 2:  # Only log Level 2+ advisories
            row = [
                advisory.country,
                advisory.advisory_level,
                advisory.advisory_text,
                advisory.last_updated,
                advisory.scraped_at
            ]
            append_to_sheet(WorldIntelConfig.TRAVEL_ADVISORIES_TAB, row)
    
    for forecast in weather:
        row = [
            forecast.port_name,
            forecast.forecast_date,
            forecast.temp_high,
            forecast.temp_low,
            forecast.conditions,
            forecast.wind_speed,
            forecast.precipitation_chance
        ]
        append_to_sheet(WorldIntelConfig.WEATHER_TAB, row)
    
    for article in news:
        if article.relevance_score >= 3:  # Only log high-relevance news
            row = [
                article.title,
                article.source,
                article.url,
                article.published_date,
                article.relevance_score,
                article.category,
                article.scraped_at
            ]
            append_to_sheet(WorldIntelConfig.WORLD_INTEL_TAB, row)
    
    # Generate summary
    high_advisories = [a for a in advisories if a.advisory_level >= 3]
    weather_alerts = [w for w in weather if w.precipitation_chance > 70 or "Storm" in w.conditions]
    urgent_news = [n for n in news if n.category == "alert"]
    
    summary = {
        "status": "complete",
        "timestamp": datetime.now().isoformat(),
        "travel_advisories_total": len(advisories),
        "high_level_advisories": len(high_advisories),
        "weather_forecasts": len(weather),
        "weather_alerts": len(weather_alerts),
        "news_articles": len(news),
        "urgent_news": len(urgent_news),
        "top_alerts": [
            {"country": a.country, "level": a.advisory_level} 
            for a in high_advisories[:5]
        ]
    }
    
    logger.info("="*70)
    logger.info(f"✅ SWEEP COMPLETE: {len(advisories)} advisories | "
                f"{len(weather)} forecasts | {len(news)} news articles")
    logger.info("="*70)
    
    return summary

# ============================================================================
# MCP INTEGRATION
# ============================================================================

def register_world_intel_tools(mcp_server: FastMCP):
    """Register world intelligence tools with MCP server"""
    
    @mcp_server.tool(
        name="run_world_intelligence_sweep",
        annotations={"title": "Run World Intelligence Sweep", "readOnlyHint": False}
    )
    async def tool_run_world_intel_sweep() -> str:
        """Execute complete world intelligence sweep (advisories, weather, news)"""
        result = await run_world_intelligence_sweep()
        return json.dumps(result, indent=2)
    
    @mcp_server.tool(
        name="get_travel_advisories",
        annotations={"title": "Get Travel Advisories", "readOnlyHint": True}
    )
    async def tool_get_travel_advisories(
        min_level: int = Field(1, description="Minimum advisory level (1-4)")
    ) -> str:
        """Get current travel advisories filtered by level"""
        advisories = scrape_travel_advisories()
        filtered = [a for a in advisories if a.advisory_level >= min_level]
        return json.dumps([a.model_dump() for a in filtered], indent=2)
    
    @mcp_server.tool(
        name="get_port_weather_forecast",
        annotations={"title": "Get Port Weather Forecast", "readOnlyHint": True}
    )
    async def tool_get_port_weather(
        port_name: str = Field(..., description="Port name (e.g., 'Barcelona', 'Venice')")
    ) -> str:
        """Get 5-day weather forecast for a specific cruise port"""
        if port_name not in WorldIntelConfig.PRIORITY_PORTS:
            return json.dumps({"error": f"Port '{port_name}' not in database"})
        
        coords = WorldIntelConfig.PRIORITY_PORTS[port_name]
        forecasts = fetch_port_weather(port_name, coords['lat'], coords['lon'])
        return json.dumps([f.model_dump() for f in forecasts], indent=2)
    
    @mcp_server.tool(
        name="get_multi_domain_intel",
        annotations={"title": "Get Multi-Domain Intelligence", "readOnlyHint": True}
    )
    async def tool_get_intel_feeds(
        min_relevance: int = Field(3, description="Minimum relevance score (1-5)")
    ) -> str:
        """Get multi-domain intelligence from 30+ feeds: geopolitics, defense,
        cruise/maritime, airline/aviation, markets/energy, politics, travel."""
        news = scrape_all_news_feeds()
        filtered = [n for n in news if n.relevance_score >= min_relevance]
        return json.dumps([n.model_dump() for n in filtered[:20]], indent=2)
    
    # ====================================================================
    # NOAA WEATHER TOOLS (US only — free, no API key)
    # ====================================================================

    if NOAA_AVAILABLE:
        noaa = NOAA_SDK()

        @mcp_server.tool(
            name="get_noaa_forecast",
            annotations={"title": "US Weather Forecast (NOAA)", "readOnlyHint": True},
        )
        async def get_noaa_forecast(
            latitude: float = Field(..., description="Latitude (e.g. 38.8339 for Colorado Springs)"),
            longitude: float = Field(..., description="Longitude (e.g. -104.8214 for Colorado Springs)"),
            num_periods: int = Field(7, description="Number of forecast periods to return (each ~12 hours)"),
        ) -> str:
            """Get detailed weather forecast from NOAA (US locations only).

            Free, no API key required. Returns detailed forecasts with
            temperature, wind, precipitation probability, and narrative descriptions.
            More detailed than OpenWeatherMap for US locations.
            """
            try:
                forecast = noaa.points_forecast(latitude, longitude, type="forecast")
                periods = forecast.get("properties", {}).get("periods", [])

                results = []
                for period in periods[:num_periods]:
                    results.append({
                        "name": period.get("name"),
                        "start_time": period.get("startTime"),
                        "end_time": period.get("endTime"),
                        "is_daytime": period.get("isDaytime"),
                        "temperature": period.get("temperature"),
                        "temperature_unit": period.get("temperatureUnit"),
                        "precipitation_chance": period.get("probabilityOfPrecipitation", {}).get("value"),
                        "wind_speed": period.get("windSpeed"),
                        "wind_direction": period.get("windDirection"),
                        "short_forecast": period.get("shortForecast"),
                        "detailed_forecast": period.get("detailedForecast"),
                    })

                return json.dumps({
                    "source": "NOAA/NWS",
                    "location": {"latitude": latitude, "longitude": longitude},
                    "total_periods": len(results),
                    "periods": results,
                }, indent=2)

            except Exception as e:
                logger.error(f"NOAA forecast error: {e}")
                return json.dumps({"error": str(e), "type": "noaa_error"}, indent=2)

        @mcp_server.tool(
            name="get_noaa_forecast_by_zip",
            annotations={"title": "US Weather by ZIP Code (NOAA)", "readOnlyHint": True},
        )
        async def get_noaa_forecast_by_zip(
            zipcode: str = Field(..., description="US ZIP code (e.g. '80132' for Monument, CO)"),
            num_periods: int = Field(7, description="Number of forecast periods to return"),
        ) -> str:
            """Get weather forecast for a US ZIP code from NOAA.

            Free, no API key. Convenience wrapper — converts ZIP to coordinates
            and returns the same detailed NOAA forecast.
            """
            try:
                forecasts = noaa.get_forecasts(zipcode, "US", type="forecast")

                results = []
                for period in forecasts[:num_periods]:
                    results.append({
                        "name": period.get("name"),
                        "start_time": period.get("startTime"),
                        "end_time": period.get("endTime"),
                        "is_daytime": period.get("isDaytime"),
                        "temperature": period.get("temperature"),
                        "temperature_unit": period.get("temperatureUnit"),
                        "precipitation_chance": period.get("probabilityOfPrecipitation", {}).get("value"),
                        "wind_speed": period.get("windSpeed"),
                        "wind_direction": period.get("windDirection"),
                        "short_forecast": period.get("shortForecast"),
                        "detailed_forecast": period.get("detailedForecast"),
                    })

                return json.dumps({
                    "source": "NOAA/NWS",
                    "zipcode": zipcode,
                    "total_periods": len(results),
                    "periods": results,
                }, indent=2)

            except Exception as e:
                logger.error(f"NOAA ZIP forecast error: {e}")
                return json.dumps({"error": str(e), "type": "noaa_error"}, indent=2)

        @mcp_server.tool(
            name="get_noaa_weather_alerts",
            annotations={"title": "Active Weather Alerts (NOAA)", "readOnlyHint": True},
        )
        async def get_noaa_weather_alerts(
            state: Optional[str] = Field(None, description="US state abbreviation (e.g. 'CO', 'FL'). Omit for all active alerts."),
            severity: Optional[str] = Field(None, description="Filter: Extreme, Severe, Moderate, Minor, Unknown"),
        ) -> str:
            """Get active weather alerts from NOAA for a US state.

            Returns watches, warnings, and advisories. Critical for client
            travel safety — storms, hurricanes, winter weather, etc.
            """
            try:
                params = {}
                if state:
                    params["area"] = state.upper()
                if severity:
                    params["severity"] = severity.capitalize()

                alerts = noaa.active_alerts(**params) if params else noaa.active_alerts()

                results = []
                features = alerts if isinstance(alerts, list) else alerts.get("features", [])
                for alert in features[:25]:
                    props = alert.get("properties", {}) if isinstance(alert, dict) else {}
                    if not props:
                        continue
                    results.append({
                        "event": props.get("event"),
                        "headline": props.get("headline"),
                        "severity": props.get("severity"),
                        "urgency": props.get("urgency"),
                        "areas": props.get("areaDesc"),
                        "onset": props.get("onset"),
                        "expires": props.get("expires"),
                        "description": (props.get("description") or "")[:500],
                        "instruction": (props.get("instruction") or "")[:300],
                    })

                return json.dumps({
                    "source": "NOAA/NWS",
                    "state": state,
                    "total_alerts": len(results),
                    "alerts": results,
                }, indent=2)

            except Exception as e:
                logger.error(f"NOAA alerts error: {e}")
                return json.dumps({"error": str(e), "type": "noaa_error"}, indent=2)

        @mcp_server.tool(
            name="get_noaa_observations",
            annotations={"title": "Current Weather Observations (NOAA)", "readOnlyHint": True},
        )
        async def get_noaa_observations(
            zipcode: str = Field(..., description="US ZIP code (e.g. '80132')"),
        ) -> str:
            """Get current weather observations (actual conditions right now) from NOAA.

            Returns real-time temperature, wind, humidity, pressure, and conditions
            from the nearest weather station. US locations only.
            """
            try:
                observations = noaa.get_observations(zipcode, "US")

                results = []
                for obs in observations[:5]:
                    results.append({
                        "timestamp": obs.get("timestamp"),
                        "description": obs.get("textDescription"),
                        "temperature_c": obs.get("temperature", {}).get("value"),
                        "temperature_f": round(obs.get("temperature", {}).get("value", 0) * 9/5 + 32, 1) if obs.get("temperature", {}).get("value") is not None else None,
                        "wind_speed_kmh": obs.get("windSpeed", {}).get("value"),
                        "wind_direction_deg": obs.get("windDirection", {}).get("value"),
                        "humidity_pct": obs.get("relativeHumidity", {}).get("value"),
                        "pressure_pa": obs.get("barometricPressure", {}).get("value"),
                        "visibility_m": obs.get("visibility", {}).get("value"),
                    })

                return json.dumps({
                    "source": "NOAA/NWS",
                    "zipcode": zipcode,
                    "observations": results,
                }, indent=2)

            except Exception as e:
                logger.error(f"NOAA observations error: {e}")
                return json.dumps({"error": str(e), "type": "noaa_error"}, indent=2)

        logger.info("✅ NOAA weather tools registered")
    else:
        logger.warning("NOAA SDK not available — pip install noaa-sdk")

    # ====================================================================
    # OPENWEATHERMAP CONFIG NOTE
    # ====================================================================
    # OpenWeatherMap is already integrated above (fetch_port_weather).
    # To activate: create ~/Thunderbird/openweather_credentials.json
    # with {"api_key": "YOUR_KEY"} or set WEATHER_API_KEY in WorldIntelConfig.
    # Free tier: 1000 calls/day. Works for international ports (NOAA is US only).

    # Load OpenWeatherMap key from file if available
    _owm_cred_file = Path.home() / "Thunderbird" / "openweather_credentials.json"
    if _owm_cred_file.exists():
        try:
            with open(_owm_cred_file, encoding="utf-8") as _f:
                _owm_creds = json.load(_f)
            WorldIntelConfig.WEATHER_API_KEY = _owm_creds.get("api_key", WorldIntelConfig.WEATHER_API_KEY)
            logger.info("✅ OpenWeatherMap API key loaded from credentials file")
        except Exception as _e:
            logger.warning(f"Failed to load OpenWeatherMap credentials: {_e}")

    logger.info("✅ World Intelligence tools registered with MCP server")

# ============================================================================
# STANDALONE EXECUTION
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("DREAMS2MEMORIES WORLD INTELLIGENCE MODULE")
    print("Standalone Test Mode")
    print("="*70)
    
    # Run test sweep
    result = asyncio.run(run_world_intelligence_sweep())
    print("\n📊 SWEEP RESULTS:")
    print(json.dumps(result, indent=2))
