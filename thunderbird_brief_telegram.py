"""
D2M Morning Brief → Telegram
Lightweight daily push to Commander at 07:05 MDT.
Pulls FPD alerts, departure countdown, CC flags from dossier frontmatter.
Complements thunderbird_morning_briefing.py (email) — this one hits Telegram.
"""
import re
import os
import json
import urllib.request
from pathlib import Path
from datetime import date

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
    urllib.request.urlopen(req, timeout=15)


def fmt_amount(val) -> str:
    try:
        return f"${int(val):,}"
    except (ValueError, TypeError):
        return f"${val}" if val else "?"


def main():
    today = date.today()
    day_label = today.strftime("%a %d %b").upper()

    active, fpd_alerts, departures, cc_flags = [], [], [], []

    for f in sorted(DOSSIER_DIR.glob("*.md")):
        if f.name == "CLAUDE.md":
            continue
        fm = parse_frontmatter(f)
        if fm.get("status") != "active":
            continue
        active.append(fm)
        client = fm.get("full_name") or fm.get("client", f.stem)
        ship = fm.get("ship", "")

        # FPD
        fpd_raw = fm.get("fpd", "")
        if fpd_raw:
            try:
                fpd = date.fromisoformat(fpd_raw)
                days = (fpd - today).days
                amt = fmt_amount(fm.get("fpd_amount"))
                if days < 0:
                    icon = "🔴 OVERDUE"
                elif days == 0:
                    icon = "🚨 DUE TODAY"
                elif days <= 3:
                    icon = "🚨 CRITICAL"
                elif days <= 7:
                    icon = "🔴 URGENT"
                elif days <= 14:
                    icon = "🟡 14-DAY"
                elif days <= 30:
                    icon = "🟡 30-DAY"
                else:
                    icon = None
                if icon:
                    cc_note = " ⚠️ NO CC" if fm.get("cc_on_file", "").lower() == "false" else ""
                    day_str = "TODAY" if days == 0 else (f"{days}d" if days > 0 else f"OVR {abs(days)}d")
                    fpd_alerts.append((days, icon, client, ship, fpd, amt, cc_note))
            except ValueError:
                pass

        # CC flag (regardless of FPD window)
        if fm.get("cc_on_file", "").lower() == "false":
            fpd_raw2 = fm.get("fpd", "")
            cc_flags.append((client, ship, fpd_raw2, fmt_amount(fm.get("fpd_amount"))))

        # Departures (next 90 days)
        dep_raw = fm.get("departure", "")
        if dep_raw:
            try:
                dep = date.fromisoformat(dep_raw)
                days_dep = (dep - today).days
                if 0 <= days_dep <= 90:
                    voyage = fm.get("voyage", "")
                    departures.append((days_dep, client, ship, voyage, dep))
            except ValueError:
                pass

    fpd_alerts.sort(key=lambda x: x[0])
    departures.sort(key=lambda x: x[0])

    lines = [f"*🌅 D2M BRIEF — {day_label}*",
             f"_{len(active)} active bookings_\n"]

    # FPD
    if fpd_alerts:
        lines.append("*📋 FPD WATCH*")
        for days, icon, client, ship, fpd, amt, cc_note in fpd_alerts:
            day_str = "TODAY" if days == 0 else ("OVERDUE" if days < 0 else f"{days}d")
            lines.append(f"{icon} *{client}*")
            lines.append(f"  {ship} · {fpd} ({day_str}) · {amt}{cc_note}")
        lines.append("")

    # CC-only warnings not already in FPD window
    fpd_clients = {x[2] for x in fpd_alerts}
    standalone_cc = [(c, s, f, a) for c, s, f, a in cc_flags if c not in fpd_clients]
    if standalone_cc:
        lines.append("*⚠️ CC NOT ON FILE*")
        for client, ship, fpd, amt in standalone_cc:
            lines.append(f"  • {client} | {ship} | FPD {fpd} | {amt}")
        lines.append("")

    # Departures
    if departures:
        lines.append("*✈️ DEPARTURES (90d)*")
        for days_dep, client, ship, voyage, dep in departures:
            if days_dep <= 7:
                icon = "🔴"
            elif days_dep <= 30:
                icon = "🟡"
            else:
                icon = "🟢"
            lines.append(f"  {icon} {days_dep}d — {client} · {ship} {voyage} · {dep}")
        lines.append("")

    if not fpd_alerts and not departures and not standalone_cc:
        lines.append("_All clear. No alerts._\n")

    lines.append("_Thunderbird OS · D2M_")

    msg = "\n".join(lines)
    print(msg)
    send_telegram(msg)
    print(f"[brief] Sent — {len(active)} active, "
          f"{len(fpd_alerts)} FPD alerts, {len(departures)} departures")


if __name__ == "__main__":
    main()
