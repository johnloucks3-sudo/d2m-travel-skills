#!/usr/bin/env python3
"""generate_rt_bluf.py — War Room BLUF pre-brief sheet (0-token extract).

Reads per-seat point papers ({ag,cc,oc,grok}_input.md) and emits a ≤150-word
one-page BLUF sheet so the Commander is oriented BEFORE the playback deck opens
(CC-Hale RT-RETRO #2). Pure text extract — no model inference, 0 tokens.

Usage:
  generate_rt_bluf.py [session_dir] [out.md]
    defaults: session_dir = OpsCenter/meetroom, out = {session_dir}/bluf.md
"""
import re, sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

SEATS = [("CC", "cc_input.md"), ("AG", "ag_input.md"),
         ("OC", "oc_input.md"), ("Grok", "grok_input.md")]

def extract_bluf(text: str) -> str:
    m = re.search(r"^##+\s*BLUF\s*\n+(.+?)(?=\n#|\Z)", text, re.M | re.S)
    if m:
        line = " ".join(m.group(1).split())
        return (line[:280] + "…") if len(line) > 280 else line
    first = next((l.strip() for l in text.splitlines() if l.strip()), "")
    return first[:140]

def main() -> int:
    MT = timezone(timedelta(hours=-6))
    here = Path(__file__).resolve().parents[1] / "OpsCenter" / "meetroom"
    room = Path(sys.argv[1]) if len(sys.argv) > 1 else here
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else room / "bluf.md"
    lines, words = [], 0
    lines.append(f"# War Room BLUF (pre-brief) · {datetime.now(MT).strftime('%Y-%m-%d %H:%M MT')}")
    lines.append("")
    for label, _ in SEATS:
        cands = sorted(room.glob(f"{label.lower()}*_input.md"))
        if not cands:
            lines.append(f"- **{label}:** (no card)")
            continue
        fp = cands[0]
        b = extract_bluf(fp.read_text().strip())
        lines.append(f"- **{label}:** {b}")
        words += len(b.split())
    lines.append("")
    lines.append(f"_Composite ≤ {words} words._")
    out.write_text("\n".join(lines))
    print(f"wrote {out} ({words} words)")
    return 0

if __name__ == "__main__":
    sys.exit(main())