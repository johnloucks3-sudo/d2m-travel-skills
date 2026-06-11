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

# FIXED 2026-06-11: was Path(__file__).parent / "dossiers" — an EMPTY dir, so the
# scanner logged "No FPD alerts today" every run, BLIND to all 15 FPD dossiers.
# Same disease as the watchdog phantom-list + credential-cookie bugs: a monitor
# reporting comfort because it read the wrong source. Now points at the real dir.
DOSSIER_DIR = Path(__file__).resolve().parent.parent.parent / "dossiers"
BOT_TOKEN = os.environ.get("TELEGRAM_C2_BOT_TOKEN", "***REMOVED-SECRET***")  # D2MC2C_bot — Commander C2 channel
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


_MUTE_FLAG = Path("/home/john/Thunderbird/config/d2mc2c_client_mute")

def send_telegram(msg: str):
    if _MUTE_FLAG.exists():
        return  # client/supplier push muted — SO 2026-05-05
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

    # Empty-source guard: a monitor that reads 0 files must NOT silently report
    # "all clear" — that's how the empty-dir blindness hid for weeks. Loud-fail.
    all_md = sorted(DOSSIER_DIR.glob("*.md"))
    if not all_md:
        send_telegram(f"🔴 FPD SCANNER ANOMALY — DOSSIER_DIR `{DOSSIER_DIR}` has 0 dossiers. "
                      f"Scanner is blind. Check the path before trusting 'no alerts'.")
        print(f"FPD scanner: 0 dossiers at {DOSSIER_DIR} — anomaly alerted, aborting.")
        return

    for f in all_md:
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

        # Paid-skip (2026-06-11): don't false-alert on bookings already paid.
        # Dossier payment marking is inconsistent, so use three signals.
        pay = fm.get("payment_status", "").lower()
        if pay in ("paid", "paid_in_full", "complete", "completed"):
            continue
        bal_raw = str(fm.get("balance_due", "")).replace(",", "").replace('"', "").strip()
        try:
            if bal_raw and float(bal_raw) == 0:
                continue
        except ValueError:
            pass

        days_out = (fpd - today).days
        if days_out < -30:
            continue  # >30d past = resolved/paid (paid-but-unmarked backstop), not a live 14-day reminder
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
