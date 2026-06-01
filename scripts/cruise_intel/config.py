"""
Cruise Intel Pipeline — Configuration
All constants, region keywords, ship-to-line mappings, and API endpoints.
"""
from pathlib import Path

# ── Output paths ──────────────────────────────────────────────────────────────
OUTPUT_DIR = Path("/home/john/Thunderbird/output")
DATA_DIR = Path("/home/john/Thunderbird/scripts/cruise_intel/data")

MASTER_CSV = OUTPUT_DIR / "T2_MASTER_CRUISE_OCTOBER_NOVEMBER_2026.csv"
STATS_JSON = OUTPUT_DIR / "T2_STATS.json"
DELUXE_JSON = OUTPUT_DIR / "T2_EXERCISE_DEMBE_CRUISE_INTELLIGENCE.json"
OAT_JSON = OUTPUT_DIR / "T2_OAT_SOURCE_DATA.json"
PERX_JSON = OUTPUT_DIR / "T2_PERX_COMBINED.json"
PONANT_RAW_JSON = OUTPUT_DIR / "T2_PONANT_PARSED.json"
PONANT_CLEAN_JSON = OUTPUT_DIR / "T2_PONANT_CLEAN.json"

# ── New native sources (Wave 2 — 2026-05-24) ──────────────────────────────────
HX_JSON        = OUTPUT_DIR / "T2_HX_EXPEDITIONS.json"
SEADREAM_JSON  = OUTPUT_DIR / "T2_SEADREAM_YACHTCLUB.json"
EXPLORA_JSON   = OUTPUT_DIR / "T2_EXPLORA_JOURNEYS.json"

# ── Aggregator sources (Wave 3 — 2026-05-24) ──────────────────────────────────
CRUISEMAPPER_JSON = OUTPUT_DIR / "T2_CRUISEMAPPER.json"
CRUISESONLY_JSON  = OUTPUT_DIR / "T2_CRUISESONLY.json"
CRUISEPLUM_JSON   = OUTPUT_DIR / "T2_CRUISEPLUM.json"

# ── Browser binary ─────────────────────────────────────────────────────────────
GSTACK_BIN = Path.home() / ".claude/skills/gstack/browse/dist/browse"

# ── Perx / sail-personalize.com API ────────────────────────────────────────────
PERX_API_URL = "https://api.sail-personalize.com/v1/search/cruises"
PERX_API_ORIGIN = "https://www.perx.com"
PERX_API_REFERER = "https://www.perx.com/"

# Regions to query — one API call per region
PERX_REGIONS = [
    {"name": "Europe",               "region_id": "europe"},
    {"name": "Mediterranean",        "region_id": "mediterranean"},
    {"name": "Arctic / Scandinavia", "region_id": "arctic"},
    {"name": "British Isles",        "region_id": "british_isles"},
    {"name": "Transatlantic",        "region_id": "transatlantic"},
]

# ── OAT trip slugs (European/Med/Arctic only) ──────────────────────────────────
OAT_BASE_URL = "https://www.oattravel.com/trips/small-ship-adventures"
OAT_EURO_TRIPS = [
    ("mediterranean", "treasures-of-the-aegean-greek-island-cruise-athens-and-istanbul",
     "The Aegean Islands, Athens & Istanbul"),
    ("mediterranean", "hidden-gems-of-the-dalmatian-coast-and-greece",
     "Hidden Gems of the Dalmatian Coast & Greece"),
    ("europe", "allure-of-the-adriatic-italy-and-croatia",    "Allure of the Adriatic"),
    ("europe", "iberian-voyage-libson-to-barcelona",          "Iberian Voyage: Lisbon to Barcelona"),
    ("europe", "athens-and-ionian-sea-voyage-from-greece-to-albania", "Athens & Ionian Sea Voyage"),
    ("europe", "jewels-of-the-sicilian-coast-palermo-siracusa-and-mount-etna",
     "Jewels of the Sicilian Coast"),
    ("mediterranean", "cruising-the-adriatic-croatia-montenegro-bosnia-and-herzegovina",
     "Cruising the Adriatic"),
    ("mediterranean", "mediterranean-cultures-and-islands-a-voyage-from-barcelona-to-athens",
     "Mediterranean Cultures & Islands"),
    ("europe", "undiscovered-adriatic-eastern-italy-venice-puglia-and-malta",
     "Undiscovered Adriatic"),
    ("europe", "croatia-italy-cruise",                        "Croatia-Italy Cruise"),
    ("mediterranean", "mediterranean-navigation-malta-sicily-tunisia-algeria-morocco-spain",
     "Mediterranean Navigation"),
    ("europe", "maritime-jewels-of-the-british-isles-and-ireland",
     "Maritime Jewels of the British Isles & Ireland"),
    ("europe", "italian-coastal-odyssey-hidden-italy-sicily-malta", "Italian Coastal Odyssey"),
    ("europe", "grand-baltic-sea-voyage",                     "Grand Baltic Sea Voyage"),
    ("europe", "cruising-the-amalfi-coast",                   "Cruising the Amalfi Coast"),
    ("europe", "winter-france-italy-cruise",                  "Winter France-Italy Cruise"),
    ("mediterranean", "turkish-coastal-voyage-greek-islands-istanbul-and-athens",
     "Turkish Coastal Voyage"),
    ("europe", "svalbard-circumnavigation-arctic-expedition",
     "Svalbard Circumnavigation Arctic Expedition"),
    ("europe", "norwegian-fjord-cruise-and-scotlands-orkney-shetland-islands",
     "Norwegian Fjord Cruise"),
    ("europe", "italy-western-coast-islands-a-voyage-from-rome-to-valletta",
     "Italy Western Coast Islands"),
    ("europe", "untamed-svalbard-an-arctic-expedition",       "Untamed Svalbard Arctic Expedition"),
    ("mediterranean", "aegean-island-cruise",                 "Aegean Island Cruise"),
    ("europe", "coastlines-of-portugal-spain-morocco",        "Coastlines of Portugal, Spain & Morocco"),
    ("mediterranean", "french-and-italian-rivieras-marseille-corsica-elba-and-rome",
     "French & Italian Rivieras"),
    ("europe", "cruising-northern-europe-from-normandys-beaches-to-the-shores-of-scandinavia",
     "Cruising Northern Europe"),
    ("mediterranean", "greece-cruise",                        "Greece Cruise"),
]

# ── Ponant URL pattern ─────────────────────────────────────────────────────────
PONANT_BASE_URL = "https://us.ponant.com/travel-in/{year}/{month}"

# Transatlantic exceptions to add back even if they have excluded ports
# (voyages that originate or conclude in Europe are still valid)
PONANT_TRANSATLANTIC_EXCEPTIONS = [
    {"ship": "Le Boréal", "departure_date": "2026-10-24",
     "from_port": "Lisbon", "to_port": "Buenos Aires",
     "nights": "19", "route": "Lisbon to Buenos Aires",
     "name": "Ocean Voyage: Lisbon - Buenos Aires"},
]

# Ports that disqualify a Ponant voyage from the Euro/Med/Arctic filter
PONANT_EXCLUDE_PORTS = [
    'fort-de-france', 'martinique', 'colón', 'colon', 'panama',
    'ushuaia', 'dakar', 'caribbean', 'buenos aires',
]

# ── deluxecruises.com URL pattern ─────────────────────────────────────────────
DELUXE_BASE_URL = "https://www.deluxecruises.com/{line}/cruises/{month}-{year}.htm"
DELUXE_CRUISE_LINES = [
    "silversea", "regent-seven-seas", "seabourn", "oceania",
    "crystal", "azamara", "windstar", "ponant", "paul-gauguin",
    "viking", "cunard", "atlas-ocean",
]

# ── Canonical cruise line name normalization ───────────────────────────────────
# Maps scraped variants → canonical name used throughout the pipeline.
# Applied in build_master.py after all source ingestion.
LINE_CANONICAL = {
    'Oceania':              'Oceania Cruises',
    'Regent Seven Seas':    'Regent Seven Seas Cruises',
    'Viking Ocean':         'Viking',
    'Viking River':         'Viking',
    'Atlas Ocean':          'Atlas Ocean Voyages',
}

# ── Region keyword filter (Euro/Med/Arctic) ────────────────────────────────────
EUROPE_MED_KEYWORDS = [
    'italy','greece','spain','portugal','france','malta','turkey',
    'croatia','iceland','norway','sweden','denmark','finland',
    'ireland','scotland','england','uk','netherlands','belgium',
    'germany','poland','russia','estonia','latvia','lithuania',
    'athens','rome','barcelona','lisbon','valletta','civitavecchia',
    'naples','venice','dubrovnik','santorini','mykonos','mediterranean',
    'aegean','adriatic','canary islands','las palmas','tenerife',
    'atlantic islands','cape verde','madeira','azores',
    'oslo','bergen','reykjavik','tromsø','svalbard','longyearbyen',
    'arctic','greenland','faroe','spitsbergen',
    'cadiz','malaga','marseille','nice','monaco',
    'genoa','livorno','palma','ibiza','cartagena','alicante',
    'piraeus','thessaloniki','istanbul','heraklion','corfu',
    'stockholm','copenhagen','helsinki','riga','tallinn',
    'southampton','portsmouth','dover','amsterdam','hamburg',
    'le havre','brest','bordeaux','bilbao','st. petersburg',
    'sicily','sardinia','mallorca','peloponnese',
    'northern europe','scandinavia','baltic',
]

# ── Ship-to-cruise-line fallback map ──────────────────────────────────────────
SHIP_LINE_MAP = {
    'Explora':                  'Explora Journeys',
    'Princess':                 'Princess Cruises',
    'ms Nieuw':                 'Holland America Line',
    'ms Oosterdam':             'Holland America Line',
    'ms Rotterdam':             'Holland America Line',
    'ms Volendam':              'Holland America Line',
    'Explorer of the Seas':     'Royal Caribbean',
    'Odyssey of the Seas':      'Royal Caribbean',
    'Wonder of the Seas':       'Royal Caribbean',
    'Star Clipper':             'Star Clippers',
    'Star Flyer':               'Star Clippers',
    'Royal Clipper':            'Star Clippers',
    'Scarlet Lady':             'Virgin Voyages',
    'Valiant Lady':             'Virgin Voyages',
    'Emerald':                  'Emerald Cruises',
    'Scenic Eclipse':           'Scenic',
    'Carnival':                 'Carnival Cruise Line',
    'National Geographic':      'Lindblad Expeditions',
    'Silver':                   'Silversea',
    'Seven Seas':               'Regent Seven Seas Cruises',
    'Seabourn':                 'Seabourn',
    'Viking':                   'Viking',
    'Nautica':                  'Oceania Cruises',
    'Riviera':                  'Oceania Cruises',
    'Marina':                   'Oceania Cruises',
    'Le ': 'PONANT',
    'L\'Austral':               'PONANT',
    'Le Boréal':                'PONANT',
    'Le Champlain':             'PONANT',
    'Le Dumont':                'PONANT',
    'World Navigator':          'Atlas Ocean Voyages',
    'World Traveller':          'Atlas Ocean Voyages',
    'World Voyager':            'Atlas Ocean Voyages',
}

# ── CSV column order ───────────────────────────────────────────────────────────
CSV_COLUMNS = [
    'cruise_line', 'ship_name', 'departure_date', 'month', 'days',
    'route', 'voyage_code',
    'on_deluxecruises', 'on_perx', 'on_oat', 'on_ponant',
    'on_hx', 'on_seadream', 'on_explora',
    'on_cruisemapper', 'on_cruisesonly', 'on_cruiseplum',
    'price_usd',
]

# ── CruiseMapper line slugs (Wave 3 + Wave 4 expansion) ──────────────────────
# Maps display name → (slug-for-URL, canonical-cruise-line-name[, opts])
# Wave 4 lines confirmed by A2 Dembe 2026-05-27 from CruiseMapper directory
CRUISEMAPPER_LINES = {
    # ── Wave 3 — luxury core ──────────────────────────────────────────────────
    'Silversea':    ('Silversea-Cruises-19',             'Silversea'),
    'Seabourn':     ('Seabourn-Cruises-2',               'Seabourn'),
    'Regent':       ('Regent-Seven-Seas-Cruises-28',     'Regent Seven Seas Cruises'),
    'Cunard':       ('Cunard-31',                        'Cunard'),
    'Oceania':      ('Oceania-Cruises-29',               'Oceania Cruises'),
    'Viking':       ('Viking-Cruises-78',                'Viking'),
    'Ponant':       ('Ponant-Cruises-40',                'PONANT'),
    'Explora':      ('MSC-Explora-Journeys-125',         'Explora Journeys'),
    'Crystal':      ('Crystal-Cruises-17',               'Crystal'),
    'HX':           ('HX-Expeditions-129',               'HX Expeditions'),
    'SeaDream':     ('SeaDream-Yacht-Club-108',          'SeaDream Yacht Club'),
    # Vasco da Gama is Mystic Cruises (same parent co.) — exclude it; Atlas fleet is World Nav/Trav/Voy
    'Atlas':        ('Atlas-Ocean-Voyages-122',          'Atlas Ocean Voyages',
                     {'ship_includes': ['World Navigator', 'World Traveller', 'World Voyager']}),
    'Ritz-Carlton': ('Ritz-Carlton-Yacht-Collection-96', 'Ritz-Carlton Yacht Club'),
    'Scenic':       ('Scenic-Cruises-82',                'Scenic'),
    'Lindblad':     ('Lindblad-Expeditions-103',         'Lindblad Expeditions'),
    # ── Wave 4 — premium & expedition expansion ───────────────────────────────
    'Windstar':     ('Windstar-Cruises-30',              'Windstar Cruises'),
    'Azamara':      ('Azamara-Cruises-7',                'Azamara'),
    'StarClippers': ('Star-Clippers-118',                'Star Clippers'),
    'SwanHellenic': ('Swan-Hellenic-Cruises-123',        'Swan Hellenic'),
    'Hurtigruten':  ('Hurtigruten-45',                   'Hurtigruten'),
    'FredOlsen':    ('Fred-Olsen-Cruise-Lines-26',       'Fred. Olsen Cruise Lines'),
    'Celestyal':    ('Celestyal-Cruises-106',            'Celestyal Cruises'),
    'Emerald':      ('Emerald-Cruises-95',               'Emerald Cruises'),
    'Ambassador':   ('Ambassador-Cruise-Line-105',       'Ambassador Cruise Line'),
    'HapagLloyd':   ('Hapag-Lloyd-Cruises-104',          'Hapag-Lloyd Cruises'),
    'Aurora':       ('Aurora-Expeditions-132',           'Aurora Expeditions'),
    'Quark':        ('Quark-Expeditions-114',            'Quark Expeditions'),
    'Saga':         ('Saga-Cruises-27',                  'Saga Cruises'),
}

# ── CruisesOnly line slugs + search codes (Wave 3) ───────────────────────────
# Maps display name → (promotion-slug, search-code-or-None)
CRUISESONLY_LINES = {
    'Silversea': ('silversea-cruises',         50),
    'Seabourn':  ('seabourn-cruise-line',      None),
    'Regent':    ('regent-seven-seas-cruises', None),
    'Crystal':   ('crystal-cruises',           None),
    'Viking':    ('viking-ocean-cruises',      None),
    'Oceania':   ('oceania-cruises',           None),
    'Ponant':    ('ponant',                    None),
    'Azamara':   ('azamara',                   None),
    'Windstar':  ('windstar-cruises',          None),
}

# ── CruisePlum credentials (Wave 3) ──────────────────────────────────────────
# Scraper reads from env vars CRUISEPLUM_USER / CRUISEPLUM_PASS
# or from this file if it exists (format: USER=... / PASS=...)
CRUISEPLUM_CREDS_FILE = Path.home() / '.config' / 'd2m' / 'cruiseplum.env'

# ── Month name <-> number ──────────────────────────────────────────────────────
MONTH_MAP = {
    'January':1,'February':2,'March':3,'April':4,'May':5,'June':6,
    'July':7,'August':8,'September':9,'October':10,'November':11,'December':12,
    'Jan':1,'Feb':2,'Mar':3,'Apr':4,'Jun':6,'Jul':7,'Aug':8,
    'Sep':9,'Oct':10,'Nov':11,'Dec':12,
}


# ── T2 Re-scope: South Pacific / APAC Luxury (May/June 2028) ───────────────────
# Target: any sailing touching *at least one* of the listed ports (Papeete, Auckland, etc.)
# Lines: luxury + ultra-luxury only (filter applied at assembly in build_master)
# Usage: python3 run_pipeline.py --year 2028 --months 5 6 --tag may-june-2028-spac --no-xxx (skip slow)
TARGET_YEAR = 2028
TARGET_MONTHS = [5, 6]  # May, June 2028

TARGET_PORTS = [
    'papeete', 'tahiti',
    'auckland', 'sydney', 'melbourne',
    'singapore',
    # Reasonable regional context (increases recall without diluting luxury focus)
    'hobart', 'wellington', 'christchurch', 'port kembla', 'fremantle',
    'noumea', 'suva', 'port vila', 'moorea', 'bora bora',
]

LUXURY_ULTRA_LINES = {
    'Silversea',
    'Regent Seven Seas Cruises',
    'Seabourn',
    'Crystal',
    'PONANT',
    'Explora Journeys',
    'Scenic',
    'Ritz-Carlton Yacht Club',
    'Viking',                    # Ocean cruises (selective)
    'Oceania Cruises',
    'Azamara',
    'Windstar Cruises',
    'SeaDream Yacht Club',
    'Atlas Ocean Voyages',
    'Paul Gauguin Cruises',      # Tahiti specialist
    'Lindblad Expeditions',
}

# Recommended --tag for this re-scope
SPAC_TAG = 'may-june-2028-spac'
SPAC_MASTER_CSV = OUTPUT_DIR / f'T2_MASTER_{SPAC_TAG}.csv'
SPAC_REPORT   = OUTPUT_DIR / f'T2_CRUISE_REPORT_{SPAC_TAG}.html'
