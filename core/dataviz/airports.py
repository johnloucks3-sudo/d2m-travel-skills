"""IATA airport coordinate lookup for great-circle route rendering.

Covers D2M's active routes (Regent/Silversea/Viking embarkation ports,
Centrav-quoted connections) plus major world hubs so any future route
resolves without a data update. Unknown codes degrade gracefully in
great_circle_map.py (label-only fallback) rather than raising.

Extend by adding a row: "XXX": (lat, lon, "City, Country").
"""
from __future__ import annotations

AIRPORTS: dict[str, tuple[float, float, str]] = {
    # --- D2M home / CONUS ---
    "DEN": (39.8617, -104.6732, "Denver, USA"),
    "COS": (38.8058, -104.7008, "Colorado Springs, USA"),
    "GRB": (44.4851, -88.1296, "Green Bay, USA"),
    "SNA": (33.6757, -117.8682, "Santa Ana, USA"),
    "FLL": (26.0726, -80.1527, "Fort Lauderdale, USA"),
    "MIA": (25.7959, -80.2870, "Miami, USA"),
    "ATL": (33.6407, -84.4277, "Atlanta, USA"),
    "ORD": (41.9742, -87.9073, "Chicago, USA"),
    "JFK": (40.6413, -73.7781, "New York, USA"),
    "EWR": (40.6895, -74.1745, "Newark, USA"),
    "IAD": (38.9531, -77.4565, "Washington Dulles, USA"),
    "LAX": (33.9416, -118.4085, "Los Angeles, USA"),
    "SFO": (37.6213, -122.3790, "San Francisco, USA"),
    "SEA": (47.4502, -122.3088, "Seattle, USA"),
    "DFW": (32.8998, -97.0403, "Dallas-Fort Worth, USA"),
    "IAH": (29.9902, -95.3368, "Houston, USA"),
    "MCO": (28.4312, -81.3081, "Orlando, USA"),
    "TPA": (27.9755, -82.5332, "Tampa, USA"),
    "BOS": (42.3656, -71.0096, "Boston, USA"),
    "PHX": (33.4352, -112.0101, "Phoenix, USA"),
    "HNL": (21.3187, -157.9224, "Honolulu, USA"),
    "SAN": (32.7338, -117.1933, "San Diego, USA"),
    "CUN": (21.0367, -86.8771, "Cancun, Mexico"),
    "YYZ": (43.6777, -79.6248, "Toronto, Canada"),

    # --- Transatlantic / European hubs ---
    "LHR": (51.4700, -0.4543, "London Heathrow, UK"),
    "LGW": (51.1481, -0.1903, "London Gatwick, UK"),
    "CDG": (49.0097, 2.5479, "Paris CDG, France"),
    "AMS": (52.3105, 4.7683, "Amsterdam, Netherlands"),
    "FRA": (50.0379, 8.5622, "Frankfurt, Germany"),
    "MUC": (48.3538, 11.7861, "Munich, Germany"),
    "ZRH": (47.4647, 8.5492, "Zurich, Switzerland"),
    "MAD": (40.4983, -3.5676, "Madrid, Spain"),
    "BCN": (41.2971, 2.0785, "Barcelona, Spain"),
    "LIS": (38.7813, -9.1359, "Lisbon, Portugal"),
    "FCO": (41.8003, 12.2389, "Rome Fiumicino, Italy"),
    "VCE": (45.5053, 12.3519, "Venice, Italy"),
    "MXP": (45.6306, 8.7281, "Milan Malpensa, Italy"),
    "ATH": (37.9364, 23.9445, "Athens, Greece"),
    "IST": (41.2753, 28.7519, "Istanbul, Turkey"),
    "KEF": (63.9850, -22.6056, "Reykjavik, Iceland"),
    "BGO": (60.2934, 5.2181, "Bergen, Norway"),
    "OSL": (60.1976, 11.1004, "Oslo, Norway"),
    "CPH": (55.6180, 12.6560, "Copenhagen, Denmark"),
    "ARN": (59.6519, 17.9186, "Stockholm Arlanda, Sweden"),
    "HEL": (60.3172, 24.9633, "Helsinki, Finland"),
    "DUB": (53.4213, -6.2701, "Dublin, Ireland"),
    "VIE": (48.1103, 16.5697, "Vienna, Austria"),
    "PRG": (50.1008, 14.2632, "Prague, Czechia"),
    "WAW": (52.1657, 20.9671, "Warsaw, Poland"),
    "NCE": (43.6584, 7.2159, "Nice, France"),
    "GVA": (46.2381, 6.1090, "Geneva, Switzerland"),
    "BRU": (50.9014, 4.4844, "Brussels, Belgium"),
    "LIN": (45.4451, 9.2767, "Milan Linate, Italy"),
    "NAP": (40.8860, 14.2908, "Naples, Italy"),
    "SVO": (55.9736, 37.4125, "Moscow Sheremetyevo, Russia"),
    "SAW": (40.8986, 29.3092, "Istanbul Sabiha Gokcen, Turkey"),

    # --- Warnemunde / Baltic / Scandi port-adjacent ---
    "HAM": (53.6304, 9.9882, "Hamburg, Germany"),
    "BER": (52.3667, 13.5033, "Berlin, Germany"),
    "GDN": (54.3776, 18.4662, "Gdansk, Poland"),
    "TLL": (59.4133, 24.8328, "Tallinn, Estonia"),
    "RIX": (56.9236, 23.9711, "Riga, Latvia"),

    # --- Med / cruise embarkation ---
    "PMI": (39.5517, 2.7388, "Palma de Mallorca, Spain"),
    "SPU": (43.5389, 16.2981, "Split, Croatia"),
    "DBV": (42.5614, 18.2682, "Dubrovnik, Croatia"),
    "TIA": (41.4147, 19.7206, "Tirana, Albania"),
    "KTR": (35.3396, 24.1497, "Heraklion Crete, Greece"),
    "JTR": (36.4114, 25.4793, "Santorini, Greece"),
    "JMK": (37.4351, 25.3481, "Mykonos, Greece"),

    # --- Middle East / long-haul connectors ---
    "DXB": (25.2532, 55.3657, "Dubai, UAE"),
    "AUH": (24.4330, 54.6511, "Abu Dhabi, UAE"),
    "DOH": (25.2731, 51.6081, "Doha, Qatar"),

    # --- Asia-Pacific ---
    "NRT": (35.7647, 140.3864, "Tokyo Narita, Japan"),
    "HND": (35.5494, 139.7798, "Tokyo Haneda, Japan"),
    "ICN": (37.4602, 126.4407, "Seoul Incheon, South Korea"),
    "SIN": (1.3644, 103.9915, "Singapore"),
    "HKG": (22.3080, 113.9185, "Hong Kong"),
    "SYD": (-33.9399, 151.1753, "Sydney, Australia"),
    "AKL": (-37.0082, 174.7850, "Auckland, New Zealand"),
    "BKK": (13.6900, 100.7501, "Bangkok, Thailand"),

    # --- South America / Caribbean ---
    "GRU": (-23.4356, -46.4731, "Sao Paulo, Brazil"),
    "EZE": (-34.8222, -58.5358, "Buenos Aires, Argentina"),
    "SJU": (18.4394, -66.0018, "San Juan, Puerto Rico"),
    "NAS": (25.0389, -77.4661, "Nassau, Bahamas"),
    "MBJ": (18.5037, -77.9134, "Montego Bay, Jamaica"),
}


def lookup(iata: str) -> tuple[float, float, str] | None:
    """Return (lat, lon, label) for an IATA code, or None if not in the table."""
    return AIRPORTS.get(iata.strip().upper())


def known_codes() -> list[str]:
    return sorted(AIRPORTS.keys())
