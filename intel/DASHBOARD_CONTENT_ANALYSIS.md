# DASHBOARD CONTENT ANALYSIS
## Staff Paper from Vic Harlan, A9 — Dreams2Memories Travel, LLC
### Date: 2026-03-20

---

**ISSUE:** Commander wants to evaluate dashboard content before committing dev hours. The question is whether a visual dashboard delivers information he cannot already get from Telegram C2, the morning briefing, or a quick `/hale` command.

**THE 30-SECOND TEST:** What does Commander need to see at a glance that he currently has to ask for?

---

## PANEL 1: REVENUE PIPELINE

### What question does it answer?
"How much money is in play, where is it in the pipeline, and what do I need to chase this week?"

### Content
| Metric | Source | Update Frequency |
|--------|--------|-----------------|
| Active bookings by status (confirmed / pending / inquiry) | Booking Master Google Sheet + TESS | On booking change; daily reconcile |
| Total pipeline value (sum of all active booking revenue) | Booking Master + dossiers | On booking change |
| Commission earned (paid bookings) vs pending (unpaid) | Booking Master; TESS `tess_get_commissions` | Monthly (commission pay cycles) |
| Next 5 FPDs with days remaining | Dossiers (FPD fields) + `dossier_scanner` alerts | Daily scan at 6:45 AM |
| Bookings by month (timeline/bar) | Booking Master date fields | On booking change |
| YTD revenue vs prior year | Booking Master (manual — no prior-year data exists yet) | Monthly |

### Red flags requiring action
- FPD within 7 days, payment not confirmed
- Commission not received 45+ days after sailing
- Pipeline value dropping (cancellation or no new bookings for 30+ days)

### Can Telegram C2 do this today?
Partially. `/hale` can run a dossier scan and return FPD alerts. But it returns text, not a ranked/sorted view. Commander has to read and mentally sort. No running totals, no trend lines.

### Current data reality check
- **Booking Master Google Sheet:** Exists, but I cannot confirm how many rows are populated or whether commission columns are filled. The dossier `CLAUDE.md` says it's mandatory, but "mandatory" and "populated" are different things.
- **Dossiers:** 21 active dossier files. Good structural data (FPDs, booking totals, balances). Example: Furlow shows $19,236 total, $15,486 balance due Apr 1. This data IS there.
- **TESS:** MCP tools exist (`tess_get_commissions`, `tess_search_bookings`, `tess_get_booking`). Live data source. But TESS is the OA portal — not all bookings route through it.
- **Commission tracking:** No dedicated commission ledger exists today. Dossiers have per-booking amounts but there is no aggregation layer.

### VERDICT: BUILD (with caveats)
This is the only panel that answers a question Commander literally cannot answer today without manually scanning 21 dossier files and a spreadsheet. The FPD countdown alone justifies it. But the commission tracking requires building a data layer that does not exist — a simple JSON or SQLite ledger that aggregates what is scattered across dossiers.

**Estimated effort to feed this panel:** Medium. FPD/booking status data exists in dossiers. Commission aggregation needs a new ~100-line module.

---

## PANEL 2: CLIENT HEALTH

### What question does it answer?
"Who am I neglecting, who needs attention before their trip, and where are my dossier gaps?"

### Content
| Metric | Source | Update Frequency |
|--------|--------|-----------------|
| Last contact date per client (email recency) | Gmail search (`gmail_search_messages`) | Real-time query |
| Days until next trip per client | Dossier embarkation dates | Static (changes only on rebooking) |
| Dossier completeness score (%) | `thunderbird_dossier_scanner.py` gap detection | Daily at 6:45 AM |
| Open action items per client | Dossier "OPEN" flags + `dossier_scanner` alerts | Daily |
| Client tier (Friend / Standard / Premium) | Dossiers (manual field) | On client onboarding |

### Red flags requiring action
- No contact in 30+ days with a trip inside 90 days
- Dossier completeness below 70% with trip inside 60 days
- 3+ open action items on any single client

### Can Telegram C2 do this today?
YES — mostly. The dossier scanner already runs daily and injects alerts into the morning briefing. `/hale scan dossiers` returns exactly this data as text. The gap: no "last contact date" tracking exists. Gmail search can answer it per-client, but nothing aggregates it.

### Current data reality check
- **Dossier scanner:** Fully operational (`thunderbird_dossier_scanner.py`). Checks FPDs, unassigned seats, missing passport verification, insurance gaps. Already feeds morning briefing.
- **Gmail contact recency:** No aggregation. Would require a sweep of `gmail_search_messages` per client on each refresh. 21 clients x 1 query = 21 API calls per refresh. Acceptable, but not instant.
- **Dossier completeness scoring:** The scanner checks for specific gaps but does not produce a percentage score. That would need ~30 lines of code added to the scanner.

### VERDICT: SKIP (marginal value over morning briefing)
The dossier scanner already delivers 80% of this in the morning briefing. Adding "last contact date" is useful but does not justify a dashboard panel — it justifies adding one more check to the existing scanner. The only visual advantage would be a sorted list by "most neglected client," which is nice but not $X-of-dev-time nice for a 21-client book.

**If Commander disagrees:** Add contact recency to the dossier scanner output (2 hours work), skip the dashboard panel.

---

## PANEL 3: SYSTEM HEALTH

### What question does it answer?
"Is my infrastructure working, or is something broken that I don't know about?"

### Content
| Metric | Source | Update Frequency |
|--------|--------|-----------------|
| MCP server status (UP/DOWN, port 8765) | `thunderbird_health.py` — `check_services()` | Real-time probe |
| REST API status (UP/DOWN, port 8766) | `thunderbird_health.py` | Real-time probe |
| n8n status (UP/DOWN, port 5678) | `thunderbird_health.py` | Real-time probe |
| Portal status (UP/DOWN, port 8780) | `thunderbird_health.py` | Real-time probe |
| Telegram C2 status (process check) | `thunderbird_health.py` | Real-time probe |
| n8n workflow success/failure (last 24h) | n8n API (if exposed) or log parsing | Hourly |
| Last morning briefing delivered | `briefing_sent.json` | Daily |
| Data store freshness (learning DB, voice ledger, fare watches) | `thunderbird_health.py` — `check_data_freshness()` | Real-time query |

### Red flags requiring action
- Any service DOWN for more than 5 minutes
- Morning briefing not delivered by 7:00 AM
- n8n workflow failure rate above 20%

### Can Telegram C2 do this today?
YES. The `system_health_check` MCP tool exists. Commander can run `/hale health` and get a full status dump. The health module (`thunderbird_health.py`) already checks services, data freshness, and resource usage. It outputs a formatted summary.

### Current data reality check
- **`thunderbird_health.py`:** Fully built. Checks 6 services, 6 data freshness indicators, disk/log sizes. Returns structured JSON or human-readable summary.
- **`system_health_check` MCP tool:** Exists and callable.
- **n8n workflow monitoring:** 16 workflows deployed. n8n has its own dashboard at port 5678. Duplicating this is waste.

### VERDICT: SKIP (this is solved)
`thunderbird_health.py` and the MCP tool already do this. A dashboard panel would be a prettier version of information Commander can get in 3 seconds via Telegram. The health module even has age labels ("2h ago", "stale") built in. n8n already has its own UI.

Building a visual panel for system health when the text version exists and works is what I call charity — giving away dev hours for no revenue impact.

---

## PANEL 4: INTELLIGENCE FEED

### What question does it answer?
"What changed in the travel world in the last 24 hours that affects my clients or my business?"

### Content
| Metric | Source | Update Frequency |
|--------|--------|-----------------|
| Fare watch alerts (price changes on monitored routes) | `fare_watches.json` + `fare_watch_check` MCP tool | Per-watch schedule (currently: 0 active watches) |
| Travel advisory changes (State Dept, FCDO) | `get_travel_advisories` MCP tool, `run_world_intelligence_sweep` | Daily morning briefing |
| Airline route/schedule changes | `scan_airline_route_changes` MCP tool | Weekly or on-demand |
| Competitive intelligence highlights | `run_competitive_surveillance` MCP tool | Weekly (wf10 n8n) |
| Port/destination weather or disruption alerts | `get_port_weather_forecast`, NOAA tools | On-demand |

### Red flags requiring action
- Travel advisory upgrade for a destination with an active booking
- Fare drop of 15%+ on a monitored route
- Airline cancels a route used by a booked client

### Can Telegram C2 do this today?
YES — and it should. The morning briefing is designed to deliver exactly this. The n8n workflows (wf3 flight price alert, wf8 fare watch, wf10 competitive intel) already push alerts to Telegram. A dashboard panel would be a read-only mirror of what Telegram already delivers proactively.

### Current data reality check
- **Fare watches:** `fare_watches.json` is empty (`{}`). Zero active watches. This panel has no data to display today.
- **Travel advisories:** Tool exists, but no evidence of regular automated pulls landing in a queryable store.
- **Competitive intel:** `run_competitive_surveillance` exists. Output goes to morning briefing text, not a database.
- **Intel infrastructure:** The intel directory has 19 files, mostly one-off research reports. No rolling feed database.

### VERDICT: SKIP (no data + Telegram already does push)
This panel has a fundamental problem: most of its data sources either (a) don't have data yet (fare watches empty), or (b) already push to Telegram. A dashboard is pull — Commander goes and looks. Telegram is push — it comes to Commander. For intelligence, push wins every time.

Fix the upstream problem first: populate fare watches, get advisory monitoring on a cron. Once that data flows, it should flow to Telegram, not a dashboard.

---

## PANEL 5: LEARNING METRICS

### What question does it answer?
"Is the AI getting better at writing like me, or am I still editing every draft?"

### Content
| Metric | Source | Update Frequency |
|--------|--------|-----------------|
| Principles captured this week | `learning_rules.db` — `principles` table | On each Commander edit captured |
| Total corrections logged | `learning_rules.db` — `corrections` table | On each diff capture |
| Draft accuracy trend (% approved without Commander edit) | Would need: approval/rejection logging in draft flow | Per draft |
| Voice consistency score | `voice_ledger.json` — rule count + applied_count | Per Dani output |

### Red flags requiring action
- Zero principles captured in 14+ days (learning system stalled)
- Draft approval rate below 50% (AI is not improving)
- Voice rule applied_count not incrementing (rules exist but aren't being used)

### Can Telegram C2 do this today?
Partially. `learning_list_rules` and `voice_ledger_list` MCP tools return current state. But no trend data exists — there is no time-series of "approval rate over time."

### Current data reality check
- **Learning rules DB:** Tables exist. Both `corrections` and `principles` have **0 rows**. The system is built but has never captured a real diff. This is the skeleton of a learning system, not a functioning one.
- **Voice ledger:** Active. Has rules with `applied_count` fields (some at 4). Created Mar 20. 6 global rules, plus tier and client rules. This is the one data source in this panel that actually has data.
- **Draft approval tracking:** Does not exist. No logging of "Commander approved draft as-is" vs "Commander edited draft." This would need to be built into the draft approval workflow (WF17).

### VERDICT: SKIP (premature — no data)
You cannot build a dashboard for a system that has zero corrections and zero principles logged. The learning compiler is a shell. The voice ledger has a handful of rules from a single analysis session. There is nothing to trend.

When the learning system starts capturing real diffs (which requires Commander to actually use the draft approval flow regularly), revisit this. Until then, a dashboard panel showing zeros is not information — it is embarrassment.

---

## FINAL VERDICT

### The Honest Count

| Panel | Build? | Why |
|-------|--------|-----|
| 1 — Revenue Pipeline | **YES** | Only way to see aggregated financial position. Scattered across 21 dossiers today. No single source of truth for "how much money is in play." |
| 2 — Client Health | **SKIP** | Morning briefing + dossier scanner already delivers 80%. Add contact recency to scanner instead. |
| 3 — System Health | **SKIP** | `thunderbird_health.py` + MCP tool already solved. n8n has its own UI. Duplication is waste. |
| 4 — Intelligence Feed | **SKIP** | No data (fare watches empty). Telegram push > dashboard pull for alerts. Fix upstream data first. |
| 5 — Learning Metrics | **SKIP** | 0 corrections, 0 principles. System is a skeleton. Nothing to display. |

### My Recommendation: Compromise — Build Panel 1 Only, Plus Two Upgrades

**Build:**
1. **Revenue Pipeline panel** — A single-page view (could be a static HTML file regenerated daily, does not need to be a React app) showing:
   - Active bookings table: client, cruise/trip, total value, paid, balance, FPD, days to FPD
   - Pipeline summary: total pipeline value, total commission potential, total collected
   - FPD countdown: sorted by urgency, red/yellow/green
   - Data source: Parse dossiers + Booking Master sheet. Regenerate daily at 6:45 AM alongside the morning briefing.

2. **Upgrade the dossier scanner** (not a dashboard — just better morning briefing):
   - Add "last email contact" per client (one Gmail query per client)
   - Add dossier completeness percentage
   - Both feed into the existing morning briefing text. No new UI.

3. **Upgrade fare watch** (not a dashboard — just activate the system):
   - Populate `fare_watches.json` with monitored routes for all active bookings
   - Alerts push to Telegram, not a dashboard

**Skip everything else.** ELON is right that a dashboard for dashboard's sake is vanity. But ELON is wrong if he says you don't need a financial aggregation view — you do, because revenue data scattered across 21 markdown files and a Google Sheet is how things fall through cracks.

### Cost Estimate

| Item | Hours | Complexity |
|------|-------|-----------|
| Commission/pipeline aggregation module | 4-6h | New SQLite or JSON ledger, dossier parser, Sheet reader |
| Static HTML pipeline report (daily regen) | 3-4h | Jinja2 template + WeasyPrint or plain HTML |
| Dossier scanner upgrades (contact recency + completeness %) | 2-3h | Add to existing `thunderbird_dossier_scanner.py` |
| Fare watch population | 1-2h | One-time data entry per active booking |
| **Total** | **10-15h** | |

### The Bottom Line

Revenue is vanity. Profit is sanity. Cash is king.

Right now, Commander cannot answer "what is my total pipeline value and commission potential" without opening 21 files. That is the one thing worth building a view for. Everything else either already works (health, dossier scanner), has no data (learning, fare watches), or is better served by push notifications (intel).

Don't build a dashboard. Build a financial aggregation layer with a daily report. The dashboard comes later, when there are 50 clients and the one-page report isn't enough.

---

*Staff Paper from Vic Harlan, A9 — Dreams2Memories Travel, LLC*
