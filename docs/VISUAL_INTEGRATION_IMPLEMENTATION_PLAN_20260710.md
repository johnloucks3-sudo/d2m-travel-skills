# THUNDERBIRD VISUAL INTEGRATION — Implementation Roadmap
**Three Parallel Initiatives · Phased Deployment · Jul 10–Aug 15, 2026**

---

## EXECUTIVE SUMMARY

| Initiative | Priority | Deploy | Dependencies | Owner | Effort |
|---|---|---|---|---|---|
| **A: Morning Brief Dashboard** | P0 (URGENT) | Jul 11 EOD | Hale state + brief schema | TALON + Exec | 6h |
| **B: Flight Research Maps** | P1 (HIGH) | Jul 25 | Centrav/Kiwi data + dataviz | A12 ELON + Whetstone | 16h |
| **C: Dossier Visual Cards** | P2 (MED) | Aug 5 | Portal schema + image assets | A8 Reyes + Exec | 14h |

**Total scope:** 36h development, parallel + sequential milestones, zero new dependencies.

---

## INITIATIVE A: MORNING BRIEF DASHBOARD
### Deploy: Jul 11 EOD (tomorrow)

**Objective:** Replace markdown brief (`hale_brief.md`, 276 lines) with interactive HTML dashboard displaying pipeline health, FPD countdowns, system status, mission board in real time.

### Data Sources
- **Source 1:** `hale_state.json` — financial_pulse, open_tasks, deferred_alerts, wing_health
- **Source 2:** `hale_brief.md` — current brief structure (CLIENT WIRE, WF-17 QUEUE, FINANCIAL PULSE, WING HEALTH, TP DRAFT FOR APPROVAL)
- **Source 3:** Mission board (OpsCenter/mission_board.json) — P0/P1 tasks, status updates

### Components (Vanilla JS/HTML, no framework)

| Component | Source | Data Binding | Priority |
|---|---|---|---|
| **Pipeline Gauge** | hale_state.json `financial_pulse` | $18,830.93 pipeline | P0 |
| **FPD Countdown Matrix** | hale_brief.md CLIENT WIRE (11 active clients) | Auto-refresh every 6h | P0 |
| **System Health Status** | hale_state.json `wing_health` | 5 services + credential status | P0 |
| **Mission Board Kanban** | mission_board.json | Columns: P0 (red), P1 (yellow), P2 (gray) | P1 |
| **Overnight Ops Summary** | hale_brief.md section 0 | Last 24h change log | P1 |

### Design Specs
- **Canvas:** 1920×1080 (desktop-first, no mobile)
- **Brand:** D2M dark navy (#003087), status palette (🟢#2ecc71 OK, 🟡#f39c12 WARN, 🔴#e74c3c CRIT)
- **Layout:** 4-column grid (pipeline + FPD + health + mission board) + footer (overnight ops)
- **Responsivity:** CSS Grid, all components shrink to fit <1600px (not mobile)
- **Real-time:** JSON endpoints auto-refresh every 5 min (pipeline), 15 min (mission board), 1h (overnight ops)

### Architecture
```
dashboard.html
├── styles (inline CSS, dark navy + status palette)
├── components (vanilla JS modules)
│   ├── pipeline-gauge.js (SVG circle + percent + $)
│   ├── fpd-matrix.js (table w/ countdown timers)
│   ├── health-status.js (service boxes + colors)
│   └── mission-kanban.js (Kanban columns)
└── data layer
    ├── fetch hale_state.json every 5min
    ├── fetch mission_board.json every 15min
    └── render on update (no flickering)
```

### Tasks (5 subtasks, ~6h total)

| Task | Owner | Effort | Dependencies |
|------|-------|--------|---|
| A-1: Create HTML skeleton + CSS foundation | TALON | 45 min | None |
| A-2: Implement pipeline gauge component | TALON | 60 min | A-1 |
| A-3: Implement FPD countdown matrix | TALON | 75 min | A-1, hale_brief.md structure |
| A-4: Implement health status + mission kanban | TALON | 90 min | A-1, mission_board.json schema |
| A-5: Integration test + deployment | TALON | 30 min | A-2, A-3, A-4 |

### Deployment
- **Destination:** `/home/john/Thunderbird/output/hale_dashboard.html` (serve via Claude Code server on :8080/dashboard)
- **Access:** Commander bookmarks, loads on session start
- **Refresh:** Auto-pulls JSON every 5–15 min (no manual refresh needed)
- **Fallback:** If JSON endpoint down, display stale data + red banner "Last updated: [timestamp]"

### Success Criteria
- ✅ Dashboard loads without errors
- ✅ Pipeline gauge displays current $18,830.93
- ✅ FPD countdowns update on refresh
- ✅ All 11 active clients visible in matrix
- ✅ Health status reflects wing_health.json (all services in view)
- ✅ Mission board shows P0/P1/P2 with correct counts
- ✅ Auto-refreshes every 5 min (pipeline) and 15 min (mission board)
- ✅ Dark navy + status colors applied throughout

### Risks & Mitigation
| Risk | Probability | Impact | Mitigation |
|------|---|---|---|
| JSON endpoint missing fields | Medium | High | Pre-validate schema; show "N/A" gracefully |
| Auto-refresh breaks on network error | Medium | Low | Implement retry-with-backoff (3 attempts, 5s delays) |
| Commander wants a new metric mid-deploy | High | Low | Add "TODO: metric X" in comments; defer to Phase 2 |

### Phase 2 (Optional, post-Jul 11)
- Add drill-down (click FPD countdown → client dossier)
- Add historical trends (pipeline over 30d)
- Add "pause auto-refresh" toggle

---

## INITIATIVE B: FLIGHT RESEARCH & ROUTE MAPS
### Deploy: Jul 25 (15 days for development + review)

**Objective:** Integrate visual layer (Great Circle routes, fare heatmaps, price tracking) into fare-watch research workflow. Enable side-by-side route comparison and 30-day fare trends for Spencer Grand Tour, Loucks Silver Nova, and Kuklinski Viking Mars.

### Data Sources
- **Source 1:** Centrav/Kiwi flight search results (JSON, 6 active routes)
- **Source 2:** Fare watch database (historical 30-day pricing, 38 watches active)
- **Source 3:** GeoJSON airport coordinates (IATA list, no external API needed)

### Components

| Component | Library | Data | Purpose |
|---|---|---|---|
| **Great Circle Route Map** | Vanilla SVG (no D3/Leaflet) | Airport pairs + IATA coords | Show direct routing DEN→FCO vs alternatives |
| **Fare Comparison Heatmap** | Canvas or SVG grid | 6 routes × 30 days | Identify seasonal dips, price patterns |
| **Price Tracking Line Chart** | Vanilla SVG + canvas | Centrav feed, 30d history | Trend line for each route |
| **Route Details Sidebar** | HTML + CSS | Fares, ETA, cabin availability | Read-write summary per route |

### Architecture
```
flight-research-dashboard.html
├── Map Canvas (SVG)
│   ├── Great Circle route lines (DEN→FCO, etc.)
│   └── Airport markers + labels
├── Heatmap Grid (Canvas or SVG)
│   └── 6 columns (routes) × 30 rows (days) = cells colored by price
├── Price Trend Chart (SVG or Canvas)
│   └── 6 line series, one per route
└── Details Sidebar (HTML)
    └── Active route summary (expandable)
```

### Data Prep (ELON A12)
- Extract 6 routes from `docs/FLIGHT_ROUTING_RESEARCH.md` and fare-watch logs
- Build JSON: `{ routes: [ { id, from, to, iata_from, iata_to, prices: [...]  }, ... ] }`
- Store at `/home/john/Thunderbird/data/flight_routes_intelligence.json`
- Pre-compute 30-day rolling avg for heatmap coloring

### Tasks (6 subtasks, ~16h total)

| Task | Owner | Effort | Dependencies |
|------|-------|--------|---|
| B-1: Data extraction + JSON schema build | ELON (A12) | 3h | Centrav logs, Kiwi API |
| B-2: SVG Great Circle route map | TALON | 3h | B-1 (airport coords) |
| B-3: Fare heatmap (Canvas grid) | TALON | 3h | B-1 (pricing data) |
| B-4: Price trend line chart (SVG) | TALON | 2h | B-1 |
| B-5: Interactive route details sidebar | TALON | 3h | B-2, B-3, B-4 |
| B-6: Integration + dataviz review (Exec) | Exec + Whetstone | 2h | B-2–B-5 |

### Dataviz Specs
- **Color palette:** Sequential gradient for heatmap (low: #c8e6c9 green, high: #c62828 red)
- **Interaction:** Click route → highlight line on chart + zoom heatmap column
- **Accessibility:** All data points labeled; hover shows exact price + date
- **Responsive:** Grid shrinks to 1200px; stacks on <768px (preview mode)

### Deployment
- **Destination:** `/home/john/Thunderbird/output/flight_research_dashboard.html`
- **Integration:** Link from Morning Brief Dashboard (click "Flight Research")
- **Data refresh:** Hourly Centrav/Kiwi poll updates `flight_routes_intelligence.json`; dashboard reads every 30 min

### Success Criteria
- ✅ Great Circle routes display correctly (DEN→FCO, DEN→VCE, DEN→MUC paths visible)
- ✅ Heatmap shows 30-day pricing for all 6 routes (no gaps)
- ✅ Price trend lines smooth; no spikes or data errors
- ✅ Click route → sidebar updates instantly
- ✅ Dataviz color palette applied + accessible (alt text)
- ✅ Loads in <2s; auto-refreshes every 30 min
- ✅ Exec sign-off on brand + voice

### Risks & Mitigation
| Risk | Probability | Impact | Mitigation |
|------|---|---|---|
| Centrav API rate limits on hourly poll | Medium | Medium | Implement exponential backoff; cache locally for 24h |
| Missing historical data for 30d trend | High | High | Use partial data (available days); note gaps in tooltip |
| SVG routing calculation complex | Medium | Medium | Pre-compute routes offline; store as GeoJSON |
| Screen clutter on 1200px breakpoint | Medium | Low | Hide route details by default on resize |

### Phase 2 (Optional, post-Jul 25)
- Add competitor pricing layer (if scrapers available)
- Add "book now" CTA for lowest-price points
- Add dynamic cabin class toggling (Economy→Business)

---

## INITIATIVE C: DOSSIER VISUAL CARDS
### Deploy: Aug 5 (26 days for creative + polish)

**Objective:** Convert client dossier markdown into visual profile cards (name, ship, dates, cabin, itinerary summary) + FPD payment roadmap (ladder chart showing deposit due → FPD → final). Primary use: Furlow/Ely-Darrow/Nichols pre-itinerary build review (MISSION-802).

### Data Sources
- **Source 1:** Client portals config (`config/client_portals.json`) — 5 active portals
- **Source 2:** Dossiers (`dossiers/*.md`) — 16 client dossiers
- **Source 3:** TESS bookings — booking refs, FPD dates, payment status
- **Source 4:** Drive images — ship photos, cabin photos (per-couple folders)

### Components

| Component | Type | Data | Purpose |
|---|---|---|---|
| **Client Profile Card** | HTML + CSS | Dossier MD | Name + ship + dates + cabin + visual summary |
| **FPD Payment Ladder** | SVG Chart | TESS booking data | Timeline: deposit → FPD → final (30-day view) |
| **Itinerary Summary** | HTML micro-layout | Dossier ports + dates | 7-day port roster (Stockholm→Oslo→Copenhagen etc.) |
| **Ship Photo Gallery** | Lightbox | Drive images | Thumbnail → full-screen (optional lightbox lib banned; use HTML5 <details>) |

### Architecture
```
dossier-cards.html
├── Client Card Deck (3-column grid for 3 couples)
│   ├── Card 1: Furlow
│   │   ├── Profile header (name, ship, dates)
│   │   ├── FPD Payment Ladder (SVG)
│   │   ├── Itinerary micro-timeline
│   │   └── Cabin photo + gallery toggle
│   ├── Card 2: Ely-Darrow
│   └── Card 3: Nichols
└── Print styles (A4, 3 cards per page)
```

### Tasks (7 subtasks, ~14h total)

| Task | Owner | Effort | Dependencies |
|------|-------|--------|---|
| C-1: Dossier data extraction (Furlow/Ely/Nichols) | Reyes (A8) | 2h | Dossier files |
| C-2: TESS payment data pull (FPD dates, balances) | Harlan (A9) | 1h | TESS API or CSV export |
| C-3: Collect + resize ship/cabin photos | Reyes (A8) | 2h | Drive folders |
| C-4: Design profile card layout + CSS | Exec (Naia) | 2h | C-1 (data structure) |
| C-5: Implement profile card HTML + photo gallery | TALON | 2h | C-4 |
| C-6: Implement FPD payment ladder (SVG) | TALON | 2h | C-2 (payment data) |
| C-7: Integration + print review | Exec | 1h | C-5, C-6 |

### Design Specs
- **Card dimensions:** 4×5" (when printed 3-up on A4)
- **Brand:** D2M dark navy header, cream background (#f7f3ea), status colors (green=FPD paid, yellow=due soon, red=overdue)
- **Typography:** Georgia serif (USAFA standard), 11pt body, 18pt header
- **Images:** 800×600px ship photo (top), 200×200px cabin photo (bottom-left)
- **Print-friendly:** No shadows, web fonts embedded, high contrast

### Dataviz: FPD Payment Ladder
```
Example: Furlow Grandeur (Deposit $5k, FPD $12k on Jul 22, Final $24k on Aug 15)

Timeline (30-day view):
Jul 7  ████ Deposit paid (✓)
Jul 22 ░░░░ FPD due (TODAY-12d, yellow)
Aug 15 ░░░░ Final payment (31d out, gray)

Legend: 
  ████ = Milestone reached
  ░░░░ = Upcoming (color-coded by urgency)
```

### Deployment
- **Destination:** `/home/john/Thunderbird/output/dossier_cards_furlow_elydarrow_nichols.html`
- **Print:** Commander prints 3-up on A4 stock (use browser Print Preview)
- **Access:** Link from hale brief ("Review 3-couple dossier summary")
- **Refresh:** Rebuild weekly from dossiers + TESS (manual trigger, no auto-refresh for payment data)

### Success Criteria
- ✅ 3 cards render correctly (Furlow, Ely-Darrow, Nichols)
- ✅ Profile cards show correct ship, dates, cabin numbers
- ✅ FPD payment ladder shows deposit (paid ✓), FPD (due Jul 22), final (due Aug 15)
- ✅ Ship + cabin photos display at correct aspect ratios
- ✅ Print layout: 3 cards fit on A4 landscape, no overflow
- ✅ Brand palette applied (dark navy + cream + status colors)
- ✅ Exec sign-off on design + voice

### Risks & Mitigation
| Risk | Probability | Impact | Mitigation |
|------|---|---|---|
| Dossier data incomplete (missing FPD dates) | High | High | Pre-audit dossiers for required fields (Harlan validates) |
| Photos missing from Drive | Medium | Medium | Use placeholder (ship name + "Photo TBD") |
| Print layout breaks on 3-up | Medium | Low | Test print in Chrome DevTools before deploy |
| TESS data stale or conflicting | Medium | Medium | Cross-check vs Regent portal; log discrepancies |

### Phase 2 (Optional, post-Aug 5)
- Add dossier comparison view (side-by-side 2+ clients)
- Add excursion highlights (top 3 excursions per client)
- Add dining venue recommendations (based on dossier preferences)

---

## PARALLEL EXECUTION TIMELINE

```
WEEK 1 (Jul 7–11): Initiative A (Dashboard)
│
├─ Mon Jul  7: ELON extracts flight + FPD data (B-1 prep)
├─ Tue Jul  8: TALON builds Dashboard skeleton + pipeline gauge
├─ Wed Jul  9: TALON completes FPD matrix + health status
├─ Thu Jul 10: TALON integrates mission board kanban
├─ Fri Jul 11: TALON deploys + tests; dashboard LIVE by EOD
│
└─ PARALLEL: Reyes + Harlan audit dossier data (C-1, C-2)
             Exec designs dossier card layout (C-4)

WEEK 2–3 (Jul 14–25): Initiative B (Flight Maps) — **CRITICAL PATH**
│
├─ Mon Jul 14: ELON finalizes flight_routes_intelligence.json (B-1 done)
├─ Tue-Wed Jul 16–17: TALON builds route map + heatmap (B-2, B-3)
├─ Thu-Fri Jul 18–19: TALON builds price trend chart (B-4)
├─ Mon-Tue Jul 21–22: TALON integrates sidebar + interaction (B-5)
├─ Wed Jul 23: Exec dataviz review + brand sign-off (B-6)
├─ Thu Jul 24: Testing + hotfixes
├─ Fri Jul 25: Flight maps LIVE
│
└─ PARALLEL: TALON drafts dossier card HTML (C-5 draft)
             Reyes collects + resizes photos (C-3)

WEEK 4–5 (Jul 28–Aug 8): Initiative C (Dossier Cards) + Polish
│
├─ Mon Jul 28: TALON finalizes dossier card HTML (C-5)
├─ Tue-Wed Jul 29–30: TALON implements FPD ladder (C-6)
├─ Thu Jul 31: Exec design review (C-7)
├─ Fri Aug  1: Testing + print validation
├─ Mon Aug  4: Hotfixes + copy review (Exec voice)
├─ Tue Aug  5: Dossier cards LIVE
│
└─ PARALLEL: Dashboard Phase 2 planning (drill-down, trends)
             Flight maps Phase 2 planning (competitor prices)

WEEK 6 (Aug 8–15): Stabilization + Cross-Initiative Polish
│
├─ Cross-link all three dashboards
├─ Add "Morning Brief" → "Flight Research" → "Dossier Cards" navigation
├─ Performance audit (load times, refresh rates)
├─ Accessibility pass (color contrast, ARIA labels, alt text)
└─ Handoff to Hale orchestrator for ongoing maintenance
```

---

## RESOURCE ALLOCATION

| Role | Initiative A | Initiative B | Initiative C | Total |
|---|---|---|---|---|
| **TALON (CONDOR) — Claire, client voice** | 5.5h (dev + review) | 8h (dev + design) | 3h (dev + review) | **16.5h** |
| **ELON (A12) — Innovation & Automation** | 0.5h (data prep) | 3h (data architecture) | 0.5h (data review) | **4h** |
| **Whetstone (A14) — Tech Currency** | 0.5h (review) | 2h (dataviz methodology) | 0.5h (tech review) | **3h** |
| **Reyes (A8) — Experience Layer** | — | 0.5h (data review) | 4h (dossier extraction + photos) | **4.5h** |
| **Harlan (A9) — Finance** | 0.5h (data validation) | 0.5h (payment data prep) | 1h (TESS data audit) | **2h** |
| **Exec (Naia) — Brand & Voice** | 0.5h (brand review) | 2h (dataviz sign-off) | 3h (design + voice) | **5.5h** |
| **Hale (COS) — Orchestration** | 0.5h (testing) | 1h (integration) | 1h (integration) | **2.5h** |
| **TOTAL** | **6h** | **16h** | **14h** | **36h** |

**Cost:** Sonnet (dataviz, design) ~2K tokens; Haiku (data fetch, integration) ~500 tokens. Zero new API costs.

---

## DEPENDENCIES & CRITICAL PATH

### Hard Dependencies
1. **Morning Brief Dashboard (A)** → must complete by Jul 11 (no blockers on B/C)
2. **Flight Maps (B)** → ELON data extraction (B-1) is critical; Centrav/Kiwi API availability required
3. **Dossier Cards (C)** → dossier audit (C-1) + TESS data pull (C-2) must complete by Jul 28

### Soft Dependencies (can work around)
- If photos missing → use placeholders ("Photo TBD")
- If FPD dates incomplete → show "TBD" in ladder chart
- If flight data incomplete → display partial routes + note gaps

---

## SUCCESS METRICS & HANDOFF

### Phase 1 Completion (by Aug 15)
- All three initiatives deployed to `/home/john/Thunderbird/output/`
- No broken links between dashboards
- Load time <2s per page
- Auto-refresh working (A: 5/15 min, B: 30 min, C: manual)
- Brand colors + D2M styling applied throughout
- Exec sign-off on all voice + copy

### Ongoing Maintenance (Hale owes)
- Daily: Monitor dashboard JSON endpoints (mission board, hale_state)
- Weekly: Refresh dossier cards from new dossiers
- Bi-weekly: Update flight maps with latest Centrav/Kiwi data
- Monthly: Dataviz audit (Whetstone, A14) for currency

### Phase 2 Planning (post-Aug 15)
- Drill-down from Dashboard → client detail views
- Competitor pricing layer (if data available)
- Mobile-responsive redesign (currently desktop-only)
- Integration with client portals (live FPD countdown in portal header)

---

## ARCHITECTURE PRINCIPLES

**Zero New Dependencies**
- Vanilla JS (no React, Vue, D3, Recharts)
- Inline CSS (no Tailwind, Bootstrap)
- SVG/Canvas for charts (no chart libraries)
- Local data (JSON files, Qdrant embedded)

**Dataviz Consistency**
- All three dashboards use same color palette (dark navy + status colors)
- Same typography (Georgia serif, USAFA standard)
- Same interaction model (hover = tooltip, click = drill-down)
- Same print-friendly approach (CSS-only, no shadow/blur)

**Data-Driven Updates**
- No hardcoded values; all data sourced from JSON/Qdrant
- Refresh timers staggered to avoid simultaneous calls
- Fallback to stale data if endpoint unavailable (with "last updated" banner)

**Hale Orchestrator Compatibility**
- Each dashboard is self-contained HTML file (no build step)
- Data fetching via simple fetch() calls (no SDK)
- Deployment via file copy to `/output/` directory
- Refresh triggers wired to Hale's OODA loop + systemd timers

---

## NEXT ACTIONS (Immediate)

1. **Hale: Schedule kickoff** with TALON (A) + ELON (B) + Exec (C) for Jul 8 AM
2. **ELON: Begin data extraction** for flight maps (B-1) — coordinate with Centrav/Kiwi APIs
3. **Reyes: Start dossier audit** (C-1) — validate Furlow/Ely-Darrow/Nichols dossier completeness
4. **TALON: Prepare Dashboard skeleton** (A-1) — HTML frame, CSS foundation, JSON endpoints
5. **Exec: Lock dossier card design** (C-4) — ship/cabin photos finalized by Jul 14

**First Milestone:** Jul 11, 10 AM MT — Morning Brief Dashboard LIVE

---

*Plan Owner: Hale (COS) · Last Updated: 2026-07-10 · Next Review: 2026-07-15*
