# D2M Brand Palette for Data Visualization

**Source:** CLAUDE.md email standards + Dreams2Memories brand identity  
**Created:** 2026-07-10  
**Purpose:** All Thunderbird dashboards, charts, and visual communications use this palette for consistency.

---

## Primary Brand Colors

| Color | Hex | Usage | Role |
|-------|-----|-------|------|
| **D2M Dark Navy** | `#003087` | Primary surface, text, accents | Primary brand |
| **Cream Paper** | `#f7f3ea` | Background (light mode) | Secondary brand |
| **Gold Accent** | `#d4af37` | Highlights, luxury details | Accent |

**Source:** CLAUDE.md — "Bright blue (#0000ff) paired with cream paper (#f7f3ea) — Commander's pen color"  
*Note: Commander uses #0000ff (pure blue) for personal email; dashboards use #003087 (D2M navy) for consistency.*

---

## Status Palette (Categorical)

Used for states, alerts, and condition codes. Reserved exclusively for status meaning (not for "series 4").

| Status | Hex | Usage | Icon |
|--------|-----|-------|------|
| **Good** | `#2ecc71` | Healthy, active, on-track | ✅ |
| **Warning** | `#f39c12` | Caution, attention needed | ⚠️ |
| **Critical** | `#e74c3c` | Urgent, blocked, error | 🔴 |
| **Neutral/Muted** | `#95a5a6` | Informational, inactive | ⚪ |

---

## Sequential Hue (Magnitude)

Used for single-measure visualizations (heat maps, progress bars, intensity).

**Sequential scale (light → dark):**
- Start: `#e8f4f8` (very light gray-blue)
- Mid: `#7bb3d6` (medium blue)
- End: `#003087` (D2M dark navy)

**Used for:** Memory usage %, pipeline completion %, confidence scores, time-to-deadline.

---

## Diverging Pair (Polarity: positive ← → negative)

Used for showing contrast, deltas, or opposing measures.

| Pole | Hex | Meaning |
|------|-----|---------|
| **Positive/Warm** | `#d4af37` (gold) | Gain, increase, positive trend |
| **Neutral** | `#95a5a6` (gray) | Baseline, no change |
| **Negative/Cool** | `#003087` (navy) | Loss, decrease, negative trend |

**Used for:** Price trends (up/down), commission changes, fare deltas vs. last search.

---

## Categorical Hues (Fixed Order)

When distinguishing multiple series/clients/ships, assign in this fixed order. Never cycle beyond #6.

| Order | Hex | Name | Used For |
|-------|-----|------|----------|
| 1 | `#003087` | Navy | Default, primary series, Thunderbird |
| 2 | `#d4af37` | Gold | Luxury accent, highlight series |
| 3 | `#7bb3d6` | Blue | Secondary client/ship |
| 4 | `#2ecc71` | Green | Tertiary client/ship |
| 5 | `#f39c12` | Orange | Quaternary client/ship |
| 6 | `#e74c3c` | Red | Fifth client/ship |

**Rule:** Do NOT cycle series 7+ (use small multiples, facets, or "Other" bucket instead).

---

## Surfaces (Light & Dark Mode)

### Light Mode (Default)
- **Chart background:** `#f7f3ea` (cream)
- **Grid/axis:** `#d4d4d4` (light gray, recessive)
- **Text (primary):** `#1a1a1a` (almost black)
- **Text (muted/secondary):** `#666666` (mid gray)

### Dark Mode (Alternative)
- **Chart background:** `#1a1a1a` (charcoal)
- **Grid/axis:** `#333333` (subtle, recessive)
- **Text (primary):** `#f7f3ea` (cream)
- **Text (secondary):** `#b0a898` (muted tan)

---

## Mark Specs & Spacing

- **Bar/column width:** 4px, rounded top-ends, 2px surface gap between adjacent fills
- **Line weight:** 2px (thin)
- **Marker size:** ≥8px (circles, diamonds)
- **Hover overlay:** 2px ring on overlapping marks, 4px expansion on hover
- **Direct labels:** selective (1–3 key points per line), white text on color fill (if contrast passes)

---

## Validation Checklist

Before shipping any chart/dashboard:

- [ ] Run `node scripts/validate_palette.js` for categorical palette
  - CVD separation ≥ 12 (goal), ≥ 8 (minimum)
  - Lightness band check (all ≥ L30 for dark text, ≤ L70 for light text)
  - Chroma floor (≥ 30 for categorical, ≥ 20 for sequential)
  - Contrast: text on color ≥ 4.5:1 (WCAG AA)
- [ ] All status colors appear with label + icon (never color alone)
- [ ] Sequential/diverging single-hue ✓
- [ ] Categorical fixed order (not cycled) ✓
- [ ] Marks: thin, spacers, hover layer ✓
- [ ] Accessibility: legend (≥2 series), table view, dark mode option ✓
- [ ] No dual-axis charts (split to small multiples if needed)
- [ ] Text uses text tokens, not series colors ✓

---

## Examples (By Initiative)

### Initiative A: Morning Brief Dashboard
- **Background:** Cream (#f7f3ea)
- **Primary UI:** Dark navy (#003087)
- **Status gauges:** Good/warning/critical palette
- **Pipeline bar:** Sequential light-to-navy
- **FPD countdown:** Gold (#d4af37) for "urgent", green for "on-track"

### Initiative B: Flight Research & Route Maps
- **Route map:** Navy (#003087) for Great Circle, gold accent for selected route
- **Fare matrix:** Sequential scale (light = cheap, dark = expensive)
- **Price trend line:** Diverging (gold up-trend, navy down-trend)

### Initiative C: Dossier Cards
- **Card background:** Cream (#f7f3ea)
- **Client accent bar:** Categorical hue (1st client = navy, 2nd = gold, etc.)
- **Payment ladder:** Sequential (light = unpaid, dark = paid)

---

## Palette Validator Script

**Location:** `/home/john/Thunderbird/scripts/validate_palette.js`

**Usage:**
```bash
node scripts/validate_palette.js "#003087,#d4af37,#7bb3d6,#2ecc71,#f39c12,#e74c3c" --mode light
```

**Output:** Pass/Fail on lightness, chroma, CVD separation, contrast.

---

**Last Updated:** 2026-07-10  
**Keeper:** Hale (Visual Communications Lead)  
**Next Review:** 2026-08-10 (monthly brand audit)
