#!/usr/bin/env python3
"""Generate Bryana onboarding HTML with embedded images."""
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
logo_b64 = (ROOT / "storage/output/logo_email_b64.txt").read_text().strip()
avatar_b64 = (ROOT / "storage/output/dani_avatar_b64.txt").read_text().strip()
john_b64 = (ROOT / "storage/output/john_headshot_b64.txt").read_text().strip()

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Dreams2Memories Travel</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: Georgia, 'Times New Roman', serif; color: #0000ff; background: #eee8db; line-height: 1.7; font-size: 15px; }}
  .wrapper {{ max-width: 680px; margin: 0 auto; background: #f7f3ea; border: 1px solid #e8dcc8; border-radius: 4px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); }}
  .header {{ padding: 28px 40px 20px; text-align: center; background: #0d1b2e; border-radius: 4px 4px 0 0; }}
  .logo {{ max-height: 90px; width: auto; }}
  .tagline {{ font-family: Georgia, serif; font-size: 10px; letter-spacing: 2.5px; text-transform: uppercase; color: #f5e9c8; font-style: italic; margin-top: 6px; }}
  .gold-rule {{ height: 2px; background: linear-gradient(90deg, transparent, #c9a84c, transparent); margin: 0 40px; border: none; }}
  .date-line {{ font-family: Georgia, serif; font-size: 11px; color: #718096; font-style: italic; text-align: right; padding: 14px 40px 0; }}
  .content {{ padding: 10px 40px 30px; }}
  .greeting {{ font-size: 20px; font-weight: bold; color: #0d1b2e; margin-bottom: 18px; }}
  .content p {{ margin-bottom: 14px; color: #0000ff; }}
  .content strong {{ color: #0d1b2e; }}
  .content a {{ color: #c9a84c; }}
  .sig-divider {{ width: 60px; height: 2px; background: #c9a84c; margin: 28px 0 20px 0; }}
  .sig-avatar {{ width: 64px; height: 64px; border-radius: 50%; border: 2px solid #f5e9c8; }}
  .sig-name {{ font-size: 17px; color: #0d1b2e; font-weight: bold; }}
  .sig-title {{ font-size: 11px; color: #c9a84c; letter-spacing: 1.5px; text-transform: uppercase; font-style: italic; }}
  .sig-company {{ font-size: 11px; color: #718096; }}
  .sig-contact {{ font-size: 12px; color: #718096; }}
  .sig-contact a {{ color: #0000ff; text-decoration: none; }}
  .footer {{ background: #faf8f3; border-top: 1px solid #e8dcc8; padding: 22px 40px; text-align: center; }}
  .footer-logo {{ max-height: 50px; width: auto; }}
  .footer-tagline {{ font-family: Georgia, serif; font-size: 10px; letter-spacing: 2.5px; text-transform: uppercase; color: #c9a84c; font-style: italic; margin-top: 8px; }}
  .bottom-bar {{ text-align: center; padding: 10px 40px; background: #0d1b2e; border-radius: 0 0 4px 4px; }}
  .bottom-bar span {{ font-family: Georgia, serif; font-size: 9px; letter-spacing: 2px; text-transform: uppercase; color: #c9a84c; }}
</style>
</head>
<body>
<div class="wrapper">

<div class="header">
<img src="data:image/png;base64,{logo_b64}" alt="Dreams2Memories Travel" class="logo">
<div class="tagline">Luxury Travel, Personally Crafted</div>
</div>

<hr class="gold-rule">

<div class="date-line">June 3, 2026</div>

<div class="content">

<p class="greeting">Hi Bryana,</p>

<p>I wanted to let you know that I've been able to work out a compromise so we can get you what you need even without a formal team role.</p>

<p>Here's the path forward:</p>

<p><strong>1. NDA &mdash; please sign and return</strong><br>
Before I can open anything up, I need a signed NDA on file. I've attached it here &mdash; please sign and send back.</p>

<p><strong>2. Training materials &mdash; full access</strong><br>
Once the NDA is back, I'll give you access to everything we use internally. Same training materials the team uses.</p>

<p><strong>3. Dani &mdash; your access via Telegram</strong><br>
You'll connect with Dani through Telegram. Here's how to get set up:</p>

<p><strong>Step 1 &mdash; Install Telegram</strong><br>
Download the Telegram app on your phone (iOS App Store or Google Play) or use the desktop version at <a href="https://desktop.telegram.org">desktop.telegram.org</a>. No account? You can sign up with just your phone number &mdash; it takes about 60 seconds.</p>

<p><strong>Step 2 &mdash; Find Dani</strong><br>
In Telegram, search for <strong>@d2m_dani_bot</strong> or open this link directly: <a href="https://t.me/d2m_dani_bot">https://t.me/d2m_dani_bot</a></p>

<p><strong>Step 3 &mdash; Start chatting</strong><br>
Tap Start and you're connected. Dani is our client-facing AI concierge &mdash; she handles trip research, recommendations, day-to-day client questions, and anything that touches the traveler experience. Think of her as the warm, confident voice that talks to our clients so we don't have to be in ten conversations at once.</p>

<p>You'll be working with Dani, not Hale &mdash; they serve different roles, and Dani is the right fit for what you'll be doing. She's available whenever you need her, and she learns from every interaction.</p>

<p><strong>4. What I'd ask of you</strong><br>
Spend time testing Dani over the next few weeks and even months. Put her through real scenarios. Try to break her. See where she's great and where she falls short. Then send your feedback to <strong>d2mconcierge@gmail.com</strong> &mdash; John monitors that address too, so both of us will see it.</p>

<p>Your outside perspective is valuable precisely because you're not inside the machine. I want to know what you find.</p>

<p>Welcome aboard &mdash; in the extended sense.</p>

<div class="sig-divider"></div>

<table cellpadding="0" cellspacing="0" border="0">
<tr>
<td style="padding-right: 16px; vertical-align: top;">
<img src="data:image/png;base64,{avatar_b64}" alt="Dani Moreau" class="sig-avatar" width="64" height="64">
</td>
<td style="vertical-align: top;">
<div class="sig-name">Dani Moreau</div>
<div class="sig-title">Luxury Travel Concierge</div>
<div class="sig-company">Dreams2Memories Travel, LLC</div>
<div class="sig-contact">
<a href="mailto:concierge@d2mluxury.quest">concierge@d2mluxury.quest</a> &middot;
<a href="https://d2mluxury.quest">d2mluxury.quest</a>
</div>
</td>
</tr>
</table>

<div style="margin-top: 28px; padding-top: 20px; border-top: 1px solid #e8dcc8;">
<table cellpadding="0" cellspacing="0" border="0">
<tr>
<td style="padding-right: 16px; vertical-align: top;">
<img src="data:image/jpeg;base64,{john_b64}" alt="John Loucks" class="sig-avatar" width="64" height="64">
</td>
<td style="vertical-align: top;">
<div class="sig-name">John Loucks</div>
<div class="sig-title">Owner &amp; Travel Advisor</div>
<div class="sig-company">Dreams2Memories Travel, LLC</div>
<div class="sig-contact">
<a href="mailto:concierge@d2mluxury.quest">concierge@d2mluxury.quest</a> &middot;
<a href="https://d2mluxury.quest">d2mluxury.quest</a>
</div>
</td>
</tr>
</table>
</div>

</div>

<div class="footer">
<img src="data:image/png;base64,{logo_b64}" alt="Dreams2Memories Travel" class="footer-logo">
<div class="footer-tagline">Luxury Travel, Personally Crafted</div>
</div>

<div class="bottom-bar">
<span>Dreams2Memories Travel, LLC &middot; Monument, CO</span>
</div>

</div>
</body>
</html>"""

out = ROOT / "drafts/bryana_onboarding_raw.html"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(html)
print(f"Written to {out}")
