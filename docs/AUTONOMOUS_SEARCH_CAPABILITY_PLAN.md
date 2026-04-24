# Thunderbird OS — Autonomous Search Capability Plan
## Dreams2Memories Travel, LLC · v2.0 (Advisor-Elevated) · 2026-04-20

---

## EXECUTIVE SUMMARY

**The honest current state:** D2M has partial data-collection tools and zero autonomous delivery. The gap is not "which hotel API" — it is the absence of a scheduler that fires searches without prompting, a formatter that converts raw results to D2M standard, and observability so Hale knows when the system worked or failed.

**The plan below is a single recommended sequence**, not a menu of options. Each layer enables the next. Building hotel credentials before the scheduler exists produces another manual lookup tool. The scheduler is the critical path.

---

## LAYER 0 — CURRENT CAPABILITY AUDIT (Ground Truth)

| Category | Tool / Module | Status | What It Actually Does |
|----------|--------------|--------|----------------------|
| **Flights** | Kayak (Playwright) | ✅ Functional | Price scrape, sanity gate wired |
| **Flights** | Skiplagged (Playwright) | ✅ Functional | Secondary source |
| **Flights** | Centrav B2B | ⚠️ Partial | reCAPTCHA blocks headless; manual session required |
| **Flights** | Expedia/CheapTickets | ❌ Bot-blocked | Not usable headless |
| **Hotels** | thunderbird_hotel_search.py | 🔴 Dormant | Module built, zero credentials; Hotelbeds API not activated |
| **Transfers** | Kiwitaxi (core) | ✅ Limited | ~20 routes, not airport-agnostic |
| **Tours/Excursions** | GetYourGuide | ⚠️ Consumer-only | No B2B API; scrape-only, fragile |
| **Cruise excursions** | (none) | ❌ Not built | Viking/Silversea/Regent portals require agent login |
| **Dining** | (none) | ❌ Not built | OpenTable/Resy have no travel-agent APIs |
| **Cruise prices** | thunderbird_price_monitor.py | 🔴 Config-empty | Structured skeleton; WATCHED_DEPARTURES = []; config files don't exist; **not operational** |
| **Scheduler** | (none) | ❌ Not built | **No lifecycle-triggered search automation exists** |
| **Format/Enrichment** | (none) | ❌ Not built | No pipeline converting raw JSON → D2M standard output |
| **Observability** | (none) | ❌ Not built | No system reporting search ran/failed to Hale |

**Key finding:** The absence of a scheduler means every tool above — even the functional ones — requires a human to initiate. We have ingredients; we do not have a kitchen.

---

## INTEGRATION TESTS — ACCEPTANCE CRITERIA

Before claiming any capability is autonomous, these three tests must pass:

**T-10: Scheduler fires without prompting**
> Given Kuklinski TP "Air Fare Watch Delivery" is due Jun 17, does the system fire the air search on Jun 17 (or Jun 3 for the draft-due lead time) without Commander or Hale initiating it?
> - PASS: Search fires at scheduled time, results land in Hale review queue
> - FAIL: Human has to trigger search manually

**T-11: Raw results → D2M standard format**
> Given a flight search returns raw JSON (airline, price, route, times), does the output include name + link + customer comments + price (economy + premium) — the McLeod gold standard?
> - PASS: Formatted output is client-ready without human enrichment
> - FAIL: Hale receives raw JSON and must manually format before Commander sees it

**T-12: Search output routes through Hale review → Commander inbox**
> Given T-10 and T-11 pass, does the formatted result arrive in Hale's review queue (wing_comms.md or structured inbox) within 15 minutes of search completion, and surface to Commander's morning brief?
> - PASS: Commander sees formatted, reviewed search result without initiating any step
> - FAIL: Result sits in a file nobody reads

**These three tests define "autonomous." Anything that fails T-10, T-11, or T-12 is a manual-assist tool, not an autonomous search.**

---

## THE BUILD SEQUENCE (Single Recommended Path)

### PHASE 1 — SCHEDULER BACKBONE (P0, Weeks 1–2)
*The scheduler is the critical path. A working hotel API with no scheduler is still a manual lookup.*

**What to build:**
```
lifecycle_search_scheduler.py
├── Load touchpoint calendar (from dossier or TASKS array)
├── For each TP with search_trigger: True, fire search N days before TP date
│   Example: "Air Fare Watch Delivery" due Jun 17 → trigger Jun 3 (14d lead)
├── Call registered search functions (flights first — only functional ones)
├── Write raw results to /home/john/Thunderbird/search_queue/{client}_{date}_{type}.json
└── Emit scheduler log entry → hale_review_queue.md
```

**Config structure (per dossier/client):**
```json
{
  "client": "Kuklinski",
  "searches": [
    {
      "tp": "Air Fare Watch Delivery",
      "due": "2026-06-17",
      "trigger_days_before": 14,
      "type": "flights",
      "routes": ["RIC→PTY", "RSW→FLL"],
      "guests": 6
    },
    {
      "tp": "Hotel: 3+3 Search Delivery",
      "due": "2026-06-17",
      "trigger_days_before": 14,
      "type": "hotels",
      "cities": ["Panama City", "Fort Lauderdale"],
      "nights": 3,
      "guests": 2
    }
  ]
}
```

**Cron / systemd timer:**
```bash
# Fire daily at 06:00 MT — check if any triggers due today
0 6 * * * /home/john/Thunderbird/scripts/lifecycle_search_scheduler.py
```

**Done when:** T-10 passes for Kuklinski air search.

---

### PHASE 2 — FORMAT / ENRICHMENT LAYER (P0, Week 2–3)
*Raw scraper JSON is not client-presentable. This layer is as important as the data layer.*

**What to build:**
```
search_formatter.py
├── Input: raw JSON from any search tool
├── Enrich each result:
│   ├── Name (airline/hotel/operator)
│   ├── Clickable link (booking URL or search URL)
│   ├── Customer reviews (scrape or cached rating)
│   ├── Price tiers: economy/premium for flights; queen/king for hotels
│   └── D2M commission flag if applicable
├── Output: formatted markdown block → client-ready
└── Template: McLeod email as the reference standard
```

**McLeod standard (required fields per result):**
```
## [Airline/Hotel Name]
**Route/Location:** [specific]
**Price:** Economy $X | Premium $Y (per person)
**Link:** [clickable URL]
**Reviews:** [4.2/5 — 1,847 reviews — "highlight quote"]
**D2M note:** [commission opportunity / upgrade flag]
```

**Done when:** T-11 passes — formatted output is client-ready without human enrichment step.

---

### PHASE 3 — ROUTING TO HALE REVIEW QUEUE (P1, Week 3)
*Closes the loop: autonomous search → Hale reviews → Commander inbox.*

**What to build:**
```
hale_review_queue.md (append-mode structured file)
├── Entry format: [date] | client | search type | status | file path | flagged items
├── Hale reads queue at session start or morning brief
└── Approved results → surface in Commander morning brief
```

**Morning brief integration:**
```
## 🔍 AUTONOMOUS SEARCHES — SINCE LAST SESSION
| Client     | Type    | Triggered  | Status  | Items | Action |
|------------|---------|------------|---------|-------|--------|
| Kuklinski  | Flights | 2026-06-03 | ✅ Done  | 6     | [Review] |
| Kuklinski  | Hotels  | 2026-06-03 | ❌ FAIL  | 0     | Hotelbeds creds expired |
```

**Done when:** T-12 passes — Commander sees formatted search result in morning brief without initiating any step.

---

### PHASE 4 — HOTEL CREDENTIALS (P1, parallel with Phase 3)
*Hotel data is the biggest gap but cannot substitute for the scheduler/formatter.*

**Hotelbeds B2B API:**
- Register at developer.hotelbeds.com (agency verification required)
- **Realistic timeline: 2–4 weeks** (B2B verification is not instant; agency documentation required)
- Interim option: Bedsonline portal login (same parent company, browser-based, no API)
- Config target: `/home/john/Thunderbird/config/hotelbeds_credentials.json`
- Module already built: `thunderbird_hotel_search.py` — ready to activate on credential receipt

**Do not block Phase 1–3 on this.** A scheduler that fires hotel searches to a stub is better than a hotel API with no scheduler.

---

### PHASE 5 — EXPAND TOOL COVERAGE (P2, Weeks 4–8)
*Add tools in order of client impact. Each tool plugs into the existing scheduler.*

| Tool | Priority | Approach | Blocker |
|------|----------|----------|---------|
| Cruise excursions (Viking/Silversea) | HIGH | Agent portal session (Playwright + saved login) | Portal login credentials |
| Transfers (expand Kiwitaxi) | MEDIUM | Add routes config; Klook/Blacklane APIs | API keys |
| Tours (GetYourGuide) | MEDIUM | GYG Partner API (requires partner application) | Application approval |
| Dining | LOW | OpenTable widget scrape (fragile) | No stable API exists |
| Cruise prices (thunderbird_price_monitor.py) | HIGH | Populate WATCHED_DEPARTURES config; validate against live data | Zero config currently; needs test run |

**Cruise price monitor activation (specific steps):**
1. Create `/home/john/Thunderbird/config/watched_departures.json` with 2-3 test voyages
2. Create empty `price_history.json`
3. Run module against live Silversea/Regent pages
4. Validate output matches real prices
5. Only then add to scheduler as a live tool

---

### PHASE 6 — OBSERVABILITY (P1, ongoing from Week 3)
*Autonomous systems fail silently. This is not optional.*

**Minimum viable observability:**
- Scheduler run log: timestamp, client, search type, result count, errors
- Hale review queue: every search result has a status (PASS / FAIL / FLAGGED)
- Morning brief: always shows "X searches ran since last session / Y failed"
- Alert threshold: any search that fails 3 consecutive runs → Telegram alert to Commander

**Failure modes to instrument:**
- Kayak bot detection (429 / captcha page)
- Hotelbeds API auth expiry
- Centrav session timeout
- GetYourGuide rate limiting
- Search config missing (WATCHED_DEPARTURES empty, routes unspecified)

---

## MILESTONES & TIMELINE

| Week | Deliverable | T-Test |
|------|-------------|--------|
| 1 | Scheduler backbone live, fires Kuklinski air search on trigger date | T-10 |
| 2 | Format/enrichment layer live for flights | T-11 |
| 3 | Results route to Hale queue, surface in morning brief | T-12 |
| 3–4 | Hotel credentials submitted to Hotelbeds | — |
| 4 | Cruise price monitor config populated, validated live | — |
| 5–7 | Hotelbeds credentials received (est.), hotel search activates | — |
| 6–8 | Cruise excursion portal sessions, transfer route expansion | — |

---

## WHAT "AUTONOMOUS" LOOKS LIKE AT MATURITY

On Jun 3, 2026 (T-14 from Kuklinski Air Fare Watch Delivery):
1. Scheduler fires at 06:00 MT — no human initiated it
2. Kayak + Skiplagged searched for RIC→PTY and RSW→FLL for 6 guests
3. Formatter enriches results: airline names, links, economy/premium prices, review scores
4. Hale review queue updated: "Kuklinski air search — 6 results — 2 flagged for upsell"
5. Commander's morning brief includes: "🔍 Kuklinski air search complete — review in queue"
6. Commander clicks review, approves, Dani gets brief to draft delivery email

**This is the goal.** Not "we have a Hotelbeds API." The goal is: the Wing searched, formatted, reviewed, and surfaced — without Commander or Hale initiating any step.

---

## WHAT NOT TO BUILD (YET)

- **AI-synthesized travel recommendations** — research before scraping. Get the data working first.
- **Dining automation** — no stable API exists. Manual research by A2 is more reliable.
- **Multi-city cruise excursion automation** — too portal-dependent. Phase 5+ only.
- **Fare prediction / price forecasting** — requires 90+ days of historical data we don't have.

---

*Autonomous Search Capability Plan v2.0 | Thunderbird Wing | D2M | 2026-04-20*
*Elevated by advisor review: scheduler-first sequence, integration tests T-10/T-11/T-12, format layer, observability, realistic Hotelbeds timeline, price monitor ground-truthed as config-empty.*
