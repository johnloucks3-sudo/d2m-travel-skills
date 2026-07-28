#!/usr/bin/env python3
"""
Zero-Latitude pipeline build — Furlow / Ely-Darrow / Nichols
Regent Seven Seas Grandeur · Storied Scandinavia · Aug 29 – Sep 8, 2026
MISSION-618 rebuild. All images verified (HTTP 200 + viewed) and base64-embedded.
Brand hexes per docs/ITINERARY_BRAND_SPEC.md (gold #c8a400; no rgba text colors).
"""
import base64, os, html

IMG_DIR = "/home/john/Thunderbird/output/grandeur_baltic_imgs"
OUT_DIR = "/home/john/Thunderbird/cruises_web"

# ---- verified image set (each used at most ONCE per document) --------------
IMG_FILES = {
    "ship":        ("ship_grandeur.jpg",     "Regent Seven Seas Grandeur (Wikimedia Commons, File:Regent Seven Seas Grandeur (53824101578).jpg) — VIEWED: ship with 'SEVEN SEAS GRANDEUR' on hull"),
    "stockholm":   ("stockholm.jpg",         "Wikimedia Commons File:Skeppsbron june 2013.jpg — VIEWED: Stockholm Skeppsbron/Gamla Stan waterfront at dusk"),
    "berlin":      ("berlin.jpg",            "Wikimedia Commons File:Brandenburg Gate - Brandenburger Tor - Berlin - Germany - 02.jpg — VIEWED: Brandenburg Gate with Quadriga"),
    "copenhagen":  ("copenhagen.jpg",        "Wikimedia Commons File:2018 - Nyhavn on sunset.jpg — VIEWED: Copenhagen Nyhavn canal, colorful townhouses"),
    "kristiansand":("kristiansand_pose.jpg", "Wikimedia Commons File:Posebyen i Kristiansand.jpg — VIEWED: Kristiansand Posebyen old-town timber houses"),
    "oslo":        ("oslo_b.jpg",            "Wikimedia Commons File:Oslo Opera house exterior in 2010.jpg — VIEWED: Oslo Opera House exterior"),
}

def data_uri(fname):
    with open(os.path.join(IMG_DIR, fname), "rb") as f:
        return "data:image/jpeg;base64," + base64.b64encode(f.read()).decode()

IMG = {k: (data_uri(v[0]), v[1]) for k, v in IMG_FILES.items()}

def data_uri_png(fname):
    with open(os.path.join(IMG_DIR, fname), "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()

# D2M brand logo (Wikimedia n/a — this is D2M's own asset, VIEWED: Dreams2Memories wordmark + ship + tagline), base64 for self-containment
D2M_LOGO = data_uri_png("d2m_logo.png")

# ---- CSS (brand-spec exact) -------------------------------------------------
CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: Georgia, 'Times New Roman', serif;
  background-color: #07076b;        /* spec: navy base */
  color: #e8f1ff;                   /* spec: primary body text */
  padding: 28px 12px;
  -webkit-print-color-adjust: exact; print-color-adjust: exact;
}
.page { max-width: 940px; margin: 0 auto; background-color: #05053f;
  border: 1px solid rgba(200,164,0,.25); border-radius: 10px; overflow: hidden; }

.hero { text-align: center; padding: 34px 20px 22px;
  background: linear-gradient(180deg,#04041b 0%,#07076b 100%); }
.hero .logo { width: 74px; height: auto; margin-bottom: 12px; }
.wordmark { color: #f0f6ff; font-size: 13px; letter-spacing: 3px; font-weight: bold; }
.voyage-title { font-size: 28px; font-weight: 400; color: #f7f3ea; margin-top: 14px; letter-spacing: 1.2px; }
.voyage-sub { font-size: 14px; color: #c8dcff; margin-top: 8px; font-style: italic; }

.ship-profile { background: rgba(200,164,0,.05);
  border-bottom: 1px solid rgba(200,164,0,.2); padding: 22px 24px; display: flex; gap: 22px; align-items: center; }
.ship-profile img { width: 300px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,.35); object-fit: cover; }
.ship-text { flex: 1; }
.ship-text h2 { font-size: 21px; color: #c8dcff; font-weight: 400; margin-bottom: 8px; }
.ship-text p { font-size: 13px; line-height: 1.55; color: #e8f1ff; margin-bottom: 12px; }
.ship-stats { display: flex; gap: 10px; font-size: 11px; color: #a8c4f0; flex-wrap: wrap; }
.ship-stats span { background: rgba(255,255,255,.05); padding: 4px 8px; border-radius: 4px; }

.stats-bar { background: rgba(0,0,0,.4); border-bottom: 1px solid rgba(200,164,0,.25);
  padding: 16px 24px; display: flex; justify-content: space-around; flex-wrap: wrap; gap: 16px; }
.stat { text-align: center; }
.stat-val { font-size: 22px; color: #c8a400; font-weight: bold; }   /* spec gold */
.stat-lbl { font-size: 10px; color: #a8c4f0; text-transform: uppercase; letter-spacing: 1px; margin-top: 2px; }

.ck-bar { background: rgba(200,164,0,.08); padding: 12px 24px; display: flex;
  justify-content: space-between; flex-wrap: wrap; gap: 6px; font-size: 12px; color: #c8dcff;
  border-bottom: 1px solid rgba(200,164,0,.2); }
.ck-bar b { color: #f7f3ea; }

/* Route map */
.route-wrap { padding: 22px 24px 6px; }
.route-title { font-size: 12px; letter-spacing: 2.5px; text-transform: uppercase; color: #c8a400;
  font-weight: 600; text-align: center; margin-bottom: 10px; }
.route-svg { width: 100%; height: auto; display: block; }

.sec-header { background: rgba(200,164,0,.08); border-top: 1px solid rgba(200,164,0,.25);
  border-bottom: 1px solid rgba(200,164,0,.25); padding: 14px 24px; font-size: 12px;
  text-transform: uppercase; letter-spacing: 2.5px; color: #c8a400; font-weight: 600;
  margin-top: 20px; }

.itinerary-container { padding: 16px; display: flex; flex-direction: column; gap: 14px; }
.day-card { background: #08083a; border: 1px solid rgba(255,255,255,.06); border-radius: 8px; overflow: hidden; }
.day-card.embark { border-left: 3px solid #c8a400; }
.day-card.sea { background: #06062e; }
.card-main { display: flex; }
.card-left { width: 74px; flex-shrink: 0; text-align: center; padding: 14px 6px;
  border-right: 1px solid rgba(255,255,255,.05); }
.day-num { font-size: 26px; color: #c8a400; font-weight: bold; line-height: 1; }   /* spec gold */
.day-dow { font-size: 11px; color: #c8dcff; margin-top: 6px; }                       /* spec muted */
.date-mon { font-size: 10px; color: #a8c8ff; text-transform: uppercase; letter-spacing: 1px; margin-top: 6px;
  border-top: 1px solid rgba(255,255,255,.1); padding-top: 6px; }                     /* spec: date-mon only */
.date-day { font-size: 18px; color: #e8f1ff; font-weight: bold; margin-top: 2px; }
.card-content { flex: 1; padding: 14px 18px; }
.port-header { display: flex; align-items: center; gap: 8px; margin-bottom: 5px; }
.port-flag { font-size: 20px; }
.port-name { font-size: 16px; font-weight: 600; color: #f7f3ea; }                     /* spec off-white */
.port-sub { font-size: 11px; color: #a8c4f0; margin-bottom: 10px; }                   /* spec muted */
.note-text { font-size: 12.5px; color: #c8dcff; font-style: italic; line-height: 1.5; margin-bottom: 8px; }
.tag { display: inline-block; font-size: 9px; letter-spacing: 1px; text-transform: uppercase;
  padding: 2px 7px; border-radius: 4px; margin-left: 6px; vertical-align: middle;
  background: rgba(200,164,0,.16); color: #c8a400; font-weight: 600; }
.tag.dock { background: rgba(168,196,240,.14); color: #a8c4f0; }

.exc-block, .dining-block { background: rgba(255,255,255,.03); border-radius: 6px;
  padding: 8px 12px; margin-bottom: 7px; border-left: 2px solid #c8a400; }
.dining-block { border-left-color: #8fa8d8; }
.block-lbl { font-size: 9px; letter-spacing: 1px; text-transform: uppercase; color: #c8a400; font-weight: 600; }
.dining-block .block-lbl { color: #a8c4f0; }
.block-val { font-size: 13px; color: #e8f1ff; margin-top: 2px; }
.block-time { font-size: 11px; color: #c8a400; }
.celebrate { background: rgba(200,164,0,.12); border: 1px solid rgba(200,164,0,.35);
  border-radius: 6px; padding: 8px 12px; margin-bottom: 7px; font-size: 12.5px; color: #f7f3ea; }

.card-images { width: 230px; flex-shrink: 0; border-left: 1px solid rgba(255,255,255,.05); }
.card-images img { width: 100%; height: 100%; min-height: 150px; object-fit: cover; display: block; }

details.intel { border-top: 1px solid rgba(255,255,255,.05); background: rgba(0,0,0,.15); }
details.intel summary { padding: 11px 18px; font-size: 11px; color: #c8a400; text-transform: uppercase;
  letter-spacing: 1px; cursor: pointer; font-weight: 500; }
details.intel .intel-content { padding: 4px 18px 18px; font-size: 12.5px; line-height: 1.6; color: #e8f1ff; }
.intel-tag { display: inline-block; background: rgba(200,164,0,.15); color: #c8a400; padding: 2px 6px;
  border-radius: 4px; font-size: 10px; font-weight: 600; margin-right: 6px; text-transform: uppercase; }
.intel-content .row { margin-bottom: 12px; }

.open-section { border-top: 3px solid #c8a400; margin-top: 26px; background-color: #05052a; }
.open-hdr { background: rgba(200,164,0,.1); padding: 14px 24px; font-size: 13px; font-weight: 600;
  text-transform: uppercase; letter-spacing: 1.5px; color: #c8a400; border-bottom: 1px solid rgba(200,164,0,.2); }
.open-item { display: flex; align-items: center; gap: 14px; padding: 13px 24px;
  border-bottom: 1px solid rgba(255,255,255,.05); font-size: 12.5px; }
.open-icon { font-size: 18px; }
.open-info { flex: 1; }
.open-title { font-weight: 600; color: #f7f3ea; margin-bottom: 3px; }
.open-desc { color: #c8dcff; }
.open-status { font-size: 9px; font-weight: bold; background: rgba(200,164,0,.22); color: #c8a400;
  padding: 4px 8px; border-radius: 4px; text-transform: uppercase; }

.footer { background: #04041a; padding: 28px; text-align: center; font-size: 12px; color: #8fa8d8;
  border-top: 1px solid rgba(255,255,255,.1); }
.footer .fco { color: #c8a400; letter-spacing: 2px; font-weight: 600; margin-bottom: 8px; }
.footer a { color: #a8c4f0; text-decoration: none; }

@media (max-width: 768px) {
  .ship-profile { flex-direction: column; text-align: center; }
  .ship-profile img { width: 100%; max-width: 340px; }
  .card-main { flex-direction: column; }
  .card-left { width: 100%; border-right: none; border-bottom: 1px solid rgba(255,255,255,.05);
    display: flex; gap: 12px; justify-content: center; align-items: center; }
  .date-mon { border-top: none; padding-top: 0; }
  .card-images { width: 100%; }
  .card-images img { min-height: 190px; }
}
"""

# ---- route map (inline SVG; self-contained; not a raster asset) ------------
def route_map():
    # approximate relative geography, W→E / N→S stylized
    nodes = [
        ("Stockholm", 780, 70),
        ("Warnemünde·Berlin", 560, 340),
        ("Copenhagen", 470, 250),
        ("Kristiansand", 210, 175),
        ("Oslo", 175, 80),
    ]
    order = [0,1,2,3,4]
    pts = " ".join(f"{nodes[i][1]},{nodes[i][2]}" for i in order)
    dots = ""
    for name,x,y in nodes:
        anchor = "start" if x < 400 else ("end" if x > 700 else "middle")
        dx = 12 if anchor=="start" else (-12 if anchor=="end" else 0)
        ty = y - 14 if name.startswith("Copenhagen") else y + 4   # lift Copenhagen label off its node
        dots += (f'<circle cx="{x}" cy="{y}" r="7" fill="#c8a400" stroke="#07076b" stroke-width="2"/>'
                 f'<text x="{x+dx}" y="{ty}" fill="#e8f1ff" font-size="17" font-family="Georgia,serif" '
                 f'text-anchor="{anchor}">{name}</text>')
    return f'''<div class="route-wrap"><div class="route-title">&#9973; Voyage Route &middot; Stockholm to Oslo</div>
<svg class="route-svg" viewBox="0 0 900 410" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Voyage route map">
<rect x="0" y="0" width="900" height="410" fill="#04041b" rx="10"/>
<polyline points="{pts}" fill="none" stroke="#c8a400" stroke-width="2.5" stroke-dasharray="8 6" opacity="0.85"/>
{dots}
<text x="450" y="398" fill="#8fa8d8" font-size="12" font-family="Georgia,serif" text-anchor="middle">
Five ports &middot; two overnights in Stockholm &middot; two in Copenhagen &middot; overnight in Oslo &middot; all alongside (dock)</text>
</svg></div>'''

# ---- port intel (Stage 2: grounded in on-file port_data + factbook intel) --
PORT_INTEL = {
 "stockholm": ("Stockholm, Sweden",
   "The “Venice of the North,” Stockholm spreads across fourteen islands where Lake Mälar meets the Baltic — the largest and one of the most beautiful capitals in Scandinavia, laced with broad waterways, waterside parks and pedestrian lanes. The medieval heart, Gamla Stan, folds around the Royal Palace and the graceful Riddarholm Church, while the island of Djurgården holds the crown jewel: the Vasa Museum, home to the almost fully intact 64-gun warship that sank on her maiden voyage in 1628 and was raised three centuries later. Two nights in port let this storied city unfold at an unhurried pace.",
   "Sweden · Swedish (English widely spoken) · Swedish krona (SEK). Temperate summer climate. Extremely safe; credit cards accepted everywhere. Ship berths alongside (Frihamnen/Stadsgården) — no tender.",
   "port_data notes + Regent destination copy (on file) + factbook intel"),
 "berlin": ("Warnemünde · Gateway to Berlin, Germany",
   "Warnemünde is Germany’s handsome Baltic seaside resort at the mouth of the Warnow — wide sand beaches, a candy-striped lighthouse, and the old fishing quarter of the Alter Strom. It is also the sea gateway to Berlin, roughly three hours south by rail or coach, where the Brandenburg Gate, Museum Island, and the layered memory of the twentieth century await. Closer to the pier, the Hanseatic city of Rostock offers medieval brick-Gothic churches, the Kröpetiner Tor, and centuries of maritime trade.",
   "Germany · German (English common) · Euro (EUR). Mild Baltic summer. Very safe. Ship berths alongside at Warnemünde cruise pier — no tender; Berlin excursions depart directly from the quay.",
   "port_data notes + established landmark fact + factbook intel"),
 "copenhagen": ("Copenhagen, Denmark",
   "Once a Viking harbor and later a great northern power, Copenhagen has become one of Europe’s most liveable capitals — a city of copper spires, canal quarters and easy bicycles. The postcard is Nyhavn, the seventeenth-century canal lined with lacquered gabled houses, wooden ships and open-air cafes. Beyond it lie the royal palace of Amalienborg, the pleasure gardens of Tivoli, the harbor-side Little Mermaid, and a food scene that helped rewrite Nordic cuisine. Two nights alongside give time for both the icons and the quiet courtyards.",
   "Denmark · Danish (English predominant second language) · Danish krone (DKK). Temperate, mild summers. Extremely safe; card-friendly. Ship berths alongside (Langelinie/Oceankaj) — no tender.",
   "port_data notes + established landmark fact + factbook intel"),
 "kristiansand": ("Kristiansand, Norway",
   "Kristiansand is southern Norway’s sun-favored coastal town, laid out on a Renaissance grid by King Christian IV in 1641. Its treasure is Posebyen, one of northern Europe’s best-preserved quarters of white-painted timber houses, threaded with quiet lanes and flowering gardens. Add a lively fish market, the skerry-dotted coastline, and the wooded hills of Baneheia, and this softer-tempo call is a gentle, walkable pleasure after the grand capitals.",
   "Norway · Norwegian (English widely spoken) · Norwegian krone (NOK). Cool, temperate coast. Extremely safe. Ship berths alongside at the town quay — no tender; the old town is a short, level walk.",
   "port_data notes + established landmark fact + factbook intel"),
 "oslo": ("Oslo, Norway",
   "Norway’s capital sits at the head of its own long fjord, framed by forested hills and dotted with islands — a city where Viking heritage meets bold contemporary design. The waterfront Opera House rises from the harbor like a glacier you can walk up; nearby, the Viking Ship and Fram polar-exploration museums, the sculpture-filled Vigeland Park, and the Munch collection tell Norway’s story. An overnight in port lets the long northern evening linger.",
   "Norway · Norwegian (English widely spoken) · Norwegian krone (NOK). Temperate coastal summer. Extremely safe; card-friendly. Ship berths alongside in the harbor — no tender; central sights are close by.",
   "port_data notes + established landmark fact + factbook intel"),
}

def intel_block(key):
    title, romance, info, src = PORT_INTEL[key]
    return (f'<details class="intel"><!-- source: {html.escape(src)} -->'
            f'<summary>&#128214; Expand &mdash; {html.escape(title)}</summary>'
            f'<div class="intel-content">'
            f'<div class="row"><span class="intel-tag">Destination</span>{html.escape(romance)}</div>'
            f'<div class="row"><span class="intel-tag">Port Info</span>{html.escape(info)}</div>'
            f'</div></details>')

# ---- day-card rendering -----------------------------------------------------
def esc(s): return html.escape(str(s))

def card(day):
    cls = "day-card " + day.get("cls", "")
    numstyle = day.get("numstyle", "")
    left = ('<div class="card-left"><div class="day-num" style="' + numstyle + '">' + str(day["num"]) + '</div>'
            '<div class="day-dow">' + esc(day["dow"]) + '</div>'
            '<div class="date-mon">' + esc(day["mon"]) + '</div>'
            '<div class="date-day">' + esc(day["dd"]) + '</div></div>')
    tag = day.get("tag", "")
    content = ('<div class="card-content"><div class="port-header"><span class="port-flag">' + day["flag"] + '</span>'
               '<span class="port-name">' + esc(day["name"]) + '</span>' + tag + '</div>')
    if day.get("sub"): content += '<div class="port-sub">' + esc(day["sub"]) + '</div>'
    if day.get("note"): content += '<div class="note-text">' + esc(day["note"]) + '</div>'
    if day.get("celebrate"): content += '<div class="celebrate">' + day["celebrate"] + '</div>'
    for ex in day.get("exc", []):
        content += ('<div class="exc-block"><div class="block-lbl">&#9973; Shore Excursion</div>'
                    '<div class="block-val">' + esc(ex[0]) + '</div>'
                    + ('<div class="block-time">' + esc(ex[1]) + '</div>' if ex[1] else "") + '</div>')
    for dn in day.get("dining", []):
        content += ('<div class="dining-block"><div class="block-lbl">&#127860; Specialty Dining</div>'
                    '<div class="block-val">' + esc(dn[0]) + '</div>'
                    + ('<div class="block-time">' + esc(dn[1]) + '</div>' if dn[1] else "") + '</div>')
    content += '</div>'
    img = ""
    if day.get("img"):
        uri, comment = IMG[day["img"]]
        img = '<div class="card-images"><!-- ' + html.escape(comment) + ' --><img src="' + uri + '" alt="' + esc(day["name"]) + '"></div>'
    inner = '<div class="card-main">' + left + content + img + '</div>'
    if day.get("intel"): inner += intel_block(day["intel"])
    return '<div class="' + cls + '">' + inner + '</div>'

# ---- per-couple itinerary data ---------------------------------------------
def build_days(c):
    ex = c["exc"]          # dict date->list of (name,time)
    def E(dkey): return ex.get(dkey, [])
    days = []
    # Pre-cruise
    days.append(dict(cls="", num="&mdash;", numstyle="font-size:16px", dow="Wed", mon="Aug", dd="26",
        flag="&#9992;&#65039;", name="DFW → Helsinki", sub=c["out1"],
        note="Your Scandinavian journey begins in Business Class across the Atlantic — relax, and toast the historic horizons ahead."))
    days.append(dict(cls="", num="&mdash;", numstyle="font-size:16px", dow="Thu", mon="Aug", dd="27",
        flag="&#9992;&#65039;", name="Helsinki → Stockholm · At Six", sub=c["out2"],
        note="Arrive in Stockholm and transfer privately to the stylish Hotel At Six for your first evening in the Swedish capital."))
    days.append(dict(cls="", num="&mdash;", numstyle="font-size:16px", dow="Fri", mon="Aug", dd="28",
        flag="&#127976;", name="At Six Stockholm", sub="Regent-included hotel night",
        note="A second unhurried night at At Six before embarkation — no room change, breakfast included."))
    # Day 1 embark Stockholm
    d1 = dict(cls="embark", num="1", dow="Sat", mon="Aug", dd="29",
        flag="&#128674;", name="Stockholm — Embarkation", tag='<span class="tag dock">Dock</span>',
        sub="Board Seven Seas Grandeur · overnight in port", img="stockholm", intel="stockholm",
        note="Step aboard your suite home and settle in; the ship stays overnight, so the city is yours this evening.",
        exc=E("aug29"), dining=E("aug29d"))
    if c.get("heidi_bday"):
        d1["celebrate"] = "&#127874; Happy Birthday, Heidi &mdash; embarkation day! We will make sure the crew knows."
    days.append(d1)
    # Day 2 Stockholm
    days.append(dict(cls="", num="2", dow="Sun", mon="Aug", dd="30",
        flag="&#128674;", name="Stockholm", tag='<span class="tag dock">Dock</span>',
        sub="Full day in port", note="A full day for Gamla Stan, the Vasa, and the waterfront before sailing.",
        exc=E("aug30"), dining=E("aug30d")))
    # Day 3 Sea
    d3 = dict(cls="sea", num="3", dow="Mon", mon="Aug", dd="31",
        flag="&#127774;", name="At Sea", sub="Baltic Sea",
        note="A restful day at sea — spa, Culinary Arts Kitchen, or a quiet balcony morning.", exc=E("aug31"), dining=E("aug31d"))
    if c.get("amy_bday"):
        d3["celebrate"] = "&#127874; Happy Birthday, Amy &mdash; celebrated at sea today. A special touch is arranged onboard."
    days.append(d3)
    # Day 4 Warnemunde/Berlin
    days.append(dict(cls="", num="4", dow="Tue", mon="Sep", dd="1",
        flag="&#128643;", name="Warnemünde · Berlin", tag='<span class="tag dock">Dock</span>',
        sub="Gateway to Berlin", img="berlin", intel="berlin",
        note="Alongside at Warnemünde — the marquee day-trip to Berlin, or the Hanseatic charm of Rostock closer to the pier.",
        exc=E("sep1"), dining=E("sep1d")))
    # Day 5 Warnemunde day2
    days.append(dict(cls="", num="5", dow="Wed", mon="Sep", dd="2",
        flag="&#128643;", name="Warnemünde · Rostock", tag='<span class="tag dock">Dock</span>',
        sub="Second day in port", note="A second day on the German Baltic coast at an easier pace.",
        exc=E("sep2"), dining=E("sep2d")))
    # Day 6 Copenhagen
    days.append(dict(cls="", num="6", dow="Thu", mon="Sep", dd="3",
        flag="&#128674;", name="Copenhagen — Arrival", tag='<span class="tag dock">Dock</span>',
        sub="Overnight in port", img="copenhagen", intel="copenhagen",
        note="Arrive in the Danish capital; the ship stays the night, so Nyhavn and Tivoli glow into the evening.",
        exc=E("sep3"), dining=E("sep3d")))
    # Day 7 Copenhagen day2
    days.append(dict(cls="", num="7", dow="Fri", mon="Sep", dd="4",
        flag="&#128674;", name="Copenhagen", tag='<span class="tag dock">Dock</span>',
        sub="Full day in port", note="A full second day for palaces, gardens and canal-side cafes.",
        exc=E("sep4"), dining=E("sep4d")))
    # Day 8 Sea
    days.append(dict(cls="sea", num="8", dow="Sat", mon="Sep", dd="5",
        flag="&#127774;", name="At Sea", sub="Skagerrak",
        note="A relaxed crossing toward the Norwegian coast.", exc=E("sep5"), dining=E("sep5d")))
    # Day 9 Kristiansand (portal-anchored Sep 6; clock times TBD)
    days.append(dict(cls="", num="9", dow="Sun", mon="Sep", dd="6",
        flag="&#128674;", name="Kristiansand", tag='<span class="tag dock">Dock</span>',
        sub="Southern Norway · arrival/departure times to be confirmed", img="kristiansand", intel="kristiansand",
        note="A gentle, walkable call — the white timber lanes of Posebyen are steps from the quay.",
        exc=E("sep6"), dining=E("sep6d")))
    # Day 10 Oslo
    days.append(dict(cls="", num="10", dow="Mon", mon="Sep", dd="7",
        flag="&#128674;", name="Oslo — Arrival", tag='<span class="tag dock">Dock</span>',
        sub="Overnight in port", img="oslo", intel="oslo",
        note="Sail up the Oslofjord to Norway’s capital; overnight in port before disembarkation.",
        exc=E("sep7"), dining=E("sep7d")))
    # Day 11 disembark
    days.append(dict(cls="embark", num="11", dow="Tue", mon="Sep", dd="8",
        flag="&#9992;&#65039;", name="Oslo → London → Dallas", sub=c["ret"],
        note="Disembark in Oslo; Regent transfers you to the airport for your Business-Class flights home. Safe travels — and thank you."))
    return days

# ---- couples ----------------------------------------------------------------
DINING = {  # shared, all three couples
 "aug30d":[("Pacific Rim","Aug 30 · 18:30")],
 "sep2d":[("Chartreuse","Sep 2 · 19:30")],
 "sep4d":[("Prime 7","Sep 4 · 18:30")],
}

COUPLES = {
 "furlow": dict(
   title="John &amp; Melissa Furlow", res="3071222", suite="Suite 827 · Concierge Suite D · Deck 8",
   ck="Paid in Full · Seven Seas Society: Gold",
   out1="AA 9018 (Finnair) · 4:50 PM → 10:45 AM +1 · PNR CKZHXA / BB4X94",
   out2="AY 811 · 1:15 PM · private transfer to At Six Stockholm",
   ret="BA 6776 (John 4C, Missy 4A) · AA 79 (John 7D, Missy 7G) · Regent airport transfer",
   nights=10, ports=5, exc_count=6,
   exc={**DINING,
     "aug30":[("Highlights of Stockholm & Vasa Museum","Aug 30 · 09:00")],
     "sep1":[("SG – The Berlin Experience","Sep 1 · 07:30")],
     "sep2":[("Amazing Rostock","Sep 2 · 09:00")],
     "sep3":[("A Tour of Two Kingdoms – Denmark to Sweden","Sep 3 · 08:45")],
     "sep6":[("Explore Kristiansand on Foot","Sep 6 · time TBC")],
     "sep7":[("Hadeland Glass Works & Fram Museum","Sep 7 · 09:30")],
   },
   open_items=[
     ("&#128203;","Online check-in opens Aug 8, 2026","Complete on the Regent guest portal once open."),
     ("&#128652;","Airport transfer (ARN &rarr; At Six)","Confirmed on hold; balance due Aug 16, 2026."),
     ("&#9992;&#65039;","Helsinki &rarr; Stockholm seats","Seat numbers being finalized with the airline."),
   ]),
 "elydarrow": dict(
   title="Al Ely &amp; Amy Darrow", res="3096289", suite="Suite 961 · Deck 9",
   ck="Paid in Full",
   out1="AA 9018 (Finnair) · Al 2H, Amy 2D · 4:50 PM → 10:45 AM +1 · PNR UXVXZP",
   out2="AY 811 · 1:15 PM · private transfer to At Six Stockholm",
   ret="BA 6776 (Al 2C, Amy 2A) · AA 79 (Al 3G, Amy 3D) · Regent airport transfer",
   nights=10, ports=5, exc_count=6, amy_bday=True,
   exc={**DINING,
     "aug30":[("GG – Swedish Nature Experience","Aug 30 · 10:30")],
     "sep1":[("Amazing Rostock","Sep 1 · 09:00")],
     "sep2":[("Medieval Flavors of Rostock","Sep 2 · 14:30")],
     "sep3":[("Christiansborg Palace & Tivoli Gardens","Sep 3 · 13:30")],
     "sep4":[("A Tour of Two Kingdoms – Denmark to Sweden","Sep 4 · 09:00")],
     "sep7":[("Oslo During World War II","Sep 7 · 09:00")],
   },
   open_items=[
     ("&#128203;","Online check-in opens Aug 8, 2026","Complete on the Regent guest portal once open."),
     ("&#128652;","Airport transfer (ARN &rarr; At Six)","Confirmed on hold; balance due Aug 16, 2026."),
     ("&#128221;","Guest profile forms","A quick return of your guest forms wraps up pre-boarding."),
   ]),
 "nichols": dict(
   title="Larry &amp; Heidi Nichols", res="3078056", suite="Suite 939 · Concierge Suite D · Deck 9",
   ck="Paid in Full",
   out1="AA 9018 (Finnair) · Larry 5D, Heidi 5H · 4:50 PM → 10:45 AM +1 · PNR DSTAGH / BERJYH",
   out2="AY 811 · Larry 2D, Heidi 2F · 1:15 PM · private transfer to At Six Stockholm",
   ret="BA 6776 (Larry 3C, Heidi 3A) · AA 79 (Larry 8D, Heidi 8G) · Regent airport transfer",
   nights=10, ports=5, exc_count=7, heidi_bday=True,
   exc={**DINING,
     "aug30":[("Highlights of Stockholm & Vasa Museum","Aug 30 · 09:00")],
     "sep1":[("SG – The Berlin Experience","Sep 1 · 07:30")],
     "sep2":[("Amazing Rostock","Sep 2 · 09:00"),("Medieval Flavors of Rostock","Sep 2 · 14:30")],
     "sep3":[("A Tour of Two Kingdoms – Denmark to Sweden","Sep 3 · 08:45")],
     "sep4":[("Tivoli Gardens & Canal Cruise","Sep 4 · 10:15")],
     "sep7":[("Panoramic Oslo","Sep 7 · 09:15")],
   },
   open_items=[
     ("&#128203;","Online check-in opens Aug 8, 2026","Complete on the Regent guest portal once open."),
     ("&#128652;","Airport transfer (ARN &rarr; At Six)","Confirmed on hold; balance due Aug 16, 2026."),
     ("&#9992;&#65039;","Return flight seats","Seat assignments being finalized with the airlines."),
   ]),
}

SHIP_P = ("Regent’s newest ultra-luxury, all-suite ship, launched in 2023 — a multimillion-dollar art "
          "collection, private balconies in every suite, eight dining venues at no extra charge, and one of the "
          "most spacious crew-to-guest ratios at sea.")

def render(cid, c):
    days = build_days(c)
    body_cards = "".join(card(d) for d in days)
    open_html = "".join(
        f'<div class="open-item"><span class="open-icon">{i[0]}</span>'
        f'<div class="open-info"><div class="open-title">{i[1]}</div><div class="open-desc">{i[2]}</div></div>'
        f'<span class="open-status">Pre-Boarding</span></div>' for i in c["open_items"])
    ship_uri, ship_comment = IMG["ship"]
    doc = f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Seven Seas Grandeur &middot; {c["title"]} | Dreams2Memories Travel</title>
<style>{CSS}</style></head>
<body><div class="page">
<div class="hero"><img class="logo" src="{D2M_LOGO}" alt="Dreams2Memories Travel">
<div class="wordmark">DREAMS2MEMORIES TRAVEL, LLC</div>
<div class="voyage-title">Seven Seas Grandeur &middot; Storied Scandinavia</div>
<div class="voyage-sub">Stockholm to Oslo &middot; August 29 &ndash; September 8, 2026</div></div>

<div class="ship-profile"><!-- {html.escape(ship_comment)} -->
<img src="{ship_uri}" alt="Seven Seas Grandeur">
<div class="ship-text"><h2>Seven Seas Grandeur</h2><p>{SHIP_P}</p>
<div class="ship-stats"><span>&#11088; {c["suite"]}</span><span>&#127860; 8 Dining Venues</span>
<span>&#127754; 55,500 Gross Tons</span><span>&#128737; 744 Guests</span><span>&#129496; Canyon Ranch Spa</span></div></div></div>

<div class="stats-bar">
<div class="stat"><div class="stat-val">{c["nights"]}</div><div class="stat-lbl">Nights</div></div>
<div class="stat"><div class="stat-val">{c["ports"]}</div><div class="stat-lbl">Ports</div></div>
<div class="stat"><div class="stat-val">{c["exc_count"]}</div><div class="stat-lbl">Shore Excursions</div></div>
<div class="stat"><div class="stat-val">3</div><div class="stat-lbl">Specialty Dinners</div></div>
</div>

<div class="ck-bar"><span><b>{c["title"]}</b> &middot; Reservation #{c["res"]}</span><span>{c["ck"]}</span></div>

{route_map()}

<div class="sec-header">&#9992;&#65039; Pre-Cruise Travel &middot; Stockholm Arrival</div>
<div class="itinerary-container">{"".join(card(d) for d in days[:3])}</div>
<div class="sec-header">&#128674; Cruise Itinerary &middot; Seven Seas Grandeur</div>
<div class="itinerary-container">{"".join(card(d) for d in days[3:13])}</div>
<div class="sec-header">&#9992;&#65039; Return Home</div>
<div class="itinerary-container">{"".join(card(d) for d in days[13:])}</div>

<div class="open-section"><div class="open-hdr">Final Pre-Boarding Notes</div>{open_html}</div>

<div class="footer"><div class="fco">DREAMS2MEMORIES TRAVEL, LLC</div>
Your voyage is planned, verified, and cared for end to end.<br>
719-291-0742 &middot; <a href="mailto:concierge@d2mluxury.quest">concierge@d2mluxury.quest</a><br>
<span style="font-size:10px">Prepared for {c["title"]} &middot; Seven Seas Grandeur &middot; Aug 29 &ndash; Sep 8, 2026</span></div>
</div></body></html>'''
    path = os.path.join(OUT_DIR, f"itinerary_grandeur_{cid}.html")
    with open(path, "w") as f: f.write(doc)
    return path, len(doc)

if __name__ == "__main__":
    for cid, c in COUPLES.items():
        p, n = render(cid, c)
        print(f"WROTE {p}  ({n:,} bytes)")
