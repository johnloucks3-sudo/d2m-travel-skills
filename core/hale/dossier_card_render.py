"""
Track C — dossier visual cards. v1 scope: payment-roadmap section only, one couple
(Furlow, proof-of-structure). Reuses Track A's brand tokens — no re-derived palette.

WF-17: output lands in output/dossier-cards/ and STOPS there. No send path here.
Read-only against the dossier file — never writes back (dossier field write authority
is Harlan/Reyes/Luna per dossiers/CLAUDE.md PRODUCTION-LOCK table).
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from core.hale.d2m_brand_tokens import PAGE_SHELL_CSS, SHIMMER, TEXT_ON_NAVY_MUTED
from core.hale.stat_tile import stat_tile, status_badge, tile_row

DOSSIERS_DIR = Path.home() / "Thunderbird" / "dossiers"
CARDS_OUT_DIR = Path.home() / "Thunderbird" / "output" / "dossier-cards"


def parse_dossier(path: Path) -> dict:
    """Extract YAML front matter + the KEY DATES table from a dossier .md file."""
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.DOTALL)
    if not m:
        raise ValueError(f"{path}: no YAML front matter found")
    front = yaml.safe_load(m.group(1)) or {}
    body = m.group(2)

    key_dates: list[tuple[str, str]] = []
    kd_match = re.search(r"### KEY DATES\s*\n\|.*?\n\|[-\s|]+\n((?:\|.*\n?)+)", body)
    if kd_match:
        for line in kd_match.group(1).strip().splitlines():
            cols = [c.strip() for c in line.strip("|").split("|")]
            if len(cols) >= 2:
                key_dates.append((cols[0], cols[1]))

    front["_key_dates"] = key_dates
    return front


def _payment_roadmap_html(d: dict) -> str:
    status = d.get("payment_status", "unknown")
    fpd_amount = d.get("fpd_amount")
    fpd = d.get("fpd", "?")
    tiles = [
        stat_tile("Payment Status", status_badge(status.replace("_", " ").upper())),
        stat_tile("FPD", str(fpd)),
    ]
    if fpd_amount:
        tiles.insert(1, stat_tile("Final Payment", f"${fpd_amount:,.2f}"))

    key_dates_rows = "".join(
        f"<tr><td>{date}</td><td>{milestone}</td></tr>" for date, milestone in d.get("_key_dates", [])
    )
    key_dates_html = (
        f"<table class='d2m-table'><tr><th>Date</th><th>Milestone</th></tr>{key_dates_rows}</table>"
        if key_dates_rows else f"<p style='color:{TEXT_ON_NAVY_MUTED}'>No key dates parsed.</p>"
    )

    return f"""
    <div class="d2m-card">
      <h2>Payment Roadmap</h2>
      {tile_row(tiles)}
    </div>
    <div class="d2m-card">
      <h2>Key Dates</h2>
      {key_dates_html}
    </div>"""


def render_card_html(d: dict) -> str:
    full_name = d.get("full_name", d.get("client", "Unknown"))
    ship = d.get("ship", "?")
    voyage = d.get("voyage", "")
    booking = d.get("booking", "?")
    departure = d.get("departure", "?")

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>{full_name} — Trip Card</title>
<style>{PAGE_SHELL_CSS}</style></head>
<body>
  <h1 style="color:{SHIMMER};font-weight:400;">{full_name}</h1>
  <div style="color:{TEXT_ON_NAVY_MUTED};margin-bottom:16px;">
    {ship}{' — ' + voyage if voyage else ''} · Booking {booking} · Departs {departure}
  </div>
  {_payment_roadmap_html(d)}
</body>
</html>"""


def write_card(dossier_filename: str) -> Path:
    d = parse_dossier(DOSSIERS_DIR / dossier_filename)
    html = render_card_html(d)
    CARDS_OUT_DIR.mkdir(parents=True, exist_ok=True)
    slug = d.get("client", "client").lower().replace(" ", "_") + "_" + str(d.get("booking", "unk"))
    out_path = CARDS_OUT_DIR / f"{slug}.html"
    out_path.write_text(html, encoding="utf-8")
    return out_path


if __name__ == "__main__":
    print(write_card("Furlow_Regent_3071222.md"))
