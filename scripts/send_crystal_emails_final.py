#!/usr/bin/env python3
"""Send both Crystal Cruises PDFs as properly formatted D2M stationery emails to John."""

import base64, json, sys
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

sys.path.insert(0, "/home/john/Thunderbird/core/email")
from thunderbird_gmail import _get_gmail_service, _get_logo_data_uri, PERSONA_DISPLAY_NAMES, COMMANDER_SIGNATURE_HTML

TO = "johnloucks3@gmail.com"
FROM_EMAIL = "d2mconcierge@gmail.com"
FROM_DISPLAY = PERSONA_DISPLAY_NAMES.get("D2M", "Dreams2Memories Travel")
LOGO = _get_logo_data_uri()

def build_stationery(content_html, title="Dreams2Memories Travel"):
    navy_banner = ""
    if LOGO:
        navy_banner = f'''
        <div style="position:relative;width:100%;max-height:180px;overflow:hidden;
                    background:linear-gradient(135deg,#003087 0%,#000d3a 100%);">
          <img src="{LOGO}" alt="Dreams2Memories Travel"
               style="width:100%;max-height:180px;object-fit:cover;object-position:center 35%;display:block;" />
          <div style="position:absolute;top:0;left:0;right:0;bottom:0;
                      background:linear-gradient(to bottom,rgba(0,0,0,0.05) 0%,rgba(0,48,135,0.35) 55%,rgba(0,13,58,0.82) 100%);"></div>
          <div style="position:absolute;bottom:0;left:0;right:0;padding:14px 28px;text-align:center;">
            <div style="color:#ffffff;font-family:Georgia,serif;font-size:18px;font-weight:bold;
                        letter-spacing:3px;text-transform:uppercase;text-shadow:0 2px 8px rgba(0,0,0,0.6);">
              Dreams2Memories Travel</div>
            <div style="color:#A9B0B7;font-family:Georgia,serif;font-size:10px;
                        letter-spacing:2px;text-transform:uppercase;margin-top:3px;font-style:italic;">
              Curating the voyage of your lifetime</div>
          </div>
        </div>'''
    else:
        navy_banner = f'''
        <div style="background:linear-gradient(135deg,#003087 0%,#001a5c 100%);padding:36px 28px;text-align:center;">
          <div style="color:#ffffff;font-family:Georgia,serif;font-size:20px;font-weight:bold;
                      letter-spacing:4px;text-transform:uppercase;">{title}</div>
          <div style="color:#A9B0B7;font-family:Georgia,serif;font-size:10px;
                      letter-spacing:2px;text-transform:uppercase;margin-top:6px;font-style:italic;">
            Curating the voyage of your lifetime</div>
        </div>'''

    silver_divider = '<div style="height:3px;background:linear-gradient(90deg,#003087,#A9B0B7,#ffffff,#A9B0B7,#003087);"></div>'

    footer = f'''
    <div style="height:3px;background:linear-gradient(90deg,#003087,#A9B0B7,#ffffff,#A9B0B7,#003087);"></div>
    <table cellpadding="0" cellspacing="0" border="0" width="100%"
           style="background:linear-gradient(135deg,#001a5c 0%,#003087 100%);">
      <tr>
        <td style="padding:14px 28px;vertical-align:middle;">
          <span style="color:#ffffff;font-family:Georgia,serif;font-size:18px;font-weight:bold;letter-spacing:4px;">
            D<span style="color:#A9B0B7;">2</span>M</span>
          <br><span style="color:#A9B0B7;font-family:Georgia,serif;font-size:9px;
                       letter-spacing:2px;text-transform:uppercase;">Dreams2Memories Travel, LLC</span>
        </td>
        <td style="padding:14px 28px;vertical-align:middle;text-align:right;">
          <a href="mailto:concierge@d2mluxury.quest"
             style="color:#ffffff;font-family:Georgia,serif;font-size:11px;text-decoration:none;letter-spacing:1px;">
            concierge@d2mluxury.quest</a>
          <br><span style="color:#A9B0B7;font-family:Georgia,serif;font-size:10px;">d2mluxury.quest</span>
        </td>
      </tr>
    </table>
    <div style="background:#000d3a;text-align:center;padding:6px;">
      <span style="color:rgba(169,176,183,0.6);font-family:Georgia,serif;font-size:9px;">
        &copy; 2026 Dreams2Memories Travel, LLC &nbsp;&middot;&nbsp; Colorado Springs, CO
      </span>
    </div>'''

    return f'''<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background-color:#eee8db;">
<div style="max-width:640px;margin:0 auto;">
  {navy_banner}
  {silver_divider}
  <div style="background-color:#f7f3ea;border-left:2px solid #A9B0B7;border-right:2px solid #A9B0B7;padding:32px 40px;">
    <div style="color:#0000ff;font-family:Georgia,'Times New Roman',serif;font-size:10.5pt;line-height:1.75;">
      {content_html}
    </div>
    {COMMANDER_SIGNATURE_HTML}
  </div>
  {footer}
</div>
</body></html>'''

def send_email(html_content, subject):
    full_html = build_stationery(html_content)
    service = _get_gmail_service()

    msg = MIMEMultipart("alternative")
    msg["to"] = TO
    msg["from"] = f'"{FROM_DISPLAY}" <{FROM_EMAIL}>'
    msg["subject"] = subject
    msg.attach(MIMEText("HTML email - view with rich content enabled", "plain"))
    msg.attach(MIMEText(full_html, "html"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    result = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    print(f"  ✅ SENT: \"{subject}\" — id={result['id']}")
    return result

def main():
    print("Building and sending Crystal Cruises emails...\n")

    send_email(
        # Version 1 — Internal Wing
        f'''
<div style="text-align:center;margin-bottom:24px;">
  <div style="display:inline-block;background:#003087;color:#FFD700;font-size:10px;font-weight:700;letter-spacing:2px;
              text-transform:uppercase;padding:4px 12px;border-radius:3px;">
    Thunderbird Intelligence Report
  </div>
</div>
<h1 style="color:#003087;font-family:Georgia,serif;font-size:24px;margin-bottom:16px;text-align:center;">
  Crystal Cruises<br><span style="font-size:18px;color:#002060;">Full-Spectrum Scan</span>
</h1>
<p style="text-align:center;color:#5C6B7A;font-size:11px;margin-bottom:20px;">
  <strong style="color:#003087;">Classification:</strong> Revenue-Tagged Market Intelligence &nbsp;|&nbsp;
  <strong style="color:#003087;">Prepared by:</strong> Lt Col Marcus "Wraith" Dembe, A2<br>
  <strong style="color:#003087;">For:</strong> Commander John "Yoda" Loucks · COS Victoria "Victory" Hale, SES-6 &nbsp;|&nbsp;
  <strong style="color:#003087;">Date:</strong> 2026-05-18
</p>
<hr style="border:none;border-top:2px solid #FFD700;margin:20px 0;">

<h2 style="color:#003087;font-family:Georgia,serif;font-size:18px;border-bottom:2px solid #FFD700;padding-bottom:6px;">
  Executive Summary
</h2>
<p>Crystal Cruises returned from a 2022 bankruptcy as a genuinely transformed product under A&amp;K Travel Group ownership. The relaunch is no cosmetic exercise — $170M in refurbishments, reduced passenger counts, 1:1 crew ratios, Nobu and Michelin dining aboard, and a first newbuild in 25 years on the way. Financial performance turned profitable in 2025. Asia 2026 is sold out. Alaska is nearly full. The product is credible ultra-luxury, not a nostalgia act.</p>
<p><strong>D2M Relevance:</strong> Crystal sits squarely in the Thunderbird target portfolio. Commission structure is advisor-favorable (base 10%, up to 16%, plus 5% new-to-Crystal bonus). Crystal Grace (2028 delivery) is a forward sales opportunity worth tracking now.</p>

<h2 style="color:#003087;font-family:Georgia,serif;font-size:18px;border-bottom:2px solid #FFD700;padding-bottom:6px;">
  Company Overview
</h2>
<p><strong>Owner:</strong> A&amp;K Travel Group (Heritage Group / Manfredi Lefebvre d'Ovidio) — acquired Crystal brand + ships at 2022 bankruptcy auction. Relaunched July 2023. Achieved net profitability in 2025. 2026 bookings ahead of all prior years. Asia SOLD OUT, Alaska approaching capacity. Three new ships on order.</p>

<h2 style="color:#003087;font-family:Georgia,serif;font-size:18px;border-bottom:2px solid #FFD700;padding-bottom:6px;">
  Ship Profiles
</h2>
<p><strong>Crystal Serenity</strong> (2003, refurb 2023) — 740 pax, 655 crew, 1:1 crew ratio. 10 dining venues including Nobu\'s Umi Uma and Michelin-starred Osteria D\'Ovidio. Deployed Mediterranean, Northern Europe.</p>
<p><strong>Crystal Symphony</strong> (1995, refurb 2023/2025) — 606 pax, 530 crew. First Alaska return since 2019 — 7 back-to-back sailings July 2026. Also Caribbean.</p>
<p><strong>Crystal Grace</strong> (2028 delivery) — First newbuild in 25 years. 650 pax all-suite. Nobu, Beefbar at sea, Monte-Carlo SBM casino. Two sister ships planned.</p>

<h2 style="color:#003087;font-family:Georgia,serif;font-size:18px;border-bottom:2px solid #FFD700;padding-bottom:6px;">
  Business Intelligence
</h2>
<p><strong>Commission:</strong> 10% base, up to 16% for luxury specialists, +5% new-to-Crystal bonus. Payment 50 days pre-departure (standard) or 30 days (Explorer Fare).</p>
<p><strong>Key pain points:</strong> Dining availability (book specialty immediately at embarkation), crew consistency (rebuilding post-bankruptcy), legacy refund overhang ($100M+ unresolved).</p>

<h2 style="color:#003087;font-family:Georgia,serif;font-size:18px;border-bottom:2px solid #FFD700;padding-bottom:6px;">
  Recommendations
</h2>
<ol>
  <li>Add Crystal to active portfolio — credible relaunch, profitable, advisor-friendly</li>
  <li>Target new-to-Crystal bonus aggressively (+5% on $25K booking = $1,250 incremental)</li>
  <li>Alaska 2026 — approaching capacity, act now</li>
  <li>Pre-brief clients on specialty dining protocol (book at embarkation)</li>
  <li>Address bankruptcy proactively: "Separate company, A&amp;K, $170M reinvested"</li>
  <li>Track Crystal Grace for 2028 forward sales</li>
</ol>
<p style="text-align:center;color:#5C6B7A;font-size:10px;margin-top:20px;">
  32 cited sources — full report in GitHub<br>
  <em>— Lt Col Marcus "Wraith" Dembe, A2 Research &amp; Market Intelligence</em>
</p>
''',
        "Crystal Cruises — Full-Spectrum Scan (Internal Wing Version)"
    )

    send_email(
        # Version 2 — Pro Bono Service
        f'''
<div style="text-align:center;margin-bottom:24px;">
  <div style="display:inline-block;background:#003087;color:#FFD700;font-size:10px;font-weight:700;letter-spacing:2px;
              text-transform:uppercase;padding:4px 12px;border-radius:3px;">
    Pro Bono Service — Analysis by AI Staff
  </div>
</div>
<h1 style="color:#003087;font-family:Georgia,serif;font-size:24px;margin-bottom:16px;text-align:center;">
  Crystal Cruises<br><span style="font-size:18px;color:#002060;">Company Profile &amp; Market Analysis</span>
</h1>
<p style="text-align:center;color:#5C6B7A;font-size:11px;margin-bottom:20px;">
  <strong style="color:#003087;">Prepared for:</strong> John Loucks, CEO &nbsp;|&nbsp;
  <strong style="color:#003087;">Researcher:</strong> Marcus Dembe (AI Research Analyst) &nbsp;|&nbsp;
  <strong style="color:#003087;">Date:</strong> 2026-05-18
</p>
<hr style="border:none;border-top:2px solid #FFD700;margin:20px 0;">

<h2 style="color:#003087;font-family:Georgia,serif;font-size:18px;border-bottom:2px solid #FFD700;padding-bottom:6px;">
  Executive Summary
</h2>
<p>Crystal Cruises returned from a 2022 bankruptcy as a genuinely transformed product under A&amp;K Travel Group ownership. $170M in refurbishments, reduced passenger counts, 1:1 crew ratios, Nobu and Michelin dining aboard, and a first newbuild in 25 years. Profitable in 2025. Asia 2026 sold out. Alaska nearly full. Commission structure is advisor-favorable (10–16% + 5% new-to-Crystal bonus). Competes directly with Regent and Seabourn.</p>

<h2 style="color:#003087;font-family:Georgia,serif;font-size:18px;border-bottom:2px solid #FFD700;padding-bottom:6px;">
  Company Overview
</h2>
<p><strong>Owner:</strong> A&amp;K Travel Group (Heritage Group). Acquired at bankruptcy auction 2022. Relaunched July 2023. Net profitable 2025. Asia SOLD OUT, Alaska near capacity. Three newbuilds on order.</p>

<h2 style="color:#003087;font-family:Georgia,serif;font-size:18px;border-bottom:2px solid #FFD700;padding-bottom:6px;">
  Fleet
</h2>
<p><strong>Crystal Serenity</strong> — 740 pax, 1:1 crew, Nobu + Michelin dining. Mediterranean/Northern Europe.<br>
<strong>Crystal Symphony</strong> — 606 pax. Alaska return July 2026 (7 back-to-back sailings). Caribbean.<br>
<strong>Crystal Grace</strong> (2028) — 650 pax all-suite. First newbuild in 25 years. Beefbar at sea. Two sister ships.</p>

<h2 style="color:#003087;font-family:Georgia,serif;font-size:18px;border-bottom:2px solid #FFD700;padding-bottom:6px;">
  Commission &amp; Incentives
</h2>
<p>10% base, up to 16% luxury specialist, +5% new-to-Crystal bonus. Payment 30–50 days pre-departure. Explorer Fare: ~20% early booking discount.</p>

<h2 style="color:#003087;font-family:Georgia,serif;font-size:18px;border-bottom:2px solid #FFD700;padding-bottom:6px;">
  Key Considerations
</h2>
<ol>
  <li><strong>Dining:</strong> Specialty restaurants fill fast — clients should book at embarkation</li>
  <li><strong>Crew:</strong> Some inconsistency reported; rebuilding post-bankruptcy</li>
  <li><strong>Legacy:</strong> $100M+ pre-bankruptcy credits unresolved — address ownership change proactively</li>
  <li><strong>No expedition</strong> ships (unlike Silversea, Seabourn)</li>
  <li><strong>Regent Seven Seas Prestige</strong> launching late 2026 — intensifies competition</li>
</ol>

<h2 style="color:#003087;font-family:Georgia,serif;font-size:18px;border-bottom:2px solid #FFD700;padding-bottom:6px;">
  Recommendations
</h2>
<ol>
  <li>Add Crystal to active portfolio</li>
  <li>Target new-to-Crystal bonus — +5% on clients new since July 2023</li>
  <li>Alaska 2026 — act now, approaching capacity</li>
  <li>Pre-brief clients on specialty dining at embarkation</li>
  <li>Track Crystal Grace for 2028 forward positioning</li>
</ol>
<p style="text-align:center;color:#5C6B7A;font-size:10px;margin-top:20px;">
  32 cited sources — full analysis in GitHub<br>
  <em>— Marcus Dembe (Research) &middot; Victoria Hale (Review) &middot; AI Staff, Dreams2Memories Travel</em>
</p>
''',
        "Crystal Cruises — Company Profile & Market Analysis (Service Version)"
    )

    print("\nBoth emails sent to johnloucks3@gmail.com.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
