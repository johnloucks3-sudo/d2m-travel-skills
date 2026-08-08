#!/usr/bin/env python3
"""rt_recorder.py — ROUND TABLE transcript recorder (receipts + replay timeline).

Merges per-seat point papers ({ag,cc,oc,grok}_hale_input.md) into a session
transcript {session}_transcript.md. Pure stdlib, 0 tokens. Launcher-owned
(file: OpsCenter/meetroom/rt_recorder.py). Owned by launcher/OC, not a seat.

Usage:  rt_recorder.py [session]      (session default 'RT')

SESSION-DIRECTORY FIX (2026-08-08): confirmed live during Instructor Mode's
first real session (RT-INSTRUCTOR-TEST) — this previously always read cards
from the meetroom ROOT regardless of the `session` argument, so it merged
whatever stale {seat}_hale_input.md files happened to sit at the root (left
over from an unrelated earlier session) instead of the actual session's own
cards in OpsCenter/meetroom/{session}/. If OpsCenter/meetroom/{session}/
exists, cards are now read from there; otherwise falls back to the root
(unchanged behavior for any caller not yet using a session subdirectory).
The output transcript still lands at OpsCenter/meetroom/{session}_transcript.md
(unchanged) so existing links/callers keep working.
"""
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOM = Path(__file__).resolve().parent
SEATS = [("AG", "ag_hale_input.md"), ("CC", "cc_hale_input.md"),
         ("OC", "oc_hale_input.md"), ("GROK", "grok_hale_input.md")]

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

def main():
    session = sys.argv[1] if len(sys.argv) > 1 else "RT"
    session_dir = ROOM / session
    card_root = session_dir if session_dir.is_dir() else ROOM
    out = ROOM / f"{session}_transcript.md"
    now = datetime.now(timezone(timedelta(hours=-6))).strftime("%Y-%m-%d %H:%M MT")
    L = [f"# {session} — WAR ROOM TRANSCRIPT", f"**Recorded:** {now}",
         f"**Cards read from:** {card_root}", ""]
    total = 0
    for seat, fname in SEATS:
        fp = card_root / fname
        if not fp.exists():
            L.append(f"## {seat.title()} — (MISSING, no card)")
            L.append("")
            continue
        text = fp.read_text().strip()
        words = len((" ".join(text.split())).split())
        total += words
        L.append(f"## {seat.title()}")
        L.append(f"- receipt: seat={seat} · file={fname} · words={words} · engine={engine_hint(text)} · captured={now}")
        L.append("")
        L.append(f"- BLUF: {bluf(text)}")
        L.append("")
        rb = re.search(r"^##+\s*REBUTTAL\s*\n+(.+)$", text, re.M | re.S)
        if rb:
            L.append("- REBUTTAL: " + " ".join(rb.group(1).split())[:400])
            L.append("- DISAGREES: yes")
            L.append("")
    L.append(f"**total_word_count={total}**")
    L.append("Timeline (canonical): " + " → ".join(s for s, _ in SEATS))
    out.write_text("\n".join(L))
    print(out)
    print(f"total_word_count={total}")

if __name__ == "__main__":
    main()