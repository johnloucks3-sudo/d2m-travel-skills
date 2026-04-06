# HTML LIFECYCLE CHART REDESIGN — COMPLETE
## Claude → Goose | April 2, 2026

---

### STATUS: ✅ ALL 4 FILES REWRITTEN

**Files updated:**
- `output/Furlow_Nichols_Ely_Lifecycle.html`
- `output/Kuklinski_Morton_Lifecycle.html`
- `output/McLeod_June_Lifecycle.html`
- `output/Loucks_Japan_Lifecycle.html`

---

### DESIGN PHILOSOPHY — ANCHOR vs FLUID

**The flaw in the original Mermaid Gantt:** It treated all items as equal blocks on a rigid time axis. The Commander's actual lifecycle is fundamentally bifurcated:

**ANCHOR ZONE (top, deterministic):**
- Displayed as: horizontal spine + milestone nodes with stems
- Nodes are: Initial contact → Deposit → FPD → Booking windows (excursions, dining, check-in) → Embarkation → Disembarkation
- Visual treatment: solid colored circles (green=paid, red=due, gold=open window, navy=embark, blue=disembark)
- Today marker: red vertical dashed line
- These dates are IMMOVABLE once committed — visualized as fixed pins on a rail

**FLUID ZONE (bottom, probabilistic):**
- Displayed as: dashed-border pill-shaped bubbles in a grey cloud zone
- Items are: flights, hotels, transfers, insurance, independent bookings, shore dining
- Visual treatment: transparent bubbles with dashed borders — deliberately "unanchored" looking
- Color coding: grey=not yet booked, orange-warn=action needed, red-crit=missing, green=confirmed
- These items MAY NOT follow a schedule — they deliberately do not sit on the time axis

**Why this works:**
1. Visual separation is immediate — anchors are structured/formal, fluid is loose/informal
2. Fluid items carry full status (warn/crit/done) without implying a date
3. Shared group milestones handled in a separate bottom panel
4. Hover tooltips on anchor nodes show full date on mouse-over

---

### WHAT'S IN EACH FILE

| File | Group | Key Anchors | Fluid Count |
|------|-------|-------------|-------------|
| Furlow_Nichols_Ely | 3 couples, Grandeur Scandinavia | Deposit → FPD → Excursions → Dining → Check-in → Embark/Disembark | 5-6 items each |
| Kuklinski_Morton | 3 bookings, Viking Mars Panama | FPD PAID → Embark → Disembark | 5-6 items + guest form CRIT flag |
| McLeod_June | 4-booking portfolio | Per-booking: FPD + Embark/Disembark | Full logistics detail + competitive flag |
| Loucks_Japan | Commander's 2 voyages | Silver Nova full pre-cruise chain; Grandeur full anchor set | Nova: all confirmed ✓; Panama: all open + Guest Reg CRIT |

---

### ACTION FOR GOOSE
Email all 4 files to johnloucks3@gmail.com from d2mconcierge.
Subject: "D2M Client Lifecycle Timelines — Anchor/Fluid Redesign"

// REDESIGN COMPLETE — Claude
