#!/usr/bin/env python3
"""
build_client_portal.py — Combine a set of client Markdown docs into ONE dark-navy
single-page portal (sticky nav + anchored sections). Self-contained inline CSS →
works from a single file / one shareable link, no infra.

Usage:
  python3 scripts/build_client_portal.py --dir output/Spencer_GrandTour_2027/client \
     --out output/Spencer_GrandTour_2027/client/html/index.html \
     --title "The Spencer Family Grand Tour 2027" \
     --subtitle "June 12 – July 2, 2027 · Your Private Travel Portal"

Nav labels are derived from an ordered map (edit NAV below) or fall back to the H1.

Dreams2Memories Travel, LLC · 2026-07-02
"""
import argparse
import re
from pathlib import Path

import markdown

LOGO = "https://lh3.googleusercontent.com/d/1HYa61cNwcialWk64DimGwIfCAbUjESsu"

# filename-stem -> short nav label (ordered)
NAV = {
    "00_Trip_Book": "Overview",
    "01_Day_by_Day_Itinerary": "Itinerary",
    "02_Shore_Excursion_Menu": "Excursions",
    "03_Florence_and_Tuscany_Options": "Florence & Tuscany",
    "04_Swiss_Alps_Journey": "Switzerland",
    "05_Your_Options_and_Investment": "Your Options",
    "06_Build_Your_Journey_Investment_Guide": "Build Your Journey",
}

# filename-stem -> Google Doc title (to match _gdoc_links.json for the "suggest edits" link)
DOC_TITLES = {
    "00_Trip_Book": "Spencer Grand Tour — Trip Book (Overview)",
    "01_Day_by_Day_Itinerary": "Spencer Grand Tour — Day-by-Day Itinerary",
    "02_Shore_Excursion_Menu": "Spencer Grand Tour — Shore Excursion Menu",
    "03_Florence_and_Tuscany_Options": "Spencer Grand Tour — Florence & Tuscany Options",
    "04_Swiss_Alps_Journey": "Spencer Grand Tour — Swiss Alps Journey",
    "05_Your_Options_and_Investment": "Spencer Grand Tour — Your Options & Investment",
    "06_Build_Your_Journey_Investment_Guide": "Spencer Grand Tour — Build Your Journey (Investment Guide)",
}

# extra nav items served alongside index.html (standalone pages / downloads)
EXTRA_NAV = (
    '<a href="Spencer_PERT_Critical_Path_v2.html">Planning Timeline</a>'
    '<a href="Spencer_Grand_Tour_Briefing.pptx">Briefing Deck ⬇</a>'
)

CSS = """
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body { margin: 0; font-family: Georgia, 'Times New Roman', serif; color: #e8f1ff;
  background-color: #07076b;
  background: radial-gradient(ellipse at 50% -6%, #2428b0 0%, #0e1088 16%, #07076b 44%, #040450 76%, #02022e 100%);
  background-attachment: fixed; }
.nav { position: sticky; top: 0; z-index: 50; backdrop-filter: blur(8px);
  background: rgba(8,8,90,0.92); border-bottom: 1px solid rgba(180,200,255,0.22);
  padding: 10px 14px; display: flex; flex-wrap: wrap; gap: 8px; align-items: center; justify-content: center; }
.nav .brand { color: #c8d8ff; font-size: 12px; letter-spacing: 2.5px; margin-right: 10px; }
.nav a { color: #cfe0ff; text-decoration: none; font-size: 13px; padding: 6px 12px;
  border: 1px solid rgba(180,200,255,0.28); border-radius: 20px; white-space: nowrap; }
.nav a:hover { background: rgba(120,150,255,0.25); border-color: rgba(200,220,255,0.6); }
.hero { text-align: center; padding: 46px 20px 30px; }
.hero img { width: 150px; height: auto; }
.hero .wordmark { color: #f0f6ff; font-size: 13px; letter-spacing: 4px; margin-top: 12px; }
.hero h1 { color: #f0f6ff; font-weight: normal; font-size: 34px; margin: 20px 0 8px; }
.hero .sub { color: #a8c4f0; font-size: 16px; font-style: italic; }
.shimmer { height: 3px; font-size: 1px;
  background: linear-gradient(90deg, #07076b 0%, rgba(220,235,255,1.0) 50%, #07076b 100%); }
.wrap { max-width: 880px; margin: 0 auto; padding: 0 12px 60px; }
section.doc { background-color: #08086e;
  background: linear-gradient(175deg, #10118c 0%, #09096e 35%, #06065e 70%, #04044c 100%);
  border-radius: 14px; box-shadow: 0 8px 40px rgba(0,0,0,0.4);
  padding: 34px 40px 40px; margin: 26px 0; font-size: 17px; line-height: 1.8; scroll-margin-top: 70px; }
section.doc h1 { color: #f0f6ff; font-size: 27px; font-weight: normal; margin: 4px 0 18px; line-height: 1.25; }
section.doc h2 { color: #c8dcff; font-size: 20px; font-weight: normal; letter-spacing: .4px;
  border-bottom: 1px solid rgba(180,200,255,0.35); padding-bottom: 8px; margin: 32px 0 15px; }
section.doc h3 { color: #a8c4f0; font-size: 16px; font-weight: bold; margin: 22px 0 8px; }
section.doc h4 { color: #c8dcff; font-size: 15px; margin: 16px 0 6px; }
section.doc p { margin: 0 0 15px; }
section.doc a { color: #a8c4f0; text-decoration: underline; text-underline-offset: 2px; }
section.doc strong { color: #f0f6ff; }
section.doc em { color: #a8c4f0; }
section.doc ul, section.doc ol { margin: 0 0 15px; padding-left: 24px; }
section.doc li { margin: 5px 0; }
section.doc hr { border: 0; height: 1px; margin: 24px 0;
  background: linear-gradient(90deg, transparent, rgba(220,235,255,0.5), transparent); }
section.doc blockquote { margin: 0 0 18px; padding: 13px 18px; background: rgba(255,255,255,0.06);
  border-left: 4px solid rgba(100,150,255,0.7); border-radius: 0 8px 8px 0; color: #c8dcff; }
section.doc blockquote p { margin: 0; color: #c8dcff; }
section.doc table { width: 100%; border-collapse: collapse; margin: 8px 0 20px; font-size: 15px; }
section.doc th { background: #0a0a68; color: #e8f1ff; text-align: left; font-weight: normal;
  padding: 10px 12px; border: 1px solid rgba(180,200,255,0.22); }
section.doc td { color: #d0e4ff; padding: 10px 12px; border: 1px solid rgba(180,200,255,0.15); vertical-align: top; }
section.doc tr:nth-child(even) td { background: rgba(255,255,255,0.03); }
section.doc img { max-width: 100%; height: auto; }
.editbar { background: rgba(120,150,255,0.16); border: 1px solid rgba(180,200,255,0.4);
  border-radius: 8px; padding: 9px 14px; margin: 0 0 20px; font-size: 14px; }
.editbar a { color: #dbe8ff; }
.foot { text-align: center; color: #8fa8d8; font-size: 12px; padding: 10px 20px 40px; }
@media (max-width: 620px) { section.doc { padding: 24px 20px 30px; font-size: 16px; } .hero h1 { font-size: 26px; } }
"""


def render_md(text):
    return markdown.markdown(text, extensions=["tables", "extra", "sane_lists", "nl2br"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--title", default="Your Travel Portal")
    ap.add_argument("--subtitle", default="")
    a = ap.parse_args()
    d = Path(a.dir)

    stems = [s for s in NAV if (d / f"{s}.md").exists()]
    stems += [f.stem for f in sorted(d.glob("*.md")) if f.stem not in NAV]

    # Google Doc edit links (optional)
    links_file = d / "_gdoc_links.json"
    gdoc = {}
    if links_file.exists():
        import json as _json
        gdoc = _json.loads(links_file.read_text()).get("docs", {})

    navlinks, sections = [], []
    for i, stem in enumerate(stems):
        f = d / f"{stem}.md"
        label = NAV.get(stem, stem.replace("_", " "))
        anchor = f"doc{i}"
        navlinks.append(f'<a href="#{anchor}">{label}</a>')
        edit_url = gdoc.get(DOC_TITLES.get(stem, ""))
        edit_banner = (
            f'<div class="editbar">✏️ <a href="{edit_url}" target="_blank" rel="noopener">'
            f'Open the working copy to suggest edits (Google Doc)</a></div>'
        ) if edit_url else ""
        sections.append(
            f'<section class="doc" id="{anchor}">\n{edit_banner}\n'
            f'{render_md(f.read_text(encoding="utf-8"))}\n</section>'
        )

    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{a.title}</title><style>{CSS}</style></head>
<body>
<div class="nav"><span class="brand">DREAMS2MEMORIES</span>{''.join(navlinks)}{EXTRA_NAV}</div>
<div class="hero">
  <img src="{LOGO}" alt="Dreams2Memories Travel">
  <div class="wordmark">DREAMS2MEMORIES TRAVEL, LLC</div>
  <h1>{a.title}</h1>
  <div class="sub">{a.subtitle}</div>
</div>
<div class="shimmer">&nbsp;</div>
<div class="wrap">
{chr(10).join(sections)}
</div>
<div class="foot">Dreams2Memories Travel, LLC · A private draft prepared for the Spencer family · John A. Loucks III · 719-291-0742 · johnloucks3@gmail.com</div>
</body></html>"""

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"Portal: {out} ({out.stat().st_size:,}b) — {len(stems)} sections: {', '.join(NAV.get(s, s) for s in stems)}")


if __name__ == "__main__":
    main()
