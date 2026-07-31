#!/usr/bin/env python3
"""
Cruise Quote Scanner — watches johnloucks3 for quote requests from cruise tool recipients.

Detection methods (both checked every run):
  1. Reply-To tag: emails addressed to johnloucks3+cruise-quote@gmail.com
  2. Thread ID match: replies in threads started by our 6 sent message IDs

On detection:
  - Sends 🚨 Telegram alert to Commander (via Dani bot)
  - Looks up sailing in cruises.db
  - Stages a pre-built quote draft in johnloucks3

Run: python3 scripts/cruise_quote_scanner.py
Timer: cruise-quote-scanner.timer (every 15 min)
"""

import json, os, re, sqlite3, base64, sys
import socket
from pathlib import Path
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import urllib.request
import httplib2

try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
except ImportError:
    print("ERROR: pip install google-auth-httplib2 google-api-python-client"); sys.exit(1)

ROOT        = Path("/home/john/Thunderbird")
TOKEN_PATH  = ROOT / "creds/johnloucks3_token.json"
THREADS_F   = ROOT / "data/cruise_quote_threads.json"
SEEN_F      = ROOT / "data/cruise_quote_seen.json"
DB_PATH     = ROOT / "output/cruises.db"
DANI_SIG    = (ROOT / "storage/signatures/dani_sig.html").read_text()
CMD_SIG     = (ROOT / "storage/signatures/commander_d2m_sig.html").read_text()

QUOTE_TAG   = "johnloucks3+cruise-quote@gmail.com"
FROM_ADDR   = "johnloucks3@gmail.com"

# ── Telegram ──────────────────────────────────────────────────────────────────
def _load_env():
    env_path = Path.home() / ".telegram_gw_live.env"
    env = {}
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"')
    return env

def tg_alert(text: str):
    env = _load_env()
    tok = env.get("TELEGRAM_DANI_TOKEN", "")
    if not tok:
        print("[TG] No Dani token found"); return
    cid = 7554895206
    payload = json.dumps({"chat_id": cid, "text": text, "parse_mode": "HTML"}).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{tok}/sendMessage",
        data=payload, headers={"Content-Type": "application/json"}
    )
    try:
        r = urllib.request.urlopen(req, timeout=8)
        print("[TG] Alert sent:", json.loads(r.read()).get("ok"))
    except Exception as e:
        print(f"[TG] Error: {e}")

# ── Gmail ─────────────────────────────────────────────────────────────────────
def get_service():
    creds = Credentials.from_authorized_user_file(str(TOKEN_PATH))
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("gmail", "v1", credentials=creds, cache_discovery=False)

def get_message_body(service, msg_id: str) -> str:
    msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
    payload = msg.get("payload", {})
    def extract(p):
        if p.get("mimeType") == "text/plain":
            data = p.get("body", {}).get("data", "")
            return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="ignore") if data else ""
        for part in p.get("parts", []):
            t = extract(part)
            if t: return t
        return ""
    return extract(payload)

def get_header(msg, name: str) -> str:
    for h in msg.get("payload", {}).get("headers", []):
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""

# ── Quote intent detection ────────────────────────────────────────────────────
# Known Crystal ships — exclude contamination from other lines in DB
CRYSTAL_SHIPS = {"Crystal Serenity", "Crystal Symphony", "Crystal Grandeur"}

QUOTE_KEYWORDS = [
    r"\bquote\b", r"\bpricing\b", r"\bhow much\b", r"\bprice\b",
    r"\bcost\b", r"\binterested in\b", r"\btell me more\b",
    r"\bsailing\b", r"\bbook\b", r"\bavailability\b", r"\brates?\b",
    r"\bfares?\b", r"\bwhat.{0,15}cost\b", r"\bmore info\b",
]

def is_quote_request(body: str) -> bool:
    body_lower = body.lower()
    return any(re.search(kw, body_lower) for kw in QUOTE_KEYWORDS)

# ── Sailing extraction ────────────────────────────────────────────────────────
LINE_ALIASES = {
    "regent": "Regent Seven Seas Cruises",
    "silversea": "Silversea Cruises",
    "crystal": "Crystal Cruises",
    "viking": "Viking",
    "atlas": "Atlas Ocean Voyages",
    "explora": "Explora Journeys",
    "oceania": "Oceania Cruises",
    "seabourn": "Seabourn",
    "cunard": "Cunard",
    "ponant": "PONANT",
}

SHIP_KEYWORDS = {
    "serenity":  "Crystal Serenity",
    "symphony":  "Crystal Symphony",
    "grandeur":  "Crystal Grandeur",
    "silver muse": "Silver Muse",
    "silver nova": "Silver Nova",
    "silver wind": "Silver Wind",
    "silver dawn": "Silver Dawn",
    "silver whisper": "Silver Whisper",
    "seven seas grandeur": "Seven Seas Grandeur",
    "seven seas splendor": "Seven Seas Splendor",
    "seven seas explorer": "Seven Seas Explorer",
    "seven seas navigator": "Seven Seas Navigator",
    "seven seas mariner": "Seven Seas Mariner",
    "seven seas voyager": "Seven Seas Voyager",
    "viking mars": "Viking Mars",
    "viking venus": "Viking Venus",
    "viking jupiter": "Viking Jupiter",
}

def extract_sailing_hints(body: str) -> dict:
    hints = {"line": None, "destination": None, "ship": None, "raw": body[:500]}
    b = body.lower()
    for alias, canonical in LINE_ALIASES.items():
        if alias in b:
            hints["line"] = canonical
            break
    for kw, ship_name in SHIP_KEYWORDS.items():
        if kw in b:
            hints["ship"] = ship_name
            break
    months = ["january","february","march","april","may","june","july",
              "august","september","october","november","december"]
    for m in months:
        if m in b:
            hints["destination"] = m.capitalize()
            break
    return hints

# ── DB lookup ─────────────────────────────────────────────────────────────────
def lookup_sailings(hints: dict, limit: int = 5) -> list:
    if not DB_PATH.exists():
        return []
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    wheres, params = ["departure >= date('now')"], []
    if hints.get("line"):
        wheres.append("line = ?"); params.append(hints["line"])
        # Exclude known contamination for Crystal
        if hints["line"] == "Crystal Cruises":
            placeholders = ",".join("?" * len(CRYSTAL_SHIPS))
            wheres.append(f"ship IN ({placeholders})")
            params.extend(sorted(CRYSTAL_SHIPS))
    if hints.get("ship"):
        wheres.append("ship LIKE ?"); params.append(f"%{hints['ship']}%")
    # Prefer priced sailings, then by departure
    rows = conn.execute(
        f"SELECT line, ship, departure, nights, from_port, price_ind, price_ts FROM cruises "
        f"WHERE {' AND '.join(wheres)} "
        f"ORDER BY (price_ind IS NOT NULL) DESC, departure ASC LIMIT ?",
        params + [limit]
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ── Quote draft builder ───────────────────────────────────────────────────────
def build_quote_html(sender_name: str, sender_email: str, body_snippet: str,
                     sailings: list, hints: dict) -> str:
    now_str = datetime.now(timezone.utc).strftime("%B %d, %Y %H:%M UTC")

    if sailings:
        rows_html = ""
        for s in sailings:
            price_str = f"${s['price_ind']:,.0f} pp" if s.get("price_ind") else "Quote on request"
            price_color = "#f0c040" if s.get("price_ind") else "#999"
            ts_str = s['price_ts'][:10] if s.get('price_ts') else ""
            nights_str = f"{s['nights']}n" if s.get("nights") else "—"
            port_str = s.get("from_port") or "—"
            rows_html += f"""
            <tr>
              <td style='padding:10px 14px;border-bottom:1px solid #1a1a6e;color:#e8eaf0;font-size:14px;'>{s['ship']}</td>
              <td style='padding:10px 14px;border-bottom:1px solid #1a1a6e;color:#e8eaf0;font-size:14px;'>{s['departure']}</td>
              <td style='padding:10px 14px;border-bottom:1px solid #1a1a6e;color:#c0c8e8;font-size:14px;'>{nights_str} · {port_str}</td>
              <td style='padding:10px 14px;border-bottom:1px solid #1a1a6e;color:{price_color};font-size:14px;font-weight:bold;'>{price_str}<br><span style='font-size:10px;color:#777;font-weight:normal;'>{ts_str}</span></td>
            </tr>"""
        sailings_block = f"""
        <p style='margin:0 0 12px;color:#f0c040;font-weight:bold;'>Upcoming sailings matching your interest:</p>
        <table width='100%' cellpadding='0' cellspacing='0' border='0' style='margin:0 0 20px;border-collapse:collapse;background:rgba(255,255,255,0.04);border-radius:6px;overflow:hidden;border:1px solid #2a2a7a;'>
          <tr style='background:rgba(201,168,76,0.15);'>
            <th style='padding:10px 14px;text-align:left;color:#c9a84c;font-size:12px;letter-spacing:1px;'>SHIP</th>
            <th style='padding:10px 14px;text-align:left;color:#c9a84c;font-size:12px;letter-spacing:1px;'>DEPARTURE</th>
            <th style='padding:10px 14px;text-align:left;color:#c9a84c;font-size:12px;letter-spacing:1px;'>NIGHTS · PORT</th>
            <th style='padding:10px 14px;text-align:left;color:#c9a84c;font-size:12px;letter-spacing:1px;'>INDICATIVE FARE</th>
          </tr>{rows_html}
        </table>"""
    else:
        sailings_block = "<p style='color:#c0c8e8;font-size:14px;'>No DB match found — pricing being researched manually. Will confirm within 2 business hours.</p>"

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#07076b;font-family:Georgia,serif;">
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#07076b;">
  <tr><td align="center" style="padding:20px 10px;">
    <table width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;width:100%;background:#07076b;">

      <tr><td style="padding:32px 32px 16px;text-align:center;">
        <div style="font-size:11px;color:#c9a84c;letter-spacing:2.5px;text-transform:uppercase;margin-bottom:10px;">Dreams2Memories Travel · Cruise Quote</div>
        <div style="font-size:24px;color:#ffffff;font-weight:bold;">Your Cruise Pricing Request</div>
        <div style="font-size:12px;color:#c0c8e8;margin-top:6px;">Responded within 2 business hours · {now_str}</div>
      </td></tr>

      <tr><td style="padding:0 32px 24px;">
        <div style="height:2px;background:linear-gradient(to right,#c8930e,#f0c040,#c8930e);border-radius:1px;"></div>
      </td></tr>

      <tr><td style="padding:0 32px 24px;font-size:15px;color:#e8eaf0;line-height:1.75;">

        <p style="margin:0 0 18px;">Hi {sender_name.split()[0]},</p>
        <p style="margin:0 0 18px;">Thank you for reaching out — I caught your message right away. Here's what I've pulled together on the sailing(s) you're interested in.</p>

        {sailings_block}

        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:0 0 20px;">
          <tr><td style="background:rgba(240,192,64,0.09);border-left:3px solid #f0c040;border-radius:4px;padding:14px 18px;font-size:13px;color:#c0c8e8;line-height:1.65;">
            <strong style="color:#f0c040;">Pricing note:</strong> Fares shown are indicative public prices as of the timestamp above. Actual pricing depends on cabin category, current availability, and promotions — including rates we can access through our host relationships. <strong style="color:#ffffff;">Reply with the sailing that interests you and I'll confirm a live, bookable rate.</strong>
          </td></tr>
        </table>

        <p style="margin:0 0 18px;">Want to dig deeper on any of these — itinerary details, cabin options, what's included? Just say the word. This is exactly what we're here for.</p>
        <p style="margin:0 0 4px;">Looking forward to helping you plan something exceptional.</p>

      </td></tr>

      <tr><td style="padding:0 32px 20px;">
        <div style="height:1px;background:rgba(201,168,76,0.4);"></div>
      </td></tr>
      <tr><td style="padding:0 32px 14px;">{DANI_SIG}</td></tr>
      <tr><td style="padding:0 32px 14px;font-size:13px;color:#c0c8e8;">
        <span style="font-size:17px;">⚡</span>&nbsp; Victory Hale &middot; Chief of Staff, Thunderbird Wing
      </td></tr>
      <tr><td style="padding:0 32px 18px;">
        <div style="height:1px;background:rgba(201,168,76,0.4);"></div>
      </td></tr>
      <tr><td style="padding:0 32px 28px;">{CMD_SIG}</td></tr>

    </table>
  </td></tr>
</table>
</body></html>"""


def stage_quote_draft(service, sender_name, sender_email, reply_to_id, html):
    subject = f"Re: A free cruise discovery tool — your honest take welcome"
    msg = MIMEMultipart("alternative")
    msg["To"]         = sender_email
    msg["From"]       = FROM_ADDR
    msg["Subject"]    = subject
    if reply_to_id:
        msg["In-Reply-To"] = reply_to_id
        msg["References"]  = reply_to_id
    msg.attach(MIMEText("Please view in HTML-capable client.", "plain"))
    msg.attach(MIMEText(html, "html"))
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    # Get or create label
    labels = service.users().labels().list(userId="me").execute().get("labels", [])
    label_id = next((l["id"] for l in labels if l["name"] == "THUNDERBIRD-Commander-Review"), None)
    if not label_id:
        label_id = service.users().labels().create(userId="me", body={
            "name": "THUNDERBIRD-Commander-Review",
            "labelListVisibility": "labelShow",
            "messageListVisibility": "show"
        }).execute()["id"]

    draft = service.users().drafts().create(
        userId="me", body={"message": {"raw": raw}}
    ).execute()
    service.users().messages().modify(
        userId="me", id=draft["message"]["id"],
        body={"addLabelIds": [label_id]}
    ).execute()
    return draft["id"]


# ── Seen state ────────────────────────────────────────────────────────────────
def load_seen() -> set:
    if SEEN_F.exists():
        return set(json.loads(SEEN_F.read_text()).get("seen_ids", []))
    return set()

def save_seen(seen: set):
    SEEN_F.write_text(json.dumps({"seen_ids": list(seen)}, indent=2))


# ── Main scan ─────────────────────────────────────────────────────────────────
def scan():
    threads_data = json.loads(THREADS_F.read_text())
    sent_ids     = {s["msg_id"] for s in threads_data["sent"]}
    sent_by_email = {s["email"].lower(): s["name"] for s in threads_data["sent"]}
    seen         = load_seen()
    svc          = get_service()
    found        = []

    # Method 1: tagged Reply-To address
    tag_query = f'to:{QUOTE_TAG} newer_than:7d'
    tag_results = svc.users().messages().list(userId="me", q=tag_query).execute()
    for m in tag_results.get("messages", []):
        mid = m["id"]
        if mid in seen: continue
        msg = svc.users().messages().get(userId="me", id=mid, format="full").execute()
        from_hdr = get_header(msg, "from")
        email_match = re.search(r'[\w.+-]+@[\w.-]+', from_hdr)
        sender_email = email_match.group(0).lower() if email_match else ""
        sender_name  = sent_by_email.get(sender_email, from_hdr)
        body         = get_message_body(svc, mid)
        found.append({"id": mid, "name": sender_name, "email": sender_email,
                      "body": body, "method": "reply-to-tag", "msg_ref": mid})

    # Method 2: thread ID matching for already-sent 6 messages
    for sent in threads_data["sent"]:
        orig_msg = svc.users().messages().get(
            userId="me", id=sent["msg_id"], format="minimal"
        ).execute()
        thread_id = orig_msg.get("threadId")
        if not thread_id: continue
        thread = svc.users().threads().get(userId="me", id=thread_id, format="full").execute()
        msgs   = thread.get("messages", [])
        for msg in msgs:
            mid = msg["id"]
            if mid == sent["msg_id"] or mid in seen: continue
            from_hdr = get_header(msg, "from")
            # Skip our own messages
            if "johnloucks3" in from_hdr or "d2mluxury" in from_hdr: continue
            body = get_message_body(svc, mid)
            if is_quote_request(body) or True:  # flag ALL replies from the 6
                found.append({"id": mid, "name": sent["name"],
                              "email": sent["email"], "body": body,
                              "method": "thread-match", "msg_ref": sent["msg_id"]})

    # Deduplicate by message ID
    seen_this_run = set()
    unique_found  = []
    for f in found:
        if f["id"] not in seen_this_run:
            seen_this_run.add(f["id"])
            unique_found.append(f)

    if not unique_found:
        print(f"[{datetime.now().strftime('%H:%M')}] No new quote requests detected.")
        return

    for req in unique_found:
        print(f"\n🔔 Reply detected from {req['name']} ({req['email']}) via {req['method']}")
        hints    = extract_sailing_hints(req["body"])
        sailings = lookup_sailings(hints)
        html     = build_quote_html(req["name"], req["email"], req["body"][:300],
                                    sailings, hints)
        draft_id = stage_quote_draft(svc, req["name"], req["email"],
                                     req.get("msg_ref"), html)
        seen.add(req["id"])

        # 🚨 Telegram alert
        snippet = req["body"][:200].replace("<","&lt;").replace(">","&gt;").strip()
        sailing_hint = hints.get("line") or "unspecified line"
        tg_alert(
            f"🚨🚨 <b>CRUISE QUOTE REQUEST</b>\n\n"
            f"<b>From:</b> {req['name']} ({req['email']})\n"
            f"<b>Line hint:</b> {sailing_hint}\n"
            f"<b>Detected via:</b> {req['method']}\n\n"
            f"<b>Message snippet:</b>\n<i>{snippet}</i>\n\n"
            f"✅ Quote draft staged in johnloucks3 · THUNDERBIRD-Commander-Review\n"
            f"Draft ID: {draft_id}\n\n"
            f"⏰ <b>SLA: 2 business hours from {datetime.now().strftime('%H:%M MT')}</b>"
        )
        print(f"  ✅ Draft staged: {draft_id} | TG alert sent")

    save_seen(seen)
    print(f"\n[Done] Processed {len(unique_found)} new reply(ies).")


if __name__ == "__main__":
    try:
        scan()
    except (httplib2.error.ServerNotFoundError, socket.gaierror, OSError) as e:
        # Transient network failure — DNS or connection unavailable. Timer retries in 15 min.
        print(f"[WARN] Network unavailable, skipping run: {e}", file=sys.stderr)
        sys.exit(0)
