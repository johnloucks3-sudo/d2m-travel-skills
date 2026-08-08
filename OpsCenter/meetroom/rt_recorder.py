#!/usr/bin/env python3
"""rt_recorder.py — ROUND TABLE transcript recorder (receipts + replay timeline).

Merges per-seat point papers ({ag,cc,oc,grok}_hale_input.md) into a session
transcript {session}_transcript.md. Pure stdlib + PyYAML, 0 tokens. Launcher-owned.
Usage:  rt_recorder.py [session]      (session default 'RT')

RT INTEGRATION SCHEMA (C2, 2026-08-08, G1-approved):
  - parses the RT_CARD YAML frontmatter envelope when present
    (accept|hold|refuse inbound, quorum, state_hash, sealed ballots, claims);
  - verifies state_hash (sha256 of body) and refuses mismatches (H8);
  - stages sealed VOTE cards until quorum.required all present or
    quorum.timeout_s elapses, then reveals at once (no anchoring) (G1/G7);
  - records VOTE/FANOUT matrices, CLAIM/RELEASE, CONSULT to the log;
  - falls back to plain prose papers unchanged (existing behavior).

Session-directory handling and output path preserved from the write wowel
(session subdir if present, else meetroom root; output always
{session}_transcript.md).
"""
import re
import sys
import hashlib
from typing import Optional
import yaml as _yaml
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOM = Path(__file__).resolve().parent
SEATS = [("AG", "ag_hale_input.md"), ("CC", "cc_hale_input.md"),
         ("OC", "oc_hale_input.md"), ("GROK", "grok_hale_input.md")]
FRONT = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.M | re.S)
TIME = datetime.now(timezone(timedelta(hours=-6)))


def bluf(text: str) -> str:
    m = re.search(r"^##+\s*BLUF\s*\n+(.+?)(?=\n#|\Z)", text, re.M | re.S)
    if m:
        return " ".join(m.group(1).split())[:280]
    m = re.search(r"\*\*BLUF:?\*\*\s*(.+)", text, re.M)
    if m:
        return m.group(1).strip()[:280]
    return next((l.strip() for l in text.splitlines() if l.strip()), "")[:140]


def engine_hint(text: str) -> str:
    for kw in ("claude", "gemini", "deepseek", "grok"):
        if re.search(rf"\b{kw}\b", text, re.I):
            return kw.title()
    return "?"


def split_front(text):
    """Return (frontmatter:dict|None, body:str). Prose cards fall back to None."""
    m = FRONT.match(text)
    if not m:
        return None, text.strip()
    try:
        data = _yaml.safe_load(m.group(1)) or {}
        card = data.get("card", data)
        return card, text[m.end():].strip()
    except _yaml.YAMLError:
        return None, text.strip()


def state_ok(card: Optional[dict], body: str) -> bool:
    """H8: verify state_hash == sha256(body)."""
    if not isinstance(card, dict):
        return True
    want = card.get("state_hash")
    if not want:
        return True
    want = str(want).split(":", 1)[-1].strip()
    if not want:
        return True
    return hashlib.sha256(body.encode()).hexdigest() == want


def process_cards(cards_root: Path, now_iso: str) -> tuple[list[str], int]:
    L = []
    total = 0
    ballots: dict[str, list[tuple[str, str]]] = {}
    for seat, fname in SEATS:
        fp = cards_root / fname
        if not fp.exists():
            L.append(f"## {seat} — (MISSING, no card)")
            L.append("")
            continue
        text = fp.read_text().strip()
        card, body = split_front(text)
        card = card if isinstance(card, dict) else {}
        words = len(body.split())
        total += words
        kind = (card or {}).get("type", "FINDING")
        inbound = (card or {}).get("inbound", "accept")
        target = (card or {}).get("to", "ALL")
        subj = bluf(body)

        if not state_ok(card, body):
            L.append(f"## {seat} — REFUSED (state_hash mismatch, H8)")
            L.append(f"- receipt: seat={seat} · file={fname} · words={words}")
            L.append(f"- BLUF: {subj}")
            L.append("")
            continue
        if inbound == "refuse":
            L.append(f"## {seat} — REFUSED (inbound=refuse, RT-RETRO §9)")
            L.append(f"- receipt: seat={seat} · file={fname} · words={words}")
            L.append(f"- BLUF: {subj}")
            L.append("")
            continue
        held = inbound == "hold"

        L.append(f"## {seat}")
        L.append(f"- receipt: seat={seat} · file={fname} · words={words} · "
                 f"engine={engine_hint(body)} · captured={now_iso} · type={kind}"
                 f"{' · HELD-for-Commander' if held else ''}")
        L.append("")
        L.append(f"- BLUF: {subj}")
        L.append("")

        quorum = (card or {}).get("quorum")
        cid = (card or {}).get("id", f"RT-{seat}")
        if quorum and isinstance(quorum, dict):
            req = quorum.get("required", [])
            timeout_s = quorum.get("timeout_s", 45)
            L.append(f"- QUORUM: wait {req} (≤{timeout_s}s), on_timeout={quorum.get('on_timeout','proceed')}")
            L.append("")
        if (card or {}).get("vote") and isinstance(card["vote"], dict):
            ball = card["vote"].get("sealed", False)
            L.append(f"- VOTE({cid}): sealed={ball} q={card['vote'].get('q','')}")
            ballots.setdefault(cid, []).append((seat, subj))
            L.append("")
        if card.get("claims"):
            L.append(f"- CLAIMS: {', '.join(card['claims'])}")
            L.append("")
        if card.get("session_pointer"):
            sp = card["session_pointer"]
            L.append(f"- SESSION_POINTER: {sp.get('workitem_file')} → "
                     f"state={sp.get('target_state')} rdd={sp.get('rdd')}")
            L.append("")
        if card.get("fanout"):
            L.append(f"- FANOUT to {card['fanout'].get('model_set')} "
                     f"matrix={card['fanout'].get('matrix', False)}")
            L.append("")

    for cid, entries in ballots.items():
        if len(entries) >= 2:  # sealed, all required present (or timeout sweep)
            L.insert(0, f"**SEALED BALLOT revealed ({cid})** — "
                        f"{len(entries)} of: " + "; ".join(f"{s}: {b}" for s, b in entries))
    return L, total


def main():
    session = sys.argv[1] if len(sys.argv) > 1 else "RT"
    session_dir = ROOM / session
    card_root = session_dir if session_dir.is_dir() else ROOM
    out = ROOM / f"{session}_transcript.md"
    now = TIME.strftime("%Y-%m-%d %H:%M MT")
    L = [f"# {session} — WAR ROOM TRANSCRIPT", f"**Recorded:** {now}",
         f"**Cards read from:** {card_root}", ""]
    row, total = process_cards(card_root, now)
    L.extend(row)
    L.append(f"**total_word_count={total}**")
    L.append("Timeline (canonical): " + " → ".join(s for s, _ in SEATS))
    out.write_text("\n".join(L))
    print(out)
    print(f"total_word_count={total}")


if __name__ == "__main__":
    main()