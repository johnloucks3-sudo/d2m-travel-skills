#!/usr/bin/env python3
"""
silver_daily_digest.py — CHIEF SILVER daily synthesis digest, canonical
AM-brief format (Commander 2026-07-16: the first free-form digest was
unreadable — this matches hale_morning_brief.py's header/section structure,
one line per item).

Usage: silver_daily_digest.py [--synthesize] [--no-send]
  --synthesize  run Silver's reasoning pass first (otherwise digest open cards)
  --no-send     print HTML to stdout instead of emailing
"""
import html
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from core.silver.insight_exchange import open_cards, seat_hit_rates  # noqa: E402

KIND_EMOJI = {"anticipated_ask": "🔮", "wing_priority": "🎯", "capability_offer": "🧰",
              "assist_offer": "🤝", "finding_share": "💡", "kudos": "🏅"}


def _dedupe(cards: list[dict]) -> list[dict]:
    """Collapse near-duplicates (multiple seats/synthesis runs cover the same
    ground): first-40-chars key across ALL seats, earliest card wins."""
    seen, out = set(), []
    for c in sorted(cards, key=lambda c: c["ts"]):
        key = c["insight"][:40].lower()
        if key not in seen:
            seen.add(key)
            out.append(c)
    return out


def _line(c: dict) -> str:
    return (f'<div class="metric">{KIND_EMOJI.get(c["kind"], "•")} '
            f'<b>[{c["seat"]}]</b> {html.escape(c["insight"][:160])} '
            f'<span style="color:#888; font-size:0.85em;">({c["id"]}, {c["confidence"]})</span></div>')


def build_digest() -> str:
    cards = _dedupe(open_cards())
    confirmed = [c for c in cards if c["confidence"] == "CONFIRMED"]
    top3 = confirmed[:3]
    asks = [c for c in cards if c["kind"] == "anticipated_ask" and c not in top3]
    priorities = [c for c in cards if c["kind"] == "wing_priority" and c not in top3]
    collegial = [c for c in cards if c["kind"] in ("assist_offer", "finding_share",
                                                   "capability_offer", "kudos")]
    rates = seat_hit_rates()
    rate_line = " · ".join(f"{s}: {v['hit']}✓ {v['miss'] + v['expired']}✗ {v['open']} open"
                           for s, v in sorted(rates.items()))
    now = datetime.now()

    def section(title, items, color="#0000ff", cap=8):
        if not items:
            return ""
        body = "".join(_line(c) for c in items[:cap])
        more = f'<div class="metric" style="color:#888;">…and {len(items) - cap} more (score_insights.py list)</div>' if len(items) > cap else ""
        return (f'<div class="section" style="border-left:3px solid {color};">'
                f'<div class="section-title" style="color:{color};">{title}</div>{body}{more}</div>')

    return f"""
<html>
<head>
    <style>
        body {{ font-family: Georgia, serif; color: #0000ff; background: #f7f3ea; margin: 20px; line-height: 1.6; }}
        .header {{ border-bottom: 2px solid #0000ff; padding-bottom: 10px; margin-bottom: 20px; }}
        .section {{ margin-bottom: 20px; padding: 10px; border-left: 3px solid #0000ff; padding-left: 15px; }}
        .section-title {{ font-weight: bold; font-size: 1.1em; margin-bottom: 8px; }}
        .metric {{ margin: 5px 0; }}
        .footer {{ margin-top: 30px; border-top: 1px solid #0000ff; padding-top: 10px; font-size: 0.9em; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🛡️ CHIEF SILVER — Daily Synthesis — {now.strftime('%A, %B %d, %Y')}</h1>
        <p>Time: {now.strftime('%H:%M MT')} | {len(cards)} distinct open insights | Scoreboard: {rate_line}</p>
    </div>
    {section("🔴 TOP 3 — CONFIRMED, ACTION OR DECISION NEEDED", top3, "#ff0000", 3)}
    {section("🔮 ANTICIPATED ASKS — what you will ask for next", asks)}
    {section("🎯 WING PRIORITIES — work before anyone asks", priorities)}
    {section("🤝 SEAT-TO-SEAT — assists, findings, offers", collegial)}
    <div class="footer">
        Grade my predictions: <code>score_insights.py hit|miss IX-xxxx</code> — hit-rates only mean something if you score.<br>
        Full list: <code>score_insights.py list</code> · Raw: OpsCenter/collaboration/insight_exchange.jsonl<br><br>
        — CMSgt S. Sterling, Command Chief
    </div>
</body>
</html>"""


if __name__ == "__main__":
    if "--synthesize" in sys.argv:
        from core.silver.insight_exchange import silver_synthesize, ingest_silver_output
        out = str(ROOT / "output/silver_insights.json")
        Path(out).unlink(missing_ok=True)
        silver_synthesize(out, wait=True)
        posted, rejects = ingest_silver_output(out)
        print(f"synthesis: posted {len(posted)}, rejected {len(rejects)}")
    digest = build_digest()
    if "--no-send" in sys.argv:
        print(digest)
    else:
        from wing_email_sender import send_wing_email
        mid = send_wing_email(
            "johnloucks3@gmail.com",
            f"🛡️ CHIEF SILVER — Daily Synthesis — {datetime.now().strftime('%b %d')}",
            digest)
        print("SENT:", mid)
