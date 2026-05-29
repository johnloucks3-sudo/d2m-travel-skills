#!/usr/bin/env python3
"""
Centrav Flight Watch Runner — systemd entry point
Dreams2Memories Travel, LLC

Called by thunderbird-fare-watch.service (daily 08:00 MDT).
Runs price checks for all active flight fare watches via Centrav B2B.

Results written to: OpsCenter/fare_watches/last_check.json
Logs to: OpsCenter/fare_watches/fare_watch.log (via service stdout redirect)
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import requests

# Ensure core/travel modules are importable
_TB = Path(__file__).resolve().parent.parent
_CORE_TRAVEL = _TB / "core" / "travel"
if str(_CORE_TRAVEL) not in sys.path:
    sys.path.insert(0, str(_CORE_TRAVEL))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("fare_watch_centrav")

from thunderbird_centrav_search import run_centrav_flight_watch_cycle  # noqa: E402

ENV_FILE = _TB / ".env"
COMMANDER_ID = 7554895206


def _load_telegram_token() -> str:
    token = os.environ.get("TELEGRAM_D2MC2C_TOKEN", "")
    if not token and ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line.startswith("TELEGRAM_D2MC2C_TOKEN="):
                token = line.split("=", 1)[1].strip().strip('"').strip("'")
    return token


def _tg_send(token: str, text: str) -> bool:
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": COMMANDER_ID, "text": text, "parse_mode": "HTML"},
            timeout=15,
        )
        return resp.ok
    except Exception as exc:
        logger.error("Telegram send failed: %s", exc)
        return False


def _build_alert_message(alerts: list, watches_checked: int) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M MT")
    lines = [
        f"🚨 <b>FARE ALERT — {len(alerts)} triggered</b>",
        f"<i>{now} · {watches_checked} watch(es) checked</i>",
        "",
    ]
    for a in alerts:
        watch_id = a.get("watch_id", "?")
        label = a.get("label", watch_id)
        alert_text = a.get("alert", "")
        price = a.get("price_pp", "?")
        baseline = a.get("baseline_pp", "?")
        change = a.get("change_from_baseline", "?")

        if "DROP" in alert_text.upper():
            icon = "📉"
            action = "<b>ACTION: Consider booking now — price dropped.</b>"
        else:
            icon = "📈"
            action = "<b>ACTION: Inventory tightening — window to book is closing.</b>"

        lines += [
            f"{icon} <b>{label}</b>",
            f"  {alert_text}",
            f"  Current: {price} · Baseline: {baseline} · Change: {change}",
            f"  {action}",
            "",
        ]
    lines.append("<i>— A2 Dembe / A5 Castillo · Thunderbird Fare Watch</i>")
    return "\n".join(lines)


def main() -> int:
    logger.info("Centrav flight watch cycle starting")
    try:
        result = asyncio.run(run_centrav_flight_watch_cycle())
    except Exception as exc:
        logger.error("Cycle failed with exception: %s", exc, exc_info=True)
        return 1

    # Print full JSON to stdout (captured in fare_watch.log by service)
    print(json.dumps(result, indent=2))

    # Summary line for log readability
    ok = result.get("watches_checked", 0)
    total = result.get("watches_total", 0)
    n_alerts = len(result.get("alerts", []))
    n_errors = len(result.get("errors", []))
    n_warnings = len(result.get("warnings", []))
    logger.info(
        "Cycle complete: %d/%d checked, %d alert(s), %d error(s), %d warning(s)",
        ok, total, n_alerts, n_errors, n_warnings,
    )

    if result.get("alerts"):
        logger.warning("PRICE ALERTS TRIGGERED:")
        for a in result["alerts"]:
            logger.warning("  %s: %s", a.get("watch_id"), a.get("alert"))

        token = _load_telegram_token()
        if token:
            msg = _build_alert_message(result["alerts"], ok)
            sent = _tg_send(token, msg)
            logger.info("Fare alert Telegram sent: %s", sent)
        else:
            logger.warning("No TELEGRAM_D2MC2C_TOKEN — fare alerts logged only")

    if result.get("warnings"):
        for w in result["warnings"]:
            logger.warning("  %s", w)

    return 0


if __name__ == "__main__":
    sys.exit(main())
