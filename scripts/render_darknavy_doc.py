#!/usr/bin/env python3
"""
render_darknavy_doc.py — Render a Markdown document into a full-page D2M dark-navy HTML document.

Document format (not the 600px email column): centered page, responsive, self-contained
inline CSS. Uses the canonical D2M dark-navy palette (#07076b family, Georgia serif),
matching scripts/d2m_email_builder.py aesthetic but sized for on-screen/website reading.

Usage:
  python3 scripts/render_darknavy_doc.py --in client/00_Trip_Book.md --out client/html/00_Trip_Book.html
  python3 scripts/render_darknavy_doc.py --dir output/Spencer_GrandTour_2027/client --outdir output/Spencer_GrandTour_2027/client/html

Dreams2Memories Travel, LLC · 2026-07-02
"""
import argparse
import re
from pathlib import Path

import markdown

LOGO = "https://lh3.googleusercontent.com/d/1HYa61cNwcialWk64DimGwIfCAbUjESsu"

SHELL = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 28px 12px;
    font-family: Georgia, 'Times New Roman', serif;
    color: #e8f1ff;
    background-color: #07076b;
    background: radial-gradient(ellipse at 50% -8%, #2428b0 0%, #0e1088 18%, #07076b 46%, #040450 78%, #02022e 100%);
    background-attachment: fixed;
  }}
  .page {{
    max-width: 860px; margin: 0 auto;
    background-color: #08086e;
    background: linear-gradient(175deg, #10118c 0%, #09096e 35%, #06065e 70%, #04044c 100%);
    border-radius: 14px;
    box-shadow: 0 8px 40px rgba(0,0,0,0.45);
    overflow: hidden;
  }}
  .hero {{
    background-color: #0a0a68;
    background: linear-gradient(180deg, #0c0c80 0%, #060650 100%);
    text-align: center; padding: 30px 24px 22px;
  }}
  .hero img {{ display: inline-block; border: 0; width: 128px; height: auto; }}
  .wordmark {{ color: #f0f6ff; font-size: 12px; letter-spacing: 3.5px; margin-top: 10px; }}
  .shimmer {{ height: 3px; font-size: 1px; line-height: 1px;
    background: linear-gradient(90deg, #07076b 0%, rgba(220,235,255,1.0) 50%, #07076b 100%); }}
  .body {{ padding: 34px 40px 40px; font-size: 17px; line-height: 1.8; }}
  .body h1 {{ color: #f0f6ff; font-size: 30px; font-weight: normal; letter-spacing: .3px; margin: 6px 0 18px; line-height: 1.25; }}
  .body h2 {{ color: #c8dcff; font-size: 21px; font-weight: normal; letter-spacing: .5px;
    border-bottom: 1px solid rgba(180,200,255,0.35); padding-bottom: 8px; margin: 34px 0 16px; }}
  .body h3 {{ color: #a8c4f0; font-size: 17px; font-weight: bold; margin: 24px 0 8px; }}
  .body h4 {{ color: #c8dcff; font-size: 15px; margin: 18px 0 6px; }}
  .body p {{ margin: 0 0 16px; color: #e8f1ff; }}
  .body a {{ color: #a8c4f0; text-decoration: underline; text-underline-offset: 2px; }}
  .body strong {{ color: #f0f6ff; }}
  .body em {{ color: #a8c4f0; }}
  .body ul, .body ol {{ color: #e8f1ff; margin: 0 0 16px; padding-left: 24px; }}
  .body li {{ margin: 5px 0; }}
  .body hr {{ border: 0; height: 1px; margin: 26px 0;
    background: linear-gradient(90deg, transparent 0%, rgba(220,235,255,0.5) 50%, transparent 100%); }}
  .body blockquote {{ margin: 0 0 20px; padding: 14px 18px;
    background: rgba(255,255,255,0.06); border-left: 4px solid rgba(100,150,255,0.7);
    border-radius: 0 8px 8px 0; color: #c8dcff; }}
  .body blockquote p {{ margin: 0; color: #c8dcff; }}
  .body table {{ width: 100%; border-collapse: collapse; margin: 8px 0 22px; font-size: 15px; }}
  .body th {{ background-color: #0a0a68; color: #e8f1ff; text-align: left; font-weight: normal;
    padding: 10px 12px; border: 1px solid rgba(180,200,255,0.22); }}
  .body td {{ color: #d0e4ff; padding: 10px 12px; border: 1px solid rgba(180,200,255,0.15); vertical-align: top; }}
  .body tr:nth-child(even) td {{ background: rgba(255,255,255,0.03); }}
  .body code {{ background: rgba(255,255,255,0.08); color: #dbe8ff; padding: 1px 5px; border-radius: 4px; font-size: 14px; }}
  .body img {{ max-width: 100%; height: auto; }}
  .footer {{ text-align: center; color: #8fa8d8; font-size: 12px; padding: 20px 24px 26px;
    border-top: 1px solid rgba(180,200,255,0.18); }}
  @media (max-width: 620px) {{ .body {{ padding: 24px 20px 30px; font-size: 16px; }} .body h1 {{ font-size: 25px; }} }}
</style>
</head>
<body>
  <div class="page">
    <div class="hero">
      <img src="{logo}" alt="Dreams2Memories Travel">
      <div class="wordmark">DREAMS2MEMORIES TRAVEL, LLC</div>
    </div>
    <div class="shimmer">&nbsp;</div>
    <div class="body">
{content}
    </div>
    <div class="footer">Dreams2Memories Travel, LLC · Prepared for the Spencer Family · Draft</div>
  </div>
</body>
</html>
"""


def render(md_text: str) -> str:
    return markdown.markdown(
        md_text,
        extensions=["tables", "extra", "sane_lists", "nl2br"],
    )


def title_from_md(md_text: str, fallback: str) -> str:
    for line in md_text.splitlines():
        m = re.match(r"#\s+(.*)", line.strip())
        if m:
            return re.sub(r"[*_`#]", "", m.group(1)).strip()
    return fallback


def convert(inp: Path, outp: Path):
    md_text = inp.read_text(encoding="utf-8")
    html = render(md_text)
    title = title_from_md(md_text, inp.stem)
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(SHELL.format(title=title, logo=LOGO, content=html), encoding="utf-8")
    print(f"  ✓ {inp.name} → {outp.relative_to(outp.parent.parent)}  ({outp.stat().st_size:,}b)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp")
    ap.add_argument("--out", dest="outp")
    ap.add_argument("--dir")
    ap.add_argument("--outdir")
    a = ap.parse_args()
    if a.dir:
        d = Path(a.dir)
        od = Path(a.outdir or (d / "html"))
        for f in sorted(d.glob("*.md")):
            convert(f, od / (f.stem + ".html"))
    elif a.inp and a.outp:
        convert(Path(a.inp), Path(a.outp))
    else:
        ap.error("use --dir DIR [--outdir OUT] or --in FILE --out FILE")


if __name__ == "__main__":
    main()
