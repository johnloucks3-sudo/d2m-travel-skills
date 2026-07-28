#!/usr/bin/env python3
"""
Draft 3 Scandinavia voyage emails — Furlow, Ely-Darrow, Nichols
Lighter USAFA palette: steel blue header, gold accent, white body
Staged as d2mconcierge drafts with THUNDERBIRD-Commander-Review label
"""
import sys
sys.path.insert(0, '/home/john/Thunderbird')
from core.email.thunderbird_gmail import gmail_create_draft_sync

STEEL_BLUE  = "#4A7DB5"
GOLD        = "#BFA14A"
LIGHT_BG    = "#EEF3FA"
CARD_BG     = "#FFFFFF"
BODY_TEXT   = "#1A2E4A"
MUTED_TEXT  = "#6B8AAA"
LIGHT_BLUE  = "#C8D8EE"


def html_shell(body_html: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Dreams2Memories Travel</title></head>
<body style="margin:0;padding:0;background-color:{LIGHT_BG};font-family:Georgia,'Times New Roman',serif;color:{BODY_TEXT};">
<table width="100%" cellpadding="0" cellspacing="0" style="background-color:{LIGHT_BG};">
<tr><td align="center" style="padding:28px 16px;">
<table width="600" cellpadding="0" cellspacing="0" style="background-color:{CARD_BG};border-radius:6px;overflow:hidden;box-shadow:0 2px 10px rgba(0,0,0,0.10);">

<!-- HEADER -->
<tr><td style="background-color:{STEEL_BLUE};padding:30px 40px 22px;">
  <div style="font-family:Georgia,serif;font-size:20px;font-weight:bold;color:#ffffff;letter-spacing:1.5px;text-transform:uppercase;">Dreams2Memories Travel</div>
  <div style="font-size:11px;color:{LIGHT_BLUE};letter-spacing:2px;margin-top:5px;text-transform:uppercase;">Luxury Travel &nbsp;·&nbsp; Tailored Experiences</div>
</td></tr>

<!-- GOLD ACCENT -->
<tr><td style="background-color:{GOLD};height:4px;"></td></tr>

<!-- BODY -->
<tr><td style="padding:36px 40px 28px;">
{body_html}
</td></tr>

<!-- GOLD ACCENT -->
<tr><td style="background-color:{GOLD};height:2px;"></td></tr>

<!-- FOOTER -->
<tr><td style="background-color:{STEEL_BLUE};padding:18px 40px;">
  <div style="color:{LIGHT_BLUE};font-size:11px;text-align:center;letter-spacing:0.5px;">
    DREAMS2MEMORIES TRAVEL, LLC &nbsp;·&nbsp; 719-291-0742 &nbsp;·&nbsp; johnloucks3@gmail.com
  </div>
</td></tr>

</table>
</td></tr>
</table>
</body>
</html>"""


def section_divider():
    return f'<tr><td colspan="2" style="border-bottom:1px solid #D8E4F0;padding:0 0 16px;margin-bottom:16px;"></td></tr>'


def itinerary_table(rows: list[tuple[str,str]]) -> str:
    """rows: list of (label, value)"""
    cells = "".join(
        f'<tr>'
        f'<td style="padding:6px 12px 6px 0;font-size:13px;color:{MUTED_TEXT};white-space:nowrap;vertical-align:top;">{label}</td>'
        f'<td style="padding:6px 0 6px 12px;font-size:13px;color:{BODY_TEXT};vertical-align:top;">{value}</td>'
        f'</tr>'
        for label, value in rows
    )
    return f'<table cellpadding="0" cellspacing="0" style="width:100%;margin:18px 0;">{cells}</table>'


# ─── FURLOW ───────────────────────────────────────────────────────────────────
FURLOW_BODY = f"""
<p style="font-size:15px;line-height:1.6;margin:0 0 20px;">John and Missy,</p>

<p style="font-size:15px;line-height:1.6;margin:0 0 20px;">
Thirty-four days. Your Scandinavia voyage is almost here, and everything is
in place. Here is where things stand.
</p>

{itinerary_table([
    ("Voyage",      "Storied Scandinavia — Aug 29 &ndash; Sep 8, 2026"),
    ("Ship",        "Seven Seas Grandeur &nbsp;|&nbsp; Suite 827, Deck 8"),
    ("Pre-cruise",  "At Six Stockholm &mdash; Nights of Aug 27 &amp; 28 (confirmed)"),
    ("Stockholm",   "Vasa Museum excursion &mdash; morning sail from Djurg&aring;rden"),
    ("Berlin",      "Full-day bus tour: Brandenburg Gate &rarr; Fernsehturm &rarr; Reichstag"),
    ("Warnem&uuml;nde", "Seaside Baltic morning &mdash; Teepott lighthouse, Strand-k&ouml;rbe"),
    ("Copenhagen",  "Two Kingdoms &mdash; Kronborg Castle &amp; Frederiksborg Palace (8:45 AM)"),
    ("Kristiansand","Guided walk through Posebyen &mdash; 1641 whitewashed old quarter"),
    ("Oslo",        "Fram Museum &amp; Hadeland &mdash; polar ship &amp; Norwegian countryside"),
    ("Dining",      "Pacific Rim (6:30 PM) &nbsp;&middot;&nbsp; Chartreuse (7:30 PM) &nbsp;&middot;&nbsp; Prime 7 (6:30 PM)"),
])}

<p style="font-size:15px;line-height:1.7;margin:20px 0 20px;">
I want you to know how much it means to me that you trusted me with this trip.
Scandinavia in August is one of the great privileges of this life &mdash; long
golden evenings over Stockholm&rsquo;s water, the impossible green of the Danish
countryside, the quiet drama of the Oslofjord at sunrise. You are going to feel
every bit of it. I am proud to have built this with you.
</p>

<p style="font-size:14px;line-height:1.6;margin:0 0 16px;color:{MUTED_TEXT};">
<strong style="color:{BODY_TEXT};">What comes next:</strong> I will be in touch shortly to collect payment
for your private airport transfer (Stockholm Arlanda &rarr; At Six). That is the
last open item before you fly.
</p>

<p style="font-size:14px;line-height:1.6;margin:0 0 8px;border-left:3px solid {GOLD};padding-left:14px;color:{BODY_TEXT};">
<strong>A word on your next voyage:</strong> If anything on this trip moves
you &mdash; a ship, a destination, an itinerary &mdash; Regent offers a Future Cruise
Credit you can book right from the gangway. No pressure, no obligation. It simply
locks your options before you leave the ship, and you can cancel without penalty
if plans change. Worth knowing.
</p>

<p style="font-size:15px;line-height:1.6;margin:24px 0 6px;">
With gratitude,
</p>
<p style="font-size:15px;margin:0 0 4px;"><strong>John A. Loucks III</strong></p>
<p style="font-size:13px;color:{MUTED_TEXT};margin:0;">Owner &nbsp;|&nbsp; Dreams2Memories Travel, LLC<br>
719-291-0742</p>
"""

# ─── ELY-DARROW ───────────────────────────────────────────────────────────────
ELY_DARROW_BODY = f"""
<p style="font-size:15px;line-height:1.6;margin:0 0 20px;">Al and Amy,</p>

<p style="font-size:15px;line-height:1.6;margin:0 0 20px;">
Thirty-four days out. Every detail of your Scandinavia voyage is confirmed
and ready, and I could not be more excited for you.
</p>

{itinerary_table([
    ("Voyage",      "Storied Scandinavia &mdash; Aug 29 &ndash; Sep 8, 2026"),
    ("Ship",        "Seven Seas Grandeur &nbsp;|&nbsp; Suite 961, Deck 9"),
    ("Pre-cruise",  "At Six Stockholm &mdash; Nights of Aug 27 &amp; 28 (your own reservation, confirmed)"),
    ("Stockholm",   "Two nights in the Capital District &mdash; Gamla Stan cobblestones, Biblioteksgatan shopping"),
    ("Warnem&uuml;nde", "Rostock Hanseatic city excursion (9:00 AM departure)"),
    ("Copenhagen",  "Christiansborg Palace &amp; Tivoli Gardens (afternoon, 1:30 PM)"),
    ("Kristiansand","Posebyen old quarter &mdash; Norway&rsquo;s best-preserved 17th-century street grid"),
    ("Oslo",        "WWII history &mdash; resistance, occupation, and liberation sites"),
    ("Dining",      "Pacific Rim (6:30 PM) &nbsp;&middot;&nbsp; Chartreuse (7:30 PM) &nbsp;&middot;&nbsp; Prime 7 (6:30 PM)"),
    ("At sea",      "A birthday at sea &mdash; Amy, the Baltic on August 31 is yours"),
])}

<p style="font-size:15px;line-height:1.7;margin:20px 0 20px;">
You placed a great deal of trust in me when you said yes to this voyage, and
I have thought about that. What I hope for you is this: that somewhere between
Stockholm and Oslo, probably when you least expect it, you look out at that
Baltic horizon and feel exactly what you came for. That is what all of this
has been for.
</p>

<p style="font-size:14px;line-height:1.6;margin:0 0 16px;color:{MUTED_TEXT};">
<strong style="color:{BODY_TEXT};">What comes next:</strong> I will reach out shortly to collect payment
for your private airport transfer (Stockholm Arlanda &rarr; At Six) and to
coordinate your At Six hotel payment. Two easy items &mdash; then you are done
until August.
</p>

<p style="font-size:14px;line-height:1.6;margin:0 0 8px;border-left:3px solid {GOLD};padding-left:14px;color:{BODY_TEXT};">
<strong>A thought for your next adventure:</strong> Regent makes it easy to
lock in a Future Cruise Credit right aboard ship &mdash; same great terms,
your schedule, your destination. If anything on this voyage sparks an idea,
it is the simplest way to hold your place in line. No commitment required.
</p>

<p style="font-size:15px;line-height:1.6;margin:24px 0 6px;">
With gratitude,
</p>
<p style="font-size:15px;margin:0 0 4px;"><strong>John A. Loucks III</strong></p>
<p style="font-size:13px;color:{MUTED_TEXT};margin:0;">Owner &nbsp;|&nbsp; Dreams2Memories Travel, LLC<br>
719-291-0742</p>
"""

# ─── NICHOLS ──────────────────────────────────────────────────────────────────
NICHOLS_BODY = f"""
<p style="font-size:15px;line-height:1.6;margin:0 0 20px;">Larry and Heidi,</p>

<p style="font-size:15px;line-height:1.6;margin:0 0 20px;">
Thirty-four days. And Heidi &mdash; yours begins the moment you step aboard.
Everything is confirmed and in place.
</p>

{itinerary_table([
    ("Voyage",      "Storied Scandinavia &mdash; Aug 29 &ndash; Sep 8, 2026"),
    ("Ship",        "Seven Seas Grandeur &nbsp;|&nbsp; Suite 939, Deck 9"),
    ("Pre-cruise",  "At Six Stockholm &mdash; Nights of Aug 27 &amp; 28 (Amex FHR, confirmed)"),
    ("Stockholm",   "Vasa Museum excursion &mdash; a 17th-century warship, perfectly preserved"),
    ("Berlin",      "Full-day: Brandenburg Gate, Fernsehturm, the sweep of reunified Berlin"),
    ("Warnem&uuml;nde", "Baltic morning &mdash; Teepott, lighthouse, and the North Sea air"),
    ("Copenhagen",  "Two Kingdoms &mdash; Kronborg &amp; Frederiksborg castles (8:45 AM)"),
    ("Kristiansand","Posebyen old quarter walk &mdash; white wooden houses, 1641 street plan"),
    ("Oslo",        "Panoramic Oslo &mdash; Vigeland, Opera House, harbor &amp; city in full"),
    ("Dining",      "Pacific Rim (6:30 PM) &nbsp;&middot;&nbsp; Chartreuse (7:30 PM) &nbsp;&middot;&nbsp; Prime 7 (6:30 PM)"),
    ("Aug 29",      "Embarkation Day &mdash; and a birthday. The ship is ready for you, Heidi."),
])}

<p style="font-size:15px;line-height:1.7;margin:20px 0 20px;">
I have loved building this trip with you. Scandinavia has a quality that is
hard to name &mdash; something older and quieter than most places, and deeply
beautiful. The Oslofjord sailing in alone is worth the flight. I am grateful
you let me be the one to put all of this together.
</p>

<p style="font-size:14px;line-height:1.6;margin:0 0 16px;color:{MUTED_TEXT};">
<strong style="color:{BODY_TEXT};">What comes next:</strong> I will be in touch shortly to collect
payment for your private airport transfer (Stockholm Arlanda &rarr; At Six).
That closes the last open item.
</p>

<p style="font-size:14px;line-height:1.6;margin:0 0 8px;border-left:3px solid {GOLD};padding-left:14px;color:{BODY_TEXT};">
<strong>One thing worth knowing:</strong> If anything on this voyage fires up
your sense of adventure, Regent offers a Future Cruise Credit right aboard ship.
It locks your options &mdash; ship, dates, itinerary &mdash; without binding you
to anything specific. No pressure, just an open door if you want it.
</p>

<p style="font-size:15px;line-height:1.6;margin:24px 0 6px;">
With gratitude,
</p>
<p style="font-size:15px;margin:0 0 4px;"><strong>John A. Loucks III</strong></p>
<p style="font-size:13px;color:{MUTED_TEXT};margin:0;">Owner &nbsp;|&nbsp; Dreams2Memories Travel, LLC<br>
719-291-0742</p>
"""


drafts = [
    {
        "to": "missy.furlow@gmail.com",
        "cc": "john.furlow@tpf.org",
        "subject": "Your Scandinavia Voyage — 34 Days Away",
        "body": html_shell(FURLOW_BODY),
        "label": "Furlow",
    },
    {
        "to": "al.ely58@gmail.com",
        "cc": "amy.darrow@me.com",  # NOTE: me.com has SPF/DKIM issue from concierge — Commander review before send
        "subject": "Your Scandinavia Voyage — 34 Days Away",
        "body": html_shell(ELY_DARROW_BODY),
        "label": "Ely-Darrow",
    },
    {
        "to": "larry.nichols@example.com",  # placeholder — update from TESS/dossier
        "cc": "",
        "subject": "Your Scandinavia Voyage — 34 Days Away, Heidi's Birthday Edition",
        "body": html_shell(NICHOLS_BODY),
        "label": "Nichols",
    },
]

for d in drafts:
    try:
        result = gmail_create_draft_sync(
            to=d["to"],
            subject=d["subject"],
            body=d["body"],
            persona_id="CONCIERGE",
        )
        print(f"[OK] {d['label']}: draft_id={result.get('id','?')}")
    except Exception as e:
        print(f"[ERR] {d['label']}: {e}")
