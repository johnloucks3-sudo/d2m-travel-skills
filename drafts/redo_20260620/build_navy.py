#!/usr/bin/env python3
"""
Rebuild the 5 client emails using the PROVEN navy template from the survey email
(kuklinski_excursion_survey_intro_dani.html) — the one that rendered correctly.
Strategy: extract the exact prefix (head+header+body-open) and suffix (sig blocks)
from the gold-standard file, inject navy-styled body content. No cream, no external
cream sig files. Same prose that already passed voice QC.
"""
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
OUT = ROOT / "drafts" / "redo_20260620"
GOLD = (ROOT / "drafts/kuklinski_excursion_survey_intro_dani.html").read_text(encoding="utf-8")

BODY_OPEN = 'line-height:1.85;color:#e8f1ff;">'
PREFIX = GOLD[: GOLD.index(BODY_OPEN) + len(BODY_OPEN)]
SUFFIX = '\n    </td>\n  </tr>\n\n  ' + GOLD[GOLD.index('<!-- Mid shimmer -->'):]
# Commander edit 2026-06-20: Dani's title discloses AI.
SUFFIX = SUFFIX.replace("Luxury Travel Concierge", "Luxury AI Travel Concierge")

# ---- navy component helpers (match gold standard) ----
def P(t):  return f'<p style="margin:0 0 20px 0;">{t}</p>'
def H2(t): return ('<h2 style="color:#c8dcff;font-family:Georgia,serif;font-size:18px;'
                   'border-bottom:1px solid rgba(180,200,255,0.35);padding-bottom:8px;'
                   f'margin:0 0 18px 0;letter-spacing:1px;">{t}</h2>')
DIV = ('<div style="height:1px;margin:24px 0;background:linear-gradient(90deg,'
       'transparent 0%,rgba(220,235,255,0.5) 50%,transparent 100%);"></div>')
def NOTE_BLUE(t): return ('<div style="background:rgba(255,255,255,0.06);'
                          'border-left:4px solid rgba(100,150,255,0.7);'
                          f'padding:14px 18px;margin:0 0 22px 0;">{t}</div>')
def NOTE_GOLD(t): return ('<div style="background:rgba(255,215,0,0.07);'
                          'border-left:4px solid rgba(255,215,0,0.55);'
                          f'padding:14px 18px;margin:0 0 20px 0;border-radius:0 4px 4px 0;">{t}</div>')
def B(t):  return f'<strong style="color:#f0f6ff;">{t}</strong>'
def EM(t): return f'<em style="color:#a8c4f0;">{t}</em>'

# Commander's own AI-disclosure two-voice preface (verbatim wording from his 2026-06-20 excursion edit).
def JOHN(names):
    return P(f'{names} &mdash; (If you&rsquo;d rather hear from me directly, just say so. Using Dani as my '
             f'voice helps me keep track of the work in my travel email.) &mdash;John')

TH = ('background-color:#0a0a68;color:#e8f1ff;font-family:Georgia,serif;'
      'padding:10px 12px;text-align:left;border:1px solid rgba(180,200,255,0.2);font-size:14px;')
TD = ('padding:9px 12px;color:#d0e4ff;font-family:Georgia,serif;font-size:14px;'
      'border:1px solid rgba(180,200,255,0.15);')
TDB = ('padding:9px 12px;color:#f0f6ff;font-family:Georgia,serif;font-size:14px;font-weight:bold;'
       'border:1px solid rgba(180,200,255,0.15);')
ALT = 'background-color:rgba(255,255,255,0.04);'

def table(headers, rows):
    h = "".join(f'<th style="{TH}">{x}</th>' for x in headers)
    out = ['<table cellpadding="0" cellspacing="0" border="0" width="100%" '
           'style="border-collapse:collapse;margin:0 0 20px 0;">', f'<tr>{h}</tr>']
    for i, r in enumerate(rows):
        alt = f' style="{ALT}"' if i % 2 == 1 else ''
        cells = "".join(f'<td style="{TD}">{c}</td>' for c in r)
        out.append(f'<tr{alt}>{cells}</tr>')
    out.append('</table>')
    return "".join(out)

# Scandinavia ports as bold-prefixed paragraphs (no <ul> — matches gold standard safety)
SCAND = (H2("WHERE THIS VOYAGE TAKES YOU") +
    P("Ten nights, and the route reads like a greatest-hits of the Baltic and the North:") +
    P(f'{B("Stockholm")} &mdash; two days to start. The Vasa, the old town, the water everywhere.') +
    P(f'{B("Warnem&uuml;nde")} &mdash; your gateway to Berlin, and Rostock&rsquo;s medieval core if you&rsquo;d rather stay close.') +
    P(f'{B("Copenhagen")} &mdash; two days, Tivoli Gardens, and one of the great walking cities of Europe.') +
    P(f'{B("Kristiansand")} &mdash; Norway&rsquo;s easygoing southern coast.') +
    P(f'{B("Oslo")} &mdash; the finish, before you fly home.'))

def assemble(*parts):
    return PREFIX + "\n\n" + "\n".join(parts) + "\n" + SUFFIX

# ===================== NICHOLS =====================
nichols = assemble(
    P("Larry, Heidi &mdash;"),
    P("Hope you&rsquo;re both having a good summer. August 29th is closer than it feels &mdash; and it&rsquo;s "
      "a big one, because Heidi&rsquo;s birthday and your embarkation day are the same day. That doesn&rsquo;t "
      "happen by accident very often, and I don&rsquo;t want to waste it."),
    P("Quick check-in on where things stand and what&rsquo;s ahead."),
    H2("YOU&rsquo;RE SET"),
    P(f"Paid in full, {B('Suite 939 on Deck 9')}, flights confirmed. You arrive Stockholm on the 27th, a "
      "night at At Six before the ship, then aboard Regent Seven Seas Grandeur on the 29th. Your specialty "
      f"dining is already locked &mdash; {B('Pacific Rim, Chartreuse, and Prime 7')} &mdash; and every shore "
      "excursion you both picked is confirmed."),
    SCAND,
    DIV,
    H2("HEIDI&rsquo;S BIRTHDAY"),
    P("Embarkation evening, first night aboard, her birthday. I&rsquo;d like to set something up &mdash; a "
      "celebration at dinner, an amenity in the suite, however you want to play it."),
    NOTE_GOLD(f'{B("Is there something you&rsquo;ve got in mind, or do you want me to surprise her?")} '
              '<span style="color:#e8f1ff;">Either way, tell me and I&rsquo;ll make the arrangements with the ship.</span>'),
    H2("WHAT&rsquo;S NEXT"),
    P("Online check-in opens August 8th &mdash; I&rsquo;ll walk you through it when it does. A full pre-voyage "
      "briefing lands closer in, with everything in one place. Nothing on your end right now."),
    P("Lots of good things lined up&hellip;"),
    P('<span style="margin:0 0 6px 0;">Dani</span>'),
)

# ===================== ELY =====================
ely = assemble(
    P("Al, Amy &mdash;"),
    P("Hope you&rsquo;re both doing well. Your Scandinavia voyage is about ten weeks out now, and I keep "
      "looking at this itinerary and thinking you two picked a good one."),
    P("Quick check-in on where things stand &mdash; and one open day I want your call on."),
    H2("YOU&rsquo;RE SET"),
    P(f"Paid in full, {B('Suite 961 on Deck 9')}, flights confirmed. You arrive Stockholm on the 27th, a "
      "night at At Six, then aboard Regent Seven Seas Grandeur on the 29th. Your specialty dining is locked "
      f"&mdash; {B('Pacific Rim, Chartreuse, and Prime 7')} &mdash; and your shore excursions are confirmed."),
    SCAND,
    DIV,
    H2("KRISTIANSAND &mdash; YOUR ONE OPEN DAY"),
    P("September 5th in Kristiansand is the one port where you don&rsquo;t have an excursion selected. "
      "That&rsquo;s a real fork:"),
    NOTE_BLUE('<span style="color:#c0d8ff;">&rarr; I can line up something &mdash; the fjord country and the old '
              'town are both worth it<br>&rarr; or we leave it deliberately open so you can wander Norway&rsquo;s '
              'southern coast at your own pace</span>'),
    P("What sounds right to the two of you?"),
    H2("WHAT&rsquo;S NEXT"),
    P("Online check-in opens August 8th &mdash; I&rsquo;ll guide you through it. A full pre-voyage briefing "
      "comes closer in. Nothing needed from you today except a thought on Kristiansand."),
    P("More soon&hellip;"),
    P('Dani'),
)

# ===================== FURLOW (two-voice, Missy primary) =====================
furlow = assemble(
    P("Missy, John &mdash;"),
    P("Your Scandinavia voyage is about ten weeks out, and you&rsquo;re in good shape. Here&rsquo;s the picture."),
    H2("YOU&rsquo;RE SET"),
    P(f"Paid in full, {B('Suite 827 on Deck 8')}, flights confirmed. You arrive Stockholm on the 27th, a "
      "night at At Six, then aboard Regent Seven Seas Grandeur on the 29th. Specialty dining is locked &mdash; "
      f"{B('Pacific Rim, Chartreuse, and Prime 7')}."),
    SCAND,
    DIV,
    H2("ONE OPEN QUESTION &mdash; KRISTIANSAND"),
    P("September 5th in Kristiansand is open &mdash; no excursion picked yet. We can line up something on "
      "Norway&rsquo;s southern coast, or leave it as a free day to roam. John, I know your weeks run at full "
      "throttle, so no pressure on timing &mdash; just let me know which way you&rsquo;d lean and I&rsquo;ll handle it."),
    H2("WHAT&rsquo;S NEXT"),
    P("Online check-in opens August 8th. A full pre-voyage briefing lands closer in &mdash; flights, hotel, "
      "transfers, ports, all in one place."),
    P("Glad this one&rsquo;s finally on the calendar&hellip;"),
    P('Dani'),
)

# ===================== KUKLINSKI TP 0.5 (two-voice) =====================
kuk05 = assemble(
    P("Kyle, Rosalie &mdash; my AI staff and I have your December voyage humming in the background. I&rsquo;m "
      "letting them give you the state of play. Nothing needs doing on your end yet.<br>Thanks &mdash; John"),
    DIV,
    P("Hi Kyle and Rosalie,"),
    P("December keeps getting closer, and this one is shaping up to be something &mdash; ten nights through the "
      "Panama Canal, Christmas at sea, the six of you across three suites on Viking Mars. Here&rsquo;s where things stand."),
    H2("YOUR BOOKING"),
    table(["Item", "Detail"], [
        [B("Ship &amp; voyage"), "Viking Mars &mdash; Panama Canal, December 17&ndash;27, 2026"],
        [B("Suites"), "Kyle &amp; Rosalie, Roger &amp; Nicholas, Josh &amp; Erica &mdash; three suites"],
        [B("Payment"), "Paid in full, $21,244"],
        [B("Shipboard credit"), "$1,200 across the three suites"],
    ]),
    H2("WHAT WE&rsquo;RE WORKING ON NOW"),
    P(f"{B('Flights.')} Your Richmond group (you, Rosalie, Roger, Nicholas) out of RIC, Josh and Erica out of "
      "Florida. The search is active and I&rsquo;m tracking fares in real time &mdash; my goal is three solid "
      "options per couple with enough runway to lock in good pricing. Nothing to do yet; just know it&rsquo;s moving."),
    P(f"{B('Hotels.')} A night or two in Panama City before embarkation so the trip starts a day early instead "
      "of rushing the pier. I&rsquo;m looking near the Amador Causeway, close to the terminal. Options land "
      "alongside the flights."),
    H2("THE ROADMAP FROM HERE"),
    P(f'{B("Early August")} &mdash; my excursion picks for each port, just before Viking opens booking on the 2nd.'),
    P(f'{B("September")} &mdash; specialty dining (Manfredi&rsquo;s, Chef&rsquo;s Table) coordinated as a group so you&rsquo;re all at one table.'),
    P(f'{B("November")} &mdash; full pre-voyage briefing: flights, hotels, transfers, packing, port guides, the works.'),
    P("For now you&rsquo;re set &mdash; three suites, paid in full, a planning machine running quietly in the "
      "background. If a question pops into your head at 10 PM, you know where to find me."),
    P("More soon&hellip;"),
    P('Dani'),
)

# ===================== KUKLINSKI TP 4.3 LOGISTICS (two-voice) =====================
kuk43 = assemble(
    P("Kyle &mdash; my AI staff pulled together the December logistics: hotels, transfers, and the flight "
      "picture, plus the handful of things they need from you to start booking. I&rsquo;ve laid out our "
      "assumptions up top so you can correct anything we&rsquo;ve gotten wrong.<br>Thanks &mdash; John"),
    DIV,
    P("Hi Kyle,"),
    P("Here&rsquo;s everything for December in one place &mdash; hotels, transfers, and flights. These are our "
      "thoughts made visible: our assumptions first, so you can fix anything that&rsquo;s off, then five "
      "specific questions I need answered before I can book."),
    H2("WHAT WE&rsquo;RE PLANNING AROUND"),
    table(["Assumption", "Detail", "Status"], [
        ["Kyle &amp; Rosalie", "Departing Richmond (RIC) &mdash; connection required, no nonstop to Panama City", ""],
        ["Roger &amp; Nicholas", "Departing Richmond (RIC) &mdash; same routing", ""],
        ["Josh &amp; Erica", "Departing a Florida airport &mdash; driving from Naples to MIA / FLL / RSW, then flying", "Question 3"],
        ["All three couples", "Arrive Panama City Dec 16 &mdash; overnight buffer before embarkation", ""],
        ["Return Dec 27", "Kyle, Rosalie, Roger, Nicholas &mdash; transfer to FLL, same-day flight home to RIC", ""],
        ["Return Dec 27", "Josh &amp; Erica &mdash; driving home to Naples from Port Everglades, no flight", ""],
    ]),
    H2("PANAMA CITY HOTEL &mdash; DECEMBER 16 (3 ROOMS)"),
    P(EM("All rates are planning estimates &mdash; confirmed quotes to follow.")),
    table(["Hotel", "Per room / night*", "To terminal"], [
        ["Radisson, Amador area (purpose-built cruise hotel)", "$150&ndash;$250", "~5 min"],
        ["American Trade Hotel, Casco Viejo (Michelin)", "$280&ndash;$380", "~25 min"],
        ["Sofitel Legend, Casco Viejo (5-star waterfront)", "$450&ndash;$664", "~25&ndash;30 min"],
    ]),
    P(EM("*Planning estimates. Casco Viejo&rsquo;s cobblestone streets are worth a thought for the group "
         "&mdash; the Amador-area Radisson avoids them entirely.")),
    H2("ARRIVAL TRANSFER &mdash; DECEMBER 16"),
    P(f"My recommendation is {B('Lift Panama')} &mdash; private, English-speaking, direct from the airport, no "
      "shared stops. Roughly $55&ndash;$80 per vehicle (estimate), SUV or van depending on the final count."),
    H2("FIVE THINGS I NEED FROM YOU"),
    NOTE_BLUE('<span style="color:#c0d8ff;">'
              '&rarr; Casco Viejo charm, or Amador convenience? The cobblestones are the trade-off.<br>'
              '&rarr; One hotel for all three couples, or split by preference?<br>'
              '&rarr; Josh &amp; Erica &mdash; which Florida airport are they driving to and flying from?<br>'
              '&rarr; One arrival transfer for all six, or separate by suite?<br>'
              '&rarr; Any room preferences I should request &mdash; bed type, floor, connecting?</span>'),
    P("Answer when you get a minute and I&rsquo;ll turn estimates into confirmed bookings."),
    P("Plenty of moving parts, all of them handled&hellip;"),
    P('Dani'),
)

files = {
    "nichols_voyage_checkin.html": nichols,
    "ely_voyage_checkin.html": ely,
    "furlow_voyage_checkin.html": furlow,
    "kuklinski_tp05_status.html": kuk05,
    "kuklinski_tp43_logistics.html": kuk43,
}
for name, html in files.items():
    (OUT / name).write_text(html, encoding="utf-8")
    print(f"wrote {name}  ({len(html)} bytes)")
print("\nDONE — 5 navy-template emails (proven shell, voice-QC'd prose).")
