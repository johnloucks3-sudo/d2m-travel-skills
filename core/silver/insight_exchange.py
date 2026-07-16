"""
core/silver/insight_exchange.py — the cross-Hale Insight Exchange (2026-07-16).

Commander's intent: the three Hale seats (CC/OC/AG) work together like humans —
sharing what they see, offering help, encouraging each other — and anticipate
his prompts and directives from each seat's unique vantage. Silver (the
non-Hale, objective, Commander-DNA clone) collects every seat's cards, reasons
over intent — "more than keywords and phrases" — predicts the next ask, and
scores predictions hit/miss so the loop actually closes (the old
commander_prediction_ledger generated 64 predictions and scored zero).

One shared append-only file: OpsCenter/collaboration/insight_exchange.jsonl.

Card kinds (collegial by design, not a cold prediction ledger):
  anticipated_ask  — "the Commander will ask for X next; here's why"
  wing_priority    — "the Wing should be working on X before anyone asks"
  capability_offer — "I can do X that you can't — route it to me"
  assist_offer     — "I see your open mission Y; I can take part Z off you"
  finding_share    — "I learned X; it changes how you should do Y"
  kudos            — "seat X's work on Y was excellent because Z" (feeds the
                     effectiveness scorecard's traits dimension)

Anti-theater: a card's `signal` must resolve (file exists, or mission id on the
board) before it posts — Silver never accepts an uncited claim.
"""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
EXCHANGE = ROOT / "OpsCenter/collaboration/insight_exchange.jsonl"
PREDICTION_LEDGER = ROOT / "OpsCenter/commander_prediction_ledger.json"

SEATS = ("CC", "OC", "AG", "SILVER")
KINDS = ("anticipated_ask", "wing_priority", "capability_offer",
         "assist_offer", "finding_share", "kudos")
CONFIDENCE = ("CONFIRMED", "INFERRED", "UNKNOWN")
STATUSES = ("open", "acted", "hit", "miss", "expired")
EXPIRE_DAYS = 7


def _signal_ok(signal: str) -> bool:
    """Silver's citation gate: the signal must point at something real —
    an existing file/path, a mission id on the board, or a dated event ref."""
    s = (signal or "").strip()
    if not s:
        return False
    for token in re.findall(r"[\w./@-]+", s):
        p = Path(token) if token.startswith("/") else ROOT / token
        if ("/" in token or "." in token) and p.exists():
            return True
    if re.search(r"MISSION-[\w-]+", s):
        try:
            board = (ROOT / "OpsCenter/mission_board.json").read_text()
            return any(m in board for m in re.findall(r"MISSION-[\w-]+", s))
        except Exception:
            return False
    return False


def post_card(seat: str, kind: str, insight: str, *, reasoning: str = "",
              signal: str = "", confidence: str = "INFERRED",
              suggested_owner: str = "") -> dict:
    """Append one card. Raises on schema violations or an unresolvable signal —
    a card that can't cite its source doesn't enter the exchange."""
    if seat not in SEATS:
        raise ValueError(f"seat must be one of {SEATS}, got {seat!r}")
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}, got {kind!r}")
    if confidence not in CONFIDENCE:
        raise ValueError(f"confidence must be one of {CONFIDENCE}")
    if not insight.strip():
        raise ValueError("empty insight")
    if kind != "kudos" and not _signal_ok(signal):
        raise ValueError(f"signal does not resolve to anything real: {signal!r} "
                         "— cite a file, path, or mission id")
    card = {
        "id": f"IX-{uuid.uuid4().hex[:8]}",
        "seat": seat, "ts": datetime.now(timezone.utc).isoformat(),
        "kind": kind, "insight": insight.strip(), "reasoning": reasoning.strip(),
        "signal": signal.strip(), "confidence": confidence,
        "suggested_owner": suggested_owner, "status": "open", "scored_ts": None,
    }
    EXCHANGE.parent.mkdir(parents=True, exist_ok=True)
    with EXCHANGE.open("a") as f:
        f.write(json.dumps(card) + "\n")
    return card


def all_cards() -> list[dict]:
    if not EXCHANGE.exists():
        return []
    out = []
    for line in EXCHANGE.read_text().splitlines():
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    # last status wins: score events append a full updated copy of the card
    latest: dict[str, dict] = {}
    for c in out:
        latest[c["id"]] = c
    return list(latest.values())


def open_cards() -> list[dict]:
    return [c for c in all_cards() if c["status"] == "open"]


def score_card(card_id: str, status: str, note: str = "") -> dict:
    """Close the falsifiability loop: mark a card hit/miss/acted/expired by
    appending an updated copy (append-only file, last status wins)."""
    if status not in ("acted", "hit", "miss", "expired"):
        raise ValueError("status must be acted|hit|miss|expired")
    for c in all_cards():
        if c["id"] == card_id:
            c["status"] = status
            c["scored_ts"] = datetime.now(timezone.utc).isoformat()
            if note:
                c["score_note"] = note
            with EXCHANGE.open("a") as f:
                f.write(json.dumps(c) + "\n")
            return c
    raise KeyError(f"no card {card_id}")


def expire_stale(days: int = EXPIRE_DAYS) -> list[str]:
    """Cards older than `days` still open → expired (an unfalsified prediction
    is a miss that never owned up)."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    expired = []
    for c in open_cards():
        if datetime.fromisoformat(c["ts"]) < cutoff:
            score_card(c["id"], "expired", f"auto-expired after {days}d unmatched")
            expired.append(c["id"])
    return expired


def seat_hit_rates() -> dict[str, dict]:
    """Per-seat scoreboard from actually-scored cards — evidence, not assumption."""
    stats: dict[str, dict] = {}
    for c in all_cards():
        s = stats.setdefault(c["seat"], {"open": 0, "hit": 0, "miss": 0,
                                         "acted": 0, "expired": 0})
        s[c["status"]] = s.get(c["status"], 0) + 1
    for s in stats.values():
        scored = s["hit"] + s["miss"] + s["expired"]
        s["hit_rate"] = round(s["hit"] / scored, 2) if scored else None
    return stats


# ── Silver: collect all seats' cards + predict (the reasoning pass) ─────────

SYNTHESIS_TASK = """\
Collect and synthesize. Below are the open insight cards from every seat, and
the open entries of the legacy commander_prediction_ledger (heuristic signals —
treat them as raw inputs, not conclusions).

As the Commander's DNA clone, reason over his intent and the Wing's trajectory:
1. What will he ask for next that no card yet covers?
2. Which open cards matter most today (dedupe, rank top 5)?
3. Where should one seat assist another (name giver, receiver, and the task)?

Output STRICT JSON: a list of card objects, each:
{"kind": "<anticipated_ask|wing_priority|assist_offer|finding_share|kudos>",
 "insight": "...", "reasoning": "intent-level why, not a trigger",
 "signal": "existing file path or MISSION-id that supports it",
 "confidence": "CONFIRMED|INFERRED|UNKNOWN", "suggested_owner": "CC|OC|AG"}
Only cite signals that actually appear in the context. No prose outside JSON.
"""


def _legacy_predictions(max_items: int = 20) -> str:
    try:
        led = json.loads(PREDICTION_LEDGER.read_text())
        entries = led if isinstance(led, list) else led.get("predictions", [])
        rows = [f"- {e.get('prediction', e)!s}"[:200]
                for e in entries if isinstance(e, dict) and e.get("status") == "open"]
        return "\n".join(rows[:max_items]) or "(none)"
    except Exception as e:
        return f"(ledger unreadable: {e})"


def silver_synthesize(out_path: str | None = None, *, wait: bool = False):
    """Dispatch Silver's reasoning pass over all open cards + legacy predictions.
    Output lands at out_path; ingest_silver_output() validates + posts it."""
    from core.silver.reasoner import dispatch
    out = out_path or str(ROOT / "output/silver_insights.json")
    cards_blob = json.dumps(open_cards(), indent=1)[:30_000]
    task = (SYNTHESIS_TASK
            + f"\n═══ OPEN CARDS ═══\n{cards_blob}"
            + f"\n═══ LEGACY PREDICTION LEDGER (open) ═══\n{_legacy_predictions()}")
    return dispatch(task, out, wait=wait)


def ingest_silver_output(path: str) -> tuple[list[dict], list[str]]:
    """Validate Silver's output through the citation gate and post what passes.
    Returns (posted_cards, rejects) — rejects are reported, never silently dropped."""
    raw = Path(path).read_text()
    m = re.search(r"\[.*\]", raw, re.S)
    items = json.loads(m.group(0) if m else raw)
    posted, rejects = [], []
    for it in items:
        try:
            posted.append(post_card(
                "SILVER", it.get("kind", "anticipated_ask"), it.get("insight", ""),
                reasoning=it.get("reasoning", ""), signal=it.get("signal", ""),
                confidence=it.get("confidence", "INFERRED"),
                suggested_owner=it.get("suggested_owner", ""),
            ))
        except (ValueError, KeyError) as e:
            rejects.append(f"{it.get('insight', '?')[:60]} — {e}")
    return posted, rejects


def brief_lines(top_n: int = 5) -> list[str]:
    """Top open insights + seat scoreboard for the CHIEF SILVER brief section."""
    cards = sorted(open_cards(), key=lambda c: (c["confidence"] != "CONFIRMED", c["ts"]))
    lines = [f"  - 💡 [{c['seat']}→{c['suggested_owner'] or 'Wing'}] "
             f"({c['kind']}, {c['confidence']}) {c['insight'][:120]}"
             for c in cards[:top_n]]
    rates = seat_hit_rates()
    if rates:
        lines.append("  - 📊 hit-rates: " + " · ".join(
            f"{s}:{v['hit_rate'] if v['hit_rate'] is not None else '—'}"
            f"({v['hit']}✓/{v['miss'] + v['expired']}✗/{v['open']}open)"
            for s, v in sorted(rates.items())))
    return lines
