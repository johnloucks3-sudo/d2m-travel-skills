#!/usr/bin/env python3
"""rt_view.py — ROUND TABLE Commander view builder (zero deps).

Reads {cc,ag,oc,grok}_hale_input.md and emits self-contained rt.html with:
  - FULL point-paper text shown (no truncation)
  - clickable links to each seat's source paper + the session transcript
  - color-coded, Commander-paced (SPACE next / view transcript / papers)
Served live at /meetroom/rt.html. Rerun after seats file/update papers, then refresh.
"""
import json, re
from pathlib import Path
from datetime import datetime, timezone, timedelta

HERE = Path(__file__).resolve().parent
SEATS = [
    ("CC",   "cc_hale_input.md",   "#1f6feb", "CC-Hale · Claude (MAX, sonnet)"),
    ("AG",   "ag_hale_input.md",   "#2ea043", "AG-Hale · Gemini 3.6 Flash"),
    ("OC",   "oc_hale_input.md",   "#d29922", "OC-Hale · DeepSeek (Jet)"),
    ("GROK", "grok_hale_input.md", "#f73b9f", "Grok-Hale · xAI (seat pending login)"),
]

def esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))

def explore_heading(text: str) -> str:
    m = re.search(r"^##\s*(.+)", text, re.M)
    return m.group(1).strip()[:120] if m else ""

cards = []
for label, fname, color, who in SEATS:
    fp = HERE / fname
    if not fp.exists():
        cards.append({"label": label, "color": color, "who": who, "fname": fname,
                      "present": False, "body": "(no point paper filed)"})
        continue
    body = fp.read_text().strip()
    cards.append({"label": label, "color": color, "who": who, "fname": fname,
                  "present": True, "body": body})

papers = sorted({fname for _, fname, *_ in SEATS if (HERE / fname).exists()})
transcripts = sorted(p.name for p in HERE.glob("*_transcript.md"))
blufs = sorted(p.name for p in HERE.glob("bluf.md"))

HTML = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ROUND TABLE — War Room</title>
<style>
 body{margin:0 0 70px;font-family:Georgia,serif;background:#0d1117;color:#e6edf3;padding:24px}
 h1{font-size:22px;letter-spacing:.12em;color:#58a6ff;border-bottom:1px solid #30363d;padding-bottom:10px}
 .top{display:flex;flex-wrap:wrap;gap:18px;margin:12px 0 24px;font-size:13px;color:#8b949e}
 .top a{color:#58a6ff}
 .card{border:1px solid #30363d;border-left:7px solid var(--c);border-radius:6px;
       padding:18px 22px;margin:16px 0;background:#161b22}
 .seat{font-weight:bold;letter-spacing:.05em;color:var(--c);font-size:15px;display:flex;justify-content:space-between}
 .paplink{color:#8b949e;font-weight:400;font-size:12px}
 .body{white-space:pre-wrap;font-size:14px;line-height:1.6;color:#c9d1d9;margin-top:10px}
 .absent{color:#f85149}
 .paper{color:#58a6ff;text-decoration:none}
 b,strong{color:#f0f6fc}
</style></head><body>
<h1>ROUND TABLE &mdash; War Room playback</h1>
<div class="top">
  <span>Session papers:</span> __PAPERS__ ·
  <span>transcripts: __TRANSCRIPTS__</span> ·
  <span>previews: __BLUFS__</span>
</div>
__CARDS__
</body></html>"""

papers_html = " · ".join(f'<a class="paper" href="{esc(f)}">{esc(f)}</a>' for f in papers) or "&mdash;"
tr_html = " ".join(f'<a class="paper" href="{esc(f)}">{esc(f)}</a>' for f in transcripts) or "&mdash;"
bl_html = " ".join(f'<a class="paper" href="{esc(f)}">{esc(f)}</a>' for f in blufs) or "&mdash;"

cards_html = []
for c in cards:
    if c["present"]:
        link = f'<span class="paplink">full paper: <a class="paper" href="{c["fname"]}">{c["fname"]}</a></span>'
        body = f'<div class="body">{esc(c["body"])}</div>'
    else:
        link = ""
        body = f'<div class="body absent">{esc(c["body"])}</div>'
    cards_html.append(
        f'<div class="card" style="--c:{c["color"]}">'
        f'<div class="seat">{esc(c["who"])} {link}</div>{body}</div>')

out = (HTML
       .replace("__PAPERS__", papers_html)
       .replace("__TRANSCRIPTS__", tr_html)
       .replace("__BLUFS__", bl_html)
       .replace("__CARDS__", "\n".join(cards_html)))
(HERE / "rt.html").write_text(out)
print(f"built rt.html — {sum(1 for c in cards if c['present'])}/4 papers, {len(out)//1024}KB")