#!/usr/bin/env python3
"""
M-086 — Dossier Nightly Validation Sweep (Phase 1)
Dreams2Memories Travel, LLC

Runs every night at 0200 MT via systemd timer.
Reads dossier cache → validates FPD + departure dates → alerts Hale.

Alert tiers:
  RED   → FPD overdue (date passed, amount present) → immediate Telegram page
  YELLOW→ FPD due within 30 days, or departure within 45 days → morning brief queue

Output:
  logs/dossier_sweep_results.json  — picked up by morning brief generator
  logs/dossier_sweep.log           — persistent audit trail
"""

import json
import logging
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

THUNDERBIRD = Path("/home/john/Thunderbird")
sys.path.insert(0, str(THUNDERBIRD))

from dotenv import load_dotenv
load_dotenv(THUNDERBIRD / ".env")
load_dotenv(THUNDERBIRD / ".env.telegram")

from core.dossier.dossier_cache import get_cache, DossierRecord

LOG_FILE     = THUNDERBIRD / "logs" / "dossier_sweep.log"
RESULTS_FILE = THUNDERBIRD / "logs" / "dossier_sweep_results.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("dossier_sweep")

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_C2_BOT_TOKEN", "")
TELEGRAM_COMMANDER = os.environ.get("TELEGRAM_COMMANDER_ID", "")

FPD_RED_WINDOW    = 0    # FPD date has passed — RED
FPD_YELLOW_WINDOW = 30   # FPD within 30 days — YELLOW
DEP_YELLOW_WINDOW = 45   # Departure within 45 days — YELLOW


def _send_telegram(text: str) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_COMMANDER:
        logger.warning("Telegram not configured — message not sent")
        return
    try:
        import requests
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": TELEGRAM_COMMANDER,
                "text": text[:3900],
                "parse_mode": "HTML",
            },
            timeout=10,
        )
        logger.info("Telegram page sent")
    except Exception as e:
        logger.error("Telegram send failed: %s", e)


def _classify(record: DossierRecord, today: date) -> tuple[str, list[str]]:
    """Return (tier, reasons) where tier is RED, YELLOW, or GREEN."""
    reasons = []
    tier = "GREEN"

    if record.fpd:
        days_until_fpd = (record.fpd - today).days
        if days_until_fpd < 0 and record.fpd_amount:
            # FPD is in the past and there's a balance — RED
            reasons.append(
                f"FPD OVERDUE {abs(days_until_fpd)}d — "
                f"${record.fpd_amount:,.0f} due {record.fpd.isoformat()}"
            )
            tier = "RED"
        elif 0 <= days_until_fpd <= FPD_YELLOW_WINDOW:
            reasons.append(
                f"FPD in {days_until_fpd}d — "
                f"${record.fpd_amount:,.0f} due {record.fpd.isoformat()}"
                if record.fpd_amount
                else f"FPD in {days_until_fpd}d — amount unknown"
            )
            if tier == "GREEN":
                tier = "YELLOW"

    if record.departure:
        days_until_dep = (record.departure - today).days
        if 0 <= days_until_dep <= DEP_YELLOW_WINDOW:
            reasons.append(f"Departure in {days_until_dep}d — {record.departure.isoformat()}")
            if tier == "GREEN":
                tier = "YELLOW"

    return tier, reasons


def run_validation_sweep(today: date = None) -> dict:
    """
    Run the full dossier validation sweep.
    Returns a results dict (also written to RESULTS_FILE).
    """
    today = today or date.today()
    logger.info("Dossier validation sweep starting — %s", today.isoformat())

    cache = get_cache()
    records = cache.get_all()
    logger.info("Loaded %d dossier records from cache", len(records))

    reds    = []
    yellows = []
    greens  = []

    for r in records:
        tier, reasons = _classify(r, today)
        entry = {
            "filename":     r.filename,
            "client_label": r.client_label,
            "fpd":          r.fpd.isoformat() if r.fpd else None,
            "fpd_amount":   r.fpd_amount,
            "departure":    r.departure.isoformat() if r.departure else None,
            "reasons":      reasons,
            "tier":         tier,
        }
        if tier == "RED":
            reds.append(entry)
        elif tier == "YELLOW":
            yellows.append(entry)
        else:
            greens.append(entry)

    results = {
        "swept_at":  datetime.now().isoformat(),
        "today":     today.isoformat(),
        "total":     len(records),
        "red":       reds,
        "yellow":    yellows,
        "green_count": len(greens),
    }

    # Persist results for morning brief pickup
    RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_FILE.write_text(json.dumps(results, indent=2))
    logger.info(
        "Sweep complete — RED: %d, YELLOW: %d, GREEN: %d",
        len(reds), len(yellows), len(greens),
    )

    # Immediate Telegram page for RED items
    if reds:
        lines = ["<b>🔴 DOSSIER SWEEP — RED ALERTS</b>", f"Date: {today.isoformat()}", ""]
        for item in reds:
            lines.append(f"<b>{item['client_label']}</b>")
            for r in item["reasons"]:
                lines.append(f"  • {r}")
            lines.append("")
        lines.append(f"Full results: {RESULTS_FILE}")
        _send_telegram("\n".join(lines))
    else:
        logger.info("No RED items — no Telegram page sent")

    return results


if __name__ == "__main__":
    results = run_validation_sweep()
    print(f"\nSweep complete:")
    print(f"  RED:    {len(results['red'])}")
    print(f"  YELLOW: {len(results['yellow'])}")
    print(f"  GREEN:  {results['green_count']}")
    if results["red"]:
        print("\nRED items:")
        for item in results["red"]:
            print(f"  {item['client_label']}: {', '.join(item['reasons'])}")
    if results["yellow"]:
        print("\nYELLOW items:")
        for item in results["yellow"]:
            print(f"  {item['client_label']}: {', '.join(item['reasons'])}")
