"""
FPD Alert — Final Payment Deadline monitor
Runs daily via systemd timer. Sends Telegram alert for any active
booking with FPD within 14 days.
"""
import re
import os
import urllib.request
import urllib.parse
import json
from pathlib import Path
from datetime import date, timedelta

DOSSIER_DIR = Path(__file__).parent / "dossiers"
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "***REMOVED-SECRET***")
COMMANDER_ID = os.environ.get("TELEGRAM_COMMANDER_ID", "7554895206")


def parse_frontmatter(path: Path) -> dict:
    txt = path.read_text()
    m = re.match(r"^---\n(.*?)\n---", txt, re.DOTALL)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip().strip('"')
    return fm


def send_telegram(msg: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = json.dumps({
        "chat_id": COMMANDER_ID,
        "text": msg,
        "parse_mode": "Markdown"
    }).encode()
    req = urllib.request.Request(url, data=data,
                                  headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=10)


def main():
    today = date.today()
    alerts = []

    for f in sorted(DOSSIER_DIR.glob("*.md")):
        fm = parse_frontmatter(f)
        if fm.get("status") != "active":
            continue
        fpd_raw = fm.get("fpd", "")
        if not fpd_raw:
            continue
        try:
            fpd = date.fromisoformat(fpd_raw)
        except ValueError:
            continue

        days_out = (fpd - today).days
        if days_out < 0:
            flag = "🔴 OVERDUE"
        elif days_out == 0:
            flag = "🚨 DUE TODAY"
        elif days_out <= 3:
            flag = "🚨 CRITICAL"
        elif days_out <= 7:
            flag = "🔴 URGENT"
        elif days_out <= 14:
            flag = "🟡 WARNING"
        else:
            continue

        amount = fm.get("fpd_amount", "?")
        client = fm.get("full_name") or fm.get("client", f.stem)
        ship = fm.get("ship", "")
        alerts.append((days_out, flag, client, ship, fpd, amount))

    if not alerts:
        print("No FPD alerts today.")
        return

    alerts.sort(key=lambda x: x[0])
    lines = ["*🗓 D2M FPD ALERT*\n"]
    for days_out, flag, client, ship, fpd, amount in alerts:
        day_str = f"{days_out}d" if days_out > 0 else "TODAY"
        lines.append(f"{flag} *{client}*")
        try:
            amt_fmt = f"${int(amount):,}"
        except (ValueError, TypeError):
            amt_fmt = f"${amount}"
        lines.append(f"  {ship} | FPD: {fpd} ({day_str}) | {amt_fmt}")
        lines.append("")

    msg = "\n".join(lines)
    print(msg)
    send_telegram(msg)
    print(f"Sent {len(alerts)} alert(s) to Telegram.")


if __name__ == "__main__":
    main()
