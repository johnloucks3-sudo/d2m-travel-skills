#!/usr/bin/env python3
"""Render D2M 4-Week Accomplishments Report to PDF with full D2M branding."""
import sys, base64, pathlib
sys.path.insert(0, '/home/john/Thunderbird')

import markdown
from weasyprint import HTML, CSS

MD_PATH  = pathlib.Path('/home/john/Thunderbird/Commander_Review/D2M_4WEEK_ACCOMPLISHMENTS_2026-03.md')
PDF_PATH = pathlib.Path('/home/john/Thunderbird/Commander_Review/D2M_4WEEK_ACCOMPLISHMENTS_2026-03.pdf')
LOGO_PATH = pathlib.Path('/home/john/Thunderbird/Agency_Logo.png')

# --- Logo as data URI ---
logo_b64 = ''
if LOGO_PATH.exists():
    logo_b64 = 'data:image/png;base64,' + base64.b64encode(LOGO_PATH.read_bytes()).decode()

# --- Convert Markdown → HTML body ---
md_text = MD_PATH.read_text()
body_html = markdown.markdown(md_text, extensions=['tables', 'extra'])

# --- Full HTML document ---
html_doc = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>D2M 4-Week Accomplishments Report</title>
</head>
<body>

<div class="cover-banner">
  {'<img class="logo" src="' + logo_b64 + '">' if logo_b64 else ''}
  <div class="cover-sub">Four-Week Accomplishments Report · February 19 – March 19, 2026</div>
</div>

<div class="content">
{body_html}
</div>

<div class="footer">
  Dreams2Memories Travel, LLC &nbsp;·&nbsp; Confidential &nbsp;·&nbsp; March 19, 2026
</div>

</body>
</html>"""

# --- CSS ---
css = CSS(string="""
@import url('https://fonts.googleapis.com/css2?family=Georgia&display=swap');

@page {
  size: Letter;
  margin: 0.75in 0.85in 0.9in 0.85in;
  @bottom-center {
    content: counter(page) " of " counter(pages);
    font-size: 8pt;
    color: #8a9ab5;
    font-family: Georgia, serif;
  }
}

body {
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 10.5pt;
  color: #1a1a2e;
  background: #f7f3ea;
  line-height: 1.65;
}

.cover-banner {
  background: #0d1b2e;
  margin: -0.75in -0.85in 0 -0.85in;
  padding: 0.55in 0.85in 0.35in 0.85in;
  text-align: center;
  border-bottom: 4px solid #c9a84c;
  page-break-after: avoid;
}

.cover-banner .logo {
  max-width: 260px;
  max-height: 80px;
  object-fit: contain;
}

.cover-sub {
  color: #c9a84c;
  font-size: 9pt;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  margin-top: 0.12in;
  font-family: Georgia, serif;
}

.content {
  padding-top: 0.3in;
}

h1 {
  color: #0d1b2e;
  font-size: 22pt;
  font-weight: bold;
  border-bottom: 2px solid #c9a84c;
  padding-bottom: 6pt;
  margin-top: 24pt;
  margin-bottom: 10pt;
}

h2 {
  color: #0d1b2e;
  font-size: 15pt;
  font-weight: bold;
  border-left: 4px solid #c9a84c;
  padding-left: 10pt;
  margin-top: 22pt;
  margin-bottom: 8pt;
  page-break-after: avoid;
}

h3 {
  color: #152540;
  font-size: 12pt;
  font-weight: bold;
  margin-top: 16pt;
  margin-bottom: 6pt;
  page-break-after: avoid;
}

p {
  margin: 0 0 9pt 0;
  color: #1a1a2e;
}

blockquote {
  border-left: 3px solid #c9a84c;
  background: #ede8dd;
  margin: 12pt 0;
  padding: 10pt 14pt;
  color: #0d1b2e;
  font-style: italic;
}

blockquote p { margin: 0; }

strong {
  color: #0d1b2e;
  font-weight: bold;
}

em { color: #2a2a4a; }

table {
  width: 100%;
  border-collapse: collapse;
  margin: 14pt 0;
  font-size: 9.5pt;
  page-break-inside: avoid;
}

th {
  background: #0d1b2e;
  color: #c9a84c;
  padding: 7pt 10pt;
  text-align: left;
  font-weight: bold;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  font-size: 8.5pt;
}

td {
  padding: 6pt 10pt;
  border-bottom: 1px solid #ddd8ce;
  color: #1a1a2e;
  vertical-align: top;
}

tr:nth-child(even) td { background: #f0ece3; }

ul, ol {
  margin: 8pt 0 8pt 18pt;
  padding: 0;
}

li {
  margin-bottom: 4pt;
  color: #1a1a2e;
}

hr {
  border: none;
  border-top: 1px solid #c9a84c;
  margin: 18pt 0;
  opacity: 0.5;
}

.footer {
  position: running(footer);
  font-size: 8pt;
  color: #8a9ab5;
  text-align: center;
  font-family: Georgia, serif;
  border-top: 1px solid #c9a84c;
  padding-top: 4pt;
  margin-top: 0.2in;
}

a { color: #0000ff; text-decoration: none; }
""")

HTML(string=html_doc).write_pdf(str(PDF_PATH), stylesheets=[css])
print(f"PDF rendered: {PDF_PATH}")
print(f"Size: {PDF_PATH.stat().st_size / 1024:.0f} KB")
