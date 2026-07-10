# Flight Research Dataviz — Design Spec
**Track B: Flight Route Maps & Fare Visualizations · 2026-07-10**
**Owner:** Thunderbird Wing (dataviz skill applied) · **Brand source:** `references/palette_d2m_brand.md`

Three components for the flight research workflow (Centrav/Kiwi/Google Flights →
fare_watches.json / fare_history.json → the per-trip HTML artifacts already
produced by `scripts/loucks_silvernova_artifact_refresh.py` and
`scripts/spencer_grandtour_flight_daily_recheck.py`).

All three follow the dataviz skill procedure: **form → color → validate →
marks → interaction → accessibility**. Color is assigned last, and every
palette below was run through `validate_palette.js`, not eyeballed.

---

## Component 1 — Great Circle Route Map (SVG)

**Form:** two-point spatial relationship (origin → destination) + a magnitude
label (distance). Not a categorical/identity chart — one route, two
endpoints — so this is closer to a diagram than a data series.

**Color assignment:**
| Element | Color | Job |
|---|---|---|
| Route line (great-circle path) | D2M navy `#003087` | Brand-ink stroke — same role as an axis or reference line, not a competing series identity |
| Endpoint markers | Gold `#d4af37` | Single accent, always paired with a direct IATA-code label |
| Surface | Cream `#f7f3ea` | Matches every existing flight-option artifact |

**Why the navy line is exempt from the categorical checks:** the skill's six
checks (`references/color-formula.md`) govern *categorical identity*
palettes — 2–8 hues competing for attention in the same chart. A single
route stroke isn't competing with anything; it plays the same role as a
gridline or axis, which the skill explicitly scopes out ("does not judge a
lone status/text color"). Validated as a WCAG *contrast* pair instead:

```
navy #003087 vs cream #f7f3ea → 10.70:1   (WCAG AA text-contrast requires 4.5:1 — passes with large margin)
```

**Gold endpoint markers — validator result (2-slot set, `--pairs all` per
scatter/map convention):**
```
node scripts/validate_palette.js "#003087,#d4af37" --mode light --surface "#f7f3ea" --pairs all
  [PASS] CVD separation      ΔE 123.6 (protan) — enormous margin
  [WARN] Contrast vs surface  #d4af37 at 1.9:1 — below 3:1, relief required
```
**Mitigation (mandatory, not optional):** every gold marker ships a direct
IATA-code label in bold navy text directly above it, plus a 1.5px navy
outline ring on the dot itself for edge definition. This is the skill's
documented relief for a sub-3:1 mark — never color alone.

**Marks:** 2px navy stroke, round line caps · 6px gold circle endpoints with
1.5px navy ring · bold 12px direct IATA labels · 9px muted city/country
sub-labels · header line states distance in nm and statute miles.

**Implementation:** `core/dataviz/great_circle_map.py` (pure stdlib —
haversine distance + spherical-slerp interpolation, equirectangular
projection, no network/tile dependency) backed by
`core/dataviz/airports.py` (IATA → lat/lon table, ~130 airports covering
every current D2M route + major world hubs). Unknown IATA codes degrade to
a labeled placeholder card, never an exception.

**Accessibility:** `role="img"` + `aria-label` states the full route and
distance in words on the `<svg>` root, so the map is announced even where
the visual doesn't render.

---

## Component 2 — Fare Comparison Heatmap

**Form:** magnitude across two dimensions (cabin/carrier × date) — a true
sequential job.

**Color assignment:** ONE hue (D2M navy family), light → dark = cheap →
expensive, per the skill's sequential rule ("one hue, steps light→dark").

**Ramp (light mode) — `references/color-formula.md` ordinal check, not the
categorical six (a sequential ramp fails the categorical check *by design*
per the skill — don't "fix" a correct ramp to satisfy the wrong validator):**
```
node scripts/validate_palette.js "#7ba8cc,#5f88bb,#3d6ea5,#1f4f93,#003087" --mode light --surface "#f7f3ea" --ordinal
  [PASS] Lightness monotone      steps read light→dark
  [PASS] Adjacent ΔL             all gaps >= 0.06
  [PASS] Light-end contrast      #7ba8cc at 2.28:1 vs surface
  [PASS] Single hue              hue spread 18°
  → ALL CHECKS PASS
```

**Ramp (dark mode) — re-anchored, not a blind inversion.** The skill notes
sequential ramps "flip anchor in dark": the true brand navy `#003087` sits
too close to a `#1a1a1a` dark surface (1.47:1, fails the 2:1 floor), so the
dark-pole step is lightened to `#2f5aa8` for this mode only. Light-mode
artifacts keep the true brand navy at full saturation.
```
node scripts/validate_palette.js "#eaf2fa,#b9d3ea,#7ba8cc,#4877c9,#2f5aa8" --mode dark --surface "#1a1a1a" --ordinal
  [PASS] Lightness monotone      steps read light→dark
  [PASS] Adjacent ΔL             all gaps >= 0.06
  [PASS] Light-end contrast      #2f5aa8 at 2.61:1 vs surface
  [PASS] Single hue              hue spread 18°
  → ALL CHECKS PASS
```

**Marks:** 5-step ramp, 2px cream/dark-surface gap between adjacent cells
(the skill's stacked/adjacent-fill spacer rule) · cell text auto-switches
white/dark ink by luminance so the price is always legible on its own fill
· empty cells render as a muted dash, never a colored zero.

**Interaction:** hover/focus tooltip per cell (route + cabin + exact price +
notes) · every heatmap ships a `<details>` "View as table" flat table by
default — not a toggle a user has to discover, an always-present element.

**Legend:** always present (sequential magnitude needs a scale key) — shown
as min/max price labels flanking the 5-step ramp swatches.

**Implementation:** `app/static/js/dataviz/fare_heatmap.js` — vanilla JS,
zero dependencies, safe DOM construction throughout (no `innerHTML` with
data-derived strings — fare notes/labels are free text from scraped
sources and must never be interpreted as markup).

---

## Component 3 — 30-Day Price Trend Line (Diverging)

**Form:** one route/cabin's fare over time, read against a baseline — a
polarity job (above/at/below baseline), not a plain magnitude job. This is
why it's diverging rather than sequential.

**Color assignment:** gold (`#d4af37`, above baseline) ← gray (`#95a5a6`,
within ±1% of baseline) → navy (`#003087`, below baseline).

**Validation approach — deliberately NOT the categorical CLI.**
`references/color-formula.md` is explicit: *"For sequential/diverging, the
check is lightness monotonicity across the ramp, not adjacency CVD —
running the categorical validator on a sequential ramp will FAIL by design
… don't 'fix' a good ramp to satisfy it."* Running it anyway confirms
that warning (included for the record, then set aside):
```
node scripts/validate_palette.js "#d4af37,#95a5a6,#003087" --mode light --surface "#f7f3ea" --pairs all
  [FAIL] Lightness band     #003087 outside the categorical L-band (0.347 < 0.43 floor)
  [FAIL] Chroma floor       #95a5a6 reads as gray (C 0.018) — correct, it IS the neutral
  → expected FAIL, not a real problem (see color-formula.md above)
```

**Manual lightness-monotonicity check (the correct test for this job),
OKLCH L per color:**
```
navy  #003087   L=0.347  C=0.153
gray  #95a5a6   L=0.710  C=0.018   (midpoint — lowest chroma by design, reads neutral)
gold  #d4af37   L=0.767  C=0.139
```
- **Down arm** (midpoint → navy pole): L 0.710 → 0.347, monotonically
  decreasing. ✅ Clean, large steps.
- **Up arm** (midpoint → gold pole): L 0.710 → 0.767, monotonically
  increasing but a small gap (Δ0.057) — gold is D2M's brand accent and is
  already near its practical lightness ceiling before it desaturates into
  cream. The up-arm's separation from the midpoint is carried mostly by
  **chroma** (0.018 → 0.139), a legitimate secondary diverging construction,
  but it's the one accepted brand-constraint tradeoff in this spec.
  **Mitigation:** every point that isn't gray-classified carries a numeric
  `+X%`/`-X%` direct label in the table view, and first/last points are
  always direct-labeled on the chart itself — color is never the only
  signal for direction.

**Marks:** 2px line, segment-colored by the *arriving* point's
classification (so a run of "up" days paints gold, "down" paints navy) ·
3px point markers, 6px on first/last (Chart.js `pointRadius` array) · 1px
dashed gray baseline reference line, labeled in the legend and tooltip ·
tension 0.15 (slight smoothing, not enough to hide reversals).

**Interaction:** Chart.js `interaction: {mode:'index', intersect:false}` —
a crosshair-style hover across the full date axis, tooltip states exact
price and %-vs-baseline. **One axis only** (price, $/pp) — date range and
cabin are filters/labels, never a second y-scale.

**Accessibility:** bottom legend (3 states, always shown — 2+ series rule)
+ a `<details>` table view listing every point's date/price/%-vs-baseline
in text, satisfying the mandatory relief for any WARN-band contrast points.

**Implementation:** `app/static/js/dataviz/price_trend_chart.js` — wraps
Chart.js (already the established convention in this repo; see the
existing `trendChart` canvas in
`output/loucks_silvernova_2027_flight_options.html`) with the diverging
classification logic. Reads the same `baseline_price_pp` /
`current_price_pp` fields already present in
`core/travel/data/fare_watches.json`, so no new data pipeline is required.

---

## Cross-cutting rules applied to all three

- **No dual-axis charts.** Trend line is single-axis; heatmap and route map
  aren't axis charts at all.
- **Categorical hues never cycled beyond the brand's fixed 6.** None of
  these three components use a rotating categorical palette — route map is
  a 2-color accent pair, heatmap and trend line are sequential/diverging.
  If a future multi-route overlay is added to the trend line (e.g.
  comparing DEN-VCE and ATH-DEN on one chart), it must use the brand's
  fixed categorical order from `palette_d2m_brand.md` and be re-validated
  with `--pairs all` (small-multiples/overlay scope) — flagging this now so
  it isn't skipped later.
- **Dark mode is a selected variant, not an automatic flip.** Only the
  heatmap currently has an explicit dark ramp (re-anchored per above); the
  route map's cream surface and the trend line's Chart.js theme should get
  the same explicit dark-mode pass before shipping a dark-mode toggle in
  the UI — logged as a follow-up, not done here.
- **Every chart renders and was eyeballed**, not just validated by script —
  see `output/dataviz_demo_flight_charts.html` (component 6 of this track).

## Files

| File | Component |
|---|---|
| `core/dataviz/airports.py` | IATA → lat/lon lookup |
| `core/dataviz/great_circle_map.py` | Component 1 — route map SVG generator |
| `app/static/js/dataviz/fare_heatmap.js` | Component 2 — fare heatmap |
| `app/static/js/dataviz/price_trend_chart.js` | Component 3 — diverging trend line |
| `scripts/flight_route_visuals_refresh.py` | Workflow integration (component 5) |
| `output/dataviz_demo_flight_charts.html` | Rendered demo, all 3 components (component 6) |
