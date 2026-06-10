#!/usr/bin/env python3
"""Generate Bryana clarification HTML — disregard first email, full D2M stationery."""
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
logo_b64   = (ROOT / "storage/output/logo_email_b64.txt").read_text().strip()
avatar_b64 = (ROOT / "storage/output/dani_avatar_b64.txt").read_text().strip()
john_b64   = (ROOT / "storage/output/john_headshot_b64.txt").read_text().strip()

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

<p>Quick note &mdash; please disregard the first email I sent you today. It went out before it was ready and was missing the Telegram instructions and a few other details.</p>

<p>The correct and complete version is the second email, subject: <strong>"Good news &mdash; I worked out a path forward."</strong> That's the one with everything in it, including how to access Dani via Telegram and all the next steps.</p>

<p>Sorry for the confusion. Use that one and you're good to go.</p>

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

out = ROOT / "drafts/bryana_clarification_raw.html"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(html)
print(f"Written to {out}")
