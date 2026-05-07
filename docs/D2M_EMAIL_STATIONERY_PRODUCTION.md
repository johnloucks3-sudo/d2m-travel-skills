# D2M Email Stationery — Production Process Reference
**Version 1.1 | 2026-05-07 | Dreams2Memories Travel, LLC**
**Maintained by: COS Hale**

---

## TWO STATIONERY SYSTEMS

Thunderbird uses two separate email stationery systems for different audiences.

### System A — Client Stationery (`_wrap_body_html`)
Client-facing correspondence. Warm luxury aesthetic.

| Element | Value |
|---------|-------|
| Background surround | Warm linen `#eee8db` |
| Paper card | Crane's Ecru cream `#f7f3ea` |
| Ink color | Bright blue `#0000ff` (Commander's pen — non-negotiable) |
| Typography | Georgia, 'Times New Roman', serif — 10.5pt, 1.6 line-height |
| Logo banner | Full-width navy `#0d1b2e`, centered `Agency_Logo_email.png` as base64 |
| Gold rule | 2.5px top-rule, 50% opacity (`rgba(201,168,76,0.50)`) |
| Card shadow | Two-layer box-shadow (light) |
| Max-width | 640px centered |

**Function:** `_wrap_body_html()` in `core/email/thunderbird_gmail.py`

Used by: `gmail_create_draft()`, `gmail_send_email()`, `_send_or_draft_as_persona()`

---

### System B — Staff Persona Stationery (`_wrap_staff_html`)
Wing-to-Commander internal communications. Each persona has a distinct visual identity.

**Function:** `_wrap_staff_html(body, persona_id)` in `core/email/thunderbird_gmail.py`

**Persona config:** `_STAFF_PERSONA_CONFIGS` dict — name, title, accent color, email

**Icon system:** `_get_staff_icon_html(persona_id, accent)` — persona-specific badge/seal

---

## COS COMMAND TEMPLATE — DESIGN SPECIFICATION
*Added 2026-05-07 per Commander direction: "save the procedure for doing this and apply to the D2M stationery production process"*

### Visual Identity
The COS template uses a **Command Channel aesthetic** — dark navy-black panels, gold accents, centered authority block. Distinct from client stationery by design (internal vs. outbound).

| Element | Value |
|---------|-------|
| Deep background | `#08090C` (near-black) |
| Header/footer panels | `#0F1419` (dark navy-black) |
| Primary text | `#D4DCE5` (cold white) |
| Secondary text | `#5C6B7A` (steel grey) |
| Accent (gold) | `#C9A227` |
| Top stripe | 4px solid gold |
| Bottom stripe | 2px solid gold |

### Header Layout — Centered Command Block
The COS header is a **single centered column** — do NOT use a 3-column table layout.

Order (top to bottom, all centered):
1. `<div>` containing 80px 4-ring eagle seal
2. IVH monogram — 20pt Georgia, 900 weight, 4px letter-spacing
3. Role label — 6.5pt Arial Black, DIRECTOR OF STAFF ► THUNDERBIRD WING
4. Full name — 13.5pt Georgia, 700 weight: `VICTORIA I.V. HALE, COLONEL, USAF (Ret'd)`
5. Org line — 7pt Arial, CHIEF OPERATING OFFICER • DREAMS2MEMORIES TRAVEL, LLC
6. COMMAND CHANNEL badge — inline-block, gold border, 6pt Arial Black

### 4-Ring Eagle Seal (80px)
```python
# Nested divs: gold(80) → black(70) → gold(58) → black(46) → eagle emoji
'<div style="display:inline-block;width:80px;height:80px;
border-radius:50%;background:{accent};">
  <div style="width:70px;height:70px;margin:5px;border-radius:50%;background:{deep};">
    <div style="width:58px;height:58px;margin:6px;border-radius:50%;background:{accent};">
      <div style="width:46px;height:46px;margin:6px;border-radius:50%;background:{deep};
      line-height:46px;text-align:center;font-size:24pt;">🦅</div>
    </div>
  </div>
</div>'
```
**Why 4 rings:** Rank distinction. Other staff use 2-ring or 3-ring seals. COS gets the full command seal.

### Mini Seal (Sig Block, 42px)
2-ring version for the signature block. Gold outer → black inner → eagle at 17pt.

### USAF O-6 Name Format (Standing Order 2026-05-07)
```
VICTORIA I.V. HALE, COLONEL, USAF (Ret'd)
```
Rules:
- Full first name (not abbreviated)
- Middle initials with periods: `I.V.`
- Last name
- Grade spelled out: `COLONEL` (not `Col.`)
- Branch: `USAF`
- Status: `(Ret'd)` — with curly apostrophe (`&rsquo;`)

**HTML encoding:** `VICTORIA I.V. HALE, COLONEL, USAF (Ret&rsquo;d)`

### Titles — Director of Staff / COO
The COS holds two titles displayed as a compound line:
- **Header label:** `DIRECTOR OF STAFF ► THUNDERBIRD WING`
- **Sig block:** `Director of Staff · COO · Thunderbird Wing`
- Do NOT use "Chief of Staff" — that is a colloquial term, not the formal title

### Sig Block Layout
Table with 2 columns: mini seal (left, 56px) | name + title + email (right).

---

## GMAIL-SAFE RULES (Both Systems)

1. **All inline styles** — no `<style>` blocks. Gmail strips them.
2. **No SVG** — Gmail strips SVGs. Use emoji (🦅) or CSS div badges instead.
3. **No external fonts** — embed or use system fonts (Arial, Georgia).
4. **No position:fixed, transform, animation** — sanitized by Gmail.
5. **Tables > divs for layout** — use `<table>` with `cellpadding="0" cellspacing="0"` for multi-column.
6. **Images as base64 data URIs** — no external hosting needed; survives Gmail caching.
7. **Centered layouts** — use `text-align:center` on container div, not `margin:auto` alone.

---

## ADDING OR MODIFYING A STAFF PERSONA TEMPLATE

### Step 1 — Update `_STAFF_PERSONA_CONFIGS`
```python
"PERSONA_ID": {
    "name": "FULL NAME, GRADE, BRANCH (Status)",  # USAF O-6 format if applicable
    "suffix": "",
    "title": "Title &nbsp;&middot;&nbsp; Role &nbsp;&middot;&nbsp; Unit",
    "accent": "#HEXCOLOR",
    "email": "email@address.com",
},
```

### Step 2 — Update `_get_staff_icon_html`
Add a branch for the persona's icon/seal badge. COS gets 4-ring; others use 2-ring or standard icon.

### Step 3 — Add/Update Template Branch in `_wrap_staff_html`
For standard personas, no branch needed — they use the default template which reads from `cfg`.
For COS (and any future command-level persona), a dedicated branch is required.

### Step 4 — Test with a live send
```python
from core.email.thunderbird_gmail import gmail_send_from_wing
result = gmail_send_from_wing(
    to="johnloucks3@gmail.com",
    subject="Template Test — [PERSONA]",
    body="<p>Test body.</p>",
    persona_id="PERSONA_ID"
)
```
Run with: `PYTHONPATH=/home/john/Thunderbird/api:/home/john/Thunderbird python3 script.py`

### Step 5 — Confirm render in Gmail
Open johnloucks3@gmail.com and verify:
- Logo/seal renders (no broken image)
- Background color correct
- Name/title format correct per this document
- No missing styles (check mobile + desktop view)

---

## DESIGN HISTORY

| Date | Change | Commander Feedback |
|------|--------|--------------------|
| 2026-03-16 | Client stationery finalized | Approved cream + blue combo |
| 2026-05-06 | COS command template v1 built | "love these colors and I am impressed it all came out" |
| 2026-05-07 | COS template v2 — centered layout, O-6 name, DoS/COO titles | Per Commander corrections |

---

*Col Victoria "Iron Vic" Hale — COS | Updated 2026-05-07*
