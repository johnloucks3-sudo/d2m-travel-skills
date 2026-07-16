# ITINERARY BRAND SPEC — Canonical Hex Reference
## Dreams2Memories Travel, LLC · Itinerary Builds Only
**Effective:** 2026-07-16
**Owner:** EXEC (Naia Solberg-Vega)
**Status:** SINGLE SOURCE OF TRUTH for itinerary hex values — supersedes inline hex in `standing_orders/SO_ITINERARY_ZERO_LATITUDE_PIPELINE_20260715.md`

---

## WHY THIS FILE EXISTS

The zero-latitude SO (2026-07-15) inlined hex values directly into its Stage 4 checklist. Inlined values drift out of sync with the email brand-guidelines skill and with the actual code that renders itineraries the moment either changes without the other. This file is the fix: **one canonical table, referenced by name, never copy-pasted.**

This spec covers **itinerary builds only** (`cruises_web/*.html`, `scripts/render_darknavy_doc.py`, `itinerary/*.py`). It is a sibling to, not a replacement for, the email brand-guidelines skill (`~/.claude/skills/brand-guidelines/SKILL.md`), which governs client emails. The two share one anchor point — dark navy `#07076b` — and diverge everywhere else, because emails and itineraries are different surfaces with different rendering histories. Do not import email-only values (cream `#f7f3ea` background, bright-blue `#0000ff` ink) into itinerary builds. Those are retired for emails and were never canonical for itineraries.

**Evidence base for every value below:** cross-checked against the actual rendered gold-standard builds — `cruises_web/itinerary_grandeur.html` and `cruises_web/itinerary_nova.html` (master templates, zero client customization), plus five live client builds (`itinerary_grandeur_nichols.html`, `itinerary_grandeur_elydarrow.html`, `itinerary_grandeur_furlow.html`, `itinerary_splendor_lyons.html`, `itinerary_splendor_lyons_v2.html`) and the token files `core/visual_synthesis/theme_tokens.py` / `core/hale/d2m_brand_tokens.py`. Not asserted from memory — grepped and counted.

---

## 1. CORE PALETTE

| Role | Hex | Notes |
|---|---|---|
| **Navy** (background/base) | `#07076b` | Confirmed identical across every file checked — master templates, all client builds, both token files. No dispute. |
| **Gold** (accent) | `#c8a400` | **See §3 — corrects the SO, which named `#c9a84c`.** |

---

## 2. ELEMENT → HEX LOOKUP TABLE (zero-latitude: look up the class, use the hex, no judgment)

| CSS class / element | Hex | Role |
|---|---|---|
| `body`, page background | `#07076b` | Navy base |
| `.day-num` | `#c8a400` | Gold — large day-number numeral |
| `.stat-val` | `#c8a400` | Gold — ship stat value |
| `.block-time` (font-size 11px variant) | `#c8a400` | Gold — schedule block time label |
| `.exc-lbl` | `#c8a400` | Gold — excursion label |
| Footer company-name treatment ("DREAMS2MEMORIES TRAVEL, LLC") | `#c8a400` | Gold — **normalize to this; do not use `#c9a84c` here, see §3** |
| `h1`, `.wordmark`, `strong` | `#f0f6ff` | Near-white, blue-tinted — top banner / bold emphasis |
| `.port-name`, `.voyage-title`, `.open-title` | `#f7f3ea` | Off-white — **flagged, not resolved this cycle, see §4** |
| `p`, `ul`/`ol`, `.date-day`, `.block-val`, `.exc-time` (value) | `#e8f1ff` | Primary body text on navy |
| `.port-sub`, `.ship-stats`, `.footer a`, `h3`, body `a` (links), `em` | `#a8c4f0` | **Muted/secondary text — general use.** This is the value the SO omitted. |
| `h2`, `h4`, `.day-dow`, `.exc-note`, blockquote text | `#c8dcff` | Muted/secondary text — sub-headers and notes |
| `.date-mon` **only** | `#a8c8ff` | **Highlight/indicator — reserved for the month indicator, not general muted text.** This is the value the SO listed but misapplied as a general-purpose muted blue. |
| Table header (`th`) background | `#0a0a68` | |
| Table header (`th`) text | `#e8f1ff` | |
| Table cell (`td`) text | `#d0e4ff` | |
| Footer fine-print (address/contact line) | `#8fa8d8` | |

**The `#a8c4f0` vs `#a8c8ff` conflict, resolved:** these are not competing values for the same role — they are two different values doing two different jobs, both correctly present in every real build checked. `#a8c4f0` is the workhorse muted color (port subtitles, ship stats, footer links, links, `h3`, `em` — 3-5 uses per document). `#a8c8ff` is reserved exclusively for `.date-mon`, the month indicator under each day number (1 use per day-block). The SO's "three pre-screened contrast blues" list (`#c8dcff` / `#e8f1ff` / `#a8c8ff`) silently dropped `#a8c4f0` even though it is the most-used muted value in every real build. The email brand-guidelines skill's list (`#e8f1ff` / `#a8c4f0` / `#c8dcff`) is the one that matches real itinerary output — except it's written for emails and doesn't carve out `#a8c8ff`'s narrow, correct role. **Both partial lists were right about the values they included and wrong by omission.** The table above is the complete, role-assigned version of both.

---

## 3. GOLD — CORRECTING THE SO'S `#c9a84c`

The SO stated "gold = `#c9a84c` exactly, no substitute." This does not match the evidence:

| File | `#c8a400` count | `#c9a84c` count |
|---|---|---|
| `itinerary_grandeur.html` (master template) | 15 | **0** |
| `itinerary_nova.html` (master template) | 19 | **0** |
| `itinerary_grandeur_nichols.html` | 15 | 1 |
| `itinerary_grandeur_elydarrow.html` | 15 | 1 |
| `itinerary_grandeur_furlow.html` | 15 | 1 |
| `itinerary_splendor_lyons.html` | 37 | 1 |
| `itinerary_splendor_lyons_v2.html` | 37 | 1 |

`#c8a400` is the structural gold — it's baked into the CSS classes (`day-num`, `stat-val`, `block-time`, `exc-lbl`) that every build inherits from the master templates, and it appears 15-37 times per document. It also matches `theme_tokens.py`'s `GOLD_ACCENT`.

`#c9a84c` appears exactly once per client document, only in a footer treatment added per-client after the fact — it is absent from both master templates (`itinerary_grandeur.html`, `itinerary_nova.html`), meaning it was never rolled into the canonical template at all.

**Canonical call: gold = `#c8a400` everywhere, including the footer.** The five client builds carrying a stray `#c9a84c` in the footer are a minor, low-visibility drift (one inline style, footer only) — not urgent to retroactively patch already-sent client documents, but new builds should use `#c8a400` in the footer too, and Sterling (A7) should normalize the five existing files next time any of them is touched for another reason.

**Flag to Commander:** this reverses an assumption in the task brief that gold was already-settled at `#c9a84c`. The evidence points the other way — `#c8a400` is both the dominant real-world value and the token-file value. If there's a reason `#c9a84c` was chosen deliberately for the footer (a distinct "signature" gold vs. "data" gold), that reason isn't recorded anywhere I found — Commander correction welcome, but absent that, `#c8a400` is the defensible single value.

---

## 4. KNOWN DRIFTS — FLAGGED, NOT FIXED THIS CYCLE (owner: Sterling A7 / Whetstone A14)

These are real inconsistencies found during this reconciliation that are **out of scope for this doc's mandate** (navy/gold/contrast-blue only) but should not be silently lost:

1. **`theme_tokens.py` gold drift:** `core/visual_synthesis/theme_tokens.py` defines `GOLD_ACCENT = "#c8a400"` — this matches §3's canonical call, no action needed there. Confirmed consistent, noting for completeness.
2. **`theme_tokens.py` `.port-sub` drift:** `theme_tokens.py`'s `get_print_safe_stylesheet()` maps `.port-sub` to `TEXT_MUTED` (`#c8dcff`). Every real rendered build uses `#a8c4f0` for `.port-sub` instead (see §2 table). If any build path actually calls `theme_tokens.py`'s stylesheet function for `.port-sub` today, it is rendering the wrong shade. Needs a code fix in `theme_tokens.py`, not a doc fix — routing to Sterling.
3. **Heading white split:** `#f0f6ff` (wordmark/h1/strong, from `render_darknavy_doc.py`) vs `#f7f3ea` (port-name/voyage-title/open-title, from the actual client HTML files, matching `theme_tokens.py`'s `TEXT_HEADING`). Two different renderers, two different "off-white" values, both currently live. Not reconciled here because it wasn't part of this cycle's mandate — flagged so it doesn't get lost. Worth noting `#f7f3ea` is also the retired cream **email** background hex; it's a different application (text-on-navy, not paper background) so it isn't automatically wrong here, but the coincidence is worth Sterling's eye.

---

## 5. WHAT THIS FILE DOES NOT COVER

- Email stationery, cream paper, blue ink — see `~/.claude/skills/brand-guidelines/SKILL.md`
- Dashboard/TCD chrome tokens — see `core/hale/d2m_brand_tokens.py` (separate palette, separate purpose, per its own docstring)
- Typography, layout, voice — unchanged, see `reference_itinerary_production_process.md`

**Any future palette change for itinerary builds edits this file first, then propagates to code.** Do not re-inline hex values into standing orders, skills, or checklists — reference this file by path.
