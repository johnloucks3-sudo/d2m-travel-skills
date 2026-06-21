# LOUCKS-AS-CLIENT LIFECYCLE — EXECUTION PLAN
**Standing Order issued:** 2026-06-18 by Commander  
**Status:** READY TO EXECUTE — read this at next session open

---

## THE ORDER

Treat ALL Loucks personal trips as full client trips — lifecycle, validation, TP chain.  
- WF-17 gate WAIVED for Loucks-as-client  
- Send directly to johnloucks3@gmail.com  
- Label every product: **"Lifecycle Product, No COMMANDER REVIEW REQUIRED"**  
- Full creative chain applies (Reyes → Luna → Naia → Dani → TALON/JET)  
- Purpose: live test of the full D2M system  
- Susan Loucks: NOT a co-client. Products go to John only.

---

## SCOPE — 3 TRIPS

### 1. Door County, WI — Sep 6–14, 2026
- **Dossier:** `dossiers/DOSSIER_DoorCounty_SisterBay_Sep2026.md` ✅ EXISTS, 35% complete
- **Property:** Country House Resort, conf #95833, 7 nights King Waterview
- **Air:** DEN→GRB Sep 6 + GRB→DEN Sep 14 — NOT BOOKED (Commander books)
- **GRB hotel:** Sep 6 (1 night) — NOT BOOKED (Commander books)
- **Rental car:** GRB Sep 6–14 — NOT BOOKED (Commander books)
- **Lifecycle:** 14 TPs defined in dossier (GP through TP 5.4)
- **Immediate actions:**
  - TP 0.5: Welcome + GP form v2 → SEND NOW
  - TP 1.2: Airfare watch email (DEN↔GRB) → SEND NOW
  - TP 1.3: GRB hotel options → SEND NOW
  - TP 2.3: Dining reservations (Fish Boil + CHOP) → SEND NOW (these fill fast)

### 2. Regent Grandeur — Dec 29, 2026 – Jan 14, 2027
- **Dossier:** `dossiers/Loucks_Regent_Grandeur_3122006.md`
- **Booking:** 3122006, Panama Canal, MIA→LAX (or LAX→MIA — verify)
- **Treatment:** Start as if booked TODAY. TP-0 goes out today.
- **FPD:** ~$24,798 due Aug 1 — Commander will pay end of July. DO NOT NAG. Log in dossier as planned_payment: "end of July 2026." No ERROR flags on this until Aug 1.
- **TP calendar:** Build from today (T-194 days as of 2026-06-18):
  - TP-0 (Booking Conf): TODAY → send
  - TP-0.5 (Welcome): This week → send
  - TP-1 (Insurance): T-180 → ~Jul 2 → queue
  - TP-2 (Specialty Dining): T-90 → ~Oct 1 → queue
  - TP-3 (Shore Excursions): T-90 → ~Oct 1 → queue
  - TP-5 (Pre-Departure Checklist): T-30 → ~Nov 29 → queue
  - TP-6 (Final Details): T-14 → ~Dec 15 → queue
  - TP-7 (Send-Off): T-1 → ~Dec 28 → queue

### 3. Silver Nova — May 5–29, 2027
- **Dossier:** `dossiers/DOSSIER_Loucks_SilverNova_May2027.md` ✅ EXISTS, 85%+ complete
- **Booking:** 506101-26, Mediterranean B2B2B, cabin 8071 Superior Veranda
- **Embark:** Venice (Fusina) May 5, 2027 | **Disembark:** Athens (Piraeus) May 29
- **FPD:** $25,837.50 due **Dec 6, 2026** — 60-day alert Oct 7, 30-day alert Nov 6
- **Deposit paid:** $8,612.50 ✅
- **Commission:** $5,517.18 / D2M share $4,413.74
- **Pre-cruise:** Sina Palazzo Sant'Angelo, Venice, May 2–5 (Conf TZ201ZG53502) ✅ BOOKED
- **Old WF-17 exception in YAML** (`dani_authorized_with_24hr_preview`) — SUPERSEDED by 2026-06-18 SO. Update dossier YAML: `wf17_exception: loucks_client_full_waiver_20260618`
- **Treatment:** Treat as onboarded client ~T-350 days out
- **TP-0 and TP-0.5:** Queue for this week
- **Key open items:** Flights not booked (DEN→VCE May 1, ATH→DEN May 29), fare watches active, Medallion Suite waitlisted, guest registration needed

---

## TEMPLATE CONVENTION

All TP draft templates for Loucks-as-client:
- **Local:** `drafts/lifecycle/loucks/tp_{n}_{slug}_template.html`
  - e.g., `tp_0_booking_conf_grandeur_template.html`
  - e.g., `tp_0.5_welcome_grandeur_template.html`
  - e.g., `tp_0.5_welcome_door_county_template.html`
- **Drive:** Upload to `D2M Lifecycle Templates / Loucks /` folder → get share links
- **Monday AM brief:** Add "THIS WEEK'S TP TEMPLATES" section listing each TP going out with Drive link + local path

---

## MONDAY AM BRIEF — NEW SECTION

Add to `agents/thunderbird_eod_brief.py` (or the Monday brief script):
```
## THIS WEEK'S TP TEMPLATES (Loucks Lifecycle)
| Trip | TP | Goes Out | Template |
|------|----|----------|----------|
| Grandeur Dec 29 | TP 1 — Insurance | Jul 2 | [Drive link] · drafts/lifecycle/loucks/tp_1_insurance_grandeur.html |
```
Commander edits templates before send. Expect heavy edits — templates are months-old base versions.

---

## IMPLEMENTATION CHECKLIST

- [ ] 1. Read `dossiers/Loucks_Regent_Grandeur_3122006.md` — get current state
- [ ] 2. Read `dossiers/DOSSIER_Loucks_SilverNova_May2027.md` — get current state
- [ ] 3. Create `drafts/lifecycle/loucks/` directory
- [ ] 4. Draft TP-0 (Grandeur booking confirmation) — send today to johnloucks3
- [ ] 5. Draft TP-0.5 (Grandeur welcome) — queue this week
- [ ] 6. Draft TP-0.5 (Silver Nova welcome) — queue this week
- [ ] 7. Draft TP-0.5 + TP 1.2 + TP 1.3 + TP 2.3 (Door County) — queue this week
- [ ] 8. Build full TP calendars for all 3 trips (dates, owners, statuses)
- [ ] 9. Wire Monday brief template section
- [ ] 10. Update dossiers with lifecycle_test: true and loucks_client_mode: true
- [ ] 11. Add FPD treatment to Grandeur dossier (planned_payment: end of July, no nag)
- [ ] 12. Commit all

---

## NOTES

- Commander expects heavy edits on tone — don't over-polish, send the template
- Do NOT apply WF-17 to any Loucks-as-client correspondence
- The label is exact: "Lifecycle Product, No COMMANDER REVIEW REQUIRED"
- This IS the real test — run the full chain as if Commander were Kyle Kuklinski
- Door County first TP is urgent: dining reservations fill fast (Fish Boil + CHOP)

---

## COMMANDER ACTION ITEMS — GRANDEUR OBC VERIFICATION (Due Jul 5, 2026)

| # | Task | Deadline | Owner | Notes |
|---|------|----------|-------|-------|
| OBC-1 | **Validate AMEX $300 OBC on Grandeur Dec 29** | Jul 5 | Commander | Confirm Amex benefit applies to booking 3122006. AMEX Plat/Centurion OBC on Regent — verify enrollment + dollar amount is exactly $300. If not confirmed, flag to Harlan. |
| OBC-2 | **NCL stock cert — get it sent in** | Jul 5 | Commander | Submit NCLH stockholder benefit for Grandeur booking 3122006. Typically $250 OBC on Regent bookings. Submit to Regent guest services with brokerage account statement showing NCLH shares. Not combinable with all promos — verify. |
| OBC-3 | **Nail down Onboard Booking OBC amount** | Jul 5 | Commander | Verify/confirm the OBC amount from any prior onboard future-cruise deposit on Grandeur booking. Get the exact dollar figure locked before FPD context. |

**Surface these in the next session morning brief — Commander-action items, not Wing-executable.**

*Written by Hale 2026-06-18 before Commander /clear. Execute at next session open.*
