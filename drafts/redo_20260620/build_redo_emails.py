#!/usr/bin/env python3
"""
Redo batch 2026-06-20 — John-voice rewrites.
Kuklinski (keep going) + Scandinavia trio (Nichols + Ely + Furlow, batched).
Voice rules applied: both-names salutation, 3-beat opener, "blunt" not "honest",
no-melodrama, personal CTA, no bare d2m link, "thoughts" not "thinking",
two-voice for AI-aware clients (Kyle, Furlow), confirmed-facts-only.
"""
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
OUT = ROOT / "drafts" / "redo_20260620"
OUT.mkdir(parents=True, exist_ok=True)

DANI_SIG = (ROOT / "storage/signatures/dani_sig.html").read_text(encoding="utf-8")
CMDR_SIG = (ROOT / "storage/signatures/commander_d2m_sig.html").read_text(encoding="utf-8")

CREAM = "#f7f3ea"; INK = "#0000ff"; NAVY = "#003087"; TEXT = "#1a1a1a"

def page(inner_html, john_preface=None):
    """Wrap body in USAFA stationery. Optional two-voice John preface on top."""
    preface_block = ""
    if john_preface:
        preface_block = f"""
        <div style="font-family:Georgia,serif;font-size:15px;color:{TEXT};line-height:1.55;">
          {john_preface}
        </div>
        <hr style="border:none;border-top:1px solid #c9a84c;margin:22px 0;">
        """
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:{CREAM};">
<table width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="{CREAM}" style="background:{CREAM};">
<tr><td align="center" style="padding:28px 12px;">
<table width="640" cellpadding="0" cellspacing="0" border="0" bgcolor="{CREAM}"
       style="background:{CREAM};max-width:640px;font-family:Georgia,serif;color:{TEXT};">
<tr><td style="padding:8px 30px 0 30px;">
{preface_block}
<div style="font-family:Georgia,serif;font-size:15px;color:{TEXT};line-height:1.6;">
{inner_html}
</div>
<hr style="border:none;border-top:1px solid #c9a84c;margin:26px 0 18px 0;">
{DANI_SIG}
<div style="height:14px;"></div>
<hr style="border:none;border-top:1px solid #d8cfb8;margin:14px 0;">
{CMDR_SIG}
</td></tr>
</table>
</td></tr></table>
</body></html>"""

def p(t): return f'<p style="margin:0 0 14px 0;">{t}</p>'
def h(t): return f'<p style="margin:18px 0 8px 0;font-size:16px;color:{NAVY};font-weight:bold;">{t}</p>'

# Shared Scandinavia anticipation block (ports) — reused, lightly varied per couple.
def scand_ports():
    return (
        h("Where this voyage takes you") +
        p("Ten nights, and the route reads like a greatest-hits of the Baltic and the North:") +
        f'<ul style="margin:0 0 14px 22px;padding:0;line-height:1.6;">'
        f'<li><b>Stockholm</b> — two days to start. The Vasa, the old town, the water everywhere.</li>'
        f'<li><b>Warnemünde</b> — your gateway to Berlin, and Rostock&rsquo;s medieval core if you&rsquo;d rather stay close.</li>'
        f'<li><b>Copenhagen</b> — two days, Tivoli Gardens, and one of the great walking cities of Europe.</li>'
        f'<li><b>Kristiansand</b> — Norway&rsquo;s easygoing southern coast.</li>'
        f'<li><b>Oslo</b> — the finish, before you fly home.</li>'
        f'</ul>'
    )

# ============================ SCANDINAVIA TRIO ============================

# --- NICHOLS (Larry & Heidi) — birthday-on-embarkation hook ---
nichols_body = (
    p("Hope you and Heidi are having a good summer. August 29th is closer than it feels &mdash; "
      "and it&rsquo;s a big one, because Heidi&rsquo;s birthday and your embarkation day are the same day. "
      "That doesn&rsquo;t happen by accident very often, and I don&rsquo;t want to waste it.") +
    p("Quick check-in on where things stand and what&rsquo;s ahead.") +
    h("You&rsquo;re set") +
    p("Paid in full, Suite 939 on Deck 9, flights confirmed. You arrive Stockholm on the 27th, "
      "a night at At Six before the ship, then aboard Regent Seven Seas Grandeur on the 29th. "
      "Your specialty dining is already locked &mdash; Pacific Rim, Chartreuse, and Prime 7 &mdash; and every "
      "shore excursion you both picked is confirmed.") +
    scand_ports() +
    h("Heidi&rsquo;s birthday") +
    p("Embarkation evening, first night aboard, her birthday. I&rsquo;d like to set something up &mdash; a celebration "
      "at dinner, an amenity in the suite, however you want to play it. Is there something you&rsquo;ve got in mind, "
      "or do you want me to surprise her? Either way, tell me and I&rsquo;ll make the arrangements with the ship.") +
    h("What&rsquo;s next") +
    p("Online check-in opens August 8th &mdash; I&rsquo;ll walk you through it when it does. A full pre-voyage briefing "
      "lands closer in, with everything in one place. Nothing on your end right now.") +
    p("Lots of good things lined up&hellip;.")
)
nichols_html = page(nichols_body)

# --- ELY (Al & Amy) — Kristiansand open-day hook. NO Parkinson's / NO insurance. ---
ely_body = (
    p("Hope you and Amy are doing well. Your Scandinavia voyage is about ten weeks out now, "
      "and I keep looking at this itinerary and thinking you two picked a good one.") +
    p("Quick check-in on where things stand &mdash; and one open day I want your call on.") +
    h("You&rsquo;re set") +
    p("Paid in full, Suite 961 on Deck 9, flights confirmed. You arrive Stockholm on the 27th, "
      "a night at At Six, then aboard Regent Seven Seas Grandeur on the 29th. Your specialty dining is "
      "locked &mdash; Pacific Rim, Chartreuse, and Prime 7 &mdash; and your shore excursions are confirmed.") +
    scand_ports() +
    h("Kristiansand &mdash; your one open day") +
    p("September 5th in Kristiansand is the one port where you don&rsquo;t have an excursion selected. "
      "That&rsquo;s a real fork: I can line up something &mdash; the fjord country and the old town are both worth it &mdash; "
      "or we leave it deliberately open so you can wander Norway&rsquo;s southern coast at your own pace. "
      "What sounds right to the two of you?") +
    h("What&rsquo;s next") +
    p("Online check-in opens August 8th &mdash; I&rsquo;ll guide you through it. A full pre-voyage briefing comes "
      "closer in. Nothing needed from you today except a thought on Kristiansand.") +
    p("More soon&hellip;.")
)
ely_html = page(ely_body)

# --- FURLOW (Missy & John) — AI-aware → two-voice. Missy primary. ---
furlow_preface = (
    p("Missy, John &mdash; my AI staff and I have been keeping your trip on track in the background, "
      "and it&rsquo;s been fun watching it come together. I&rsquo;m letting them lay out where we are below.") +
    p("Answer the one open question when you get a minute &mdash; no rush.<br>Thanks &mdash; John")
)
furlow_body = (
    p("Hi Missy and John,") +
    p("Your Scandinavia voyage is about ten weeks out, and you&rsquo;re in good shape. Here&rsquo;s the picture.") +
    h("You&rsquo;re set") +
    p("Paid in full, Suite 827 on Deck 8, flights confirmed. You arrive Stockholm on the 27th, a night at "
      "At Six, then aboard Regent Seven Seas Grandeur on the 29th. Specialty dining is locked &mdash; "
      "Pacific Rim, Chartreuse, and Prime 7.") +
    scand_ports() +
    h("One open question &mdash; Kristiansand") +
    p("September 5th in Kristiansand is open &mdash; no excursion picked yet. We can line up something on Norway&rsquo;s "
      "southern coast, or leave it as a free day to roam. John, I know your weeks run at full throttle, so no "
      "pressure on timing &mdash; just let me know which way you&rsquo;d lean and I&rsquo;ll handle it.") +
    h("What&rsquo;s next") +
    p("Online check-in opens August 8th. A full pre-voyage briefing lands closer in &mdash; flights, hotel, "
      "transfers, ports, all in one place.") +
    p("Glad this one&rsquo;s finally on the calendar&hellip;.")
)
furlow_html = page(furlow_body, john_preface=furlow_preface)

# ============================ KUKLINSKI (keep going) ============================

# --- KUKLINSKI TP 0.5 — status check-in (AI-aware → two-voice). Confirmed-facts-only. ---
kuk_welcome_preface = (
    p("Kyle, Rosalie &mdash; my AI staff and I have your December voyage humming in the background. "
      "I&rsquo;m letting them give you the state of play. Nothing needs doing on your end yet.<br>Thanks &mdash; John")
)
kuk_welcome_body = (
    p("Hi Kyle and Rosalie,") +
    p("December keeps getting closer, and this one is shaping up to be something &mdash; ten nights through the "
      "Panama Canal, Christmas at sea, the six of you across three suites on Viking Mars. Here&rsquo;s where things stand.") +
    h("Your booking") +
    f'<ul style="margin:0 0 14px 22px;padding:0;line-height:1.6;">'
    f'<li><b>Ship &amp; voyage:</b> Viking Mars &mdash; Panama Canal, December 17&ndash;27, 2026</li>'
    f'<li><b>Suites:</b> Kyle &amp; Rosalie, Roger &amp; Nicholas, Josh &amp; Erica &mdash; three suites</li>'
    f'<li><b>Payment:</b> paid in full, $21,244</li>'
    f'<li><b>Shipboard credit:</b> $1,200 across the three suites</li>'
    f'</ul>' +
    h("What we&rsquo;re working on now") +
    p("<b>Flights.</b> Your Richmond group (you, Rosalie, Roger, Nicholas) out of RIC, Josh and Erica out of "
      "Florida. The search is active and I&rsquo;m tracking fares in real time &mdash; my goal is three solid options "
      "per couple with enough runway to lock in good pricing. Nothing to do yet; just know it&rsquo;s moving.") +
    p("<b>Hotels.</b> A night or two in Panama City before embarkation so the trip starts a day early instead of "
      "rushing the pier. I&rsquo;m looking near the Amador Causeway, close to the terminal. Options land alongside the flights.") +
    h("The roadmap from here") +
    f'<ul style="margin:0 0 14px 22px;padding:0;line-height:1.6;">'
    f'<li><b>Early August</b> &mdash; my excursion picks for each port, just before Viking opens booking on the 2nd.</li>'
    f'<li><b>September</b> &mdash; specialty dining (Manfredi&rsquo;s, Chef&rsquo;s Table) coordinated as a group so you&rsquo;re all at one table.</li>'
    f'<li><b>November</b> &mdash; full pre-voyage briefing: flights, hotels, transfers, packing, port guides, the works.</li>'
    f'</ul>' +
    p("For now you&rsquo;re set &mdash; three suites, paid in full, a planning machine running quietly in the background. "
      "If a question pops into your head at 10 PM, you know where to find me.") +
    p("More soon&hellip;.")
)
kuk_welcome_html = page(kuk_welcome_body, john_preface=kuk_welcome_preface)

# --- KUKLINSKI TP 4.3 — Logistics (AI-aware → two-voice). Assumptions status BLANK. Estimates flagged. ---
kuk_log_preface = (
    p("Kyle &mdash; my AI staff pulled together the December logistics: hotels, transfers, and the flight picture, "
      "plus the handful of things they need from you to start booking. I&rsquo;ve laid out our assumptions up top so "
      "you can correct anything we&rsquo;ve gotten wrong.<br>Thanks &mdash; John")
)
kuk_log_body = (
    p("Hi Kyle,") +
    p("Here&rsquo;s everything for December in one place &mdash; hotels, transfers, and flights. These are our thoughts "
      "made visible: our assumptions first, so you can fix anything that&rsquo;s off, then five specific questions "
      "I need answered before I can book.") +
    h("What we&rsquo;re planning around") +
    f'<table cellpadding="6" cellspacing="0" border="0" width="100%" '
    f'style="border-collapse:collapse;font-size:14px;margin-bottom:14px;">'
    f'<tr style="background:#efe7d2;color:{NAVY};"><th align="left">Assumption</th><th align="left">Detail</th><th align="left">Status</th></tr>'
    f'<tr><td>Kyle &amp; Rosalie</td><td>Departing Richmond (RIC) &mdash; connection required, no nonstop to Panama City</td><td></td></tr>'
    f'<tr><td>Roger &amp; Nicholas</td><td>Departing Richmond (RIC) &mdash; same routing</td><td></td></tr>'
    f'<tr><td>Josh &amp; Erica</td><td>Departing a Florida airport &mdash; driving from Naples to MIA / FLL / RSW, then flying</td><td>Question 3</td></tr>'
    f'<tr><td>All three couples</td><td>Arrive Panama City Dec 16 &mdash; overnight buffer before embarkation</td><td></td></tr>'
    f'<tr><td>Return Dec 27</td><td>Kyle, Rosalie, Roger, Nicholas &mdash; transfer to FLL, same-day flight home to RIC</td><td></td></tr>'
    f'<tr><td>Return Dec 27</td><td>Josh &amp; Erica &mdash; driving home to Naples from Port Everglades, no flight</td><td></td></tr>'
    f'</table>' +
    h("Panama City hotel &mdash; December 16 (3 rooms)") +
    p("<i>All rates are planning estimates &mdash; confirmed quotes to follow.</i>") +
    f'<table cellpadding="6" cellspacing="0" border="0" width="100%" '
    f'style="border-collapse:collapse;font-size:14px;margin-bottom:14px;">'
    f'<tr style="background:#efe7d2;color:{NAVY};"><th align="left">Hotel</th><th align="left">Per room / night*</th><th align="left">To terminal</th></tr>'
    f'<tr><td>Radisson, Amador area (purpose-built cruise hotel)</td><td>$150&ndash;$250</td><td>~5 min</td></tr>'
    f'<tr><td>American Trade Hotel, Casco Viejo (Michelin)</td><td>$280&ndash;$380</td><td>~25 min</td></tr>'
    f'<tr><td>Sofitel Legend, Casco Viejo (5-star waterfront)</td><td>$450&ndash;$664</td><td>~25&ndash;30 min</td></tr>'
    f'</table>' +
    p("<i>*Planning estimates. Casco Viejo&rsquo;s cobblestone streets are worth a thought for the group &mdash; "
      "the Amador-area Radisson avoids them entirely.</i>") +
    h("Arrival transfer &mdash; December 16") +
    p("My recommendation is <b>Lift Panama</b> &mdash; private, English-speaking, direct from the airport, no shared "
      "stops. Roughly $55&ndash;$80 per vehicle (estimate), SUV or van depending on the final count.") +
    h("Five things I need from you") +
    f'<ol style="margin:0 0 14px 22px;padding:0;line-height:1.7;">'
    f'<li>Casco Viejo charm, or Amador convenience? The cobblestones are the trade-off.</li>'
    f'<li>One hotel for all three couples, or split by preference?</li>'
    f'<li>Josh &amp; Erica &mdash; which Florida airport are they driving to and flying from?</li>'
    f'<li>One arrival transfer for all six, or separate by suite?</li>'
    f'<li>Any room preferences I should request &mdash; bed type, floor, connecting?</li>'
    f'</ol>' +
    p("Answer when you get a minute and I&rsquo;ll turn estimates into confirmed bookings.") +
    p("Plenty of moving parts, all of them handled&hellip;.")
)
kuk_log_html = page(kuk_log_body, john_preface=kuk_log_preface)

# ============================ WRITE FILES ============================
files = {
    "nichols_voyage_checkin.html": nichols_html,
    "ely_voyage_checkin.html": ely_html,
    "furlow_voyage_checkin.html": furlow_html,
    "kuklinski_tp05_status.html": kuk_welcome_html,
    "kuklinski_tp43_logistics.html": kuk_log_html,
}
for name, html in files.items():
    (OUT / name).write_text(html, encoding="utf-8")
    print(f"wrote {OUT/name}  ({len(html)} bytes)")
print("\nDONE — 5 files. (Excursion TP4.2 already built+form-locked; dining TP4.1 not re-staged.)")
