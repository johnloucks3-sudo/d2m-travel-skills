import json
from pathlib import Path
OUT = Path("/home/john/Thunderbird/validations/rssc_scrape")
DOSSIER = Path("/home/john/Thunderbird/dossiers/Lyons_Nancy_Ken.md")

def fmt_excursions(d, date_sort=True):
    items = list(d["excursions"].values())
    # sort by activity date
    months={'Jan':1,'Feb':2,'Mar':3,'Apr':4,'May':5,'Jun':6,'Jul':7,'Aug':8,'Sep':9,'Oct':10,'Nov':11,'Dec':12}
    def key(e):
        try:
            dd,mm=e["activity_date"].split("-"); return (months.get(mm,99), int(dd))
        except: return (99,99)
    items.sort(key=key)
    lines=[]
    for e in items:
        lines.append(f"#### {e['title']}  ·  {e['port']}")
        lines.append(f"- **Date:** {e['activity_date']}  ·  **Duration:** {e['duration']}  ·  **Price:** {e['price']}")
        if e.get("highlights"):
            lines.append(f"\n**Highlights**\n{e['highlights']}")
        if e.get("description"):
            lines.append(f"\n**Description**\n{e['description']}")
        lines.append("")
    return "\n".join(lines)

aug = json.load(open(OUT/"2979301_capture.json"))
dec = json.load(open(OUT/"3116314_capture.json"))

sec = []
sec.append("\n\n---\n\n## PORTAL GROUND TRUTH + BOOKED EXCURSIONS (2026-06-12)")
sec.append("*Source: rssc.com GUEST portal (Pavlus booking, Nancy's own login), captured 2026-06-12. "
           "Handlers: bookedcruise.aspx + UpdateVoyage / GetGuests / GetBookingNumber / GetTexts (.ashx). "
           "Tag key: **CONFIRMED** = read from portal this session; **UNKNOWN** = not exposed by guest portal.*")
sec.append("\n### Reservations on file in Nancy's guest account (all 4)")
sec.append("| Res # | Voyage | Ship | Dates | Suite | In D2M scope |")
sec.append("|---|---|---|---|---|---|")
sec.append("| **2979301** | Athens→NY · Historic Horizons | Seven Seas Splendor | Aug 11 – Sep 6, 2026 | 847 / Deck 8 / Serenity F1 | ✅ August |")
sec.append("| **3116314** | Miami→LA · Panama Canal & Pacific Gems (GRA261229) | Seven Seas Grandeur | Dec 29, 2026 – Jan 14, 2027 | 749 / Deck 7 / Serenity F1 | ✅ December |")
sec.append("| 3116322 | London→London · Enchanted Scotland | Seven Seas Splendor | Sep 13 – 25, 2027 | 748 / Deck 7 / Serenity F1 | (out of scope) |")
sec.append("| 3116323 | London→Lisbon · Sparkling Wines & Glimmering Seas | Seven Seas Splendor | Sep 25 – Oct 8, 2027 | 748 / Deck 7 / Serenity F1 | (out of scope) |")

# ---- AUGUST ----
sec.append("\n---\n\n## AUGUST 2026 — SEVEN SEAS SPLENDOR · Res 2979301 (PORTAL GROUND TRUTH)")
sec.append("### Booking ground truth — CONFIRMED")
sec.append("| Field | Value |")
sec.append("|---|---|")
sec.append("| Reservation | 2979301 — CONFIRMED |")
sec.append("| Ship / Voyage | Seven Seas Splendor · Athens (Piraeus) → New York · Historic Horizons — CONFIRMED |")
sec.append("| Dates | Departs Aug 11, 2026 · Returns Sep 6, 2026 — CONFIRMED |")
sec.append("| Suite | 847 · Deck 8 · Serenity Suite — F1 — CONFIRMED |")
sec.append("| Guests | KENNETH LYONS (74) · NANCY LYONS (71) — CONFIRMED |")
sec.append("| Guest Registration & Ticket Contract | COMPLETE (both guests) — CONFIRMED |")
sec.append("| Payment status | \"Deposit Received\" + \"Final Payment Made\" (Mar 14, 2026) — CONFIRMED (checklist) |")
sec.append("| Shipboard Credit | **$850 total / $592 remaining** — $425 per guest, $296 available per guest — CONFIRMED |")
sec.append("| Dining | 6 of 6 dining reservations completed (Pacific Rim, Prime 7 ×2, Chartreuse ×2) — CONFIRMED |")
sec.append("| Booked shore excursions | **14** (all complimentary / $0.00) — CONFIRMED |")
sec.append("| Online check-in | Opens / due Jul 21, 2026 — CONFIRMED |")
sec.append("| Cruise fare total / balance ($) | **UNKNOWN** — guest portal does not expose cruise fare or balance; only credits + checklist. (Agent portal / TESS / Pavlus invoice required.) |")
sec.append("\n> **Discrepancy note:** Dossier previously recorded \"18 of 20 ports — booked excursions.\" "
           "Portal ground truth shows **14 booked excursions** (one per port-day across 14 dates), all complimentary. "
           "The 14 figure is authoritative as of this capture.")
sec.append("\n### Booked Shore Excursions — 14 (all Free) — CONFIRMED")
sec.append(fmt_excursions(aug))

# ---- DECEMBER ----
sec.append("\n---\n\n## DECEMBER 2026 — SEVEN SEAS GRANDEUR · Res 3116314 (PORTAL GROUND TRUTH)")
sec.append("*Nancy & Ken's OWN booking — companion sailing to Commander's 3122006 (same voyage GRA261229), separate reservation & suite. "
           "Public itinerary + port descriptions: reuse validations/rssc_scrape/3122006_itinerary_and_ports_FINAL.json (same sailing — not re-pulled).*")
sec.append("### Booking ground truth — CONFIRMED")
sec.append("| Field | Value |")
sec.append("|---|---|")
sec.append("| Reservation | 3116314 — CONFIRMED |")
sec.append("| Ship / Voyage | Seven Seas Grandeur · Miami → Los Angeles · Panama Canal & Pacific Gems · **GRA261229** — CONFIRMED |")
sec.append("| Dates | Departs Dec 29, 2026 · Returns Jan 14, 2027 — CONFIRMED |")
sec.append("| Suite | 749 · Deck 7 · Serenity Suite — F1 — CONFIRMED |")
sec.append("| Guests | KENNETH LYONS (74) · NANCY LYONS (71) — CONFIRMED |")
sec.append("| Guest Registration & Ticket Contract | COMPLETE (both guests) — CONFIRMED |")
sec.append("| Shipboard Credit | **$800 total / $800 remaining** — $400 per guest, all available — CONFIRMED |")
sec.append("| Future Cruise Credits applied | **$4,640** ($0 remaining) — CONFIRMED |")
sec.append("| Booked shore excursions | **7** (all complimentary / $0.00) — CONFIRMED |")
sec.append("| Dining reservations | Open Wed Sep 30, 2026 (8pm ET) — CONFIRMED (not yet booked) |")
sec.append("| Shore excursion booking window | Jun 2, 2026 (already booked) — CONFIRMED |")
sec.append("| Online check-in | Dec 8, 2026 — CONFIRMED |")
sec.append("| Final Payment Due | **Aug 1, 2026** (checklist label — uncrossed) — CONFIRMED label / payment NOT yet confirmed paid |")
sec.append("| Cruise fare total / balance ($) | **UNKNOWN** — guest portal does not expose cruise fare or balance. The \"Deposit Needed to Confirm\" + \"Final Payment Due\" checklist labels are ambiguous templates; do NOT infer paid/unpaid. (Agent portal / TESS / Pavlus invoice required.) |")
sec.append("\n### Booked Shore Excursions — 7 (all Free) — CONFIRMED")
sec.append(fmt_excursions(dec))

sec.append("\n---\n*Guest-portal API handlers discovered (for future re-use): "
           "`/Controls/MyAccount/Excursions/Handlers/UpdateVoyage.ashx` (voyage + ports + excursions + credits + amountDue), "
           "`GetGuests.ashx` (per-guest SBC allocation + ages), `GetBookingNumber.ashx`, `GetTexts.ashx`. "
           "Guest portal uses the SAME handler names as the agent portal. Detail page: `bookedcruise.aspx?<encrypted-id>`; "
           "bookings list: `bookedcruises.aspx`. Excursion cart `cartTotal`/`amountDue` = excursion cart only (NOT cruise fare).*")

text = "\n".join(sec)
with open(DOSSIER, "a") as f:
    f.write(text)
print("Appended", len(text), "chars to dossier. Aug excursions:", aug["excursion_count"], "Dec excursions:", dec["excursion_count"])
