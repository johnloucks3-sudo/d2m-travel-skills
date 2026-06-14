#!/usr/bin/env python3
"""
d2m-perx-trigger-detector — Perx interline discount monitor.

Per memory: Perx is an interline rates LEADING INDICATOR.
Heavy discounts on Perx = TA rates incoming from airlines.
This script watches Perx for discount surges and alerts Commander
so D2M can proactively position before TA rate drops.

Schedule: Every 30 min business hours / 2 hr off-hours via systemd timer
Output:   OpsCenter/logs/perx_trigger.log
          OpsCenter/data/perx_baseline.json
          hale_decisions.md on triggers
          Gmail draft on significant discount events
"""

import json
import logging
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
LOG_PATH = ROOT / "OpsCenter/logs/perx_trigger.log"
AUDIT_LOG = ROOT / "OpsCenter/logs/perx_trigger.jsonl"
BASELINE_FILE = ROOT / "OpsCenter/data/perx_baseline.json"
HALE_DECISIONS = ROOT / "hale_decisions.md"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [PERX-TRIGGER] %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(LOG_PATH)],
)
log = logging.getLogger(__name__)

# Trigger threshold: if any route shows > this % discount from baseline, fire alert
DISCOUNT_THRESHOLD_PCT = 20.0

# Key D2M routes to watch (based on active bookings)
WATCH_ROUTES = [
    {"origin": "DEN", "destination": "MIA", "label": "Denver→Miami (cruise gateway)"},
    {"origin": "DEN", "destination": "FLL", "label": "Denver→FLL (cruise gateway)"},
    {"origin": "DEN", "destination": "BCN", "label": "Denver→Barcelona"},
    {"origin": "DEN", "destination": "LIS", "label": "Denver→Lisbon"},
    {"origin": "DEN", "destination": "ATH", "label": "Denver→Athens"},
    {"origin": "DEN", "destination": "FCO", "label": "Denver→Rome"},
    {"origin": "DCA", "destination": "MIA", "label": "DCA→Miami"},
    {"origin": "ORD", "destination": "MIA", "label": "Chicago→Miami"},
]


def load_baseline() -> dict:
    try:
        if BASELINE_FILE.exists():
            return json.loads(BASELINE_FILE.read_text())
    except Exception:
        pass
    return {}


def save_baseline(baseline: dict) -> None:
    BASELINE_FILE.parent.mkdir(parents=True, exist_ok=True)
    BASELINE_FILE.write_text(json.dumps(baseline, indent=2))


def get_perx_rates(route: dict) -> dict | None:
    """
    Attempt to pull Perx interline rates via Perplexity intel or direct scrape.
    Perx doesn't have a public API — use Perplexity to get intel on current
    interline discount activity, then parse for signals.
    """
    try:
        sys.path.insert(0, str(ROOT))
        from core.search.perplexity_search import search

        query = (
            f"Current interline airline fares and discounts for {route['origin']} to {route['destination']}. "
            f"Are there any significant fare drops, promotional rates, or travel agent deals available today {date.today()}? "
            f"Report lowest available round-trip economy fare."
        )
        result = search(query, max_tokens_per_page=400)
        if not result:
            return None

        # Try to extract a price from the result
        import re
        price_matches = re.findall(r'\$(\d{2,4}(?:\.\d{2})?)', result)
        if price_matches:
            price = min(float(p) for p in price_matches)
            return {
                "route": f"{route['origin']}-{route['destination']}",
                "label": route["label"],
                "price": price,
                "intel": result[:400],
                "checked_at": datetime.now().isoformat(),
            }
    except Exception as e:
        log.debug(f"Perplexity error for {route['origin']}-{route['destination']}: {e}")

    return None


def check_for_triggers(baseline: dict) -> list[dict]:
    triggers = []

    for route in WATCH_ROUTES:
        key = f"{route['origin']}-{route['destination']}"
        current = get_perx_rates(route)
        if not current:
            continue

        if key in baseline:
            baseline_price = baseline[key].get("price", 0)
            current_price = current["price"]
            if baseline_price > 0:
                discount_pct = (baseline_price - current_price) / baseline_price * 100
                if discount_pct >= DISCOUNT_THRESHOLD_PCT:
                    triggers.append({
                        "route": key,
                        "label": route["label"],
                        "baseline_price": baseline_price,
                        "current_price": current_price,
                        "discount_pct": round(discount_pct, 1),
                        "intel": current.get("intel", ""),
                    })
                    log.warning(
                        f"PERX TRIGGER: {key} — {discount_pct:.1f}% drop "
                        f"(${baseline_price:.0f} → ${current_price:.0f})"
                    )
                else:
                    log.info(f"{key}: ${current_price:.0f} ({discount_pct:+.1f}% vs baseline ${baseline_price:.0f})")
        else:
            log.info(f"Baseline set for {key}: ${current['price']:.0f}")

        baseline[key] = current

    return triggers


def draft_perx_alert(triggers: list[dict], run_dt: datetime) -> None:
    try:
        sys.path.insert(0, str(ROOT))
        from core.email.thunderbird_gmail import gmail_create_draft_sync

        rows = "\n".join(
            f"<tr><td>{t['label']}</td><td>${t['baseline_price']:.0f}</td><td style='color:green;'><b>${t['current_price']:.0f}</b></td><td style='color:green;'><b>-{t['discount_pct']}%</b></td></tr>"
            for t in triggers
        )
        body = f"""<div style='background:#f7f3ea;padding:20px;font-family:Georgia;color:#0000ff;'>
<p>Commander —</p>
<p><strong>PERX INTERLINE SIGNAL DETECTED</strong></p>
<p>Heavy discounts detected — TA rate drops likely incoming. Recommend proactive client outreach on pending bookings.</p>
<table border='1' cellpadding='6' style='border-collapse:collapse;color:#0000ff;'>
<tr><th>Route</th><th>Baseline</th><th>Current</th><th>Discount</th></tr>
{rows}
</table>
<p>Per Wing intelligence: Perx heavy discounts = TA interline rates incoming within 2-4 weeks.</p>
<p>— Hale / Intel</p>
</div>"""
        gmail_create_draft_sync(
            to="d2mconcierge@gmail.com",
            subject=f"[PERX SIGNAL] {len(triggers)} Route(s) — TA Rates Likely Incoming",
            body=body,
        )
        log.info(f"Perx alert draft created for {len(triggers)} route(s)")
    except Exception as e:
        log.warning(f"Could not create Gmail draft: {e}")


def write_hale_decision(triggers: list[dict], run_dt: datetime) -> None:
    if not triggers:
        return
    lines = [
        f"\n### {run_dt.strftime('%Y-%m-%d %H:%M:%S')} — Autonomous Decision (Tier T0)\n",
        f"**Decision:** Perx trigger detector fired — {len(triggers)} route(s) showing significant discount\n",
    ]
    for t in triggers:
        lines.append(f"  - {t['label']}: -{t['discount_pct']}% (${t['baseline_price']:.0f}→${t['current_price']:.0f})\n")
    lines.append("**Domain:** Intel / Fare strategy\n**Type:** proactive alert\n**Outcome:** Commander draft created\n")
    with open(HALE_DECISIONS, "a") as f:
        f.writelines(lines)


def main() -> int:
    run_dt = datetime.now()
    log.info(f"Perx trigger detector — {run_dt.isoformat()}")

    baseline = load_baseline()
    triggers = check_for_triggers(baseline)
    save_baseline(baseline)

    entry = {
        "ts": run_dt.isoformat(),
        "routes_checked": len(WATCH_ROUTES),
        "triggers": len(triggers),
        "detail": triggers,
    }
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")

    if triggers:
        write_hale_decision(triggers, run_dt)
        draft_perx_alert(triggers, run_dt)
        log.warning(f"{len(triggers)} Perx trigger(s) — TA rates likely incoming")
    else:
        log.info("No Perx triggers — all rates stable")

    return 0


if __name__ == "__main__":
    sys.exit(main())
