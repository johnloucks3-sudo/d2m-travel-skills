#!/usr/bin/env python3
"""
Build 3 per-couple itinerary preview drafts for Regent Grandeur Storied Scandinavia.
Wraps in D2M dark navy template, creates Gmail drafts via thunderbird_gmail.
"""

import sys, os, json, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.email.thunderbird_gmail import gmail_create_draft_sync

TEMPLATE_PATH = 'storage/templates/d2m_canonical_darknavy.html'

# ── Body content for each couple ──

BODIES = {
    "furlow": """
<p style="margin:0 0 18px 0">Dear Missy &amp; John,</p>

<p style="margin:0 0 18px 0">Your Regent Seven Seas Grandeur voyage is in full motion — and I've built a dedicated page just for the two of you so you can see everything at a glance.</p>

<table cellpadding="0" cellspacing="0" border="0" style="margin:18px 0;width:100%">
<tr><td style="padding:14px 18px;background:#f5f6f8;border-radius:6px">
  <div style="font-size:15px;font-weight:bold;color:#002554;margin-bottom:6px">Your Booking</div>
  <div style="font-size:13px;color:#1a1a2e;line-height:1.7">
    Suite 827 · D-Concierge<br>
    Paid in full $15,486<br>
    <span style="color:#003594">7 excursions confirmed</span>
  </div>
</td></tr></table>

<p style="margin:0 0 18px 0">
  <a href="https://itinerary.d2mluxury.quest/cruises/itinerary_grandeur_furlow.html"
     style="color:#003594;font-weight:bold;font-size:16px">
    → View your per-couple itinerary page
  </a>
  <br>
  <span style="color:#4a4a5a;font-size:12px">Your full day-by-day, excursion details, dining, and action items.</span>
</p>

<div style="margin:20px 0;height:1px;background-color:#B2B4B2"></div>

<p style="margin:0 0 12px 0;font-size:15px;font-weight:bold;color:#002554">Excursion Highlights</p>
<ul style="margin:0 0 18px 0;padding-left:20px;color:#1a1a2e;line-height:1.8">
  <li><strong style="color:#002554">Stockholm</strong> — Highlights &amp; Vasa Museum (Aug 30)</li>
  <li><strong style="color:#002554">Berlin/Warnemünde</strong> — The Berlin Experience (Sep 1) + Amazing Rostock (Sep 2)</li>
  <li><strong style="color:#002554">Copenhagen</strong> — A Tour of Two Kingdoms (Sep 3)</li>
  <li><strong style="color:#002554">Kristiansand</strong> — Explore on Foot (Sep 6)</li>
  <li><strong style="color:#002554">Oslo</strong> — Hadeland Glass Works &amp; Fram Museum (Sep 7)</li>
</ul>

<div style="margin:20px 0;height:1px;background-color:#B2B4B2"></div>

<p style="margin:0 0 12px 0;font-size:15px;font-weight:bold;color:#002554">Specialty Dining (all 3 couples)</p>
<ul style="margin:0 0 18px 0;padding-left:20px;color:#1a1a2e;line-height:1.8">
  <li>Pacific Rim — Aug 30 at 6:30 PM</li>
  <li>Chartreuse — Sep 2 at 7:30 PM</li>
  <li>Prime 7 — Sep 4 at 6:30 PM</li>
</ul>

<div style="margin:20px 0;height:1px;background-color:#B2B4B2"></div>

<p style="margin:0 0 12px 0;font-size:15px;font-weight:bold;color:#002554">Open Items</p>
<table cellpadding="0" cellspacing="0" border="0" style="margin:0 0 18px 0;width:100%">
  <tr><td style="padding:10px 14px;background:#fdecea;border-left:3px solid #ff6432;border-radius:4px;margin-bottom:6px">
    <div style="color:#cc5200;font-size:13px">⚠️ <strong style="color:#b34700">Copenhagen (Sep 4)</strong> — No excursion booked. Was Tivoli Gardens in earlier plans. Let me know if you'd like me to add something!</div>
  </td></tr>
  <tr><td style="padding:10px 14px;background:#fdf6e3;border-left:3px solid #ffc832;border-radius:4px;margin-top:6px">
    <div style="color:#a6820a;font-size:13px">🟡 <strong style="color:#8a6d00">HEL→ARN seats</strong> (AY 811 / PNR BB4X94) — awaiting seat assignment</div>
  </td></tr>
  <tr><td style="padding:10px 14px;background:#fdf6e3;border-left:3px solid #ffc832;border-radius:4px;margin-top:6px">
    <div style="color:#a6820a;font-size:13px">🟡 <strong style="color:#8a6d00">At Six Night 1 (Aug 27)</strong> — Amex FHR, need confirmation #</div>
  </td></tr>
</table>

<p style="margin:18px 0 6px 0;font-style:italic;color:#4a4a5a">The full itinerary page has all the details — click the link above to explore. Questions on that open Copenhagen day? Just reply here and I'll make it happen.</p>

<p style="margin:18px 0 0 0;color:#1a1a2e">Warmly,<br><strong style="color:#002554">Dani</strong></p>
""",

    "elydarrow": """
<p style="margin:0 0 18px 0">Dear Al &amp; Amy,</p>

<p style="margin:0 0 18px 0">Your Regent Seven Seas Grandeur voyage is shaping up beautifully — and I've built a dedicated page just for the two of you so you can see everything at a glance.</p>

<table cellpadding="0" cellspacing="0" border="0" style="margin:18px 0;width:100%">
<tr><td style="padding:14px 18px;background:#f5f6f8;border-radius:6px">
  <div style="font-size:15px;font-weight:bold;color:#002554;margin-bottom:6px">Your Booking</div>
  <div style="font-size:13px;color:#1a1a2e;line-height:1.7">
    Suite 961<br>
    Paid in full $16,640<br>
    <span style="color:#003594">5 excursions confirmed</span>
  </div>
</td></tr></table>

<p style="margin:0 0 18px 0">
  <a href="https://itinerary.d2mluxury.quest/cruises/itinerary_grandeur_elydarrow.html"
     style="color:#003594;font-weight:bold;font-size:16px">
    → View your per-couple itinerary page
  </a>
  <br>
  <span style="color:#4a4a5a;font-size:12px">Your full day-by-day, excursion details, dining, and action items.</span>
</p>

<div style="margin:20px 0;height:1px;background-color:#B2B4B2"></div>

<p style="margin:0 0 12px 0;font-size:15px;font-weight:bold;color:#002554">Excursion Highlights</p>
<ul style="margin:0 0 18px 0;padding-left:20px;color:#1a1a2e;line-height:1.8">
  <li><strong style="color:#002554">Stockholm</strong> — Swedish Nature Experience (Aug 30)</li>
  <li><strong style="color:#002554">Berlin/Warnemünde</strong> — Amazing Rostock (Sep 1) + Medieval Flavors of Rostock (Sep 2)</li>
  <li><strong style="color:#002554">Copenhagen</strong> — Christiansborg Palace &amp; Tivoli Gardens (Sep 3) + A Tour of Two Kingdoms (Sep 4)</li>
  <li><strong style="color:#002554">Oslo</strong> — Oslo During World War II (Sep 7)</li>
</ul>

<div style="margin:20px 0;height:1px;background-color:#B2B4B2"></div>

<p style="margin:0 0 12px 0;font-size:15px;font-weight:bold;color:#002554">Specialty Dining (all 3 couples)</p>
<ul style="margin:0 0 18px 0;padding-left:20px;color:#1a1a2e;line-height:1.8">
  <li>Pacific Rim — Aug 30 at 6:30 PM</li>
  <li>Chartreuse — Sep 2 at 7:30 PM</li>
  <li>Prime 7 — Sep 4 at 6:30 PM</li>
</ul>

<div style="margin:20px 0;height:1px;background-color:#B2B4B2"></div>

<p style="margin:0 0 12px 0;font-size:15px;font-weight:bold;color:#002554">Housekeeping</p>
<table cellpadding="0" cellspacing="0" border="0" style="margin:0 0 18px 0;width:100%">
  <tr><td style="padding:10px 14px;background:#fdf6e3;border-left:3px solid #ffc832;border-radius:4px;margin-bottom:6px">
    <div style="color:#a6820a;font-size:13px">🟡 If anything changes with your health situation before the trip, please let me know — we want to make sure everything is squared away.</div>
  </td></tr>
</table>

<p style="margin:18px 0 6px 0;font-style:italic;color:#4a4a5a">The full itinerary page has all the details — click the link above to explore. Questions on anything? Just reply here.</p>

<p style="margin:18px 0 0 0;color:#1a1a2e">Warmly,<br><strong style="color:#002554">Dani</strong></p>
""",

    "nichols": """
<p style="margin:0 0 18px 0">Dear Larry &amp; Heidi,</p>

<p style="margin:0 0 18px 0">Your Regent Seven Seas Grandeur voyage is practically here — and I've built a dedicated page just for the two of you so you can see everything at a glance.</p>

<table cellpadding="0" cellspacing="0" border="0" style="margin:18px 0;width:100%">
<tr><td style="padding:14px 18px;background:#f5f6f8;border-radius:6px">
  <div style="font-size:15px;font-weight:bold;color:#002554;margin-bottom:6px">Your Booking</div>
  <div style="font-size:13px;color:#1a1a2e;line-height:1.7">
    Suite 939<br>
    Paid in full $14,986<br>
    <span style="color:#003594">7 excursions confirmed</span>
  </div>
</td></tr></table>

<p style="margin:0 0 18px 0">
  <a href="https://itinerary.d2mluxury.quest/cruises/itinerary_grandeur_nichols.html"
     style="color:#003594;font-weight:bold;font-size:16px">
    → View your per-couple itinerary page
  </a>
  <br>
  <span style="color:#4a4a5a;font-size:12px">Your full day-by-day, excursion details, dining, and action items.</span>
</p>

<div style="margin:20px 0;height:1px;background-color:#B2B4B2"></div>

<p style="margin:0 0 12px 0;font-size:15px;font-weight:bold;color:#002554">Excursion Highlights</p>
<ul style="margin:0 0 18px 0;padding-left:20px;color:#1a1a2e;line-height:1.8">
  <li><strong style="color:#002554">Stockholm</strong> — Highlights &amp; Vasa Museum (Aug 30)</li>
  <li><strong style="color:#002554">Berlin/Warnemünde</strong> — The Berlin Experience (Sep 1) + Amazing Rostock <em>and</em> Medieval Flavors of Rostock (Sep 2)</li>
  <li><strong style="color:#002554">Copenhagen</strong> — A Tour of Two Kingdoms (Sep 3) + Tivoli Gardens &amp; Canal Cruise (Sep 4)</li>
  <li><strong style="color:#002554">Oslo</strong> — Panoramic Oslo (Sep 7)</li>
</ul>

<div style="margin:20px 0;height:1px;background-color:#B2B4B2"></div>

<p style="margin:0 0 12px 0;font-size:15px;font-weight:bold;color:#002554">🎂 Special Note</p>
<p style="margin:0 0 18px 0;color:#1a1a2e">Heidi — your birthday falls on embark day (Aug 29)! We've noted it with the Grandeur team. Pacific Rim on Aug 30 will be a wonderful celebration dinner.</p>

<div style="margin:20px 0;height:1px;background-color:#B2B4B2"></div>

<p style="margin:0 0 12px 0;font-size:15px;font-weight:bold;color:#002554">Specialty Dining (all 3 couples)</p>
<ul style="margin:0 0 18px 0;padding-left:20px;color:#1a1a2e;line-height:1.8">
  <li>Pacific Rim — Aug 30 at 6:30 PM <span style="color:#003594">(Heidi's birthday dinner!)</span></li>
  <li>Chartreuse — Sep 2 at 7:30 PM</li>
  <li>Prime 7 — Sep 4 at 6:30 PM</li>
</ul>

<div style="margin:20px 0;height:1px;background-color:#B2B4B2"></div>

<p style="margin:0 0 12px 0;font-size:15px;font-weight:bold;color:#002554">Housekeeping</p>
<table cellpadding="0" cellspacing="0" border="0" style="margin:0 0 18px 0;width:100%">
  <tr><td style="padding:10px 14px;background:#eaf7ea;border-left:3px solid #64c864;border-radius:4px">
    <div style="color:#1a7a1a;font-size:13px">✅ All confirmed — nothing outstanding on your end. A few remaining group items (transfer from ARN) are being handled on our side.</div>
  </td></tr>
</table>

<p style="margin:18px 0 6px 0;font-style:italic;color:#4a4a5a">The full itinerary page has all the details — click the link above to explore. Questions on anything? Just reply here.</p>

<p style="margin:18px 0 0 0;color:#1a1a2e">Warmly,<br><strong style="color:#002554">Dani</strong></p>
"""
}


def build_full_html(couple_key):
    """Insert body content into dark navy template."""
    with open(TEMPLATE_PATH) as f:
        template = f.read()
    body_content = BODIES[couple_key]
    return template.replace("{{BODY_CONTENT}}", body_content)


# ── Create drafts ──

DRAFTS = [
    {
        "key": "furlow",
        "to": "missy.furlow@gmail.com",
        "subject": "Your Regent Grandeur — Itinerary Preview & Per-Couple Page",
    },
    {
        "key": "elydarrow",
        "to": "al.ely58@gmail.com",
        "subject": "Your Regent Grandeur — Itinerary Preview & Per-Couple Page",
    },
    {
        "key": "nichols",
        "to": "larry.nichols4811@gmail.com",
        "subject": "Your Regent Grandeur — Itinerary Preview & Per-Couple Page",
    },
]

results = []
for draft in DRAFTS:
    try:
        html_full = build_full_html(draft["key"])
        gmail_create_draft_sync(
            to=draft["to"],
            subject=draft["subject"],
            body=html_full,
        )
        results.append(f"✅ {draft['key']}: draft created → {draft['to']}")
        print(f"OK: {draft['key']} → {draft['to']}")
    except Exception as e:
        results.append(f"❌ {draft['key']}: FAILED — {e}")
        print(f"FAIL: {draft['key']}: {e}")

print("\n--- SUMMARY ---")
for r in results:
    print(r)
