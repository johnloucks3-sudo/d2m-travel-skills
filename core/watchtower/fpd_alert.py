#!/usr/bin/env python3
"""
FPD Alert — Final Payment Deadline Scanner
Dreams2Memories Travel, LLC

Scans ~/Thunderbird/dossiers/ for payment deadlines within 14 days.
Fires Telegram alert to Commander (C2 bot).

Run: python3 fpd_alert.py
Systemd: thunderbird-fpd-alert.timer (daily 07:03 MDT)
"""

import os
import re
import requests
from datetime import datetime, date, timedelta
from pathlib import Path
from dotenv import load_dotenv

# ── Config ──────────────────────────────────────────────────────────────────
load_dotenv(Path(__file__).parent / ".env")

BOT_TOKEN      = os.getenv("TELEGRAM_C2_BOT_TOKEN")
COMMANDER_ID   = os.getenv("TELEGRAM_COMMANDER_ID")
DOSSIER_DIR    = Path(__file__).parent / "dossiers"
ALERT_DAYS     = 14   # warn if due within N days
URGENT_DAYS    = 7    # 🔴 if due within N days

# ── Date parsing ─────────────────────────────────────────────────────────────
# Patterns to match: APR 1, Mar 31, April 1, 2026, FPD: Apr 1
DATE_PATTERNS = [
    r'(?:FPD|Final\s+Payment|final\s+payment|FINAL\s+PAYMENT)\s*[:\-–]?\s*([A-Za-z]+ \d{1,2}(?:,\s*\d{4})?)',
    r'(?:FPD|Final\s+Payment|final\s+payment|FINAL\s+PAYMENT)\s*[:\-–]?\s*(\w+ \d{1,2})',
    r'\*\*FPD[:\s]+([A-Z]{3}\s+\d{1,2}(?:,\s*\d{4})?)\*\*',
    r'FPD\s+([A-Z]{3}\s+\d{1,2})',
    r'APR\s+(\d{1,2})',          # catches "APR 1"
    r'MAR\s+(\d{1,2})',          # catches "MAR 31"
]

MONTHS = {
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
    'january': 1, 'february': 2, 'march': 3, 'april': 4, 'june': 6,
    'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12,
}

def parse_date(text: str, ref_year: int) -> date | None:
    """Parse a date string like 'Apr 1', 'APR 1, 2026', 'March 31' into a date."""
    text = text.strip()
    # Try full: "Apr 1, 2026" or "April 1, 2026"
    m = re.match(r'([A-Za-z]+)\s+(\d{1,2}),?\s*(\d{4})', text)
    if m:
        mon = MONTHS.get(m.group(1).lower())
        if mon:
            try:
                return date(int(m.group(3)), mon, int(m.group(2)))
            except ValueError:
                pass
    # Try short: "Apr 1" or "APR 1"
    m = re.match(r'([A-Za-z]+)\s+(\d{1,2})', text)
    if m:
        mon = MONTHS.get(m.group(1).lower())
        if mon:
            try:
                d = date(ref_year, mon, int(m.group(2)))
                # If date already passed this year, try next year
                if d < date.today() - timedelta(days=1):
                    d = date(ref_year + 1, mon, int(m.group(2)))
                return d
            except ValueError:
                pass
    return None


def extract_amount(text: str) -> str:
    """Extract first dollar amount near the match."""
    m = re.search(r'\$[\d,]+', text)
    return m.group(0) if m else "amt TBD"


def scan_dossiers() -> list[dict]:
    """Return list of upcoming payment events sorted by date."""
    today = date.today()
    cutoff = today + timedelta(days=ALERT_DAYS)
    ref_year = today.year

    hits: list[dict] = []
    seen: set[tuple] = set()

    for md_file in DOSSIER_DIR.glob("*.md"):
        try:
            text = md_file.read_text(encoding="utf-8")
        except Exception:
            continue

        lines = text.splitlines()
        for i, line in enumerate(lines):
            # Look for lines mentioning FPD / Final Payment
            if not re.search(r'FPD|[Ff]inal\s+[Pp]ayment', line):
                continue

            # Try to extract a date from this line (and 1 line above/below for context)
            context = "\n".join(lines[max(0, i-1):i+2])

            found_date = None
            # Try each pattern
            for pat in DATE_PATTERNS:
                for m in re.finditer(pat, context, re.IGNORECASE):
                    candidate = parse_date(m.group(1) if m.lastindex >= 1 else m.group(0), ref_year)
                    if candidate and today <= candidate <= cutoff:
                        found_date = candidate
                        break
                if found_date:
                    break

            if not found_date:
                continue

            # Build a label from filename + line snippet
            label = md_file.stem.replace('_', ' ')
            amount = extract_amount(context)
            days_out = (found_date - today).days

            key = (found_date, label)
            if key in seen:
                continue
            seen.add(key)

            hits.append({
                "date":     found_date,
                "days_out": days_out,
                "label":    label,
                "amount":   amount,
                "file":     md_file.name,
                "snippet":  line.strip()[:120],
            })

    hits.sort(key=lambda x: x["date"])
    return hits


def build_message(hits: list[dict]) -> str:
    today_str = datetime.now().strftime("%d %b %Y %H:%M MDT")
    if not hits:
        return (
            f"✅ *FPD SCAN CLEAR*\n"
            f"No payment deadlines within {ALERT_DAYS} days.\n"
            f"_{today_str}_"
        )

    lines = [f"⚠️ *D2M PAYMENT ALERT — {today_str}*\n"]
    for h in hits:
        emoji = "🔴" if h["days_out"] <= URGENT_DAYS else "🟡"
        due_str = h["date"].strftime("%a %d %b")
        lines.append(
            f"{emoji} *{h['label']}*\n"
            f"   Due: {due_str} ({h['days_out']}d) · {h['amount']}\n"
            f"   _{h['snippet']}_\n"
        )

    lines.append(f"\n_{len(hits)} deadline(s) flagged — review dossiers_")
    return "\n".join(lines)


def send_telegram(message: str) -> bool:
    if not BOT_TOKEN or not COMMANDER_ID:
        print("❌ Missing TELEGRAM_C2_BOT_TOKEN or TELEGRAM_COMMANDER_ID in .env")
        return False
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id":    COMMANDER_ID,
        "text":       message,
        "parse_mode": "Markdown",
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()
        print(f"✅ Telegram alert sent ({len(message)} chars)")
        return True
    except Exception as e:
        print(f"❌ Telegram send failed: {e}")
        return False


def main():
    print(f"[FPD Alert] Scanning {DOSSIER_DIR} ...")
    hits = scan_dossiers()
    print(f"[FPD Alert] Found {len(hits)} deadline(s) within {ALERT_DAYS} days")
    msg = build_message(hits)
    print(msg)
    send_telegram(msg)


if __name__ == "__main__":
    main()
