#!/usr/bin/env python3
"""
MISSION-002 — D2M Client Lifecycle Chart
=========================================
Generates an HTML timeline showing where each active client sits in the
D2M lifecycle using the anchor-node event model.

Anchor Nodes:
  Node 1 (Unpredictable): Initial Contact, Deposit/Booking
  Node 2 (Hard Anchors):  FPD, Pre-trip validation, Embarkation, Disembarkation
  Node 3 (Fluid):         Flights, Pre/post hotels, Excursions, Transfers

Output: ~/Thunderbird/output/lifecycle_chart.html

Usage:
  python3 OpsCenter/client_lifecycle_chart.py
"""

import json
import logging
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / "output"
OUTPUT_FILE = OUTPUT_DIR / "lifecycle_chart.html"
LOG_FILE = Path(__file__).parent.parent / "logs" / "overwatch.log"

logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s [LIFECYCLE-002] %(message)s",
)
log = logging.getLogger("lifecycle_chart")

# ── Client Data (sourced from dossiers 2026-04-07) ──────────────────────────
# Each client: name, ship, voyage, key anchor dates, status, revenue, notes
# Extend by reading dossiers via thunderbird_dossier.py when available.

TODAY = date.today()

CLIENTS = [
    {
        "name": "Furlow — Missy & John",
        "ship": "Regent Seven Seas Grandeur",
        "voyage": "Scandinavia",
        "booking": "3071222",
        "color": "#1a6fa8",
        "anchors": {
            "booked":      date(2025, 10, 1),   # approx booking date
            "fpd":         date(2026, 4, 1),    # ✅ PAID $15,486
            "validation":  date(2026, 8, 12),
            "depart_home": date(2026, 8, 26),
            "embark":      date(2026, 8, 29),
            "disembark":   date(2026, 9, 8),
        },
        "fpd_paid": True,
        "fpd_amount": 15486,
        "total": 19236,
        "status": "ACTIVE",
        "fluid": ["Finnair BB4X94 booked", "Suite 827 confirmed"],
        "open": ["Insurance (Chase Sapphire Review pending)"],
    },
    {
        "name": "Nichols — Larry",
        "ship": "Regent Seven Seas Grandeur",
        "voyage": "Scandinavia",
        "booking": "3078056",
        "color": "#2d8a6e",
        "anchors": {
            "booked":      date(2025, 11, 1),
            "fpd":         date(2026, 4, 1),
            "validation":  date(2026, 8, 12),
            "depart_home": date(2026, 8, 26),
            "embark":      date(2026, 8, 29),
            "disembark":   date(2026, 9, 8),
        },
        "fpd_paid": True,
        "fpd_amount": 0,      # confirm from dossier
        "total": 0,
        "status": "ACTIVE",
        "fluid": [],
        "open": ["Allianz insurance coverage brief on file", "Flights TBD"],
    },
    {
        "name": "Ely / Darrow",
        "ship": "Regent Seven Seas Grandeur",
        "voyage": "Scandinavia",
        "booking": "3096289",
        "color": "#7b3fa8",
        "anchors": {
            "booked":      date(2025, 12, 1),
            "fpd":         date(2026, 3, 23),   # ✅ PAID Mar 23
            "validation":  date(2026, 8, 12),
            "depart_home": date(2026, 8, 26),
            "embark":      date(2026, 8, 29),
            "disembark":   date(2026, 9, 8),
        },
        "fpd_paid": True,
        "fpd_amount": 0,
        "total": 0,
        "status": "ACTIVE",
        "fluid": [],
        "open": ["Flights TBD", "Pre/post hotel TBD"],
    },
    {
        "name": "Lyons — Nancy & Ken",
        "ship": "Regent Seven Seas Splendor",
        "voyage": "Athens → New York",
        "booking": "TBD",
        "color": "#c47a1e",
        "anchors": {
            "booked":      date(2026, 1, 15),   # approx
            "fpd":         date(2026, 5, 11),   # ~90 days before embark
            "validation":  date(2026, 7, 28),
            "depart_home": date(2026, 8, 9),
            "embark":      date(2026, 8, 11),   # Athens
            "disembark":   date(2026, 8, 25),   # New York
        },
        "fpd_paid": False,
        "fpd_amount": 0,
        "total": 0,
        "status": "ACTIVE",
        "fluid": ["Athens pre-cruise dinner planned"],
        "open": ["FPD TBD", "Flights TBD", "Athens hotel TBD"],
    },
    {
        "name": "McLeod / McGlasson — Erik & Melissa",
        "ship": "Silver Muse",
        "voyage": "Mediterranean",
        "booking": "298475-25",
        "color": "#b03030",
        "anchors": {
            "booked":      date(2025, 9, 1),
            "fpd":         date(2026, 1, 24),   # ✅ PAID
            "validation":  date(2026, 6, 9),
            "depart_home": date(2026, 6, 18),   # DEN→FCO
            "embark":      date(2026, 6, 23),   # Venice (Fusina)
            "disembark":   date(2026, 7, 3),
        },
        "fpd_paid": True,
        "fpd_amount": 0,
        "total": 0,
        "status": "ACTIVE",
        "fluid": [
            "DEN→FCO Jun 18 (UA177, PNR NFBDP6)",
            "Rome Jun 19-21: Colosseum, Florence day trip",
            "Vatican Jun 22",
            "Blacklane transfer confirmed",
            "Suite 617 confirmed",
        ],
        "open": ["Rome→Civitavecchia transfer dispute unresolved", "Return transfers TBD"],
    },
    {
        "name": "Kuklinski Group — Kyle / Roger / Josh",
        "ship": "Viking Mars",
        "voyage": "Panama Canal",
        "booking": "9593880 / 9593873 / 9595029",
        "color": "#1a5c1a",
        "anchors": {
            "booked":      date(2026, 3, 10),
            "fpd":         date(2026, 3, 31),   # ✅ PAID $21,244
            "validation":  date(2026, 11, 17),
            "depart_home": date(2026, 12, 15),
            "embark":      date(2026, 12, 17),  # Panama City
            "disembark":   date(2026, 12, 27),
        },
        "fpd_paid": True,
        "fpd_amount": 21244,
        "total": 21244,
        "status": "ACTIVE",
        "fluid": [],
        "open": ["Flights NOT booked", "Pre/post hotel NOT booked", "Transfers NOT booked", "Josh guest form missing"],
    },
    {
        "name": "Westbrook — Ron & Lindy",
        "ship": "Silver Nova",
        "voyage": "Pacific / Hawaii",
        "booking": "TBD",
        "color": "#6b6b6b",
        "anchors": {
            "booked":      date(2026, 2, 1),
            "fpd":         date(2026, 5, 1),
            "validation":  date(2026, 8, 1),
            "depart_home": date(2026, 8, 15),
            "embark":      date(2026, 8, 20),
            "disembark":   date(2026, 9, 5),
        },
        "fpd_paid": False,
        "fpd_amount": 0,
        "total": 0,
        "status": "PROSPECT — Itinerary delivered, awaiting Commander approval to send",
        "fluid": [],
        "open": ["Itinerary pending Commander send approval", "Booking not confirmed"],
    },
]


def lifecycle_phase(client: dict) -> tuple[str, str]:
    """Return (phase_label, phase_color) based on today's position in client journey."""
    anchors = client["anchors"]
    embark = anchors["embark"]
    disembark = anchors["disembark"]
    fpd = anchors.get("fpd")

    if TODAY > disembark:
        return "POST-CRUISE", "#888888"
    if TODAY >= embark:
        return "ON VOYAGE", "#1a8a1a"
    if fpd and TODAY >= fpd:
        return "PRE-CRUISE ACTIVE", "#1a6fa8"
    if fpd and TODAY < fpd:
        days_to_fpd = (fpd - TODAY).days
        if days_to_fpd <= 30:
            return f"FPD DUE ({days_to_fpd}d)", "#c0392b"
        return "BOOKED — PRE-FPD", "#e67e22"
    return "EARLY STAGE", "#95a5a6"


def days_label(d: date) -> str:
    delta = (d - TODAY).days
    if delta < 0:
        return f"✅ {abs(delta)}d ago"
    if delta == 0:
        return "TODAY"
    return f"T-{delta}d"


def build_html() -> str:
    rows = []
    for c in CLIENTS:
        phase, phase_color = lifecycle_phase(c)
        anchors = c["anchors"]

        open_items = "".join(f"<li>⚠️ {x}</li>" for x in c["open"]) if c["open"] else "<li style='color:#888'>None</li>"
        fluid_items = "".join(f"<li>✅ {x}</li>" for x in c["fluid"]) if c["fluid"] else "<li style='color:#888'>TBD</li>"

        anchor_rows = ""
        labels = {
            "booked": "Booked",
            "fpd": "Final Payment",
            "validation": "Pre-trip Validation",
            "depart_home": "Depart Home",
            "embark": "Embarkation",
            "disembark": "Disembarkation",
        }
        for key, label in labels.items():
            d = anchors.get(key)
            if not d:
                continue
            past = d < TODAY
            style = "color:#888;text-decoration:line-through;" if past else "font-weight:bold;"
            paid_tag = ""
            if key == "fpd" and c.get("fpd_paid"):
                amt = f"${c['fpd_amount']:,}" if c['fpd_amount'] else ""
                paid_tag = f" <span style='color:#1a8a1a;font-weight:bold;'>✅ PAID {amt}</span>"
            elif key == "fpd" and not c.get("fpd_paid"):
                paid_tag = " <span style='color:#c0392b;font-weight:bold;'>⚠️ UNPAID</span>"
            anchor_rows += f"""
            <tr>
              <td style='{style}'>{label}</td>
              <td style='{style}'>{d.strftime('%b %d, %Y')}</td>
              <td>{days_label(d)}{paid_tag}</td>
            </tr>"""

        rows.append(f"""
        <div class="client-card" style="border-left: 6px solid {c['color']};">
          <div class="client-header">
            <div>
              <h2>{c['name']}</h2>
              <div class="ship-info">{c['ship']} — {c['voyage']}</div>
              <div class="booking-ref">Booking: {c['booking']}</div>
            </div>
            <div class="phase-badge" style="background:{phase_color};">{phase}</div>
          </div>
          <div class="client-body">
            <div class="section">
              <h3>📅 Anchor Nodes</h3>
              <table class="anchor-table">
                <thead><tr><th>Event</th><th>Date</th><th>Status</th></tr></thead>
                <tbody>{anchor_rows}</tbody>
              </table>
            </div>
            <div class="section">
              <h3>✅ Fluid Variables (Confirmed)</h3>
              <ul>{fluid_items}</ul>
            </div>
            <div class="section">
              <h3>⚠️ Open Items</h3>
              <ul>{open_items}</ul>
            </div>
          </div>
        </div>""")

    cards_html = "\n".join(rows)
    generated = datetime.now().strftime("%Y-%m-%d %H:%M MT")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>D2M Client Lifecycle Chart — {generated}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: Georgia, serif; background: #f7f3ea; color: #222; padding: 24px; }}
  .header {{ text-align: center; margin-bottom: 32px; }}
  .header h1 {{ font-size: 2em; color: #1a3a5c; }}
  .header .subtitle {{ color: #555; margin-top: 6px; font-size: 0.95em; }}
  .client-card {{ background: #fff; border-radius: 8px; margin-bottom: 28px;
                  box-shadow: 0 2px 8px rgba(0,0,0,0.08); overflow: hidden; }}
  .client-header {{ display: flex; justify-content: space-between; align-items: flex-start;
                    padding: 20px 24px; background: #f0ece0; }}
  .client-header h2 {{ font-size: 1.4em; color: #1a3a5c; }}
  .ship-info {{ color: #555; margin-top: 4px; font-style: italic; }}
  .booking-ref {{ color: #888; font-size: 0.85em; margin-top: 2px; }}
  .phase-badge {{ padding: 8px 16px; border-radius: 20px; color: #fff;
                  font-weight: bold; font-size: 0.85em; white-space: nowrap; }}
  .client-body {{ display: grid; grid-template-columns: 1.5fr 1fr 1fr; gap: 0; }}
  .section {{ padding: 20px 24px; border-right: 1px solid #eee; }}
  .section:last-child {{ border-right: none; }}
  .section h3 {{ font-size: 0.9em; color: #555; margin-bottom: 12px;
                 text-transform: uppercase; letter-spacing: 0.5px; }}
  .anchor-table {{ width: 100%; border-collapse: collapse; font-size: 0.88em; }}
  .anchor-table th {{ text-align: left; color: #888; font-weight: normal;
                      padding: 4px 0; border-bottom: 1px solid #eee; }}
  .anchor-table td {{ padding: 5px 4px 5px 0; vertical-align: top; }}
  ul {{ list-style: none; padding: 0; font-size: 0.88em; }}
  ul li {{ padding: 4px 0; line-height: 1.4; }}
  .footer {{ text-align: center; color: #888; font-size: 0.8em; margin-top: 24px; }}
  @media (max-width: 800px) {{
    .client-body {{ grid-template-columns: 1fr; }}
    .section {{ border-right: none; border-bottom: 1px solid #eee; }}
  }}
</style>
</head>
<body>
<div class="header">
  <h1>Dreams2Memories Travel — Client Lifecycle</h1>
  <div class="subtitle">Active Bookings · Anchor-Node Model · Generated {generated}</div>
</div>
{cards_html}
<div class="footer">Dreams2Memories Travel, LLC · Thunderbird OS · {generated}</div>
</body>
</html>"""


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    html = build_html()
    OUTPUT_FILE.write_text(html, encoding="utf-8")
    log.info(f"Lifecycle chart written to {OUTPUT_FILE}")
    print(f"✅ MISSION-002 COMPLETE — {OUTPUT_FILE}")
    return str(OUTPUT_FILE)


if __name__ == "__main__":
    main()
