# Templates — D2M Template Pipeline

## Template Files
| File | Purpose |
|------|---------|
| `d2m_base.css.j2` | Brand CSS partial — navy/gold tokens, all component styles |
| `hotel_guide.html.j2` | Hotel guide template — 4 overridable blocks |
| `d2m_hotel_guide_schema.py` | Python dataclasses + `render_to_pdf()` helper |
| `dani_validation_email.html.j2` | Client email stationery — navy banner, cream paper, blue ink |

## Template Blocks (Overridable)
| Block | Contents |
|-------|----------|
| `cover` | Cover page — client name, destination, meta strip, geometric arch |
| `hotel_cards` | Loop over hotels — photos, price box, rates table, distances |
| `comparison` | Side-by-side comparison + recommendation cards |
| `logistics` | Transport grid + info box + footnotes |

## Data Contract Rules (STRICT)
- All currency pre-formatted as strings via `fmt_usd()` — **NEVER format inside templates**
- Photos as base64 data URIs — index 0 = main, 1-2 = sidebar
- `PriceBox.prestige=True` flips gold box to purple (over-budget/5-star)
- `RoomRate.is_pick=True` highlights row in gold
- `Landmark.nearest=True` renders gold NEAREST badge
- `CompRow.cancel_class`: `ok` (green) | `no` (red) | `tbd` (muted)
- Badge classes: `value` | `location` | `experience` | `luxury` | `local`

## CSS Brand Tokens
| Variable | Value · Usage |
|----------|---------------|
| `--navy` | #0d1b2e · Primary background |
| `--navy2` | #152540 · Secondary background |
| `--navy3` | #1e3358 · Card/contact box background |
| `--gold` | #c9a84c · Primary accent, borders, labels |
| `--gold-light` | #e8c97a · Price amounts, highlights |
| `--gold-pale` | #f5e9c8 · Subtle gold tint |
| `--muted` | #8a9ab5 · Secondary text, metadata |
| `--prestige-*` | #7a5a9a / #4a2a6a · Over-budget/5-star purple tier |

## Render One-Liner
```python
from d2m_hotel_guide_schema import HotelGuideContext, render_to_pdf
ctx = HotelGuideContext(doc=..., hotels=[...], comparison=[...], ...)
render_to_pdf(ctx, 'output/ClientName_Destination_MonYYYY.pdf')
```

## Email Stationery — BRAND STANDARD (updated 2026-03-23)
- **Ink:** `#0000ff` bright blue — Commander's pen. ALL templates. NEVER substitute.
- **Paper:** `#f7f3ea` cream — email-wrapper / content area background
- **Surround:** `#eee8db` warm linen — body/outer background
- **Banner:** `#0d1b2e` navy — header background, logo area, bottom bar
- **Gold accent:** `#c9a84c` — rules, labels, agent title, bottom bar text
- **Font:** Georgia, 'Times New Roman', serif — NO Google Fonts (stripped by Gmail)
- Baked into `_wrap_body_html()` in `thunderbird_gmail.py` — auto-applied to plain-text wrapping
- `tier1_correspondence.html.j2` — canonical Jinja2 template for all client correspondence
- `dani_validation_email.html.j2` — Dani's rich trip validation template
- All templates synced to same brand tokens as of 2026-03-23
- Never override per-email — stationery is brand standard

## Context Engineering (Wired 23 MAR 2026)
All documents generated from context packs — never raw prompts.
See `../context_engineering/CONTEXT_ENGINEERING.md` for full framework.
See `../context_engineering/context_packs.py` for all 4 doc type schemas.

### Document Workflow (MD → Drive → Google Doc → Final)
1. Generate draft as `.md` → save to Google Drive `/D2M Trip Dossiers/[Client]/`
2. Telegram Commander with link
3. Commander edits in Google Doc
4. COS captures diff → Learning Compiler extracts principles
5. Format final → PDF (WeasyPrint) or HTML → deliver via Gmail/Telegram

### Context Pack → Template Mapping
| Context Pack | Template | Renderer |
|--------------|----------|----------|
| `ProposalContextPack` | `dani_proposal.html.j2` | `d2m_proposal_schema.render_to_pdf()` |
| `ItineraryContextPack` | `dreams2memories_itinerary.html` | WeasyPrint direct |
| `TripValidationContextPack` | `dani_validation_email.html.j2` | Gmail stationery |
| `EmailContextPack` | `tier1_correspondence.html.j2` | `_wrap_body_html()` |
