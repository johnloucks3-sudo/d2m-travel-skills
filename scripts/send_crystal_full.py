#!/usr/bin/env python3
"""Send full Crystal Cruises report as two properly formatted D2M emails."""

import base64, sys, re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

sys.path.insert(0, "/home/john/Thunderbird/core/email")
from thunderbird_gmail import _get_gmail_service, _get_logo_data_uri, PERSONA_DISPLAY_NAMES, COMMANDER_SIGNATURE_HTML

import markdown

TO = "johnloucks3@gmail.com"
FROM_EMAIL = "d2mconcierge@gmail.com"
FROM_DISPLAY = PERSONA_DISPLAY_NAMES.get("D2M", "Dreams2Memories Travel")
LOGO = _get_logo_data_uri()

def md_to_html(md_text):
    return markdown.markdown(md_text, extensions=['tables', 'fenced_code'])

def build_stationery(content_html):
    navy = ""
    if LOGO:
        navy = f'''
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
        navy = f'''
        <div style="background:linear-gradient(135deg,#003087 0%,#001a5c 100%);padding:36px 28px;text-align:center;">
          <div style="color:#ffffff;font-family:Georgia,serif;font-size:20px;font-weight:bold;
                      letter-spacing:4px;text-transform:uppercase;">Dreams2Memories Travel</div>
          <div style="color:#A9B0B7;font-family:Georgia,serif;font-size:10px;
                      letter-spacing:2px;text-transform:uppercase;margin-top:6px;font-style:italic;">
            Curating the voyage of your lifetime</div>
        </div>'''

    divider = '<div style="height:3px;background:linear-gradient(90deg,#003087,#A9B0B7,#ffffff,#A9B0B7,#003087);"></div>'

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
  {navy}
  {divider}
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
    full = build_stationery(html_content)
    service = _get_gmail_service()
    msg = MIMEMultipart("alternative")
    msg["to"] = TO
    msg["from"] = f'"{FROM_DISPLAY}" <{FROM_EMAIL}>'
    msg["subject"] = subject
    msg.attach(MIMEText("HTML email - enable rich content", "plain"))
    msg.attach(MIMEText(full, "html"))
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    result = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    print(f"  ✅ SENT: \"{subject}\" — id={result['id']}")
    return result


def strip_hr(text):
    """Replace markdown HR lines with styled HR."""
    return '\n<hr style="border:none;border-top:2px solid #FFD700;margin:24px 0;">\n'.join(
        text.split('\n---\n')
    )

def main():
    with open("/home/john/Thunderbird/output/crystal_scan_2026-05-18.md") as f:
        raw = f.read()

    # Split off the header/lines before content
    parts = raw.split('## EXECUTIVE SUMMARY', 1)
    body_md = '## EXECUTIVE SUMMARY' + parts[1] if len(parts) > 1 else raw

    # ── Version 1: Internal Wing ──────────────────────────────────────────
    v1_md = body_md
    v1_html = md_to_html(v1_md)
    v1_html = strip_hr(v1_html)
    # Style tables
    v1_html = v1_html.replace('<table>',
        '<table style="width:100%;border-collapse:collapse;margin-bottom:16px;font-size:10pt;">')
    v1_html = v1_html.replace('<th>', '<th style="background:#003087;color:#FFD700;padding:6px 10px;text-align:left;font-size:9px;letter-spacing:0.5px;text-transform:uppercase;border-bottom:1px solid #d4c9b0;">')
    v1_html = v1_html.replace('<td>', '<td style="padding:6px 10px;border-bottom:1px solid #d4c9b0;color:#2c2c2c;">')
    v1_html = v1_html.replace('<strong>', '<strong style="color:#001840;">')

    # Prepend the wing header
    v1_header = f'''
<div style="text-align:center;margin-bottom:24px;">
  <div style="display:inline-block;background:#003087;color:#FFD700;font-size:10px;font-weight:700;letter-spacing:2px;
              text-transform:uppercase;padding:4px 12px;border-radius:3px;">
    Thunderbird Intelligence Report
  </div>
</div>
<h1 style="color:#003087;font-family:Georgia,serif;font-size:24px;margin-bottom:4px;text-align:center;">
  Crystal Cruises — Full-Spectrum Scan</h1>
<div style="text-align:center;font-size:11px;color:#5C6B7A;margin-bottom:24px;">
  <strong style="color:#003087;">Classification:</strong> Revenue-Tagged Market Intelligence &nbsp;|&nbsp;
  <strong style="color:#003087;">Prepared by:</strong> Lt Col Marcus "Wraith" Dembe, A2 Research &amp; Market Intelligence<br>
  <strong style="color:#003087;">For:</strong> Commander John "Yoda" Loucks · COS Victoria "Victory" Hale, SES-6 &nbsp;|&nbsp;
  <strong style="color:#003087;">Date:</strong> 2026-05-18 &nbsp;|&nbsp; Live Web Sweep
</div>
<hr style="border:none;border-top:3px solid #FFD700;margin:0 0 24px 0;">
'''

    send_email(v1_header + v1_html,
        "Crystal Cruises — Full-Spectrum Scan (Internal Wing Version)")

    # ── Version 2: Service Version (no military terms, no commission data) ──
    v2_md = body_md

    # ── SWEEP 1: Strip classification / military framing ──
    v2_md = v2_md.replace('**Classification:** Revenue-Tagged Market Intelligence\n', '')
    v2_md = v2_md.replace('**Prepared by:** Lt Col Marcus "Wraith" Dembe, A2 Research & Market Intelligence\n',
                          '**Prepared by:** Marcus Dembe, AI Research Analyst\n')
    v2_md = v2_md.replace('**For:** Commander John "Yoda" Loucks · COS Victoria "Victory" Hale, SES-6\n',
                          '**For:** John Loucks, CEO\n')
    v2_md = v2_md.replace('**Search Conducted:** Live web sweep, May 2026\n', '')
    v2_md = v2_md.replace('Revenue-Tagged Market Intelligence', 'Market Analysis')
    v2_md = v2_md.replace('(D2M Portfolio Lens)', '(Portfolio Lens)')
    v2_md = v2_md.replace('**Assessment:**', '')
    v2_md = v2_md.replace('**Competitive gap to watch:**', '**Worth watching:**')
    v2_md = v2_md.replace('**Demand Signal:**', '**Demand signal:**')

    # ── SWEEP 2: Strip commission data ──
    # Executive summary — strip D2M Relevance that mentions commission
    v2_md = v2_md.replace(
        '\n**D2M Relevance:** Crystal sits squarely in the Thunderbird target portfolio. Commission structure is advisor-favorable (base 10%, up to 16%, plus 5% new-to-Crystal bonus). The product competes directly with Regent and Seabourn for our client archetypes. Crystal Grace (2028 delivery) is a forward sales opportunity worth tracking now.',
        ''
    )
    # Entire Section 4.1 — Commission Structure
    v2_md = v2_md.replace(
        '\n#### 4.1 — Commission Structure\n\n| Element | Detail |\n|---------|--------|\n| **Base Commission Rate** | 10% of commissionable cruise revenue (minimum) |\n| **Effective Rate for Luxury Specialists** | Up to 16% (luxury cruise lines commonly pay higher tiers for volume and preferred partners) |\n| **New-to-Crystal Bonus** | +5% additional commission on bookings for guests new to Crystal, OR past guests who have not sailed Crystal since July 31, 2023 |\n| **Commission Payment — Standard Sailings (<40 nights)** | 50 days prior to departure (once paid in full, within cancellation penalty period) |\n| **Commission Payment — Long Voyages (40+ nights)** | 90 days prior to departure |\n| **Commission Payment — Explorer Fare bookings** | Within 30 days of final payment (fastest payout) |\n| **Non-Commissionable** | Discounted/reduced rate, charter, incentive, and FAM cruises |\n\n**D2M Advisor Note:** The 5% new-to-Crystal bonus is meaningful on a luxury booking. On a $20,000 base fare, that is an additional $1,000 on top of the standard commission — worth actively targeting clients who haven\'t sailed Crystal or haven\'t since the relaunch. The early-payment structure (50-day pre-departure) is significantly better than many lines\' post-departure payment models.',
        ''
    )
    # Section 4.2 — strip Explorer Fare commission-timing
    v2_md = v2_md.replace(
        '- **Explorer Fare:** ~20% early booking discount; commissions paid faster (30 days post-final payment)',
        '- **Explorer Fare:** ~20% early booking discount'
    )
    # Trade channel reference to commission
    v2_md = v2_md.replace(
        '- Faster commission payments and the 5% new-to-Crystal bonus signal deliberate advisor-friendly repositioning',
        '- Advisor-friendly policies signal deliberate trade channel investment'
    )

    # ── SWEEP 3: Strip internal D2M advisory language ──
    v2_md = v2_md.replace('**D2M Advisor Note:**', '**Note:**')
    v2_md = v2_md.replace('**D2M advisory implication:**', '')
    v2_md = v2_md.replace('**D2M Relevance:**', '**Relevance:**')
    v2_md = v2_md.replace('(Thunderbird)', '')
    v2_md = v2_md.replace('**D2M Relevance (solar eclipse):**', '')
    v2_md = v2_md.replace('D2M advisory implication:', '')
    v2_md = v2_md.replace('**D2M advisory implication:**', '')

    # ── SWEEP 4: Strip commission rows from comparison table ──
    v2_md = v2_md.replace(
        '| **Base Commission** | 10–16% | 10–16% | 10–16% | 10–16% |',
        '| **Pricing Model** | All-inclusive | All-inclusive (deepest) | All-inclusive + butler | All-inclusive |')
    v2_md = v2_md.replace(
        '| **New Advisor Bonus** | +5% new-to-Crystal | None documented | None documented | None documented |',
        '| **Advisor Program** | Active trade investment | Established | Established | Established |')

    # ── SWEEP 5: Strip commission references from recommendations ──
    v2_md = v2_md.replace(
        '\n**1. Add Crystal to active portfolio.** The relaunch is credible. Financial stability is confirmed (profitable 2025). Commission structure is advisor-favorable. The product competes honestly against Regent and Seabourn for D2M\'s existing client base.',
        '\n**1. Consider Crystal for the portfolio.** The relaunch is credible. Financial stability confirmed (profitable 2025). Product competes honestly against Regent and Seabourn.')
    v2_md = v2_md.replace(
        '\n**2. Target the New-to-Crystal bonus aggressively.** Any client who has not sailed Crystal (or hasn\'t since the relaunch) qualifies for the +5% bonus. On a $25,000 booking, that\'s $1,250 incremental to D2M. Identify which clients have sailed Regent/Seabourn/Silversea but not Crystal.',
        '\n**2. Identify Regent/Seabourn clients for Crystal consideration.** Guests sailed ultra-luxury lines but not Crystal since the relaunch are natural prospects.')

    # Strip leftover standalone "D2M" framing
    v2_md = v2_md.replace('Thunderbird Wing', 'Dreams2Memories Travel')
    v2_md = v2_md.replace('Thunderbird target portfolio', 'target portfolio')
    v2_md = v2_md.replace('D2M\'s existing client base', 'existing client base')
    v2_md = v2_md.replace('for D2M\'s', 'for')
    v2_md = v2_md.replace('for our client archetypes', '')

    v2_html = md_to_html(v2_md)
    v2_html = strip_hr(v2_html)
    v2_html = v2_html.replace('<table>',
        '<table style="width:100%;border-collapse:collapse;margin-bottom:16px;font-size:10pt;">')
    v2_html = v2_html.replace('<th>', '<th style="background:#003087;color:#FFD700;padding:6px 10px;text-align:left;font-size:9px;letter-spacing:0.5px;text-transform:uppercase;border-bottom:1px solid #d4c9b0;">')
    v2_html = v2_html.replace('<td>', '<td style="padding:6px 10px;border-bottom:1px solid #d4c9b0;color:#2c2c2c;">')
    v2_html = v2_html.replace('<strong>', '<strong style="color:#001840;">')

    # Change the sign-off line
    v2_html = v2_html.replace(
        '*— Lt Col Marcus "Wraith" Dembe, A2 Research & Market Intelligence*\n*Thunderbird Wing, Dreams2Memories Travel, LLC*\n*2026-05-18 | Intelligence sweep conducted live — all sources cited above*',
        '*— Marcus Dembe (Research) · Victoria Hale (Review) · AI Staff, Dreams2Memories Travel, LLC*\n*2026-05-18 | All sources cited above*'
    )

    # Clean up any remaining "D2M" references that slipped through
    v2_html = v2_html.replace('<strong>:</strong>', '')
    v2_html = v2_html.replace('D2M Relevance', 'Relevance')
    v2_html = v2_html.replace('D2M Advisor Note', '')
    v2_html = v2_html.replace('D2M advisory', '')

    v2_header = f'''
<div style="text-align:center;margin-bottom:24px;">
  <div style="display:inline-block;background:#003087;color:#FFD700;font-size:10px;font-weight:700;letter-spacing:2px;
              text-transform:uppercase;padding:4px 12px;border-radius:3px;">
    Company Profile
  </div>
</div>
<h1 style="color:#003087;font-family:Georgia,serif;font-size:24px;margin-bottom:4px;text-align:center;">
  Crystal Cruises — Profile &amp; Market Analysis</h1>
<div style="text-align:center;font-size:11px;color:#5C6B7A;margin-bottom:24px;">
  <strong style="color:#003087;">Prepared for:</strong> John Loucks, CEO &nbsp;|&nbsp;
  <strong style="color:#003087;">Research by:</strong> Marcus Dembe, AI Research Analyst &nbsp;|&nbsp;
  <strong style="color:#003087;">Reviewed by:</strong> Victoria Hale, AI Staff<br>
  <strong style="color:#003087;">Date:</strong> 2026-05-18 &nbsp;|&nbsp; Live Research Sweep
</div>
<hr style="border:none;border-top:3px solid #FFD700;margin:0 0 24px 0;">
'''

    send_email(v2_header + v2_html,
        "Crystal Cruises — Company Profile & Market Analysis")

    print("\nBoth sent to johnloucks3@gmail.com.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
