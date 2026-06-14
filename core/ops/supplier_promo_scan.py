#!/usr/bin/env python3
"""
d2m-supplier-promo-scan — Daily scan of supplier promotions, classify by client fit.

Uses Perplexity to scan for current promotions from D2M luxury suppliers
(Regent, Silversea, Viking, Windstar, Scenic, etc.).
Classifies promos against active client profiles and surfaces top matches.

Schedule: Daily 05:00 MDT via systemd timer
Output:   OpsCenter/logs/supplier_promo_scan.log
          OpsCenter/data/supplier_promos.json
          Gmail draft (d2mconcierge) for top matches
"""

import json
import logging
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
BLACKBOARD_DIR = ROOT / "Blackboard/clients"
LOG_PATH = ROOT / "OpsCenter/logs/supplier_promo_scan.log"
AUDIT_LOG = ROOT / "OpsCenter/logs/supplier_promo_scan.jsonl"
PROMOS_FILE = ROOT / "OpsCenter/data/supplier_promos.json"
HALE_DECISIONS = ROOT / "hale_decisions.md"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [SUPPLIER-PROMO] %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(LOG_PATH)],
)
log = logging.getLogger(__name__)

D2M_SUPPLIERS = [
    "Regent Seven Seas",
    "Silversea",
    "Viking Ocean",
    "Windstar",
    "Scenic",
    "Seabourn",
    "Crystal Cruises",
    "Explora Journeys",
]


def get_active_client_profiles() -> list[dict]:
    """Load client interests from Blackboard YAML."""
    import yaml

    clients = []
    today = date.today()

    for fp in BLACKBOARD_DIR.glob("*.yaml"):
        try:
            data = yaml.safe_load(fp.read_text())
        except Exception:
            continue
        if not data:
            continue

        # Skip clients who have departed
        bookings = data.get("bookings", [])
        if isinstance(bookings, dict):
            bookings = [bookings]

        future_booking = False
        for b in bookings:
            if not isinstance(b, dict):
                continue
            dep_str = b.get("departure_date") or b.get("embark_date")
            if dep_str:
                try:
                    dep = date.fromisoformat(str(dep_str)[:10])
                    if dep > today + timedelta(days=30):
                        future_booking = True
                except Exception:
                    pass

        clients.append({
            "client_id": data.get("client_id", fp.stem),
            "client_name": data.get("name", data.get("client_name", fp.stem)),
            "preferred_suppliers": data.get("preferred_suppliers", []),
            "preferred_destinations": data.get("preferred_destinations", []),
            "travel_style": data.get("travel_style", ""),
            "has_future_booking": future_booking,
        })

    return clients


def scan_supplier_promos() -> list[dict]:
    """Use Perplexity to find current supplier promotions."""
    try:
        sys.path.insert(0, str(ROOT))
        from core.search.perplexity_search import search

        query = (
            f"Current luxury cruise promotions and deals from {', '.join(D2M_SUPPLIERS[:5])} "
            f"as of {date.today()}. List specific promotions with savings amounts, departure dates, "
            f"and booking deadlines. Focus on 2026-2027 sailings."
        )
        results = search(query, max_results=5, max_tokens_per_page=1000)
        if not results:
            return []

        # Flatten all snippets into one searchable text
        result = " ".join(r.get("snippet", "") + " " + r.get("title", "") for r in results)

        # Parse into structured promos
        promos = []
        for supplier in D2M_SUPPLIERS:
            if supplier.lower() in result.lower() or supplier.split()[0].lower() in result.lower():
                idx = result.lower().find(supplier.lower())
                if idx == -1:
                    idx = result.lower().find(supplier.split()[0].lower())
                if idx >= 0:
                    snippet = result[max(0, idx-50):idx+400].strip()
                    promos.append({
                        "supplier": supplier,
                        "intel": snippet,
                        "found_at": datetime.now().isoformat(),
                        "sources": [r.get("url", "") for r in results if r.get("url")],
                    })

        return promos
    except Exception as e:
        log.warning(f"Perplexity error: {e}")
        return []


def match_promos_to_clients(promos: list[dict], clients: list[dict]) -> list[dict]:
    """Match promotions to interested clients."""
    matches = []
    for promo in promos:
        supplier_lower = promo["supplier"].lower()
        for client in clients:
            preferred = [s.lower() for s in (client.get("preferred_suppliers") or [])]
            # Match on preferred supplier or has future booking with same line
            if preferred and any(p in supplier_lower or supplier_lower in p for p in preferred):
                matches.append({
                    "client_name": client["client_name"],
                    "supplier": promo["supplier"],
                    "intel": promo["intel"][:200],
                    "has_future_booking": client["has_future_booking"],
                })

    return matches


def draft_promo_brief(promos: list[dict], matches: list[dict], run_dt: datetime) -> None:
    if not promos:
        return
    try:
        sys.path.insert(0, str(ROOT))
        from core.email.thunderbird_gmail import gmail_create_draft_sync

        promo_rows = "".join(
            f"<tr><td><b>{p['supplier']}</b></td><td style='font-size:12px;'>{p['intel'][:150]}</td></tr>"
            for p in promos
        )
        match_section = ""
        if matches:
            match_rows = "".join(
                f"<tr><td>{m['client_name']}</td><td>{m['supplier']}</td><td style='font-size:11px;'>{m['intel'][:100]}</td></tr>"
                for m in matches[:5]
            )
            match_section = f"""<p><strong>Client Matches ({len(matches)}):</strong></p>
<table border='1' cellpadding='4' style='border-collapse:collapse;color:#0000ff;font-size:12px;'>
<tr><th>Client</th><th>Supplier</th><th>Promo</th></tr>
{match_rows}
</table>"""

        body = f"""<div style='background:#f7f3ea;padding:20px;font-family:Georgia;color:#0000ff;'>
<p>Commander —</p>
<p><strong>SUPPLIER PROMO SCAN — {run_dt.strftime('%B %d, %Y')}</strong></p>
<p>Found {len(promos)} active promotion(s) from D2M supplier partners:</p>
<table border='1' cellpadding='6' style='border-collapse:collapse;color:#0000ff;'>
<tr><th>Supplier</th><th>Intel</th></tr>
{promo_rows}
</table>
{match_section}
<p>— Intel / Hale</p>
</div>"""

        gmail_create_draft_sync(
            to="d2mconcierge@gmail.com",
            subject=f"[SUPPLIER PROMOS] {len(promos)} Active — {run_dt.strftime('%b %d')}",
            body=body,
        )
        log.info(f"Supplier promo brief created: {len(promos)} promos, {len(matches)} client matches")
    except Exception as e:
        log.warning(f"Could not draft promo brief: {e}")


def main() -> int:
    run_dt = datetime.now()
    log.info(f"Supplier promo scan — {run_dt.date()}")

    promos = scan_supplier_promos()
    log.info(f"Found {len(promos)} supplier promotion(s)")

    clients = get_active_client_profiles()
    matches = match_promos_to_clients(promos, clients)

    # Save promos
    promo_data = {
        "ts": run_dt.isoformat(),
        "promos": promos,
        "matches": matches,
    }
    PROMOS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROMOS_FILE.write_text(json.dumps(promo_data, indent=2))

    entry = {
        "ts": run_dt.isoformat(),
        "promos_found": len(promos),
        "client_matches": len(matches),
    }
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")

    if promos:
        draft_promo_brief(promos, matches, run_dt)
    else:
        log.info("No active supplier promos found today")

    return 0


if __name__ == "__main__":
    sys.exit(main())
