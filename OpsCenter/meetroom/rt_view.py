#!/usr/bin/env python3
"""rt_view.py — ROUND TABLE Commander view builder (zero deps).

Reads {cc,ag,oc,grok}_hale_input.md and emits self-contained rt.html with:
  - FULL point-paper text shown (no truncation)
  - clickable links to each seat's source paper + the session transcript
  - color-coded, Commander-paced (SPACE next / view transcript / papers)
Served live at /meetroom/rt.html. Rerun after seats file/update papers, then refresh.

C3 (RT-Interop schema 2026-08-08): reads the RT_CARD frontmatter (when present)
to render a per-card line with type, target, inbound hold/refuse, CLAIM paths,
quorum, sealed-ballot status, fanout matrix, session pointer, and budget route —
so the Commander gets the envelope at a glance, not just the prose.

Usage: rt_view.py [session]   — optional; if OpsCenter/meetroom/{session}/
exists, cards are read from there (same session-directory fix as
rt_recorder.py, 2026-08-08). rt.html always regenerates at the meetroom root
so the existing served URL keeps working regardless of session.
"""
import json, re, sys, hashlib
from pathlib import Path
from datetime import datetime, timezone, timedelta
import yaml as _yaml

FRONT = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.M | re.S)
HERE = Path(__file__).resolve().parent
_session_arg = sys.argv[1] if len(sys.argv) > 1 else ""
_session_dir = HERE / _session_arg if _session_arg else None
CARD_ROOT = _session_dir if (_session_dir and _session_dir.is_dir()) else HERE
SEATS = [
    ("CC",   "cc_hale_input.md",   "#1f6feb", "CC-Hale · Claude (MAX, sonnet)"),
    ("AG",   "ag_hale_input.md",   "#2ea043", "AG-Hale · Gemini 3.6 Flash"),
    ("OC",   "oc_hale_input.md",   "#d29922", "OC-Hale · DeepSeek (Jet)"),
    ("GROK", "grok_hale_input.md", "#f73b9f", "Grok-Hale · xAI (seat pending login)"),
]

def esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))

def split_front(text):
    m = FRONT.match(text)
    if not m:
        return None, text.strip()
    try:
        data = _yaml.safe_load(m.group(1)) or {}
        return (data.get("card", data), text[m.end():].strip())
    except _yaml.YAMLError:
        return None, text.strip()

def envelope_line(card, body) -> tuple[bool, str]:
    """Render envelope meta as an HTML line; False when no frontmatter."""
    if not isinstance(card, dict):
        return False, ""
    bits = []
    bits.append(f"type: <b>{esc(str(card.get('type','FINDING')))}</b>")
    bits.append(f"to: {esc(str(card.get('to','ALL')))}")
    inbound = card.get("inbound", "accept")
    badge = {"accept": '#3fb950', "hold": '#d29922', "refuse": '#f85149'}.get(inbound, '#8b949e')
    bits.append(f"inbound: <span style=\"color:{badge}\">{esc(inbound)}</span>")
    if card.get("route"):
        r = card["route"]
        bits.append(f"route: <b>{esc(str(r.get('lane','auto')))}</b>"
                    f"${r.get('max_budget_cents',0)/100:.2f}/fallback<{esc(str(r.get('fallback_lane','ag')))}")
    if card.get("claims"):
        bits.append(f"claims: <code>{esc(', '.join(card['claims']))}</code>")
    if card.get("vote"):
        v = card["vote"]
        bits.append(f"<b>sealed-ballot:</b> \"{esc(str(v.get('q')))[:60]}\""
                    f"{'' if v.get('sealed', True) else ' (open)'}")
    if card.get("pairing"):
        p = card["pairing"]
        bits.append(f"pairing: {esc(str(p.get('generator')))}→{esc(str(p.get('validator')))}")
    if card.get("state_hash"):
        ok = hashlib.sha256(body.encode()).hexdigest() == str(card["state_hash"]).split(":", 1)[-1].strip()
        badge = "#3fb950" if ok else "#f85149"
        bits.append(f"state_hash: <span style=\"color:{badge}\">{'OK' if ok else 'MISMATCH'}</span>")
    return True, " · ".join(bits)

def explore_heading(text: str) -> str:
    m = re.search(r"^##\s*(.+)", text, re.M)
    return m.group(1).strip()[:120] if m else ""

cards = []
for label, fname, color, who in SEATS:
    fp = CARD_ROOT / fname
    if not fp.exists():
        cards.append({"label": label, "color": color, "who": who, "fname": fname,
                      "present": False, "has_env": False, "envline": "",
                      "body": "(no point paper filed)"})
        continue
    body_txt = fp.read_text().strip()
    card_meta, prose = split_front(body_txt)
    has_env, envline = envelope_line(card_meta, prose)
    cards.append({"label": label, "color": color, "who": who, "fname": fname,
                  "present": True, "has_env": has_env, "envline": envline,
                  "body": body_txt})

papers = sorted({fname for _, fname, *_ in SEATS if (CARD_ROOT / fname).exists()})
transcripts = sorted(p.name for p in HERE.glob("*_transcript.md"))
blufs = sorted(p.name for p in CARD_ROOT.glob("*bluf.md"))

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
 .body{white-space:pre-wrap;font-size:14px;line-height:1.6;color:#c9d1d1;margin-top:10px}
 .env{font-size:12px;color:#8b949e;margin-top:6px;padding-top:6px;border-top:1px dashed #30363d;white-space:normal}
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

# hrefs are relative to rt.html, which always lives at the meetroom root —
# prefix with the session dir name when cards were read from a subdirectory.
_href_prefix = f"{_session_arg}/" if CARD_ROOT != HERE else ""

papers_html = " · ".join(f'<a class="paper" href="{esc(_href_prefix + f)}">{esc(f)}</a>' for f in papers) or "&mdash;"
tr_html = " ".join(f'<a class="paper" href="{esc(f)}">{esc(f)}</a>' for f in transcripts) or "&mdash;"
bl_html = " ".join(f'<a class="paper" href="{esc(_href_prefix + f)}">{esc(f)}</a>' for f in blufs) or "&mdash;"

cards_html = []
for c in cards:
    if c["present"]:
        link = f'<span class="paplink">full paper: <a class="paper" href="{esc(_href_prefix + c["fname"])}">{c["fname"]}</a></span>'
        body = f'<div class="body">{esc(c["body"])}</div>'
    else:
        link = ""
        body = f'<div class="body absent">{esc(c["body"])}</div>'
    env = f'<div class="env">🎛 {c["envline"]}</div>' if c.get("has_env") else ""
    cards_html.append(
        f'<div class="card" style="--c:{c["color"]}">'
        f'<div class="seat">{esc(c["who"])} {link}</div>{body}{env}</div>')

out = (HTML
       .replace("__PAPERS__", papers_html)
       .replace("__TRANSCRIPTS__", tr_html)
       .replace("__BLUFS__", bl_html)
       .replace("__CARDS__", "\n".join(cards_html)))
(HERE / "rt.html").write_text(out)
print(f"built rt.html — {sum(1 for c in cards if c['present'])}/4 papers, {len(out)//1024}KB")