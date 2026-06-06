"""Build Spencer Grand Tour DOCX from revised Commander text."""

from docx import Document
from docx.shared import Pt, RGBColor, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import copy

OUT = "/home/john/Thunderbird/output/Spencer_FlightQuotes_DMC_2027.docx"

# ── Brand colors ──────────────────────────────────────────────────────────────
NAVY   = RGBColor(0x00, 0x30, 0x87)
GOLD   = RGBColor(0xB4, 0x53, 0x09)
CREAM  = RGBColor(0xF7, 0xF3, 0xEA)
AMBER  = RGBColor(0x92, 0x40, 0x0E)
WHITE  = RGBColor(0xFF, 0xFF, 0xFF)
BLACK  = RGBColor(0x1A, 0x1A, 0x1A)
GREEN  = RGBColor(0x15, 0x80, 0x3D)
LTBLUE = RGBColor(0xA8, 0xC4, 0xFF)
DGREY  = RGBColor(0x55, 0x55, 0x55)

doc = Document()

# ── Page margins ─────────────────────────────────────────────────────────────
for section in doc.sections:
    section.top_margin    = Inches(0.75)
    section.bottom_margin = Inches(0.75)
    section.left_margin   = Inches(1.0)
    section.right_margin  = Inches(1.0)


# ── Helpers ───────────────────────────────────────────────────────────────────

def shade_cell(cell, hex_color: str):
    """Apply background shading to a table cell."""
    tc   = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd  = OxmlElement("w:shd")
    shd.set(qn("w:val"),   "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"),  hex_color)
    tcPr.append(shd)


def cell_text(cell, text, bold=False, color=None, size=9, align=None, italic=False):
    """Set cell text with formatting — clears existing paragraphs."""
    cell.text = ""
    p   = cell.paragraphs[0]
    run = p.add_run(text)
    run.bold   = bold
    run.italic = italic
    run.font.size = Pt(size)
    if color:
        run.font.color.rgb = color
    if align:
        p.alignment = align
    return run


def add_h1(text, color=NAVY):
    p   = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run = p.add_run(text)
    run.bold = True
    run.font.size  = Pt(18)
    run.font.color.rgb = color
    pPr = p._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"),  "single")
    bottom.set(qn("w:sz"),   "12")
    bottom.set(qn("w:space"),"4")
    bottom.set(qn("w:color"), "003087")
    pBdr.append(bottom)
    pPr.append(pBdr)
    p.paragraph_format.space_before = Pt(18)
    p.paragraph_format.space_after  = Pt(8)
    return p


def add_h2(text, color=NAVY):
    p   = doc.add_paragraph()
    run = p.add_run(text.upper())
    run.bold = True
    run.font.size  = Pt(8)
    run.font.color.rgb = color
    run.font.name  = "Georgia"
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.space_after  = Pt(4)
    return p


def add_body(text, bold=False, italic=False, color=BLACK, size=10.5, space_after=8):
    p   = doc.add_paragraph()
    run = p.add_run(text)
    run.bold   = bold
    run.italic = italic
    run.font.size  = Pt(size)
    run.font.color.rgb = color
    p.paragraph_format.space_after  = Pt(space_after)
    p.paragraph_format.space_before = Pt(0)
    return p


def add_note_box(text):
    """Yellow D2M Notes box rendered as a single-cell table."""
    tbl  = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.LEFT
    cell = tbl.cell(0, 0)
    shade_cell(cell, "FFFBEB")
    # Left border amber
    tc   = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcBdr = OxmlElement("w:tcBdr")
    left = OxmlElement("w:left")
    left.set(qn("w:val"),  "single")
    left.set(qn("w:sz"),   "18")
    left.set(qn("w:space"),"0")
    left.set(qn("w:color"),"F59E0B")
    tcBdr.append(left)
    tcPr.append(tcBdr)
    cell.text = ""
    p   = cell.paragraphs[0]
    label = p.add_run("✦ D2M Notes — ")
    label.bold = True
    label.font.size  = Pt(9)
    label.font.color.rgb = AMBER
    body = p.add_run(text)
    body.font.size  = Pt(9)
    body.font.color.rgb = AMBER
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after  = Pt(4)
    cell.width = Inches(6.5)
    doc.add_paragraph().paragraph_format.space_after = Pt(4)
    return tbl


def add_table_header(tbl, headers, col_colors=None):
    row = tbl.rows[0]
    for i, hdr in enumerate(headers):
        cell = row.cells[i]
        shade_cell(cell, "003087")
        cell_text(cell, hdr, bold=True, color=WHITE, size=8.5, align=WD_ALIGN_PARAGRAPH.LEFT)


def make_table(headers, widths=None):
    tbl = doc.add_table(rows=1, cols=len(headers))
    tbl.style = "Table Grid"
    tbl.alignment = WD_TABLE_ALIGNMENT.LEFT
    add_table_header(tbl, headers)
    if widths:
        for i, w in enumerate(widths):
            tbl.columns[i].width = Inches(w)
    return tbl


def add_row(tbl, values, bg=None, bold=False, color=BLACK, size=9):
    row = tbl.add_row()
    for i, val in enumerate(values):
        cell = row.cells[i]
        if bg:
            shade_cell(cell, bg)
        cell_text(cell, str(val), bold=bold, color=color, size=size)
    return row


def add_spacer(pts=6):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after  = Pt(pts)


def add_card(title, subtitle, body_text, color=NAVY):
    tbl  = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.LEFT
    cell = tbl.cell(0, 0)
    shade_cell(cell, "FFFFFF")
    tc   = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcBdr = OxmlElement("w:tcBdr")
    left = OxmlElement("w:left")
    left.set(qn("w:val"),  "single")
    left.set(qn("w:sz"),   "18")
    left.set(qn("w:space"),"0")
    r, g, b = color
    left.set(qn("w:color"), f"{r:02X}{g:02X}{b:02X}")
    tcBdr.append(left)
    tcPr.append(tcBdr)
    cell.text = ""
    # Title
    p1   = cell.paragraphs[0]
    rt   = p1.add_run(title)
    rt.bold = True
    rt.font.size  = Pt(10)
    rt.font.color.rgb = color
    # Subtitle
    if subtitle:
        p2   = cell.add_paragraph()
        rs   = p2.add_run(subtitle)
        rs.italic = True
        rs.font.size  = Pt(8)
        rs.font.color.rgb = DGREY
    # Body
    p3   = cell.add_paragraph()
    rb   = p3.add_run(body_text)
    rb.font.size  = Pt(9)
    rb.font.color.rgb = RGBColor(0x44, 0x44, 0x44)
    add_spacer(6)
    return tbl


# ═══════════════════════════════════════════════════════════════════════════════
# DOCUMENT BUILD
# ═══════════════════════════════════════════════════════════════════════════════

# ── TITLE BLOCK ───────────────────────────────────────────────────────────────
tbl = doc.add_table(rows=1, cols=1)
tbl.alignment = WD_TABLE_ALIGNMENT.LEFT
cell = tbl.cell(0, 0)
shade_cell(cell, "003087")
cell.text = ""
p = cell.paragraphs[0]
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("Dreams2Memories Travel  ·  Private Client Package")
r.font.size  = Pt(9)
r.font.color.rgb = LTBLUE

p2 = cell.add_paragraph()
p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
r2 = p2.add_run("Spencer Family Grand Tour")
r2.bold = True
r2.font.size  = Pt(22)
r2.font.color.rgb = WHITE

p3 = cell.add_paragraph()
p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
r3 = p3.add_run("Flight Quotes & Travel Planner Recommendations")
r3.font.size  = Pt(13)
r3.font.color.rgb = RGBColor(0xF0, 0xC0, 0x40)

p4 = cell.add_paragraph()
p4.alignment = WD_ALIGN_PARAGRAPH.CENTER
r4 = p4.add_run("Bill & Kathleen Spencer  ·  12 Travelers  ·  June 12 – July 2, 2027")
r4.font.size  = Pt(10)
r4.font.color.rgb = WHITE

p5 = cell.add_paragraph()
p5.alignment = WD_ALIGN_PARAGRAPH.CENTER
r5 = p5.add_run("Prepared by John Loucks  ·  Dreams2Memories Travel  ·  June 2026")
r5.font.size  = Pt(8.5)
r5.font.color.rgb = LTBLUE

add_spacer(4)

# Sub-bar
tbl2 = doc.add_table(rows=1, cols=1)
cell2 = tbl2.cell(0, 0)
shade_cell(cell2, "001A4D")
cell2.text = ""
pb = cell2.paragraphs[0]
pb.alignment = WD_ALIGN_PARAGRAPH.CENTER
rb = pb.add_run("✈ FLIGHT QUOTES   |   🗺 DMC & TRAVEL PLANNER RECOMMENDATIONS   |   🏨 HOTEL OPTIONS   |   🚂 RAIL PLANNING")
rb.bold = True
rb.font.size  = Pt(8)
rb.font.color.rgb = RGBColor(0xF0, 0xC0, 0x40)

add_spacer(10)

# ── D2M NOTES INTRO ───────────────────────────────────────────────────────────
add_note_box(
    "Throughout this document you will see D2M Notes — the yellow boxes. These are planning insights "
    "provided by the Dreams2Memories team of AI-assisted travel planners: why we favor a particular route, "
    "what we know about a property from experience, what details we've noticed that matter to your family "
    "specifically, and where the fine print works in your favor. They are our thinking made visible — so you "
    "can see not just what we recommend, but why. All pricing in this document is planning-grade; summer 2027 "
    "fares are not yet published. This is an initial look at the full travel picture so you can see the shape "
    "of the journey before we go to market for firm quotes."
)

add_spacer(6)

# ── OPENING ───────────────────────────────────────────────────────────────────
add_h2("Twenty-One Days. Three Celebrations. One Grand Tour.", color=NAVY)
add_body(
    "Bill & Kathleen — this is the architecture of your family's Grand Tour. Three flight legs, three "
    "generations, five milestones, and twenty-one of the most extraordinary days any family can share "
    "together. Rome opens with the whole family. The Disney Wish sails all twelve of you through the "
    "Mediterranean. Switzerland closes with the eight of you who push on — rails, the Alps, and the "
    "memory of a lifetime."
)
add_body(
    "Below you'll find our flight quotes for all three legs of your journey, our recommended ground "
    "partners in Italy and Switzerland, and the hotel options I believe best fit your family. Everything "
    "is designed around maximum rail, maximum experience, minimum friction."
)

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION I — FLIGHTS
# ═══════════════════════════════════════════════════════════════════════════════
add_h1("Section I — Flight Quotes")

# LEG 1
add_h2("Leg 1 of 3  ·  All 12 Travelers  —  DEN → FCO  ·  Denver to Rome", color=NAVY)
add_body("June 12, 2027   Departs: 17:50  ·  Arrives: 12:20+1", italic=True, color=DGREY)
add_note_box(
    "United confirmed DEN-FCO nonstop on Boeing 787-9 Dreamliner, launched May 2025, seasonal route "
    "(May–September). June 12 is firmly within the window. Group of 12 qualifies for United Group Desk "
    "pricing — call 800-426-1122 now. Group rates can hold inventory before 2027 booking window opens "
    "(~Aug 2026) and lock fares at today's published levels."
)

tbl = make_table(
    ["Carrier", "Route", "Cabin", "Est. Per Seat", "12-Pax Total", "Notes"],
    widths=[1.3, 1.4, 1.0, 1.0, 1.0, 1.3]
)
add_row(tbl, [
    "United Airlines  ★ PREFERRED",
    "DEN → FCO\nNonstop · 10h 50m",
    "Polaris Business",
    "$5,500–$6,500",
    "$66,000–$78,000",
    "Only nonstop DEN-FCO. 787-9 Dreamliner. Flat-bed seats. Group discount may reduce 10–30%."
])
add_row(tbl, [
    "United Airlines\nPremium Plus",
    "DEN → FCO\nNonstop · 10h 50m",
    "Premium Plus",
    "$1,500–$1,800",
    "$18,000–$21,600",
    "Extra legroom, enhanced meal, priority boarding. Same aircraft, one flight, same arrival."
], bg="F9F7F4")
add_spacer(8)

add_body("Child Fare Notes:", bold=True, color=NAVY)
add_body(
    "James (age 5 on travel date): Full adult fare required. Priced at adult rate above.\n"
    "Judah (age 2 on travel date): Lap infant on international routes = 10% of adult fare (~$550–$650 in Polaris). "
    "If you prefer his own seat — which I strongly recommend for a 10h 45m overnight — plan adult fare. "
    "Two-year-olds and flat-bed seats are a good combination for everyone involved.\n"
    "Strollers: Two strollers check free as child equipment — do not count against baggage allowance.",
    size=9.5
)
add_body(
    "Group Rate Opportunity: United defines groups as 10+ passengers. Your party of 12 qualifies. "
    "Benefits: name change flexibility, fare hold without full deposit, coordinated check-in. "
    "A 20% group discount on Polaris saves approximately $13,200–$15,600. I'll initiate the group inquiry on your behalf.",
    italic=True, color=NAVY, size=9.5
)

# LEG 2
add_h2("Leg 2 of 3  ·  Tim's Family — 4 Travelers  —  FCO → DEN  ·  Rome to Denver", color=NAVY)
add_body("June 23, 2027   Departure: No earlier than 11:00am  ·  United 14:20 FCO", italic=True, color=DGREY)
add_body(
    "Tim's family (Tim, JoAnne, James age 6, Judah age 3 at travel time). Ship docks Civitavecchia ~0800 — "
    "1.5h transfer to FCO means earliest possible departure is 1100. United's westbound FCO-DEN departs "
    "14:20 — perfect compliance, no stress. ONLY a nonstop qualifies here. Connection risk with two small "
    "children and two strollers after a cruise disembarkation is too high.", size=9.5
)

tbl = make_table(
    ["Carrier", "Route", "Departure", "Cabin", "Est. Per Seat", "4-Pax Total"],
    widths=[1.5, 1.4, 0.8, 1.0, 1.0, 0.9]
)
add_row(tbl, [
    "United Airlines  ★ ONLY OPTION",
    "FCO → DEN\nNonstop",
    "14:20",
    "Business",
    "$5,500–$6,500",
    "$22,000–$26,000"
])
add_row(tbl, [
    "United Airlines\nPremium Economy",
    "FCO → DEN\nNonstop",
    "14:20",
    "Premium Economy",
    "$1,000–$1,800",
    "$4,000–$7,200"
], bg="F9F7F4")
add_spacer(6)
add_body(
    "Why nonstop is non-negotiable: Alternative carriers (Lufthansa via Frankfurt, Delta via Atlanta, "
    "American via Philadelphia) all require a connection. With two children ages 5 and 2, two strollers, "
    "after cruise disembarkation — a misconnect creates a genuine family speedbump in a foreign country. "
    "United's 14:20 nonstop is the only routing I can stand behind for Tim's family. Hopefully it will "
    "still be available.",
    italic=True, size=9.5
)

# LEG 3
add_h2("Leg 3 of 3  ·  Remaining 8 Travelers  —  ZRH → DEN  ·  Zurich to Denver", color=NAVY)
add_body("July 2, 2027   After 2 nights Zurich  ·  Trip finale", italic=True, color=DGREY)
add_note_box(
    "SWISS Airlines operates a nonstop ZRH-DEN — confirm frequency on Wednesday July 2 when 2027 schedule "
    "publishes (approx. Aug–Sep 2026). If SWISS doesn't fly that specific date, United ZRH-DEN via ORD is "
    "the fallback. SWISS Business Class (Helvetic) is excellent — flat-bed, superb catering, quieter cabin "
    "than US carriers. Worth a premium."
)

tbl = make_table(
    ["Carrier", "Route", "Cabin", "Est. Per Seat", "8-Pax Total", "Notes"],
    widths=[1.3, 1.4, 1.0, 1.0, 1.0, 1.3]
)
add_row(tbl, [
    "SWISS Air Lines  ★ PREFERRED",
    "ZRH → DEN\nNonstop · ~10h 45m",
    "Business",
    "$3,500–$5,500",
    "$28,000–$44,000",
    "Premium Swiss product. Confirm frequency on July 2 when 2027 schedule opens."
])
add_row(tbl, [
    "United Airlines",
    "ZRH → ORD → DEN\nOne-stop",
    "Business",
    "$3,000–$5,000",
    "$24,000–$40,000",
    "Star Alliance partner. Good fallback. ORD adds ~4h."
], bg="F9F7F4")
add_row(tbl, [
    "Lufthansa",
    "ZRH → FRA → DEN\nOne-stop",
    "Business",
    "$2,800–$4,500",
    "$22,400–$36,000",
    "Best value. Strong product. FRA is a smooth hub for connections."
])
add_row(tbl, [
    "SWISS / United / Lufthansa",
    "ZRH → DEN",
    "Premium Economy",
    "$1,200–$2,500",
    "$9,600–$20,000",
    "Strong backup — especially appropriate for Lillie (18) and Clara (15)."
], bg="F9F7F4")
add_spacer(8)

# BUDGET SUMMARY
add_h2("Flight Budget Summary — All Three Legs", color=NAVY)
tbl = make_table(
    ["Leg", "Route", "Pax", "Business Class", "Premium Economy"],
    widths=[0.5, 2.2, 0.5, 1.6, 1.7]
)
add_row(tbl, ["1", "DEN → FCO  ·  Jun 12", "12", "$66,000–$78,000", "$18,000–$21,600"])
add_row(tbl, ["2", "FCO → DEN  ·  Jun 23", "4",  "$22,000–$26,000", "$4,000–$7,200"], bg="F9F7F4")
add_row(tbl, ["3", "ZRH → DEN  ·  Jul 2",  "8",  "$28,000–$44,000", "$9,600–$20,000"])
add_row(tbl,
    ["", "TOTAL — ALL BUSINESS CLASS", "", "$116,000–$148,000", "$31,600–$48,800"],
    bold=True, color=NAVY, bg="EBF0FF"
)
add_spacer(4)
add_body(
    "Group discount applied (est. 15–20% on Leg 1). Potential savings: $10,000–$15,000. "
    "All figures are planning-grade estimates based on 2025–2026 published fare data. "
    "Summer 2027 schedules open approximately August 2026.",
    italic=True, color=DGREY, size=8.5
)

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION II — ITALY
# ═══════════════════════════════════════════════════════════════════════════════
add_h1("Section II — Italy: Travel Planners & Ground Logistics")

add_body(
    "Rome hosts all 12 of you for three days. Florence welcomes the remaining 8 for two. Both cities deserve "
    "a ground operator who knows the Vatican queue at 6am, the Florentine sommelier worth calling, and the "
    "difference between a luxury transfer and an ordinary taxi. Below are our vetted partners."
)
add_note_box(
    "Top call: Europe Express (800-565-7236, Private Groups line). They are purpose-built for travel advisors "
    "managing private multi-city groups — full Italy coverage, Vatican and Colosseum private tour capability, "
    "hotel partnerships in both cities. Icaterina is the boutique ultra-luxury alternative if maximum "
    "white-glove is the priority. Get proposals from both and compare. Insight Vacations is a coach-tour "
    "operator — not appropriate for this profile."
)

add_h2("Italy — DMC Recommendations", color=NAVY)

add_card(
    "★ Europe Express — Primary Recommendation",
    "Travel Advisor DMC  ·  Full Italy Coverage  ·  Private Group Desk",
    "Europe Express is built for exactly this engagement — a travel advisor running a private multi-city, "
    "multi-generational celebration group. Their Private Groups desk coordinates Rome, Florence, Vatican "
    "private tours, hotel partnerships, ground transfers, and inter-city rail. They know the Vatican at "
    "opening, the Colosseum's underground tunnels, and which Florentine restaurant will close its terrace "
    "for a 50th anniversary dinner.\n\n"
    "Private Groups: 800-565-7236  |  Elevated Journeys (premium tier): 888-848-8005  |  europeexpress.com",
    color=NAVY
)
add_card(
    "Icaterina — Ultra-Luxury Alternative",
    "Rome Boutique  ·  Ultra-Luxury  ·  Private Villa Access  ·  After-Hours Cultural Experiences",
    "Boutique Rome-based DMC with US representation. Budget: $5,000–$50,000+ per person. Bespoke itineraries, "
    "chauffeur-driven transfers, exclusive after-hours cultural experiences (Vatican at night, private museum "
    "access). For a 50th anniversary with 'spare no expense' mandate, this is the operator who can arrange a "
    "private Sistine Chapel viewing before the public enters.\n\n"
    "US Rep (DESTINARE): +1 718-813-2591  |  icaterina.com  |  WhatsApp available",
    color=GOLD
)
add_card(
    "Tauck Bridges — Multi-Generational Italy",
    "Multi-Generational Specialist  ·  Ages 2–74 Profile Match  ·  Private Program Available",
    "Tauck's Bridges program is specifically designed for mixed-generation groups. Their Italy product "
    "includes after-hours exclusive Sistine Chapel access, premium escorts, and all-inclusive pricing. "
    "Custom/private division can configure a program around your non-standard dates. Worth a direct inquiry "
    "given your ages 2–74 profile.\n\ntauck.com/tours/italy-small-group-tour → Custom Journeys desk",
    color=RGBColor(0x1D, 0x4E, 0xD8)
)

add_h2("Rome — Guided Experiences", color=NAVY)
add_note_box(
    "The Roman Guy has the highest ratings for private Vatican and Colosseum tours. For the 'spare no "
    "expense' mandate, the 'Alone at the Vatican' product ($7,561) gives the entire group the Sistine "
    "Chapel to themselves — that is a 50th anniversary experience that no one forgets. Get the quote. "
    "Underground Colosseum (hypogeum) access sells out 4–8 weeks in advance even for 2027 — book through "
    "a block-booking operator early."
)

tbl = make_table(
    ["Experience", "Operator / Notes", "Est. Price"],
    widths=[2.2, 3.1, 1.2]
)
add_row(tbl, [
    "Private Vatican — Museums, Sistine Chapel & St. Peter's",
    "The Roman Guy · Skip-the-line · Expert guide · Family-friendly format",
    "From $663 (12 pax — quote for group)"
])
add_row(tbl, [
    "'Alone at the Vatican' — Exclusive Access",
    "The Roman Guy · Museum closed to public · 50th Anniversary Signature Experience",
    "$7,561 (entire group)"
], bg="FFF8F0")
add_row(tbl, [
    "Private Colosseum — Arena Floor + Underground Hypogeum + Forum",
    "Licensed guide + block booking required · Underground access sells out fast",
    "€150–€200/person (12 pax group)"
])
add_row(tbl, [
    "Rome at Night — Private Walking Tour",
    "Trevi, Pantheon, Navona, Spanish Steps by lamplight · Bill's requested highlight",
    "$250–$300/person (private guide)"
], bg="FFF8F0")
add_spacer(8)

add_h2("Rome — Hotel Options (5 Rooms, June 12–15)", color=NAVY)
add_note_box(
    "Hotel de Russie is my primary recommendation — Rocco Forte service standard, garden courtyard great "
    "for the children, walkable to everything. Hassler is the prestige statement if Bill wants the address "
    "that means something. Either way, 5 rooms in peak June Rome books 6–12 months out — this inquiry needs "
    "to go soon."
)

tbl = make_table(
    ["Hotel", "Est. Rate/Room/Night", "Notes"],
    widths=[2.0, 1.5, 3.0]
)
add_row(tbl, [
    "★ Hotel de Russie (Rocco Forte)\nPRIMARY RECOMMENDATION",
    "$800–$1,400",
    "Walking distance to Spanish Steps and Piazza del Popolo. Secret garden courtyard — ideal for children "
    "and grandparents. Rocco Forte service is among the best in Europe."
])
add_row(tbl, ["Hotel Hassler Roma", "$700–$1,200",
    "At the top of the Spanish Steps. The address in Rome. Rooftop restaurant. If the milestone warrants "
    "the statement hotel — this is it. Bill will know this name."], bg="F9F7F4")
add_row(tbl, ["Sofitel Rome Villa Borghese", "$500–$900",
    "Near Villa Borghese gardens. Connecting rooms available — best multi-gen room configuration. "
    "Slightly better value with no compromise on location."])
add_row(tbl, ["W Rome", "$600–$1,000",
    "Near Trevi Fountain and Spanish Steps. Modern luxury. 148 rooms/suites. Good fallback if above "
    "unavailable for 5 rooms."], bg="F9F7F4")
add_spacer(8)

add_h2("Italy — Ground Transfers", color=NAVY)
tbl = make_table(
    ["Transfer", "Distance / Time", "Est. Cost", "Notes"],
    widths=[2.3, 1.1, 0.9, 2.2]
)
add_row(tbl, ["FCO → Rome Hotel (arrival Jun 12)", "~35 km · 45–60 min", "€300–€400",
    "Private minibus for 12 pax + luggage. Night/early surcharge may apply."])
add_row(tbl, ["Rome Hotel → Civitavecchia Port (Jun 15)", "~90 min · 70 km", "€400–€500",
    "Depart hotel ~10:00 for 12:00 noon embarkation. Private minibus."], bg="F9F7F4")
add_row(tbl, ["Civitavecchia → FCO (Tim's family · Jun 23)", "~90 min · nonstop", "€250–€350",
    "4 pax + 2 strollers. Depart ship ~09:00–09:30 for 14:20 flight."])
add_row(tbl, ["Rome → Florence · High-Speed Train (Jun 23, 8 pax)", "1h 35m Frecciarossa", "€700–€1,300",
    "Business/Club Executive class. Meal included. Book advance — peak summer."], bg="F9F7F4")
add_spacer(8)

add_h2("Florence — Hotel Options (4 Rooms, June 23–25)", color=NAVY)
add_note_box(
    "Four Seasons Firenze for maximum luxury — the private park, the Michelin-starred restaurant, the spa — "
    "this is the 50th anniversary moment in Florence. Portrait Firenze is the intimacy option. Two nights "
    "only, so arrival and departure logistics matter — Florence SMN station is 15–20 minutes from both "
    "properties."
)

tbl = make_table(
    ["Hotel", "Est. Rate/Room/Night", "Notes"],
    widths=[2.0, 1.5, 3.0]
)
add_row(tbl, [
    "★ Four Seasons Firenze\nPRIMARY — Anniversary Experience",
    "$1,200–$2,500",
    "11-acre private park in central Florence. La Magnolia restaurant on the garden terrace. Full spa. "
    "For a 50th anniversary dinner in Florence — there is no better setting."
])
add_row(tbl, ["Portrait Firenze", "$1,000–$2,000",
    "All-suite. 30 meters from Ponte Vecchio. Salvatore Ferragamo family property. Handcrafted interiors. "
    "The choice for those who want Florence to feel personal, not palatial."], bg="F9F7F4")
add_row(tbl, ["The St. Regis Florence", "$900–$1,800",
    "Arno riverfront. Ponte Vecchio views. Historic Brunelleschi-designed palazzo. Exceptional concierge. "
    "Strong fallback at slightly better value."])
add_row(tbl, ["Hotel Bernini Palace", "$400–$800",
    "15th-century building steps from Uffizi and Piazza della Signoria. Best value-to-location option "
    "in the centro storico."], bg="F9F7F4")
add_spacer(8)

add_h2("Florence — Experiences", color=NAVY)
tbl = make_table(["Experience", "Notes", "Est. Price"], widths=[2.2, 3.1, 1.2])
add_row(tbl, [
    "Private Accademia Gallery — Michelangelo's David",
    "Skip-the-line private group · Up to 8 pax · Expert guide · Advance reservation essential",
    "From $1,321 (group of 8)"
])
add_row(tbl, [
    "Private Tuscan Celebration Dinner",
    "Four Seasons La Magnolia (garden terrace) or Sabatini private dining room · 50th Anniversary",
    "Custom quote (via hotel/DMC)"
], bg="F9F7F4")
add_row(tbl, [
    "Chianti Wine Country Day Trip (Optional)",
    "Dario Cecchini's restaurant in Panzano · 45 min from Florence · Legendary experience",
    "Private vehicle + restaurant cost"
])
add_spacer(8)

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION III — SWITZERLAND
# ═══════════════════════════════════════════════════════════════════════════════
add_h1("Section III — Switzerland: Travel Planners & Rail Planning")

add_note_box(
    "Bill is a rail fan — the Swiss Travel Pass + railtour suisse is the combination that delivers "
    "'as much rail as possible.' Clara (15) travels FREE with the Swiss Family Card — it's a genuine "
    "saving. Jungfraujoch sells out for June — book by January 2027 at the latest. Book Victoria-Jungfrau "
    "NOW — June 2027 fills 12–18 months out."
)

# Rail narrative box
tbl_r = doc.add_table(rows=1, cols=1)
cell_r = tbl_r.cell(0, 0)
shade_cell(cell_r, "1E3A5F")
cell_r.text = ""
p_rl = cell_r.paragraphs[0]
rl = p_rl.add_run("🚂  THE RAIL EXPERIENCE — BILL'S MANDATE")
rl.bold = True
rl.font.size  = Pt(8.5)
rl.font.color.rgb = RGBColor(0xF0, 0xC0, 0x40)
p_r2 = cell_r.add_paragraph()
rr = p_r2.add_run(
    "You told me this trip runs on rails, and Switzerland delivers like nowhere else on earth. "
    "The Jungfraujoch railway is the highest in Europe. The Luzern-Interlaken Express passes three lakes "
    "and a waterfall that Wordsworth couldn't have invented. The Bernina Express — if we route through it — "
    "crosses a UNESCO World Heritage viaduct at 2,253 meters. Zermatt bans cars entirely; you arrive by "
    "train, full stop. Every mile between Interlaken and Zurich is a window seat worth having. "
    "This is why you chose Switzerland."
)
rr.font.size  = Pt(10)
rr.font.color.rgb = RGBColor(0xE2, 0xE8, 0xF0)
add_spacer(8)

add_h2("Switzerland — Travel Planner Recommendations", color=GREEN)
add_card(
    "★ Railtour Suisse SA — Primary Recommendation",
    "50+ Years  ·  Bern/Geneva HQ  ·  Group Travel Division  ·  Switzerland Designated Rail Specialist",
    "Switzerland's definitive rail-centric DMC. Their entire product architecture is built around the "
    "country's train network — not just as logistics, but as the experience itself. Venice Simplon-Orient "
    "Express partnerships, Jungfrau region packages, panoramic train programs, luxury hotel combinations. "
    "When you say 'as much rail as possible,' railtour suisse is the operator who translates that mandate "
    "into a working itinerary rather than a travel brochure promise.\n\n"
    "railtour.ch  |  Group travel: railtour.ch/en/group-travel  |  Bern + Geneva offices",
    color=GREEN
)
add_card(
    "Bucher Travel (Bucher Incoming)",
    "160 Years  ·  Lucerne HQ  ·  Own Limousine Fleet  ·  1,500+ Bespoke Programs/Year",
    "One of Switzerland's oldest and most capable DMCs. 90+ staff, own fleet, Lucerne headquarters with "
    "direct access to the Jungfrau region. 10,000+ transfers annually. Their luxury arm is purpose-built "
    "for this profile. Excellent for groups who want a single operator to manage everything.\n\n"
    "+41 41 418 55 55  |  info@buchertravel.ch  |  Pilatusstrasse 27, Lucerne",
    color=GOLD
)

add_h2("Switzerland — Swiss Travel Pass (8 Travelers)", color=GREEN)
add_note_box(
    "Clara (15) travels FREE with the Swiss Family Card — issued free when a parent (Mike or Katie) "
    "purchases a Swiss Travel Pass. For a group of 8 spanning ages 15–74, the 8-day 1st class pass is "
    "the clear choice. It covers everything — trains, buses, lake boats, most mountain railways (with "
    "supplement for Jungfraujoch, but with substantial discount)."
)

tbl = make_table(
    ["Traveler", "Age", "Pass Type", "8-Day 1st Class (2026 ref.)", "Notes"],
    widths=[1.5, 0.5, 1.5, 1.5, 1.55]
)
for row_data in [
    ("Bill Spencer",     "74", "Adult",  "$906",    "Standard adult rate"),
    ("Kathleen Spencer", "72", "Adult",  "$906",    "Standard adult rate"),
    ("Billy Spencer",    "48", "Adult",  "$906",    ""),
    ("Mandy Spencer",    "40", "Adult",  "$906",    ""),
    ("Mike Yaggi",       "50", "Adult",  "$906",    ""),
    ("Katie Yaggi",      "46", "Adult",  "$906",    ""),
    ("Lillie Yaggi",     "18", "Youth",  "~$634",   "~30% youth discount"),
]:
    add_row(tbl, list(row_data))

r = tbl.add_row()
shade_cell(r.cells[0], "F0FDF4")
shade_cell(r.cells[1], "F0FDF4")
shade_cell(r.cells[2], "F0FDF4")
shade_cell(r.cells[3], "F0FDF4")
shade_cell(r.cells[4], "F0FDF4")
cell_text(r.cells[0], "Clara Yaggi", bold=True, color=GREEN, size=9)
cell_text(r.cells[1], "15", size=9)
cell_text(r.cells[2], "FREE — Swiss Family Card", bold=True, color=GREEN, size=9)
cell_text(r.cells[3], "$0", bold=True, color=GREEN, size=9)
cell_text(r.cells[4], "Travels free with parent (Mike or Katie). Card issued free at pass purchase.", size=8.5)

r2 = tbl.add_row()
for c in r2.cells:
    shade_cell(c, "EBF5EE")
cell_text(r2.cells[0], "TOTAL (8 travelers)", bold=True, color=NAVY, size=9)
cell_text(r2.cells[1], "", size=9)
cell_text(r2.cells[2], "", size=9)
cell_text(r2.cells[3], "~$6,070", bold=True, color=NAVY, size=9)
cell_text(r2.cells[4], "All rail + buses + lake boats covered Jun 25 – Jul 2", size=8.5)
add_spacer(4)
add_body(
    "What the Swiss Travel Pass covers: Full SBB rail network, Postbuses, lake boats, 500+ museums. "
    "25% discount on Jungfrau Travel Pass. 50% off Gornergrat Railway and Matterhorn Glacier Paradise. "
    "Significant reduction on most mountain excursions.",
    italic=True, size=8.5, color=GREEN
)
add_spacer(8)

add_h2("Interlaken — Hotel Options (4 Rooms, June 25–30)", color=GREEN)
add_note_box(
    "Victoria-Jungfrau is the correct answer here. 150+ year history, Leading Hotels of the World, direct "
    "Jungfrau view, 5,500 m² spa — exactly right for Bill and Kathleen's anniversary stay. Request a suite "
    "for the principals. Book NOW — this hotel fills June 2027 dates 12–18 months out. A June 2026 inquiry "
    "is on time but not early."
)

tbl = make_table(
    ["Hotel", "Est. Rate/Room/Night", "Notes"],
    widths=[2.2, 1.4, 2.9]
)
add_row(tbl, [
    "★ Victoria-Jungfrau Grand Hotel & Spa\nPRIMARY RECOMMENDATION",
    "CHF 900–1,500",
    "The Swiss Alpine Grand Hotel. 216 rooms. Direct Jungfrau view. Nescens spa (5,500 m²). Three "
    "restaurants. Walking distance to Interlaken Ost rail station. For a 50th anniversary in the Alps — "
    "this is the hotel. Request the Jungfrau View suite for Bill & Kathleen."
])
add_row(tbl, ["Lindner Grand Hotel Beau Rivage", "CHF 600–1,000",
    "Five-star, 101 rooms. Lake Thun and Alps views. Contemporary feel vs. Victoria-Jungfrau's historic "
    "grandeur. Good alternative or supplement if Victoria-Jungfrau cannot accommodate all 4 rooms."], bg="F9F7F4")
add_spacer(8)

add_h2("Switzerland — Excursion Plan", color=GREEN)
add_note_box(
    "Two mountain days recommended: Jungfraujoch (full day) and Zermatt/Gornergrat (full day). Keep "
    "Lauterbrunnen and Grindelwald as half-day options around those anchors. Altitude note for Bill (74) "
    "and Kathleen (72): Jungfraujoch summit is 3,454m — not physically demanding, but the altitude is real. "
    "Warm indoor areas and an acclimatization gallery are on-site. This is a manageable experience; "
    "thousands of seniors do it every year. Pre-advise your group. We loved it."
)

tbl = make_table(["Experience", "Duration / Notes", "Est. Cost"], widths=[2.3, 3.1, 1.1])
add_row(tbl, [
    "Jungfraujoch — Top of Europe Railway",
    "Full day · Highest railway station in Europe · Eiger Express gondola route · 8 pax advance booking required",
    "CHF 261/person (~50% off w/ Swiss Pass)"
])
add_row(tbl, [
    "Zermatt + Gornergrat Railway — Matterhorn Panorama",
    "Full day · Train from Interlaken 2h 15m · Cog railway summit · 360° Matterhorn views · Covered by Swiss Pass",
    "CHF 132/person (~50% off w/ Swiss Pass)"
], bg="F9F7F4")
add_row(tbl, [
    "Lauterbrunnen Valley Walk",
    "Half day · Flat valley path · 72 waterfalls · Trümmelbach Falls · Suitable for ages 15–74 · No booking",
    "Free (covered by Swiss Pass)"
])
add_row(tbl, [
    "Grindelwald First + First Cliff Walk",
    "Half day · Suspended walkway · Eiger views · Gondola from Grindelwald village · All ages accessible",
    "~CHF 68/person (discount w/ Swiss Pass)"
], bg="F9F7F4")
add_row(tbl, [
    "Luzern-Interlaken Express (routing to Zurich)",
    "Jul 1 · Interlaken Ost → Lucerne → Zurich · Lakes Brienz, Lungern, Sarnen · Panoramic windows throughout",
    "Covered (Swiss Travel Pass)"
])
add_spacer(8)

add_h2("Zurich — Hotel Options (4 Rooms, July 1–2)", color=NAVY)
tbl = make_table(["Hotel", "Est. Rate/Room/Night", "Notes"], widths=[2.2, 1.4, 2.9])
add_row(tbl, [
    "★ Baur au Lac\nPRIMARY RECOMMENDATION",
    "$1,200–$2,000",
    "180+ years. Private park on Lake Zurich. Pavillon restaurant (2 Michelin stars). Bahnhofstrasse "
    "shopping is literally walking distance. Virtuoso preferred property — amenity upgrades may apply."
])
add_row(tbl, ["Park Hyatt Zurich", "$700–$1,200",
    "Five-star. City center. 4 restaurants, spa, fitness. Contemporary vs. Baur au Lac's historic elegance. "
    "Good alternative. World of Hyatt group rates possible."], bg="F9F7F4")
add_spacer(8)

add_h2("Zurich — Experiences", color=NAVY)
tbl = make_table(["Experience", "Notes", "Est. Price"], widths=[2.2, 3.1, 1.2])
add_row(tbl, [
    "Lindt Home of Chocolate",
    "Seestrasse 204 · 15 min from city · Advance booking required (sells out) · Chocolate workshop add-on · All ages",
    "CHF 15–20/person"
])
add_row(tbl, [
    "Bahnhofstrasse & Altstadt Shopping",
    "Walking distance from Baur au Lac · Bucherer Swiss watches, major luxury houses, boutique Altstadt",
    "Free (half day)"
], bg="F9F7F4")
add_row(tbl, [
    "Uetliberg — Zurich's Local Mountain",
    "City panorama · 20 min by S-Bahn · Covered by Swiss Travel Pass · Easy half-day option",
    "Covered (Swiss Travel Pass)"
])
add_spacer(8)

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION IV — NEXT STEPS
# ═══════════════════════════════════════════════════════════════════════════════
add_h1("Section IV — Booking Priorities & Next Steps")

add_note_box(
    "This is the action list — these go in order. Victoria-Jungfrau and the United Group Desk are the "
    "two most time-sensitive items. Europe Express and railtour suisse quotes can happen this week. "
    "Jungfraujoch advance booking goes in January 2027. Vatican block booking follows the same timeline."
)

steps = [
    ("1. United Group Desk — Initiate Now (Leg 1, 12 pax)",
     "Call 800-426-1122. Provide date, route, 12 passengers. Request space hold and group fare quote. "
     "2027 rates not yet published — they can hold inventory now. This call is D2M's job; I'll make it on your behalf."),
    ("2. Victoria-Jungfrau — Group Room Inquiry (4 rooms, Jun 25–30)",
     "June 2027 books 12–18 months out. This inquiry is on-time but not early. Request anniversary suite "
     "for Bill & Kathleen. Contact via victoria-jungfrau.ch group desk."),
    ("3. Europe Express — Italy DMC Proposal Request",
     "Call Private Groups line: 800-565-7236. Brief them on 12 pax Rome (Jun 12–15), 8 pax Florence "
     "(Jun 23–25). Request full-service proposal. Get a second quote from Icaterina (+1 718-813-2591) for comparison."),
    ("4. Railtour Suisse — Switzerland Program Request",
     "Contact railtour.ch/en/group-travel. Brief: 8 travelers, rail-centric mandate, Jun 25–Jul 2. "
     "Request turnkey rail program: Interlaken + Zurich, Swiss Travel Pass included, Jungfraujoch + Zermatt anchor days."),
    ("5. Rome + Florence Hotel Room Blocks",
     "Hotel de Russie Rome (5 rooms, Jun 12–15): contact Rocco Forte group desk. Four Seasons Firenze "
     "(4 rooms, Jun 23–25): contact directly. June peak — both fill fast."),
    ("6. Baur au Lac Zurich — Room Block (4 rooms, Jul 1–2)",
     "Short stay (2 nights) — some luxury properties prioritize longer stays in peak season. Book early "
     "and reference the celebration context. +41 44 220 50 20 or info@bauraulac.ch."),
    ("7. Jungfraujoch Group Booking (January 2027)",
     "Book 8-person group via jungfrau.ch by January 2027 at the latest — June sells out months in advance. "
     "Book Lindt Home of Chocolate advance tickets simultaneously."),
]

for title, detail in steps:
    p = doc.add_paragraph()
    r1 = p.add_run(title + "\n")
    r1.bold = True
    r1.font.size  = Pt(10)
    r1.font.color.rgb = NAVY
    r2 = p.add_run(detail)
    r2.font.size  = Pt(9.5)
    r2.font.color.rgb = BLACK
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after  = Pt(6)
    p.paragraph_format.left_indent  = Inches(0.2)

add_spacer(8)
add_body(
    "All flight pricing represents planning-grade estimates based on 2025–2026 published fare data. "
    "Summer 2027 airline schedules and fares open approximately August–September 2026. Hotel pricing is "
    "current-market proxy; 2027 rates not yet published. Swiss Travel Pass pricing reflects 2026 published "
    "rates. DMC and tour operator pricing is market estimate only; actual quotes require direct vendor "
    "engagement. All prices in USD unless noted as CHF or EUR.",
    italic=True, color=DGREY, size=8.5
)

# ── FOOTER / SIG ──────────────────────────────────────────────────────────────
add_spacer(12)
tbl_f = doc.add_table(rows=1, cols=1)
cell_f = tbl_f.cell(0, 0)
shade_cell(cell_f, "000D3A")
cell_f.text = ""
pf1 = cell_f.paragraphs[0]
pf1.alignment = WD_ALIGN_PARAGRAPH.CENTER
rf1 = pf1.add_run("Dreams2Memories Travel")
rf1.bold = True
rf1.font.size  = Pt(13)
rf1.font.color.rgb = RGBColor(0xF0, 0xC0, 0x40)
pf2 = cell_f.add_paragraph()
pf2.alignment = WD_ALIGN_PARAGRAPH.CENTER
rf2 = pf2.add_run("Curating the voyage of your lifetime")
rf2.italic = True
rf2.font.size  = Pt(9)
rf2.font.color.rgb = LTBLUE
pf3 = cell_f.add_paragraph()
pf3.alignment = WD_ALIGN_PARAGRAPH.CENTER
rf3 = pf3.add_run("John Loucks  ·  Owner & Founder  ·  719-291-0742")
rf3.font.size  = Pt(9)
rf3.font.color.rgb = LTBLUE

doc.save(OUT)
print(f"Saved: {OUT}")
