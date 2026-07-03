#!/usr/bin/env python3
"""Send cruise tool email to Nancy Lyons + Erik McLeod — with 2-hr price quote provision."""
import base64, sys
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
except ImportError:
    print("ERROR: pip install google-auth-httplib2 google-api-python-client"); sys.exit(1)

ROOT      = Path("/home/john/Thunderbird")
TOKEN     = ROOT / "creds/johnloucks3_token.json"
FROM_ADDR = "johnloucks3@gmail.com"
CC_ADDRS  = ["johnloucks3@gmail.com", "concierge@d2mluxury.quest"]
SCREENSHOT_URL = "https://d2mluxury.quest/cruises/cruise_tool_screenshot.jpg"
DANI_SIG  = (ROOT / "storage/signatures/dani_sig.html").read_text()
CMD_SIG   = (ROOT / "storage/signatures/commander_d2m_sig.html").read_text()

SUBJECT = "A free cruise discovery tool from John — your honest take welcome"

RECIPIENTS = [
    {
        "name": "Nancy",
        "email": "nancylyons73@outlook.com",
        "opener": "I hope you and Ken are doing wonderfully! John asked me to share something new with a few clients he truly values — and you were absolutely on that list.",
    },
    {
        "name": "Erik",
        "email": "emcleod@gmail.com",
        "opener": "I hope you and Melissa are enjoying some downtime after the Silver Muse — what a voyage! John wanted me to share something new with a handful of clients he trusts most, and you were at the top of the list.",
    },
]

PRICE_CAVEAT_BLOCK = """
        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:0 0 20px;">
          <tr><td style="background:rgba(255,255,255,0.06);border:1px solid rgba(201,168,76,0.5);border-radius:6px;padding:16px 20px;font-size:14px;color:#e8eaf0;line-height:1.7;">
            <div style="font-size:12px;color:#c9a84c;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:8px;">📌 On Pricing — Important Note</div>
            Fares shown in the tool are <strong style="color:#f0c040;">indicative prices</strong> pulled from public booking engines. They give you a solid sense of the range — but they may not reflect current promotions, your specific cabin category, group rates, or the host agency pricing we can access on your behalf.<br><br>
            <strong style="color:#f0c040;">Want a live quote on any sailing?</strong> Just reply with the voyage that caught your eye and John's team will confirm actual pricing within <strong style="color:#ffffff;">2 business hours</strong>. No obligation — just a real number to work with.
          </td></tr>
        </table>
"""


def build_html(name, opener):
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#07076b;font-family:Georgia,serif;">
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#07076b;">
  <tr><td align="center" style="padding:20px 10px;">
    <table width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;width:100%;background:#07076b;">

      <tr><td style="padding:32px 32px 16px;text-align:center;">
        <div style="font-size:11px;color:#c9a84c;letter-spacing:2.5px;text-transform:uppercase;margin-bottom:10px;">Dreams2Memories Travel</div>
        <div style="font-size:26px;color:#ffffff;font-weight:bold;line-height:1.25;">A Free Cruise Discovery Tool</div>
        <div style="font-size:13px;color:#c0c8e8;margin-top:8px;">Built for you — not to market to you</div>
      </td></tr>

      <tr><td style="padding:0 32px 24px;">
        <div style="height:2px;background:linear-gradient(to right,#c8930e,#f0c040,#c8930e);border-radius:1px;"></div>
      </td></tr>

      <tr><td style="padding:0 32px 24px;font-size:15px;color:#e8eaf0;line-height:1.75;">

        <p style="margin:0 0 18px;">Hi {name},</p>
        <p style="margin:0 0 18px;">{opener}</p>
        <p style="margin:0 0 18px;">John tasked Victory (our AI Chief of Staff) and me with building a <strong style="color:#f0c040;">free cruise discovery tool</strong> — a clean, no-pressure way to explore luxury sailings without the usual marketing noise. Over <strong style="color:#f0c040;">15,000 sailings across 28 cruise lines</strong>, all in one searchable place.</p>

        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:22px 0;">
          <tr><td style="background:rgba(255,255,255,0.07);border:1px solid #c9a84c;border-radius:8px;padding:18px 24px;text-align:center;">
            <div style="font-size:12px;color:#c9a84c;margin-bottom:6px;letter-spacing:1px;">TAKE IT FOR A SPIN</div>
            <a href="https://d2mluxury.quest/cruises" style="font-size:22px;font-weight:bold;color:#f0c040;text-decoration:none;">d2mluxury.quest/cruises</a>
          </td></tr>
        </table>

        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:0 0 22px;">
          <tr><td style="border-radius:6px;border:1px solid rgba(201,168,76,0.4);">
            <a href="https://d2mluxury.quest/cruises">
              <img src="{SCREENSHOT_URL}" alt="D2M Cruise Discovery Tool" width="536" style="width:100%;display:block;border-radius:5px;">
            </a>
          </td></tr>
        </table>

        <p style="margin:0 0 12px;color:#f0c040;font-weight:bold;">A few things worth exploring:</p>
        <ul style="margin:0 0 20px;padding-left:22px;color:#e8eaf0;">
          <li style="margin-bottom:9px;">Search by destination, ship name, or departure port</li>
          <li style="margin-bottom:9px;">Filter to your favorite cruise line — Regent, Silversea, Crystal, Viking, and more</li>
          <li style="margin-bottom:9px;">Compare up to 8 sailings side by side in the tray at the bottom</li>
          <li style="margin-bottom:9px;">Each line card links directly to the cruise line&#39;s booking site and CruiseMapper for vessel tracking</li>
        </ul>

        {PRICE_CAVEAT_BLOCK}

        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:0 0 20px;">
          <tr><td style="background:rgba(240,192,64,0.09);border-left:3px solid #f0c040;border-radius:4px;padding:14px 18px;font-size:14px;color:#e8eaf0;line-height:1.65;">
            <strong style="color:#f0c040;">On pricing coverage:</strong> Crystal Cruises fares are live today. Regent, Silversea, Atlas, and Explora are actively being added — expect steady improvement over the coming weeks.
          </td></tr>
        </table>

        <p style="margin:0 0 18px;">The goal is simple: <strong style="color:#f0c040;">this tool is always slanted toward your benefit, never toward marketing.</strong> No sign-up, no sales pitch — just a genuinely useful resource for when you&#39;re dreaming about your next voyage.</p>
        <p style="margin:0 0 18px;">Your honest feedback is genuinely welcomed — what works, what&#39;s confusing, what&#39;s missing. Your perspective shapes what we build next.</p>
        <p style="margin:0 0 4px;">Thank you for trusting us with your travels. We&#39;re grateful for you.</p>

      </td></tr>

      <tr><td style="padding:0 32px 20px;">
        <div style="height:1px;background:rgba(201,168,76,0.4);"></div>
      </td></tr>
      <tr><td style="padding:0 32px 14px;">{DANI_SIG}</td></tr>
      <tr><td style="padding:0 32px 14px;font-size:13px;color:#c0c8e8;">
        <span style="font-size:17px;">⚡</span>&nbsp; Victory Hale &middot; Chief of Staff, Thunderbird Wing &middot; Dreams2Memories Travel
      </td></tr>
      <tr><td style="padding:0 32px 18px;">
        <div style="height:1px;background:rgba(201,168,76,0.4);"></div>
      </td></tr>
      <tr><td style="padding:0 32px 28px;">{CMD_SIG}</td></tr>

    </table>
  </td></tr>
</table>
</body></html>"""


def get_service():
    creds = Credentials.from_authorized_user_file(str(TOKEN))
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def send_one(service, recipient):
    html = build_html(recipient["name"], recipient["opener"])
    msg = MIMEMultipart("alternative")
    msg["To"]       = recipient["email"]
    msg["From"]     = FROM_ADDR
    msg["Cc"]       = ", ".join(CC_ADDRS)
    msg["Reply-To"] = "johnloucks3+cruise-quote@gmail.com"
    msg["Subject"]  = SUBJECT
    msg.attach(MIMEText("Please view this email in an HTML-capable client.", "plain"))
    msg.attach(MIMEText(html, "html"))
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    result = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    return result["id"]


def main():
    svc = get_service()
    for r in RECIPIENTS:
        msg_id = send_one(svc, r)
        print(f"✅ SENT → {r['name']} ({r['email']}) · msg ID: {msg_id}")
    print(f"\nCC'd on all: {', '.join(CC_ADDRS)}")


if __name__ == "__main__":
    main()
