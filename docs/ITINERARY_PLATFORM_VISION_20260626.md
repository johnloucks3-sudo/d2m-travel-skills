# STAFF NOTE — ITINERARY PLATFORM VISION
## D2M Thunderbird Wing · Commander Directive · 2026-06-26
*From: Col. John A. Loucks III · To: All Wing Staff*
*Classification: Strategic · Chronicle-worthy · Roadmap artifact*

---

## THE MILESTONE

The Silver Nova May 2027 Excursion Planner and Itinerary Viewer represent an **epic milestone** in D2M's product evolution. What we built today is not a one-off deliverable — it is the **founding architecture** of how D2M will present every voyage, every client, every lifecycle.

This is a Chronicle event. Document it, build on it, never let it atrophy.

---

## THE MODEL — GRADUAL BUILDING ON THE CLIENT'S TIMELINE

**Old approach (wrong):** Pull everything from the dossier. Smash it together in a massive exercise. Output a wall of text or a static PDF. Client reads it once or never.

**New approach (right):** Start with a single layer. Make it interactive. Add the next layer when the client is ready. The HTML presentation is client-friendly — they will engage with it. The planner IS the conversation.

### The Build Sequence — Mapped to Canonical Lifecycle TPs/ARCs

**⚠️ DOCTRINE:** Do NOT invent new date milestones. The 23 TPs and ARC touchpoints in the canonical lifecycle ARE the trigger sequence. Every layer of the itinerary platform maps to an existing TP or ARC — not a made-up "T-12mo" date.

**⚠️ ACCELERATION RULE:** Expect the client to compress the timeline. After booking and deposit, the 30,000 ft overview gets requested within **weeks**, not months. Design for early engagement. The high-level itinerary view (all ports, voyage arc, segments) should be ready to show at TP 0.5 or TP 1.1 — not buried in planning prep.

| TP / ARC | Layer Added to Itinerary Platform | Notes |
|---|---|---|
| TP 0.5 · Welcome | Voyage overview: ship, dates, ports, segments | The 30,000 ft view. Client wants this immediately after booking. |
| TP 1.1 · Voyage Preview | Port-by-port destination guide; excursion research begins | First HTML layer live. Client starts engaging with ports. |
| TP 1.2 · Airfare Watch | Air options layer added to itinerary | Prices, routing options, group vs. individual |
| ARC 4.1 · Specialty Dining | Dining reservations layer added | Ship dining + port restaurants |
| ARC 4.2 · Excursion Planning | Excursion planner fully populated; client selects | SELECT interface, budget meter, planning strip |
| ARC 4.3 · Logistics | Hotels + transfers layer added | Pre/post cruise nights, pier transfers, inter-city |
| TP 5.x · Final Prep | All layers locked; horizontal itinerary delivered | Full view: every day, every category, every detail |

**The gradual build is the product.** Each TP is a layer. Each layer keeps D2M in the client's consciousness at the moment that topic is relevant to them. Better for all personas — Rondo needs one step at a time. Melissa needs the emotional arc to develop. Erik needs line items. All of them benefit from watching it build on their own timeline.

---

## NEXT APPLICATIONS (in priority order)

### 1. Kuklinski — Viking Mars Dec 2026
- **Excursion planner first** — same model as Nova. Panama Canal ports + Caribbean stops.
- Then add: air (DEN → Miami or FLL), transfers, no specialty dining needed (Viking all-inclusive).
- Trigger: TP 1.1 Voyage Preview (already overdue per brief — 9 pending). Excursion layer follows immediately.

### 2. Furlow / Ely-Darrow / Nichols — Regent Grandeur Aug 29, 2026
- **Final itinerary** — these are 63 days out. Excursion research needed now (MISSION-802).
- Build the horizontal itinerary for all three couples simultaneously (shared voyage, individual selections).
- This is a GROUP model — one voyage, multiple client views, budget isolation per couple.

### 3. McLeod — Regent Grandeur Dec 2026 + Princess Mar 2027 + Regent Prestige Dec 2027
- **Vertical-first, then horizontal.** Read the McLeod itinerary (all components listed vertically as we have now), then convert to the horizontal sliding view — each day is a column, each row is a category (port · excursion · dining · hotel · transfer · notes).
- This is the most complex active client: 3 voyages, 2 people, multi-year. The horizontal view handles complexity that a vertical list cannot.
- McLeod is the **template stress test** — if the model handles McLeod, it handles any client.

### 4. Loucks — Silver Nova May 2027 (current) + Grandeur Dec 2026 (32-day)
- Nova: continue building layers (air, dining, transfers).
- Grandeur 32-day: this is the **hardest test case** — 32 days, multiple segments, international air, transfers across 4 cities. The horizontal sliding itinerary is the only format that survives this complexity.
- Build the Grandeur itinerary using the same HTML framework. Each segment gets a horizontal swim lane.

---

## THE HORIZONTAL SLIDING ITINERARY

**Concept:** Days run left to right (columns). Categories run top to bottom (rows). The client scrolls horizontally through their voyage — like reading a score or a timeline.

**Row structure (each day column contains):**
- Port / city name + flag + country
- Ship times (arr/dep) or hotel nights
- Excursion selected (name + provider + price + time)
- Dining reservation (restaurant + time + confirmation)
- Air leg (flight number + dep/arr + airline)
- Transfer (pickup + dropoff + vehicle type)
- Notes / warnings / reminders
- Budget running total for that day

**Why horizontal wins:**
- A 32-day voyage looks insane vertically (32 dense rows). Horizontally it scrolls naturally — like a calendar.
- Clients can see "blank days" (no excursion, no dining booked) at a glance and feel urgency to fill them.
- Segment breaks become visual columns — the eye tracks three distinct "chapters."
- Mobile: swipe right through the voyage. Intuitive.

**Technical approach:**
- Same localStorage sync as Nova — selections made anywhere persist everywhere.
- Fixed left column (category labels). Scrollable right panel (days).
- CSS: `display: grid` with `grid-template-columns: 140px repeat(N, 200px)`. Horizontal scroll on the day panel only.
- Day columns collapse on mobile (tap to expand).

---

## COMMANDER'S ARCHITECTURAL ROLE

*"My job is to structure the long-term models to allow us to build on the client's timeline."*

This is the right framing. The Wing executes the layers. The Commander owns the model:
- What categories go on each row
- What triggers each build phase (which TP, which FPD milestone)
- What the client sees vs. what stays internal
- When a layer is "done enough" to share vs. when it needs another pass

The Wing needs: search, scanning, price quotes, booking data, credential access. Commander provides: the model, the sequence, the send authority.

---

## CONNECTION TO EXISTING ROADMAP ARTIFACTS

| Artifact | Location | Connection |
|---|---|---|
| Flight Plan | `output/flight_plan.html` + `docs/FLIGHT_PLAN.md` | Air layer of the horizontal itinerary |
| Campaign Plan | `output/campaign_plan_v2.txt` | Client lifecycle sequence drives build triggers |
| Mission | `docs/MISSION_DEVELOPMENT_WAY_AHEAD_20260601.md` | This platform is the client-facing proof of the mission |
| CCR | `output/` | Technology readiness — HTML platform is Gate 4 equivalent |
| Build Plan (Flights/Hotels) | `docs/BUILD_PLAN_FLIGHTS_AND_HOTELS.md` | Direct feed into horizontal itinerary layers |
| Canonical Lifecycle 23 TPs | Memory: `reference_canonical_lifecycle_touchpoints.md` | TP timing drives the build phase triggers |

**This vision document IS the roadmap.** Everything above feeds into it. The itinerary platform is where the roadmap becomes visible to the client.

---

## WHAT THE WING DOES NEXT

1. **MISSION-802** — Grandeur Aug 29 excursion research (Furlow/Ely/Nichols) — build the planner, same Nova model
2. **McLeod vertical audit** — read the full McLeod itinerary, identify all missing components vs. the layer model above
3. **Horizontal itinerary prototype** — build one horizontal view (start with McLeod Dec 2026, single voyage, 19 days)
4. **Kuklinski excursion planner** — spin up Viking Mars Dec 2026 equivalent of Nova planner
5. **Loucks 32-day planning** — Grandeur Dec 2026 horizontal itinerary begins

*All of the above are pre-approved operational actions under Hale's 95% autonomy band. None require Commander gates except WF-17 on final client delivery.*

---

*— V. Hale, VCS · Thunderbird Wing · 2026-06-26*
*Filed: `docs/ITINERARY_PLATFORM_VISION_20260626.md`*
*Copy: Chronicle Event Record · Flight Plan · Campaign Plan*
