"""
McLeod / McGlasson — Silver Muse Mediterranean — Final Itinerary Generator
Dreams2Memories Travel, LLC
Luna (A6) Creative Lead | Hale COS Orchestration | EXEC Brand Polish

Produces:
  output/McLeod_SilverMuse_Final.html
  output/McLeod_SilverMuse_Final.pdf

Run: python3 itinerary/generate_mcleod_itinerary.py
"""

import subprocess, json, sys, base64
from pathlib import Path
from datetime import datetime

PEXELS_KEY   = "***REMOVED-SECRET***"
OUTPUT_DIR   = Path("/home/john/Thunderbird/output")
IMGS         = OUTPUT_DIR / "mcleod_port_images"
SM_IMGS      = Path("/home/john/Thunderbird/storage/output/silver_muse_imgs")
LOGO_B64_FILE= Path("/home/john/Thunderbird/output/logo_small_b64.txt")
HTML_OUT     = OUTPUT_DIR / "McLeod_SilverMuse_Final.html"
PDF_OUT      = OUTPUT_DIR / "McLeod_SilverMuse_Final.pdf"

NAVY  = "#0d1b2e"
CREAM = "#f7f3ea"
LINEN = "#eee8db"
BLUE  = "#0000ff"
GOLD  = "#c9a84c"
SLATE = "#34495e"
MIST  = "#7f8c8d"

# ── PORT NARRATIVES (Luna A6) ─────────────────────────────────────────────────
PORT_NARRATIVES = {
    "Civitavecchia (Rome) — Embarkation": (
        "Rome releases you to the sea",
        "Four days in Rome leave a particular residue — the smell of espresso and exhaust and two-thousand-year-old stone, "
        "the way the light falls on the Forum at the golden hour, a dinner in Trastevere that went long because nobody wanted to end it. "
        "Civitavecchia is where Rome hands you off to something different: the Silver Muse waiting at the pier, white and composed, "
        "butler already at your suite door, the Tyrrhenian Sea spreading out beyond the breakwater in every shade the afternoon offers. "
        "The transition from four days of walking ancient streets to the unhurried pace of an all-suite ship happens fast — "
        "and that first hour on deck, with the Italian coast going amber behind you and a glass of something cold in hand, "
        "is worth standing still for. The city you just lived becomes a smudge of terracotta on the horizon. "
        "The next ten days belong to the sea."
    ),
    "Naples, Italy": (
        "Naples & Herculaneum",
        "Naples is not subtle and has never pretended to be — it arrives all at once, loud and layered and unashamed, "
        "with Vesuvius looming on the skyline like a punctuation mark at the end of a very long sentence about what civilization costs. "
        "The city itself rewards those who resist the temptation to treat it merely as a transit point for Pompeii, "
        "though Herculaneum demands its due: walking those excavated streets in the early afternoon, when the tourist buses have thinned, "
        "produces a silence that is almost unbearable in its weight. "
        "Eat at whatever trattoria on Via dei Tribunali looks like the locals eat there — the pizza here is not an item on a menu "
        "but an argument about what flour and fire and time can accomplish. "
        "The bay at dusk, with the mountain going dark against the orange sky, is the view that stays."
    ),
    "Giardini Naxos, Sicily": (
        "Taormina & Mount Etna",
        "The Greek theatre at Taormina has been staging performances for two thousand years, and its current production — "
        "Mount Etna framed by columns of ancient stone, the sea glittering three hundred meters below — runs daily and requires no ticket. "
        "The town above the theatre is a single long corso of medieval and baroque architecture, ice cream shops, and local ceramic work "
        "that is worth the browse even if you buy nothing, and the view from the terraces of the Villa Comunale gardens stops conversation completely. "
        "Etna is always visible and always slightly threatening, which gives the whole landscape an edge that coastal prettiness alone cannot supply. "
        "Giardini Naxos below is quieter, less photographed, and excellent for a long lunch before the tender back."
    ),
    "Siracusa (Syracuse), Sicily": (
        "The Greek City of the West",
        "Siracusa was once the largest city in the ancient world — larger than Athens, more powerful than Carthage, "
        "the place where Archimedes did mathematics in the bath and where Aeschylus premiered tragedies before crowds of ten thousand. "
        "The island of Ortygia, connected to the modern city by a short bridge, contains the bones of that ancient greatness: "
        "a Greek temple absorbed into a Norman cathedral, a Baroque piazza built on top of a classical agora, and the Arethusa spring "
        "where papyrus grows in a pool that has been freshwater since antiquity, fed by an underground river that surfaces beneath the sea. "
        "The morning fish market at the Rettifilo, with its swordfish and sea urchins and the particular noise of Sicilian vendors at work, "
        "is as alive as it has been for four thousand years, and the narrow streets of Ortygia, emptied of cars and cooling in the island breeze, "
        "are among the most beautiful in the Mediterranean. "
        "This is the port that puts all the others in perspective."
    ),
    "Valletta, Malta": (
        "Honey limestone, Game of Thrones, and the Grand Harbour",
        "Valletta glows the color of old honey in the morning light — crusading knights cut this city from local limestone "
        "in the sixteenth century, and five hundred years of Mediterranean sun have baked it into something that looks less built than grown. "
        "Today's excursion follows the footprints of a different kind of epic: the Game of Thrones filming locations that gave Westeros "
        "its most convincing skyline, the ancient harbor fortifications that doubled as King's Landing, walls that were already old "
        "when the cameras arrived and will be here long after. "
        "Between the filming sites, there is time to eat like a local — ftira, the Maltese bread ring sealed with oil and tuna, "
        "and harissa paste that the islands have made their own for centuries, both sold from bakeries that open before the tour buses arrive. "
        "The Upper Barrakka Gardens in the early afternoon offer the most theatrical harbor view in the Mediterranean: "
        "the Grand Harbour thirty meters below, the three silent cities of Vittoriosa, Senglea, and Cospicua across the water, "
        "the whole scene so layered in siege and ambition and improbable survival that the fiction of dragons feels almost modest by comparison."
    ),
    "Kotor, Montenegro": (
        "Blue Cave Speedboat Adventure",
        "The Bay of Kotor arrives like a held breath — dark Dinaric Alps dropping almost vertically into water so still and enclosed "
        "that the walled city's reflection appears with photographic fidelity, the whole scene slightly unreal in the early morning light. "
        "Today you trade the view from shore for the view from the water: a speedboat threading the outer bay at 08:30, "
        "the spray cold and the coast rushing past at a scale that makes the cliffs feel genuinely enormous. "
        "The Blue Cave, accessible only by water, holds the quality of light that artists spend careers trying to describe — "
        "a filtered turquoise that seems to come from inside the stone rather than from the sky above it. "
        "Back in port with time before departure, the Old Town's medieval streets offer a slower counterpoint: "
        "cats in doorways, Byzantine icons accumulating centuries quietly in small churches, the limestone walls "
        "still warm from the morning sun."
    ),
    "Dubrovnik, Croatia": (
        "A Day at the Beach Club",
        "Dubrovnik is a city so beautiful it can exhaust you with its own perfection — the walls, the Stradun, the terracotta rooftops, "
        "the island of Lokrum sitting in the bay like punctuation at the end of a very long sentence about the Adriatic. "
        "Today you make the wise choice: five hours at a beach club where the water is Adriatic-cold and Mediterranean-clear "
        "and the only thing required of you is to be in it. "
        "The Dalmatian coast from the water reveals what the postcards miss — the scale of the walls from sea level, "
        "the way the city rises from the limestone in layers that feel simultaneously ancient and entirely alive. "
        "Lunch on the terrace with a glass of local Plavac Mali, the city gleaming above, the afternoon light doing "
        "what only Adriatic light does. The walls and the Stradun and the old republic will be there when you walk back "
        "through the Pile Gate later — unhurried, having already had the best of the day."
    ),
    "Split, Croatia": (
        "Diocletian's Living Palace",
        "Split is still a city inside a palace — Diocletian's retirement estate, built for a Roman emperor who wanted somewhere comfortable "
        "to end his days, eventually became the compressed, layered, entirely alive city center that exists today, with apartments and "
        "restaurants and a jazz bar occupying spaces the emperor intended for temples and guard quarters. "
        "The Peristyle, the central courtyard of the original complex, is the kind of ancient public space that remains genuinely used "
        "rather than merely preserved, and in the evening it functions as an outdoor salon where the city collects itself. "
        "The Riva promenade along the waterfront is best at the breakfast hour, with a coffee and no particular agenda. "
        "Split does not need to perform for visitors — it is too busy being itself."
    ),
    "Zadar, Croatia": (
        "Salt works, royal vineyards, and a sea that plays music",
        "Today's excursion moves inland first, to the salt works of Nin — one of the oldest continuously harvested salt pans in "
        "the Mediterranean, where shallow Adriatic brine evaporates into fleur de sel that chefs in Dubrovnik pay serious money for. "
        "The salt here has the faint mineral depth that industrial salt cannot replicate, and the landscape around the pans — "
        "flat, blinding white under the Croatian sun, broken only by distant steeples — is unlike anything else on the coast. "
        "From Nin, the route climbs into the Dalmatian hinterland for lunch at a royal vineyard, where Plavac Mali and Marastina "
        "grow in thin limestone soil that concentrates everything the grape has into a small, serious pour. "
        "Zadar itself waits for the late afternoon: walk the Roman forum, still partially above ground in the middle of a neighborhood square; "
        "stand at dusk on the Riva above the Sea Organ, whose underwater pipes translate each wave into a low, shifting chord "
        "that is neither music nor silence but the Adriatic speaking in its own key. "
        "Alfred Hitchcock called this the most beautiful sunset in the world. He was not wrong."
    ),
    "Fusina (Venice) — Disembarkation": (
        "Arriving in Venice",
        "The water taxi from Fusina threads the lagoon as dawn firms up behind the campaniles and the pink marble of the Doge's Palace "
        "emerges from morning mist — Venice arriving not like a city but like a revelation that has been waiting patiently. "
        "Your three nights at the Hilton Molino Stucky on Giudecca put you across the channel from San Marco, which is exactly "
        "the right position: close enough to walk the sestieri easily, far enough to return each evening to a neighborhood that moves "
        "at a different, more local pace. "
        "The best Venice experience is consistently the one you find by getting lost — following a calle until it dead-ends at a canal, "
        "eating at the bacaro where there are no English menus, arriving at Campo Santa Margherita at aperitivo hour when the light "
        "is copper and the prosecco is cold. Let these three days be unhurried; Venice rewards exactly that."
    ),
}

SEA_NARRATIVE = (
    "The Adriatic at Midpassage",
    "The Adriatic is the most civilized of seas — narrow enough to feel intimate, deep enough to be serious, "
    "its surface today a hammered silver under a sky that can't decide between blue and white. "
    "Silver Muse finds her rhythm between the Italian heel and the Croatian coast in a corridor that has carried "
    "Venetian galleys and Byzantine trade ships and Roman grain fleets for three thousand years. "
    "The pool deck invites idleness; La Terrazza is already planning tonight's menu. "
    "This is the luxury of a single day with no agenda and nothing required of you but presence — "
    "the Adriatic holds the ship, the ship holds you, and tomorrow is Kotor."
)

# ── KNOWN PROPER NOUN CORRECTIONS ────────────────────────────────────────────
# Catches misspellings before they reach the rendered output.
# Add entries whenever a new port/site/vessel name is confirmed from primary source.
SPELL_CORRECTIONS = {
    "Herculanum":    "Herculaneum",
    "Herculanium":   "Herculaneum",
    "Siracusa Italy": "Siracusa (Syracuse), Sicily",
    "Syracuse Sicily": "Siracusa (Syracuse), Sicily",
    "Taormina Sicily": "Giardini Naxos, Sicily",
    "Molino Stuki":  "Hilton Molino Stucky Venice",
    "Molino Stucki": "Hilton Molino Stucky Venice",
    "Blacklain":     "Blacklane",
    "Kotor Montenegro": "Kotor, Montenegro",
    "Dubrovnik Croatia": "Dubrovnik, Croatia",
}

def spell_check(text: str) -> str:
    """Apply known proper noun corrections to any string before rendering."""
    for wrong, right in SPELL_CORRECTIONS.items():
        text = text.replace(wrong, right)
    return text

# ── DAY TABLE ────────────────────────────────────────────────────────────────
# (day, date, port, is_sea, img_src, arrive, depart, excursion)
# PORT ORDER + TIMES SOURCE: silversea.com voyage SM260623010 (verified 2026-05-30)
#   Corroborated by: my.silversea.com activities portal (Apr 27 2026) + Melissa McGlasson Italy Summer 2026.pdf
DAYS = [
    (1,  "2026-06-23", "Civitavecchia (Rome) — Embarkation",
         False, ("file", str(SM_IMGS / "grand_suite.jpg")),
         "", "19:00",
         "Embarkation Day — Welcome Aboard Silver Muse · Booking 298475-25"),
    (2,  "2026-06-24", "Naples, Italy",
         False, ("file", str(IMGS / "naples.jpg")),
         "08:00", "18:00",
         "RUINS OF HERCULANEUM · Depart 08:45 · 3.5 hrs · Included [Source: activities portal, Apr 27 2026]"),
    (3,  "2026-06-25", "Giardini Naxos, Sicily",
         False, ("file", str(IMGS / "taormina.jpg")),
         "09:00", "19:00",
         "GREEK &amp; ROMAN TAORMINA · Depart 09:30 · 4 hrs · Included [Source: activities portal, Apr 27 2026]"),
    (4,  "2026-06-26", "Siracusa (Syracuse), Sicily",
         False, ("file", str(IMGS / "siracusa.jpg")),
         "08:00", "18:00",
         "9 excursions available · No shore excursion booked as of Apr 27, 2026 [Source: silversea.com SM260623010]"),
    (5,  "2026-06-27", "Valletta, Malta",
         False, ("file", str(IMGS / "valletta.jpg")),
         "08:00", "17:45",
         "GAME OF THRONES FILMING LOCATIONS · Depart 09:15 · 4 hrs · Included [Source: activities portal, Apr 27 2026]"),
    (6,  "2026-06-28", "Day at Sea — Adriatic Crossing",
         True,  ("split",
                 ("file", str(SM_IMGS / "pool_deck.jpg")),
                 ("file", str(SM_IMGS / "panorama_lounge.jpg"))),
         "", "", ""),
    (7,  "2026-06-29", "Kotor, Montenegro",
         False, ("file", str(IMGS / "kotor.jpg")),
         "08:00", "17:30",
         "SPEEDBOAT ADVENTURE TO BLUE CAVE · Depart 08:30 · 4 hrs · $318 booked [Source: activities portal, Apr 27 2026]"),
    (8,  "2026-06-30", "Dubrovnik, Croatia",
         False, ("file", str(IMGS / "dubrovnik.jpg")),
         "08:00", "18:00",
         "DAY AT THE BEACH CLUB · Depart 09:00 · 5 hrs · $278 booked [Source: activities portal, Apr 27 2026]"),
    (9,  "2026-07-01", "Split, Croatia",
         False, ("file", str(IMGS / "split.jpg")),
         "08:00", "18:00",
         "UNESCO WORLD HERITAGE SITES · Depart 08:45 · 4.5 hrs · Included [Source: activities portal, Apr 27 2026]"),
    (10, "2026-07-02", "Zadar, Croatia",
         False, ("file", str(IMGS / "zadar.jpg")),
         "08:00", "18:00",
         "ZADAR, NIN SALT WORKS &amp; ROYAL VINEYARDS · Depart 08:45 · 5 hrs · Included [Source: activities portal, Apr 27 2026]"),
    (11, "2026-07-03", "Fusina (Venice) — Disembarkation",
         False, ("file", str(IMGS / "venice.jpg")),
         "07:00", "",
         "Disembarkation · Venice Guide &amp; Boat — Private Water Taxi &amp; Guide · Order #14878 · 09:30 · €350 PAID"),
]

# ── IMAGE LOADERS ─────────────────────────────────────────────────────────────
def load_file(path: str) -> dict:
    p = Path(path)
    try:
        data = base64.b64encode(p.read_bytes()).decode()
        label = p.stem.replace("_", " ").title()
        return {"url": f"data:image/jpeg;base64,{data}",
                "credit": f"{label} · Silver Muse Mediterranean" if "silver_muse" in str(p) else f"{label}",
                "is_b64": True}
    except Exception as e:
        print(f"  ⚠ file {path}: {e}")
        return {"url": "", "credit": "", "is_b64": True}


def resolve_src(src: tuple) -> dict:
    kind = src[0]
    if kind == "file":
        return load_file(src[1])
    return {"url": "", "credit": "", "is_b64": False}


def get_logo_b64() -> str:
    try:
        return LOGO_B64_FILE.read_text().strip()
    except Exception:
        return ""


def fmt_date(ds: str) -> str:
    try:
        return datetime.strptime(ds, "%Y-%m-%d").strftime("%B %-d, %Y")
    except Exception:
        return ds


# ── HTML TEMPLATE ─────────────────────────────────────────────────────────────
def render_html(days_data: list, logo_b64: str, ship_b64: str, no_photos: bool = False) -> str:
    logo_src = f"data:image/png;base64,{logo_b64}" if logo_b64 else ""
    ship_src = f"data:image/jpeg;base64,{ship_b64}" if ship_b64 else ""

    day_cards = []
    for d in days_data:
        day_num   = d["day"]
        date_str  = fmt_date(d["date"])
        port      = d["port"]
        is_sea    = d["is_sea"]
        img_url   = d["img_url"]
        photo_cred= d["photographer"]
        narrative = d["narrative"]
        subtitle  = d["subtitle"]
        dock      = d["dock"]
        depart    = d["depart"]
        excursion = d["excursion"]

        badge_bg  = "#2c5f8a" if is_sea else NAVY
        badge_txt = "Day at Sea" if is_sea else "Port of Call"
        if "Embarkation" in port:
            badge_bg  = "#1a5c1a"
            badge_txt = "Embarkation"
        elif "Disembarkation" in port:
            badge_bg  = "#5c1a1a"
            badge_txt = "Disembarkation"

        times_html = ""
        if dock and depart:
            times_html = f'<div class="times">Arrive {dock} &nbsp;·&nbsp; Depart {depart}</div>'
        elif dock:
            times_html = f'<div class="times">{dock}</div>'
        elif depart:
            times_html = f'<div class="times">Depart {depart}</div>'

        exc_html = ""
        if excursion and "Embarkation Day" not in excursion and "Disembarkation" not in excursion:
            exc_html = f'''
            <div class="detail-block excursion-block">
              <span class="detail-icon">⚓</span>
              <span class="detail-label">Shore Excursion</span>
              <span class="detail-text">{excursion}</span>
            </div>'''
        elif excursion:
            exc_html = f'''
            <div class="detail-block">
              <span class="detail-icon">📍</span>
              <span class="detail-text">{excursion}</span>
            </div>'''

        credit_html = f'<div class="photo-credit">Photo: {photo_cred}</div>' if photo_cred else ""

        split_data = d.get("split_imgs")
        if no_photos:
            img_html = ""
        elif split_data:
            left_url, left_cred   = split_data[0]["url"], split_data[0]["credit"]
            right_url, right_cred = split_data[1]["url"], split_data[1]["credit"]
            img_html = f'''
            <div class="photo-split">
              <div class="photo-half">
                <img src="{left_url}" alt="Silver Muse at Sea" class="port-photo" />
                <div class="photo-credit">{left_cred}</div>
              </div>
              <div class="photo-half">
                <img src="{right_url}" alt="Silver Muse at Sea" class="port-photo" />
                <div class="photo-credit">{right_cred}</div>
              </div>
            </div>'''
        elif img_url:
            img_html = f'''
            <div class="photo-wrap">
              <img src="{img_url}" alt="{port}" class="port-photo" />
              {credit_html}
            </div>'''
        else:
            img_html = ""

        subtitle_html = f'<div class="day-subtitle">{subtitle}</div>' if subtitle else ""

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
          {subtitle_html}
          <div class="narrative">{narrative}</div>
          {times_html}
          {exc_html}
        </div>''')

    cards_html = "\n".join(day_cards)

    logo_banner = (
        f'<div class="logo-banner"><img src="{logo_src}" alt="Dreams2Memories Travel" class="logo-img" /></div>'
        if logo_src else
        f'<div class="logo-banner text-logo"><div class="text-logo-inner">Dreams2Memories Travel</div></div>'
    )

    if no_photos:
        ship_html = ""
    elif ship_src:
        ship_html = f'''<div class="ship-photo-wrap" style="position:relative;">
  <img src="{ship_src}" alt="Silver Muse" class="ship-photo" />
  <div class="ship-caption">Silver Muse &nbsp;·&nbsp; Silversea Cruises &nbsp;·&nbsp; 596 Guests &nbsp;·&nbsp; All-Suite · All-Inclusive</div>
</div>'''
    else:
        ship_html = ""

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Erik McLeod &amp; Melissa McGlasson — Silver Muse Mediterranean</title>
<style>
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
html {{ background: {LINEN}; }}
body {{
  font-family: Verdana, Geneva, 'Segoe UI', Arial, sans-serif;
  background: {LINEN};
  color: {SLATE};
  line-height: 1.72;
}}
.page {{
  max-width: 800px;
  margin: 0 auto;
  background: {CREAM};
  box-shadow: 0 2px 24px rgba(0,0,0,0.12);
}}
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
.cover {{
  background: {NAVY};
  color: white;
  padding: 90px 48px 80px;
  text-align: center;
  border-bottom: 5px solid {GOLD};
  position: relative;
}}
.cover-eyebrow {{
  font-size: 0.82em;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: {GOLD};
  margin-bottom: 8px;
}}
.cover-rule {{
  width: 60px;
  height: 1px;
  background: {GOLD};
  margin: 16px auto 24px;
  opacity: 0.6;
}}
.cover-title {{
  font-size: 3.4em;
  font-weight: normal;
  line-height: 1.15;
  margin-bottom: 18px;
  letter-spacing: -0.01em;
}}
.cover-subtitle {{
  font-size: 1.35em;
  font-style: italic;
  color: rgba(255,255,255,0.8);
  margin-bottom: 36px;
  letter-spacing: 0.03em;
}}
.cover-dates {{
  display: inline-block;
  border: 1px solid {GOLD};
  border-radius: 3px;
  padding: 12px 36px;
  font-size: 1.08em;
  color: {GOLD};
  letter-spacing: 0.08em;
  margin-bottom: 36px;
}}
.cover-meta {{
  font-size: 0.88em;
  color: rgba(255,255,255,0.65);
  line-height: 2.2;
}}
.cover-meta strong {{ color: rgba(255,255,255,0.92); }}
.ship-photo-wrap {{ background: {NAVY}; padding: 0; position: relative; }}
.ship-photo {{ width: 100%; height: 500px; object-fit: cover; display: block; opacity: 0.9; }}
.ship-caption {{
  position: absolute;
  bottom: 0; left: 0; right: 0;
  background: linear-gradient(transparent, rgba(13,27,46,0.85));
  color: white;
  padding: 40px 40px 20px;
  font-size: 0.82em;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: rgba(201,168,76,0.9);
}}
.summary-box {{
  padding: 36px 40px;
  border-bottom: 1px solid #ddd5c8;
}}
.summary-box h2 {{
  font-size: 1.1em;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: {NAVY};
  margin-bottom: 20px;
  border-bottom: 2px solid {GOLD};
  padding-bottom: 8px;
}}
.summary-grid {{ display: flex; flex-direction: column; gap: 6px; }}
.summary-row {{ display: flex; gap: 16px; font-size: 0.92em; padding: 5px 0; border-bottom: 1px solid rgba(0,0,0,0.05); }}
.summary-label {{ width: 140px; flex-shrink: 0; color: {MIST}; font-style: italic; }}
.summary-value {{ color: {SLATE}; font-weight: 500; }}
.precruise {{
  padding: 32px 40px;
  border-bottom: 1px solid #ddd5c8;
  background: {CREAM};
}}
.precruise h2 {{
  font-size: 1.05em;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: {NAVY};
  margin-bottom: 18px;
  border-bottom: 2px solid {GOLD};
  padding-bottom: 8px;
}}
.pre-item {{
  display: flex;
  gap: 14px;
  padding: 10px 0;
  border-bottom: 1px solid rgba(0,0,0,0.05);
  align-items: flex-start;
  font-size: 0.91em;
}}
.pre-item:last-child {{ border-bottom: none; }}
.pre-icon {{ font-size: 1.1em; width: 22px; flex-shrink: 0; padding-top: 1px; }}
.pre-text {{ color: {SLATE}; line-height: 1.5; }}
.pre-text strong {{ color: {NAVY}; }}
.section-heading {{
  background: {NAVY};
  color: {GOLD};
  text-align: center;
  padding: 22px 40px;
  font-size: 0.95em;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  border-top: 1px solid rgba(201,168,76,0.3);
  border-bottom: 1px solid rgba(201,168,76,0.3);
}}
.day-card {{
  padding: 38px 44px 32px;
  border-bottom: 1px solid #ddd5c8;
}}
.day-header {{
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 22px;
}}
.day-number {{
  font-size: 0.78em;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: {GOLD};
  font-style: normal;
  margin-bottom: 2px;
}}
.day-date {{
  font-size: 1.1em;
  color: {NAVY};
  font-weight: bold;
  margin-top: 3px;
}}
.day-right {{ text-align: right; }}
.day-port {{
  font-size: 1.55em;
  color: {NAVY};
  font-weight: bold;
  margin-bottom: 8px;
  line-height: 1.1;
}}
.day-badge {{
  display: inline-block;
  padding: 3px 10px;
  border-radius: 3px;
  font-size: 0.7em;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: white;
}}
.photo-wrap {{ margin-bottom: 18px; border-radius: 4px; overflow: hidden; }}
.port-photo {{
  width: 100%;
  height: 320px;
  object-fit: cover;
  display: block;
  border-radius: 4px;
}}
.photo-split {{
  display: flex;
  gap: 8px;
  margin-bottom: 18px;
}}
.photo-half {{ flex: 1; overflow: hidden; border-radius: 4px; }}
.photo-half .port-photo {{ height: 260px; border-radius: 4px; }}
.photo-credit {{
  font-size: 0.68em;
  color: {MIST};
  margin-top: 4px;
  font-style: italic;
}}
.day-subtitle {{
  font-size: 0.88em;
  color: {GOLD};
  letter-spacing: 0.08em;
  text-transform: uppercase;
  margin-bottom: 10px;
  font-style: normal;
}}
.narrative {{
  font-size: 0.96em;
  color: {BLUE};
  font-style: italic;
  line-height: 1.82;
  margin-bottom: 18px;
  border-left: 4px solid {GOLD};
  padding: 10px 16px;
  background: rgba(201,168,76,0.04);
  border-radius: 0 4px 4px 0;
}}
.times {{
  font-size: 0.85em;
  color: {MIST};
  margin-bottom: 10px;
  letter-spacing: 0.03em;
}}
.detail-block {{
  display: flex;
  align-items: flex-start;
  gap: 10px;
  font-size: 0.87em;
  padding: 8px 0;
  border-top: 1px solid rgba(0,0,0,0.05);
}}
.detail-icon {{ font-size: 1em; }}
.detail-label {{
  font-weight: bold;
  color: {NAVY};
  min-width: 110px;
  flex-shrink: 0;
}}
.detail-text {{ color: {SLATE}; }}
.excursion-block {{ background: rgba(13,27,46,0.03); border-radius: 4px; padding: 8px 12px; }}
.excursion-block .detail-label {{ color: {NAVY}; }}
.footer {{
  background: {NAVY};
  color: rgba(255,255,255,0.7);
  padding: 28px 40px;
  text-align: center;
  border-top: 3px solid {GOLD};
  font-size: 0.85em;
}}
.footer-name {{ color: white; font-size: 1em; margin-bottom: 6px; }}
.footer-line {{ margin: 3px 0; }}
.footer a {{ color: {GOLD}; text-decoration: none; }}
.dining-section {{
  padding: 32px 40px;
  border-bottom: 1px solid #ddd5c8;
  background: {CREAM};
}}
.dining-section h2 {{
  font-size: 1.05em;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: {NAVY};
  margin-bottom: 18px;
  border-bottom: 2px solid {GOLD};
  padding-bottom: 8px;
}}
.dining-subsection {{
  margin-bottom: 20px;
}}
.dining-subsection h3 {{
  font-size: 0.85em;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: {GOLD};
  margin-bottom: 10px;
}}
.dining-item {{
  display: flex;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid rgba(0,0,0,0.04);
  align-items: flex-start;
  font-size: 0.88em;
}}
.dining-item:last-child {{ border-bottom: none; }}
.dining-icon {{ font-size: 1em; width: 20px; flex-shrink: 0; padding-top: 2px; }}
.dining-text {{ color: {SLATE}; line-height: 1.5; }}
.dining-text strong {{ color: {NAVY}; }}
.dining-source {{
  font-size: 0.75em;
  color: {MIST};
  font-style: italic;
  margin-left: 4px;
}}
@media print {{
  html, body {{ background: white; }}
  .page {{ box-shadow: none; max-width: 100%; }}
  .day-card {{ page-break-inside: avoid; }}
}}
@page {{ margin: 0; size: letter; }}
</style>
</head>
<body>
<div class="page">

  {logo_banner}

  <!-- COVER -->
  <div class="cover">
    <div class="cover-eyebrow">Dreams2Memories Travel &nbsp;·&nbsp; A Private Itinerary</div>
    <div class="cover-rule"></div>
    <div class="cover-title">Erik McLeod &amp; Melissa McGlasson</div>
    <div class="cover-subtitle">Rome &nbsp;·&nbsp; The Mediterranean &nbsp;·&nbsp; The Adriatic &nbsp;·&nbsp; Venice</div>
    <div class="cover-dates">June 18 &mdash; July 6, 2026 &nbsp;·&nbsp; 11 Nights · Civitavecchia to Venice</div>
    <div class="cover-meta">
      <strong>Silver Muse</strong> &nbsp;·&nbsp; All-Suite · All-Inclusive · Butler Service &nbsp;·&nbsp; Booking 298475-25<br/>
      Civitavecchia &rarr; Naples &rarr; Sicily &rarr; Malta &rarr; Montenegro &rarr; Croatia &rarr; Venice<br/>
      <span style="color:{GOLD};letter-spacing:0.1em;font-size:0.9em;">PAID IN FULL &nbsp;·&nbsp; SILVERSEA CRUISES</span>
    </div>
  </div>

  <!-- SHIP PHOTO -->
  {ship_html}

  <!-- VOYAGE SUMMARY -->
  <div class="summary-box">
    <h2>Voyage Summary</h2>
    <div class="summary-grid">
      <div class="summary-row">
        <div class="summary-label">Booking</div>
        <div class="summary-value">298475-25 · Silversea Cruises</div>
      </div>
      <div class="summary-row">
        <div class="summary-label">Ship</div>
        <div class="summary-value">Silver Muse · 40,700 GT · 596 guests · 1:1.4 crew ratio</div>
      </div>
      <div class="summary-row">
        <div class="summary-label">Cabin</div>
        <div class="summary-value">All-Suite Ship · All-Inclusive · Butler Service</div>
      </div>
      <div class="summary-row">
        <div class="summary-label">Cruise Fare</div>
        <div class="summary-value">Paid in Full — January 24, 2026</div>
      </div>
      <div class="summary-row">
        <div class="summary-label">Embarkation</div>
        <div class="summary-value">Civitavecchia (Rome) · June 23 · Evening</div>
      </div>
      <div class="summary-row">
        <div class="summary-label">Disembarkation</div>
        <div class="summary-value">Venice / Fusina · July 3 · Morning</div>
      </div>
      <div class="summary-row">
        <div class="summary-label">Insurance</div>
        <div class="summary-value">Travel Insurance · Paid · Medical + Trip Interruption</div>
      </div>
      <div class="summary-row">
        <div class="summary-label">Includes</div>
        <div class="summary-value">All shore excursions · Dining · Premium beverages · Butler · Gratuities</div>
      </div>
      <div class="summary-row">
        <div class="summary-label">Shore Excursion Balance</div>
        <div class="summary-value">$596 remaining as of April 27, 2026 · Covers Kotor ($318) + Dubrovnik ($278) <span style="font-size:0.82em;color:{MIST};">[Source: my.silversea.com activities portal, Apr 27, 2026]</span></div>
      </div>
    </div>
  </div>

  <!-- PRE-CRUISE: ROME -->
  <div class="precruise">
    <h2>Part One — Pre-Cruise Rome &nbsp;·&nbsp; June 18–23</h2>
    <div class="pre-item">
      <div class="pre-icon">🚗</div>
      <div class="pre-text"><strong>Jun 18 at 14:00 · Blacklane — Home → Denver International Airport (DEN)</strong> — Booking #127664621 · Chauffeur: Mr. Said Yusifli · Pickup: 1541 Armstrong Dr, Longmont CO 80504 · Business Van/SUV · 5 pax / 5 bags · Complimentary (Silversea all-inclusive) · Arrives DEN 2:42 PM [Source: Blacklane confirmation email, May 24, 2026]</div>
    </div>
    <div class="pre-item">
      <div class="pre-icon">✈</div>
      <div class="pre-text"><strong>Jun 18 · Denver (DEN) → Rome (FCO)</strong> — United UA 177 · Erik: PNR ML237016 · Melissa: PNR TF317131 · Business Class · Seats: 3D/3F · Overnight flight · Arrive FCO June 19 [Source: Silversea booking 298475-25 + Erik McLeod email, Mar 17, 2026]</div>
    </div>
    <div class="pre-item">
      <div class="pre-icon">🚗</div>
      <div class="pre-text"><strong>Jun 19 at 13:30 · Welcome Pickups → Baglioni Hotel Regina</strong> — Order #w-6377007-2 · FCO Arrival Hall, NCC corner (1–4) · Flight UA 177 from Denver · Driver holds sign</div>
    </div>
    <div class="pre-item">
      <div class="pre-icon">🏨</div>
      <div class="pre-text"><strong>Jun 19–23 · Baglioni Hotel Regina, Rome</strong> — Via V. Veneto 72 · 4 nights · Conf #6851SF075162 · Chase Luxury: breakfast daily, $100 property credit, welcome Prosecco, Wi-Fi, room upgrade subject to availability</div>
    </div>
    <div class="pre-item">
      <div class="pre-icon">🗺</div>
      <div class="pre-text"><strong>June 19–22 · Rome —</strong> These four days belong entirely to you. You planned them, booked them, and know exactly how you want to spend them — the itinerary is yours, and we wouldn't touch it. What we'll say is this: when June 23 arrives and the driver pulls away from the Baglioni, you'll feel the city releasing you, unhurried, into something else entirely. That something is the Silver Muse at Civitavecchia, and it's worth the anticipation.</div>
    </div>
    <div class="pre-item">
      <div class="pre-icon">🚗</div>
      <div class="pre-text"><strong>Jun 23 at 10:00 · Welcome Pickups → Civitavecchia Port</strong> — Order #w-6377007-1 · Driver at hotel entrance · Arriving for afternoon embarkation</div>
    </div>
  </div>

  <!-- SPECIALTY DINING -->
  <div class="dining-section">
    <h2>Dining Aboard Silver Muse &amp; Ashore</h2>

    <div class="dining-subsection">
      <h3>Specialty Dining — 7 Reservations Confirmed</h3>
      <div class="dining-item">
        <div class="dining-icon">🍽</div>
        <div class="dining-text"><strong>La Dame</strong> — Silver Muse's signature French restaurant. Intimate, reservation-only. The caviar service is non-negotiable. <span class="dining-source">[Source: my.silversea.com activities portal, Apr 27, 2026 — reservation confirmed]</span></div>
      </div>
      <div class="dining-item">
        <div class="dining-icon">🍽</div>
        <div class="dining-text"><strong>Atlantide</strong> — Modern Mediterranean cuisine, intimate setting, reservation required. Sea-view dining. <span class="dining-source">[Source: activities portal, Apr 27, 2026 — reservation confirmed]</span></div>
      </div>
      <div class="dining-item">
        <div class="dining-icon">🎷</div>
        <div class="dining-text"><strong>Silver Note</strong> — Jazz supper club. Dinner with live music; the atmosphere is unlike anything else on the ship. Reserve early — it fills. <span class="dining-source">[Source: activities portal, Apr 27, 2026 — reservation confirmed]</span></div>
      </div>
      <div class="dining-item">
        <div class="dining-icon">🍜</div>
        <div class="dining-text"><strong>Indochine</strong> — Asian fusion cuisine in an intimate, lantern-lit setting. Reservation required. <span class="dining-source">[Source: activities portal, Apr 27, 2026 — reservation confirmed]</span></div>
      </div>
      <div class="dining-item">
        <div class="dining-icon">🍣</div>
        <div class="dining-text"><strong>Kaiseki</strong> — Japanese tasting experience. Reservation required; one of the most sought-after tables on board. <span class="dining-source">[Source: activities portal, Apr 27, 2026 — reservation confirmed]</span></div>
      </div>
      <div class="dining-item">
        <div class="dining-icon">🌿</div>
        <div class="dining-text"><strong>La Terrazza</strong> — Italian cuisine with al fresco terrace. Open seating for breakfast and lunch; dinner by reservation. <span class="dining-source">[Source: activities portal, Apr 27, 2026 — reservation confirmed]</span></div>
      </div>
      <div class="dining-item">
        <div class="dining-icon">🔥</div>
        <div class="dining-text"><strong>The Grill</strong> — Pool deck casual with grilled seafood, dry-aged steaks, and the best lunch at sea. Open seating. <span class="dining-source">[Source: activities portal, Apr 27, 2026 — reservation confirmed]</span></div>
      </div>
    </div>

    <div class="dining-subsection">
      <h3>Rome — Pre-Cruise Dining &nbsp;<span style="font-size:0.75em;color:{MIST};text-transform:none;letter-spacing:0;">[Source: Client planning — Italy Summer 2026.pdf]</span></h3>
      <div class="dining-item">
        <div class="dining-icon">🍷</div>
        <div class="dining-text"><strong>June 19–22 · Rome</strong> — Dinner reservations confirmed by client. Via dei Tribunali pizza, Trastevere trattoria evening, Via Veneto terrace. Full reservation details in client's Italy Summer 2026 itinerary.</div>
      </div>
    </div>

    <div class="dining-subsection">
      <h3>Venice — Post-Cruise Dining &nbsp;<span style="font-size:0.75em;color:{MIST};text-transform:none;letter-spacing:0;">[Source: Client planning — Italy Summer 2026.pdf]</span></h3>
      <div class="dining-item">
        <div class="dining-icon">🍷</div>
        <div class="dining-text"><strong>July 3–5 · Venice</strong> — Dinner reservations confirmed by client. Trattoria Altanella (Giudecca — old-school Venetian, legendary fritto misto), plus additional evenings in Cannaregio and San Polo. Full reservation details in client's Italy Summer 2026 itinerary.</div>
      </div>
      <div class="dining-item">
        <div class="dining-icon">☕</div>
        <div class="dining-text"><strong>Skyline Rooftop Bar</strong> — Hilton Molino Stucky. Aperitivo with panoramic lagoon views before dinner each evening. Recommended.</div>
      </div>
    </div>
  </div>

  <!-- DAILY ITINERARY -->
  <div class="section-heading">The Silver Muse Mediterranean · 11 Days · Day by Day</div>

  {cards_html}

  <!-- POST-CRUISE: VENICE -->
  <div class="precruise" style="border-top:1px solid #ddd5c8; border-bottom:1px solid #ddd5c8;">
    <h2>Part Three — Post-Cruise Venice &nbsp;·&nbsp; July 3–6</h2>
    <div class="pre-item">
      <div class="pre-icon">🚤</div>
      <div class="pre-text"><strong>Jul 3 at 09:30 · Venice Guide &amp; Boat → Hilton Molino Stucky</strong> — Order #14878 · Fusina terminal → Giudecca Island · €350 PAID · Private water taxi, 2 pax</div>
    </div>
    <div class="pre-item">
      <div class="pre-icon">🏨</div>
      <div class="pre-text"><strong>Jul 3–6 · Hilton Molino Stucky, Venice</strong> — Giudecca Island · 3 nights · Confirmation number pending from Hilton · Skyline Rooftop Bar · La Palanca canal-side for lunch · Vaporetto access to San Marco across the channel</div>
    </div>
    <div class="pre-item">
      <div class="pre-icon">🗺</div>
      <div class="pre-text"><strong>Jul 3–5 · Venice — Giudecca &amp; beyond.</strong> Bacaro crawl through Cannaregio. Campo Santa Margherita at aperitivo hour. The Frari church and the Accademia. A gondola if the mood takes you. Dinner at Trattoria Altanella — old-school Venetian, cash only, legendary fritto misto.</div>
    </div>
    <div class="pre-item">
      <div class="pre-icon">🚤</div>
      <div class="pre-text"><strong>Jul 6 at 09:00 · Consorzio Motoscafi Venezia → Marco Polo Airport (VCE)</strong> — Booking <strong>96SGY</strong> · Hilton Molino Stucky pier → VCE · €170 PAID · 2 pax · 4 suitcases</div>
    </div>
    <div class="pre-item">
      <div class="pre-icon">✈</div>
      <div class="pre-text"><strong>Jul 6 · Venice (VCE) → Toronto (YYZ) → Denver (DEN)</strong> — Air Canada AC 817 (VCE→YYZ · seats 3A / 4A) + AC 1041 (YYZ→DEN · seats 2A / 2C) · Business Class · PNRs: H1PY618 (Erik) / N6TX610 (Melissa) [Source: Erik McLeod email, Mar 17, 2026]</div>
    </div>
    <div class="pre-item">
      <div class="pre-icon">🚗</div>
      <div class="pre-text"><strong>Jul 6 at 21:07 · Blacklane — Denver International Airport (DEN) → Home</strong> — Pickup: DEN arrivals · Destination: 1541 Armstrong Dr, Longmont CO 80504 · Complimentary (Silversea all-inclusive) · Booking # pending [Source: Commander confirmed May 29, 2026]</div>
    </div>
  </div>

  <!-- FOOTER -->
  <div class="footer">
    <div class="footer-name">Prepared by Your Dreams2Memories Travel Team</div>
    <div class="footer-line">Concierge Intelligence · <a href="mailto:concierge@d2mluxury.quest">concierge@d2mluxury.quest</a></div>
    <div class="footer-line">John Loucks · 719-291-0742</div>
    <div class="footer-line" style="margin-top:12px; font-size:0.78em; opacity:0.6;">
      Generated {datetime.now().strftime("%B %-d, %Y")} · Dreams2Memories Travel, LLC · All times local
    </div>
  </div>

</div>
</body>
</html>'''


HTML_NOPHOTO_OUT = OUTPUT_DIR / "McLeod_SilverMuse_NoPhotos.html"

# ── MAIN ──────────────────────────────────────────────────────────────────────
def preflight_check() -> bool:
    """Gate: verify all required images exist before rendering. Fail loudly."""
    print("\n── PRE-FLIGHT IMAGE CHECK ──────────────────────────────────────────")
    errors = []
    for (day, date, port, is_sea, src, dock, depart, excursion) in DAYS:
        if src[0] == "split":
            for sub_src in [src[1], src[2]]:
                p = Path(sub_src[1])
                if not p.exists():
                    errors.append(f"  ✗ Day {day} split image MISSING: {p}")
        elif src[0] == "file":
            p = Path(src[1])
            if not p.exists():
                errors.append(f"  ✗ Day {day} ({port[:30]}) image MISSING: {p}")
    if errors:
        print("  PREFLIGHT FAILED — fix images before rendering:")
        for e in errors:
            print(e)
        print("  Run: python3 itinerary/fetch_port_images.py  to re-fetch missing images")
        return False
    print(f"  ✓ All {len(DAYS)} day images confirmed present")
    return True


def main():
    no_photos = "--no-photos" in sys.argv
    print("── McLeod / McGlasson · Silver Muse Mediterranean ──────────────────")

    # Dossier gate: validate dossier before any rendering (Sterling A7 — 2026-05-29)
    dossier = Path("/home/john/Thunderbird/dossiers/McLeod_Erik_Melissa_SilverMuse_Complete.md")
    result = subprocess.run(
        [sys.executable, str(Path(__file__).parent / "validate_dossier.py"), str(dossier)],
        capture_output=True, text=True
    )
    if result.returncode == 2:
        print("✗ DOSSIER VALIDATION FAILED — generator refused to run")
        print(result.stdout)
        sys.exit(2)
    if result.returncode == 1:
        print("⚠ Dossier warnings — proceeding (review before sending to client)")

    # Pre-flight: verify images unless explicitly skipping photos
    if not no_photos and not preflight_check():
        sys.exit(1)

    print("\nLoading images…")
    days_data = []
    for (day, date, port, is_sea, src, dock, depart, excursion) in DAYS:
        # Apply spell corrections to all text fields
        port      = spell_check(port)
        excursion = spell_check(excursion)
        if is_sea:
            narrative = SEA_NARRATIVE[1]
            subtitle  = SEA_NARRATIVE[0]
        else:
            pair = PORT_NARRATIVES.get(port, ("", ""))
            subtitle  = pair[0]
            narrative = pair[1]

        day_dict = {
            "day":          day,
            "date":         date,
            "port":         port,
            "is_sea":       is_sea,
            "img_url":      "",
            "photographer": "",
            "narrative":    narrative,
            "subtitle":     subtitle,
            "dock":         dock,
            "depart":       depart,
            "excursion":    excursion,
        }

        if src[0] == "split":
            left  = load_file(src[1][1])
            right = load_file(src[2][1])
            day_dict["split_imgs"] = [
                {"url": left["url"],  "credit": left.get("credit", "Silver Muse · Silversea")},
                {"url": right["url"], "credit": right.get("credit", "Silver Muse · Silversea")},
            ]
        else:
            p = resolve_src(src)
            day_dict["img_url"]      = p.get("url", "")
            day_dict["photographer"] = p.get("credit", "")

        days_data.append(day_dict)
        print(f"  Day {day:2d} — {port[:40]}")

    print("\nLoading logo…")
    logo_b64 = get_logo_b64()
    print(f"  logo: {'OK' if logo_b64 else 'MISSING — text fallback'}")

    print("Loading Silver Muse ship photo…")
    ship_path = SM_IMGS / "exterior.jpg"
    try:
        ship_b64 = base64.b64encode(ship_path.read_bytes()).decode()
        print(f"  ship: OK ({ship_path.stat().st_size // 1024}KB)")
    except Exception as e:
        print(f"  ship: MISSING ({e})")
        ship_b64 = ""

    print("\nRendering HTML (with photos)…")
    html = render_html(days_data, logo_b64, ship_b64, no_photos=False)
    HTML_OUT.write_text(html, encoding="utf-8")
    print(f"  HTML → {HTML_OUT}  ({HTML_OUT.stat().st_size // 1024}KB)")

    print("\nRendering HTML (no photos)…")
    html_np = render_html(days_data, logo_b64, ship_b64, no_photos=True)
    HTML_NOPHOTO_OUT.write_text(html_np, encoding="utf-8")
    print(f"  HTML → {HTML_NOPHOTO_OUT}  ({HTML_NOPHOTO_OUT.stat().st_size // 1024}KB)")

    print("\nGenerating PDF (WeasyPrint)…")
    try:
        from weasyprint import HTML as WP
        WP(filename=str(HTML_OUT)).write_pdf(str(PDF_OUT))
        size = PDF_OUT.stat().st_size // 1024 if PDF_OUT.exists() else 0
        print(f"  PDF  → {PDF_OUT}  ({size}KB)")
    except Exception as e:
        print(f"  ⚠ WeasyPrint: {e}")
        print("  Open HTML in Chrome → Print → Save as PDF")

    print(f"\n✅ DONE")
    print(f"   Full:     file://{HTML_OUT}")
    print(f"   NoPhotos: file://{HTML_NOPHOTO_OUT}")


if __name__ == "__main__":
    main()
