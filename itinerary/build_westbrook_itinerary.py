#!/usr/bin/env python3
"""Build Westbrook Silver Nova Itinerary HTML with embedded images."""

import base64
import io
from pathlib import Path
from PIL import Image

IMG_DIR = Path.home() / "Thunderbird" / "restaurant_images" / "Silver_Nova_Images"
OUT_DIR = Path.home() / "Thunderbird" / "output"
LOGO_PATH = Path.home() / "Thunderbird" / "Agency_Logo.png"
HEADSHOT_PATH = Path.home() / "Thunderbird" / "John_Headshot.jpg"


def compress_image(path, width, height, quality, fmt="JPEG"):
    """Compress and resize image, return base64 data URI."""
    img = Image.open(path)
    img = img.convert("RGB") if fmt == "JPEG" else img.convert("RGBA")
    # Resize to cover width x height, then center crop
    ratio_w = width / img.width
    ratio_h = height / img.height
    ratio = max(ratio_w, ratio_h)
    new_w = int(img.width * ratio)
    new_h = int(img.height * ratio)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    # Center crop
    left = (new_w - width) // 2
    top = (new_h - height) // 2
    img = img.crop((left, top, left + width, top + height))
    buf = io.BytesIO()
    if fmt == "JPEG":
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        mime = "image/jpeg"
    else:
        img.save(buf, format="PNG", optimize=True)
        mime = "image/png"
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:{mime};base64,{b64}"


def compress_logo(path, size=200):
    img = Image.open(path).convert("RGBA")
    img = img.resize((size, size), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/png;base64,{b64}"


def compress_headshot(path, size=100):
    img = Image.open(path).convert("RGB")
    # Square crop from center
    s = min(img.width, img.height)
    left = (img.width - s) // 2
    top = (img.height - s) // 2
    img = img.crop((left, top, left + s, top + s))
    img = img.resize((size, size), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85, optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/jpeg;base64,{b64}"


print("Compressing images...")

# Hero
hero_uri = compress_image(IMG_DIR / "silver_nova.jpg", 800, 500, 80)

# Port day images (800x500 q80)
port_images = {
    "day1": ("tokyo_narita_pexels.jpg", 800, 500, 80),
    "day2": ("hilton_odaiba_pexels.jpg", 800, 500, 80),
    "day3": ("yokohama_port_pexels.jpg", 800, 500, 80),
    "day5": ("miyako.jpg", 800, 500, 80),
    "day6": ("aomori.jpg", 800, 500, 80),
    "day14": ("kodiak_bear_cub_pexels.jpg", 800, 500, 80),
    "day16": ("sitka.jpg", 800, 500, 80),
    "day17": ("juneau.jpg", 800, 500, 80),
    "day18": ("wrangell.jpg", 800, 500, 80),
    "day19": ("ketchikan.jpg", 800, 500, 80),
    "day20": ("inside_passage_pexels.jpg", 800, 500, 80),
    "day21": ("victoria.jpg", 800, 500, 80),
    "day22": ("seattle.jpg", 800, 500, 80),
}

# Sea day images (800x300 q75)
sea_images = {
    "day7": ("titan_at_sea_2.png", 800, 300, 75),
    "day8": ("titan_pacific_ocean_1.png", 800, 300, 75),
    "day9": ("titan_at_sea_3.png", 800, 300, 75),
    "day10": ("titan_cruising_pacific_1.png", 800, 300, 75),
    "day11": ("titan_at_sea_4.png", 800, 300, 75),
    "day12": ("pacific_ocean_sunset_pexels.jpg", 800, 300, 75),
    "day13": ("titan_at_sea_5.png", 800, 300, 75),
    "day15": ("gulf_alaska_pexels.jpg", 800, 300, 75),
}

# Kuril Islands — special (800x400 q80)
day4_uri = compress_image(IMG_DIR / "kuril_islands_pexels.jpg", 800, 400, 80)

img_uris = {}
for key, (fname, w, h, q) in {**port_images, **sea_images}.items():
    img_uris[key] = compress_image(IMG_DIR / fname, w, h, q)

logo_uri = compress_logo(LOGO_PATH, 200)
logo_small_uri = compress_logo(LOGO_PATH, 80)
headshot_uri = compress_headshot(HEADSHOT_PATH, 100)

print("Building HTML...")

# Sea day art labels
sea_labels = {
    "day4": "TITAN ART &middot; SAILING FROM JAPAN",
    "day7": "TITAN ART &middot; NORTH PACIFIC",
    "day8": "TITAN ART &middot; PACIFIC OCEAN",
    "day9": "TITAN ART &middot; MID-PACIFIC",
    "day10": "TITAN ART &middot; INTERNATIONAL DATE LINE",
    "day11": "TITAN ART &middot; BONUS DAY",
    "day12": "",
    "day13": "TITAN ART &middot; APPROACHING ALASKA",
    "day15": "",
}


def port_img(key, alt=""):
    return f'<div class="img-port"><img src="{img_uris[key]}" alt="{alt}"></div>'


def sea_img(key, alt="", label=""):
    uri = day4_uri if key == "day4" else img_uris[key]
    lbl = label or sea_labels.get(key, "")
    label_html = f'<div class="art-label">{lbl}</div>' if lbl else ''
    return f'<div class="img-sea"><img src="{uri}" alt="{alt}">{label_html}</div>'


html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Westbrook Silver Nova — April 2026</title>
<style>
@page {{
    size: A4;
    margin: 15mm 12mm 15mm 12mm;
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    font-family: Georgia, 'Times New Roman', serif;
    background: #0d1b2e;
    color: #e8e0d0;
    line-height: 1.6;
    font-size: 11px;
}}
h1, h2, h3, h4 {{ color: #c9a84c; font-weight: 600; }}
h1 {{ font-size: 28px; letter-spacing: 3px; text-transform: uppercase; }}
h2 {{ font-size: 16px; margin-bottom: 8px; border-bottom: 1px solid #1e3358; padding-bottom: 4px; }}
h3 {{ font-size: 13px; margin-bottom: 6px; }}

.header {{
    text-align: center;
    padding: 20px 0 10px;
}}
.header .logo {{ height: 90px; margin-bottom: 8px; }}
.header .subtitle {{ color: #8a9ab5; font-size: 12px; letter-spacing: 2px; margin: 4px 0; }}
.header .guests {{ color: #e8c97a; font-size: 13px; margin-top: 6px; font-style: italic; }}
.header .dates {{ color: #8a9ab5; font-size: 11px; margin-top: 2px; }}

.hero {{
    text-align: center;
    margin: 10px 0 16px;
}}
.hero img {{
    width: 100%;
    max-width: 100%;
    height: 220px;
    object-fit: cover;
    border: 1px solid #c9a84c;
    border-radius: 4px;
}}

.info-box {{
    background: #152540;
    border: 1px solid #1e3358;
    border-radius: 6px;
    padding: 12px 16px;
    margin: 10px 0;
}}
.info-box h3 {{ color: #c9a84c; margin-bottom: 6px; }}
.info-box p, .info-box li {{ color: #e8e0d0; font-size: 10.5px; line-height: 1.5; }}
.info-box ul {{ list-style: none; padding-left: 0; }}
.info-box ul li {{ padding: 2px 0; }}
.info-box .label {{ color: #8a9ab5; font-weight: 600; }}
.info-box .highlight {{ color: #e8c97a; font-weight: 600; }}
.info-box .paid {{ color: #4ecf7a; font-weight: 700; }}

.alert-box {{
    background: #2a1a10;
    border: 1px solid #c9a84c;
    border-left: 4px solid #c9a84c;
    border-radius: 4px;
    padding: 10px 14px;
    margin: 8px 0;
    font-size: 10.5px;
}}
.alert-box .alert-title {{ color: #e8c97a; font-weight: 700; font-size: 11px; margin-bottom: 4px; }}

.day-card {{
    background: #152540;
    border: 1px solid #1e3358;
    border-radius: 6px;
    margin: 12px 0;
    padding: 14px 16px;
    page-break-inside: avoid;
}}
.day-card .day-header {{
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 6px;
}}
.day-card .day-num {{ color: #c9a84c; font-size: 14px; font-weight: 700; }}
.day-card .day-title {{ color: #e8c97a; font-size: 13px; }}
.day-card .day-date {{ color: #8a9ab5; font-size: 10px; }}
.day-card .port-hours {{ color: #8a9ab5; font-size: 10px; font-style: italic; margin-bottom: 6px; }}
.day-card p {{ font-size: 10.5px; margin: 4px 0; }}
.day-card ul {{ list-style: none; padding-left: 0; }}
.day-card ul li {{ font-size: 10.5px; padding: 2px 0; }}

.tag-booked {{
    display: inline-block;
    background: #1a4a2a;
    color: #4ecf7a;
    font-size: 9px;
    font-weight: 700;
    padding: 1px 6px;
    border-radius: 3px;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}}
.tag-free {{
    display: inline-block;
    background: #4a3a10;
    color: #e8c97a;
    font-size: 9px;
    font-weight: 700;
    padding: 1px 6px;
    border-radius: 3px;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}}
.tag-dinner {{
    display: inline-block;
    background: #1e3358;
    color: #c9a84c;
    font-size: 9px;
    font-weight: 700;
    padding: 1px 6px;
    border-radius: 3px;
    letter-spacing: 0.5px;
}}

.img-port {{
    margin: 8px 0;
    text-align: center;
}}
.img-port img {{
    width: 100%;
    height: 200px;
    object-fit: cover;
    border-radius: 4px;
    border: 1px solid #1e3358;
}}
.img-sea {{
    margin: 8px 0;
    text-align: center;
}}
.img-sea img {{
    width: 100%;
    height: 140px;
    object-fit: cover;
    border-radius: 4px;
    border: 1px solid #1e3358;
    opacity: 0.85;
}}
.img-sea .art-label {{
    text-align: center;
    font-size: 0.65em;
    color: #4a5a75;
    letter-spacing: 1px;
    font-style: italic;
    margin-top: 2px;
}}

.dining-table, .cost-table, .contacts-table {{
    width: 100%;
    border-collapse: collapse;
    margin: 8px 0;
    font-size: 10.5px;
}}
.dining-table th, .cost-table th, .contacts-table th {{
    background: #1e3358;
    color: #c9a84c;
    text-align: left;
    padding: 6px 10px;
    font-size: 10px;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}}
.dining-table td, .cost-table td, .contacts-table td {{
    padding: 5px 10px;
    border-bottom: 1px solid #1e3358;
    color: #e8e0d0;
}}
.dining-table tr:nth-child(even), .cost-table tr:nth-child(even), .contacts-table tr:nth-child(even) {{
    background: #0d1b2e;
}}
.cost-table .total-row td {{
    color: #e8c97a;
    font-weight: 700;
    border-top: 2px solid #c9a84c;
    font-size: 11px;
}}

.footer {{
    text-align: center;
    margin-top: 20px;
    padding: 16px;
    border-top: 1px solid #1e3358;
}}
.footer .headshot {{
    width: 50px;
    height: 50px;
    border-radius: 50%;
    border: 2px solid #c9a84c;
    margin-bottom: 6px;
}}
.footer .name {{ color: #c9a84c; font-size: 13px; font-weight: 700; }}
.footer .title {{ color: #8a9ab5; font-size: 10px; }}
.footer .contact {{ color: #e8e0d0; font-size: 10px; margin-top: 2px; }}
.footer .slogan {{ color: #8a9ab5; font-size: 9px; font-style: italic; margin-top: 4px; letter-spacing: 1px; }}
.footer .footer-logo {{ height: 60px; opacity: 0.7; margin-top: 6px; }}

.transport-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    margin: 8px 0;
}}
.transport-grid .segment {{
    background: #0d1b2e;
    border: 1px solid #1e3358;
    border-radius: 4px;
    padding: 8px 10px;
}}
.transport-grid .segment .seg-label {{
    color: #c9a84c;
    font-size: 9px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}
.transport-grid .segment .seg-detail {{
    color: #e8e0d0;
    font-size: 10px;
    margin-top: 2px;
}}
.transport-grid .segment .seg-conf {{
    color: #8a9ab5;
    font-size: 9px;
    margin-top: 1px;
}}
</style>
</head>
<body>

<!-- SECTION 1: HEADER -->
<div class="header">
    <img src="{logo_uri}" class="logo" alt="D2M Logo">
    <h1>Silver Nova</h1>
    <div class="subtitle">Tokyo &middot; Yokohama &middot; Alaska Inside Passage &middot; Seattle</div>
    <div class="dates">April 21 &ndash; May 11, 2026 &middot; 22 Days</div>
    <div class="guests">Prepared for Ronald &ldquo;Rondo&rdquo; &amp; Lindy Westbrook</div>
</div>

<!-- HERO IMAGE -->
<div class="hero">
    <img src="{hero_uri}" alt="Silver Nova">
</div>

<!-- SECTION 2: SHIP INFO -->
<div class="info-box">
    <h3>Silversea &middot; Silver Nova</h3>
    <p>Evolution-class &middot; 728 guests &middot; All-suite, all-inclusive</p>
    <p>S.A.L.T. culinary program &middot; Otium Spa &middot; La Dame by Relais &amp; Ch&acirc;teaux &middot; Silver Note jazz</p>
    <ul>
        <li><span class="label">Booking:</span> #566904-25 &middot; Voyage SN260423019</li>
        <li><span class="label">Cabin:</span> 7031 &mdash; Superior Veranda Suite</li>
        <li><span class="label">Fare:</span> <span class="highlight">$5,400 &times; 2 = $10,800</span> &middot; <span class="paid">PAID IN FULL</span></li>
        <li><span class="label">Agent:</span> Ms. Jenna Woodcock &middot; +1 512-691-4501</li>
    </ul>
</div>

<!-- SECTION 3: TRAVELERS & DOCUMENTS -->
<div class="info-box">
    <h3>Travelers &amp; Documents</h3>
    <ul>
        <li><span class="label">Rondo:</span> E-Ticket 016 7337230403 &middot; Passport Feb 2026&ndash;Feb 2036 &#10003;</li>
        <li><span class="label">Lindy:</span> E-Ticket 016 7337230404 &middot; Passport Feb 2025&ndash;Feb 2035 &#10003;</li>
        <li><span class="label">Companions:</span> John &amp; Susie Loucks &mdash; Party of 4 for all dining &amp; excursions</li>
        <li><span class="label">Insurance:</span> Allianz Annual Premier $15K &middot; Conf E2549991663 &middot; <span class="highlight">$1,530</span></li>
        <li><span class="label">Claims:</span> 1-800-334-7525 &middot; 24hr US: 1-800-654-1908 &middot; Int'l: 1-804-281-5700</li>
    </ul>
</div>

<div class="alert-box">
    <div class="alert-title">&#9888; VISIT JAPAN WEB &mdash; Required Before Departure</div>
    Register at <strong>vjw.digital.go.jp</strong> &mdash; both Rondo and Lindy must complete separately. QR codes needed at NRT immigration.
</div>

<!-- SECTION 4: TRANSPORTATION -->
<h2>Transportation &amp; Accommodation</h2>

<div class="info-box">
    <h3>Pre-Cruise</h3>
    <div class="transport-grid">
        <div class="segment">
            <div class="seg-label">Home Pickup</div>
            <div class="seg-detail">Tue Apr 21, 7:30 AM &middot; Marcus</div>
            <div class="seg-conf">Monument, CO &rarr; DEN</div>
        </div>
        <div class="segment">
            <div class="seg-label">Flight Out &mdash; UA 143</div>
            <div class="seg-detail">DEN &rarr; NRT &middot; 11:35 AM &rarr; 2:45 PM (+1)</div>
            <div class="seg-conf">Premium Economy &middot; 21A &amp; 21C &middot; Conf I0Y9VG / GQLRAF</div>
        </div>
        <div class="segment">
            <div class="seg-label">NRT Transfer &mdash; Transferz</div>
            <div class="seg-detail">Private sedan &middot; Meet &amp; Greet T1</div>
            <div class="seg-conf">Itin #73268402723830 &middot; $209.55</div>
        </div>
        <div class="segment">
            <div class="seg-label">Hotel &mdash; Hilton Tokyo Odaiba</div>
            <div class="seg-detail">1 night &middot; Apr 22&ndash;23 &middot; King room</div>
            <div class="seg-conf">Conf #33S2013960 &middot; &yen;73,364 (~$480)</div>
        </div>
        <div class="segment">
            <div class="seg-label">Hotel &rarr; Port &mdash; Blacklane</div>
            <div class="seg-detail">Private sedan &middot; 4 pax &middot; 10:30 AM</div>
            <div class="seg-conf">Conf PE146862609 &middot; $156</div>
        </div>
    </div>
</div>

<div class="info-box">
    <h3>Post-Cruise</h3>
    <div class="transport-grid">
        <div class="segment">
            <div class="seg-label">SEA Transfer</div>
            <div class="seg-detail">Pier 91 &rarr; SEA-TAC &middot; ~9:30 AM</div>
            <div class="seg-conf">&#9888; Planned for Silversea Transportation</div>
        </div>
        <div class="segment">
            <div class="seg-label">Flight Home &mdash; UA 757</div>
            <div class="seg-detail">SEA &rarr; DEN &middot; 12:46 PM &rarr; 4:30 PM</div>
            <div class="seg-conf">Economy &middot; 2h44m &middot; Conf I0Y9VG</div>
        </div>
    </div>
</div>

<!-- SECTION 5: DAY-BY-DAY -->
<h2 style="margin-top:16px;">Day-by-Day Itinerary</h2>

<!-- DAY 1 -->
<div class="day-card">
    <div class="day-header">
        <span class="day-num">Day 1</span>
        <span class="day-title">Departure Day</span>
        <span class="day-date">Tuesday, April 21</span>
    </div>
    {port_img("day1", "Tokyo departure")}
    <ul>
        <li><strong>7:30 AM</strong> &mdash; Marcus pickup, Monument CO &rarr; DEN</li>
        <li><strong>11:35 AM</strong> &mdash; UA 143 DEN &rarr; NRT &middot; Premium Economy, Seats 21A &amp; 21C</li>
        <li>Cross the Pacific &mdash; arrive tomorrow afternoon Japan time</li>
    </ul>
</div>

<!-- DAY 2 -->
<div class="day-card">
    <div class="day-header">
        <span class="day-num">Day 2</span>
        <span class="day-title">Arrive Tokyo</span>
        <span class="day-date">Wednesday, April 22</span>
    </div>
    {port_img("day2", "Hilton Tokyo Odaiba")}
    <ul>
        <li><strong>2:45 PM</strong> &mdash; Arrive NRT &middot; Visit Japan Web QR codes ready</li>
        <li><strong>~3:30 PM</strong> &mdash; Transferz sedan Meet &amp; Greet at Terminal 1</li>
        <li><strong>~5:00 PM</strong> &mdash; Check in Hilton Tokyo Odaiba &middot; Conf #33S2013960</li>
        <li>Evening: Rest, explore Odaiba, Rainbow Bridge views</li>
    </ul>
</div>

<!-- DAY 3 -->
<div class="day-card">
    <div class="day-header">
        <span class="day-num">Day 3</span>
        <span class="day-title">Embarkation &middot; Yokohama</span>
        <span class="day-date">Thursday, April 23</span>
    </div>
    {port_img("day3", "Yokohama Port")}
    <ul>
        <li>Morning: AP Honors Breakfast at Hilton</li>
        <li><strong>10:30 AM</strong> &mdash; Blacklane pickup &rarr; Yokohama Port Shinko Terminal</li>
        <li><strong>~12:30 PM</strong> &mdash; Explore Red Brick Warehouses and Cosmo Clock Ferris Wheel</li>
        <li>Afternoon: Board Silver Nova &mdash; Cabin 7031 Superior Veranda Suite</li>
        <li><strong>7:00 PM</strong> &mdash; Ship departs Yokohama</li>
        <li><span class="tag-dinner">DINNER</span> La Terrazza &mdash; 18:30/19:30 (Party of 4)</li>
    </ul>
</div>

<!-- DAY 4 -->
<div class="day-card">
    <div class="day-header">
        <span class="day-num">Day 4</span>
        <span class="day-title">At Sea &mdash; Kuril Islands</span>
        <span class="day-date">Friday, April 24</span>
    </div>
    {sea_img("day4", "Kuril Islands", "KURIL ISLANDS &middot; SAILING FROM JAPAN")}
    <p>First full day aboard Silver Nova. Explore the ship &mdash; Otium Spa, S.A.L.T. Kitchen, pool deck. Attend the port talk for Miyako.</p>
</div>

<!-- DAY 5 -->
<div class="day-card">
    <div class="day-header">
        <span class="day-num">Day 5</span>
        <span class="day-title">Miyako, Iwate</span>
        <span class="day-date">Saturday, April 25</span>
    </div>
    <div class="port-hours">8:00 AM &ndash; 5:00 PM</div>
    {port_img("day5", "Miyako")}
    <p><span class="tag-booked">BOOKED</span> <strong>Jodogahama &amp; Ryusendo</strong> &mdash; 8:45 AM, ~4 hrs, Moderate</p>
    <ul>
        <li>Jodogahama Beach &mdash; white quartz cliffs, emerald water</li>
        <li>Ryusendo Cave &mdash; limestone caves with crystal-blue underground lakes</li>
    </ul>
</div>

<!-- DAY 6 -->
<div class="day-card">
    <div class="day-header">
        <span class="day-num">Day 6</span>
        <span class="day-title">Aomori</span>
        <span class="day-date">Sunday, April 26</span>
    </div>
    <div class="port-hours">8:00 AM &ndash; 4:00 PM</div>
    {port_img("day6", "Aomori")}
    <p><span class="tag-free">FREE TO EXPLORE</span></p>
    <ul>
        <li>Nebuta Museum Wa Rasse &mdash; illuminated festival floats</li>
        <li>A-FACTORY cidery &amp; crafts market</li>
        <li>Auga Fresh Market &mdash; local seafood, produce</li>
    </ul>
    <p><span class="tag-dinner">DINNER</span> The Grill &mdash; 18:30/19:30 (Party of 4)</p>
</div>

<!-- DAY 7 -->
<div class="day-card">
    <div class="day-header">
        <span class="day-num">Day 7</span>
        <span class="day-title">At Sea</span>
        <span class="day-date">Monday, April 27</span>
    </div>
    {sea_img("day7", "North Pacific")}
    <p>The Pacific crossing begins. Butler service, Otium Spa, enrichment lectures. Settle into ocean life.</p>
</div>

<!-- DAY 8 -->
<div class="day-card">
    <div class="day-header">
        <span class="day-num">Day 8</span>
        <span class="day-title">At Sea</span>
        <span class="day-date">Tuesday, April 28</span>
    </div>
    {sea_img("day8", "Pacific Ocean")}
    <p>Ocean crossing rhythm &mdash; all-inclusive luxury dining, pool deck, the rhythm of the open Pacific.</p>
</div>

<!-- DAY 9 -->
<div class="day-card">
    <div class="day-header">
        <span class="day-num">Day 9</span>
        <span class="day-title">At Sea</span>
        <span class="day-date">Wednesday, April 29</span>
    </div>
    {sea_img("day9", "Mid-Pacific")}
    <p>Mid-Pacific. Wine tastings, Superior Veranda views, ocean in every direction.</p>
    <p><span class="tag-dinner">DINNER</span> Silver Note &mdash; 18:30/19:30 (Party of 4) &mdash; Jazz &amp; fine dining</p>
</div>

<!-- DAY 10 -->
<div class="day-card">
    <div class="day-header">
        <span class="day-num">Day 10</span>
        <span class="day-title">International Date Line</span>
        <span class="day-date">Thursday, April 30</span>
    </div>
    {sea_img("day10", "International Date Line")}
    <p>Crossing the International Date Line eastbound &mdash; <strong>you gain a day!</strong> Live April 30th twice.</p>
</div>

<!-- DAY 11 -->
<div class="day-card">
    <div class="day-header">
        <span class="day-num">Day 11</span>
        <span class="day-title">Bonus Day at Sea</span>
        <span class="day-date">Thursday, April 30 (repeated)</span>
    </div>
    {sea_img("day11", "Bonus Day")}
    <p>Your bonus 24 hours &mdash; a gift of the Date Line. Now sailing in the Eastern Hemisphere.</p>
</div>

<!-- DAY 12 -->
<div class="day-card">
    <div class="day-header">
        <span class="day-num">Day 12</span>
        <span class="day-title">At Sea</span>
        <span class="day-date">Friday, May 1</span>
    </div>
    {sea_img("day12", "Pacific sunset")}
    <p>Approaching the North Pacific. Cooler temperatures &mdash; perfect whale-watching conditions from the veranda.</p>
    <p><span class="tag-dinner">DINNER</span> La Terrazza &mdash; 18:30/19:30 (Party of 4)</p>
</div>

<!-- DAY 13 -->
<div class="day-card">
    <div class="day-header">
        <span class="day-num">Day 13</span>
        <span class="day-title">At Sea</span>
        <span class="day-date">Saturday, May 2</span>
    </div>
    {sea_img("day13", "Approaching Alaska")}
    <p>Final full sea day before Kodiak. Pack your layers &mdash; Alaska will be 40&ndash;50&deg;F. Last chance for pool-deck lounging.</p>
</div>

<!-- DAY 14 -->
<div class="day-card">
    <div class="day-header">
        <span class="day-num">Day 14</span>
        <span class="day-title">Kodiak Island</span>
        <span class="day-date">Sunday, May 3</span>
    </div>
    <div class="port-hours">12:00 PM &ndash; 7:00 PM</div>
    {port_img("day14", "Kodiak bear cub")}
    <p><span class="tag-free">FREE TO EXPLORE</span> &mdash; 5-hour port call</p>
    <ul>
        <li>Baranov Museum &mdash; oldest Russian-American building in Alaska</li>
        <li>Holy Resurrection Cathedral &mdash; Russian Orthodox landmark</li>
        <li>Harbor walk &mdash; fresh Kodiak seafood</li>
        <li>Optional taxi: Fort Abercrombie State Historical Park</li>
    </ul>
</div>

<!-- DAY 15 -->
<div class="day-card">
    <div class="day-header">
        <span class="day-num">Day 15</span>
        <span class="day-title">At Sea &mdash; Gulf of Alaska</span>
        <span class="day-date">Monday, May 4</span>
    </div>
    {sea_img("day15", "Gulf of Alaska glacier")}
    <p>Sailing the Gulf of Alaska toward the Inside Passage. Watch for humpback whales from the veranda.</p>
    <p><span class="tag-dinner">DINNER</span> The Grill &mdash; 18:30/19:30 (Party of 4)</p>
</div>

<!-- DAY 16 -->
<div class="day-card">
    <div class="day-header">
        <span class="day-num">Day 16</span>
        <span class="day-title">Sitka</span>
        <span class="day-date">Tuesday, May 5</span>
    </div>
    <div class="port-hours">9:00 AM &ndash; 5:00 PM &middot; Tender Port</div>
    {port_img("day16", "Sitka")}
    <p><span class="tag-free">FREE TO EXPLORE</span></p>
    <ul>
        <li>Sitka National Historical Park &mdash; Totem Trail through temperate rainforest</li>
        <li>Alaska Raptor Center &mdash; bald eagles and rehabilitation</li>
        <li>St. Michael's Cathedral &mdash; Russian colonial era</li>
        <li>Fortress of the Bear &mdash; rescued brown bears</li>
        <li>Whale watching in Sitka Sound</li>
    </ul>
</div>

<!-- DAY 17 -->
<div class="day-card">
    <div class="day-header">
        <span class="day-num">Day 17</span>
        <span class="day-title">Juneau</span>
        <span class="day-date">Wednesday, May 6</span>
    </div>
    <div class="port-hours">9:00 AM &ndash; 7:00 PM</div>
    {port_img("day17", "Juneau")}
    <p><span class="tag-booked">BOOKED</span> <strong>Juneau Gold &mdash; Underground Mining Heritage</strong> &mdash; 10:00 AM, ~2h15m, Minimal</p>
    <ul>
        <li>Historic gold mine tour with underground exploration</li>
        <li>Free time: Mendenhall Glacier, Mt Roberts Tramway, Red Dog Saloon</li>
    </ul>
</div>

<!-- DAY 18 -->
<div class="day-card">
    <div class="day-header">
        <span class="day-num">Day 18</span>
        <span class="day-title">Wrangell</span>
        <span class="day-date">Thursday, May 7</span>
    </div>
    <div class="port-hours">12:00 PM &ndash; 7:00 PM</div>
    {port_img("day18", "Wrangell totem poles")}
    <ul>
        <li>Walk to Petroglyph Beach &mdash; 8,000-year-old rock carvings</li>
        <li>Chief Shakes Tribal House &amp; totem poles</li>
    </ul>
    <p><span class="tag-booked">BOOKED</span> <strong>Tongass Botanicals Nature Walk</strong> &mdash; 4:00 PM, ~1h30m, Extensive</p>
    <p><span class="tag-dinner">DINNER</span> La Terrazza &mdash; 18:30/19:30 (Party of 4)</p>
</div>

<!-- DAY 19 -->
<div class="day-card">
    <div class="day-header">
        <span class="day-num">Day 19</span>
        <span class="day-title">Ketchikan</span>
        <span class="day-date">Friday, May 8</span>
    </div>
    <div class="port-hours">8:00 AM &ndash; 4:00 PM</div>
    {port_img("day19", "Ketchikan")}
    <p><span class="tag-booked">BOOKED</span> <strong>Ketchikan by Land &amp; Sea</strong> &mdash; 10:00 AM, ~1h30m, Minimal</p>
    <ul>
        <li>Free time: Creek Street boardwalk, Totem Heritage Center, Saxman Village</li>
    </ul>
</div>

<!-- DAY 20 -->
<div class="day-card">
    <div class="day-header">
        <span class="day-num">Day 20</span>
        <span class="day-title">Inside Passage &mdash; Scenic Cruising</span>
        <span class="day-date">Saturday, May 9</span>
    </div>
    {port_img("day20", "Inside Passage")}
    <p>All-day scenic cruising through the legendary Inside Passage &mdash; narrow channels, forested islands, fjords. Watch for humpback whales, orcas, and bald eagles from the deck.</p>
    <p><span class="tag-dinner">DINNER</span> The Grill &mdash; 18:30/19:30 &mdash; <strong>Final specialty dinner!</strong> (Party of 4)</p>
</div>

<!-- DAY 21 -->
<div class="day-card">
    <div class="day-header">
        <span class="day-num">Day 21</span>
        <span class="day-title">Victoria, BC</span>
        <span class="day-date">Sunday, May 10</span>
    </div>
    <div class="port-hours">9:00 AM &ndash; 7:00 PM</div>
    {port_img("day21", "Victoria BC")}
    <p><span class="tag-free">FREE TO EXPLORE</span></p>
    <ul>
        <li>Inner Harbour &mdash; stunning waterfront, street performers</li>
        <li>Fairmont Empress &mdash; iconic afternoon tea</li>
        <li>Butchart Gardens &mdash; world-famous botanical gardens (taxi or shuttle)</li>
        <li>Fisherman's Wharf &mdash; floating homes, fish &amp; chips</li>
    </ul>
</div>

<!-- DAY 22 -->
<div class="day-card">
    <div class="day-header">
        <span class="day-num">Day 22</span>
        <span class="day-title">Seattle &amp; Home</span>
        <span class="day-date">Monday, May 11</span>
    </div>
    {port_img("day22", "Seattle")}
    <ul>
        <li><strong>7:00 AM</strong> &mdash; Arrive Seattle, debarkation</li>
        <li><strong>~9:30 AM</strong> &mdash; Transfer Pier 91 &rarr; SEA-TAC &middot; <em>&#9888; Planned for Silversea Transport</em></li>
        <li><strong>12:46 PM</strong> &mdash; UA 757 SEA &rarr; DEN &middot; 2h44m nonstop</li>
        <li><strong>4:30 PM</strong> &mdash; Arrive Denver</li>
        <li><strong>~5:30 PM</strong> &mdash; Home to Monument, CO</li>
    </ul>
</div>

<!-- SECTION 6: DINING RESERVATIONS -->
<h2 style="margin-top:16px;">Specialty Dining Reservations</h2>
<div class="info-box">
    <p style="margin-bottom:6px;">Party of 4 &mdash; Westbrooks + Loucks &middot; All Included ($0)</p>
    <table class="dining-table">
        <thead>
            <tr><th>Date</th><th>Evening</th><th>Restaurant</th><th>Time</th></tr>
        </thead>
        <tbody>
            <tr><td>Apr 23</td><td>Embarkation Night</td><td>La Terrazza</td><td>18:30 / 19:30</td></tr>
            <tr><td>Apr 26</td><td>Aomori Port Day</td><td>The Grill</td><td>18:30 / 19:30</td></tr>
            <tr><td>Apr 29</td><td>Sea Day</td><td>Silver Note</td><td>18:30 / 19:30</td></tr>
            <tr><td>May 1</td><td>Sea Day</td><td>La Terrazza</td><td>18:30 / 19:30</td></tr>
            <tr><td>May 4</td><td>Sea Day</td><td>The Grill</td><td>18:30 / 19:30</td></tr>
            <tr><td>May 7</td><td>Wrangell Port Day</td><td>La Terrazza</td><td>18:30 / 19:30</td></tr>
            <tr><td>May 9</td><td>Inside Passage</td><td>The Grill</td><td>18:30 / 19:30</td></tr>
        </tbody>
    </table>
</div>

<!-- SECTION 7: COST SUMMARY -->
<h2 style="margin-top:16px;">Cost Summary</h2>
<div class="info-box">
    <table class="cost-table">
        <thead>
            <tr><th>Item</th><th style="text-align:right;">Cost</th></tr>
        </thead>
        <tbody>
            <tr><td>Flights &mdash; 2 adults (UA 143 + UA 757)</td><td style="text-align:right;">$4,190.00</td></tr>
            <tr><td>Narita Transfer (Transferz)</td><td style="text-align:right;">$209.55</td></tr>
            <tr><td>Hilton Tokyo Odaiba &mdash; 1 night</td><td style="text-align:right;">~$480.00</td></tr>
            <tr><td>Hotel &rarr; Yokohama Port (Blacklane, 4 pax)</td><td style="text-align:right;">$156.00</td></tr>
            <tr><td>Silversea Cruise &mdash; 2 guests (PAID IN FULL)</td><td style="text-align:right;">$10,800.00</td></tr>
            <tr><td>Allianz Travel Insurance &mdash; Annual Premier</td><td style="text-align:right;">$1,530.00</td></tr>
            <tr><td>Seattle Terminal &rarr; SEA-TAC</td><td style="text-align:right;">Silversea</td></tr>
            <tr class="total-row"><td>ESTIMATED TOTAL</td><td style="text-align:right;">~$17,365.55 + SEA transfer</td></tr>
        </tbody>
    </table>
</div>

<!-- SECTION 8: KEY CONTACTS -->
<h2 style="margin-top:16px;">Key Contacts</h2>
<div class="info-box">
    <table class="contacts-table">
        <thead>
            <tr><th>Who</th><th>Phone</th><th>Notes</th></tr>
        </thead>
        <tbody>
            <tr><td>United Re-protection</td><td>1-888-885-5890</td><td>Schedule changes</td></tr>
            <tr><td>Allianz Claims</td><td>1-800-334-7525</td><td>Insurance claims</td></tr>
            <tr><td>Allianz 24hr (US)</td><td>1-800-654-1908</td><td>Emergency assistance</td></tr>
            <tr><td>Allianz 24hr (Int'l)</td><td>1-804-281-5700</td><td>Collect calls accepted</td></tr>
            <tr><td>Transferz</td><td>+1 252-656-9317</td><td>support@transferz.com</td></tr>
            <tr><td>Hilton Tokyo Odaiba</td><td>+81 3-5500-5500</td><td>Hotel direct</td></tr>
            <tr><td>Jenna Woodcock</td><td>+1 512-691-4501</td><td>Interline Travel &amp; Tour</td></tr>
        </tbody>
    </table>
</div>

<!-- SECTION 9: OPEN ITEMS -->
<h2 style="margin-top:16px;">Open Items</h2>
<div class="alert-box">
    <div class="alert-title">&#9888; Seattle Cruise Terminal &rarr; SEA-TAC Transfer</div>
    Not yet booked. Planned for Silversea complimentary transportation &mdash; confirm closer to sailing.
</div>
<div class="alert-box">
    <div class="alert-title">&#9888; Visit Japan Web Registration</div>
    Both Rondo and Lindy must register separately at <strong>vjw.digital.go.jp</strong> before departure. QR codes required at NRT immigration.
</div>
<div class="alert-box">
    <div class="alert-title">&#9888; UA Re-Protection Notice</div>
    Original UA 1351 re-protected to confirmed UA 757 (SEA &rarr; DEN). Monitor for further schedule changes.
</div>

<!-- FOOTER -->
<div class="footer">
    <img src="{headshot_uri}" class="headshot" alt="John Loucks"><br>
    <div class="name">John A. Loucks III</div>
    <div class="title">Owner, Dreams2Memories Travel, LLC</div>
    <div class="contact">719-291-0742 &middot; johnloucks3@gmail.com</div>
    <div class="slogan">&ldquo;Curating the experience of a lifetime&rdquo;</div>
    <br>
    <img src="{logo_small_uri}" class="footer-logo" alt="D2M Logo">
</div>

</body>
</html>
"""

out_path = OUT_DIR / "Westbrook_Silver_Nova_Apr2026.html"
out_path.write_text(html, encoding="utf-8")
print(f"HTML written to {out_path}")
print(f"HTML size: {out_path.stat().st_size:,} bytes")
