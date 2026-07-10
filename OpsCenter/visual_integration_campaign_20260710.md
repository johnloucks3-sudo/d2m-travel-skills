# Visual Integration Campaign — Three-Track Parallel Initiative
**Started:** 2026-07-10 15:48 MT  
**Commander Authorization:** All three tracks, parallel execution  
**Orchestrator:** Hale (hale-coo agent)  
**Planner:** Plan agent (roadmap in progress)

---

## TRACK A: Morning Brief Dashboard (URGENT)
**Delivery:** 2026-07-11 EOD (tomorrow)  
**Owner:** TBD (Designer + Frontend)  
**Status:** 🟡 Awaiting plan

| Task | Owner | Status | Blocker |
|------|-------|--------|---------|
| Dataviz: lock palette + validate | Designer | ✅ DONE | — |
| Sketch component layout (gauge, timers, kanban, heatmap) | Designer | ✅ DONE | — |
| Build HTML artifact (vanilla JS, no dependencies) | Frontend | ✅ DONE | — |
| Integrate live data (hale_state.json, mission_board.json, systemd, free) | Data | ✅ DONE | — |
| Local server + API endpoint (port 8926, /api/data) | Frontend | ✅ DONE | — |
| WF-17 gate + artifact deployment | Hale | ✅ DONE | — |

**Scope:** Pipeline gauge + FPD countdown timers + system health (memory/swap/services) + mission kanban

**Palette:** D2M dark navy + status colors (good/warning/critical)

**Dependencies:** None (can ship standalone)

---

## TRACK B: Flight Research & Route Maps (Medium Priority)
**Delivery:** Next flight research cycle (≤7 days, likely Spencer booking call)  
**Owner:** TBD (Dataviz + Data Integration)  
**Status:** 🟡 Awaiting plan

| Task | Owner | Status | Blocker |
|------|-------|--------|---------|
| Design form: which chart types per data job (route → SVG map, fares → heatmap, trends → line chart) | Dataviz | ⏳ | — |
| Validate palettes (route map, heatmap, line) per dataviz spec | Dataviz | ⏳ | palette_d2m_brand.md (DONE) |
| Build route map renderer (Kiwi/Google results → Great Circle SVG) | Frontend | ⏳ | Form approval |
| Build fare matrix heatmap (carrier × cabin × date → color intensity) | Frontend | ⏳ | Form approval |
| Build price trend line (30-day history, diverging palette for ↑↓) | Frontend | ⏳ | Form approval |
| Integrate into next flight search (call United, Spencer DEN-FCO) | Integration | ⏳ | All charts DONE |

**Scope:** Visual + analytical layer for flight research; integrate into workflow, not standalone.

**Palette:** Sequential (fare heatmap), diverging (price trends), route map uses navy + gold

**Dependencies:** Form/chart-type decisions (blocks renderer work)

---

## TRACK C: Dossier Visual Cards (Medium Priority)
**Delivery:** Ready for Furlow/Ely-Darrow/Nichols review (~10 days, before Jul 22 itinerary build)  
**Owner:** TBD (Designer + Data)  
**Status:** 🟡 Awaiting plan

| Task | Owner | Status | Blocker |
|------|-------|--------|---------|
| Design card template (profile + timeline + payment ladder) | Designer | ⏳ | — |
| Extract dossier schema (client fields, booking data, FPD structure) | Data | ⏳ | — |
| Build card renderer (per-client HTML generation from Qdrant/dossiers) | Frontend | ⏳ | Template + schema |
| Validate dataviz on payment ladder (sequential: unpaid → paid) | Dataviz | ⏳ | Template |
| Generate 3x test cards (Furlow, Ely-Darrow, Nichols) | Data Integration | ⏳ | Renderer DONE |
| Review + iterate with Commander | Hale | ⏳ | Test cards ready |

**Scope:** Visual client briefing card; used for pre-review + potentially embedded in portals later.

**Palette:** Categorical hues per client (Furlow=navy, Ely-Darrow=gold, Nichols=blue), sequential ladder

**Dependencies:** Template design (blocks renderer), schema finalization (blocks data extraction)

---

## Critical Path & Dependencies

```
START (2026-07-10)
  ├─ TRACK A: Palette lock (DONE) → sketch → build → deploy → EOD 2026-07-11 ✅
  ├─ TRACK B: Form decision → palette validate → build 3 charts → integrate → ≤2026-07-17
  └─ TRACK C: Template sketch → schema extract → build renderer → generate → ≤2026-07-20
```

**Shared critical resource:** Dataviz validation (palette + mark specs). Sequenced: A → B → C priority.

---

## Blocker Tracking

| Blocker | Severity | Mitigation | ETA Resolution |
|---------|----------|------------|-----------------|
| (None yet — awaiting Planner) | — | — | — |

---

## Success Criteria

**TRACK A (Morning Brief):**
- [ ] Dashboard renders without errors
- [ ] Real-time data updates (refresh every 30s or on state change)
- [ ] All 4 components visible + interactive (no overflow, readable on 1920×1080)
- [ ] Brand palette validated (CVD ≥ 8, contrast ≥ 4.5:1)
- [ ] Artifact deployment + optional local `/dashboard` server working
- [ ] Commander views it tomorrow morning before 06:00 MT

**TRACK B (Flight Research):**
- [ ] 3 chart types rendered per flight search
- [ ] Data flows from Kiwi/Google APIs into charts
- [ ] Palettes validated before ship
- [ ] Integrated into next Spencer call or flight research task
- [ ] No regression on existing flight research workflow

**TRACK C (Dossier Cards):**
- [ ] 3 test cards generate from real dossier data
- [ ] Card layout readable + branded (dark navy + client categorical hue)
- [ ] Payment ladder accurately reflects booking state
- [ ] Commander approves visual direction before itinerary build (Jul 22)

---

## Resource Requests (Awaiting Hale Orchestrator)

- **Designer:** frontend-design skill, dataviz methodology, Template A/C + Form B
- **Frontend:** Artifact building, Recharts/D3, HTML generation, component library
- **Data:** Qdrant queries, dossier schema extraction, real-time state binding
- **Dataviz:** Palette validation, form/chart-type decisions, accessibility pass

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Palette validation fails (CVD/contrast) | Low | Medium | Swap colors per validator; test early |
| Real-time data binding complex (live Qdrant) | Medium | Medium | Mock data first, integrate data layer last |
| Scope creep on TRACK C (feature requests) | Medium | Medium | Lock template by Jul 17 EOD |
| Chart library perf (large dataset) | Low | Medium | Test with 1K+ data points; virtualize if needed |

---

## Daily Standby (once execution starts)

- **06:00 MT:** Hale briefs status (all 3 tracks % complete, blockers)
- **Async updates:** Log blockers in this file as they emerge
- **Commander gates:** WF-17 on TRACK A (live dashboard), TRACK C (dossier cards before client use)

---

**Next action:** Await Planner + Hale Orchestrator roadmap + task assignments.

*Record end time when Plan returns:* ⏳
