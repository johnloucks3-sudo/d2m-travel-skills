#!/usr/bin/env python3
"""
McLeod/McGlasson Silver Muse Daily Itinerary Brief
Runs at 0800 MT — sends current day's schedule to johnloucks3
All event times shown as: local Italy time / MT (CEST - 8h = MT)
"""
from datetime import date, timedelta
from pathlib import Path

# All Italy-leg times shown as "HH:MM local / HH:MM MT"
# Italy = CEST = UTC+2 | MT = MDT = UTC-6 | Delta = -8h
# Colorado-leg times (Jun 18 outbound, Jun 6 return pickup) already in MT
ITINERARY = {
    "2026-06-18": (
        "Longmont → DEN → Airborne",
        "Blacklane pickup 14:00 MT from 1541 Armstrong Dr. "
        "UA 177 DEN→FCO departs 17:45 MT. Overnight Business Class (seats 3D/3F, PNR NFBDP6)."
    ),
    "2026-06-19": (
        "Rome — FCO Arrival + Baglioni Check-in",
        "Land FCO 12:20 local / 04:20 MT. "
        "Welcome Pickups car at 13:30 local / 05:30 MT (Order w-6377007-2). "
        "Baglioni Hotel Regina, Via V. Veneto 72 — check-in from 14:00 local / 06:00 MT. "
        "Grand Deluxe Room, $100 property credit active. "
        "Dinner suggestion: Sistina 52 (5★ modern Italian, Trevi area, 7 min walk) "
        "or Diana's Place (1★ Michelin, Trastevere, 12 min walk) — call same day to book."
    ),
    "2026-06-20": (
        "Rome — Colosseum Day",
        "Colosseum + Arena Floor + Roman Forum + Palatine Hill guided tour: "
        "10:00 local / 02:00 MT (GYG, $301.86 paid). 3 hours. "
        "Arena floor access — most visitors don't see this. "
        "Afternoon: Trevi Fountain (go at dawn for no crowds; fine at dusk too), Pantheon, Piazza Navona. "
        "Dinner suggestion: Colline Emiliane (Emilia-Romagna regional, near Spanish Steps, 3-4 day notice) "
        "or Aroma at Palazzo Manfredi (1★ Michelin, rooftop with Colosseum view at night, ~€180-220/pp — call today)."
    ),
    "2026-06-21": (
        "FLORENCE DAY TRIP (Rome base)",
        "TRAIN OUT: Frecciarossa 8502 Business Class, "
        "departs Roma Termini 06:45 local / 22:45 MT (Jun 20). Ref JJQ6Z5. 1h 45m to Firenze S.M.N. "
        "Tip: stow bags at Firenze SMN luggage storage (~€6/bag) and explore hands-free. "
        "EXCURSION: Uffizi Gallery + Michelangelo's David + Gelato Walk with art historian — "
        "09:30 local / 01:30 MT (GYG, $257.96-$368.52 paid). 3 hours. "
        "Covers: Birth of Venus (Botticelli) + da Vinci + Raphael + Titian in Uffizi; "
        "David (5.17m marble, 1504) in Accademia; authentic gelato at Gelateria dei Neri. "
        "SIGHTS: Duomo (Brunelleschi dome exterior free) · Ponte Vecchio (gold/silver shops on medieval bridge) "
        "· Piazza della Signoria (outdoor sculpture museum). "
        "LUNCH: Buca Mario (oldest restaurant in Florence, near Piazza della Signoria) "
        "or Trattoria Mario (cash only, communal tables, ribollita, lunch only). "
        "RETURN: Frecciarossa 9431 Executive Class, departs Firenze S.M.N. 18:45 local / 10:45 MT. "
        "Arrives Roma Termini ~20:30 local / 12:30 MT."
    ),
    "2026-06-22": (
        "Rome — Vatican Day (checkout tomorrow)",
        "Vatican Museums + Sistine Chapel + St. Peter's Basilica + Dome Climb: "
        "08:30 local / 00:30 MT (GYG, $766.84 paid). 4 hours. "
        "Dome climb is the move — unforgettable views from the top. "
        "Afternoon at leisure: Spanish Steps (10 min walk from hotel), Borghese Gallery if desired (must book ahead). "
        "⚠️ CHECKOUT TOMORROW: Baglioni checkout by 12:00 local / 04:00 MT Jun 23. Confirm bags packed tonight. "
        "Dinner suggestion: Glass Hostaria (1★ Michelin, Trastevere, Chef Cristina Bowerman) "
        "or La Pergola (3★ Michelin, Waldorf Cavalieri, €250+/pp — call today, books months out)."
    ),
    "2026-06-23": (
        "Rome → Civitavecchia → Silver Muse EMBARKATION",
        "Checkout Baglioni by 12:00 local / 04:00 MT. "
        "Welcome Pickups car departs hotel entrance 10:00 local / 02:00 MT (Order w-6377007-1) → Civitavecchia port. "
        "Silver Muse embarkation, Booking 298475-25, Suite 617 Classic Veranda. "
        "All meals, beverages, and select excursions included from embarkation. "
        "Specialty dining: La Dame tonight at 19:30 local / 11:30 MT ($120 for 2, pre-booked)."
    ),
    "2026-06-24": (
        "Naples, Italy — Herculaneum",
        "Excursion: Ruins of Herculaneum — 08:45 local / 00:45 MT. 3h 30m. Silversea included. "
        "Better preserved than Pompeii (pyroclastic surge sealed it instantly — wood, fabric survived). "
        "Smaller, less crowded, no Vesuvius hike required. "
        "Erik's birthday: La Dame specialty dinner tonight, 19:30-20:30 local / 11:30 MT ($120, pre-booked). "
        "Naples tip if time after excursion: espresso at any street bar — €1, best in Italy."
    ),
    "2026-06-25": (
        "Giardini Naxos, Sicily — Taormina",
        "Excursion: Greek & Roman Taormina — 09:30 local / 01:30 MT. 4h. Silversea included. "
        "Greek Theatre (3rd century BC) with Mount Etna backdrop — most photographed view in Sicily. "
        "Cable car (Funivia) from Giardini Naxos €3/way. "
        "Sicilian must: Pasticceria Etna — granita con brioche, essential morning treat."
    ),
    "2026-06-26": (
        "Siracusa, Sicily — Noto Baroque",
        "Excursion: Baroque Town of Noto — 08:45 local / 00:45 MT. 3h 30m. Silversea included. "
        "UNESCO Baroque, built in golden limestone after 1693 earthquake. "
        "Caffè Sicilia (Via V. Emanuele 125, Noto) — best granita in Sicily (pistachio, almond). "
        "Specialty dining: The Grill tonight at 19:30 local / 11:30 MT (complimentary)."
    ),
    "2026-06-27": (
        "Valletta, Malta — Game of Thrones",
        "Excursion: Game of Thrones filming locations — 09:15 local / 01:15 MT. 4h. Silversea included. "
        "St. John's Co-Cathedral: Caravaggio's only signed painting (Beheading of St. John). "
        "GoT: City walls = King's Landing · Mdina = Red Keep early seasons · Fort Ricasoli = Dragonstone. "
        "Everything walkable inside 800m × 600m walled city."
    ),
    "2026-06-28": (
        "At Sea — Adriatic Crossing",
        "Full day at sea. All ship amenities. Leisurely transit to Montenegro. "
        "Specialty dining: Silver Note tonight at 19:00-20:00 local / 11:00 MT (complimentary)."
    ),
    "2026-06-29": (
        "Kotor, Montenegro — Speedboat Blue Cave",
        "Excursion: Speedboat Adventure to Blue Cave ⭐ — 08:30 local / 00:30 MT. 4h. $318 (pre-booked). "
        "Bay of Kotor: southernmost fjord in Europe, UNESCO World Heritage. "
        "Blue Cave only accessible by water — bioluminescent, swimming from boat. "
        "Old Town walled city: Cathedral of St. Tryphon (1166), famous for its cats."
    ),
    "2026-06-30": (
        "Dubrovnik, Croatia — Beach Club Day",
        "Excursion: Day at the Beach Club ⭐ — 09:00 local / 01:00 MT. 5h. $278 (pre-booked). "
        "City Walls walk (2km, €35) is another day — today is beach. "
        "GoT sites: Stradun = Cersei Walk of Shame · Rector's Palace = Purple Wedding · Fort Lovrijenac = Red Keep exterior. "
        "Cable car to Mount Srđ if time (€30 return, stunning view of walled city)."
    ),
    "2026-07-01": (
        "Split, Croatia — Diocletian's Palace",
        "Excursion: UNESCO World Heritage Sites — 08:45 local / 00:45 MT. 4h 30m. Silversea included. "
        "Diocletian's Palace (AD 305): entire city center lives inside a Roman palace — ~3,000 residents. "
        "Peristyle: former emperor's reception hall, now hosts summer concerts. "
        "Specialty dining: La Terrazza tonight at 19:30 local / 11:30 MT (complimentary)."
    ),
    "2026-07-02": (
        "Zadar, Croatia — Salt Works & Vineyards",
        "Excursion: Nin Salt Works & Royal Vineyards — 08:45 local / 00:45 MT. 5h. Silversea included. "
        "Hand-harvested fleur de sel — chefs in Dubrovnik and Venice pay premium for it. "
        "Sea Organ (free): 35 stone steps + pipes = Adriatic waves make music. "
        "Final night aboard Silver Muse. Disembark tomorrow morning."
    ),
    "2026-07-03": (
        "Venice (Fusina) — DISEMBARKATION + Hilton Molino Stucky",
        "Disembark Fusina (Venice) AM. "
        "Venice Guide and Boat private transfer 09:00 local / 01:00 MT (Order #14878, €350 PAID) → "
        "Hilton Molino Stucky private water dock, Giudecca Island. "
        "Check-in 15:00 local / 07:00 MT. Executive Suite. $2,696.35. 3 nights. "
        "Skyline Rooftop Bar for aperitivo this evening. "
        "Dinner: Trattoria Altanella (5 min walk, legendary fritto misto, cash only, book today) "
        "or La Palanca (steps from hotel, canal-side, locals only, lunch only — closes 15:00 local / 07:00 MT)."
    ),
    "2026-07-04": (
        "Venice — Day 1",
        "Hilton Molino Stucky. Free hotel shuttle to Zattere + San Zaccaria (8 AM–midnight). "
        "Must-see: St. Mark's Basilica (go before 09:30 local / 01:30 MT — no bags), Doge's Palace. "
        "Rialto market (closes noon local / 04:00 MT) · Ponte Vecchio · Dorsoduro (Accademia). "
        "Vaporetto Line 2: Molino Stucky → San Marco 15 min, €9.50/trip or €25 day pass. "
        "Dinner: Osteria Alle Testiere (22 seats, best seafood in Venice — arrive 18:00 local / 10:00 MT at opening) "
        "or Zanze XVI (Cannaregio, local lagoon fish, same-day reservation)."
    ),
    "2026-07-05": (
        "Venice — Day 2",
        "Hilton Molino Stucky. Day at leisure. "
        "Day trips: Murano (glass, 30 min vaporetto) · Burano (colors, lace, 45 min) · Torcello (Byzantine mosaics, quietest). "
        "Cicchetti (Venetian tapas): All'Arco near Rialto market · Cantinone già Schiavi (Dorsoduro, wine walls). "
        "Checkout tomorrow: Hilton checkout 11:00 local / 03:00 MT. "
        "Consorzio Motoscafi boat at 09:00 local / 01:00 MT tomorrow (Booking 96SGY, €170 PAID). "
        "Dinner: Regina Sconta (traditional Venetian, seafood) or Trattoria da Romano (Burano, family-run 1919, fritto misto)."
    ),
    "2026-07-06": (
        "Venice → Toronto → Denver — DEPARTURE",
        "⚠️ CHECKOUT 11:00 local / 03:00 MT. "
        "Consorzio Motoscafi boat departs 09:00 local / 01:00 MT from Molino Stucky (Booking 96SGY, €170 PAID) → VCE airport. "
        "AC 817 VCE→YYZ departs 12:20 local / 04:20 MT (seats 3A/4A, PNR CXNT6Q). "
        "AC 1041 YYZ→DEN departs 18:40 MT, arrives 20:22 MT. "
        "Blacklane pickup at DEN 21:07 MT → Longmont."
    ),
}

def build_brief(today_str: str) -> str:
    today = ITINERARY.get(today_str)
    yesterday_str = str(date.fromisoformat(today_str) - timedelta(days=1))
    yesterday = ITINERARY.get(yesterday_str)
    tomorrow_str = str(date.fromisoformat(today_str) + timedelta(days=1))
    tomorrow = ITINERARY.get(tomorrow_str)

    if not today:
        return f"No McLeod itinerary entry for {today_str} — trip complete or date out of range."

    body = f"""McLeod / McGlasson — Silver Muse Mediterranean
DAILY ITINERARY BRIEF · {today_str} · 0800 MT
[All Italy-leg times: local CEST / MT — delta = CEST - 8h]
{'='*62}

TODAY: {today[0]}
{today[1]}

YESTERDAY: {yesterday[0] if yesterday else 'N/A'}
{yesterday[1] if yesterday else ''}

TOMORROW: {tomorrow[0] if tomorrow else 'N/A'}
{tomorrow[1] if tomorrow else ''}

{'='*62}
KEY CONTACTS
  Welcome Pickups (Rome): w-6377007-1 (hotel→port) / w-6377007-2 (airport→hotel)
  Venice boat (Jul 3): Venice Guide & Boat, Order #14878 — +39 041 528 5975
  Venice boat (Jul 6): Consorzio Motoscafi, Booking 96SGY — +39 041 522 2303
  Baglioni Hotel Regina: +39 06 421 111
  Hilton Molino Stucky: +39 041 272 3311
  Silversea Shoreside: 1-800-774-9996
  UA PNR (outbound): NFBDP6 | AC PNR (return): CXNT6Q
"""
    return body


if __name__ == "__main__":
    import sys
    today_str = sys.argv[1] if len(sys.argv) > 1 else str(date.today())
    brief = build_brief(today_str)
    print(brief)
