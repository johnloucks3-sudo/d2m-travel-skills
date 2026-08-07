#!/usr/bin/env python3
"""rt_view.py — ROUND TABLE Commander view builder (zero deps).

Reads {cc,ag,oc,grok}_hale_input.md from this dir and emits a self-contained
rt.html: color-coded, BLUF-then-expand cards, SPACE/click advance.
Open rt.html in a browser (file://). No server needed.
"""
import json, re
from pathlib import Path
from datetime import datetime, timezone, timedelta

HERE = Path(__file__).resolve().parent
SEATS = [
    ("cc",   "cc_hale_input.md",   "#1f6feb", "CC-Hale · Claude"),
    ("ag",   "ag_hale_input.md",   "#2ea043", "AG-Hale · Gemini"),
    ("oc",   "oc_hale_input.md",   "#d29922", "OC-Hale · DeepSeek"),
    ("grok", "grok_hale_input.md", "#f73b9f", "Grok-Hale · xAI"),
]

def bluf(text: str) -> str:
    m = re.search(r"^##*\s*BLUF[:\s]*(.+)$", text, re.M | re.I)
    if m:
        return m.group(1).strip()
    first = next((l.strip() for l in text.splitlines() if l.strip()), "")
    return first[:160]

def esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))

cards = []
for seat, fname, color, label in SEATS:
    fp = HERE / fname
    if not fp.exists():
        cards.append({"seat": seat, "color": color, "label": label,
                      "present": False,
                      "bluf": "(no card filed — seat deferred)",
                      "body": "This seat has not filed a card yet."})
        continue
    body = fp.read_text().strip()
    cards.append({"seat": seat, "color": color, "label": label,
                  "present": True, "bluf": bluf(body), "body": body})

data = {
    "session": "Round Table v0 — Commander view",
    "built": datetime.now(timezone(timedelta(hours=-6))).strftime("%Y-%m-%d %H:%M MT"),
    "present": sum(1 for c in cards if c["present"]),
    "cards": cards,
}

HTML = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ROUND TABLE</title>
<style>
 body{margin:0 0 80px;font-family:Georgia,serif;background:#0d1117;color:#e6edf3;padding:24px}
 h1{font-size:20px;letter-spacing:.12em;color:#58a6ff;border-bottom:1px solid #30363d;padding-bottom:8px}
 .meta{color:#8b949e;font-size:12px;margin:10px 0 18px}
 .card{border:1px solid #30363d;border-left:6px solid var(--c);border-radius:6px;
       padding:16px 18px;margin:14px 0;background:#161b22;display:none}
 .card.active{display:block}
 .seat{font-weight:bold;font-size:13px;letter-spacing:.04em;color:var(--c)}
 .bluf{font-size:16px;font-weight:bold;color:#f0f6fc;margin:8px 0 4px;border-left:2px solid rgba(255,255,255,.18);padding-left:12px;cursor:pointer}
 .hint{color:#8b949e;font-size:11px;margin-left:12px;font-weight:400}
 .body{white-space:pre-wrap;font-size:13px;line-height:1.55;color:#c9d1d9;margin-top:10px;display:none}
 .body.open{display:block}
 .bar{position:fixed;bottom:0;left:0;right:0;background:#161b22;border-top:1px solid #30363d;
      padding:12px 24px;font-size:12px;color:#8b949e;display:flex;gap:26px;align-items:center}
 .kbd{border:1px solid #30363d;border-radius:4px;padding:1px 7px;background:#0d1117}
 #pos{font-weight:bold;color:#e6edf3}
</style></head><body>
<h1>ROUND TABLE &mdash; play-by-play</h1>
<div class="meta">__META__</div>
<div id="deck"></div>
<div class="bar">
 <span><span class="kbd">SPACE</span> next card</span>
 <span><span class="kbd">P</span> previous</span>
 <span><span class="kbd">E</span> expand / collapse card</span>
 <span id="pos"></span>
</div>
<script>
const DATA=__DATA__;
const esc=s=>String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
const deck=document.getElementById('deck');
let i=-1;
DATA.cards.forEach(c=>{
  const el=document.createElement('div');
  el.className='card';
  el.style.setProperty('--c',c.color);
  el.dataset.seat=c.seat;
  const absent=c.present?'':' <span style="color:#f85149">(absent)</span>';
  el.innerHTML=
    '<div class="seat">'+esc(c.label)+absent+'</div>'+
    '<div class="bluf">'+(c.present?'':'<span class="hint">expand &raquo;</span> ')+esc(c.bluf)+'</div>'+
    '<div class="body">'+esc(c.body)+'</div>';
  el.querySelector('.bluf').addEventListener('click',()=>toggleBody(el));
  el.querySelector('.body').addEventListener('click',()=>toggleBody(el));
  deck.appendChild(el);
});
function toggleBody(el){const b=el.querySelector('.body');b.classList.toggle('open')}
function show(n){
  i=(n+DATA.cards.length)%DATA.cards.length;
  document.querySelectorAll('.card').forEach(c=>c.classList.remove('active'));
  document.querySelectorAll('.card')[i].classList.add('active');
  document.getElementById('pos').textContent='card '+(i+1)+' of '+DATA.cards.length;
}
show(0);
document.addEventListener('keydown',e=>{
  if(e.code==='Space'){show(i+1);e.preventDefault()}
  else if(e.key==='p'||e.key==='P'){show(i-1)}
  else if(e.key==='e'||e.key==='E'){
    const el=document.querySelector('.card.active .body'); if(el)el.classList.toggle('open');
  }
});
</script></body></html>"""

meta = (f"{data['session']} &mdash; {data['built']} &nbsp;·&nbsp; "
        f"{data['present']} of 4 seats filed")
out = (HTML.replace("__DATA__", json.dumps(data).replace("</", "<\\u002F"))
           .replace("__META__", meta))

target = HERE / "rt.html"
target.write_text(out)
print(f"built {target} — {data['present']}/4 seats, {len(out)//1024}KB")