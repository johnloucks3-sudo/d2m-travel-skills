#!/usr/bin/env python3
"""
kuklinski-recommend — Kuklinski Group Travel DNA Recommendation Engine
Discretionary Arc Automation | Phase 2 Project #3
Dreams2Memories Travel, LLC | Thunderbird OS

Usage:
  kuklinski-recommend --phase [intake|voyage|post] --category [dining|excursion|cabin]
  kuklinski-recommend --phase intake --category cabin
  kuklinski-recommend --phase voyage --category dining
  kuklinski-recommend --list-guests
  kuklinski-recommend --full-brief
"""

import argparse
import json
import sys
from datetime import date, datetime
from textwrap import dedent

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

VOYAGE_START = date(2026, 12, 17)
VOYAGE_END   = date(2026, 12, 27)
SHIP         = "Viking Mars"
ITINERARY    = "Panama Canal"
CRUISE_LINE  = "Viking"

# ─────────────────────────────────────────────────────────────────────────────
# GUEST DATABASE
# ─────────────────────────────────────────────────────────────────────────────

GUESTS = {
    "kyle_rosalie": {
        "names": ["Kyle Kuklinski", "Rosalie Kuklinski"],
        "booking": "9593880",
        "cabin": "4122",
        "category": "DV1",
        "deck": 4,
        "ages": [43, 41],
        "email": "kyle.kuklinski@gmail.com",
        "sbc_total": 800,
        "home": "Richmond VA",
        "archetype": "CULTURAL_ADVENTURER",
        "role": "Group organizer / primary contact",
        "dob": ["1983-02-09", "1985-03-04"],
        "phone": "804-801-4762",
        "mobility": "full",
        "dietary": [],
        "milestones": [],
    },
    "roger_nicholas": {
        "names": ["Roger Kuklinski", "Dr. Nicholas Kuklinski"],
        "booking": "9593873",
        "cabin": "8012",
        "category": "DV1",
        "deck": 8,
        "ages": [74, 44],
        "email": "Roger.kuklinski@gmail.com",
        "sbc_total": 200,
        "home": "Richmond VA",
        "archetype": "GENERATIONAL_BRIDGE",
        "role": "Father-son pair; multi-pace planning required",
        "dob": ["1951-09-08", "1981-06-16"],
        "phone": "704-609-6867",
        "mobility": "moderate",
        "dietary": [],
        "milestones": [],
    },
    "josh_erica": {
        "names": ["Joshua Morton", "Erica Dodge"],
        "booking": "9595029",
        "cabin": "3015",
        "category": "V1",
        "deck": 3,
        "ages": [80, 78],
        "email": "Josh@jerichopix.com",
        "sbc_total": 200,
        "home": "Naples FL",
        "archetype": "SEASONED_VOYAGER",
        "role": "Photographer + comfort-seeker; leisure pace required",
        "dob": ["1945-12-11", "1948-03-04"],
        "phone": "818-317-9843",
        "mobility": "limited",
        "dietary": [],
        "milestones": ["CHRISTMAS_EVE_DEC24"],
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# TRAVEL DNA MATRIX
# ─────────────────────────────────────────────────────────────────────────────

TRAVEL_DNA = {
    "CULTURAL_ADVENTURER": {
        "description": "Engaged, outward-facing, wants to DO and SEE. Organizes, delegates, leads group.",
        "dining_style": "Adventurous. Will try Chef's Table. Wants group celebration moments.",
        "excursion_appetite": "Active to moderate. Leads group excursion decisions.",
        "cabin_priority": "Views and space. Will upgrade if value is clear.",
        "pace": "brisk",
        "split_ok": True,
    },
    "GENERATIONAL_BRIDGE": {
        "description": "Two speeds in one booking. Roger (74) = contemplative. Nick (44, Dr.) = intellectually curious.",
        "dining_style": "Roger: classic/relaxed, not too late. Nick: open to anything. Book Manfredi's for both; Chef's Table optional for Nick.",
        "excursion_appetite": "SPLIT recommended. Roger = boat/carriage/leisurely. Nick = walking/depth tours.",
        "cabin_priority": "Deck 8 DV1 is optimal — highest standard veranda, panoramic views. Keep.",
        "pace": "split",
        "split_ok": True,
    },
    "SEASONED_VOYAGER": {
        "description": "Unhurried. Visual/aesthetic (Josh is a photographer). Comfort and warmth first.",
        "dining_style": "Leisurely. Earlier seating strongly preferred. Manfredi's perfect. Chef's Table is very long — offer but don't push.",
        "excursion_appetite": "LEISURE ONLY. Boat tours, carriage rides, scenic overlooks. No steps, no heat exposure, no trams.",
        "cabin_priority": "⚠ CRITICAL MISMATCH: Deck 3 V1 has restricted/obstructed ocean view. Josh is a photographer. Upsell to DV1 Deck 5-7 is STRONG recommendation.",
        "pace": "leisurely",
        "split_ok": False,
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# PORTS
# ─────────────────────────────────────────────────────────────────────────────

PORTS = [
    {"day": 1, "date": "2026-12-17", "name": "Panama City (Embarkation)", "type": "embarkation"},
    {"day": 2, "date": "2026-12-18", "name": "Panama Canal Transit", "type": "canal"},
    {"day": 3, "date": "2026-12-19", "name": "Cartagena, Colombia", "type": "port"},
    {"day": 4, "date": "2026-12-20", "name": "Sea Day", "type": "sea"},
    {"day": 5, "date": "2026-12-21", "name": "Puerto Limón, Costa Rica", "type": "port"},
    {"day": 6, "date": "2026-12-22", "name": "Sea Day", "type": "sea"},
    {"day": 7, "date": "2026-12-23", "name": "Sea Day", "type": "sea"},
    {"day": 8, "date": "2026-12-24", "name": "Christmas Eve (At Sea)", "type": "sea_special"},
    {"day": 9, "date": "2026-12-25", "name": "Christmas Day (At Sea)", "type": "sea_special"},
    {"day": 10, "date": "2026-12-26", "name": "At Sea", "type": "sea"},
    {"day": 11, "date": "2026-12-27", "name": "Ft. Lauderdale (Disembarkation)", "type": "disembarkation"},
]

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def days_until_voyage():
    return (VOYAGE_START - date.today()).days


def get_phase_context(phase: str) -> str:
    days = days_until_voyage()
    if phase == "intake":
        return f"PRE-VOYAGE — {days} days until embarkation Dec 17, 2026"
    elif phase == "voyage":
        return "ABOARD Viking Mars — Dec 17-27, 2026"
    else:
        return "POST-VOYAGE — Retention and next booking phase"


# ─────────────────────────────────────────────────────────────────────────────
# CABIN RECOMMENDATIONS
# ─────────────────────────────────────────────────────────────────────────────

def recommend_cabin(phase: str) -> str:
    lines = []
    lines.append("=" * 72)
    lines.append("CABIN RECOMMENDATIONS — Kuklinski Group")
    lines.append(f"Phase: {phase.upper()} | {get_phase_context(phase)}")
    lines.append("=" * 72)

    if phase == "intake":
        lines.append("""
BOOKING ASSESSMENT — 3 CABINS

┌─────────────────────────────────────────────────────────────────────┐
│ BOOKING 1 — Kyle & Rosalie Kuklinski                                │
│ Cabin 4122 · DV1 · Deck 4                                           │
│ Status: APPROPRIATE                                                  │
│ Assessment: Mid-ship DV1 veranda. Good stability, decent views.      │
│   Kyle/Rosalie will appreciate the veranda for sea days.             │
│ Action: HOLD — no upsell needed unless Kyle asks                     │
│ SBC note: $800 SBC → direct toward Chef's Table + wine packages      │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ BOOKING 2 — Roger & Dr. Nicholas Kuklinski                          │
│ Cabin 8012 · DV1 · Deck 8                                           │
│ Status: OPTIMAL                                                      │
│ Assessment: Deck 8 = Viking's highest standard veranda deck.         │
│   Best unobstructed panoramic views on the ship. Roger (74) will     │
│   spend real time on that veranda — best possible placement.         │
│   Nick uses it for morning reading and post-excursion decompression. │
│ Action: HOLD — do not change                                         │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ BOOKING 3 — Joshua Morton & Erica Dodge                             │
│ Cabin 3015 · V1-Veranda · Deck 3                                    │
│ Status: ⚠ MISMATCH FLAG — UPSELL RECOMMENDED                       │
│                                                                      │
│ THE PROBLEM: V1 Veranda on Deck 3 = lowest cabin category, near     │
│ waterline. Ocean views are restricted/obstructed. Smaller veranda.  │
│ Port noise. Water-line view vs open ocean horizon.                   │
│                                                                      │
│ WHY THIS MATTERS: Josh Morton is a photographer (jerichopix.com).   │
│ His entire contribution to this voyage is through the lens. Deck 3  │
│ gives him restricted horizon, lower sightlines, less natural light.  │
│ Erica at 78 will spend significant time on the veranda — comfort     │
│ and view quality directly affect her voyage satisfaction.            │
│                                                                      │
│ UPSELL TARGET: DV1 Veranda, Deck 5-7 (mid-ship)                    │
│ Upgrade delta: est. $700-$900/person ($1,400-$1,800 total)          │
│ D2M commission on upgrade: est. $350-450 additional                 │
│                                                                      │
│ PITCH TO KYLE: "Josh is a photographer — he'll be on that veranda   │
│   at sunrise every morning. The view difference between Deck 3 and  │
│   Deck 6 is significant. This is the one upgrade I'd recommend."    │
│                                                                      │
│ Action: UPSELL NOW — call Viking 1-855-8-VIKING, ref #9595029      │
└─────────────────────────────────────────────────────────────────────┘

INTAKE CABIN SUMMARY
  Hold:  Booking 9593880 (Kyle/Rosalie) — DV1 Deck 4 appropriate
  Hold:  Booking 9593873 (Roger/Nick) — DV1 Deck 8 OPTIMAL
  ACT:   Booking 9595029 (Josh/Erica) — V1 Deck 3 → upgrade to DV1 Deck 5-7
""")

    elif phase == "voyage":
        lines.append("""
ONBOARD CABIN & SBC STRATEGY

SBC SPENDING GUIDE (Total: $1,200 across 3 bookings)
  Kyle/Rosalie — $800 SBC:
    Chef's Table (2 × ~$95)     = $190
    Manfredi's (2 × ~$15)       = $30
    Wine/beverages sea days     = $200
    Spa (Rosalie)               = ~$120
    Reserve                     = $260
    Action: Use SBC deliberately. Check Viking app: My Account → Credits.

  Roger/Nick — $200 SBC:
    Manfredi's (2 × ~$15)       = $30
    Nick: Chef's Table optional  = ~$95 (if he joins Night 7)
    Beverages + enrichment       = $75

  Josh/Erica — $200 SBC:
    Manfredi's (2 × ~$15)       = $30
    Aquavit Terrace beverages    = $50
    Spa (Erica)                  = ~$80
    Josh: photo-print packages   = $40

VERANDA USE BY COUPLE
  Deck 4 (Kyle/Rosalie): Standard views. Good sea day use.
  Deck 8 (Roger/Nick): BEST panoramic view on ship. Roger owns sunrise.
  Deck 3 (Josh/Erica): Limited view. Josh should use Aquavit Terrace
    and bow deck for photography instead of the cabin veranda.
    Guest Services can advise on quiet deck hours for sunrise shots.
""")

    else:  # post
        lines.append("""
POST-VOYAGE CABIN FEEDBACK

FEEDBACK TRIGGERS (3-7 days post-disembarkation):

Kyle/Rosalie:
  "How did Cabin 4122 work for you and Rosalie? Anything you'd change
   for next time — deck level, location, size?"

Roger (via Kyle):
  "Did Deck 8 work well for Roger? I placed him there specifically
   for the views — worth it?"

Josh/Erica:
  "Josh — honest feedback: how was the photography situation from
   your cabin? Did the veranda work for you?"
  Target: If Deck 3 view was limiting → rebooking pitch:
    "Next time I'm putting you on Deck 6. Same ship, completely
     different photography window."

REBOOKING SIGNAL:
  Josh confirms Deck 3 restricted views = immediate DV1 pre-sale framing.
  Roger confirms Deck 8 = lock in Deck 8+ for all future Roger bookings.
""")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# DINING RECOMMENDATIONS
# ─────────────────────────────────────────────────────────────────────────────

def recommend_dining(phase: str) -> str:
    lines = []
    lines.append("=" * 72)
    lines.append("DINING RECOMMENDATIONS — Kuklinski Group")
    lines.append(f"Phase: {phase.upper()} | {get_phase_context(phase)}")
    lines.append("=" * 72)

    if phase == "intake":
        lines.append("""
PRE-VOYAGE DINING STRATEGY

TRIGGER: Arc 4-A preference collection → send May 15, 2026
BOOKING: Embarkation day Dec 17 — go to podiums within FIRST HOUR aboard

RESTAURANTS ABOARD VIKING MARS
  Manfredi's Italian Kitchen
    Cover: ~$15/pp | Duration: ~90 min | Dress: Smart casual
    URL: vikingcruises.com/oceans/life-on-board/restaurants/manfredis.html
    Fit: ALL 6 GUESTS — universally accessible pace and menu
    Note: Handmade pasta, branzino, osso buco. Earlier seating recommended
          for Roger (74) and Josh/Erica (80s).

  The Chef's Table
    Cover: ~$95/pp | Duration: 2.5-3 hrs | Dress: Smart casual+
    URL: vikingcruises.com/oceans/life-on-board/restaurants/the-chefs-table.html
    Fit: SELECTIVE (see below) — FILLS FIRST on embarkation day
    Note: 2.5-3 hrs is too long for Seasoned Voyagers (Josh/Erica at 80s).

RECOMMENDED STRATEGY (split approach):

  GROUP DINNER: All 6 → Manfredi's, Night 3 (Dec 19, post-Cartagena)
    Timing: 6:30 PM reservation for 6
    Why Night 3: Group settled, Cartagena stories, relaxed pace.
                 Roger and Josh/Erica comfortable for 90 min.
    Action: Kyle → Manfredi's podium (Deck 2) within first hour of boarding

  SELECT DINNER: Kyle + Rosalie + Nick → Chef's Table, Night 7 (Dec 23)
    Timing: 7:00 PM reservation for 3
    Why: Younger/mid-age travelers want full tasting menu experience.
         Roger, Josh, Erica opt for main dining (The Restaurant).
    Note: Nick (Dr.) will appreciate the tasting menu format.
    SBC: Fully covered by Kyle's $800 SBC ($190 for 2, + ~$95 for Nick)

  CHRISTMAS EVE (Dec 24): Group dinner in The Restaurant — ALL 6
    Viking runs special holiday gala menu. Group milestone event.
    Request group table Dec 17 when making other reservations.

DIETARY COLLECTION (Arc 4-A questions — send May 15):
  □ Dietary restrictions / allergies across all 6 guests?
  □ Any celebration nights? (Roger milestone? Anniversary?)
  □ Wine preferences? (Viking package ~$199/person at Manfredi's)
  □ Early seating preference for older travelers?
  □ Josh/Erica: Chef's Table 2.5-3 hrs — interested, or Manfredi's only?

TIMING:
  May 15, 2026  → Arc 4-A (preference collection)
  Jun 1, 2026   → Arc 4-B (strategy options — present 3 approaches)
  Jun 15, 2026  → Arc 4-C (confirm strategy)
  Dec 17, 2026  → Execute at podiums
""")

    elif phase == "voyage":
        lines.append("""
ONBOARD DINING EXECUTION

EMBARKATION DAY (Dec 17) — FIRST 60 MINUTES:

  STEP 1: Kyle → Manfredi's podium (Deck 2)
    Request: Table for 6, Night 3 (Dec 19), 6:30 PM
    Backup nights: Night 4 or Night 5

  STEP 2: Kyle → Chef's Table podium (same area — FILLS FIRST)
    Request: Table for 3 (Kyle, Rosalie, Nick), Night 7 (Dec 23)
    Backup: Night 6 (Dec 22)

  STEP 3: Kyle → The Restaurant host
    Request: Group table for 6, Christmas Eve (Dec 24)
    Note: Viking holiday gala menu — reserve early

VOYAGE DINING SCHEDULE

  Night 1  (Dec 17) Embarkation     → The Restaurant, all 6
  Night 2  (Dec 18) Canal Day       → World Café (casual, long day)
  Night 3  (Dec 19) Cartagena       → MANFREDI'S, all 6, 6:30 PM ★
  Night 4  (Dec 20) Sea Day         → The Restaurant or World Café
  Night 5  (Dec 21) Costa Rica      → The Restaurant, all 6
  Night 6  (Dec 22) Sea Day         → Aquavit Terrace lunch + The Restaurant
  Night 7  (Dec 23) Sea Day         → CHEF'S TABLE (Kyle/Rosalie/Nick) ★
                                       Roger + Josh/Erica → The Restaurant
  Night 8  (Dec 24) CHRISTMAS EVE   → The Restaurant gala, ALL 6 ★
  Night 9  (Dec 25) Christmas Day   → World Café brunch + The Restaurant
  Night 10 (Dec 26) At Sea          → The Restaurant farewell dinner, all 6

PER-ARCHETYPE DINING NOTES:
  Cultural Adventurer (Kyle/Rosalie):
    Manfredi's + Chef's Table both booked. SBC covers all specialty dining.
    Kyle: SBC tracking — check Viking app balance mid-voyage.

  Generational Bridge (Roger/Nick):
    Roger: 6:30 PM start every night. Never past 9:00 PM.
    Nick: Night 7 Chef's Table — if he wants to join Kyle's table, book early.
    Both: Manfredi's Night 3 is the father-son group moment.

  Seasoned Voyager (Josh/Erica):
    Manfredi's Night 3 is their ONE specialty dining evening.
    All other nights: The Restaurant (full service, comfortable pace).
    Erica: request same waiter section across voyage if possible (consistency).
    Josh: Aquavit Terrace breakfast daily — best light for morning shots.
""")

    else:  # post
        lines.append("""
POST-VOYAGE DINING FEEDBACK

FEEDBACK TRIGGERS (3-5 days post-disembarkation):

Kyle:
  "How was Manfredi's for the group Night 3? Did the Chef's Table
   deliver for you, Rosalie, and Nick?"
  Target: Menu preferences for next booking brief.

Roger (via Kyle):
  "Did the 6:30 PM seating work well for Roger? Any dining pace issues?"
  Target: Confirms early seating need for all future Roger bookings.

Josh (via Kyle):
  "Did Josh and Erica enjoy Manfredi's? Did Aquavit Terrace get used
   for photography?"
  Target: Aquavit Terrace = Seasoned Voyager signature experience confirmed.

CHRISTMAS EVE MEMORY ANCHOR:
  "The Christmas Eve group dinner aboard Viking Mars — how did that land
   for the group? That was the emotional peak I designed the schedule around."
  If strong → "Viking does a Christmas sailing every December. 2027 slots
   open in February. Want me to hold dates?"

REBOOKING DINING HOOK:
  Chef's Table highlight → "There are ships with even more elevated tasting
    experiences. Want me to find them for the group?"
  Christmas Eve peak → "Viking Christmas 2027 — want early access?"
""")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# EXCURSION RECOMMENDATIONS
# ─────────────────────────────────────────────────────────────────────────────

def recommend_excursion(phase: str) -> str:
    lines = []
    lines.append("=" * 72)
    lines.append("EXCURSION RECOMMENDATIONS — Kuklinski Group")
    lines.append(f"Phase: {phase.upper()} | {get_phase_context(phase)}")
    lines.append("=" * 72)

    if phase == "intake":
        lines.append("""
PRE-VOYAGE EXCURSION STRATEGY

TRIGGER: Arc 2-A preference collection → send Jul 28, 2026
BOOKING: Aug 2, 2026 — Viking excursion window opens. BOOK SAME DAY.

MOBILITY TIER MATRIX
  Tier 1 (Active/Moderate): Kyle (43), Rosalie (41), Nick (44)
    → Walking tours, aerial trams, multi-hour excursions OK
    → Heat tolerance: good with hydration
    → Budget: open to premium private options

  Tier 2 (Moderate/Leisurely): Roger (74)
    → Short walks OK. Carriage/boat preferred.
    → No significant uphill. No extreme heat exposure.
    → Private vehicle with A/C strongly preferred in Cartagena.

  Tier 3 (Leisure Only): Josh (80), Erica (78)
    → SEATED excursions ONLY
    → Boat tours, carriage rides, scenic overlooks: YES
    → Aerial trams, walking tours, physical activity: NO
    → Josh: visual/photographic experience is primary value
    → Heat sensitivity: acclimatized (Naples FL) but 80+ requires caution

PORT-BY-PORT RECOMMENDATIONS

PORT 1 — PANAMA CANAL TRANSIT (Dec 18)
  RECOMMENDATION: STAY ABOARD — ALL 6 GUESTS

  Rationale: Panama Canal transit is a once-in-a-lifetime SHIP experience.
  Being aboard when Viking Mars moves through the locks is irreplaceable.
  Josh Morton (photographer) on the BOW at canal entry = his best single
  photography moment of the entire voyage. Do not skip this for a shore
  excursion to the visitor center.

  Josh & Erica:  Bow deck — seated area available. Sunrise positioning.
                 Josh: arrive at bow by 5:30 AM. Full transit = 8-10 hrs.
  Roger:         Upper deck with enrichment narration. Bring binoculars.
  Kyle/Nick:     Active deck for full transit arc photos.

  Key question for Arc 2-A (Jul 28):
    "Stay aboard for the actual canal transit, or shore excursion to
     Miraflores Locks? I have a strong recommendation — want it?"

PORT 2 — CARTAGENA, COLOMBIA (Dec 19)
  NOTE: Avg temp 88°F. Heat is a real factor for Roger, Josh, Erica.

  TIER 1 (Kyle, Rosalie, Nick):
    Option A [RECOMMENDED]: Walled City Walking Tour (Viking)
      Price: ~$59/pp | Duration: 2.5 hrs | Mobility: moderate
      URL: vikingcruises.com/oceans/shore-excursions
      Why: Historical depth. Nick will engage heavily with the guide.
    Option B [PREMIUM]: Private Old City & Jewel Museum
      Price: ~$140/pp | Duration: 4 hrs | Private A/C vehicle
      Why: Better for heat; custom routing; emerald museum add-on

  TIER 2/3 (Roger, Josh, Erica):
    Option ONLY: Walled City & Carriage Tour (Viking)
      Price: ~$79/pp | Duration: 3 hrs | Mobility: minimal
      URL: vikingcruises.com/oceans/shore-excursions
      Why: Horse-drawn carriage, seated throughout, no walking required.
           Josh can photograph from carriage (Plaza de Bolivar angles).
    Alternative: Stay aboard (Aquavit Terrace, shade, rest)
      If Roger/Josh/Erica concerned about 88°F heat — valid choice.
      Present as equal option, not a consolation.

  Day management: Manfredi's Group Dinner = tonight (Night 3, 6:30 PM).
    All excursions must return by 4:00 PM. Verify against Viking port time.

PORT 3 — PUERTO LIMÓN, COSTA RICA (Dec 21)
  SPLIT RECOMMENDED:

  TIER 1 (Kyle, Rosalie, Nick):
    Option A [RECOMMENDED]: Rainforest Aerial Tram (Viking)
      Price: ~$119/pp | Duration: 4 hrs | Mobility: moderate
      URL: vikingcruises.com/oceans/shore-excursions
      Why: Best wildlife canopy access. Books out FAST — priority Aug 2.
           Short uphill walk to platform. Confirm Kyle's group is OK.
    Option B [PREMIUM]: Private Sloth Sanctuary + Canal Boat
      Price: ~$165/pp | Duration: 5 hrs | Private vehicle
      Superior wildlife guarantee. Photographer-friendly pace.

  TIER 2/3 (Roger, Josh, Erica):
    Option ONLY [STRONGLY RECOMMENDED]: Tortuguero Canals Boat Tour (Viking)
      Price: ~$89/pp | Duration: 3.5 hrs | Mobility: MINIMAL
      URL: vikingcruises.com/oceans/shore-excursions
      Why: SEATED THROUGHOUT. River canals. Monkeys, sloths, birds.
           Water-level wildlife shots = Josh's best photography of voyage.
           Roger fully comfortable for full duration (shaded boat).
    Premium Alt: Private Canal Boat (Roger/Josh/Erica only)
      Price: ~$165/pp | Dedicated guide, photographer-friendly positioning.
      Recommend if SBC covers it or Kyle wants to upgrade them.

BOOKING ORDER AUG 2 (fills fastest first):
  1. Costa Rica: Aerial Tram (books out fastest — book FIRST at open)
  2. Costa Rica: Tortuguero Canals
  3. Cartagena: Walled City Walking Tour (Tier 1)
  4. Cartagena: Carriage Tour (Tier 2/3)
  NOTE: Panama Canal = staying aboard, no booking needed.

ARC 2-A QUESTIONS TO SEND KYLE (Jul 28):
  1. Canal day: Stay aboard or shore excursion? (lead with strong rec)
  2. Activity level across the group (general; for split planning)
  3. Cartagena heat tolerance for Roger, Josh, Erica
  4. Costa Rica: wildlife interest scale 1-5 for the group
  5. Private vs group preference for any port
  6. Budget comfort for premium private tours (Tier 1)
""")

    elif phase == "voyage":
        lines.append("""
ONBOARD EXCURSION EXECUTION

PANAMA CANAL TRANSIT (Dec 18) — ALL ABOARD, NO SHORE EXCURSION

  JOSH MORTON — PHOTOGRAPHER BRIEF:
    Best positions:
      Bow (forward): Best wide-angle lock views. Position by 5:30 AM.
      Deck 8 (Roger/Nick veranda): Premium elevation angle for locks.
      Upper deck aft: Compression shots as ship enters lock chambers.
    Peak moment: Entering Miraflores Locks (~10:00 AM estimated)
    Bring: Telephoto for lock mechanism detail. Wide-angle for scale.
    Viking provides binoculars at Guest Services — request morning of.
    Aquavit Terrace: Open for breakfast during transit. Grab and go.

  ALL GUESTS:
    Viking narration during transit — enrichment value for Roger/Nick.
    Full transit = 8-10 hours. Pace yourself. World Café for lunch.
    Most photographic moment of the entire voyage for the group.

CARTAGENA (Dec 19) — PORT DAY

  TIER 1 (Kyle, Rosalie, Nick):
    Excursion per pre-booking. Return by 4:00 PM (Manfredi's at 6:30 PM).
    Kyle: Set group meeting point for Manfredi's dinner at 6:00 PM.
    Nick: Ask guide questions — he'll want depth on the walled city history.

  TIER 2/3 (Roger, Josh, Erica):
    Carriage Tour departure on daily program. Carry water (88°F).
    Josh: Request slower pace through Plaza de Bolivar for photography.
          Carriage window framing = unique architectural shots.
    If staying aboard: Aquavit Terrace, pool deck shade, afternoon nap.
    All three must be rested for 6:30 PM Manfredi's group dinner.

  TONIGHT: MANFREDI'S GROUP DINNER, all 6, 6:30 PM
    Kyle: Arrive 30 min early to confirm table setup and dietary notes.
    This is the GROUP BONDING dinner — Cartagena stories, first
    specialty meal, group photo moment. The meal to remember.

PUERTO LIMÓN, COSTA RICA (Dec 21) — PORT DAY

  TIER 1 (Kyle, Rosalie, Nick):
    Aerial Tram or Private — per pre-booking.
    Wildlife timing: Best tram wildlife is 8:00-10:00 AM (sloths active).
    Kyle: Bring phone with good zoom. Toucans and howler monkeys are vocal.
    Return by 3:00 PM (sea day follows, no time pressure otherwise).

  TIER 2/3 (Roger, Josh, Erica) — Tortuguero Canals:
    Duration: 3.5 hrs | Fully seated | Water-level wildlife
    JOSH PHOTOGRAPHY NOTE: Water-level shots of wildlife are rare.
      Wide angle for canopy, telephoto for sloths in trees.
      Request front or side seating from guide (not rear of boat).
      This is Josh's best excursion photography of the entire voyage.
    Roger: Bring hat and sunscreen. Open water exposure. Best comfort
           of all excursions — seated, shaded boat.

SEA DAYS (Dec 20, 22, 23, 26)

  Cultural Adventurer (Kyle/Rosalie):
    Enrichment lectures, fitness center, spa (Rosalie — use SBC),
    evening pool deck social hour.

  Generational Bridge (Roger/Nick):
    Roger: Morning veranda coffee, afternoon enrichment lecture.
    Nick: Library or guest speaker programming (Viking lectures = strong).
    Evening: The Restaurant, early night for Roger.

  Seasoned Voyager (Josh/Erica):
    Josh: Aquavit Terrace daily. Sea day light = best for ship architecture.
    Dawn (golden hour): Aquavit Terrace East-facing for sea-light shots.
    Erica: Spa morning, World Café lunch, afternoon rest, early dinner.

CHRISTMAS EVE (Dec 24) & CHRISTMAS DAY (Dec 25):
  Viking holiday programming — carol events, deck activities.
  Group dinner Christmas Eve in The Restaurant (all 6) ★
  Josh: Christmas Day sunrise on empty decks = best light of the voyage.
        Position on bow or upper deck. Bring wide-angle lens.
""")

    else:  # post
        lines.append("""
POST-VOYAGE EXCURSION FEEDBACK + REBOOKING

FEEDBACK TRIGGERS (3-5 days post-disembarkation):

Kyle:
  "Which excursion was the group's highlight? Any port where the
   recommendation missed — too physical, too hot, wrong for anyone?"
  Target: Validate split strategy. Refine Tier 1/2/3 for future groups.

Josh (via Kyle):
  "The Tortuguero canals for Josh and Erica — right call?
   Did he get the photography moments he was hoping for?"
  If yes → "Next time I can get Josh a private canal boat — same
    experience, his pace, no group timing constraints."

CANAL TRANSIT FEEDBACK:
  "Was staying aboard for the canal transit the right decision?
   Any regrets about not doing the Miraflores shore excursion?"
  If strong → "I knew Josh needed to be on that bow at 5:30 AM."

EXCURSION REBOOKING HOOKS:
  Tortuguero canals strong for Josh/Erica:
    → "AmaWaterways runs a Mekong river cruise. Every day is a
       Tortuguero moment. Want me to pull options for the group?"
  Aerial tram strong for Kyle/Nick:
    → "Ponant does Amazon expedition with similar canopy experiences.
       Adventure level up from Viking. Want to see it?"
  Costa Rica was a highlight:
    → "Viking has a dedicated Costa Rica itinerary — 10 nights, 3 ports.
       Would the group want that as their next voyage?"

CHRISTMAS VOYAGE ANCHOR:
  "Was Christmas Eve aboard everything you hoped for the group?
   Hard to replicate that on land."
  If strong → "Viking Christmas 2027. February availability opens.
   Same group, same ship, December. Want me to hold dates?"
""")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# FULL BRIEF + LIST GUESTS
# ─────────────────────────────────────────────────────────────────────────────

def full_brief() -> str:
    lines = [
        "=" * 72,
        "KUKLINSKI GROUP — COMPLETE TRAVEL DNA BRIEF",
        "A8 Reyes | Dreams2Memories Travel, LLC",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M MT')}",
        f"Ship: {SHIP} | {ITINERARY} | Dec 17-27, 2026",
        "=" * 72,
        "",
    ]
    for couple_key, data in GUESTS.items():
        names = " & ".join(data["names"])
        archetype = TRAVEL_DNA[data["archetype"]]
        lines.append(f"GUEST PAIR: {names}")
        lines.append(f"  Archetype:  {data['archetype']}")
        lines.append(f"  DNA:        {archetype['description']}")
        lines.append(f"  Cabin:      {data['cabin']} ({data['category']}) Deck {data['deck']}")
        lines.append(f"  SBC:        ${data['sbc_total']}")
        lines.append(f"  Mobility:   {data['mobility'].upper()}")
        lines.append(f"  Pace:       {archetype['pace']}")
        lines.append(f"  Dining:     {archetype['dining_style']}")
        lines.append(f"  Excursions: {archetype['excursion_appetite']}")
        lines.append(f"  Cabin note: {archetype['cabin_priority']}")
        lines.append("")
    lines.append("RUN ALL RECOMMENDATIONS:")
    for ph in ["intake", "voyage", "post"]:
        for cat in ["cabin", "dining", "excursion"]:
            lines.append(f"  kuklinski-recommend --phase {ph} --category {cat}")
    return "\n".join(lines)


def list_guests(as_json=False) -> str:
    if as_json:
        return json.dumps(GUESTS, indent=2)
    lines = ["=" * 72, "KUKLINSKI GROUP — GUEST DIRECTORY", "=" * 72, ""]
    for couple_key, data in GUESTS.items():
        lines.append(f"PAIR: {' & '.join(data['names'])}")
        lines.append(f"  Booking:   #{data['booking']} | Cabin: {data['cabin']} ({data['category']}) Deck {data['deck']}")
        lines.append(f"  Ages:      {data['ages'][0]} & {data['ages'][1]}")
        lines.append(f"  Archetype: {data['archetype']}")
        lines.append(f"  Email:     {data['email']}")
        lines.append(f"  Phone:     {data['phone']}")
        lines.append(f"  SBC:       ${data['sbc_total']}")
        lines.append(f"  Mobility:  {data['mobility']}")
        lines.append("")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# CLI ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="kuklinski-recommend",
        description=(
            "Kuklinski Group Travel DNA Recommendation Engine\n"
            "Dreams2Memories Travel, LLC | Viking Mars | Panama Canal | Dec 17-27, 2026"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=dedent("""
        Examples:
          kuklinski-recommend --phase intake --category cabin
          kuklinski-recommend --phase voyage --category dining
          kuklinski-recommend --phase post --category excursion
          kuklinski-recommend --full-brief
          kuklinski-recommend --list-guests
          kuklinski-recommend --list-guests --json
        """),
    )

    parser.add_argument(
        "--phase",
        choices=["intake", "voyage", "post"],
        help="Lifecycle phase: intake (pre-voyage), voyage (aboard), post (after)",
    )
    parser.add_argument(
        "--category",
        choices=["dining", "excursion", "cabin"],
        help="Recommendation category",
    )
    parser.add_argument(
        "--full-brief",
        action="store_true",
        help="Print complete group Travel DNA brief",
    )
    parser.add_argument(
        "--list-guests",
        action="store_true",
        help="List all guests with booking details",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output guest data as JSON (use with --list-guests)",
    )

    args = parser.parse_args()

    if args.full_brief:
        print(full_brief())
        sys.exit(0)

    if args.list_guests:
        print(list_guests(as_json=args.json))
        sys.exit(0)

    if not args.phase or not args.category:
        parser.print_help()
        print("\nERROR: Both --phase and --category are required.")
        sys.exit(1)

    dispatch = {
        "cabin": recommend_cabin,
        "dining": recommend_dining,
        "excursion": recommend_excursion,
    }

    print(dispatch[args.category](args.phase))
    sys.exit(0)


if __name__ == "__main__":
    main()
