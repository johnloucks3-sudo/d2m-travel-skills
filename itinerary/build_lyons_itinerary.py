#!/usr/bin/env python3
"""Build Lyons Seven Seas Splendor Itinerary HTML and PDF with D2M Dark Navy branding & Scraped Intel."""

import os
import json
import re
from pathlib import Path
from weasyprint import HTML
import base64
import mimetypes

OUT_DIR = Path("/home/john/Thunderbird/cruises_web")
OUT_DIR.mkdir(parents=True, exist_ok=True)

HTML_PATH = OUT_DIR / "itinerary_splendor_lyons.html"
PDF_PATH = OUT_DIR / "itinerary_splendor_lyons.pdf"

LOGO_URL = "https://lh3.googleusercontent.com/d/1HYa61cNwcialWk64DimGwIfCAbUjESsu"

IMAGES = {
    "flight": "https://images.pexels.com/photos/5778703/pexels-photo-5778703.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "athens": "https://images.pexels.com/photos/36825391/pexels-photo-36825391.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "athens_2": "https://images.pexels.com/photos/22679617/pexels-photo-22679617.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "splendor": "splendor.jpg",
    "splendor_deck": "splendor_pool.jpg",
    "splendor_lobby": "splendor_lobby.jpg",
    "splendor_dining": "splendor_dining.jpg",
    "splendor_pool": "splendor_pool.jpg",
    "splendor_spa": "splendor_spa.jpg",
    "valletta": "https://images.pexels.com/photos/33362891/pexels-photo-33362891.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "valletta_2": "https://images.pexels.com/photos/15042362/pexels-photo-15042362.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "naples": "https://images.pexels.com/photos/17855614/pexels-photo-17855614.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "naples_2": "https://images.pexels.com/photos/10229029/pexels-photo-10229029.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "rome": "https://images.pexels.com/photos/27541217/pexels-photo-27541217.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "rome_2": "https://images.pexels.com/photos/36132782/pexels-photo-36132782.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "tuscany": "https://images.pexels.com/photos/14515698/pexels-photo-14515698.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "tuscany_2": "https://images.pexels.com/photos/14515702/pexels-photo-14515702.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "cannes": "https://images.pexels.com/photos/13115905/pexels-photo-13115905.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "cannes_2": "https://images.pexels.com/photos/33972082/pexels-photo-33972082.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "barcelona": "https://images.pexels.com/photos/16984552/pexels-photo-16984552.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "barcelona_2": "https://images.pexels.com/photos/14793749/pexels-photo-14793749.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "sea_med": "https://images.pexels.com/photos/38218399/pexels-photo-38218399.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "malaga": "https://images.pexels.com/photos/22033738/pexels-photo-22033738.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "malaga_2": "https://images.pexels.com/photos/16753451/pexels-photo-16753451.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "portimao": "https://images.pexels.com/photos/16021278/pexels-photo-16021278.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "portimao_2": "https://images.pexels.com/photos/10537964/pexels-photo-10537964.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "lisbon": "https://images.pexels.com/photos/34967967/pexels-photo-34967967.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "lisbon_2": "https://images.pexels.com/photos/19240592/pexels-photo-19240592.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "sea_atl": "https://images.pexels.com/photos/28588328/pexels-photo-28588328.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "azores": "https://images.pexels.com/photos/33515018/pexels-photo-33515018.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "azores_2": "https://images.pexels.com/photos/29141707/pexels-photo-29141707.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "stjohns": "https://images.pexels.com/photos/4582564/pexels-photo-4582564.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "stjohns_2": "https://images.pexels.com/photos/23495711/pexels-photo-23495711.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "saintpierre": "https://images.pexels.com/photos/358737/nature-landscape-ocean-water-358737.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "saintpierre_2": "https://images.pexels.com/photos/17413631/pexels-photo-17413631.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "sydney": "https://images.pexels.com/photos/18709446/pexels-photo-18709446.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "sydney_2": "https://images.pexels.com/photos/18314147/pexels-photo-18314147.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "halifax": "https://images.pexels.com/photos/7623719/pexels-photo-7623719.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "halifax_2": "https://images.pexels.com/photos/10552283/pexels-photo-10552283.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "boston": "https://images.pexels.com/photos/27600024/pexels-photo-27600024.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "boston_2": "https://images.pexels.com/photos/35823347/pexels-photo-35823347.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "newport": "https://images.pexels.com/photos/34354721/pexels-photo-34354721.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "newport_2": "https://images.pexels.com/photos/34354722/pexels-photo-34354722.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "newyork": "https://images.pexels.com/photos/8569166/pexels-photo-8569166.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "newyork_2": "https://images.pexels.com/photos/28319629/pexels-photo-28319629.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940"
}

def encode_img(path):
    if path.startswith('http'):
        return path
    full_path = os.path.join('/home/john/Thunderbird/cruises_web', path)
    if os.path.exists(full_path):
        mime = mimetypes.guess_type(full_path)[0] or 'image/jpeg'
        with open(full_path, 'rb') as f:
            b64 = base64.b64encode(f.read()).decode('utf-8')
            return f"data:{mime};base64,{b64}"
    return path

for k, v in IMAGES.items():
    IMAGES[k] = encode_img(v)

# Load parsed dossier data
json_path = Path(__file__).parent / "dossier_data.json"
if json_path.exists():
    dossier_data = json.loads(json_path.read_text(encoding="utf-8"))
else:
    dossier_data = {"ship": {}, "ports": {}, "excursions": {}}

# Map correct port image URLs from the dossier where available
for pk, p_info in dossier_data.get("ports", {}).items():
    if p_info.get("img") and p_info["img"].startswith("http"):
        # Map port names to the IMAGES dict
        lower_pk = pk.lower().replace(" ", "").replace("'", "")
        if lower_pk in IMAGES:
            IMAGES[lower_pk] = p_info["img"]

DAYS = [
    {
        "day": None, "date": "Aug 9", "dow": "Sun", "type": "travel",
        "port": "JAX → DFW → ATH", "flag": "✈️",
        "sub": "AA 1061 (11:37 AM) / AA 216 (4:00 PM)",
        "note": "Nancy & Ken begin their grand luxury journey, flying first class across the Atlantic. Relax and toast to the historic horizons awaiting you.",
        "img": IMAGES["flight"]
    },
    {
        "day": None, "date": "Aug 10", "dow": "Mon", "type": "travel",
        "port": "Arrive Athens · GB Hotel", "flag": "🏛️",
        "sub": "Hotel Grande Bretagne (Marriott Luxury Collection)",
        "dining": {"name": "Grande Bretagne Roof Garden Restaurant", "time": "19:00"},
        "note": "Check into the legendary Grande Bretagne. Savor a romantic sunset dinner at the GB Roof Garden with views of the glowing Acropolis.",
        "img": IMAGES["athens"], "img2": IMAGES["athens_2"]
    },
    {
        "day": 1, "date": "Aug 11", "dow": "Tue", "type": "embark",
        "port": "Athens (Piraeus), Greece", "flag": "🇬🇷",
        "sub": "Seven Seas Splendor · Cabin 847 Serenity Suite F1",
        "note": "Step aboard the ultra-luxury Seven Seas Splendor. Toast with welcome champagne on your private balcony in Serenity Suite 847.",
        "img": IMAGES["splendor"], "img2": IMAGES["splendor_lobby"]
    },
    {
        "day": 2, "date": "Aug 12", "dow": "Wed", "type": "sea",
        "port": "Cruising the Mediterranean Sea", "flag": "🌊",
        "dining": {"name": "Pacific Rim", "time": "18:30"},
        "note": "A romantic day of leisure sailing the sapphire Mediterranean. Indulge in couples' spa treatments and a candlelit dinner.",
        "img": IMAGES["splendor_deck"], "img2": IMAGES["splendor_spa"]
    },
    {
        "day": 3, "date": "Aug 13", "dow": "Thu", "type": "port",
        "port": "Valletta, Malta", "flag": "🇲🇹",
        "sub": "8:00 AM – 3:00 PM",
        "exc": "Malta Attraction Pass", "time": "08:30",
        "note": "Wander the honey-colored limestone ramparts of Valletta hand-in-hand, overlooking the majestic azure harbor.",
        "img": IMAGES["valletta"], "img2": IMAGES["valletta_2"]
    },
    {
        "day": 4, "date": "Aug 14", "dow": "Fri", "type": "port",
        "port": "Naples, Italy", "flag": "🇮🇹",
        "sub": "12:00 PM – 8:30 PM",
        "exc": "Naples Exploring Above and Beyond", "time": "13:30",
        "note": "Sip limoncello with views of Vesuvius. Take a romantic excursion along the dramatic clifftops of the Amalfi Coast.",
        "img": IMAGES["naples"], "img2": IMAGES["naples_2"]
    },
    {
        "day": 5, "date": "Aug 15", "dow": "Sat", "type": "port",
        "port": "Rome (Civitavecchia), Italy", "flag": "🇮🇹",
        "sub": "8:30 AM – 8:30 PM",
        "exc": "A Taste of the Enchanting Tuscia", "time": "09:00",
        "note": "Explore the Eternal City together. Toss a coin into the Trevi Fountain, wishing for a lifetime of beautiful journeys.",
        "img": IMAGES["rome"], "img2": IMAGES["rome_2"]
    },
    {
        "day": 6, "date": "Aug 16", "dow": "Sun", "type": "port",
        "port": "Tuscany (Livorno), Italy", "flag": "🇮🇹",
        "sub": "8:00 AM – 8:00 PM",
        "exc": "Bolgheri & Wine Tasting", "time": "14:00",
        "note": "A private wine tasting in Bolgheri. Sip full-bodied reds amidst rolling vineyards, olive groves, and cypress-lined avenues.",
        "img": IMAGES["tuscany"], "img2": IMAGES["tuscany_2"]
    },
    {
        "day": 7, "date": "Aug 17", "dow": "Mon", "type": "port",
        "port": "Cannes, France ⚓", "flag": "🇫🇷",
        "sub": "7:00 AM – 6:00 PM",
        "exc": "Wine Tasting in Provence", "time": "09:00",
        "note": "Stroll the glamorous Croisette, share a seafood lunch by the yacht harbor, and toast with Provencal rosé under the French sun.",
        "img": IMAGES["cannes"], "img2": IMAGES["cannes_2"]
    },
    {
        "day": 8, "date": "Aug 18", "dow": "Tue", "type": "port",
        "port": "Barcelona, Spain", "flag": "🇪🇸",
        "sub": "Arrives 11:00 AM · Overnight",
        "exc": "GL-Barcelona's Neighborhood", "time": "10:00",
        "note": "An overnight stay in Catalonia's romantic capital. Walk the Gothic Quarter and watch the city lights flicker to life.",
        "img": IMAGES["barcelona"], "img2": IMAGES["barcelona_2"]
    },
    {
        "day": 9, "date": "Aug 19", "dow": "Wed", "type": "port",
        "port": "Barcelona, Spain", "flag": "🇪🇸",
        "sub": "Departs 10:00 PM",
        "exc": "Montjuic Treasures & Cable Car Ride", "time": "09:45",
        "dining": {"name": "Prime 7", "time": "18:30"},
        "note": "Enjoy a cable car ride over Montjuïc at sunset before returning to the harbor for late-night departures.",
        "img": IMAGES["barcelona"], "img2": IMAGES["barcelona_2"]
    },
    {
        "day": 10, "date": "Aug 20", "dow": "Thu", "type": "sea",
        "port": "Cruising the Mediterranean Sea", "flag": "🌊",
        "note": "Sailing toward the Atlantic. Cozy up on the deck as the Splendor glides through the historic Strait of Gibraltar.",
        "img": IMAGES["sea_med"], "img2": IMAGES["splendor_dining"]
    },
    {
        "day": 11, "date": "Aug 21", "dow": "Fri", "type": "port",
        "port": "Malaga, Spain", "flag": "🇪🇸",
        "sub": "8:00 AM – 8:00 PM",
        "exc": "Malaga City", "time": "08:30",
        "dining": {"name": "Chartreuse", "time": "18:30"},
        "note": "Explore the Moorish Alcazaba fortress and wander the sun-dappled plazas filled with the scent of jasmine.",
        "img": IMAGES["malaga"], "img2": IMAGES["malaga_2"]
    },
    {
        "day": 12, "date": "Aug 22", "dow": "Sat", "type": "port",
        "port": "Portimao, Portugal", "flag": "🇵🇹",
        "sub": "10:30 AM – 6:00 PM",
        "exc": "Cape St. Vincent, Sagres & Lagos", "time": "10:30",
        "note": "Witness the dramatic golden cliffs of Cape St. Vincent at the edge of Europe, where cliffs meet the open Atlantic.",
        "img": IMAGES["portimao"], "img2": IMAGES["portimao_2"]
    },
    {
        "day": 13, "date": "Aug 23", "dow": "Sun", "type": "port",
        "port": "Lisbon, Portugal", "flag": "🇵🇹",
        "sub": "Arrives 7:00 AM · Overnight",
        "exc": "Lisbon Tastes & Traditions", "time": "09:30",
        "note": "Lisbon overnight. Listen to soulful Fado music in the Alfama district and share warm, sweet Pastéis de Nata.",
        "img": IMAGES["lisbon"], "img2": IMAGES["lisbon_2"]
    },
    {
        "day": 14, "date": "Aug 24", "dow": "Mon", "type": "port",
        "port": "Lisbon, Portugal", "flag": "🇵🇹",
        "sub": "Departs 12:00 PM",
        "exc": "Scenic Sintra & Cascais", "time": "07:00",
        "note": "A morning excursion to the fairy-tale castles and romantic mountain palaces of Sintra before sailing.",
        "img": IMAGES["lisbon"], "img2": IMAGES["lisbon_2"]
    },
    {
        "day": 15, "date": "Aug 25", "dow": "sea", "type": "sea",
        "port": "Cruising the Atlantic Ocean", "flag": "🌊",
        "dining": {"name": "Prime 7", "time": "18:30"},
        "note": "Sailing west across the Atlantic. Relax on your private balcony, wrapped in sea breezes as the ship heads to the Azores.",
        "img": IMAGES["sea_atl"], "img2": IMAGES["splendor_pool"]
    },
    {
        "day": 16, "date": "Aug 26", "dow": "Wed", "type": "port",
        "port": "Ponta Delgada (Azores), Portugal", "flag": "🇵🇹",
        "sub": "10:00 AM – 7:00 PM",
        "exc": "A Taste of the Azores", "time": "14:00",
        "note": "Walk through lush pineapple plantations, emerald volcanic crater lakes, and exotic hot springs in this mid-ocean Eden.",
        "img": IMAGES["azores"], "img2": IMAGES["azores_2"]
    },
    {
        "day": 17, "date": "Aug 27", "dow": "Thu", "type": "sea",
        "port": "Cruising the Atlantic Ocean", "flag": "🌊",
        "note": "Transatlantic crossing day 1 of 3. Blissful serenity at sea. Savor late-morning breakfasts in your suite.",
        "img": IMAGES["splendor_deck"], "img2": IMAGES["splendor_lobby"]
    },
    {
        "day": 18, "date": "Aug 28", "dow": "Fri", "type": "sea",
        "port": "Cruising the Atlantic Ocean", "flag": "🌊",
        "dining": {"name": "Chartreuse", "time": "18:30"},
        "note": "Transatlantic crossing day 2 of 3. Read by the pool, enjoy afternoon tea, and dress up for elegant dining evenings.",
        "img": IMAGES["sea_atl"], "img2": IMAGES["splendor_dining"]
    },
    {
        "day": 19, "date": "Aug 29", "dow": "Sat", "type": "sea",
        "port": "Cruising the Atlantic Ocean", "flag": "🌊",
        "note": "Transatlantic crossing day 3 of 3. Stargaze from the top deck and feel the endless romance of the open ocean.",
        "img": IMAGES["splendor"], "img2": IMAGES["splendor_pool"]
    },
    {
        "day": 20, "date": "Aug 30", "dow": "Sun", "type": "port",
        "port": "St. John's, Newfoundland", "flag": "🇨🇦",
        "sub": "7:00 AM – 5:00 PM",
        "exc": "Explore the First City", "time": "09:30",
        "note": "Stand together on Signal Hill, watching the rugged North American cliffs meet the crashing waves.",
        "img": IMAGES["stjohns"], "img2": IMAGES["stjohns_2"]
    },
    {
        "day": 21, "date": "Aug 31", "dow": "Mon", "type": "port",
        "port": "Saint-Pierre, Miquelon", "flag": "🇵🇲",
        "sub": "8:00 AM – 5:00 PM",
        "exc": "Ile Aux Marins - Sailor's Island", "time": "08:45",
        "dining": {"name": "Pacific Rim", "time": "18:30"},
        "note": "A charming French island escape. Stroll the historic harbor and savor fresh croissants at an authentic local bakery.",
        "img": IMAGES["saintpierre"], "img2": IMAGES["saintpierre_2"]
    },
    {
        "day": 22, "date": "Sep 1", "dow": "Tue", "type": "port",
        "port": "Sydney, Nova Scotia", "flag": "🇨🇦",
        "sub": "8:00 AM – 5:00 PM",
        "exc": "Sydney Pub Tour", "time": "13:00",
        "note": "Experience the warm fiddle music and maritime hospitality of Cape Breton Island and taste fresh local seafood.",
        "img": IMAGES["sydney"], "img2": IMAGES["sydney_2"]
    },
    {
        "day": 23, "date": "Sep 2", "dow": "Wed", "type": "port",
        "port": "Halifax, Nova Scotia", "flag": "🇨🇦",
        "sub": "10:00 AM – 6:00 PM",
        "exc": "Tunnels, Tales and Mysteries of Georges", "time": "10:01",
        "note": "Stroll the historic waterfront boardwalk and take a scenic coastal drive to the romantic Peggy's Cove lighthouse.",
        "img": IMAGES["halifax"], "img2": IMAGES["halifax_2"]
    },
    {
        "day": 24, "date": "Sep 3", "dow": "Thu", "type": "port",
        "port": "Boston, Massachusetts", "flag": "🇺🇸",
        "sub": "Arrives 5:30 PM · Overnight",
        "note": "Evening arrival in Boston. Sip wine on deck and watch the historic harbor skyline light up for the night.",
        "img": IMAGES["boston"], "img2": IMAGES["boston_2"]
    },
    {
        "day": 25, "date": "Sep 4", "dow": "Fri", "type": "port",
        "port": "Boston, Massachusetts", "flag": "🇺🇸",
        "sub": "Departs 3:00 PM",
        "exc": "Freedom Trail Walker", "time": "09:30",
        "note": "Trace the footsteps of history on the Freedom Trail before heading back to the ship for an afternoon departure.",
        "img": IMAGES["boston"], "img2": IMAGES["boston_2"]
    },
    {
        "day": 26, "date": "Sep 5", "dow": "Sat", "type": "port",
        "port": "Newport, Rhode Island", "flag": "🇺🇸",
        "sub": "11:30 AM – 6:30 PM",
        "exc": "Vanderbilts Newport", "time": "12:30",
        "note": "Tour the breathtaking Vanderbilt Gilded Age mansions and take the stunning Cliff Walk overlooking the ocean.",
        "img": IMAGES["newport"], "img2": IMAGES["newport_2"]
    },
    {
        "day": 27, "date": "Sep 6", "dow": "Sun", "type": "disembark",
        "port": "New York · Disembark & Fly Home", "flag": "✈️",
        "sub": "DL 2005 LGA → JAX (12:29 PM – 3:01 PM)",
        "note": "Sail past the Statue of Liberty at sunrise. A breathtaking finale to a legendary voyage, before your private transfer home to JAX.",
        "img": IMAGES["newyork"], "img2": IMAGES["newyork_2"]
    }
]

OPEN_ITEMS = [
    {"icon": "🔑", "title": "Online Check-In", "desc": "Regent online check-in opens July 21, 2026.", "status": "PENDING"},
    {"icon": "🚗", "title": "Athens Arrival Transfer (Transfeero)", "desc": "8/10/2026 @ 12:20 PM: ATH Airport to Hotel Grande Bretagne (Confirmed)", "status": "CONFIRMED"},
    {"icon": "🚗", "title": "Embarkation Transfer (Transfeero)", "desc": "8/11/2026 @ 11:30 AM: Hotel Grande Bretagne to Seven Seas Splendor Port (Confirmed)", "status": "CONFIRMED"},
    {"icon": "🚗", "title": "Disembarkation Transfer (Transfeero)", "desc": "9/6/2026 @ 9:00 AM: Seven Seas Splendor Pier to LaGuardia (LGA) Airport (Confirmed)", "status": "CONFIRMED"},
    {"icon": "🚕", "title": "Return Home Transfer (Bob's Taxi)", "desc": "9/6/2026 @ 3:01 PM: JAX Airport to Home (Confirmed)", "status": "CONFIRMED"}
]

print("Building HTML...")

# Build HTML string
html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Seven Seas Splendor · Historic Horizons | Lyons</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
    font-family: 'Inter', system-ui, -apple-system, Georgia, serif;
    background-color: #04041b;
    color: #e8f1ff;
    padding: 28px 12px;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
}}
@page {{
    background-color: #04041b;
    margin: 10mm;
}}
.page {{
    max-width: 900px;
    margin: 0 auto;
    background-color: #08082e;
    background-image: linear-gradient(175deg, #090940 0%, #06062b 50%, #04041a 100%);
    border-radius: 16px;
    box-shadow: 0 12px 40px rgba(0,0,0,0.6);
    overflow: hidden;
}}
.hero {{
    background-color: #080838;
    background-image: linear-gradient(180deg, #0b0b4a 0%, #06062b 100%);
    text-align: center;
    padding: 40px 24px 30px;
    border-bottom: 3px solid #c8a400;
}}
.hero img.logo {{ display: inline-block; border: 0; width: 140px; height: auto; margin-bottom: 16px; }}
.wordmark {{ color: #f0f6ff; font-size: 11px; letter-spacing: 4px; margin-top: 4px; font-weight: normal; text-transform: uppercase; }}
.voyage-title {{ font-size: 28px; font-weight: 300; color: #f7f3ea; margin-top: 15px; letter-spacing: 1.5px; font-family: Georgia, serif; }}
.voyage-sub {{ font-size: 14px; color: rgba(255,255,255,.7); margin-top: 8px; font-style: italic; font-family: Georgia, serif; }}

.ship-profile {{
    background: rgba(200, 164, 0, 0.05);
    border-bottom: 1px solid rgba(200, 164, 0, 0.2);
    padding: 24px;
    display: flex;
    gap: 24px;
    align-items: center;
}}
.ship-profile img {{
    width: 250px;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    object-fit: cover;
}}
.ship-text {{ flex: 1; }}
.ship-text h2 {{ font-family: Georgia, serif; font-size: 20px; color: #c8a400; font-weight: 400; margin-bottom: 8px; }}
.ship-text p {{ font-size: 13px; line-height: 1.5; color: rgba(255,255,255,0.8); margin-bottom: 12px; }}
.ship-stats {{ display: flex; gap: 16px; font-size: 11px; color: #a8c4f0; flex-wrap: wrap; }}
.ship-stats span {{ background: rgba(255,255,255,0.05); padding: 4px 8px; border-radius: 4px; }}

.stats-bar {{
    background: rgba(0,0,0,.4);
    border-bottom: 1px solid rgba(200,164,0,.25);
    padding: 16px 24px;
    display: flex;
    justify-content: space-around;
    flex-wrap: wrap;
    gap: 16px;
}}
.stat {{ text-align: center; }}
.stat-val {{ font-size: 22px; font-weight: 600; color: #c8a400; font-family: Georgia, serif; }}
.stat-lbl {{ font-size: 9px; text-transform: uppercase; letter-spacing: 1.5px; color: rgba(255,255,255,.6); margin-top: 4px; }}

.ck-bar {{
    background: rgba(0,0,0,.2);
    border-bottom: 1px solid rgba(255,255,255,.1);
    padding: 12px 24px;
    font-size: 12px;
    color: #c8dcff;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 10px;
}}

.sec-header {{
    background: rgba(200,164,0,.08);
    border-top: 1px solid rgba(200,164,0,.25);
    border-bottom: 1px solid rgba(200,164,0,.25);
    padding: 14px 24px;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 2.5px;
    color: #c8a400;
    font-weight: 600;
    margin-top: 24px;
    margin-bottom: 16px;
}}

.itinerary-container {{
    padding: 0 16px 24px;
    display: flex;
    flex-direction: column;
    gap: 16px;
}}

.day-card {{
    background: rgba(255, 255, 255, 0.03);
    backdrop-filter: blur(8px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    transition: transform 0.2s, box-shadow 0.2s;
}}
.day-card:hover {{
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(0,0,0,0.3);
    background: rgba(255, 255, 255, 0.05);
}}
.day-card.embark {{ border-left: 4px solid #1a7a1a; }}
.day-card.disembark {{ border-left: 4px solid #8b0000; }}
.day-card.travel {{ border-left: 4px solid #c8a400; }}
.day-card.sea {{ border-left: 4px solid #2352b5; }}

.card-main {{
    display: flex;
    flex-wrap: nowrap;
}}
.card-left {{
    width: 90px;
    padding: 16px;
    text-align: center;
    border-right: 1px solid rgba(255,255,255,.05);
    background: rgba(0,0,0,0.2);
    display: flex;
    flex-direction: column;
    justify-content: center;
    flex-shrink: 0;
}}
.day-num {{ font-size: 24px; font-weight: bold; color: #c8a400; font-family: Georgia, serif; line-height: 1; }}
.day-dow {{ font-size: 10px; color: #c8dcff; text-transform: uppercase; letter-spacing: 1px; margin-top: 6px; }}
.date-mon {{ font-size: 10px; color: #a8c8ff; text-transform: uppercase; letter-spacing: 1px; margin-top: 8px; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 8px; }}
.date-day {{ font-size: 18px; font-weight: bold; color: #e8f1ff; margin-top: 2px; }}

.card-content {{
    flex: 1;
    padding: 16px 20px;
    display: flex;
    flex-direction: column;
    justify-content: center;
}}
.port-header {{
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;
}}
.port-flag {{ font-size: 20px; }}
.port-name {{ font-size: 16px; font-weight: 600; color: #f7f3ea; }}
.port-sub {{ font-size: 11px; color: #a8c4f0; margin-bottom: 12px; }}
.exc-block, .dining-block {{
    background: rgba(255,255,255,0.03);
    border-radius: 6px;
    padding: 8px 12px;
    margin-bottom: 8px;
    border-left: 2px solid #c8a400;
}}
.dining-block {{ border-left-color: #4CAF50; }}
.block-lbl {{ font-size: 9px; text-transform: uppercase; letter-spacing: 1px; color: rgba(255,255,255,0.5); margin-bottom: 2px; }}
.block-val {{ font-size: 13px; font-weight: 500; color: #e8f1ff; display: flex; justify-content: space-between; }}
.block-time {{ font-size: 11px; color: #c8a400; }}
.dining-block .block-time {{ color: #4CAF50; }}
.note-text {{ font-size: 12px; color: rgba(255,255,255,0.7); font-style: italic; margin-top: 4px; line-height: 1.4; }}

.card-images {{
    width: 220px;
    display: flex;
    flex-direction: column;
    border-left: 1px solid rgba(255,255,255,.05);
    flex-shrink: 0;
}}
.card-images img {{
    width: 100%;
    height: 110px;
    object-fit: cover;
}}

details.intel-dropdown {{
    border-top: 1px solid rgba(255,255,255,0.05);
    background: rgba(0,0,0,0.15);
}}
details.intel-dropdown summary {{
    padding: 12px 20px;
    font-size: 11px;
    color: #c8a400;
    text-transform: uppercase;
    letter-spacing: 1px;
    cursor: pointer;
    user-select: none;
    font-weight: 500;
    outline: none;
    transition: background 0.2s;
}}
details.intel-dropdown summary:hover {{ background: rgba(255,255,255,0.05); }}
details.intel-dropdown .intel-content {{
    padding: 16px 20px 20px;
    font-size: 13px;
    line-height: 1.6;
    color: rgba(255,255,255,0.85);
    border-top: 1px solid rgba(255,255,255,0.03);
}}
.intel-content p {{ margin-bottom: 12px; }}
.intel-content p:last-child {{ margin-bottom: 0; }}
.intel-tag {{
    display: inline-block;
    background: rgba(200, 164, 0, 0.15);
    color: #c8a400;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 10px;
    font-weight: 600;
    margin-right: 6px;
    text-transform: uppercase;
}}

.open-section {{
    border-top: 3px solid #c8a400;
    margin-top: 40px;
    background-color: #050524;
}}
.open-hdr {{
    background: rgba(200,164,0,.1);
    padding: 16px 24px;
    font-size: 14px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    color: #c8a400;
    border-bottom: 1px solid rgba(200,164,0,.2);
}}
.open-item {{
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 14px 24px;
    border-bottom: 1px solid rgba(255,255,255,.05);
    font-size: 12px;
}}
.open-item:last-child {{ border-bottom: none; }}
.open-icon {{ font-size: 20px; }}
.open-info {{ flex: 1; }}
.open-title {{ font-weight: 600; color: #f7f3ea; margin-bottom: 4px; }}
.open-desc {{ color: rgba(255,255,255,.7); }}
.open-status {{
    font-size: 9px;
    font-weight: bold;
    background: #8b6b00;
    color: #fff;
    padding: 4px 8px;
    border-radius: 4px;
    text-transform: uppercase;
}}

.footer {{
    background: #020214;
    padding: 30px;
    text-align: center;
    border-top: 1px solid rgba(255,255,255,.1);
    font-size: 12px;
    color: #8fa8d8;
}}
.footer a {{ color: #a8c4f0; text-decoration: none; }}

/* Responsive styling for iPhone and iPad */
@media (max-width: 768px) {{
    body {{
        padding: 14px 6px;
    }}
    .hero {{
        padding: 30px 16px 20px;
    }}
    .voyage-title {{
        font-size: 22px;
    }}
    .voyage-sub {{
        font-size: 12px;
    }}
    .ship-profile {{
        flex-direction: column;
        text-align: center;
        padding: 16px;
    }}
    .ship-profile img {{
        width: 100%;
        max-width: 320px;
    }}
    .stats-bar {{
        padding: 12px;
    }}
    .stat-val {{
        font-size: 18px;
    }}
    .ck-bar {{
        flex-direction: column;
        align-items: flex-start;
        gap: 6px;
        padding: 12px 16px;
    }}
    .card-main {{
        flex-direction: column;
    }}
    .card-left {{
        width: 100%;
        border-right: none;
        border-bottom: 1px solid rgba(255,255,255,.05);
        flex-direction: row;
        justify-content: space-around;
        align-items: center;
        padding: 10px 16px;
        background: rgba(0,0,0,0.3);
    }}
    .date-mon {{
        margin-top: 0;
        border-top: none;
        padding-top: 0;
    }}
    .card-content {{
        padding: 16px;
    }}
    .card-images {{
        width: 100%;
        border-left: none;
        border-top: 1px solid rgba(255,255,255,.05);
        flex-direction: row;
    }}
    .card-images img {{
        width: 50%;
        height: 120px;
    }}
}}

/* Selective print styling for a clean, slimmed-down PDF */
@media print {{
    body {{ 
        background: #04041b !important; 
        color: #e8f1ff !important;
        padding: 0 !important;
        -webkit-print-color-adjust: exact; 
    }}
    .page {{
        box-shadow: none !important;
        border-radius: 0 !important;
        background: #08082e !important;
    }}
    .day-card {{ 
        page-break-inside: avoid; 
        border: 1px solid rgba(255,255,255,0.15) !important; 
        margin-bottom: 12px !important; 
        background: rgba(255,255,255,0.02) !important;
    }}
    
    /* SLIMMED DOWN PDF: Hide the long destination and excursion deep-dives */
    details.intel-dropdown {{ 
        display: none !important; 
    }}
    
    /* Optimize images in print so they don't consume too much toner and space */
    .card-images {{
        width: 160px !important;
    }}
    .card-images img {{
        height: 80px !important;
    }}
}}
</style>
</head>
<body>

<div class="page">
    <!-- HERO HEADER -->
    <div class="hero">
        <img src="{LOGO_URL}" class="logo" alt="D2M Logo">
        <div class="wordmark">DREAMS2MEMORIES TRAVEL, LLC</div>
        <div class="voyage-title">Seven Seas Splendor &middot; Historic Horizons</div>
        <div class="voyage-sub">Athens (Piraeus) to New York &middot; August 11 &ndash; September 6, 2026</div>
    </div>

    <!-- SHIP PROFILE INJECTION -->
    <div class="ship-profile">
        <img src="{IMAGES['splendor']}" alt="Seven Seas Splendor">
        <div class="ship-text">
            <h2>Seven Seas Splendor</h2>
            <p>The epitome of luxury perfected. Every room onboard is a suite offering a private furnished balcony, marble-and-stone bathrooms, and 24-hour in-suite dining. With over an acre of Italian marble and 500 crystal chandeliers, it offers an unrivaled all-inclusive experience.</p>
            <div class="ship-stats" style="margin-bottom: 12px;">
                <span>⭐ Serenity Suite (F1) #847</span>
                <span>🍽️ 7 Specialty Dining Venues</span>
                <span>🌊 735ft Length</span>
                <span>🧖‍♀️ Serene Spa & Wellness</span>
            </div>
            
            <details style="background: rgba(0,0,0,0.2); border: 1px solid rgba(255,255,255,0.05); border-radius: 6px; margin-top: 12px; overflow: hidden;">
                <summary style="padding: 8px 12px; font-size: 11px; color: #c8a400; text-transform: uppercase; letter-spacing: 1px; cursor: pointer;">🚢 View Full Ship Details & Specialty Dining</summary>
                <div style="padding: 12px; font-size: 13px; line-height: 1.5; color: rgba(255,255,255,0.85); border-top: 1px solid rgba(255,255,255,0.05);">
                    <div style="font-weight: 600; color: #c8a400; margin-bottom: 6px;">Specialty Dining Venues:</div>
                    <ul style="margin-left: 20px; margin-bottom: 12px; list-style-type: disc;">
"""

ship_data = dossier_data.get("ship", {})
for d_item in ship_data.get("dining", []):
    d_html = d_item.replace("**", "<b>", 1).replace("**", "</b>", 1) if "**" in d_item else d_item
    html_content += f'<li style="margin-bottom: 4px;">{d_html}</li>'
    
html_content += """
                    </ul>
                    <div style="font-weight: 600; color: #c8a400; margin-bottom: 6px;">Accommodations & Suites:</div>
                    <ul style="margin-left: 20px; margin-bottom: 12px; list-style-type: disc;">
"""

for s_item in ship_data.get("suites", []):
    s_html = s_item.replace("**", "<b>", 1).replace("**", "</b>", 1) if "**" in s_item else s_item
    html_content += f'<li style="margin-bottom: 4px;">{s_html}</li>'
    
html_content += f"""
                    </ul>
                    <div style="font-weight: 600; color: #c8a400; margin-bottom: 6px;">Deck Logistics:</div>
                    <p style="font-size: 12px; color: rgba(255,255,255,0.7);">{ship_data.get("decks", "").replace(chr(10), "<br>")}</p>
                </div>
            </details>
        </div>
    </div>

    <!-- STATS -->
    <div class="stats-bar">
        <div class="stat"><div class="stat-val">26</div><div class="stat-lbl">Nights</div></div>
        <div class="stat"><div class="stat-val">18</div><div class="stat-lbl">Excursions</div></div>
        <div class="stat"><div class="stat-val">17</div><div class="stat-lbl">Ports</div></div>
        <div class="stat"><div class="stat-val">$850</div><div class="stat-lbl">SBC Credit</div></div>
    </div>

    <!-- CLIENT INFO BAR -->
    <div class="ck-bar">
        <span><b>Nancy &amp; Ken Lyons</b> &middot; Res #2979301 &middot; Paid in Full</span>
        <span style="font-size: 10px; opacity: 0.8;">Seven Seas Society: Gold (Hits Platinum this trip! 🎓)</span>
    </div>

    <!-- DAY BY DAY -->
    <div id="itinerary" class="itinerary-container">
"""

for d in DAYS:
    # Add section headers
    if d["day"] is None and d["type"] == "travel" and d["date"] == "Aug 9":
        html_content += '<div class="sec-header">✈️ PRE-CRUISE TRAVEL &middot; ATHENS ARRIVAL</div>'
    elif d["day"] == 1:
        html_content += '<div class="sec-header">🛳️ CRUISE ITINERARY &middot; SEVEN SEAS SPLENDOR</div>'
    
    row_cls = d["type"]
    html_content += f'<div class="day-card {row_cls}">'
    
    html_content += '<div class="card-main">'
    # Left Column: Date & Day
    html_content += '<div class="card-left">'
    if d["day"] is not None:
        html_content += f'<div class="day-num">Day {d["day"]}</div>'
    else:
        html_content += '<div class="day-num" style="font-size:16px">&mdash;</div>'
    html_content += f'<div class="day-dow">{d["dow"]}</div>'
    html_content += f'<div class="date-mon">{d["date"].split()[0]}</div>'
    html_content += f'<div class="date-day">{d["date"].split()[1]}</div>'
    html_content += '</div>'
    
    # Middle Column: Content
    html_content += '<div class="card-content">'
    html_content += f'<div class="port-header"><span class="port-flag">{d["flag"]}</span><span class="port-name">{d["port"]}</span></div>'
    if d.get("sub"):
        html_content += f'<div class="port-sub">{d["sub"]}</div>'
        
    if d.get("exc"):
        html_content += f'<div class="exc-block"><div class="block-lbl">Excursion Booked</div><div class="block-val"><span>{d["exc"]}</span><span class="block-time">🕐 {d["time"]}</span></div></div>'
        
    if d.get("dining"):
        html_content += f'<div class="dining-block"><div class="block-lbl">Dining Reservation</div><div class="block-val"><span>{d["dining"]["name"]}</span><span class="block-time">🕐 {d["dining"]["time"]}</span></div></div>'
        
    if d.get("note"):
        html_content += f'<div class="note-text">{d["note"]}</div>'
    html_content += '</div>'
    
    # Right Column: Images
    html_content += '<div class="card-images">'
    html_content += f'<img src="{d["img"]}" alt="{d["port"]}">'
    if d.get("img2"):
        html_content += f'<img src="{d["img2"]}" alt="{d["port"]} detail">'
    html_content += '</div>'
    html_content += '</div>' # End card-main
    
    # Match the port name in dossier_data
    matched_port_key = None
    for pk in dossier_data.get("ports", {}):
        if pk.lower() in d["port"].lower():
            matched_port_key = pk
            break
            
    port_intel = dossier_data["ports"].get(matched_port_key) if matched_port_key else None
    port_excs = dossier_data["excursions"].get(matched_port_key, []) if matched_port_key else []
    
    has_dropdown = port_intel or port_excs
    
    if has_dropdown:
        html_content += '<details class="intel-dropdown" name="itinerary-intel">'
        html_content += f'<summary>📖 Expand Destination & Excursion Deep-Dive</summary>'
        html_content += '<div class="intel-content">'
        
        # 1. Port Romance
        if port_intel and port_intel.get("romance"):
            html_content += f'<div style="margin-bottom: 14px;"><span class="intel-tag">Destination Insight</span> {port_intel["romance"]}</div>'
            
        # 2. Key Highlights / Sights
        if port_intel and port_intel.get("highlights"):
            html_content += '<div style="margin-bottom: 14px;"><span class="intel-tag">Key Sights & Highlights</span>'
            html_content += '<ul style="margin-left: 20px; margin-top: 6px; font-size: 13px; line-height: 1.5; list-style-type: disc;">'
            for hl in port_intel["highlights"]:
                hl_formatted = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', hl)
                html_content += f'<li style="margin-bottom: 4px;">{hl_formatted}</li>'
            html_content += '</ul></div>'
            
        # 3. Port Information
        if port_intel and port_intel.get("info"):
            # Format any bold indicators in the port info text
            info_formatted = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', port_intel["info"])
            html_content += f'<div style="margin-bottom: 14px;"><span class="intel-tag">Port Logistics & Info</span> <span style="font-size: 12px; color: rgba(255,255,255,0.75);">{info_formatted}</span></div>'
            
        # 4. Excursions
        if port_excs:
            html_content += '<div style="margin-top: 14px; border-top: 1px solid rgba(255,255,255,0.08); padding-top: 10px;">'
            html_content += '<div style="font-size: 12px; text-transform: uppercase; letter-spacing: 1px; color: #c8a400; margin-bottom: 8px; font-weight: 600;">Regent shore excursions:</div>'
            for exc in port_excs:
                html_content += f'<div style="background: rgba(255,255,255,0.02); border-left: 2px solid #c8a400; padding: 10px; margin-bottom: 8px; border-radius: 4px;">'
                html_content += f'<div style="font-size: 13px; font-weight: 600; color: #f7f3ea;">{exc["name"]}</div>'
                if exc.get("marketing"):
                    html_content += f'<div style="font-size: 12px; font-style: italic; color: rgba(255,255,255,0.6); margin-top: 2px;">"{exc["marketing"]}"</div>'
                if exc.get("description"):
                    html_content += f'<div style="font-size: 12px; color: rgba(255,255,255,0.8); margin-top: 4px;">{exc["description"]}</div>'
                html_content += f'<div style="display: flex; gap: 16px; margin-top: 6px; font-size: 11px; color: #a8c4f0;">'
                html_content += f'<span>🕐 Duration: {exc["duration"]}</span>'
                html_content += f'<span>🏷️ Price: {exc["price"]}</span>'
                html_content += '</div>'
                html_content += '</div>'
            html_content += '</div>'
            
        html_content += '</div>'
        html_content += '</details>'
    
    html_content += '</div>' # End day-card

html_content += """
    </div>

    <!-- OPEN ITEMS SECTION -->
    <div class="open-section">
        <div class="open-hdr">✓ Outstanding Action &amp; Transfer Items</div>
"""

for item in OPEN_ITEMS:
    html_content += f"""
        <div class="open-item">
            <div class="open-icon">{item["icon"]}</div>
            <div class="open-info">
                <div class="open-title">{item["title"]}</div>
                <div class="open-desc">{item["desc"]}</div>
            </div>
            <div class="open-status">{item["status"]}</div>
        </div>
    """

html_content += f"""
    </div>

    <!-- FOOTER -->
    <div class="footer">
        <div style="font-family: Georgia, serif; font-size: 14px; font-weight: bold; color: #c9a84c; margin-bottom: 8px;">
            DREAMS2MEMORIES TRAVEL, LLC
        </div>
        <div>John A. Loucks III &middot; Owner</div>
        <div style="margin-top: 6px;">
            📧 <a href="mailto:johnloucks3@gmail.com">johnloucks3@gmail.com</a> &middot; 📞 (719)-291-0742 &middot; <a href="https://www.d2mluxury.quest">www.d2mluxury.quest</a>
        </div>
    </div>
</div>

</body>
</html>
"""

# Write HTML
print(f"Writing HTML to {HTML_PATH}...")
HTML_PATH.write_text(html_content, encoding="utf-8")

# Write PDF
print(f"Compiling PDF to {PDF_PATH} using WeasyPrint...")
HTML(str(HTML_PATH)).write_pdf(str(PDF_PATH), media_type='print')

print("SUCCESS!")
