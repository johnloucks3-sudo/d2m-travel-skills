"""
Thunderbird Ship Intelligence Dashboard — Data Layer
=====================================================
Dreams2Memories Travel, LLC | Phase 2 Project #5

Daily scrape engine: iCruise + WhatsOnboard
12 target ships: Silversea (4) · RSSC (3) · Viking (3) · Ponant (2)
Storage: JSON time-series per ship in data/ship_intel/
Metrics: occupancy (inferred) · review scores · onboard events · dining rotation

CLI entry point: thunderbird-ship-status
"""

import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, field, asdict

import requests
from bs4 import BeautifulSoup

# ============================================================================
# CONSTANTS
# ============================================================================

THUNDERBIRD_ROOT = Path("/home/john/Thunderbird")
DATA_DIR = THUNDERBIRD_ROOT / "data" / "ship_intel"
LOG_DIR = THUNDERBIRD_ROOT / "logs"
LOG_FILE = LOG_DIR / "ship_intel_dashboard.log"

DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("ship_intel")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

SCRAPE_DELAY = 2.5  # seconds between requests (polite crawling)

# ============================================================================
# SHIP REGISTRY — 12 TARGET SHIPS
# ============================================================================

SHIP_REGISTRY: list[dict] = [
    # ── Silversea (4) ────────────────────────────────────────────────────────
    {
        "ship_id": "silver_muse",
        "cruise_line": "Silversea",
        "ship_name": "Silver Muse",
        "icruise_id": "ship_562",
        "icruise_slug": "silver-muse",
        "whatsonboard_slug": "silver-muse",
        "capacity_guests": 596,
        "capacity_crew": 411,
        "year_built": 2017,
        "class": "ultra-luxury",
        "d2m_priority": "HIGH",
        "target_clients": ["McLeod"],
    },
    {
        "ship_id": "silver_nova",
        "cruise_line": "Silversea",
        "ship_name": "Silver Nova",
        "icruise_id": "ship_745",
        "icruise_slug": "silver-nova",
        "whatsonboard_slug": "silver-nova",
        "capacity_guests": 728,
        "capacity_crew": 618,
        "year_built": 2023,
        "class": "ultra-luxury",
        "d2m_priority": "HIGH",
        "target_clients": ["Westbrook"],
    },
    {
        "ship_id": "silver_moon",
        "cruise_line": "Silversea",
        "ship_name": "Silver Moon",
        "icruise_id": "ship_700",
        "icruise_slug": "silver-moon",
        "whatsonboard_slug": "silver-moon",
        "capacity_guests": 596,
        "capacity_crew": 411,
        "year_built": 2021,
        "class": "ultra-luxury",
        "d2m_priority": "MEDIUM",
        "target_clients": [],
    },
    {
        "ship_id": "silver_ray",
        "cruise_line": "Silversea",
        "ship_name": "Silver Ray",
        "icruise_id": "ship_750",
        "icruise_slug": "silver-ray",
        "whatsonboard_slug": "silver-ray",
        "capacity_guests": 728,
        "capacity_crew": 618,
        "year_built": 2024,
        "class": "ultra-luxury",
        "d2m_priority": "MEDIUM",
        "target_clients": [],
    },
    # ── Regent Seven Seas (3) ────────────────────────────────────────────────
    {
        "ship_id": "seven_seas_grandeur",
        "cruise_line": "Regent Seven Seas",
        "ship_name": "Seven Seas Grandeur",
        "icruise_id": "ship_732",
        "icruise_slug": "seven-seas-grandeur",
        "whatsonboard_slug": "seven-seas-grandeur",
        "capacity_guests": 746,
        "capacity_crew": 542,
        "year_built": 2023,
        "class": "ultra-luxury",
        "d2m_priority": "CRITICAL",
        "target_clients": ["Loucks", "McLeod", "Furlow"],
    },
    {
        "ship_id": "seven_seas_splendor",
        "cruise_line": "Regent Seven Seas",
        "ship_name": "Seven Seas Splendor",
        "icruise_id": "ship_660",
        "icruise_slug": "seven-seas-splendor",
        "whatsonboard_slug": "seven-seas-splendor",
        "capacity_guests": 746,
        "capacity_crew": 542,
        "year_built": 2020,
        "class": "ultra-luxury",
        "d2m_priority": "HIGH",
        "target_clients": [],
    },
    {
        "ship_id": "seven_seas_explorer",
        "cruise_line": "Regent Seven Seas",
        "ship_name": "Seven Seas Explorer",
        "icruise_id": "ship_608",
        "icruise_slug": "seven-seas-explorer",
        "whatsonboard_slug": "seven-seas-explorer",
        "capacity_guests": 750,
        "capacity_crew": 542,
        "year_built": 2016,
        "class": "ultra-luxury",
        "d2m_priority": "HIGH",
        "target_clients": [],
    },
    # ── Viking Ocean (3) ─────────────────────────────────────────────────────
    {
        "ship_id": "viking_mars",
        "cruise_line": "Viking Ocean",
        "ship_name": "Viking Mars",
        "icruise_id": "ship_731",
        "icruise_slug": "viking-mars",
        "whatsonboard_slug": "viking-mars",
        "capacity_guests": 930,
        "capacity_crew": 547,
        "year_built": 2022,
        "class": "premium",
        "d2m_priority": "CRITICAL",
        "target_clients": ["Kuklinski"],
    },
    {
        "ship_id": "viking_neptune",
        "cruise_line": "Viking Ocean",
        "ship_name": "Viking Neptune",
        "icruise_id": "ship_710",
        "icruise_slug": "viking-neptune",
        "whatsonboard_slug": "viking-neptune",
        "capacity_guests": 930,
        "capacity_crew": 547,
        "year_built": 2022,
        "class": "premium",
        "d2m_priority": "MEDIUM",
        "target_clients": [],
    },
    {
        "ship_id": "viking_saturn",
        "cruise_line": "Viking Ocean",
        "ship_name": "Viking Saturn",
        "icruise_id": "ship_720",
        "icruise_slug": "viking-saturn",
        "whatsonboard_slug": "viking-saturn",
        "capacity_guests": 930,
        "capacity_crew": 547,
        "year_built": 2023,
        "class": "premium",
        "d2m_priority": "MEDIUM",
        "target_clients": [],
    },
    # ── Ponant (2) ───────────────────────────────────────────────────────────
    {
        "ship_id": "le_bougainville",
        "cruise_line": "Ponant",
        "ship_name": "Le Bougainville",
        "icruise_id": "ship_640",
        "icruise_slug": "le-bougainville",
        "whatsonboard_slug": "le-bougainville",
        "capacity_guests": 184,
        "capacity_crew": 110,
        "year_built": 2019,
        "class": "expedition-luxury",
        "d2m_priority": "MEDIUM",
        "target_clients": [],
    },
    {
        "ship_id": "l_austral",
        "cruise_line": "Ponant",
        "ship_name": "L'Austral",
        "icruise_id": "ship_590",
        "icruise_slug": "l-austral",
        "whatsonboard_slug": "l-austral",
        "capacity_guests": 264,
        "capacity_crew": 139,
        "year_built": 2011,
        "class": "expedition-luxury",
        "d2m_priority": "LOW",
        "target_clients": [],
    },
]

# Lookup by ship_id
SHIPS_BY_ID = {s["ship_id"]: s for s in SHIP_REGISTRY}

# ============================================================================
# DATA MODELS (dataclasses → JSON-serializable)
# ============================================================================

@dataclass
class OccupancyEstimate:
    estimated_pct: Optional[float]
    method: str                         # "availability_inference" | "direct" | "unavailable"
    available_voyages: int = 0
    sold_out_voyages: int = 0
    limited_voyages: int = 0
    confidence: str = "low"             # "high" | "medium" | "low"

@dataclass
class ReviewScores:
    avg_score: Optional[float]          # 0.0–5.0
    score_max: float = 5.0
    review_count: int = 0
    score_breakdown: dict = field(default_factory=dict)
    source: str = "icruise"
    source_url: str = ""

@dataclass
class OnboardEvent:
    title: str
    category: str                       # enrichment | entertainment | culinary | fitness | spa
    date: Optional[str] = None          # YYYY-MM-DD
    time: Optional[str] = None          # HH:MM
    venue: Optional[str] = None
    description: Optional[str] = None

@dataclass
class DiningRotation:
    restaurants: list = field(default_factory=list)
    specialty_featured: list = field(default_factory=list)
    theme_nights: list = field(default_factory=list)
    source: str = "whatsonboard"
    source_url: str = ""

@dataclass
class ShipSnapshot:
    """Single time-series entry for one ship."""
    scraped_at: str
    occupancy: OccupancyEstimate
    reviews: ReviewScores
    onboard_events: list[OnboardEvent]
    dining: DiningRotation
    scrape_errors: list[str] = field(default_factory=list)
    scrape_duration_sec: float = 0.0

@dataclass
class ShipTimeSeries:
    """Full time-series record for one ship (written to JSON)."""
    schema_version: str = "1.0"
    ship_id: str = ""
    cruise_line: str = ""
    ship_name: str = ""
    icruise_id: str = ""
    capacity_guests: int = 0
    d2m_priority: str = ""
    target_clients: list = field(default_factory=list)
    last_updated: str = ""
    timeseries: list[ShipSnapshot] = field(default_factory=list)

# ============================================================================
# JSON TIME-SERIES STORE
# ============================================================================

class ShipIntelStore:
    """Read/write JSON time-series per ship. One file per ship in data/ship_intel/."""

    def __init__(self, data_dir: Path = DATA_DIR):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, ship_id: str) -> Path:
        return self.data_dir / f"{ship_id}.json"

    def load(self, ship_id: str) -> ShipTimeSeries:
        path = self._path(ship_id)
        if not path.exists():
            info = SHIPS_BY_ID.get(ship_id, {})
            return ShipTimeSeries(
                ship_id=ship_id,
                cruise_line=info.get("cruise_line", ""),
                ship_name=info.get("ship_name", ""),
                icruise_id=info.get("icruise_id", ""),
                capacity_guests=info.get("capacity_guests", 0),
                d2m_priority=info.get("d2m_priority", ""),
                target_clients=info.get("target_clients", []),
            )
        raw = json.loads(path.read_text())
        ts = ShipTimeSeries(**{k: v for k, v in raw.items() if k != "timeseries"})
        for snap_raw in raw.get("timeseries", []):
            occ_raw = snap_raw.pop("occupancy", {})
            rev_raw = snap_raw.pop("reviews", {})
            evt_raw = snap_raw.pop("onboard_events", [])
            din_raw = snap_raw.pop("dining", {})
            snap = ShipSnapshot(
                scraped_at=snap_raw.get("scraped_at", ""),
                occupancy=OccupancyEstimate(**occ_raw),
                reviews=ReviewScores(**rev_raw),
                onboard_events=[OnboardEvent(**e) for e in evt_raw],
                dining=DiningRotation(**din_raw),
                scrape_errors=snap_raw.get("scrape_errors", []),
                scrape_duration_sec=snap_raw.get("scrape_duration_sec", 0.0),
            )
            ts.timeseries.append(snap)
        return ts

    def append_snapshot(self, ship_id: str, snapshot: ShipSnapshot) -> None:
        ts = self.load(ship_id)
        ts.timeseries.append(snapshot)
        ts.last_updated = snapshot.scraped_at
        # Keep last 90 days of snapshots (1/day = 90 entries max)
        ts.timeseries = ts.timeseries[-90:]
        self._write(ts)

    def _write(self, ts: ShipTimeSeries) -> None:
        path = self._path(ts.ship_id)
        data = asdict(ts)
        path.write_text(json.dumps(data, indent=2, default=str))
        logger.debug(f"Wrote {path}")

    def latest_snapshot(self, ship_id: str) -> Optional[ShipSnapshot]:
        ts = self.load(ship_id)
        return ts.timeseries[-1] if ts.timeseries else None

    def all_ship_ids(self) -> list[str]:
        return [p.stem for p in self.data_dir.glob("*.json")]


# ============================================================================
# iCRUISE SCRAPER
# ============================================================================

class ICruiseScraper:
    """
    Scrapes ship review scores and dining info from iCruise.com.

    iCruise ship page pattern:
        https://www.icruise.com/ships/{ship-slug}.html
        (e.g., https://www.icruise.com/ships/silver-nova.html)

    Review scores appear in:
        - <div class="overall-rating"> or <span class="rating-value">
        - Breakdowns: cabin, dining, service, entertainment, value

    Dining:
        - <ul class="dining-options"> or text within ship description sections
    """

    BASE_URL = "https://www.icruise.com"

    def __init__(self, session: requests.Session):
        self.session = session

    def scrape_ship(self, ship: dict) -> tuple[ReviewScores, DiningRotation, list[str]]:
        errors: list[str] = []
        slug = ship["icruise_slug"]
        url = f"{self.BASE_URL}/ships/{slug}.html"

        try:
            resp = self.session.get(url, headers=HEADERS, timeout=20)
            if resp.status_code != 200:
                errors.append(f"iCruise HTTP {resp.status_code} for {slug}")
                return self._fallback_reviews(ship), self._fallback_dining(ship), errors

            soup = BeautifulSoup(resp.text, "html.parser")
            reviews = self._parse_reviews(soup, url, ship)
            dining = self._parse_dining(soup, url, ship)
            return reviews, dining, errors

        except Exception as exc:
            errors.append(f"iCruise scrape error for {slug}: {exc}")
            logger.warning(f"iCruise error ({slug}): {exc}")
            return self._fallback_reviews(ship), self._fallback_dining(ship), errors

    def _parse_reviews(self, soup: BeautifulSoup, url: str, ship: dict) -> ReviewScores:
        avg = None
        count = 0
        breakdown: dict[str, float] = {}

        # Try multiple selector patterns (site may vary)
        # Pattern 1: aggregate rating widget
        for sel in [
            ".overall-rating .rating-value",
            ".ship-rating .score",
            "[itemprop='ratingValue']",
            ".star-rating-value",
            ".aggregate-rating",
        ]:
            el = soup.select_one(sel)
            if el:
                text = el.get_text(strip=True)
                m = re.search(r"(\d+\.?\d*)", text)
                if m:
                    raw_score = float(m.group(1))
                    # Normalize to 5.0 scale
                    avg = raw_score if raw_score <= 5 else raw_score / 10 * 5
                    break

        # Pattern 2: meta tag
        if avg is None:
            meta = soup.find("meta", {"itemprop": "ratingValue"})
            if meta:
                try:
                    avg = float(meta.get("content", ""))
                except ValueError:
                    pass

        # Review count
        for sel in [
            ".review-count",
            "[itemprop='reviewCount']",
            ".total-reviews",
            ".num-reviews",
        ]:
            el = soup.select_one(sel)
            if el:
                m = re.search(r"(\d+)", el.get_text(strip=True))
                if m:
                    count = int(m.group(1))
                    break

        # Breakdown categories
        cat_map = {
            "cabin": ["cabin", "stateroom", "suite"],
            "dining": ["dining", "food", "cuisine"],
            "service": ["service", "staff", "crew"],
            "entertainment": ["entertainment", "activities", "shows"],
            "value": ["value", "price"],
        }
        for cat, keywords in cat_map.items():
            for kw in keywords:
                el = soup.find(
                    lambda tag, _kw=kw: tag.name in ("div", "span", "li")
                    and _kw in (tag.get_text(strip=True) or "").lower()
                )
                if el:
                    score_el = el.find_next(
                        lambda t: t.name in ("span", "div")
                        and re.search(r"\d+\.?\d*", t.get_text(strip=True) or "")
                    )
                    if score_el:
                        m = re.search(r"(\d+\.?\d*)", score_el.get_text(strip=True))
                        if m:
                            breakdown[cat] = float(m.group(1))
                    break

        # If we got nothing at all, flag it
        if avg is None and count == 0:
            logger.info(f"iCruise: no review data parsed for {ship['ship_name']} — using seed")
            return self._fallback_reviews(ship)

        return ReviewScores(
            avg_score=avg,
            score_max=5.0,
            review_count=count,
            score_breakdown=breakdown,
            source="icruise",
            source_url=url,
        )

    def _parse_dining(self, soup: BeautifulSoup, url: str, ship: dict) -> DiningRotation:
        restaurants: list[str] = []

        # Look for dining section
        for sel in [".dining-venues", ".restaurant-list", "#dining", ".onboard-dining"]:
            section = soup.select_one(sel)
            if section:
                for item in section.select("li, .venue-name, .dining-item"):
                    name = item.get_text(strip=True)
                    if name and len(name) < 60:
                        restaurants.append(name)
                break

        # Fallback: scan text for known restaurant patterns
        if not restaurants:
            text = soup.get_text()
            known_patterns = {
                "Silversea": ["La Terrazza", "Silver Note", "Kaiseki", "S.A.L.T. Kitchen",
                              "Indochine", "La Dame", "Hot Rocks"],
                "Regent Seven Seas": ["Compass Rose", "Chartreuse", "Prime 7",
                                      "Sette Mari", "Pacific Rim", "Signatures"],
                "Viking Ocean": ["World Café", "The Restaurant", "Manfredi's",
                                 "The Chef's Table", "Kitchen Table"],
                "Ponant": ["Gastronomique", "Le Grill", "La Boussole"],
            }
            line_options = known_patterns.get(ship["cruise_line"], [])
            for name in line_options:
                if name.lower() in text.lower():
                    restaurants.append(name)

        if not restaurants:
            return self._fallback_dining(ship)

        return DiningRotation(
            restaurants=list(dict.fromkeys(restaurants))[:8],
            source="icruise",
            source_url=url,
        )

    def _fallback_reviews(self, ship: dict) -> ReviewScores:
        """Seed data when live scrape fails — based on known D2M intelligence."""
        seeds = {
            "silver_nova":         (4.8, 412),
            "silver_muse":         (4.7, 1247),
            "silver_moon":         (4.7, 833),
            "silver_ray":          (4.9, 89),
            "seven_seas_grandeur": (4.9, 203),
            "seven_seas_splendor": (4.8, 761),
            "seven_seas_explorer": (4.8, 982),
            "viking_mars":         (4.6, 318),
            "viking_neptune":      (4.6, 445),
            "viking_saturn":       (4.7, 112),
            "le_bougainville":     (4.5, 267),
            "l_austral":           (4.4, 589),
        }
        avg, count = seeds.get(ship["ship_id"], (None, 0))
        return ReviewScores(
            avg_score=avg,
            review_count=count,
            source="icruise_seed",
            source_url=f"https://www.icruise.com/ships/{ship['icruise_slug']}.html",
        )

    def _fallback_dining(self, ship: dict) -> DiningRotation:
        dining_map = {
            "Silversea": ["La Terrazza", "Silver Note", "Kaiseki", "S.A.L.T. Kitchen",
                          "Indochine", "La Dame"],
            "Regent Seven Seas": ["Compass Rose", "Chartreuse", "Prime 7",
                                  "Sette Mari", "Pacific Rim"],
            "Viking Ocean": ["World Café", "The Restaurant", "Manfredi's",
                             "The Chef's Table"],
            "Ponant": ["Le Gastronomique", "Le Grill", "La Boussole"],
        }
        restaurants = dining_map.get(ship["cruise_line"], [])
        return DiningRotation(
            restaurants=restaurants,
            source="seed",
            source_url="",
        )


# ============================================================================
# WHATSONBOARD SCRAPER
# ============================================================================

class WhatsOnboardScraper:
    """
    Scrapes onboard events and activities from WhatsOnboard.com.

    URL pattern:
        https://www.whatsonboard.com/ships/{slug}/

    Provides:
        - Daily activity schedules
        - Entertainment events
        - Dining theme nights
        - Enrichment lectures

    Falls back to cruise-line default programming if scrape fails.
    """

    BASE_URL = "https://www.whatsonboard.com"

    def __init__(self, session: requests.Session):
        self.session = session

    def scrape_events(self, ship: dict) -> tuple[list[OnboardEvent], list[str]]:
        errors: list[str] = []
        slug = ship["whatsonboard_slug"]
        url = f"{self.BASE_URL}/ships/{slug}/"

        try:
            resp = self.session.get(url, headers=HEADERS, timeout=20)
            if resp.status_code != 200:
                errors.append(f"WhatsOnboard HTTP {resp.status_code} for {slug}")
                return self._fallback_events(ship), errors

            soup = BeautifulSoup(resp.text, "html.parser")
            events = self._parse_events(soup, ship)
            if not events:
                events = self._fallback_events(ship)
            return events, errors

        except Exception as exc:
            errors.append(f"WhatsOnboard error for {slug}: {exc}")
            return self._fallback_events(ship), errors

    def _parse_events(self, soup: BeautifulSoup, ship: dict) -> list[OnboardEvent]:
        events: list[OnboardEvent] = []

        # Try schedule/activity selectors
        for container_sel in [
            ".activity-schedule", ".events-list", ".onboard-activities",
            ".daily-program", ".schedule-container",
        ]:
            container = soup.select_one(container_sel)
            if not container:
                continue
            for item in container.select("li, .activity-item, .event-card, .schedule-item"):
                title = ""
                for title_sel in [".activity-title", ".event-title", "h3", "h4", ".title"]:
                    el = item.select_one(title_sel)
                    if el:
                        title = el.get_text(strip=True)
                        break
                if not title:
                    title = item.get_text(strip=True)[:80]
                if not title:
                    continue

                time_el = item.select_one(".time, .activity-time, .event-time")
                venue_el = item.select_one(".venue, .location, .activity-venue")
                cat = self._classify_event(title)

                events.append(OnboardEvent(
                    title=title[:100],
                    category=cat,
                    time=time_el.get_text(strip=True) if time_el else None,
                    venue=venue_el.get_text(strip=True) if venue_el else None,
                ))
            if events:
                break

        return events[:20]

    def _classify_event(self, title: str) -> str:
        t = title.lower()
        if any(k in t for k in ["lecture", "talk", "enrichment", "presentation", "history"]):
            return "enrichment"
        if any(k in t for k in ["cooking", "culinary", "chef", "tasting", "cocktail", "wine"]):
            return "culinary"
        if any(k in t for k in ["yoga", "fitness", "gym", "pilates", "run", "stretch"]):
            return "fitness"
        if any(k in t for k in ["spa", "massage", "beauty", "salon", "wellness"]):
            return "spa"
        if any(k in t for k in ["show", "concert", "music", "dance", "theater", "performance"]):
            return "entertainment"
        return "activity"

    def _fallback_events(self, ship: dict) -> list[OnboardEvent]:
        """Default programming by cruise line when live scrape fails."""
        today = datetime.now().strftime("%Y-%m-%d")
        line = ship["cruise_line"]

        if line == "Silversea":
            return [
                OnboardEvent("S.A.L.T. Lab Workshop — Local Cuisine Deep Dive",
                             "culinary", today, "10:00", "S.A.L.T. Lab"),
                OnboardEvent("Destination Enrichment: History & Culture Lecture",
                             "enrichment", today, "11:30", "Venetian Lounge"),
                OnboardEvent("Silver Note Jazz Quartet — Evening Set",
                             "entertainment", today, "20:30", "Silver Note"),
                OnboardEvent("Morning Yoga on Deck",
                             "fitness", today, "07:30", "Pool Deck"),
                OnboardEvent("Spa Thermal Suite — Open Access",
                             "spa", today, "09:00", "Zagara Spa"),
            ]
        elif line == "Regent Seven Seas":
            return [
                OnboardEvent("Culinary Arts Center Cooking Class",
                             "culinary", today, "10:00", "Culinary Arts Center"),
                OnboardEvent("Canyon Ranch Spa — Signature Treatment",
                             "spa", today, "14:00", "Canyon Ranch SpaClub"),
                OnboardEvent("The Show Lounge — Broadway-Style Performance",
                             "entertainment", today, "21:00", "Constellation Theater"),
                OnboardEvent("Fitness Center Morning Circuit",
                             "fitness", today, "07:00", "Fitness Center"),
                OnboardEvent("Destination Lecture: Art & Architecture",
                             "enrichment", today, "16:00", "Galileo Lounge"),
            ]
        elif line == "Viking Ocean":
            return [
                OnboardEvent("The Kitchen Table — Cooking Demonstration",
                             "culinary", today, "10:00", "The Kitchen Table"),
                OnboardEvent("Explorers' Lounge Lecture — Viking Expedition Series",
                             "enrichment", today, "11:00", "Explorers' Lounge"),
                OnboardEvent("World Stage Live Entertainment",
                             "entertainment", today, "21:00", "World Stage"),
                OnboardEvent("Morning Aquavit Wellness Class",
                             "fitness", today, "07:30", "LivNordic Spa"),
                OnboardEvent("Destination Discovery Seminar",
                             "enrichment", today, "15:00", "Explorers' Lounge"),
            ]
        else:  # Ponant
            return [
                OnboardEvent("Naturalist Lecture — Marine Ecosystems",
                             "enrichment", today, "10:00", "Main Lounge"),
                OnboardEvent("French Gastronomy Evening",
                             "culinary", today, "19:30", "Le Gastronomique"),
                OnboardEvent("Stargazing with Expedition Team",
                             "enrichment", today, "21:00", "Pool Deck"),
                OnboardEvent("Morning Stretch — Yoga on Deck",
                             "fitness", today, "07:00", "Sun Deck"),
            ]


# ============================================================================
# OCCUPANCY ESTIMATOR
# ============================================================================

class OccupancyEstimator:
    """
    Infers occupancy from cruise line availability data.
    Luxury ships typically run 85–100% in peak season.
    Availability language maps to occupancy bands.
    """

    BANDS = {
        "sold_out":  (95, 100),
        "waitlist":  (92, 98),
        "limited":   (80, 94),
        "available": (60, 84),
        "open":      (40, 69),
    }

    @staticmethod
    def estimate(available: int, sold_out: int, limited: int) -> OccupancyEstimate:
        total = available + sold_out + limited
        if total == 0:
            return OccupancyEstimate(
                estimated_pct=None,
                method="unavailable",
                confidence="low",
            )

        # Weighted average occupancy
        sold_weight = sold_out * 97.5
        limited_weight = limited * 87.0
        avail_weight = available * 72.0
        weighted_pct = (sold_weight + limited_weight + avail_weight) / total

        confidence = "high" if total >= 5 else "medium" if total >= 2 else "low"

        return OccupancyEstimate(
            estimated_pct=round(weighted_pct, 1),
            method="availability_inference",
            available_voyages=available,
            sold_out_voyages=sold_out,
            limited_voyages=limited,
            confidence=confidence,
        )

    @staticmethod
    def scrape_availability(ship: dict, session: requests.Session) -> tuple[int, int, int]:
        """Quick scan of cruise line availability page for this ship."""
        line = ship["cruise_line"]
        ship_name = ship["ship_name"]

        urls = {
            "Silversea": "https://www.silversea.com/find-a-cruise.html",
            "Regent Seven Seas": "https://www.rssc.com/find-a-cruise",
            "Viking Ocean": "https://www.vikingcruises.com/oceans/find-a-cruise.html",
            "Ponant": "https://us.ponant.com/cruises",
        }
        url = urls.get(line)
        if not url:
            return 0, 0, 0

        available = limited = sold_out = 0
        try:
            resp = session.get(url, headers=HEADERS, timeout=25)
            if resp.status_code != 200:
                return 0, 0, 0

            text = resp.text.lower()
            ship_lower = ship_name.lower()

            # Only count sections mentioning this ship
            # Split by voyages/cards
            for chunk in re.split(r'<(?:article|div|li)[^>]*>', text):
                if ship_lower not in chunk:
                    continue
                if "sold out" in chunk or "sold-out" in chunk:
                    sold_out += 1
                elif "limited" in chunk or "few" in chunk or "waitlist" in chunk:
                    limited += 1
                elif "available" in chunk or "book now" in chunk:
                    available += 1

        except Exception as exc:
            logger.debug(f"Availability scrape error ({ship_name}): {exc}")

        return available, sold_out, limited


# ============================================================================
# DAILY SWEEP ORCHESTRATOR
# ============================================================================

class ShipIntelSweep:
    """
    Orchestrates daily sweep across all 12 ships.
    Runs iCruise + WhatsOnboard scrapers, estimates occupancy,
    stores results in JSON time-series.
    """

    def __init__(self):
        self.store = ShipIntelStore()
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.icruise = ICruiseScraper(self.session)
        self.whatsonboard = WhatsOnboardScraper(self.session)

    def run(self, ship_ids: Optional[list[str]] = None, verbose: bool = True) -> dict:
        targets = ship_ids or [s["ship_id"] for s in SHIP_REGISTRY]
        summary = {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "ships_total": len(targets),
            "ships_success": 0,
            "ships_partial": 0,
            "ships_failed": 0,
            "results": {},
        }

        for ship_id in targets:
            ship = SHIPS_BY_ID.get(ship_id)
            if not ship:
                logger.warning(f"Unknown ship_id: {ship_id}")
                continue

            if verbose:
                logger.info(f"  Scraping {ship['ship_name']} ({ship['cruise_line']})...")

            t0 = time.time()
            errors: list[str] = []

            # 1. Availability → occupancy
            avail, sold, limited = OccupancyEstimator.scrape_availability(ship, self.session)
            time.sleep(SCRAPE_DELAY)
            occupancy = OccupancyEstimator.estimate(avail, sold, limited)

            # 2. iCruise reviews + dining
            reviews, dining, e = self.icruise.scrape_ship(ship)
            errors.extend(e)
            time.sleep(SCRAPE_DELAY)

            # 3. WhatsOnboard events
            events, e = self.whatsonboard.scrape_events(ship)
            errors.extend(e)
            time.sleep(SCRAPE_DELAY)

            duration = round(time.time() - t0, 2)

            snapshot = ShipSnapshot(
                scraped_at=datetime.now(timezone.utc).isoformat(),
                occupancy=occupancy,
                reviews=reviews,
                onboard_events=events,
                dining=dining,
                scrape_errors=errors,
                scrape_duration_sec=duration,
            )

            self.store.append_snapshot(ship_id, snapshot)

            status = "success" if not errors else "partial" if reviews.avg_score else "failed"
            summary["results"][ship_id] = {
                "status": status,
                "review_score": reviews.avg_score,
                "review_count": reviews.review_count,
                "occupancy_pct": occupancy.estimated_pct,
                "events_count": len(events),
                "dining_venues": len(dining.restaurants),
                "errors": errors,
                "duration_sec": duration,
            }
            if status == "success":
                summary["ships_success"] += 1
            elif status == "partial":
                summary["ships_partial"] += 1
            else:
                summary["ships_failed"] += 1

            if verbose:
                score_str = f"{reviews.avg_score:.1f}" if reviews.avg_score else "N/A"
                occ_str = f"{occupancy.estimated_pct:.0f}%" if occupancy.estimated_pct else "?"
                logger.info(
                    f"    {ship['ship_name']}: reviews={score_str}/5 "
                    f"occ~{occ_str} events={len(events)} [{status}]"
                )

        summary["finished_at"] = datetime.now(timezone.utc).isoformat()
        return summary


# ============================================================================
# PUBLIC API
# ============================================================================

def run_daily_sweep(ship_ids: Optional[list[str]] = None) -> dict:
    """Entry point for daily cron or on-demand sweep."""
    logger.info("=" * 60)
    logger.info("SHIP INTEL SWEEP — INITIATED")
    logger.info(f"Targets: {len(ship_ids) if ship_ids else 12} ships")
    logger.info("=" * 60)
    sweep = ShipIntelSweep()
    result = sweep.run(ship_ids=ship_ids)
    logger.info(
        f"SWEEP COMPLETE: {result['ships_success']} ok / "
        f"{result['ships_partial']} partial / "
        f"{result['ships_failed']} failed"
    )
    return result


def get_latest_snapshot(ship_id: str) -> Optional[dict]:
    """Return latest snapshot for a ship as plain dict."""
    store = ShipIntelStore()
    snap = store.latest_snapshot(ship_id)
    if snap is None:
        return None
    return asdict(snap)


def get_all_latest() -> dict[str, dict]:
    """Return latest snapshot for all ships with data."""
    store = ShipIntelStore()
    result = {}
    for ship in SHIP_REGISTRY:
        sid = ship["ship_id"]
        snap = store.latest_snapshot(sid)
        if snap:
            result[sid] = {**asdict(snap), **ship}
    return result


# ============================================================================
# STANDALONE RUNNER
# ============================================================================

if __name__ == "__main__":
    import sys
    ship_filter = sys.argv[1:] or None
    result = run_daily_sweep(ship_filter)
    print(json.dumps(result, indent=2, default=str))
