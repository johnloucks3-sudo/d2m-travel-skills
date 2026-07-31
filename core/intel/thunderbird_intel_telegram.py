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
INTEL_OUTPUT_DIR = Path(__file__).resolve().parent / "output" / "intel_crew"
BOT_TOKEN = os.environ.get("TELEGRAM_D2MC2C_TOKEN") or os.environ.get("TELEGRAM_C2_BOT_TOKEN",
                            "***REMOVED-SECRET***")
COMMANDER_ID = os.environ.get("TELEGRAM_COMMANDER_ID", "7554895206")
MAX_CHUNK = 3800  # Telegram 4096 limit, with headroom
DRIVE_FOLDER_ID = os.environ.get("DRIVE_INTEL_FOLDER_ID", "")


def send_telegram(msg: str, parse_mode: str = "HTML"):
    """Send message to the Commander.

    Routed through the single gate (C2 RECALIBRATION task 8, Commander directive
    2026-07-29). This used to hit the bot API directly — one of the direct senders
    the gate replaced. This module already fires close to the sanctioned 06:30
    window (d2m-intel-telegram.timer, 06:35 MDT), so it queues (urgency="WINDOW")
    rather than breaking through, and lands in the same consolidated brief instead
    of arriving as a near-duplicate second push.
    """
    import logging
    log = logging.getLogger(__name__)
    try:
        from core.comms.commander_channel import notify
        title = msg.splitlines()[0][:80] if msg.strip() else "D2M Intel"
        result = notify("intel", title, msg, urgency="WINDOW", source="thunderbird_intel_telegram")
        if result.get("status") not in ("sent", "queued", "suppressed"):
            log.warning(f"notify() rejected intel push: {result.get('detail')}")
    except Exception as e:
        log.warning(f"notify() send failed: {e}")


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


def upload_to_drive(package: dict, package_path: Path) -> str:
    """Upload intel package to Drive, return webViewLink."""
    try:
        thunderbird_root = Path(__file__).resolve().parent.parent.parent
        sys.path.insert(0, str(thunderbird_root / "scripts"))
        from drive_upload_robust import upload_file
        uploaded = upload_file(
            local_path=str(package_path),
            folder_id=DRIVE_FOLDER_ID or None,
            name=f"intel_package_{datetime.now().strftime('%Y%m%d')}.json",
        )
        return uploaded.get("webViewLink", "")
    except Exception as e:
        print(f"[intel-push] Drive upload failed: {e}")
        return ""


def format_sources_footer(package: dict, drive_link: str = "") -> str:
    """Build a Telegram-formatted sources footer with key links."""
    sources = package.get("sources", [])
    if not sources and not drive_link:
        return ""

    lines = ["\n📎 **SOURCES & REFERENCES**\n"]

    if drive_link:
        lines.append(f"📄 **Full Intel Report:** {drive_link}")
        lines.append("")

    if sources:
        news_count = 0
        adv_count = 0
        for s in sources:
            if s["type"] == "news" and news_count < 8:
                lines.append(f"📰 <a href='{s['url']}'>{s['title'][:80]}</a>")
                news_count += 1
            elif s["type"] == "advisory" and adv_count < 3:
                lines.append(f"⚠️ {s['title']}")
                adv_count += 1

        total_news = sum(1 for s in sources if s["type"] == "news")
        if total_news > 8:
            lines.append(f"   _+ {total_news - 8} more news sources in full report_")

    return "\n".join(lines)


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

    # Upload full report to Drive
    drive_link = ""
    latest_packages = sorted(INTEL_OUTPUT_DIR.glob("intel_package_*.json"))
    if latest_packages:
        drive_link = upload_to_drive(package, latest_packages[-1])

    # Build sources footer
    sources_footer = format_sources_footer(package, drive_link)

    # Push COS review to Telegram C2
    chunk_and_send(cos_review, header=header)

    # Push sources footer if there's content
    if sources_footer:
        send_telegram(sources_footer, parse_mode="HTML")

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
