# SO-2026-06-03: D2M Trip Validation Report — Standard Operating Procedure
**Document:** SO-TripValidation_v1  
**Owner:** Sterling (A7) | **Drafted by:** Hale (COS)  
**Approved:** Commander | **Effective:** 2026-06-03 | **Version:** 1.1  
**Binding on:** All Wing staff producing client trip validation reports

---

## 1. PURPOSE

This SO codifies the canonical D2M Trip Validation Report format derived from the Furlow/Ely-Darrow Regent validation (booking 3071222/3096289, Jun 2026). Every future client trip validation — cruise, land, hybrid — follows this structure without deviation.

Objectives:
- Eliminate duplicate action items across sections
- Enforce single-source-of-truth data sourcing per section
- Standardize badge language and visual treatment
- Produce consistent validation coverage scores for Commander briefings

**Template:** `~/Thunderbird/templates/trip_validation_template_v1.html`  
**CSS class reference:** `~/Thunderbird/templates/d2m_base.css.j2`

---

## 2. CANONICAL SECTION STRUCTURE — 14 SECTIONS TOTAL

Every Trip Validation Report contains exactly these sections in this order. No omissions. No additions without Commander approval and SO amendment.

### 2.1 Content Sections (1–11, including §3b)

| # | Section Title | Required Content | Primary Data Source |
|---|---|---|---|
| 1 | **Trip Overview** | Client names, booking reference(s), ship/property, departure/return dates, suite/cabin/room category, agent, agency, booking status | RSSC Agent Portal or line-specific booking portal |
| 2 | **Flight Schedule** | One row per flight leg: date, route, airline, flight number, class, confirmation code, seat assignment(s), status badge | RSSC air portal; or GDS/AmEx Platinum Travel if booked independently |
| 3 | **Hotels & Lodging** | One row per stay: check-in/out, property, confirmation number, room type, nightly rate, total cost, status badge; cancelled stays rendered with strikethrough | AmEx Fine Hotels & Resorts (FHR) concierge portal; or cruise-line included hotel portal; or direct booking confirmation |
| 3b | **Group Booking Ripple Map** | One row per shared booking/group arrangement: service name, primary booking reference, affected clients, non-affected clients, cancellation impact notes, status badge | Dossier cross-reference; live portal scrape; Commander notes log |
| 5 | **Transfers** | One row per transfer leg: date, route, provider, confirmation reference, cost, status badge; cancelled transfers rendered with strikethrough | Regent/cruise-line transfer portal; or ground vendor confirmation |
| 6 | **Shore Excursions** | One row per excursion: date, port, tour name, booking reference, departure time, duration, cost classification (INCLUDED / PAID), status badge | RSSC Agent Portal — Excursions tab (live scrape) |
| 7 | **Specialty Dining** | One row per restaurant reservation: date, restaurant, time, covers, reservation reference, status badge | RSSC Agent Portal — Dining tab |
| 8 | **Culinary Arts Kitchen** | One row per booking: date, session, time, confirmation, status badge; if not yet bookable, note booking-open date | RSSC Agent Portal — CAK tab |
| 9 | **Travel Insurance** | One row per coverage type: policy name/source, coverage limit, deductible, status badge; coverage gaps noted inline (see § 5.2) | Chase/AmEx cardholder portal; standalone policy documents uploaded to TESS |
| 10 | **Document Status** | One row per traveler per document: passport number (last 4 digits only), expiry, 6-month rule pass/fail, visa status where applicable, TESS verification status badge | TESS CRM — client profile Documents tab; cross-check dossier photo intake |
| 11 | **Daily Itinerary** | One row per day: day number, date, location/port, scheduled activity, booking reference, status badge | RSSC Agent Portal — Itinerary tab (live scrape); merged with flight and hotel data for pre-/post-cruise days |

**§2 Flight Schedule — per-client seat rule (v1.1):** For shared flights (same flight number, same date), list each client's seat assignment(s) separately — even when booked under the same PNR. No group seat status aggregates permitted. If unassigned, use status badge per client.

**§3b Group Booking Ripple Map — hard rule (v1.1):** Any shared booking (hotel group block, same-flight PNR group, shared transfer) that affects multiple clients in the same validation window must be documented in this section. Purpose: single source of truth for who is affected when a booking changes. Omit this section only when no shared bookings exist; note "No shared bookings — §3b not applicable."

### 2.2 Summary Sections (12–14)

| # | Section Title | Required Content | Source |
|---|---|---|---|
| 12 | **Financial Summary** | Line items: cruise fare, flights, hotels, transfers, excursions, insurance, gratuities; sub-totals; TOTAL; payment method; paid/due/FPD status badges | RSSC booking summary (portal); hotel/flight confirmations; TESS payment records |
| 13 | **Validation Matrix** | Rollup table by category: count, confirmed, pending, issues, coverage %; overall coverage score | Calculated from sections 1–12 (including §3b) (see § 6) |
| 14 | **Actions Required** | Consolidated, numbered, deduplicated action list drawn from ALL prior sections | Deduped from inline alerts (see § 7) |

**Hard rule:** No standalone "To-Do List," "Open Items," or "Next Steps" section separate from § 14. Ever. Any such section is a format violation — Sterling flags at QA gate.

---

## 3. DATA SOURCES

### 3.1 Source Hierarchy — Precedence Order

When sources conflict, the higher-ranked source wins. Discrepancies must be resolved or flagged before WF-17.

| Rank | Source | Used For | Access Method |
|---|---|---|---|
| 1 | **RSSC Agent Portal** (live scrape) | Cruise bookings, excursions, dining, CAK, ship itinerary, air booked through RSSC | Playwright scrape via `thunderbird_browser.py`; or manual agent login at regentsevenseas.com/agent |
| 2 | **AmEx Platinum FHR Concierge Portal** | Hotels booked via Fine Hotels & Resorts; pre-/post-cruise lodging | AmEx Travel portal under logged-in Platinum account; confirmation email cross-reference |
| 3 | **TESS CRM** | Guest documents (passports, visas), contact info, payment records, uploaded insurance policies | MCP tools: `tess_get_client`, `tess_get_booking`, `tess_get_trip`; token: `~/Thunderbird/tess_token.json` |
| 4 | **Chase Sapphire / AmEx cardholder portals** | Travel insurance coverage details, trip interruption benefits | Chase Travel portal or AmEx benefits portal; cardholder benefit guide PDFs |
| 5 | **Client Dossier** (cross-reference only) | Sanity check for all above; notes, preferences, group coordination data | `~/Thunderbird/dossiers/[ClientName]_[Line]_[Booking].md` |

**Rule:** The dossier is a cross-reference, never the sole source for any section. If portal data and dossier disagree: portal is authoritative. Flag the delta.

**Dossier Freshness Gate (v1.1):** Before any validation begins, check all relevant dossier modification dates. If any dossier is >30 days stale (>30 days since last modification), flag to Hale. Hale decides: (a) proceed with dossier data + flag deltas, or (b) trigger portal rescrape before validation.

### 3.2 RSSC Agent Portal — Scrape Protocol

Per booking reference (7-digit Regent ID):
1. Navigate to Reservation Detail page
2. Pull: booking status, suite number, passengers, payment summary, FPD, credits
3. Navigate Excursions tab → capture all bookings (name, port date, ref, INCLUDED/PAID)
4. Navigate Dining tab → capture all specialty dining reservations
5. Navigate Itinerary tab → capture port-by-port daily schedule
6. Navigate Air tab → capture all flight legs with confirmation codes
7. Record scrape timestamp — used as "as of" date in report header

If portal is unavailable: note "RSSC portal offline — data from dossier [date]. Verify at next scrape." Flag as pending.

### 3.3 AmEx FHR — Hotel Pull Protocol

1. Log into AmEx Travel portal under Platinum cardholder account
2. Retrieve hotel confirmation: property, dates, room type, rate, FHR benefits (breakfast, amenity credit, room upgrade if available)
3. Cross-check against dossier for cancelled/pending stays
4. Cancelled stays: include in Hotels section with strikethrough formatting and `badge-warn` status
5. FHR benefits earned: note in row comments; do not include in financial totals unless confirmed by hotel

### 3.4 TESS — Document Verification Protocol

For each traveler on the booking:
1. `tess_get_client` → pull passport on file (expiry date, issue country)
2. Calculate 6-month rule: passport must be valid 6 months past RETURN date
3. If no passport on file: status = `badge-warn` — "Not provided to D2M"
4. If passport expires within 6-month window: status = `badge-warn` — "6-month rule FAIL — expires [date]"
5. If passport valid: status = `badge-ok` — "Verified [expiry]"
6. Visa: flag required visas per itinerary ports; source = State Dept / cruise line requirements

---

## 4. BADGE TAXONOMY

Badges apply to individual rows within section tables. Every row that represents a booking, reservation, or status must carry one badge. Rows without a badge are a format violation.

| Badge | CSS Class | Display | Meaning | When to Use |
|---|---|---|---|---|
| ✓ Confirmed | `badge-ok` | Green | Booked, paid, and verified against primary source | Confirmed excursion, paid hotel, verified passport, assigned seat |
| ⚠ Pending | `badge-pending` | Yellow | Ticketed or reserved but not fully finalized | Seat not yet assigned, booking on waitlist, payment processing, document not yet uploaded to TESS |
| ✗ Issue | `badge-warn` | Red | Requires corrective action or cancellation | Cancelled stay still showing active, 6-month passport fail, unresolved discrepancy |
| ℹ Info | `badge-info` | Blue | Informational — no action required | Open-seating dining (no reservation needed), policy note, included benefit |

**Dining-specific rules:**
- Restaurant requires reservation + reservation exists → `badge-ok`
- Restaurant requires reservation + not yet booked → `badge-warn` with booking-window note
- Walk-in / open-seating restaurant → `badge-info` ("Open seating — no reservation required")
- CAK not yet bookable (booking window not open) → `badge-pending` with open-date note
- CAK not booked (window open) → `badge-warn`

**Excursion-specific rules:**
- INCLUDED excursion, confirmed → `badge-ok` + INCLUDED cost badge inline
- PAID excursion, confirmed, charged → `badge-ok` + dollar amount
- Any excursion waitlisted → `badge-pending`

---

## 5. ALERT SYSTEM

### 5.1 Alert Types

Three types. Each appears inline, immediately after the section table it relates to. Alerts are **never** repeated in § 14 Actions Required — § 14 references alerts by number only.

| Alert Class | Border Color | Background | Use For |
|---|---|---|---|
| `alert alert-warn` | Orange `#b26a0a` | `#fff9f0` | Actionable item requiring follow-up before departure; owner and deadline required |
| `alert alert-ok` | Green `#1b7a2b` | `#f0fdf4` | Positive milestone or confirmed status worth surfacing to client/Commander |
| `alert alert-error` | Red `#c0392b` | `#fef5f3` | Critical issue; reserved for items that block travel if unresolved |

`alert-error` is rarely used. Insurance gaps, unresolved payment disputes, expired passports within the travel window qualify. Seat assignment gaps do not.

### 5.2 Alert Placement Rule

- One alert per distinct issue. Do not bundle multiple issues into one alert box.
- Alert appears immediately after the table of the section it belongs to.
- Alert is numbered sequentially across the entire document (ALERT-01, ALERT-02, etc.)
- The alert number is how § 14 references it: "ALERT-01: Assign seats on BB4X94 (HEL→ARN)"

### 5.3 Insurance Gap Handling

Insurance section alerts follow the negative-space rule (SO-PIPELINE-INTEGRITY-20260528):
- Do not speculate about coverage adequacy without confirmed policy details
- If client relies on credit card coverage: note the card, note what coverage is stated in the benefit guide, note what coverage guide version was checked
- Do not recommend specific standalone policies without Commander direction
- Flag gaps as: "Credit card coverage confirmed for X. Standalone policy: not on file. Commander review recommended."

**Insurance Status Gate — pre-validation (v1.1):** Before beginning any trip validation, confirm: "Insurance status known for every client on this booking?" If any client's insurance status is unknown (no policy on file, no card benefit guide checked, no dossier entry), surface to Commander before proceeding with validation. Owner: Hale.

---

## 6. VALIDATION MATRIX CALCULATION

Section § 13 (Validation Matrix) summarizes validation status across all trackable categories.

### 6.1 Categories and Scoring

| Category | What Gets Counted |
|---|---|
| Flights | Each flight leg = 1 item |
| Hotels | Each night's stay property = 1 item (not per night) |
| Transfers | Each transfer leg = 1 item |
| Excursions | Each booked excursion = 1 item |
| Specialty Dining | Each reservation-required restaurant booking slot = 1 item |
| Culinary Arts Kitchen | Each session = 1 item (if applicable) |
| Insurance | Each coverage type line = 1 item |
| Documents | Each traveler-document pair = 1 item |

### 6.2 Scoring Rules Per Row

- **Confirmed:** `badge-ok` rows
- **Pending:** `badge-pending` rows
- **Issues:** `badge-warn` rows
- **Info rows** (`badge-info`): excluded from count; do not inflate totals

### 6.3 Coverage Percentage Calculation

```
Coverage % = (Confirmed) / (Confirmed + Pending + Issues) × 100
```

Round to nearest whole number. Display as integer (e.g., "94%", not "94.3%").

### 6.4 Matrix Table Format

| Category | Total | Confirmed | Pending | Issues | Coverage |
|---|---|---|---|---|---|
| Flights | N | N | N | N | N% |
| Hotels | N | N | N | N | N% |
| Transfers | N | N | N | N | N% |
| Excursions | N | N | N | N | N% |
| Specialty Dining | N | N | N | N | N% |
| Insurance | N | N | N | N | N% |
| Documents | N | N | N | N | N% |
| **OVERALL** | **N** | **N** | **N** | **N** | **N%** |

Overall row = sum of all categories. Overall coverage = confirmed / (confirmed + pending + issues) across all categories combined.

### 6.5 Summary Box (Header Stats)

The report header summary box displays five KPIs derived from the matrix:

| KPI | Calculation |
|---|---|
| Total Days | Departure date to return date inclusive |
| Total Confirmed Cost | Sum of all `badge-ok` financial line items in § 12 |
| Bookings Tracked | Count of all rows across sections 2–10 (including §3b) (excl. info rows) |
| Countries | Count of distinct countries in § 11 daily itinerary |
| Validation Coverage | Overall coverage % from matrix |

---

## 7. ACTIONS REQUIRED — CARDINAL RULES

Section § 14 is the single, consolidated action list for the entire report. It is the ONLY action list.

### 7.1 Deduplication Rule

Before writing any action item, check: does another section already surface this issue as an alert? If yes, the action item is the alert reference only — not a restatement.

**Correct:** `1. ALERT-03 — Cancel Haymarket Hotel + associated transfer (Transfers row 2). Owner: Hale. Deadline: ASAP.`  
**Wrong:** Two separate items — one for the hotel cancellation and one for the transfer.

If two alerts (in different sections) resolve to a single underlying action: merge them into one action item.

### 7.2 Action Item Format

```
[N]. [ALERT-XX] — [Action description]. Owner: [Staff or Commander]. Deadline: [Date or "Before departure"].
```

- Owner is always a named staff member or "Commander" — never "TBD"
- Deadline is an absolute date when known; "Before [milestone]" when date is unknown
- If Commander action: note "Commander review / send required"

### 7.3 What Does NOT Go in § 14

- Confirmed items (badge-ok) — these are done, not actions
- Info items (badge-info) — no action needed
- Restatements of section content — the alert number is sufficient
- Speculative or future-state items ("may want to consider") — not actions

### 7.4 Completeness Check (JET gate)

Before WF-17, JET verifies:
- Every `alert-warn` and `alert-error` in the document has a corresponding § 14 entry
- No `badge-pending` row is unaddressed if it has a clear resolution path
- No duplicate items appear in § 14
- No item in § 14 also appears verbatim in another section

---

## 8. REGENT-SPECIFIC DINING DATA

Seven Seas Grandeur restaurant reservation policy (applicable to Furlow/Ely-Darrow booking 3071222/3096289 and all Grandeur sailings):

| Restaurant | Policy | Badge Default |
|---|---|---|
| Prime 7 | Reservation required | `badge-warn` if unbooked (window open) |
| Chartreuse | Reservation required | `badge-warn` if unbooked (window open) |
| Pacific Rim | Reservation required | `badge-warn` if unbooked (window open) |
| Compass Rose | Open seating | `badge-info` ("Walk-in — no reservation required") |
| Sette Mari | Open seating | `badge-info` ("Walk-in — no reservation required") |
| La Veranda | Open seating | `badge-info` ("Walk-in — no reservation required") |
| Solis | **Grandeur does NOT have Solis** — newer ships only | Omit entirely for Grandeur reports |
| The Chef's Table | **Grandeur does NOT have The Chef's Table** | Omit entirely for Grandeur reports |

Booking window opens: final payment date + 60 days. If window is not yet open, badge = `badge-pending` with window-open date noted.

For non-Regent products: replace this section with line-specific dining policy derived from cruise line documentation. Sterling maintains line-specific reference data in `~/Thunderbird/intel/cruise_lines/`.

---

## 9. STAFF QA GATES

All four gates must be satisfied before the validation report enters WF-17.

| Gate | Staff | What They Verify | Blocking? |
|---|---|---|---|
| Financial | Harlan (A9) | All dollar figures match portal/TESS source within session; FPD matches portal; payment status current | Yes — no WF-17 without Harlan sign-off on any report containing $ figures |
| Content | Dani (A3) + Naia (EXEC) | Names spelled correctly, dates accurate, venues/restaurants correct for the sailing, brand voice consistent | Yes |
| Process / SO Compliance | Sterling (A7) | Section count = 14, badge taxonomy correct, no duplicate action items, alert numbering sequential, § 14 complete | Yes |
| Release | Commander | WF-17 send gate — sole send authority per SO-WF17-CLIENTSEND-PROHIBITION-20260530 | Yes |

**Note on Pipeline Integrity (SO-PIPELINE-INTEGRITY-20260528):** Financial figures in this report must trace to a live portal scrape or TESS booking record from the same session. Figures from the dossier alone require Harlan to flag the delta and confirm resolution before sign-off.

---

## 10. REPORT HEADER REQUIREMENTS

Every report header must include:

```
DREAMS2MEMORIES TRAVEL, LLC — TRIP VALIDATION
[CLIENT NAMES] | [TRIP TITLE] | [DEPARTURE – RETURN DATES]
Validation Date: [DATE] | Prepared by: [Staff name(s)] | RSSC Portal Scrape: [Timestamp]
```

- "Prepared by" = the Wing staff member(s) who assembled the report, not the Commander
- RSSC Portal Scrape timestamp = when the live portal data was pulled
- If data is >48 hours old at report delivery: flag in header — "Note: Portal data as of [timestamp]. Recommend re-scrape before client send."

---

## 11. VERSIONING & AMENDMENT PROTOCOL

This SO is owned by Sterling (A7). Amendments require:
1. Commander approval
2. Version increment (v1.0 → v1.1 for editorial/clarification; v1.x → v2.0 for structural changes)
3. Entry in Revision History below
4. Notification to Hale for distribution to Wing staff

New cruise lines or product categories may require line-specific addenda (e.g., "SO-TripValidation_Viking_Addendum.md"). Addenda supplement — they do not override — this SO.

---

## 12. REVISION HISTORY

| Version | Date | Author | Change |
|---|---|---|---|
| 1.0 | 2026-06-03 | Sterling (A7) — drafted by Hale on Commander tasking | Initial canonical format; derived from Furlow/Ely-Darrow Regent validation |
| 1.1 | 2026-06-03 | Sterling (A7) | Section C process additions: §3b Group Booking Ripple Map inserted between §3 and §5; Dossier Freshness Gate added to §3.1 Source Hierarchy; Insurance Status Gate added to §5.3; per-client seat rule added to §2. All internal § cross-references updated (§12→§13, §13→§14). Section count corrected to 14. |
