#!/usr/bin/env python3
"""Build Grandeur Itinerary HTML and PDF files for Furlow, Ely-Darrow, and Nichols.
Branded in D2M Dark Space-Blue and following the Lyons format exactly.
"""

import os
import sys
import re
import base64
import mimetypes
from pathlib import Path
from weasyprint import HTML

ROOT = Path("/home/john/Thunderbird")
OUT_DIR = ROOT / "cruises_web"
OUT_DIR.mkdir(parents=True, exist_ok=True)

LOGO_URL = "https://lh3.googleusercontent.com/d/1HYa61cNwcialWk64DimGwIfCAbUjESsu"

# Local Ship Profile Image
GRANDEUR_IMG_PATH = ROOT / "output/Grandeur_Scandinavia_Portal/assets/grandeur_ship_exterior.jpg"

def encode_img(path):
    if str(path).startswith('http'):
        return str(path)
    if os.path.exists(path):
        mime = mimetypes.guess_type(path)[0] or 'image/jpeg'
        with open(path, 'rb') as f:
            b64 = base64.b64encode(f.read()).decode('utf-8')
            return f"data:{mime};base64,{b64}"
    return str(path)

# Base64 encode the Grandeur exterior image
grandeur_exterior_b64 = encode_img(GRANDEUR_IMG_PATH)

# High quality Pexels image URLs for the destinations
IMAGES = {
    "flight": "https://images.pexels.com/photos/5778703/pexels-photo-5778703.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "stockholm": "https://images.pexels.com/photos/3617496/pexels-photo-3617496.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "stockholm_2": "https://images.pexels.com/photos/3579178/pexels-photo-3579178.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "warnemunde": "https://images.pexels.com/photos/1125212/pexels-photo-1125212.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "warnemunde_2": "https://images.pexels.com/photos/3642345/pexels-photo-3642345.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "copenhagen": "https://images.pexels.com/photos/15291437/pexels-photo-15291437.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "copenhagen_2": "https://images.pexels.com/photos/9395273/pexels-photo-9395273.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "kristiansand": "https://images.pexels.com/photos/1009136/pexels-photo-1009136.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "kristiansand_2": "https://images.pexels.com/photos/2880507/pexels-photo-2880507.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "oslo": "https://images.pexels.com/photos/14849187/pexels-photo-14849187.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "oslo_2": "https://images.pexels.com/photos/14849184/pexels-photo-14849184.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "sea_baltic": "https://images.pexels.com/photos/1001682/pexels-photo-1001682.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "sea_north": "https://images.pexels.com/photos/1295138/pexels-photo-1295138.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "grandeur_dining": "https://images.pexels.com/photos/262978/pexels-photo-262978.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940"
}

# Load the port descriptions from our JSON catalog
port_catalog = {}
catalog_path = ROOT / "validations/rssc_scrape/extracted_port_details.json"
if catalog_path.exists():
    import json
    with open(catalog_path, "r") as f:
        port_catalog = json.load(f)

# Clients config
CLIENTS = {
    "furlow": {
        "key": "furlow",
        "title": "Grandeur · Furlow Itinerary | D2M",
        "header_names": "John & Melissa Furlow",
        "suite_number": "827",
        "deck": "8",
        "suite_cat": "Concierge Suite - D",
        "booking_id": "3071222",
        "paid_amount": "$15,486",
        "loyalty": "Seven Seas Society: Gold (Hits Platinum this trip! 🎓)",
        "open_items": [
            {"icon": "✈️", "title": "AY 811 Seats (Outbound Leg 2)", "desc": "HEL → ARN seats are currently UNASSIGNED (PNR BB4X94). Contact Finnair or AA to assign seats.", "status": "OPEN"},
            {"icon": "🚗", "title": "ARN → At Six Stockholm Transfer — Aug 27", "desc": "✅ Confirmed via Project Expedition (Ref PE184710612). Private sedan. Hold w/o Payment — full payment due Aug 16, 2026.", "status": "CONFIRMED"},
            {"icon": "🏨", "title": "At Six Stockholm pre-cruise Night 1 (Aug 27)", "desc": "Haymarket cancelled — At Six booking not yet in dossier. Amex FHR booking to be arranged.", "status": "OPEN"},
        ],
        "excursions": {
            "Aug 30": {"name": "Highlights of Stockholm & Vasa Museum", "time": "09:00"},
            "Sep 01": {"name": "SG-The Berlin Experience", "time": "07:30"},
            "Sep 02": {"name": "Amazing Rostock", "time": "09:00"},
            "Sep 03": {"name": "A Tour of Two Kingdoms - Denmark to Sweden", "time": "08:45"},
            "Sep 04": {"name": "Tivoli Gardens & Canal Cruise", "time": "08:45"},
            "Sep 06": {"name": "Explore Kristiansand on Foot", "time": "10:00"},
            "Sep 07": {"name": "Hadeland Glass Works & Fram Museum", "time": "09:30"}
        },
        "excursions_count": "7",
        "open_count": "2"
    },
    "elydarrow": {
        "key": "elydarrow",
        "title": "Grandeur · Ely & Darrow Itinerary | D2M",
        "header_names": "Al Ely & Amy Darrow",
        "suite_number": "961",
        "deck": "9",
        "suite_cat": "Concierge Suite - D",
        "booking_id": "3096289",
        "paid_amount": "$16,640",
        "loyalty": "Seven Seas Society: Member",
        "open_items": [
            {"icon": "🇳🇴", "title": "Kristiansand Shore Excursion (Sep 6)", "desc": "No shore excursion has been selected for Kristiansand. Please let us know if you would like free time or a booked tour.", "status": "OPEN"},
            {"icon": "✈️", "title": "AY 811 Seats (Outbound Leg 2)", "desc": "HEL → ARN seats assigned — seat numbers TBD (PNR UXVXZP). Confirm with AA.", "status": "OPEN"},
            {"icon": "🚗", "title": "ARN → At Six Stockholm Transfer — Aug 27", "desc": "✅ Confirmed via Project Expedition (Ref PE184711812). Private sedan. Hold w/o Payment — full payment due Aug 16, 2026.", "status": "CONFIRMED"},
            {"icon": "🏨", "title": "At Six Stockholm pre-cruise Night 1 (Aug 27)", "desc": "✅ Al & Amy's own reservation confirmed (deferred payment at hotel, Aug 27–28).", "status": "CONFIRMED"},
            {"icon": "🎂", "title": "Amy's Birthday at Sea — August 31", "desc": "✅ Amy's birthday falls on Day 3 (Baltic Sea). A perfect day for an onboard celebration — the Grandeur's culinary team and spa are at your disposal.", "status": "CONFIRMED"},
            {"icon": "🩺", "title": "Travel Insurance", "desc": "✅ Insurance purchased 2026-06-23. All documents in place.", "status": "CONFIRMED"},
        ],
        "excursions": {
            "Aug 30": {"name": "Swedish Nature Experience", "time": "10:30"},
            "Sep 01": {"name": "Amazing Rostock", "time": "09:00"},
            "Sep 02": {"name": "Medieval Flavors of Rostock", "time": "14:30"},
            "Sep 03": {"name": "Christiansborg Palace & Tivoli Gardens", "time": "13:30"},
            "Sep 04": {"name": "A Tour of Two Kingdoms - Denmark to Sweden", "time": "09:00"},
            "Sep 06": {"name": "None selected", "time": "", "gap": True},
            "Sep 07": {"name": "Oslo During World War II", "time": "09:00"}
        },
        "excursions_count": "6",
        "open_count": "2"
    },
    "nichols": {
        "key": "nichols",
        "title": "Grandeur · Nichols Itinerary | D2M",
        "header_names": "Larry & Heidi Nichols",
        "suite_number": "939",
        "deck": "9",
        "suite_cat": "Concierge Suite - D",
        "booking_id": "3078056",
        "paid_amount": "$14,986",
        "loyalty": "Seven Seas Society: Gold",
        "open_items": [
            {"icon": "🇳🇴", "title": "Kristiansand Shore Excursion (Sep 6)", "desc": "No shore excursion has been selected for Kristiansand. Please let us know if you would like free time or a booked tour.", "status": "OPEN"},
            {"icon": "🚗", "title": "ARN → At Six Stockholm Transfer — Aug 27", "desc": "✅ Confirmed via Project Expedition (Ref PE184712212). Private sedan. Hold w/o Payment — full payment due Aug 16, 2026.", "status": "CONFIRMED"},
            {"icon": "🏨", "title": "At Six Stockholm pre-cruise Night 1 (Aug 27)", "desc": "✅ Amex FHR Conf #9092637820900 (Trip ZO-AX1049-13385). Standard Room, 1 King Bed. 12pm check-in, breakfast×2, $100 F&B credit, Wi-Fi. Due at hotel (SEK 3,715 incl. taxes).", "status": "CONFIRMED"},
            {"icon": "🎂", "title": "Heidi's Birthday Celebration", "desc": "✅ Birthday is embarkation day (Aug 29). Group birthday dinner at Pacific Rim on Aug 30 at 6:30 PM — registered with shipboard staff.", "status": "CONFIRMED"},
        ],
        "excursions": {
            "Aug 30": {"name": "Highlights of Stockholm & Vasa Museum", "time": "09:00"},
            "Sep 01": {"name": "The Berlin Experience", "time": "07:30"},
            "Sep 02": {"name": "Amazing Rostock (09:00) & Medieval Flavors (14:30)", "time": "Multiple"},
            "Sep 03": {"name": "A Tour of Two Kingdoms – Denmark to Sweden", "time": "08:45"},
            "Sep 04": {"name": "Tivoli Gardens & Canal Cruise", "time": "10:15"},
            "Sep 06": {"name": "None selected", "time": "", "gap": True},
            "Sep 07": {"name": "Panoramic Oslo", "time": "09:15"}
        },
        "excursions_count": "7",
        "open_count": "1"
    }
}

# Day-by-day static base itinerary template for Storied Scandinavia
ITINERARY_DAYS = [
    {
        "day": None, "date": "Aug 26", "dow": "Wed", "type": "travel",
        "port": "DFW → HEL (fly)", "flag": "✈️",
        "sub": "AA 9018 / Finnair · 4:50 PM → 10:45 AM +1",
        "note": "Begin your Scandinavian luxury journey, flying Business Class across the Atlantic. Relax and toast to the historic horizons awaiting you.",
        "img": IMAGES["flight"], "img2": None, "port_key": "Stockholm"
    },
    {
        "day": None, "date": "Aug 27", "dow": "Thu", "type": "travel",
        "port": "HEL → ARN → At Six Stockholm", "flag": "✈️",
        "sub": "AY 811 1:15 PM → 1:15 PM · At Six Stockholm",
        "note": "Arrive in Stockholm and transfer to the stylish Hotel At Six. Enjoy your first evening exploring the beautiful capital.",
        "img": IMAGES["stockholm"], "img2": None, "port_key": "Stockholm"
    },
    {
        "day": None, "date": "Aug 28", "dow": "Fri", "type": "travel",
        "port": "Stockholm", "flag": "🏙️",
        "sub": "Hotel At Six · Regent Included Hotel Night",
        "note": "A full day of leisure at Stockholm. Walk Gamla Stan's cobbled paths, explore the royal canals, and prepare for embarkation tomorrow.",
        "img": IMAGES["stockholm_2"], "img2": None, "port_key": "Stockholm"
    },
    {
        "day": 1, "date": "Aug 29", "dow": "Sat", "type": "embark",
        "port": "Stockholm, Sweden", "flag": "🇸🇪",
        "sub": "Seven Seas Grandeur · Board by 15:00",
        "note": "Embark Seven Seas Grandeur. Enjoy welcome champagne, meet up with the group on the pool deck, and settle into your suite.",
        "img": grandeur_exterior_b64, "img2": IMAGES["grandeur_dining"], "port_key": "Stockholm"
    },
    {
        "day": 2, "date": "Aug 30", "dow": "Sun", "type": "port",
        "port": "Stockholm, Sweden", "flag": "🇸🇪",
        "sub": "Departs 5:00 PM",
        "dining": {"name": "Pacific Rim", "time": "6:30 PM", "host": "Nichols"},
        "note": "Wander the waterfront of Sweden's floating capital. This evening, celebrate Heidi's birthday with a Pan-Asian group dinner at Pacific Rim.",
        "img": IMAGES["stockholm"], "img2": IMAGES["stockholm_2"], "port_key": "Stockholm"
    },
    {
        "day": 3, "date": "Aug 31", "dow": "Mon", "type": "sea",
        "port": "Cruising the Baltic Sea", "flag": "🌊",
        "note": "A day of pure leisure on the Baltic Sea. Indulge in culinary delights, relax by the pool, or visit the Serene Spa.",
        "img": IMAGES["sea_baltic"], "img2": None, "port_key": None
    },
    {
        "day": 4, "date": "Sep 1", "dow": "Tue", "type": "port",
        "port": "Berlin (Warnemünde), Germany", "flag": "🇩🇪",
        "sub": "6:00 AM – Overnight",
        "note": "Arrive at the seaside resort of Warnemünde. Explore the historic harbor or take a full-day excursion inland to historic Berlin.",
        "img": IMAGES["warnemunde"], "img2": IMAGES["warnemunde_2"], "port_key": "Warnemunde"
    },
    {
        "day": 5, "date": "Sep 2", "dow": "Wed", "type": "port",
        "port": "Berlin (Warnemünde), Germany", "flag": "🇩🇪",
        "sub": "Overnight – Departs 9:00 PM",
        "dining": {"name": "Chartreuse", "time": "7:30 PM", "host": "Furlow"},
        "note": "A second day in Warnemünde to tour Rostock or enjoy Baltic coast sights. This evening, share a fine French dining experience at Chartreuse.",
        "img": IMAGES["warnemunde"], "img2": IMAGES["warnemunde_2"], "port_key": "Warnemunde"
    },
    {
        "day": 6, "date": "Sep 3", "dow": "Thu", "type": "port",
        "port": "Copenhagen, Denmark", "flag": "🇩🇰",
        "sub": "Arrives 9:00 AM – Overnight",
        "note": "Arrive in Denmark's capital. Explore the palaces and streets. Copenhagen stays overnight, giving you a wonderful evening ashore.",
        "img": IMAGES["copenhagen"], "img2": IMAGES["copenhagen_2"], "port_key": "Copenhagen"
    },
    {
        "day": 7, "date": "Sep 4", "dow": "Fri", "type": "port",
        "port": "Copenhagen, Denmark", "flag": "🇩🇰",
        "sub": "Overnight – Departs 6:00 PM",
        "dining": {"name": "Prime 7", "time": "7:30 PM", "host": "Ely"},
        "note": "Spend the morning at Tivoli Gardens or shopping on Strøget. This evening, enjoy our third group dinner at Prime 7 steakhouse.",
        "img": IMAGES["copenhagen"], "img2": IMAGES["copenhagen_2"], "port_key": "Copenhagen"
    },
    {
        "day": 8, "date": "Sep 5", "dow": "Sat", "type": "sea",
        "port": "Cruising the North Sea", "flag": "🌊",
        "note": "Sailing towards Norway. Relax on deck and watch the dramatic Scandinavian sky reflect on the open North Sea.",
        "img": IMAGES["sea_north"], "img2": None, "port_key": None
    },
    {
        "day": 9, "date": "Sep 6", "dow": "Sun", "type": "port",
        "port": "Kristiansand, Norway", "flag": "🇳🇴",
        "sub": "8:00 AM – 6:00 PM",
        "note": "Norway's southern gem. Wander through the white-washed wooden houses of the Posebyen old town or stroll the boardwalk.",
        "img": IMAGES["kristiansand"], "img2": IMAGES["kristiansand_2"], "port_key": "Kristiansand"
    },
    {
        "day": 10, "date": "Sep 7", "dow": "Mon", "type": "port",
        "port": "Oslo, Norway", "flag": "🇳🇴",
        "sub": "Arrives 8:00 AM – Overnight",
        "note": "Sail through Oslofjord to arrive in Norway's capital. Stand on the ramparts of Akershus Fortress overlooking the ship.",
        "img": IMAGES["oslo"], "img2": IMAGES["oslo_2"], "port_key": "Oslo"
    },
    {
        "day": None, "date": "Sep 8", "dow": "Tue", "type": "disembark",
        "port": "Oslo · Disembark & Fly Home", "flag": "✈️",
        "sub": "OSL → LHR → DFW · BA 6776 + AA 79 (11:15 AM departure)",
        "note": "Disembark in Oslo and take your private transfer to the airport. A breathtaking conclusion to a storied Scandinavia voyage.",
        "img": IMAGES["flight"], "img2": None, "port_key": "Oslo"
    }
]

def build_client_html(client_key):
    cfg = CLIENTS[client_key]
    
    # Header block
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{cfg["title"]}</title>
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

@media (max-width: 768px) {{
    body {{ padding: 14px 6px; }}
    .hero {{ padding: 30px 16px 20px; }}
    .voyage-title {{ font-size: 22px; }}
    .voyage-sub {{ font-size: 12px; }}
    .ship-profile {{ flex-direction: column; text-align: center; padding: 16px; }}
    .ship-profile img {{ width: 100%; max-width: 320px; }}
    .stats-bar {{ padding: 12px; }}
    .stat-val {{ font-size: 18px; }}
    .ck-bar {{ flex-direction: column; align-items: flex-start; gap: 6px; padding: 12px 16px; }}
    .card-main {{ flex-direction: column; }}
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
    .date-mon {{ margin-top: 0; border-top: none; padding-top: 0; }}
    .card-content {{ padding: 16px; }}
    .card-images {{ width: 100%; border-left: none; border-top: 1px solid rgba(255,255,255,.05); flex-direction: row; }}
    .card-images img {{ width: 50%; height: 120px; }}
}}

@media print {{
    body {{
        background: #04041b !important;
        color: #e8f1ff !important;
        padding: 0 !important;
        -webkit-print-color-adjust: exact;
    }}
    .page {{ box-shadow: none !important; border-radius: 0 !important; background: #08082e !important; }}
    .day-card {{
        page-break-inside: avoid;
        border: 1px solid rgba(255,255,255,0.15) !important;
        margin-bottom: 12px !important;
        background: rgba(255,255,255,0.02) !important;
    }}
    details.intel-dropdown {{ display: none !important; }}
    .card-images {{ width: 160px !important; }}
    .card-images img {{ height: 80px !important; }}
}}
</style>
</head>
<body>

<div class="page">
    <!-- HERO HEADER -->
    <div class="hero">
        <img src="{LOGO_URL}" class="logo" alt="D2M Logo">
        <div class="wordmark">DREAMS2MEMORIES TRAVEL, LLC</div>
        <div class="voyage-title">Seven Seas Grandeur &middot; Storied Scandinavia</div>
        <div class="voyage-sub">Stockholm to Oslo &middot; August 29 &ndash; September 8, 2026</div>
    </div>

    <!-- SHIP PROFILE INJECTION -->
    <div class="ship-profile">
        <img src="{grandeur_exterior_b64}" alt="Seven Seas Grandeur">
        <div class="ship-text">
            <h2>Seven Seas Grandeur</h2>
            <p>A Heritage of Perfection. Experience Regent's newest ultra-luxury vessel, featuring a multimillion-dollar art curation, all-suite accommodations with private balconies, 8 exquisite dining venues, and a personalized 1:1.3 crew-to-guest service ratio.</p>
            <div class="ship-stats" style="margin-bottom: 12px;">
                <span>⭐ Suite {cfg["suite_number"]} ({cfg["suite_cat"]})</span>
                <span>🍽️ 8 Specialty Dining Venues</span>
                <span>🌊 55,500 Gross Tonnage</span>
                <span>🧖‍♀️ Serene Spa & Wellness</span>
            </div>
            
            <details style="background: rgba(0,0,0,0.2); border: 1px solid rgba(255,255,255,0.05); border-radius: 6px; margin-top: 12px; overflow: hidden;">
                <summary style="padding: 8px 12px; font-size: 11px; color: #c8a400; text-transform: uppercase; letter-spacing: 1px; cursor: pointer;">🚢 View Onboard Specialty Dining &amp; Highlights</summary>
                <div style="padding: 12px; font-size: 13px; line-height: 1.5; color: rgba(255,255,255,0.85); border-top: 1px solid rgba(255,255,255,0.05);">
                    <div style="font-weight: 600; color: #c8a400; margin-bottom: 6px;">Specialty Dining Venues:</div>
                    <ul style="margin-left: 20px; margin-bottom: 12px; list-style-type: disc;">
                        <li style="margin-bottom: 4px;"><b>Compass Rose:</b> Flagship restaurant featuring custom crystal chandeliers and a fully customizable menu.</li>
                        <li style="margin-bottom: 4px;"><b>Prime 7:</b> Intimate, classic American steakhouse serving premium dry-aged steaks and lobster.</li>
                        <li style="margin-bottom: 4px;"><b>Chartreuse:</b> Parisian-inspired fine French dining with modern touchpoints.</li>
                        <li style="margin-bottom: 4px;"><b>Pacific Rim:</b> Dramatic Pan-Asian restaurant featuring a majestic brass dragon entrance.</li>
                        <li style="margin-bottom: 4px;"><b>Sette Mari at La Veranda:</b> Fine Italian table-service dining by night, relaxed buffet by day.</li>
                    </ul>
                    <div style="font-weight: 600; color: #c8a400; margin-bottom: 6px;">Suite Comforts (Deck {cfg["deck"]}):</div>
                    <p style="font-size: 12px; color: rgba(255,255,255,0.7); line-height: 1.4;">Your Concierge Suite features a private furnished balcony, marble bathrooms, luxurious Elite Slumber™ bed, daily replenished mini-bar, 24-hour in-suite dining, and priority dining &amp; shore excursion bookings.</p>
                </div>
            </details>
        </div>
    </div>

    <!-- STATS -->
    <div class="stats-bar">
        <div class="stat"><div class="stat-val">10</div><div class="stat-lbl">Nights</div></div>
        <div class="stat"><div class="stat-val">5</div><div class="stat-lbl">Ports</div></div>
        <div class="stat"><div class="stat-val">{cfg["excursions_count"]}</div><div class="stat-lbl">Excursions</div></div>
        <div class="stat"><div class="stat-val">{cfg["paid_amount"]}</div><div class="stat-lbl">Paid In Full</div></div>
        <div class="stat"><div class="stat-val" style="color:#ff8c66">{cfg["open_count"]}</div><div class="stat-lbl">Open Items</div></div>
    </div>

    <!-- CLIENT INFO BAR -->
    <div class="ck-bar">
        <span><b>{cfg["header_names"]}</b> &middot; Res #{cfg["booking_id"]} &middot; Paid in Full</span>
        <span style="font-size: 10px; opacity: 0.8;">{cfg["loyalty"]}</span>
    </div>

    <!-- DAY BY DAY -->
    <div id="itinerary" class="itinerary-container">
"""

    # Populate days
    for d in ITINERARY_DAYS:
        # Add section headers
        if d["day"] is None and d["type"] == "travel" and d["date"] == "Aug 26":
            html += '<div class="sec-header">✈️ PRE-CRUISE TRAVEL &middot; STOCKHOLM ARRIVAL</div>'
        elif d["day"] == 1:
            html += '<div class="sec-header">🛳️ CRUISE ITINERARY &middot; SEVEN SEAS GRANDEUR</div>'
        
        row_cls = d["type"]
        html += f'<div class="day-card {row_cls}">'
        html += '<div class="card-main">'
        
        # Left column
        html += '<div class="card-left">'
        if d["day"] is not None:
            html += f'<div class="day-num">Day {d["day"]}</div>'
        else:
            html += '<div class="day-num" style="font-size:16px">&mdash;</div>'
        html += f'<div class="day-dow">{d["dow"]}</div>'
        html += f'<div class="date-mon">{d["date"].split()[0]}</div>'
        html += f'<div class="date-day">{d["date"].split()[1]}</div>'
        html += '</div>'
        
        # Content column
        html += '<div class="card-content">'
        html += f'<div class="port-header"><span class="port-flag">{d["flag"]}</span><span class="port-name">{d["port"]}</span></div>'
        if d.get("sub"):
            html += f'<div class="port-sub">{d["sub"]}</div>'
            
        # Match excursion for this client
        date_str = d["date"]
        # Map month code
        m_map = {"Aug": "Aug", "Sep": "Sep"}
        mon = date_str.split()[0]
        day_num = date_str.split()[1].zfill(2)
        exc_date_key = f"{mon} {day_num}"
        
        matched_exc = None
        # Try exact match in excursions
        for k, exc_val in cfg["excursions"].items():
            # e.g., k is "Aug 30" or "Sep 01"
            if exc_date_key == k or (k.startswith("Sep") and exc_date_key.startswith("Sep") and int(k.split()[1]) == int(day_num)):
                matched_exc = exc_val
                break
        
        if matched_exc:
            if matched_exc.get("gap"):
                html += f'<div class="exc-block" style="border-left-color: #ff6b6b; background: rgba(255,100,100,0.05);">'
                html += f'<div class="block-lbl" style="color: #ff8c8c;">Excursion Status</div>'
                html += f'<div class="block-val"><span style="color: #ff6b6b; font-weight: bold;">⚠️ {matched_exc["name"]}</span></div></div>'
            elif matched_exc["name"] != "None selected":
                time_str = f'🕐 {matched_exc["time"]}' if matched_exc.get("time") else ""
                html += f'<div class="exc-block"><div class="block-lbl">Excursion Booked</div><div class="block-val"><span>{matched_exc["name"]}</span><span class="block-time">{time_str}</span></div></div>'
            
        # Match group dining
        # Group dining dates: Aug 30, Sep 02, Sep 04
        matched_dining = None
        if d["day"] == 2: # Aug 30
            matched_dining = {"name": "Pacific Rim", "time": "6:30 PM", "host": "Nichols (Heidi's Birthday Dinner! 🎂)"}
        elif d["day"] == 5: # Sep 2
            matched_dining = {"name": "Chartreuse", "time": "7:30 PM", "host": "Furlow"}
        elif d["day"] == 7: # Sep 4
            matched_dining = {"name": "Prime 7", "time": "7:30 PM", "host": "Ely"}
            
        if matched_dining:
            html += f'<div class="dining-block"><div class="block-lbl">Group Dining</div><div class="block-val"><span>{matched_dining["name"]} (Host: {matched_dining["host"]})</span><span class="block-time">🕐 {matched_dining["time"]}</span></div></div>'
            
        if d.get("note"):
            html += f'<div class="note-text">{d["note"]}</div>'
        html += '</div>'
        
        # Right column (Images)
        html += '<div class="card-images">'
        html += f'<img src="{d["img"]}" alt="{d["port"]}">'
        if d.get("img2"):
            html += f'<img src="{d["img2"]}" alt="{d["port"]} detail">'
        html += '</div>'
        
        html += '</div>' # End card-main
        
        # Port destination dropdown (scraped catalog info)
        port_key = d.get("port_key")
        port_intel = port_catalog.get(port_key) if port_key else None
        
        if port_intel:
            html += '<details class="intel-dropdown" name="itinerary-intel">'
            html += f'<summary>📖 Expand Destination &amp; Excursion Deep-Dive</summary>'
            html += '<div class="intel-content">'
            
            # Port Romance
            if port_intel.get("romance_copy"):
                romance_clean = re.sub('<[^<]+?>', '', port_intel["romance_copy"]) # strip tags
                html += f'<div style="margin-bottom: 14px;"><span class="intel-tag">Destination Insight</span> {romance_clean}</div>'
                
            # Highlights
            if port_intel.get("highlights"):
                # if list
                if isinstance(port_intel["highlights"], list):
                    html += '<div style="margin-bottom: 14px;"><span class="intel-tag">Key Sights &amp; Highlights</span>'
                    html += '<ul style="margin-left: 20px; margin-top: 6px; font-size: 13px; line-height: 1.5; list-style-type: disc;">'
                    for hl in port_intel["highlights"]:
                        html += f'<li style="margin-bottom: 4px;">{hl}</li>'
                    html += '</ul></div>'
                else:
                    html += f'<div style="margin-bottom: 14px;"><span class="intel-tag">Key Sights &amp; Highlights</span> {port_intel["highlights"]}</div>'
                    
            # Port Logistics
            html += f'<div style="margin-bottom: 14px;"><span class="intel-tag">Port Logistics &amp; Info</span> <span style="font-size: 12px; color: rgba(255,255,255,0.75);">Docking or tendering info per Regent Seven Seas standard operating schedules. Taxis and public transit options are readily accessible at the cruise gateway.</span></div>'
            
            html += '</div>'
            html += '</details>'
            
        html += '</div>' # End day-card
        
    html += """
    </div>

    <!-- OPEN ITEMS SECTION -->
    <div class="open-section">
        <div class="open-hdr">✓ Outstanding Action &amp; Transfer Items</div>
"""

    for item in cfg["open_items"]:
        status = item["status"]
        if status == "CONFIRMED":
            badge_style = "background:#1a6b1a;color:#fff;"
        elif status == "OPEN":
            badge_style = "background:#8b0000;color:#fff;"
        else:
            badge_style = "background:#8b6b00;color:#fff;"
        html += f"""
        <div class="open-item">
            <div class="open-icon">{item["icon"]}</div>
            <div class="open-info">
                <div class="open-title">{item["title"]}</div>
                <div class="open-desc">{item["desc"]}</div>
            </div>
            <div class="open-status" style="{badge_style}">{status}</div>
        </div>
        """

    html += f"""
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
    return html

# Generate files
for key in CLIENTS.keys():
    html_content = build_client_html(key)
    html_path = OUT_DIR / f"itinerary_grandeur_{key}.html"
    pdf_path = OUT_DIR / f"itinerary_grandeur_{key}.pdf"
    
    print(f"Writing {html_path}...")
    html_path.write_text(html_content, encoding="utf-8")
    
    print(f"Compiling {pdf_path}...")
    HTML(str(html_path)).write_pdf(str(pdf_path), media_type='print')

print("\nALL ITINERARIES COMPILED SUCCESSFULLY!")
