#!/usr/bin/env python3
"""
Westbrook Silver Nova Trans-Pacific — Final Itinerary Generator
Dreams2Memories Travel, LLC
Luna (A6) Creative Lead | COS Orchestration | EXEC Brand Polish

Produces: output/Westbrook_SilverNova_Final.html + .pdf
"""

import subprocess, json, sys, os
from pathlib import Path
from datetime import datetime

# ── CONFIG ────────────────────────────────────────────────────────────────────
PEXELS_KEY   = "***REMOVED-SECRET***"
OUTPUT_DIR   = Path("/home/john/Thunderbird/output")
LOGO_B64_FILE= Path("/home/john/Thunderbird/output/logo_small_b64.txt")
HTML_OUT     = OUTPUT_DIR / "Westbrook_SilverNova_Final.html"
PDF_OUT      = OUTPUT_DIR / "Westbrook_SilverNova_Final.pdf"

# ── BRAND PALETTE ─────────────────────────────────────────────────────────────
NAVY   = "#0d1b2e"
CREAM  = "#f7f3ea"
LINEN  = "#eee8db"
BLUE   = "#0000ff"
GOLD   = "#c9a84c"
SLATE  = "#34495e"
MIST   = "#7f8c8d"

# ── SEA DAY NARRATIVES (Silver Nova-specific, Luna voice) ─────────────────────
SEA_NARRATIVES = {
    2:  ("The Open Pacific",
         "As Japan's shores dissolve into morning mist, Silver Nova finds her rhythm on the open Pacific — "
         "a vast indigo canvas stretching to every horizon. Stand on your veranda and feel the salt-kissed "
         "breeze as the ship glides through waters that have separated ancient civilizations from the wild north. "
         "The journey has truly begun."),
    5:  ("Life Aboard at Sea",
         "Halfway across the world's mightiest ocean, Silver Nova becomes her own small paradise. "
         "The pool deck shimmers under Pacific sunlight as you drift between cocktail-hour conversation "
         "and the hypnotic cadence of blue water below. "
         "This is the luxury of distance — the world quietly left behind."),
    6:  ("An Evening on the Pacific",
         "As the Pacific sun dissolves into bands of coral and gold, La Terrazza fills with the soft clink "
         "of crystal and murmured conversation. Every evening at sea is a private dinner party — "
         "the horizon your only neighbor, the ocean your soundtrack. Tonight, linger."),
    7:  ("The Observation Lounge",
         "The Observation Lounge earns its name today: walls of glass frame an endless Pacific wilderness, "
         "waves building with restless energy beneath a sky of bruised slate and silver. "
         "Settle into a deep chair with your favorite drink and watch the ocean do what it has done for millennia — "
         "no agenda, no destination, just the sea."),
    8:  ("Date Line — You Gain a Day",
         "Somewhere in the night, without a sound, Silver Nova crossed the International Date Line — "
         "and you gained a day, as if the Pacific reached into its pockets and handed you twenty-four hours. "
         "Step onto your veranda as twin dawns seem to merge; the ocean looks exactly the same, "
         "yet everything is slightly, wonderfully different. Some gifts come wrapped in longitude."),
    9:  ("The North Pacific Corridor",
         "The Pacific is changing character — deepening from tropical blue to the cold jade of the North Pacific, "
         "the horizon taking on the silver clarity that means latitude. "
         "This is the Kuril corridor, one of the planet's great seaways, "
         "and Silver Nova threads it with quiet authority. Watch for sea birds; they are the first signs that Alaska is drawing close."),
    10: ("Chasing the Aurora",
         "The sun barely dips below the horizon before the sky begins to move. "
         "In these high latitudes, if you are fortunate, the aurora borealis dances above the ship — "
         "green curtains rippling in silence, their reflection shivering on dark Arctic water below. "
         "Stay on deck. This is the kind of night that replaces ordinary nights permanently."),
    11: ("Alaska Draws Near",
         "Alaska announces itself slowly: a scent of spruce and cold salt water, "
         "clouds that carry a different weight, mountains ghosting in and out of mist on the far horizon. "
         "Another night of possibility — the aurora may return, or the Milky Way may take its place, "
         "arching over a Silver Nova nearly alone on these northern seas. Either way, look up."),
    13: ("A Sea Day Between Wild Places",
         "After the raw grandeur of Kodiak, Silver Nova offers its quietest gift: a day of pure ship. "
         "The Otium Spa calls with warm stone therapy and the sound of the Alaskan sea against the hull. "
         "Alaska is on the other side of the glass — its eagles, its glaciers, its silence — "
         "and you are here, balanced perfectly between wilderness and luxury."),
    18: ("Silver Note — Last Sea Day",
         "On this last sea day before Vancouver Island, the Silver Note opens early. "
         "Jazz floats through the ship like woodsmoke — a saxophone threading through Pacific Northwest light, "
         "the coastline of Canada just there on the horizon. "
         "This passage is ending; raise a glass to nineteen extraordinary days."),
}

# ── DINING SCHEDULE ───────────────────────────────────────────────────────────
DINING = {
    "2026-04-23": ("La Terrazza", "18:30"),
    "2026-04-26": ("The Grill", "18:30"),
    "2026-04-29": ("Silver Note", "18:30"),
    "2026-05-01": ("La Terrazza", "18:30"),
    "2026-05-04": ("The Grill", "18:30"),
    "2026-05-07": ("La Terrazza", "18:30"),
    "2026-05-09": ("The Grill", "18:30"),
}

# ── 20-DAY ITINERARY DATA ─────────────────────────────────────────────────────
# (day, date_str, port, is_sea, pexels_id, dock, depart, excursion)
DAYS = [
    (1,  "2026-04-23", "Tokyo (Harumi), Japan",          False, 23023919, "10:30 AM transfer", "7:00 PM",   ""),
    (2,  "2026-04-24", "Day at Sea",                     True,  12422952, "", "",               ""),
    (3,  "2026-04-25", "Miyako, Iwate, Japan",            False, 7833735,  "8:00 AM",           "5:00 PM",   "Jodogahama & Ryusendo — 8:45 AM · ~4 hrs · Moderate"),
    (4,  "2026-04-26", "Aomori, Japan",                  False, 15925248, "7:00 AM",           "6:00 PM",   "Free to Explore"),
    (5,  "2026-04-27", "Day at Sea",                     True,  20199321, "", "",               ""),
    (6,  "2026-04-28", "Day at Sea",                     True,  5769594,  "", "",               ""),
    (7,  "2026-04-29", "Day at Sea",                     True,  813011,   "", "",               ""),
    (8,  "2026-04-30", "Date Line — Gain a Day",         True,  30037143, "", "",               ""),
    (9,  "2026-04-30", "Day at Sea",                     True,  5802999,  "", "",               ""),
    (10, "2026-05-01", "Day at Sea",                     True,  8932585,  "", "",               ""),
    (11, "2026-05-02", "Day at Sea",                     True,  4573211,  "", "",               ""),
    (12, "2026-05-03", "Kodiak Island, Alaska",          False, 17444649, "12:00 PM",          "7:00 PM",   "Free to Explore"),
    (13, "2026-05-04", "Day at Sea",                     True,  13048487, "", "",               ""),
    (14, "2026-05-05", "Sitka, Alaska",                  False, 34145844, "9:00 AM",           "5:00 PM",   "Free to Explore"),
    (15, "2026-05-06", "Juneau, Alaska",                 False, 12897647, "7:00 AM",           "4:00 PM",   "Gold — Underground Mining Heritage · 10:00 AM · ~2h 15m · Minimal"),
    (16, "2026-05-07", "Wrangell, Alaska",               False, 36075386, "8:00 AM",           "3:00 PM",   "Tongass Botanicals Nature Walk · 4:00 PM · ~1h 30m · Extensive"),
    (17, "2026-05-08", "Ketchikan, Alaska",              False, 12761922, "8:00 AM",           "3:00 PM",   "By Land & Sea · 10:00 AM · ~1h 30m · Minimal"),
    (18, "2026-05-09", "Day at Sea",                     True,  12530456, "", "",               ""),
    (19, "2026-05-10", "Victoria, British Columbia",     False, 35380038, "9:00 AM",           "7:00 PM",   "Free to Explore"),
    (20, "2026-05-11", "Seattle, Washington",            False, 28933961, "7:00 AM",           "",          "Disembarkation — Seattle Cruise Terminal"),
]

# ── PEXELS IMAGE FETCHER ──────────────────────────────────────────────────────
def get_pexels_photo(photo_id: int) -> dict:
    """Return {url, photographer, page_url} for a Pexels photo ID."""
    r = subprocess.run(
        ["curl", "-s", "-H", f"Authorization: {PEXELS_KEY}",
         f"https://api.pexels.com/v1/photos/{photo_id}"],
        capture_output=True, text=True
    )
    try:
        d = json.loads(r.stdout)
        return {
            "url":          d["src"]["large2x"],
            "photographer": d.get("photographer", "Pexels"),
            "page_url":     d.get("url", ""),
        }
    except Exception as e:
        print(f"  ⚠ Pexels {photo_id}: {e}")
        return {"url": "", "photographer": "", "page_url": ""}


def get_logo_b64() -> str:
    try:
        return LOGO_B64_FILE.read_text().strip()
    except Exception:
        return ""


# ── DATE FORMATTER ────────────────────────────────────────────────────────────
def fmt_date(ds: str) -> str:
    try:
        return datetime.strptime(ds, "%Y-%m-%d").strftime("%B %-d, %Y")
    except Exception:
        return ds


# ── HTML TEMPLATE ─────────────────────────────────────────────────────────────
def render_html(days_data: list, logo_b64: str) -> str:
    logo_src = f"data:image/png;base64,{logo_b64}" if logo_b64 else ""

    day_cards = []
    for d in days_data:
        day_num   = d["day"]
        date_str  = fmt_date(d["date"])
        port      = d["port"]
        is_sea    = d["is_sea"]
        img_url   = d["img_url"]
        photo_cred= d["photographer"]
        narrative = d["narrative"]
        dock      = d["dock"]
        depart    = d["depart"]
        excursion = d["excursion"]
        dining    = d.get("dining", "")

        # Day type badge
        badge_bg  = "#2c5f8a" if is_sea else NAVY
        badge_txt = "Day at Sea" if is_sea else "Port of Call"

        # Arrival / departure line
        times_html = ""
        if dock and depart:
            times_html = f'<div class="times">Arrive {dock} &nbsp;·&nbsp; Depart {depart}</div>'
        elif dock:
            times_html = f'<div class="times">{dock}</div>'
        elif depart:
            times_html = f'<div class="times">Depart {depart}</div>'

        # Excursion block
        exc_html = ""
        if excursion and excursion != "Free to Explore" and excursion != "Disembarkation — Seattle Cruise Terminal":
            exc_html = f'''
            <div class="detail-block excursion-block">
              <span class="detail-icon">⚓</span>
              <span class="detail-label">Excursion</span>
              <span class="detail-text">{excursion}</span>
            </div>'''
        elif excursion:
            exc_html = f'''
            <div class="detail-block">
              <span class="detail-icon">📍</span>
              <span class="detail-text">{excursion}</span>
            </div>'''

        # Dining block
        din_html = ""
        if dining:
            restaurant, time = dining
            din_html = f'''
            <div class="detail-block dining-block">
              <span class="detail-icon">🍽</span>
              <span class="detail-label">Specialty Dining</span>
              <span class="detail-text">{restaurant} · {time}</span>
            </div>'''

        # Photo credit
        credit_html = f'<div class="photo-credit">Photo: {photo_cred} · Pexels</div>' if photo_cred else ""

        # Image block
        img_html = ""
        if img_url:
            img_html = f'''
            <div class="photo-wrap">
              <img src="{img_url}" alt="{port}" class="port-photo" />
              {credit_html}
            </div>'''

        day_cards.append(f'''
        <div class="day-card" id="day-{day_num}">
          <div class="day-header">
            <div class="day-left">
              <div class="day-number">Day {day_num}</div>
              <div class="day-date">{date_str}</div>
            </div>
            <div class="day-right">
              <div class="day-port">{port}</div>
              <div class="day-badge" style="background:{badge_bg}">{badge_txt}</div>
            </div>
          </div>
          {img_html}
          <div class="narrative">{narrative}</div>
          {times_html}
          {exc_html}
          {din_html}
        </div>
        ''')

    cards_html = "\n".join(day_cards)

    logo_banner = f'''
    <div class="logo-banner">
      <img src="{logo_src}" alt="Dreams2Memories Travel" class="logo-img" />
    </div>''' if logo_src else f'''
    <div class="logo-banner text-logo">
      <div class="text-logo-inner">Dreams2Memories Travel</div>
    </div>'''

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Ron & Lindy Westbrook — Silver Nova Trans-Pacific</title>
<style>
/* ─── RESET ────────────────────────────────────────────── */
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

/* ─── PAGE ─────────────────────────────────────────────── */
html {{ background: {LINEN}; }}
body {{
  font-family: Georgia, 'Times New Roman', serif;
  background: {LINEN};
  color: {SLATE};
  line-height: 1.65;
}}
.page {{
  max-width: 800px;
  margin: 0 auto;
  background: {CREAM};
  box-shadow: 0 2px 24px rgba(0,0,0,0.12);
}}

/* ─── LOGO BANNER ───────────────────────────────────────── */
.logo-banner {{
  background: {NAVY};
  padding: 28px 40px;
  text-align: center;
  border-bottom: 3px solid {GOLD};
}}
.logo-img {{ height: 70px; width: auto; }}
.text-logo-inner {{
  color: white;
  font-size: 1.4em;
  letter-spacing: 0.08em;
  font-style: italic;
}}

/* ─── COVER ─────────────────────────────────────────────── */
.cover {{
  background: {NAVY};
  color: white;
  padding: 60px 40px 50px;
  text-align: center;
  border-bottom: 4px solid {GOLD};
}}
.cover-eyebrow {{
  font-size: 0.85em;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: {GOLD};
  margin-bottom: 18px;
}}
.cover-title {{
  font-size: 2.4em;
  font-weight: normal;
  line-height: 1.2;
  margin-bottom: 14px;
}}
.cover-subtitle {{
  font-size: 1.15em;
  font-style: italic;
  color: rgba(255,255,255,0.85);
  margin-bottom: 28px;
}}
.cover-dates {{
  display: inline-block;
  border: 1px solid rgba(201,168,76,0.5);
  border-radius: 4px;
  padding: 10px 28px;
  font-size: 1.05em;
  color: {GOLD};
  letter-spacing: 0.05em;
  margin-bottom: 28px;
}}
.cover-meta {{
  font-size: 0.9em;
  color: rgba(255,255,255,0.7);
  line-height: 2;
}}
.cover-meta strong {{ color: rgba(255,255,255,0.95); }}

/* ─── VOYAGE SUMMARY BOX ────────────────────────────────── */
.summary-box {{
  padding: 36px 40px;
  border-bottom: 1px solid #ddd5c8;
  background: {CREAM};
}}
.summary-box h2 {{
  color: {NAVY};
  font-size: 1.05em;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  margin-bottom: 20px;
  padding-bottom: 10px;
  border-bottom: 2px solid {GOLD};
}}
.summary-grid {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px 32px;
}}
.summary-row {{ font-size: 0.92em; }}
.summary-label {{ color: {MIST}; font-size: 0.82em; text-transform: uppercase; letter-spacing: 0.08em; }}
.summary-value {{ color: {SLATE}; font-weight: bold; }}

/* ─── PRE-CRUISE SECTION ────────────────────────────────── */
.precruise {{
  padding: 32px 40px;
  border-bottom: 1px solid #ddd5c8;
  background: #faf7f2;
}}
.precruise h2 {{
  color: {NAVY};
  font-size: 1.05em;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  margin-bottom: 18px;
  padding-bottom: 10px;
  border-bottom: 2px solid {GOLD};
}}
.pre-item {{
  font-size: 0.9em;
  padding: 8px 0;
  border-bottom: 1px dotted #d5ccc0;
  display: flex;
  gap: 12px;
}}
.pre-item:last-child {{ border-bottom: none; }}
.pre-icon {{ color: {BLUE}; width: 20px; flex-shrink: 0; }}
.pre-text {{ color: {SLATE}; line-height: 1.5; }}

/* ─── SECTION HEADING ───────────────────────────────────── */
.section-heading {{
  background: {NAVY};
  color: white;
  text-align: center;
  padding: 20px 40px;
  font-size: 1em;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  border-top: 3px solid {GOLD};
  border-bottom: 3px solid {GOLD};
}}

/* ─── DAY CARD ──────────────────────────────────────────── */
.day-card {{
  padding: 36px 40px 32px;
  border-bottom: 1px solid #ddd5c8;
  page-break-inside: avoid;
}}
.day-card:last-child {{ border-bottom: none; }}

.day-header {{
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 22px;
  padding-bottom: 16px;
  border-bottom: 2px solid {GOLD};
}}
.day-left {{ flex-shrink: 0; margin-right: 20px; }}
.day-number {{
  font-size: 0.75em;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: {GOLD};
  margin-bottom: 4px;
}}
.day-date {{
  font-size: 0.85em;
  color: {MIST};
}}
.day-right {{ text-align: right; }}
.day-port {{
  font-size: 1.5em;
  color: {NAVY};
  font-weight: normal;
  line-height: 1.2;
  margin-bottom: 8px;
}}
.day-badge {{
  display: inline-block;
  font-size: 0.7em;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: white;
  padding: 3px 10px;
  border-radius: 2px;
}}

/* ─── PHOTO ─────────────────────────────────────────────── */
.photo-wrap {{
  margin: 0 0 20px;
  position: relative;
}}
.port-photo {{
  width: 100%;
  height: 340px;
  object-fit: cover;
  display: block;
  border-radius: 3px;
}}
.photo-credit {{
  font-size: 0.72em;
  color: {MIST};
  text-align: right;
  margin-top: 5px;
  font-style: italic;
}}

/* ─── NARRATIVE ─────────────────────────────────────────── */
.narrative {{
  font-size: 1em;
  line-height: 1.8;
  color: {BLUE};
  padding: 16px 20px;
  border-left: 3px solid {GOLD};
  background: rgba(247,243,234,0.6);
  margin-bottom: 16px;
  font-style: italic;
}}

/* ─── TIMES ─────────────────────────────────────────────── */
.times {{
  font-size: 0.82em;
  color: {MIST};
  letter-spacing: 0.06em;
  margin-bottom: 12px;
  text-transform: uppercase;
}}

/* ─── DETAIL BLOCKS ─────────────────────────────────────── */
.detail-block {{
  display: flex;
  align-items: baseline;
  gap: 10px;
  font-size: 0.88em;
  padding: 8px 0;
  border-top: 1px dotted #d5ccc0;
}}
.detail-icon {{ flex-shrink: 0; }}
.detail-label {{
  font-size: 0.8em;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: {MIST};
  flex-shrink: 0;
  min-width: 90px;
}}
.detail-text {{ color: {SLATE}; }}
.excursion-block .detail-label {{ color: #2c5f8a; }}
.dining-block .detail-label {{ color: #7b4f2e; }}

/* ─── FOOTER ────────────────────────────────────────────── */
.footer {{
  background: {NAVY};
  color: rgba(255,255,255,0.8);
  text-align: center;
  padding: 40px;
  border-top: 3px solid {GOLD};
}}
.footer .footer-name {{
  color: white;
  font-size: 1.1em;
  margin-bottom: 8px;
  font-style: italic;
}}
.footer .footer-line {{ font-size: 0.88em; margin: 4px 0; }}
.footer a {{ color: {GOLD}; text-decoration: none; }}

/* ─── PRINT / PDF ───────────────────────────────────────── */
@media print {{
  html, body {{ background: white; }}
  .page {{ box-shadow: none; max-width: 100%; }}
  .day-card {{ page-break-inside: avoid; }}
}}
@page {{
  margin: 0;
  size: letter;
}}
</style>
</head>
<body>
<div class="page">

  {logo_banner}

  <!-- COVER -->
  <div class="cover">
    <div class="cover-eyebrow">Dreams2Memories Travel · Silver Nova Trans-Pacific</div>
    <div class="cover-title">Ron &amp; Lindy Westbrook</div>
    <div class="cover-subtitle">A Voyage from Japan to the Last Frontier</div>
    <div class="cover-dates">April 23 — May 11, 2026 &nbsp;·&nbsp; 19 Nights</div>
    <div class="cover-meta">
      <strong>Silver Nova</strong> &nbsp;·&nbsp; Cabin 7031 Superior Veranda Suite
      &nbsp;·&nbsp; Voyage SN260423019<br/>
      Tokyo (Harumi) &rarr; Miyako &rarr; Aomori &rarr; Pacific Crossing
      &rarr; Alaska &rarr; Victoria &rarr; Seattle
    </div>
  </div>

  <!-- VOYAGE SUMMARY -->
  <div class="summary-box">
    <h2>Voyage Summary</h2>
    <div class="summary-grid">
      <div class="summary-row">
        <div class="summary-label">Booking</div>
        <div class="summary-value">566904-25</div>
      </div>
      <div class="summary-row">
        <div class="summary-label">Voyage</div>
        <div class="summary-value">SN260423019</div>
      </div>
      <div class="summary-row">
        <div class="summary-label">Cabin</div>
        <div class="summary-value">7031 Superior Veranda Suite</div>
      </div>
      <div class="summary-row">
        <div class="summary-label">Cruise Fare</div>
        <div class="summary-value">$10,800 — Paid in Full</div>
      </div>
      <div class="summary-row">
        <div class="summary-label">Embarkation</div>
        <div class="summary-value">Tokyo Harumi Terminal · Apr 23 · 7:00 PM</div>
      </div>
      <div class="summary-row">
        <div class="summary-label">Disembarkation</div>
        <div class="summary-value">Seattle · May 11 · 7:00 AM</div>
      </div>
      <div class="summary-row">
        <div class="summary-label">Insurance</div>
        <div class="summary-value">Allianz Annual Premier — Conf E2549991663</div>
      </div>
      <div class="summary-row">
        <div class="summary-label">Includes</div>
        <div class="summary-value">All Excursions · Dining · Beverages · Butler · Gratuities</div>
      </div>
    </div>
  </div>

  <!-- PRE-CRUISE -->
  <div class="precruise">
    <h2>Pre-Cruise Arrangements (April 21–23)</h2>
    <div class="pre-item">
      <div class="pre-icon">✈</div>
      <div class="pre-text"><strong>Apr 21 · United UA 143</strong> — Denver → Tokyo Narita · 11:35 AM · Seats 21A/21C (Premium Economy) · PNR I0Y9VG</div>
    </div>
    <div class="pre-item">
      <div class="pre-icon">🚗</div>
      <div class="pre-text"><strong>Apr 21 · Marcus Pickup</strong> — Home → DEN · 7:30 AM</div>
    </div>
    <div class="pre-item">
      <div class="pre-icon">🚌</div>
      <div class="pre-text"><strong>Apr 22 · Transferz Private Sedan</strong> — NRT Terminal 1 Meet &amp; Greet → Hilton Tokyo Odaiba · Booking 73268402723830</div>
    </div>
    <div class="pre-item">
      <div class="pre-icon">🏨</div>
      <div class="pre-text"><strong>Apr 22–23 · Hilton Tokyo Odaiba</strong> — King Hilton Guest Room · Airport Honors Breakfast · Conf 33S2013960</div>
    </div>
    <div class="pre-item">
      <div class="pre-icon">🚌</div>
      <div class="pre-text"><strong>Apr 23 · Shared Transfer to Port</strong> — Hilton Odaiba → Harumi Terminal · 10:30 AM · 4 pax (Loucks + Westbrook) · PE151557101 · Driver locator: checkpickup.com/3AG7KZ</div>
    </div>
  </div>

  <!-- DAILY ITINERARY HEADING -->
  <div class="section-heading">Your 20-Day Voyage · Day by Day</div>

  <!-- DAY CARDS -->
  {cards_html}

  <!-- RETURN FLIGHT -->
  <div class="precruise" style="border-top:1px solid #ddd5c8; border-bottom:none;">
    <h2>Return Arrangements (May 11)</h2>
    <div class="pre-item">
      <div class="pre-icon">🚌</div>
      <div class="pre-text"><strong>Seattle Cruise Terminal → SEA-TAC</strong> — Transfer needed by ~10:00 AM · <em>Not yet booked — book before Apr 15</em></div>
    </div>
    <div class="pre-item">
      <div class="pre-icon">✈</div>
      <div class="pre-text"><strong>United UA 757</strong> — Seattle → Denver · 12:46 PM → 4:30 PM · PNR I0Y9VG</div>
    </div>
  </div>

  <!-- FOOTER -->
  <div class="footer">
    <div class="footer-name">Prepared by Dani Moreau &amp; the Dreams2Memories Travel Wing</div>
    <div class="footer-line">Concierge Intelligence · <a href="mailto:concierge@d2mluxury.quest">concierge@d2mluxury.quest</a></div>
    <div class="footer-line">John Loucks · 719-291-0742</div>
    <div class="footer-line" style="margin-top:12px; font-size:0.78em; opacity:0.6;">
      Generated {datetime.now().strftime("%B %-d, %Y")} · Dreams2Memories Travel, LLC · All times local
    </div>
  </div>

</div>
</body>
</html>'''


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    print("── Silver Nova Itinerary Generator ──────────────────────")
    print("Fetching Pexels images…")

    # Collect unique photo IDs
    all_ids = list({d[4] for d in DAYS if d[4]})
    photos  = {}
    for pid in all_ids:
        print(f"  {pid}…", end=" ", flush=True)
        photos[pid] = get_pexels_photo(pid)
        print(photos[pid]["photographer"])

    # Build day data dicts
    print("\nAssembling day data…")
    days_data = []
    for (day, date, port, is_sea, pid, dock, depart, excursion) in DAYS:
        p = photos.get(pid, {})
        narrative = SEA_NARRATIVES.get(day, ("", ""))[1] if is_sea else ""

        # Embarkation day narrative
        if day == 1 and not is_sea:
            narrative = (
                "Welcome aboard Silver Nova. Your Superior Veranda Suite awaits — "
                "butler service, Bulgari amenities, and a veranda poised over the waters of Tokyo Bay. "
                "Tonight, Harumi Terminal slips behind you as Japan's lights fade and the Pacific begins."
            )
        if day == 20 and not is_sea:
            narrative = (
                "The Emerald City emerges from morning mist like a dream resolving into focus: "
                "the Space Needle first, then the skyline, then the green hills of the Pacific Northwest beyond. "
                "After nineteen nights, Silver Nova glides into Elliott Bay with quiet authority. "
                "You have crossed the Pacific and touched the edges of Japan and Alaska — you are home."
            )

        days_data.append({
            "day":          day,
            "date":         date,
            "port":         port,
            "is_sea":       is_sea,
            "img_url":      p.get("url", ""),
            "photographer": p.get("photographer", ""),
            "narrative":    narrative,
            "dock":         dock,
            "depart":       depart,
            "excursion":    excursion,
            "dining":       DINING.get(date, ""),
        })

    print("\nLoading logo…")
    logo_b64 = get_logo_b64()
    print(f"  logo: {'OK' if logo_b64 else 'MISSING — using text fallback'}")

    print("\nRendering HTML…")
    html = render_html(days_data, logo_b64)
    HTML_OUT.write_text(html, encoding="utf-8")
    print(f"  HTML → {HTML_OUT}")

    print("\nGenerating PDF (WeasyPrint)…")
    try:
        from weasyprint import HTML as WP
        WP(filename=str(HTML_OUT)).write_pdf(str(PDF_OUT))
        print(f"  PDF  → {PDF_OUT}")
    except Exception as e:
        print(f"  ⚠ WeasyPrint error: {e}")
        try:
            import pdfkit
            pdfkit.from_file(str(HTML_OUT), str(PDF_OUT))
            print(f"  PDF  → {PDF_OUT} (via pdfkit fallback)")
        except Exception as e2:
            print(f"  ✗ PDF generation failed: {e2}")
            print("  HTML is ready — open in Chrome and Print → Save as PDF")

    size = PDF_OUT.stat().st_size // 1024 if PDF_OUT.exists() else 0
    print(f"\n✅ DONE  |  HTML: {HTML_OUT.stat().st_size//1024}KB  |  PDF: {size}KB")
    print(f"\n  Open: file://{HTML_OUT}")


if __name__ == "__main__":
    main()
