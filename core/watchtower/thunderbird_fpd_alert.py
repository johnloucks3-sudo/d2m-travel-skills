"""
FPD Alert — Final Payment Deadline monitor
Runs daily via systemd timer. Sends Telegram alert for any active
booking with FPD within 14 days.
"""
import re
import os
import sys
import argparse
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


# Paid-skip vocabulary (Gap 3 hardening 2026-06-11, Sterling/A7).
# Dossier payment marking is INCONSISTENT across the corpus — so paid-skip uses
# TWO independent signals (this keyword set OR balance_due==0). Deliberately
# STRICT: a "paid" signal must be unambiguous. "confirmed" / "deposit_only" /
# "balance_due" are NOT paid — they mean money is still owed and MUST alert.
# Widening this set to suppress an ambiguous status is exactly how a real FPD
# goes silent. Add a value here only when it provably means paid-in-full.
PAID_STATUSES = {"paid", "paid_in_full", "paidinfull", "complete", "completed", "settled"}


def main(today: date = None):
    if today is None:
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
        # Signal 1 — explicit paid status keyword (strict set, see PAID_STATUSES).
        # Normalize separators so "paid in full" / "paid-in-full" all match.
        pay = re.sub(r"[\s\-]+", "_", fm.get("payment_status", "").lower().strip())
        if pay in PAID_STATUSES:
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
    # Strip Telegram markdown for email plain-text
    email_body = msg.replace("*", "").replace("`", "")
    print(msg)
    if _DRY_RUN:
        print(f"[DRY RUN] Would have sent {len(alerts)} alert(s) to Telegram — suppressed.")
        return
    send_telegram(msg)
    print(f"Sent {len(alerts)} alert(s) to Telegram.")
    # Also email to johnloucks3 inbox (SO 27 MAR 2026 — internal reports are full sends)
    try:
        import sys as _sys
        _sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
        from core.email.thunderbird_gmail import gmail_send_from_wing
        from datetime import datetime as _dt
        gmail_send_from_wing(
            to="johnloucks3@gmail.com",
            subject=f"⚠️ D2M FPD ALERT // {_dt.now().strftime('%b %-d')} — {len(alerts)} ACTIVE",
            body=email_body,
            persona_id="COS",
        )
        print(f"Email sent to johnloucks3.")
    except Exception as _e:
        print(f"Email send failed (non-fatal): {_e}")


# Module-level flag set by CLI; default False keeps the daily timer (argless) live.
_DRY_RUN = False


if __name__ == "__main__":
    # The daily systemd timer calls this script with NO args → date.today(), live send.
    # --today and --dry-run exist for testability/verification ONLY (Sterling 2026-06-11):
    # prove a future FPD is caught by simulating fpd-minus-N days without paging Commander.
    parser = argparse.ArgumentParser(description="FPD Alert — Final Payment Deadline monitor")
    parser.add_argument("--today", help="Override 'today' as YYYY-MM-DD (verification only)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Compute + print alerts but DO NOT send to Telegram")
    args = parser.parse_args()
    _DRY_RUN = args.dry_run
    override = date.fromisoformat(args.today) if args.today else None
    main(today=override)
