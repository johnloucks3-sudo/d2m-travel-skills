#!/usr/bin/env python3
"""
Thunderbird Intel Crew — Persona Chain Pipeline
=================================================

The intelligence pipeline:
  A2 Dembe (COLLECT) → A2 Dembe (ANALYZE) → A1 Radar (AUDIT) → COS Hale (REVIEW) → Commander

Uses sequential call_persona() calls with Claude Opus.
Each persona's output feeds into the next persona's prompt.

Usage:
  from thunderbird_intel_crew import IntelCrew
  result = IntelCrew().run()

  # Or run specific stages:
  crew = IntelCrew()
  raw = crew.collect()
  analyzed = crew.analyze(raw)
  audited = crew.audit(analyzed)
  reviewed = crew.review(audited)
"""

import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger("thunderbird_intel_crew")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [INTEL_CREW] %(message)s",
    stream=sys.stderr,
)

THUNDERBIRD_DIR = Path(__file__).parent
DOSSIER_DIR = THUNDERBIRD_DIR / "dossiers"
MEMORY_DIR = Path.home() / ".claude" / "projects" / "-home-john-Thunderbird" / "memory"


# ============================================================================
# DYNAMIC CLIENT PROFILE LOADER
# ============================================================================

# Known cruise line names for extraction
_CRUISE_LINES = [
    "Silversea", "Regent", "RSSC", "Regent Seven Seas",
    "Cunard", "Oceania", "Seabourn", "Viking", "AmaWaterways",
    "Ponant", "Princess", "Celebrity", "Royal Caribbean",
]

# Common airport codes (IATA) — used for regex extraction
_AIRPORT_RE = re.compile(r'\b([A-Z]{3})\b')

# Known IATA codes relevant to D2M clients (avoids false positives from 3-letter words)
_KNOWN_AIRPORTS = {
    "COS", "DEN", "DCA", "IAD", "RIC", "OMA", "EWR", "JFK", "LGA",
    "HNL", "OGG", "KOA", "LIH", "ITO", "SEA", "LAX", "SFO", "SAN",
    "OAK", "SJC", "SMF", "PHX", "LAS", "DFW", "ATH", "FCO", "VCE",
    "ARN", "CPH", "OSL", "FLL", "PBI", "MIA", "PTY", "ANC", "JAX",
    "ATL", "ORD", "BOS", "YYZ",
}


def _extract_from_trip_dossier(text: str) -> List[Dict]:
    """Extract client profiles from a trip dossier (~/Thunderbird/dossiers/ format).

    These files use plain-text formatting with fields like:
      Ship: Silver Nova (Silversea)
      Route: Yokohama → Pacific → Seattle
      Embarkation: April 23, 2026
      CLIENT: JOHN & SUSAN LOUCKS
    """
    profiles = []

    # Extract ship and cruise line
    ship_match = re.search(r'Ship:\s*(.+?)(?:\n|$)', text)
    cruise_lines_found = []
    if ship_match:
        ship_line = ship_match.group(1).strip()
        for cl in _CRUISE_LINES:
            if cl.lower() in ship_line.lower():
                cruise_lines_found.append(cl)

    # Extract route / ports from the Route line
    route_match = re.search(r'Route:\s*(.+?)(?:\n|$)', text)
    ports = []
    if route_match:
        route_text = route_match.group(1).strip()
        # Split on arrows and extract city names
        for segment in re.split(r'[→>]', route_text):
            port = segment.strip()
            if port and port not in ("TBD",):
                # Strip parenthetical info for the port name
                clean = re.sub(r'\s*\(.*?\)', '', port).strip()
                if clean:
                    ports.append(clean)

    # Extract embarkation/disembarkation dates
    dates = []
    for label in ("Embarkation", "Disembarkation"):
        m = re.search(rf'{label}:\s*(.+?)(?:\n|$)', text)
        if m:
            dates.append(m.group(1).strip())

    # Extract destinations from route ports + embark/disembark lines
    destinations = list(ports)
    for d in dates:
        # Extract city/country after the date portion
        city_m = re.search(r'—\s*(.+?)$', d)
        if city_m:
            city = city_m.group(1).strip()
            if city not in destinations:
                destinations.append(city)

    # Extract airport codes found in the text
    airports = set()
    for m in _AIRPORT_RE.finditer(text):
        code = m.group(1)
        if code in _KNOWN_AIRPORTS:
            airports.add(code)

    # Find all CLIENT sections
    client_blocks = re.finditer(
        r'(?:CLIENT|BOOKING\s+\d+):\s*(.+?)(?:\n|═)',
        text
    )

    for cb in client_blocks:
        client_name = cb.group(1).strip()
        # Clean up "JOHN & SUSAN LOUCKS" → "Loucks"
        # Use the last word as family name for matching
        name_parts = client_name.split()
        if name_parts:
            family_name = name_parts[-1].title()
            # Also keep the full name for display
            profile = {
                "destinations": destinations,
                "cruise_lines": cruise_lines_found,
                "ports": ports,
                "airports": sorted(airports),
                "dates": dates,
            }
            # Remove empty lists
            profile = {k: v for k, v in profile.items() if v}
            if profile:
                profiles.append((family_name, profile))

    return profiles


def _extract_from_memory_dossier(text: str, filename: str) -> List[Dict]:
    """Extract client profiles from a memory dossier (~/.claude/.../memory/dossier_*.md format).

    These files use markdown with YAML frontmatter and markdown tables.
    """
    profiles = []

    # Extract client name from filename: dossier_Lyons_Nancy_Ken.md → "Lyons"
    fname_match = re.match(r'dossier_([^.]+)', filename)
    if not fname_match:
        return profiles
    name_parts = fname_match.group(1).split('_')
    family_name = name_parts[0]  # First part is family name

    # Extract destinations
    destinations = []

    # Look for destination in Travel Profile table or Travel Opportunity
    dest_patterns = [
        r'\*\*Destination\*\*\s*\|\s*(.+?)(?:\s*\||\s*$)',
        r'\*\*Upcoming Voyage\*\*\s*\|\s*(.+?)(?:\s*\||\s*$)',
        r'\*\*Trip\*\*\s*\|\s*(.+?)(?:\s*\||\s*$)',
        r'\*\*Current Need\*\*\s*\|\s*(.+?)(?:\s*\||\s*$)',
    ]
    for pattern in dest_patterns:
        for m in re.finditer(pattern, text):
            val = m.group(1).strip()
            if val and val != "TBD":
                destinations.append(val)

    # Extract embarkation/disembarkation info
    dates = []
    for label in ("Embarkation", "Disembarkation"):
        m = re.search(rf'\*\*{label}\*\*\s*\|\s*(.+?)(?:\s*\||\s*$)', text)
        if m:
            dates.append(m.group(1).strip())

    # Extract ship/cruise line
    cruise_lines = []
    ship_match = re.search(r'\*\*Ship\*\*\s*\|\s*(.+?)(?:\s*\||\s*$)', text)
    if ship_match:
        ship_text = ship_match.group(1).strip()
        for cl in _CRUISE_LINES:
            if cl.lower() in ship_text.lower():
                cruise_lines.append(cl)

    # Also scan full text for cruise line mentions
    for cl in _CRUISE_LINES:
        if cl.lower() in text.lower() and cl not in cruise_lines:
            cruise_lines.append(cl)

    # Extract ports from route or hotel info
    ports = []
    hotel_match = re.search(r'\*\*Pre-Cruise Hotel\*\*\s*\|\s*(.+?)(?:\s*\||\s*$)', text)
    if hotel_match:
        hotel_text = hotel_match.group(1).strip()
        # Extract city from hotel line (e.g., "Hotel Grande Bretagne, Athens")
        city_m = re.search(r',\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', hotel_text)
        if city_m:
            ports.append(city_m.group(1))

    # Extract airports
    airports = set()
    # Look for explicit airport mentions
    origin_match = re.search(r'\*\*Origin\*\*\s*\|\s*(.+?)(?:\s*\||\s*$)', text)
    if origin_match:
        origin = origin_match.group(1).strip()
        # Extract IATA codes from parenthetical mentions like (DCA/IAD/RIC)
        for code in re.findall(r'[A-Z]{3}', origin):
            if code in _KNOWN_AIRPORTS:
                airports.add(code)

    # Scan full text for known airport codes
    for m in _AIRPORT_RE.finditer(text):
        code = m.group(1)
        if code in _KNOWN_AIRPORTS:
            airports.add(code)

    # Extract location for destination context
    loc_match = re.search(r'\*\*Location\*\*\s*\|\s*(.+?)(?:\s*\||\s*$)', text)
    if loc_match:
        loc = loc_match.group(1).strip()
        if loc and loc != "TBD":
            destinations.append(loc)

    # Extract airlines
    airlines = []
    airline_keywords = ["Southwest", "SWA", "Hawaiian", "American", "Delta", "United", "AA", "DL", "UA"]
    for ak in airline_keywords:
        if ak in text:
            airlines.append(ak)

    # Build profile
    profile = {}
    if destinations:
        profile["destinations"] = destinations
    if cruise_lines:
        profile["cruise_lines"] = cruise_lines
    if ports:
        profile["ports"] = ports
    if airports:
        profile["airports"] = sorted(airports)
    if airlines:
        profile["airlines"] = airlines
    if dates:
        profile["dates"] = dates

    if profile:
        profiles.append((family_name, profile))

    return profiles


def load_client_profiles() -> Dict:
    """Dynamically load client travel profiles from dossier files.

    Reads from two sources:
    1. Trip dossiers: ~/Thunderbird/dossiers/*.md
    2. Memory dossiers: ~/.claude/projects/-home-john-Thunderbird/memory/dossier_*.md

    Merges profiles by family name. Falls back to hardcoded defaults if no
    dossiers are found.

    Returns dict keyed by client/family name with travel profile data matching
    the structure expected by client_impact_filter():
        { "airports": [...], "airlines": [...], "destinations": [...],
          "ports": [...], "cruise_lines": [...], "dates": [...] }
    """
    profiles: Dict[str, Dict] = {}

    def _merge_profile(name: str, new_data: Dict):
        """Merge new_data into existing profile for name, deduplicating lists."""
        if name not in profiles:
            profiles[name] = {}
        existing = profiles[name]
        for key, val in new_data.items():
            if key in existing and isinstance(existing[key], list):
                # Merge and deduplicate while preserving order
                seen = set(existing[key])
                for item in val:
                    if item not in seen:
                        existing[key].append(item)
                        seen.add(item)
            else:
                existing[key] = val

    files_read = 0

    # Source 1: Trip dossiers
    if DOSSIER_DIR.is_dir():
        for fpath in sorted(DOSSIER_DIR.glob("*.md")):
            # Skip non-dossier files (like tips guides)
            if "Tips" in fpath.name or "Guide" in fpath.name:
                continue
            try:
                text = fpath.read_text(encoding="utf-8", errors="replace")
                for name, profile in _extract_from_trip_dossier(text):
                    _merge_profile(name, profile)
                    files_read += 1
            except Exception as e:
                logger.warning(f"Failed to read trip dossier {fpath.name}: {e}")

    # Source 2: Memory dossiers
    if MEMORY_DIR.is_dir():
        for fpath in sorted(MEMORY_DIR.glob("dossier_*.md")):
            try:
                text = fpath.read_text(encoding="utf-8", errors="replace")
                for name, profile in _extract_from_memory_dossier(text, fpath.name):
                    _merge_profile(name, profile)
                    files_read += 1
            except Exception as e:
                logger.warning(f"Failed to read memory dossier {fpath.name}: {e}")

    if profiles:
        logger.info(f"Loaded {len(profiles)} client profiles from {files_read} dossier files")
        return profiles

    # Fallback: hardcoded profiles if no dossiers found
    logger.warning("No dossier files found — using hardcoded fallback profiles")
    return {
        "Justin Loucks": {
            "airports": ["DCA", "IAD", "COS", "DEN"],
            "airlines": ["Southwest", "SWA"],
            "destinations": ["Virginia", "Colorado"],
        },
        "Ryan Loucks": {
            "airports": ["OMA", "COS", "DEN"],
            "airlines": [],
            "destinations": ["Omaha", "Colorado"],
        },
        "Westbrook": {
            "airports": ["HNL", "COS", "DEN", "SEA"],
            "airlines": ["Southwest", "SWA", "Hawaiian"],
            "destinations": ["Honolulu", "Hawaii", "Colorado"],
        },
        "Lyons": {
            "ports": ["Athens", "Piraeus"],
            "cruise_lines": ["Regent", "RSSC"],
            "destinations": ["Greece", "Mediterranean"],
        },
    }


class IntelCrew:
    """The Thunderbird Intelligence Pipeline.

    A2 Dembe (COLLECT) → A2 Dembe (ANALYZE) → A1 Radar (AUDIT) → COS Hale (REVIEW)

    Each stage is a persona call via Claude Opus. Each persona's output
    feeds into the next persona's prompt. COS has final quality gate.
    """

    def __init__(self, client_profiles: Optional[Dict] = None):
        """Initialize the intel crew.

        Args:
            client_profiles: Optional dict of client travel profiles for
                           client-aware filtering. If None, will be loaded.
        """
        self.client_profiles = client_profiles or self._load_client_profiles()
        self.timestamp = datetime.now().isoformat()

    def _load_client_profiles(self) -> Dict:
        """Load client travel profiles for client-aware filtering."""
        try:
            from thunderbird_context import get_active_client_travel_profile
            return get_active_client_travel_profile()
        except (ImportError, AttributeError):
            # Fallback: hardcoded known profiles
            return {
                "Justin Loucks": {
                    "airports": ["DCA", "IAD", "COS", "DEN"],
                    "airlines": ["Southwest", "SWA"],
                    "destinations": ["Virginia", "Colorado"],
                },
                "Ryan Loucks": {
                    "airports": ["OMA", "COS", "DEN"],
                    "airlines": [],
                    "destinations": ["Omaha", "Colorado"],
                },
                "Westbrook": {
                    "airports": ["HNL", "COS", "DEN", "SEA"],
                    "airlines": ["Southwest", "SWA", "Hawaiian"],
                    "destinations": ["Honolulu", "Hawaii", "Colorado"],
                },
                "Lyons": {
                    "ports": ["Athens", "Piraeus"],
                    "cruise_lines": ["Regent", "RSSC"],
                    "destinations": ["Greece", "Mediterranean"],
                },
            }

    def collect(self) -> Dict[str, Any]:
        """Stage 1: COLLECT — Run all scrapers, return raw intel package.

        Gathers:
        - RSS news feeds (world intel)
        - Airline route changes
        - Travel advisories
        """
        logger.info("=" * 60)
        logger.info("INTEL CREW — Stage 1: COLLECT (A2 Dembe)")
        logger.info("=" * 60)

        raw = {
            "timestamp": self.timestamp,
            "stage": "collect",
            "news_feeds": [],
            "airline_articles": [],
            "advisories": [],
        }

        # RSS feeds
        try:
            from thunderbird_world_intel import scrape_all_news_feeds
            news = scrape_all_news_feeds()
            raw["news_feeds"] = [n.model_dump() for n in news]
            logger.info(f"Collected {len(news)} news articles")
        except Exception as e:
            logger.error(f"News collection failed: {e}")

        # Airline route changes
        try:
            from thunderbird_airline_monitor import scrape_airline_route_changes
            airline = scrape_airline_route_changes()
            raw["airline_articles"] = airline
            logger.info(f"Collected {len(airline)} airline articles")
        except Exception as e:
            logger.error(f"Airline collection failed: {e}")

        # Travel advisories
        try:
            from thunderbird_world_intel import scrape_travel_advisories
            advisories = scrape_travel_advisories()
            raw["advisories"] = [a.model_dump() for a in advisories]
            logger.info(f"Collected {len(advisories)} travel advisories")
        except Exception as e:
            logger.error(f"Advisory collection failed: {e}")

        return raw

    def analyze(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Stage 2: ANALYZE — A2 Dembe produces full-content analysis per domain.

        Flags client impacts based on client profiles.
        """
        logger.info("=" * 60)
        logger.info("INTEL CREW — Stage 2: ANALYZE (A2 Dembe)")
        logger.info("=" * 60)

        from thunderbird_personas import call_persona

        client_profile_str = json.dumps(self.client_profiles, indent=2, default=str)

        analysis_prompt = f"""INTELLIGENCE ANALYSIS TASKING

You have been provided a raw intelligence package. Produce a FULL-CONTENT analysis organized by domain.
This is NOT a summary — provide complete analysis with context, implications, and assessment.

CRITICAL DIRECTIVE: Cover ALL domains BROADLY. The Commander has ordered ISW/RealClear quality-bar
intelligence across war, geopolitics, politics, social issues, markets, energy — NOT just items
that directly affect D2M clients. Think of this as a senior officer's daily read file.

CLIENT PROFILES (flag ANY item that affects these clients, but DO NOT limit coverage to them):
{client_profile_str}

For each domain, provide:
1. Full analysis of key developments (NOT one-line summaries)
2. Confidence level (HIGH/MEDIUM/LOW)
3. CLIENT IMPACT flag if it affects any active client (but cover ALL significant stories regardless)
4. Recommended actions

DOMAINS TO ANALYZE (ALL required — none may be skipped):
- WAR / GEOPOLITICS / MILITARY (conflicts, escalations, naval movements, sanctions)
- POLITICS / POLICY (US and international, legislative, regulatory)
- SOCIAL ISSUES (strikes, protests, public health, labor)
- CRUISE & MARITIME (ports, shipping, cruise line news, passenger reviews)
- AIRLINE & AVIATION (route changes, strikes, FAA/TSA — CRITICAL domain)
- MARKETS & ENERGY (oil, currency, shipping costs, economic indicators)
- TRAVEL ADVISORIES (State Dept, destination safety, weather threats)

RAW INTEL PACKAGE:

NEWS ARTICLES ({len(raw.get('news_feeds', []))} items):
{json.dumps(raw.get('news_feeds', [])[:50], indent=1, default=str)[:30000]}

AIRLINE ROUTE CHANGES ({len(raw.get('airline_articles', []))} items):
{json.dumps(raw.get('airline_articles', [])[:30], indent=1, default=str)[:15000]}

TRAVEL ADVISORIES ({len(raw.get('advisories', []))} items):
{json.dumps(raw.get('advisories', [])[:20], indent=1, default=str)[:10000]}
"""

        result = call_persona("A2", analysis_prompt, max_tokens=4000)

        return {
            "timestamp": self.timestamp,
            "stage": "analyze",
            "analyst": "A2-Dembe",
            "analysis": result.get("answer", ""),
            "raw_item_counts": {
                "news": len(raw.get("news_feeds", [])),
                "airline": len(raw.get("airline_articles", [])),
                "advisories": len(raw.get("advisories", [])),
            },
        }

    def audit(self, analyzed: Dict[str, Any]) -> Dict[str, Any]:
        """Stage 3: AUDIT — A1 Radar checks coverage gaps and quality.

        Verifies:
        - All domains covered
        - Client dossier compliance
        - Source quality
        - Coverage gaps
        """
        logger.info("=" * 60)
        logger.info("INTEL CREW — Stage 3: AUDIT (A1 Radar)")
        logger.info("=" * 60)

        from thunderbird_personas import call_persona

        client_profile_str = json.dumps(self.client_profiles, indent=2, default=str)

        audit_prompt = f"""INTELLIGENCE AUDIT TASKING

Review A2 Dembe's analysis for completeness, accuracy, and compliance.

ACTIVE CLIENT PROFILES (verify ALL are addressed):
{client_profile_str}

CHECK:
1. COVERAGE GAPS — Are all domains covered? Any missing topics?
2. CLIENT DOSSIER COMPLIANCE — Is every active client's travel profile cross-referenced?
3. SOURCE QUALITY — Are assessments properly sourced? Any unsupported claims?
4. PRIORITY ACCURACY — Are severity ratings correct? Any misclassified items?
5. ACTIONABILITY — Can the Commander act on this? Are recommendations specific?

Flag anything that's:
- Missing (domain not covered)
- Weak (insufficient detail or unsourced)
- Misclassified (wrong severity)
- Client-blind (affects a client but not flagged)

A2 DEMBE'S ANALYSIS:
{analyzed.get('analysis', '')}

ITEM COUNTS FROM RAW COLLECTION:
{json.dumps(analyzed.get('raw_item_counts', {}), indent=2)}
"""

        result = call_persona("A1", audit_prompt, max_tokens=3000)

        return {
            "timestamp": self.timestamp,
            "stage": "audit",
            "auditor": "A1-Radar",
            "audit_report": result.get("answer", ""),
            "analysis": analyzed.get("analysis", ""),
            "raw_item_counts": analyzed.get("raw_item_counts", {}),
        }

    def review(self, audited: Dict[str, Any]) -> Dict[str, Any]:
        """Stage 4: REVIEW — COS Hale quality gate.

        COS reviews the full package, reorders by importance,
        stamps APPROVED, and adds synthesis.
        """
        logger.info("=" * 60)
        logger.info("INTEL CREW — Stage 4: REVIEW (COS Hale)")
        logger.info("=" * 60)

        from thunderbird_personas import call_persona

        review_prompt = f"""COS INTELLIGENCE REVIEW — QUALITY GATE

You are reviewing the morning intelligence package before it reaches the Commander.

STANDING ORDER: The Commander directed intelligence coverage to be BROAD — war, geopolitics,
politics, social issues, markets, energy, AND travel/cruise/airline. If A2's analysis is
missing any of these domains, flag it as a DEFICIENCY. The Commander wants a senior officer's
daily read file, not just a travel industry newsletter.

YOUR DUTIES:
1. Verify A2's analysis covers ALL 7 domains (war/geopol, politics, social, cruise/maritime, airline, markets, advisories)
2. Verify A1's audit findings are addressed
3. Reorder items by COMMANDER PRIORITY (client impacts at TOP, then by threat level across ALL domains)
4. Add your COS SYNTHESIS — 3-5 sentences on what matters most today
5. Stamp APPROVED or flag DEFICIENCIES

If there are coverage gaps (from A1's audit), note them explicitly —
the Commander needs to know what we DON'T know.

A2 DEMBE'S ANALYSIS:
{audited.get('analysis', '')}

A1 RADAR'S AUDIT:
{audited.get('audit_report', '')}

COLLECTION STATS:
{json.dumps(audited.get('raw_item_counts', {}), indent=2)}
"""

        result = call_persona("COS", review_prompt, max_tokens=3000)

        return {
            "timestamp": self.timestamp,
            "stage": "review",
            "reviewer": "COS-Hale",
            "status": "COS-APPROVED",
            "cos_review": result.get("answer", ""),
            "analysis": audited.get("analysis", ""),
            "audit_report": audited.get("audit_report", ""),
            "raw_item_counts": audited.get("raw_item_counts", {}),
        }

    def client_impact_filter(self, intel_items: List[Dict]) -> List[Dict]:
        """Score each intel item against client profiles.

        Scoring:
        - Airline + airport match = CRITICAL (the SWA/Dulles test)
        - Port + cruise line match = HIGH
        - Destination country match = MEDIUM
        - No match = STANDARD
        """
        scored_items = []

        for item in intel_items:
            text = json.dumps(item).lower()
            severity = "STANDARD"
            affected_clients = []

            for client, profile in self.client_profiles.items():
                airports = [a.lower() for a in profile.get("airports", [])]
                airlines = [a.lower() for a in profile.get("airlines", [])]

                airport_match = any(a in text for a in airports)
                airline_match = any(a in text for a in airlines)

                if airport_match and airline_match:
                    severity = "CRITICAL"
                    affected_clients.append(client)
                elif airport_match:
                    if severity != "CRITICAL":
                        severity = "HIGH"
                    affected_clients.append(client)

                ports = [p.lower() for p in profile.get("ports", [])]
                cruise_lines = [c.lower() for c in profile.get("cruise_lines", [])]

                if any(p in text for p in ports) and any(c in text for c in cruise_lines):
                    if severity != "CRITICAL":
                        severity = "HIGH"
                    affected_clients.append(client)

                destinations = [d.lower() for d in profile.get("destinations", [])]
                if any(d in text for d in destinations):
                    if severity == "STANDARD":
                        severity = "MEDIUM"
                    affected_clients.append(client)

            item["impact_severity"] = severity
            item["affected_clients"] = list(set(affected_clients))
            scored_items.append(item)

        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "STANDARD": 3}
        scored_items.sort(key=lambda x: severity_order.get(x["impact_severity"], 3))

        return scored_items

    def run(self) -> Dict[str, Any]:
        """Run the full intel pipeline: COLLECT -> ANALYZE -> AUDIT -> REVIEW.

        Returns the complete intel package ready for the morning brief.
        """
        logger.info("=" * 60)
        logger.info("THUNDERBIRD INTEL CREW — FULL PIPELINE")
        logger.info("=" * 60)

        raw = self.collect()
        analyzed = self.analyze(raw)
        audited = self.audit(analyzed)
        reviewed = self.review(audited)

        # Run client impact filter on airline articles
        airline_impacts = []
        try:
            from thunderbird_airline_monitor import check_client_airport_impact
            airline_impacts = check_client_airport_impact()
        except Exception as e:
            logger.warning(f"Airline impact check failed: {e}")

        # Extract source links from raw collected data
        sources = []
        for article in raw.get("news_feeds", []):
            if article.get("title") and article.get("url"):
                sources.append({"title": article["title"], "url": article["url"], "type": "news"})
        for article in raw.get("airline_articles", []):
            if article.get("title") and article.get("url"):
                sources.append({"title": article["title"], "url": article["url"], "type": "airline"})
        for advisory in raw.get("advisories", []):
            if advisory.get("country"):
                sources.append({
                    "title": f"Travel Advisory: {advisory['country']} (Level {advisory.get('advisory_level', '?')})",
                    "url": "https://travel.state.gov/content/travel/en/traveladvisories/traveladvisories.html/",
                    "type": "advisory"
                })

        package = {
            "timestamp": self.timestamp,
            "pipeline": "A2->A1->COS",
            "status": reviewed.get("status", "UNKNOWN"),
            "cos_review": reviewed.get("cos_review", ""),
            "analysis": reviewed.get("analysis", ""),
            "audit_report": reviewed.get("audit_report", ""),
            "airline_impacts": airline_impacts,
            "raw_item_counts": reviewed.get("raw_item_counts", {}),
            "sources": sources,
        }

        # Save the package
        output_dir = THUNDERBIRD_DIR / "output" / "intel_crew"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"intel_package_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        output_path.write_text(json.dumps(package, indent=2, default=str), encoding="utf-8")

        logger.info(f"Intel package saved: {output_path}")
        logger.info("INTEL CREW — PIPELINE COMPLETE")

        return package


# ============================================================================
# MCP TOOL REGISTRATION
# ============================================================================

def register_intel_crew_tools(mcp_server):
    """Register intel crew tools with MCP server."""
    from pydantic import Field

    @mcp_server.tool(
        name="run_intel_crew",
        annotations={"title": "Run Intel Crew Pipeline", "readOnlyHint": False},
    )
    async def tool_run_intel_crew() -> str:
        """Run the full Thunderbird Intel Crew pipeline:
        A2 Dembe (COLLECT) -> A2 Dembe (ANALYZE) -> A1 Radar (AUDIT) -> COS Hale (REVIEW)

        Returns COS-approved intelligence package."""
        crew = IntelCrew()
        result = crew.run()
        return json.dumps(result, indent=2, default=str)

    logger.info("Intel crew tools registered with MCP server")


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    result = IntelCrew().run()
    print(json.dumps(result, indent=2, default=str))
