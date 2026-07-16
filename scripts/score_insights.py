#!/usr/bin/env python3
"""
score_insights.py — close the prediction falsifiability loop in one line.

Usage:
  score_insights.py list                     # open cards, oldest first
  score_insights.py hit IX-xxxxxxxx [note]   # Commander actually asked → hit
  score_insights.py miss IX-xxxxxxxx [note]
  score_insights.py acted IX-xxxxxxxx [note] # executed proactively, pre-ask
  score_insights.py expire                   # auto-expire >7d open cards
  score_insights.py rates                    # per-seat hit-rate scoreboard
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.silver.insight_exchange import (  # noqa: E402
    open_cards, score_card, expire_stale, seat_hit_rates,
)

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    if cmd == "list":
        for c in sorted(open_cards(), key=lambda c: c["ts"]):
            print(f"{c['id']} [{c['seat']}→{c['suggested_owner'] or 'Wing'}] "
                  f"{c['kind']}/{c['confidence']} ({c['ts'][:10]}): {c['insight'][:110]}")
    elif cmd in ("hit", "miss", "acted"):
        note = " ".join(sys.argv[3:])
        c = score_card(sys.argv[2], cmd, note)
        print(f"{c['id']} → {cmd}" + (f" ({note})" if note else ""))
    elif cmd == "expire":
        ids = expire_stale()
        print(f"expired {len(ids)}: {ids}" if ids else "nothing stale")
    elif cmd == "rates":
        for seat, v in sorted(seat_hit_rates().items()):
            print(f"{seat}: hit_rate={v['hit_rate']} "
                  f"({v['hit']}✓ {v['miss']}✗ {v['expired']}⏰ {v['acted']}⚡ {v['open']} open)")
    else:
        sys.exit(__doc__)
