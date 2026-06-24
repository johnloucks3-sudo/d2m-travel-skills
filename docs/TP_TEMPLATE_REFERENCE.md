# D2M LIFECYCLE TOUCHPOINT REFERENCE — COMMANDER REVIEW
**MISSION-435 Deliverable · Built 2026-06-24 · Pending Commander Approval**

---

## STANDING AUTHORITY REQUEST

Once Commander approves this document, the Wing has standing authority to:
1. Produce any TP listed below, for any active client, without per-TP Commander approval
2. Stage the completed email as a draft in johnloucks3 (labeled THUNDERBIRD-Commander-Review)
3. Notify Commander once staged — Commander executes the send

WF-17 gate applies to all client sends. Commander send authority is not delegated.

---

## TEMPLATE STATUS

| TP | Phase | HTML Template | Status |
|----|-------|---------------|--------|
| 0.5 | Onboarding | tp_0_5_welcome_validation.html | ✅ Built |
| 0.6 | Onboarding | tp_0_6_insurance_advisory.html | ✅ Built |
| 1.1 | Discovery | tp_1_1_voyage_preview.html | ✅ Built |
| 1.2 | Discovery | tp_1_2_airfare_watch.html | ✅ Built |
| 1.3 | Discovery | *(no HTML template — research deliverable, not standard email)* | 📋 Prose |
| 2.1 | Momentum | tp_2_1_excursion_planning.html | ✅ Built |
| 2.2 | Momentum | tp_2_2_monthly_validation.html | ✅ Built |
| 2.3 | Momentum | *(Culinary Arts Kitchen — cruise-line specific, Regent only)* | 📋 Conditional |
| 2.4 | Momentum | tp_2_3_dining_reservations.html | ✅ Built |
| 2.5 | Momentum | tp_2_4_document_audit.html | ✅ Built |
| 3.1 | Pre-Departure | tp_3_1_pre_voyage_brief.html | ✅ Built |
| 3.2 | Pre-Departure | tp_3_2_final_confirmation.html | ✅ Built |
| 3.3 | Pre-Departure | tp_3_3_bon_voyage.html | ✅ Built |
| 4.1 | Payment | tp_4_1_payment_reminder_fpd21.html | ✅ Built |
| 4.2 | Payment | *(FPD-14 reminder — variant of 4.1)* | 📋 Variant |
| 4.3 | Payment | *(FPD-7 final goal — variant)* | 📋 Variant |
| 4.4 | Payment | tp_4_4_final_payment_due.html | ✅ Built |
| 4.5 | Payment | tp_4_5_payment_confirmation.html | ✅ Built |
| 4.6 | Payment | *(FCC/Credits — conditional only)* | 📋 Conditional |
| 5.1 | Post-Voyage | tp_5_1_welcome_home.html | ✅ Built |
| 5.2 | Post-Voyage | tp_5_2_feedback_next_voyage.html | ✅ Built |
| 5.3 | Post-Voyage | *(Thank You + Referral)* | 📋 Pending |
| 5.4 | Post-Voyage | *(Next Voyage Plant)* | 📋 Pending |
| ARC-1 | Discretionary | arc1_airfare_hotel.html | ✅ Built |
| ARC-2 | Discretionary | arc2_excursion_arc.html | ✅ Built |
| ARC-3 | Discretionary | arc3_transfers.html | ✅ Built |
| ARC-4 | Discretionary | arc4_specialty_dining.html | ✅ Built |

All templates: `/home/john/Thunderbird/storage/tp_templates/`

---

## TOUCHPOINT DETAILS

### TP 0.5 — Welcome / Booking Validation
- **Trigger:** Within 7 days of booking confirmation
- **Trigger condition:** `completed_tps` does not include "0.5"
- **Purpose:** Confirm booking details, introduce D2M, set expectations, collect guest registration, note FPD
- **Staff:** Dani (voice) + Hale (routing)
- **Variables:** CLIENT_FULLNAMES, SHIP_NAME, CRUISE_LINE, DEPARTURE_DATE, BOOKING_REF, FPD_DATE, FPD_AMOUNT, SUITE_INFO
- **WF-17:** Commander send to client

### TP 0.6 — Insurance Advisory
- **Trigger:** 7-14 days after booking
- **Trigger condition:** `completed_tps` does not include "0.6"
- **Purpose:** Pre-existing condition window warning, quote 3 insurance options
- **Staff:** A9 Harlan (financial verification) + Hale (routing)
- **Critical rule:** Include Squaremouth quote ID and 60-day pre-existing window calculation
- **Variables:** CLIENT_FULLNAMES, DEPARTURE_DATE, INSURANCE_DEADLINE, QUOTE_ID, PLAN_OPTIONS

### TP 1.1 — Voyage Preview (Destination Guide)
- **Trigger:** E-240 to E-210 (7-8 months before departure)
- **Trigger condition:** `completed_tps` does not include "1.1" AND departure >= 180 days out
- **Purpose:** Port-by-port narrative, ship highlights, dining overview, portal opening dates
- **Staff:** A2 Dembe (research) + A6 Luna (narrative) + Dani (voice) + Hale (routing)
- **Variables:** CLIENT_FIRSTNAME, CLIENT_FULLNAMES, VOYAGE_NAME, CRUISE_LINE, SHIP_NAME, DEPARTURE_DATE, BOOKING_REF, DAYS_UNTIL, EMBARK_PORT, ITINERARY_NARRATIVE, PORT_LIST, SHIP_HIGHLIGHTS, DINING_OPTIONS, PORTAL_OPENING_DATES

### TP 1.2 — Airfare Watch
- **Trigger:** E-210 to E-180 (6-7 months before departure)
- **Trigger condition:** `completed_tps` does not include "1.2" AND flights not booked
- **Purpose:** Routing options, fare ranges, booking window recommendation
- **Staff:** A2 Dembe (routing research) + A5 Viper (booking strategy) + Dani (voice)
- **Variables:** CLIENT_FIRSTNAME, CLIENT_FULLNAMES, VOYAGE_NAME, CRUISE_LINE, SHIP_NAME, DEPARTURE_DATE, BOOKING_REF, ORIGIN_CITY, EMBARK_PORT, DISEMBARK_PORT, PAX_COUNT, ROUTING_OPTIONS, FARE_RANGES, BOOKING_WINDOW_OPEN, GROUP_DESK_OPTION

### TP 1.3 — Hotel Options (Pre/Post-Cruise)
- **Trigger:** E-210 to E-180 (concurrent with 1.2)
- **Trigger condition:** Hotel not booked AND hotel relevant (international embark/disembark)
- **Purpose:** 3 hotel options each for pre-cruise and post-cruise nights
- **Staff:** A2 Dembe (research)
- **Format:** Research deliverable with hotel names, links, rates, reviews (not standard HTML template)

### TP 2.1 — Excursion Research & Recommendations
- **Trigger:** E-180 to portal opening date
- **Trigger condition:** `completed_tps` does not include "2.1" AND excursion portal not yet open
- **Purpose:** Port-by-port excursion recommendations before client can book independently
- **Staff:** A2 Dembe (research) + Excursion-Analysis skill
- **Critical rule:** Must complete BEFORE excursion portal opens so client has recommendations ready
- **Note:** This is a high-value TP — use the `/excursion-analysis` skill for full research

### TP 2.2 — Monthly Validation (Rolling)
- **Trigger:** 1st of each month from T-180 to departure month
- **Trigger condition:** Ongoing — fires monthly
- **Purpose:** Status check against validation matrix, flag open items, update dossier
- **Staff:** Hale
- **Variables:** CLIENT_FULLNAMES, VOYAGE_NAME, DEPARTURE_DATE, VALIDATION_MATRIX, OPEN_ITEMS

### TP 2.4 — Dining Reservations
- **Trigger:** E-90 to specialty dining portal opening
- **Trigger condition:** `completed_tps` does not include "2.4" AND dining portal not yet open
- **Purpose:** Specialty dining research, booking recommendations, opening day strategy
- **Staff:** A2 Dembe (research) + A6 Luna (dining narrative)

### TP 2.5 — Document Audit
- **Trigger:** E-90 to E-75
- **Trigger condition:** `completed_tps` does not include "2.5"
- **Purpose:** Passport validity check (6mo past return), visa requirements, guest registration, emergency contacts
- **Staff:** Hale

### TP 3.1 — Pre-Voyage Brief
- **Trigger:** E-28 to E-21
- **Trigger condition:** `completed_tps` does not include "3.1"
- **Purpose:** Comprehensive trip packet — all logistics, weather, packing, check-in details
- **Staff:** Hale + A2 Dembe + A6 Luna (comprehensive)

### TP 3.2 — Final Confirmation
- **Trigger:** E-14 to E-7
- **Trigger condition:** `completed_tps` does not include "3.2"
- **Purpose:** All logistics locked, print-ready confirmations, transfer confirmation
- **Staff:** Hale

### TP 3.3 — Send-Off / Bon Voyage
- **Trigger:** E-5 to E-3
- **Trigger condition:** `completed_tps` does not include "3.3"
- **Purpose:** Warm send-off, final weather, last-minute tips, emergency contacts
- **Staff:** Hale + A6 Luna

### TP 4.1 — Payment Reminder #1 (FPD-21)
- **Trigger:** 21 days before Final Payment Due date
- **Trigger condition:** FPD is future AND `completed_tps` does not include "4.1"
- **Purpose:** Balance amount, payment options, FPD countdown
- **Staff:** Hale + A9 Harlan (financial verification)
- **Hard rule:** Dollar amounts must be Harlan-verified before send (SO-PIPELINE-INTEGRITY Rule 5)

### TP 4.4 — Final Payment Due (FPD day)
- **Trigger:** FPD date
- **Trigger condition:** FPD today AND payment not confirmed
- **Purpose:** CRITICAL — cancellation risk notification, payment link
- **Staff:** A9 Harlan + Hale

### TP 4.5 — Payment Confirmation
- **Trigger:** FPD+7
- **Trigger condition:** Payment received AND `completed_tps` does not include "4.5"
- **Purpose:** Confirm payment posted, update dossier, celebrate
- **Staff:** A9 Harlan

### TP 5.1 — Welcome Home
- **Trigger:** D+7 (7 days after return)
- **Trigger condition:** Voyage complete AND `completed_tps` does not include "5.1"
- **Purpose:** Debrief, highlights request, share memories
- **Staff:** Hale + Dani

### TP 5.2 — Survey / Feedback Request
- **Trigger:** D+14
- **Trigger condition:** `completed_tps` does not include "5.2"
- **Purpose:** Structured feedback, TripAdvisor/Google ask
- **Staff:** A7 Gauge + Dani

---

## PRODUCTION RULES (binding on all Wing agents producing TPs)

1. **Template variables:** Zero `{{PLACEHOLDER}}` tokens may remain in final HTML
2. **Harlan sign-off:** Any TP mentioning dollar amounts requires Harlan verification before WF-17
3. **Primary sources:** All financial figures sourced from portal, TESS, or dossier — never from memory
4. **Draft routing:** All client TPs staged in johnloucks3 Gmail, labeled THUNDERBIRD-Commander-Review (Label_115)
5. **Dossier update:** After staging, update `draft_pending_tps` field in client dossier
6. **Lifecycle queue:** Append entry to `/home/john/Thunderbird/storage/lifecycle_draft_queue.jsonl`
7. **Contact holds:** Honor any `contact_hold_until` field in dossier — draft the email, but note the hold
8. **WF-17 exception:** Loucks-as-client TPs (booking 3122006, SilverNova 2027, Door County Sep 2026) — send directly to johnloucks3@gmail.com

---

## VOICE STANDARDS (John's voice — binding)

From sent email analysis (Spencer, Kuklinski gold standard 2026-06-20):
- Open with client name and em-dash: `Kyle and Rosalie —`
- Active, direct sentences. No throat-clearing.
- Warm but not effusive. Authoritative but not cold.
- Specifics over generalities: name the port, the ship, the date
- No melodrama. No "I'm thrilled to share..."
- Close with "Thanks," or "John" — never "Best,"
- Dani's section is clearly labeled, uses her professional voice (Luxury AI Travel Concierge)
- Commander sig block appears last (storage/signatures/commander_d2m_sig.html)

---

*Template directory: `/home/john/Thunderbird/storage/tp_templates/`*
*Canonical lifecycle: `/home/john/.claude/projects/-home-john-Thunderbird/memory/reference_canonical_lifecycle_touchpoints.md`*
*Created: 2026-06-24 · MISSION-435 · Thunderbird Wing*
