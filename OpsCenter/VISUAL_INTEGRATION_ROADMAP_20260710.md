# Visual Integration Roadmap — Three-Track Campaign
*Generated 2026-07-10 · Planner: Plan agent (synchronous, read-only) · Compiled by Hale*

## Pre-flight finding — four dashboard systems already exist; only one is the right extension point

| System | Output | Domain | Health | Action |
|---|---|---|---|---|
| `OpsCenter/dashboard_generator.py` + `d2m-dashboard-refresh.service/.timer` | `output/d2m-dashboard/index.html` | Blackboard client YAML → booking/validation tracker | Healthy, clean logs since 2026-06-04 | **Do not touch — unrelated domain** |
| `core/ops/hale_dashboard_gen.py` + `hale-dashboard-refresh.timer` | `output/hale_dashboard.html` | systemd/mission-board health | Running but has template bugs, not brand-styled, internal-only | Out of scope |
| `core/visual_synthesis/{visual_generators.py,data_generators.py}` + `hale-visual-synthesis.timer` | `output/visuals/dashboard.html` | Stub/placeholder data only (`get_phase1_test_data()`) | Runs daily on fake data; has reusable Plotly chart functions | **Reuse chart functions, retire the stub pipeline** |
| `d2m_ops_dashboard.html` (repo root + output/) | static file | "Commission Reconciliation," untouched since May 4 | True deadwood | Flag for cleanup pass, no action now |
| `scripts/morning_brief_engine.py` + `thunderbird-morning-brief.service/.timer` | `hale_brief.md` (+ email) | **Owns every section named in the task**: Client Wire, WF-17 Gate, Financial Pulse, Wing Health, Staff Concerns, TP Draft | Builds in-memory HTML per section already, never persisted as standalone dashboard | **Correct extension point for Track A** |

`ci-fix-d2m-dashboard.service` logs (2026-07-03→07-09) are all 0 bytes — Lane-1 `OnFailure=` firings on `d2m-dashboard.service` (FastAPI, :8901), NOT on `d2m-dashboard-refresh.service`. The pipeline we're extending has an independently clean log the whole time. Cannot verify what was being fixed — treated as open risk, mitigated with a generation-success assertion (below), not assumed resolved.

**Fix-vs-rebuild verdict, Track A: FIX/EXTEND `scripts/morning_brief_engine.py`.** Not `dashboard_generator.py` — that's a different system despite the shared name.

---

## TRACK A — Morning Brief Dashboard (ship 2026-07-11 EOD)

**Approach:** Extend `morning_brief_engine.py` to write a second artifact — branded standalone HTML — from the same in-memory structured data already assembled for the email. Reuse (rewire, don't rewrite) the Plotly functions in `visual_generators.py`, currently sitting on stub data.

**Files:**
- Modify: `scripts/morning_brief_engine.py` — after `BRIEF_OUT.write_text(md)`, call new `render_dashboard_html(data)` → `output/hale-brief-dashboard/index.html`
- New: `core/hale/brief_dashboard_render.py` — client wire table, WF-17 stat tile, financial pulse tiles, wing health grid, staff concerns table, TP draft card. Extract navy tokens from `storage/templates/d2m_canonical_darknavy.html` directly — do not wrap in the email's Gmail-compat table skeleton.
- Modify: `core/visual_synthesis/visual_generators.py` — swap stub data for live inputs; restyle per dataviz skill palette.
- New (safeguard): schema/section-count assertion in `brief_dashboard_render.py` so a future silent failure surfaces in `logs/morning_brief_engine.log`, not another opaque 0-byte ci-fix cycle.
- Deprecate-flag (don't kill pre-deadline): `data_generators.py::generate_html_dashboard()` + `hale-visual-synthesis.timer`.
- **Do not touch:** `dashboard_generator.py`, `d2m-dashboard-refresh.*` (different, healthy system).

**Dependencies:** `thunderbird_tp_scheduler.py`, `OpsCenter/staff_concerns.json`, `OpsCenter/tp_draft_queue.json`, `hale_state.json`, `storage/lifecycle_draft_queue.jsonl` — all already read by the engine. Skills: **dataviz** (stat tiles, wing-health grid), **brand-guidelines** (TP draft card voice/typography check).

**Cadence:** rides existing 06:00 MT timer, no new timer for the main run. Known v1 gap: `hale_scan_wirer.py` appends intraday OVERNIGHT OPS entries directly to `hale_brief.md` outside the engine's run — dashboard can lag those. Fast-follow, not EOD-blocking.

**First deliverable:** `output/hale-brief-dashboard/index.html`, Client Wire + Financial Pulse sections only, via manual `--once` run, verified against live `hale_brief.md` before adding remaining sections.

**WF-17 note:** dashboard itself is Commander-internal, not gated. The TP Draft card it renders (Section 6) must render as read-only preview only — never a send action.

---

## TRACK B — Flight Research & Route Maps (integrate ≤7 days)

**Approach:** `output/airfare_dashboard.html` already exists (Chart.js) and already regenerates daily via `scripts/fare_watch_artifacts_daily_refresh.py` (an `ExecStartPre` on the morning-brief service) — extend that script, don't build a new pipeline.

**Chart library call:** inline SVG (server-templated, no build step) for route maps + fare-matrix heatmaps, + existing Chart.js for time series. **Recharts rejected** — no React/JS build step exists in this static-HTML pipeline; adding one is unjustified scope. `core/travel/map_generator.py` (Google Static Maps, paid/quota'd) rejected for route maps — use simple SVG airport-to-airport arcs instead, no API-key dependency.

**Files:**
- New: `core/travel/route_map_svg.py` — SVG route maps from `fare_watch_list` route strings via airport-code lat/lon lookup + arc projection
- New: `core/travel/fare_matrix_heatmap.py` — SVG/HTML heatmap (route × date/cabin) from real `fare_watches.json`, dataviz skill sequential-hue method
- Modify: `scripts/fare_watch_artifacts_daily_refresh.py` — add both artifact types to existing refresh loop
- Modify: `airfare_dashboard.html` generator — restyle to true `#07076b` brand navy (currently close generic `#1a1a2e`/`#16213e`)

**Dependencies:** `fare_watch_add`/`fare_watch_list`/`fare_watch_check` MCP tools (already live), `OpsCenter/fare_watches/` cache, Centrav/Kiwi/Google Flights (already integrated, no new work). Skill: **dataviz**.

**First deliverable:** `output/route_maps/loucks_silvernova_2027.svg` — standalone, before wiring into daily refresh.

---

## TRACK C — Dossier Visual Cards (ready for review ≤10 days, before Jul 22 build)

**Approach:** Confirmed consistent YAML front matter across all three dossiers (`client`, `full_name`, `cruise_line`, `ship`, `voyage`, `booking`, `departure`, `fpd`, `fpd_amount`, `payment_status`) + `KEY DATES`/`FLIGHTS`/`HOTEL & TRANSFERS` tables. Sufficient real structured data — nothing invented.

**Files:**
- New: `core/hale/dossier_card_render.py` — parses front matter + tables into payment-roadmap + itinerary-summary card per couple
- New output: `output/dossier-cards/{furlow_3071222,ely_darrow_3096289,nichols_3078056}.html` (or one combined review page — **open decision for Commander/team-lead, not assumed**)
- Reuses Track A's brand-token module — palette defined once, not three times

**Dependencies:** the three dossier files (confirmed readable now). Skills: **dataviz** (payment-roadmap timeline), **brand-guidelines** (voice/typography), **frontend-design** (optional card-layout polish after content is correct).

**WF-17 — explicit and binding:** these are client-facing visual outputs. Generated cards land in `output/dossier-cards/` and STOP. Any send to Furlow/Ely-Darrow/Nichols requires the full WF-17 draft-approval flow (`client-draft` skill gate), separate from and after this generation step — true even once cards are "ready for review."

**First deliverable:** `output/dossier-cards/furlow_3071222.html`, single couple, payment-roadmap section only, checked against source dossier before scaling to the other two couples + itinerary summary.

---

## Shared component layer — recommended: yes

- New: `core/hale/d2m_brand_tokens.py` — navy/Georgia/shimmer tokens from the canonical template + dataviz-skill palette swapped to brand hues (validator run once)
- New: `core/hale/stat_tile.py` — one reusable stat-tile/status-badge generator (A's financial tiles, B's fare-watch counts, C's payment-status badges all need this primitive)

Track A builds both files first (needed for its own deadline). B and C import, never fork their own palette.

## Dependency graph

```
Track A (blocking, due Jul 11 EOD)
  └─ core/hale/d2m_brand_tokens.py  ─┐
  └─ core/hale/stat_tile.py         ─┤  shared layer — extract as first commit, not gated behind full Track A completion
  └─ morning_brief_engine.py extend ─┘
         │
         ├──> Track B (parallel, ≤7 days — independent data, fare_watches.json exists now)
         └──> Track C (parallel, ≤10 days — independent data, dossier .md files exist now)
                 └─ WF-17 hold on any client send (not blocking on card generation)
```

B and C have no dependency on each other. Neither depends on Track A's full section coverage — only on the small shared token/tile module, extracted early.

## Critical files
- `/home/john/Thunderbird/scripts/morning_brief_engine.py`
- `/home/john/Thunderbird/core/visual_synthesis/visual_generators.py`
- `/home/john/Thunderbird/storage/templates/d2m_canonical_darknavy.html`
- `/home/john/Thunderbird/scripts/fare_watch_artifacts_daily_refresh.py`
- `/home/john/Thunderbird/dossiers/Furlow_Regent_3071222.md`
