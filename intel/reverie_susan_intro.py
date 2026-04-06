"""
Draft: REVERIE intro email to Susan Loucks with orientation PDF attachment.
FROM: concierge@d2mluxury.quest (via d2mconcierge@gmail.com)
TO:   susanna.loucks@gmail.com
CC:   johnloucks3@gmail.com
"""

import base64
import os
import sys
import tempfile
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

sys.path.insert(0, "/home/john/Thunderbird")

from thunderbird_gmail import (
    _get_gmail_service,
    _tag_commander_review,
    _wrap_body_html,
)

# ---------------------------------------------------------------------------
# 1. Orientation PDF source HTML
# ---------------------------------------------------------------------------

ORIENTATION_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
  @page {
    size: Letter;
    margin: 0.9in 0.85in 0.9in 0.85in;
    @bottom-center {
      content: "app.d2mluxury.quest  ·  Dreams2Memories Travel, LLC  ·  " counter(page);
      font-family: Georgia, serif;
      font-size: 8pt;
      color: #8a7a60;
    }
  }

  body {
    font-family: Georgia, 'Times New Roman', serif;
    font-size: 11pt;
    line-height: 1.7;
    color: #1a1208;
    background: #fff;
    margin: 0;
    padding: 0;
  }

  /* ---- Cover band ---- */
  .cover-band {
    background-color: #0d1b2e;
    color: #f7f3ea;
    padding: 36pt 0 28pt 0;
    text-align: center;
    margin-bottom: 0;
  }
  .cover-band .voyage-label {
    font-size: 9pt;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: #c9a84c;
    margin-bottom: 8pt;
  }
  .cover-band h1 {
    font-size: 26pt;
    font-weight: normal;
    letter-spacing: 0.06em;
    margin: 0 0 6pt 0;
    color: #f7f3ea;
  }
  .cover-band .subtitle {
    font-size: 11pt;
    color: #c2b8a6;
    margin: 0;
    letter-spacing: 0.04em;
  }

  /* ---- Gold rule ---- */
  .gold-rule {
    border: none;
    border-top: 1.5pt solid #c9a84c;
    margin: 0 0 24pt 0;
  }

  /* ---- Body content ---- */
  .body-pad { padding: 0; }

  h2 {
    font-size: 13pt;
    font-weight: normal;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #0d1b2e;
    margin: 22pt 0 6pt 0;
    border-bottom: 0.5pt solid #c9a84c;
    padding-bottom: 4pt;
  }

  h3 {
    font-size: 11pt;
    font-weight: bold;
    color: #0d1b2e;
    margin: 14pt 0 4pt 0;
  }

  p { margin: 0 0 9pt 0; }

  .app-link {
    display: block;
    text-align: center;
    background: #0d1b2e;
    color: #f7f3ea;
    font-size: 13pt;
    letter-spacing: 0.12em;
    padding: 12pt 0;
    margin: 16pt 0;
    text-decoration: none;
  }

  .login-box {
    background: #f7f3ea;
    border-left: 3pt solid #c9a84c;
    padding: 10pt 16pt;
    margin: 14pt 0;
    font-size: 10.5pt;
  }
  .login-box strong { color: #0d1b2e; }

  /* ---- Feature grid ---- */
  .feature-row {
    display: flex;
    gap: 0;
    margin: 4pt 0 10pt 0;
  }
  .feature-icon {
    width: 28pt;
    flex-shrink: 0;
    font-size: 14pt;
    padding-top: 1pt;
  }
  .feature-text { flex: 1; }
  .feature-text strong { color: #0d1b2e; }

  /* ---- Offline callout ---- */
  .callout {
    background: #f7f3ea;
    border: 0.5pt solid #c9a84c;
    padding: 12pt 16pt;
    margin: 16pt 0;
    font-size: 10.5pt;
  }
  .callout strong { color: #0d1b2e; }

  /* ---- Page break ---- */
  .break { page-break-after: always; }

  /* ---- Screen table ---- */
  table.screens {
    width: 100%;
    border-collapse: collapse;
    margin: 12pt 0;
    font-size: 10.5pt;
  }
  table.screens th {
    background: #0d1b2e;
    color: #f7f3ea;
    padding: 7pt 10pt;
    text-align: left;
    font-weight: normal;
    letter-spacing: 0.06em;
    font-size: 9.5pt;
  }
  table.screens td {
    padding: 7pt 10pt;
    border-bottom: 0.5pt solid #ddd6c9;
    vertical-align: top;
  }
  table.screens tr:nth-child(even) td { background: #faf7f2; }
  .screen-name { font-weight: bold; color: #0d1b2e; white-space: nowrap; }
  .screen-path { font-size: 9pt; color: #8a7a60; font-style: italic; }

  /* ---- Footer ---- */
  .doc-footer {
    margin-top: 36pt;
    padding-top: 10pt;
    border-top: 0.5pt solid #c9a84c;
    font-size: 9pt;
    color: #8a7a60;
    text-align: center;
  }
</style>
</head>
<body>

<div class="cover-band">
  <div class="voyage-label">Silver Nova · Pacific Crossing · April 10 – May 11, 2026</div>
  <h1>REVERIE</h1>
  <div class="subtitle">Your Personal Voyage Companion &nbsp;·&nbsp; Susan Loucks</div>
</div>
<hr class="gold-rule">

<div class="body-pad">

<p>REVERIE is a private travel app built for this voyage. It lives on your phone, knows every detail of your itinerary, and works without internet at sea. This document is your orientation.</p>

<p class="app-link">app.d2mluxury.quest</p>

<div class="login-box">
  <strong>Your login:</strong> susanna.loucks@gmail.com<br>
  Enter your email address at the link above — you'll receive a magic link by email. Tap it once and you're in. Your session stays active throughout the voyage.
</div>

<p><em>This is your account. John has a separate login and cannot see your journal entries.</em></p>


<h2>The Six Screens</h2>

<table class="screens">
  <tr>
    <th>Screen</th>
    <th>What It Does</th>
  </tr>
  <tr>
    <td><span class="screen-name">REVERIE</span><br><span class="screen-path">Home</span></td>
    <td>Your dashboard. Shows the countdown to departure, then shifts to a "today" card once you're underway — what's happening, where you are, what's booked tonight. During the Pacific crossing, a <strong>Sea Letter</strong> appears each morning: a short narrative from your concierge anchored to that day's geography and evening plans.</td>
  </tr>
  <tr>
    <td><span class="screen-name">VOYAGE</span><br><span class="screen-path">Itinerary</span></td>
    <td>All 32 days — Colorado to Seattle — with a photo for each. Tap any card to expand it and see excursion times, confirmation numbers, dining reservations, and costs. ⛵ marks shore excursion days. 🍽 marks specialty dining reservations.</td>
  </tr>
  <tr>
    <td><span class="screen-name">BRIDGE</span><br><span class="screen-path">Navigation</span></td>
    <td>Live ship position on a map. Ship specs (cabin 8075 — Superior Veranda). Two clocks: Denver home time and local ship time, updating as you cross time zones. Emergency contacts at the bottom: ship medical, Silversea 24/7, D2M direct line, US Embassy Tokyo.</td>
  </tr>
  <tr>
    <td><span class="screen-name">ORACLE</span><br><span class="screen-path">Dani AI</span></td>
    <td>Your AI concierge — available around the clock. Ask anything: dining recommendations, shore excursion questions, what to pack for Juneau, Tokyo transit directions. She knows your full itinerary and trip dossier. Common responses are cached and work without Wi-Fi.</td>
  </tr>
  <tr>
    <td><span class="screen-name">JOURNAL</span><br><span class="screen-path">Private</span></td>
    <td>The Afterglow journal — yours alone. Write by typing, dictate by voice, or insert travel emojis. Attach photos from your camera roll or snap one directly. Entries show date and location. John's journal is completely separate and neither of you can read the other's.</td>
  </tr>
  <tr>
    <td><span class="screen-name">WAYFINDER</span><br><span class="screen-path">Tokyo Transit</span></td>
    <td>Step-by-step Tokyo metro directions for 7 destinations: Shinjuku, Shibuya, Ginza, Akihabara, Asakusa, Harajuku, and Harumi Port. Line names, transfer points, travel times, and fares in yen.</td>
  </tr>
</table>


<h2>The Journal — A Closer Look</h2>

<p>The journal is the feature most worth setting up before you leave Colorado. A few things to know:</p>

<div class="feature-row">
  <div class="feature-icon">🎙</div>
  <div class="feature-text"><strong>Voice dictation.</strong> Tap the mic in the composer. Speak naturally — the app transcribes and drops the text at your cursor. Works well for end-of-day impressions when typing feels like work.</div>
</div>
<div class="feature-row">
  <div class="feature-icon">📷</div>
  <div class="feature-text"><strong>Photos.</strong> Attach directly from your camera roll or take one in the moment. Multiple photos per entry. HEIC (iPhone native format) is fully supported.</div>
</div>
<div class="feature-row">
  <div class="feature-icon">🌊</div>
  <div class="feature-text"><strong>Travel emojis.</strong> Tap the emoji button for 36 voyage-specific emojis — 🚢✈️🏔️🐋🦅🌸🍣 and more. They insert at your cursor.</div>
</div>
<div class="feature-row">
  <div class="feature-icon">🔒</div>
  <div class="feature-text"><strong>Private by design.</strong> Entries are stored under your account only. John's entries are in a completely separate space. No shared view, no overlap.</div>
</div>

<p>Entries sync to the server when you have Wi-Fi. At sea without connection, new entries will save locally and sync the next time you connect — at a port, on the ship's Wi-Fi, or when you land in Seattle.</p>


<h2>Before You Leave — Three Things to Do</h2>

<p><strong>1. Log in over Wi-Fi.</strong> The app pre-caches your itinerary, bookings, sea letters, and map data the first time you log in. This is what makes it work offline for 11 Pacific sea days.</p>

<p><strong>2. Allow notifications</strong> (if prompted). Some devices ask when you first open the app.</p>

<p><strong>3. Add it to your home screen.</strong> On iPhone: tap the Share icon in Safari → "Add to Home Screen." It will install as an app icon and behave like a native app, including offline mode.</p>


<div class="callout">
  <strong>At sea without internet:</strong> All 32 days of your itinerary, your full booking detail, all 10 Sea Letters, the ship map, Tokyo transit directions, and the Dani chat (common responses) are available completely offline. The journal works offline and syncs when you reconnect.
</div>


<h2>What's Already Loaded</h2>

<p>Everything from your trip dossier is pre-loaded and requires no input from you:</p>

<div class="feature-row">
  <div class="feature-icon">✈️</div>
  <div class="feature-text">All flights — Allegiant COS→SNA, Delta LAX→HNL, JAL HNL→HND, Southwest SEA→DEN</div>
</div>
<div class="feature-row">
  <div class="feature-icon">🏨</div>
  <div class="feature-text">All hotels — Marriott Bayview Newport Beach, Hale Koa Honolulu, Hilton Odaiba Tokyo</div>
</div>
<div class="feature-row">
  <div class="feature-icon">🚢</div>
  <div class="feature-text">Silver Nova — cabin 8075 Superior Veranda, booking 566910-25, all 19 cruise nights</div>
</div>
<div class="feature-row">
  <div class="feature-icon">⛵</div>
  <div class="feature-text">All shore excursions — Kyoto Food Tour, Fuji/Hakone, Sitka Culinary Adventure, Juneau Whale Watching, Wrangell John Muir Hike, Ketchikan By Land &amp; Sea, Victoria Horse-Drawn Trolley</div>
</div>
<div class="feature-row">
  <div class="feature-icon">🍽</div>
  <div class="feature-text">All specialty dining reservations — Kaiseki, S.A.L.T. Chef's Table, La Dame, The Grill, Silver Note, La Terrazza</div>
</div>


<div class="doc-footer">
  Prepared by Danielle Moreau · Dreams2Memories Travel, LLC<br>
  app.d2mluxury.quest &nbsp;·&nbsp; concierge@d2mluxury.quest
</div>

</div><!-- body-pad -->

</body>
</html>
"""

# ---------------------------------------------------------------------------
# 2. Email body — Dani's voice
# ---------------------------------------------------------------------------

EMAIL_BODY_HTML = """John and I put something together for you before the trip, and I wanted to get it to you now while there's time to poke around.

<br><br>

It's called <strong>REVERIE</strong> — a travel app built specifically for this voyage. Every detail of your itinerary is already loaded: all 32 days, every hotel, every flight, every shore excursion, every specialty dining reservation. You don't need to enter anything.

<br><br>

<strong>Your link:</strong> <a href="https://app.d2mluxury.quest" style="color: #0000ff;">app.d2mluxury.quest</a><br>
<strong>Your login:</strong> susanna.loucks@gmail.com — you'll get a magic link by email, tap it once, you're in.

<br><br>

This is your account. John has a separate one. The one feature I want to call out specifically is the <strong>Journal</strong> — it's private to you, he can't see it, and you can write by typing, by speaking into the mic, or by attaching photos directly from your camera roll. HEIC from iPhone works fine. The journal syncs when you have Wi-Fi and holds locally when you don't.

<br><br>

The app also has your full itinerary with tap-to-expand detail on each day, a live ship map with Denver-vs-ship time clocks, step-by-step Tokyo metro directions for seven destinations, and Dani — the AI concierge — who knows your full dossier and is available at any hour.

<br><br>

One important step before you leave: <strong>log in over Wi-Fi at home.</strong> That first login pre-loads everything for offline use. You'll have your full itinerary, all ten Sea Letters, the ship map, and Dani's common responses available for all eleven Pacific sea days with no internet required.

<br><br>

I've attached a full orientation — it covers every screen and walks you through setup. The short version: install it now, log in once, and it will be ready the morning you leave Colorado.

<br><br>

Anything you can't find or want added before you sail, just let me know.

<br><br>

Dani Moreau<br>
<em>D2M Luxury Travel Concierge</em><br>
Dreams2Memories Travel, LLC<br>
<a href="mailto:concierge@d2mluxury.quest" style="color: #0000ff;">concierge@d2mluxury.quest</a>
"""


def main():
    # --- Generate PDF ---
    print("Generating orientation PDF...")
    from weasyprint import HTML as WeasyprintHTML

    pdf_path = "/tmp/REVERIE_Orientation_Susan_Loucks.pdf"
    WeasyprintHTML(string=ORIENTATION_HTML).write_pdf(pdf_path)
    print(f"  PDF written: {pdf_path} ({os.path.getsize(pdf_path):,} bytes)")

    # --- Build MIME message ---
    subject = "REVERIE — Your Pacific Crossing App"

    outer = MIMEMultipart("mixed")
    outer["To"] = "susanna.loucks@gmail.com"
    outer["Cc"] = "johnloucks3@gmail.com"
    outer["From"] = "concierge@d2mluxury.quest"
    outer["Subject"] = subject

    # HTML body with stationery
    body_wrapped = _wrap_body_html(EMAIL_BODY_HTML, persona_id="A3")
    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText("Please view this email in an HTML-capable client.", "plain"))
    alt.attach(MIMEText(body_wrapped, "html"))
    outer.attach(alt)

    # PDF attachment
    with open(pdf_path, "rb") as f:
        pdf_data = f.read()
    att = MIMEApplication(pdf_data, _subtype="pdf")
    att.add_header("Content-Disposition", "attachment",
                   filename="REVERIE_Orientation_Susan_Loucks.pdf")
    outer.attach(att)

    # --- Create Gmail draft ---
    print("Creating Gmail draft...")
    service = _get_gmail_service()
    raw = base64.urlsafe_b64encode(outer.as_bytes()).decode()
    draft = service.users().drafts().create(
        userId="me", body={"message": {"raw": raw}}
    ).execute()

    draft_id = draft["id"]
    message_id = draft.get("message", {}).get("id", "")

    # Tag for Commander review
    if message_id:
        try:
            _tag_commander_review(service, message_id)
            print(f"  Commander review label applied.")
        except Exception as e:
            print(f"  Warning: label tagging failed: {e}")

    print(f"\nDraft created.")
    print(f"  Draft ID:   {draft_id}")
    print(f"  Message ID: {message_id}")
    print(f"  Subject:    {subject}")
    print(f"  To:         susanna.loucks@gmail.com")
    print(f"  Cc:         johnloucks3@gmail.com")
    print(f"  Attachment: REVERIE_Orientation_Susan_Loucks.pdf")
    print(f"\nReview at: https://mail.google.com/mail/u/0/#drafts")


if __name__ == "__main__":
    main()
