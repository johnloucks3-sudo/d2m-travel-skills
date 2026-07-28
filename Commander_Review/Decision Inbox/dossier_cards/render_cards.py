#!/usr/bin/env python3
"""Render dossier visual cards (Track C) from data/*.json -> cards/*.html."""
import json
from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

BASE = Path(__file__).parent
DATA_DIR = BASE / "data"
CARDS_DIR = BASE / "cards"

STAGE_ICON = {"paid": "✓", "partial": "◐", "unpaid": "○"}


def fmt_date(iso):
    if not iso:
        return "—"
    y, m, d = (int(x) for x in iso.split("-"))
    return date(y, m, d).strftime("%b %-d, %Y")


def fmt_money(n):
    if n is None:
        return "—"
    return f"${n:,.0f}"


def build_timeline(data_as_of, departure, return_date, stages):
    y, m, d = (int(x) for x in data_as_of.split("-"))
    today = date(y, m, d)
    dy, dm, dd = (int(x) for x in departure.split("-"))
    dep = date(dy, dm, dd)
    ry, rm, rd = (int(x) for x in return_date.split("-"))
    ret = date(ry, rm, rd)

    start = None
    for s in stages:
        if s.get("date"):
            sy, sm, sd = (int(x) for x in s["date"].split("-"))
            sdate = date(sy, sm, sd)
            if start is None or sdate < start:
                start = sdate
    if start is None:
        start = dep  # fallback, no deposit date on file

    total_span = (ret - start).days or 1
    today_offset = (today - start).days
    today_pct = max(0, min(100, round(today_offset / total_span * 100, 1)))
    dep_offset = (dep - start).days
    progress_pct = max(0, min(100, round(dep_offset / total_span * 100, 1)))

    return {
        "today_pct": today_pct,
        "progress_pct": progress_pct,
        "start_label": f"{'Deposit' if start != dep else 'Departure'} {fmt_date(start.isoformat())}",
    }


def render_one(json_path: Path, env: Environment):
    data = json.loads(json_path.read_text())

    departure_fmt = fmt_date(data["departure_date"])
    return_fmt = fmt_date(data["return_date"])

    payment_stages = []
    for s in data["payment"]["stages"]:
        payment_stages.append({
            "label": s["label"],
            "date_fmt": fmt_date(s.get("date")),
            "amount_fmt": fmt_money(s.get("amount")),
            "status": s["status"],
            "icon": STAGE_ICON[s["status"]],
        })

    timeline = build_timeline(
        data["data_as_of"], data["departure_date"], data["return_date"],
        data["payment"]["stages"],
    )

    y, m, d = (int(x) for x in data["data_as_of"].split("-"))
    as_of = date(y, m, d)
    dy, dm, dd = (int(x) for x in data["departure_date"].split("-"))
    days_to_departure = (date(dy, dm, dd) - as_of).days

    has_internal_alerts = any(a.get("internal_only") for a in data["alerts"])

    tmpl = env.get_template("card.html.jinja")
    html = tmpl.render(
        data=data,
        departure_fmt=departure_fmt,
        return_fmt=return_fmt,
        payment_stages=payment_stages,
        payment_total_fmt=fmt_money(data["payment"]["total_amount"]),
        payment_paid_fmt=fmt_money(data["payment"]["paid_to_date"]),
        payment_balance_fmt=fmt_money(data["payment"]["balance_due"]),
        timeline=timeline,
        quick={"days_to_departure": days_to_departure},
        has_internal_alerts=has_internal_alerts,
    )

    out_path = CARDS_DIR / f"{data['client_id']}.html"
    out_path.write_text(html)
    return out_path, data["display_name"]


def main():
    CARDS_DIR.mkdir(exist_ok=True)
    env = Environment(loader=FileSystemLoader(str(BASE / "template")), autoescape=True)
    rendered = []
    for json_path in sorted(DATA_DIR.glob("*.json")):
        out_path, name = render_one(json_path, env)
        rendered.append((out_path, name))
        print(f"rendered {name} -> {out_path}")

    index_items = "\n".join(
        f'<li><a href="{p.name}">{n}</a></li>' for p, n in rendered
    )
    index_html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<title>Dossier Cards — Index</title>
<style>body{{font-family:system-ui,sans-serif;padding:24px;background:#fcfcfb;}}
li{{margin:8px 0;font-size:16px;}} a{{color:#184f95;text-decoration:none;font-weight:600;}}</style>
</head><body><h1>Dossier Visual Cards</h1><ul>{index_items}</ul></body></html>"""
    (CARDS_DIR / "index.html").write_text(index_html)
    print(f"rendered index -> {CARDS_DIR / 'index.html'}")


if __name__ == "__main__":
    main()
