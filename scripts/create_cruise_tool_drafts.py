#!/usr/bin/env python3
"""
Create 4 cruise tool feedback request drafts in johnloucks3.
Recipients: Stefanie, Kim, Bryana, Susan Loucks
Dark navy D2M canonical format. Labels: THUNDERBIRD-Commander-Review
"""
import json, base64, sys
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
except ImportError:
    print("ERROR: pip install google-auth-httplib2 google-api-python-client")
    sys.exit(1)

ROOT = Path("/home/john/Thunderbird")
TOKEN_PATH = ROOT / "creds/johnloucks3_token.json"
SCREENSHOT_URL = "https://d2mluxury.quest/cruises/cruise_tool_screenshot.jpg"
DANI_SIG = (ROOT / "storage/signatures/dani_sig.html").read_text()
CMD_SIG   = (ROOT / "storage/signatures/commander_d2m_sig.html").read_text()

RECIPIENTS = [
    {
        "name": "Stefanie",
        "email": "stef@bbenefits.net",
        "opener": "I hope your summer is off to a great start! John asked me to reach out to a handful of trusted people — and you were at the top of his list.",
    },
    {
        "name": "Kim",
        "email": "crnakim@yahoo.com",
        "opener": "I hope you're doing wonderfully! John asked me to share something new with a few people whose opinions he genuinely values — and you were first on the list.",
    },
    {
        "name": "Bryana",
        "email": "bryanajarboe@gmail.com",
        "opener": "Hope your day is going well! John wanted me to loop you in on something new we've been building — you've been part of this journey and he wanted you to see it early.",
    },
    {
        "name": "Susan",
        "email": "susanna.loucks@gmail.com",
        "opener": "Hope you're doing great! John asked me to share something new — a free cruise discovery tool we built that we think you'll find genuinely useful as you plan your upcoming voyages.",
    },
]

SUBJECT = "A free cruise discovery tool — your honest take welcome"


def build_html(name: str, opener: str) -> str:
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#07076b;font-family:Georgia,serif;">
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#07076b;">
  <tr>
    <td align="center" style="padding:20px 10px;">
      <table width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;width:100%;background:#07076b;">

        <!-- Header -->
        <tr>
          <td style="padding:32px 32px 16px;text-align:center;">
            <div style="font-size:11px;color:#c9a84c;letter-spacing:2.5px;text-transform:uppercase;margin-bottom:10px;">Dreams2Memories Travel</div>
            <div style="font-size:26px;color:#ffffff;font-weight:bold;line-height:1.25;">A Free Cruise Discovery Tool</div>
            <div style="font-size:13px;color:#c0c8e8;margin-top:8px;">Built for you — not to market to you</div>
          </td>
        </tr>

        <!-- Gold rule -->
        <tr><td style="padding:0 32px 24px;">
          <div style="height:2px;background:linear-gradient(to right,#c8930e,#f0c040,#c8930e);border-radius:1px;"></div>
        </td></tr>

        <!-- Body -->
        <tr>
          <td style="padding:0 32px 24px;font-size:15px;color:#e8eaf0;line-height:1.75;">

            <p style="margin:0 0 18px;">Hi {name},</p>

            <p style="margin:0 0 18px;">{opener}</p>

            <p style="margin:0 0 18px;">John tasked Victory (our AI Chief of Staff) and me with building a <strong style="color:#f0c040;">free cruise discovery tool</strong> — a clean, no-pressure way to explore luxury sailings without the usual marketing noise. Over <strong style="color:#f0c040;">15,000 sailings across 28 cruise lines</strong>, all in one searchable place.</p>

            <!-- URL box -->
            <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:22px 0;">
              <tr>
                <td style="background:rgba(255,255,255,0.07);border:1px solid #c9a84c;border-radius:8px;padding:18px 24px;text-align:center;">
                  <div style="font-size:12px;color:#c9a84c;margin-bottom:6px;letter-spacing:1px;">TAKE IT FOR A SPIN</div>
                  <a href="https://d2mluxury.quest/cruises" style="font-size:22px;font-weight:bold;color:#f0c040;text-decoration:none;letter-spacing:0.5px;">d2mluxury.quest/cruises</a>
                </td>
              </tr>
            </table>

            <!-- Screenshot -->
            <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:0 0 22px;">
              <tr>
                <td style="border-radius:6px;overflow:hidden;border:1px solid rgba(201,168,76,0.4);">
                  <a href="https://d2mluxury.quest/cruises">
                    <img src="{SCREENSHOT_URL}" alt="D2M Cruise Discovery Tool" width="536" style="width:100%;display:block;border-radius:5px;">
                  </a>
                </td>
              </tr>
            </table>

            <p style="margin:0 0 12px;color:#f0c040;font-weight:bold;">A few things worth exploring:</p>
            <ul style="margin:0 0 20px;padding-left:22px;color:#e8eaf0;">
              <li style="margin-bottom:9px;">Search by destination, ship name, or departure port</li>
              <li style="margin-bottom:9px;">Filter to your favorite cruise line — Regent, Silversea, Crystal, Viking, and more</li>
              <li style="margin-bottom:9px;">Compare up to 8 sailings side by side in the tray at the bottom</li>
              <li style="margin-bottom:9px;">Each line card shows upcoming departures with direct links to the cruise line's booking site</li>
            </ul>

            <!-- Pricing note -->
            <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:0 0 20px;">
              <tr>
                <td style="background:rgba(240,192,64,0.09);border-left:3px solid #f0c040;border-radius:4px;padding:14px 18px;font-size:14px;color:#e8eaf0;line-height:1.65;">
                  <strong style="color:#f0c040;">Quick note on pricing:</strong> Crystal Cruises fares are live today. We're actively adding Regent, Silversea, Atlas, and Explora — pricing will fill in steadily. The infrastructure is built; the data is flowing.
                </td>
              </tr>
            </table>

            <p style="margin:0 0 18px;">The goal is simple: <strong style="color:#f0c040;">this tool is always slanted toward your benefit, never toward marketing.</strong> No sign-up. No sales pitch. Just a genuinely useful resource for when you're dreaming about your next voyage — or actively planning one.</p>

            <p style="margin:0 0 18px;">Your honest feedback is genuinely welcomed — what works, what's confusing, what's missing. You've been part of this journey, and your perspective is exactly what shapes what we build next.</p>

            <p style="margin:0 0 4px;">Thank you — for your time, your trust, and for being part of what we're building here.</p>

          </td>
        </tr>

        <!-- Rule -->
        <tr><td style="padding:0 32px 20px;">
          <div style="height:1px;background:rgba(201,168,76,0.4);"></div>
        </td></tr>

        <!-- Dani sig -->
        <tr><td style="padding:0 32px 14px;">
          {DANI_SIG}
        </td></tr>

        <!-- Hale mark -->
        <tr><td style="padding:0 32px 14px;font-size:13px;color:#c0c8e8;">
          <span style="font-size:17px;">⚡</span>&nbsp; Victory Hale &middot; Chief of Staff, Thunderbird Wing &middot; Dreams2Memories Travel
        </td></tr>

        <!-- Rule -->
        <tr><td style="padding:0 32px 18px;">
          <div style="height:1px;background:rgba(201,168,76,0.4);"></div>
        </td></tr>

        <!-- Commander sig -->
        <tr><td style="padding:0 32px 28px;">
          {CMD_SIG}
        </td></tr>

      </table>
    </td>
  </tr>
</table>
</body>
</html>"""


def get_service():
    creds = Credentials.from_authorized_user_file(str(TOKEN_PATH))
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def get_or_create_label(service, label_name):
    labels = service.users().labels().list(userId="me").execute().get("labels", [])
    for lbl in labels:
        if lbl["name"] == label_name:
            return lbl["id"]
    new = service.users().labels().create(
        userId="me",
        body={"name": label_name, "labelListVisibility": "labelShow", "messageListVisibility": "show"}
    ).execute()
    return new["id"]


def create_draft(service, to_email: str, subject: str, html_body: str, label_id: str):
    msg = MIMEMultipart("alternative")
    msg["To"] = to_email
    msg["From"] = "johnloucks3@gmail.com"
    msg["Subject"] = subject
    msg.attach(MIMEText("Please view this email in an HTML-capable client.", "plain"))
    msg.attach(MIMEText(html_body, "html"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    draft = service.users().drafts().create(
        userId="me",
        body={"message": {"raw": raw}}
    ).execute()
    # Apply label to the underlying message
    msg_id = draft["message"]["id"]
    service.users().messages().modify(
        userId="me",
        id=msg_id,
        body={"addLabelIds": [label_id]}
    ).execute()
    return draft["id"]


def main():
    svc = get_service()
    label_id = get_or_create_label(svc, "THUNDERBIRD-Commander-Review")
    print(f"Label ID: {label_id}")

    for r in RECIPIENTS:
        html = build_html(r["name"], r["opener"])
        draft_id = create_draft(svc, r["email"], SUBJECT, html, label_id)
        print(f"✅ Draft staged for {r['name']} ({r['email']}) → draft ID: {draft_id}")

    print(f"\nDone. 4 drafts in johnloucks3 · label: THUNDERBIRD-Commander-Review")


if __name__ == "__main__":
    main()
