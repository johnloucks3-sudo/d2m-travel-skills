"""
D2M Intel Push → Telegram C2
Runs the full intel crew pipeline (A2 → A1 → COS) and delivers
COS-approved morning brief to Commander via Telegram.

Pipeline:  scrape_all_news_feeds()
        → A2 Dembe (collect + analyze)
        → A1 Radar (audit)
        → COS Hale (quality gate + synthesis)
        → Telegram C2

Fires daily at 06:35 MDT via d2m-intel-telegram.timer.
Also callable: python3 thunderbird_intel_telegram.py [--dry-run]
"""
import json
import os
import sys
import argparse
import urllib.request
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).parent
BOT_TOKEN = os.environ.get("TELEGRAM_C2_BOT_TOKEN",
                            "***REMOVED-SECRET***")
COMMANDER_ID = os.environ.get("TELEGRAM_COMMANDER_ID", "7554895206")
MAX_CHUNK = 3800  # Telegram 4096 limit, with headroom


def send_telegram(msg: str, parse_mode: str = "Markdown"):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = json.dumps({
        "chat_id": COMMANDER_ID,
        "text": msg,
        "parse_mode": parse_mode,
    }).encode()
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}
    )
    urllib.request.urlopen(req, timeout=15)


def chunk_and_send(text: str, header: str = ""):
    """Send long text in Telegram-safe chunks."""
    if header:
        send_telegram(header)
    lines = text.split("\n")
    buf = ""
    for line in lines:
        if len(buf) + len(line) + 1 > MAX_CHUNK:
            if buf.strip():
                send_telegram(buf)
            buf = line + "\n"
        else:
            buf += line + "\n"
    if buf.strip():
        send_telegram(buf)


def run_intel_pipeline(dry_run: bool = False) -> dict:
    """Execute full IntelCrew pipeline and return the package."""
    sys.path.insert(0, str(BASE))
    from thunderbird_intel_crew import IntelCrew
    crew = IntelCrew()
    package = crew.run()
    return package


def format_header(package: dict) -> str:
    ts = datetime.now().strftime("%a %d %b %Y %H:%M MT")
    counts = package.get("raw_item_counts", {})
    total = sum(counts.values()) if counts else "?"
    domains = len(counts) if counts else "?"
    return (
        f"*🔵 D2M MORNING INTEL — {ts}*\n"
        f"_{total} items · {domains} domains · A2→A1→COS pipeline_"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Run pipeline but print instead of sending to Telegram")
    args = parser.parse_args()

    print(f"[intel-push] Starting pipeline — {datetime.now().strftime('%H:%M:%S')}")

    try:
        package = run_intel_pipeline(dry_run=args.dry_run)
    except Exception as e:
        err = f"⚠️ Intel pipeline error: `{e}`"
        print(err)
        if not args.dry_run:
            send_telegram(err)
        return

    cos_review = package.get("cos_review", "")
    if not cos_review:
        msg = "⚠️ Intel crew returned empty COS review — check thunderbird_intel_crew.py logs"
        print(msg)
        if not args.dry_run:
            send_telegram(msg)
        return

    header = format_header(package)
    airline_impacts = package.get("airline_impacts", [])

    if args.dry_run:
        print(header)
        print(cos_review)
        if airline_impacts:
            print(f"\n[AIRLINE IMPACTS: {len(airline_impacts)} items]")
        print("\n[dry-run] Not sent to Telegram.")
        return

    # Push to Telegram C2
    chunk_and_send(cos_review, header=header)

    # Airline client impacts as follow-on alert if critical
    if airline_impacts:
        critical = [x for x in airline_impacts if x.get("severity") in ("CRITICAL", "HIGH")]
        if critical:
            lines = ["*✈️ CLIENT FLIGHT IMPACTS*"]
            for item in critical[:5]:
                lines.append(f"  🔴 *{item.get('client', '?')}* — {item.get('headline', '')[:80]}")
            send_telegram("\n".join(lines))

    print(f"[intel-push] Complete — brief delivered to C2")


if __name__ == "__main__":
    main()
