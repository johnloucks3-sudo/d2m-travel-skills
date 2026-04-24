# STAFF PAPER — Price Intelligence Tools → Lifecycle Integration
## COS Hale → Commander Loucks | 2026-04-17

---

**ISSUE:** Four price intelligence tools now exist (flight, tour, transfer, hotel), but the lifecycle scheduler's SEARCH_WINDOW_OPEN events post tasks to wing_comms as unstructured text — no automation connects tool invocation to lifecycle triggers or to Dani's client email pipeline.

---

**DISCUSSION:**

The lifecycle scheduler is live, 73 touchpoints across 3 clients. It already fires `SEARCH_WINDOW_OPEN` events for ARC1 (Airfare+Hotel), ARC2 (Excursions), ARC3 (Transfers), and the event writes a task to `OpsCenter/collaboration/wing_comms.md` with staff assignment, window dates, and notes. What happens next is manual: a human reads the task and (today) does nothing automated.

The four tools built this session map perfectly to three ARC families:
- **ARC1-A/B/C** (Airfare + Hotel) → `/flight-price` + `/hotel-price`
- **ARC2-A/B/C** (Excursions) → `/tour-price`
- **ARC3-A/B/C** (Transfers) → `/transfer-price`

Tool status:
- `/flight-price` — LIVE. Centrav (B2B) requires manual session refresh every ~2hrs. Kayak/Skiplagged for consumer sanity-check.
- `/tour-price` — LIVE. GetYourGuide + TourRadar. Consumer retail pricing (no wholesale path yet).
- `/transfer-price` — LIVE. Kiwitaxi, 20+ pre-mapped D2M routes. Fixed per-vehicle pricing.
- `/hotel-price` — DORMANT. MCP module built, awaiting `hotelbeds_credentials.json`. Activate via Hotelbeds developer registration or Bedsonline portal credentials.

The persona stack for lifecycle search windows:
- **A2 Dembe** — runs the tools, interprets raw output, surfaces 3 options (value/recommended/luxury)
- **A9 Vic** — validates markup math (net × 1.25 standard, × 1.22 SLH) before anything goes to Dani
- **A3 Dani** — aggregates A2+A9 results, crafts client email (aggregator→artist→advocate), holds in WF-17 gate
- **COS Hale** — orchestrates timing, reviews Dani's draft, routes to Commander for send approval
- **Commander** — send gate only (SO 21 MAR 2026)

Weekly reports (WEEKLY_REPORT_DUE events): A2 Dembe compiles week's tool findings into a structured intel report → SEND to johnloucks3@gmail.com (not draft, per intel full-send SO 27 MAR 2026). Format: what we searched, what we found, what changed since last week, recommendation.

---

**OPTIONS:**

**A — Manual-Triggered (no code change):**
Current behavior. Scheduler posts task to wing_comms. Hale or A2 reads task and manually runs tools when prompted. Cons: tools get forgotten, research happens ad-hoc, no guaranteed cadence.

**B — Wired Notifications (light code change, recommended):**
Upgrade `_fire_search_window_open()` to detect ARC type from TP label → append specific tool invocation instructions to the wing_comms task (which tool to run, with what arguments, for which client's route/destination/dates). A2 Dembe executes when she picks up the task. Scheduler stays event-driven; tools stay on-demand. No auto-execution, no cost surprises.

**C — Auto-Execute on SEARCH_WINDOW_OPEN (heavier, future):**
Scheduler runs the tools directly when the event fires, caches output to `core/travel/data/`, posts structured results to wing_comms. Dani's pipeline reads cached results at email-generation time. Requires: credential management for Centrav (flight), Hotelbeds (hotel), reliable tool availability. Best long-term goal but overkill until hotel credentials are set.

---

**ACTIONS:**

1. **Commander approves Option B** (or selects A or C) — no code written until you decide.

2. **If B approved:** Modify `_fire_search_window_open()` in `D2M/d2m_lifecycle_scheduler.py` — add ARC-type detection logic (match TP label against ARC1/ARC2/ARC3 keywords), append tool-specific instructions to the wing_comms task post. Estimated: 40 lines of Python.

3. **Hotel activation (separate action):** Register D2M at developer.hotelbeds.com OR provide Bedsonline portal credentials → create `~/Thunderbird/hotelbeds_credentials.json` → `/hotel-price` goes live. Until then, ARC1 hotel searches are manual lookups.

4. **Centrav session management:** Current TTL is ~2hrs. For lifecycle reliability, evaluate whether a scheduled session-refresh hook is feasible, or accept that Commander runs `--centrav-login` at session start.

5. **Weekly report template:** Hale will draft the standard weekly report format (A2 → Commander) once Option B or C is selected — different structure depending on whether results are cached vs. generated on demand.

---

*Prepared by: COS Hale | Reviewed by: COS Hale | Routing: Commander for decision*
