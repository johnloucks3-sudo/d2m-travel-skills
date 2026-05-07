# RECORDS MAINTENANCE — BEST PRACTICES SOP
**Thunderbird Wing, Dreams2Memories Travel, LLC**

*Canonical Reference | Version 1.0 | Updated 2026-05-07*

---

## EXECUTIVE SUMMARY

Records maintenance is the backbone of operational continuity. A properly maintained dossier eliminates surprises, enables proactive decision-making, and serves as the single source of truth for any booking at any stage. This SOP formalizes the procedures for dossier creation, update cadence, FPD tracking, and data quality standards.

**Primary tools:**
- `~/Thunderbird/dossiers/` — master dossier storage (markdown files)
- `core/booking/thunderbird_dossier_scanner.py` — automated gap detection
- Booking Master Google Sheet — central reference for all active bookings
- `THUNDERBIRD_MASTER_PLAN.md` Part 5 — canonical trip definitions
- Google Drive `D2M Trip Dossiers/` (ID: `1QbbW4hapyfgG6c6Iv94OxtjhySuf2zou`) — read-only mirror

---

## 1. DOSSIER LIFECYCLE

### 1.1 Dossier Types & Naming

Three types of dossiers exist. Each has a distinct naming convention and purpose.

| Type | Naming Pattern | Example | Purpose |
|------|---|---|---|
| **Individual** | `{LastName}_{FirstName}_{Ship}_{Type}.md` | `Furlow_John_GrandeurScandinavia.md` | Single client/couple on a specific cruise |
| **Master Trip** | `DOSSIER_{Ship}_{Region}_{MonthYear}.md` | `DOSSIER_Grandeur_Scandinavia_Aug2026.md` | All clients on same cruise; shared itinerary, excursions, dining |
| **Supplemental** | `{LastName}_{Topic}.md` | `McLeod_InsuranceGap.md` | One-off issue: insurance, visa, accessibility need |

**Location:** All dossiers live in `~/Thunderbird/dossiers/`.

### 1.2 Dossier Creation Triggers

A new individual dossier is created when:
1. A new client inquiry arrives and advances to "likely to book" status (TP0.5 or higher)
2. A client confirms a booking (initial confirmation from cruise line received)
3. A client requires a supplemental document (insurance gap, visa issue, medical accommodation)

A new master trip dossier is created when:
- Two or more clients book the **same cruise, same sailing** (shared itinerary, coordinated excursions/dining)
- Trip-level information (itinerary changes, general notes, shared logistics) applies to multiple clients

### 1.3 Required Fields by Phase

Every dossier must contain these fields. Mark unknowns as `NEEDED` or `TBD` — never fabricate.

#### TP0.5 (Initial Inquiry) — Minimum Fields
```markdown
CLIENT_NAMES: [full legal names as on passport]
CONTACT_EMAIL: [email address]
CONTACT_PHONE: [phone number]
INQUIRY_DATE: [YYYY-MM-DD]
INITIAL_INTEREST: [destination, ship preference, travel window, rough budget]
STATUS: TP0.5 — Initial Inquiry
```

#### TP1 (Validation Sent) — Add to Above
```markdown
SHIP: [vessel name and cruise line]
DEPARTURE_DATE: [YYYY-MM-DD]
RETURN_DATE: [YYYY-MM-DD]
CABIN_PREFERENCE: [category/location if expressed]
AIR_TRAVEL: [origin/destination airports, cabin class preference]
VALIDATION_EMAIL_SENT: [YYYY-MM-DD]
INSURANCE_REQUIRED: [yes/no, policy notes if yes]
STATUS: TP1 — Validation Sent
```

#### TP2 (Booked) — Add to Above
```markdown
BOOKING_CONFIRMATION_NUMBER: [cruise line confirmation code]
CABIN_ASSIGNMENT: [deck + room number + category]
FINAL_PAYMENT_DATE: [YYYY-MM-DD, from cruise line confirmation ONLY]
PAYMENT_STATUS: [paid-in-full, balance-due with amount]
AMOUNT_PAID: [USD, formatted via fmt_usd()]
AMOUNT_DUE: [USD or $0.00 if paid in full]
AIR_PNR: [if booked: airline code + confirmation number]
AIR_SEATS: [seat assignments, cabin class]
TRANSFERS: [airport-to-port, port-to-hotel, all ground transport details]
EMERGENCY_CONTACTS: [at least one per traveler with relationship]
DIETARY_MEDICAL: [allergies, restrictions, medications — mark CONFIDENTIAL if sensitive]
GUEST_FORM_STATUS: [not-sent / sent-pending / completed]
STATUS: TP2 — Booked
```

#### TP3+ (Post-Booking) — Add to Above
```markdown
EXCURSIONS_BOOKED: [port-by-port list with dates and costs]
SPECIALTY_DINING: [restaurant names, dates, covers, any dietary notes]
SEAT_NUMBERS: [final seat assignments if changed]
TRAVEL_INSURANCE_POLICY: [insurer name, policy number, coverage limits]
FINAL_ITINERARY_SENT: [YYYY-MM-DD when itinerary PDF delivered to client]
PRE_CRUISE_CHECKLIST: [link to pre-cruise comms / confirmations received]
STATUS: TP3+ — [descriptive phase]
```

### 1.4 Update Cadence Rules

| Phase | Cadence | Trigger |
|-------|---------|---------|
| TP0.5–TP1 | Every touch | Email received, call note added, preference change |
| TP2 (Booked) | Weekly minimum; daily if FPD approaching | Payment received, FPD alert threshold hit, excursions opened |
| TP2.5–TP3 (Final) | Weekly minimum; escalate if FPD < 14 days | Specialty dining opens, shore excursions open, final seat assignments available |
| Post-Voyage | Once post-disembark | Trip complete, invoice reconciliation, feedback collected |

**Never let a dossier be more than 7 days stale.** If a booking has a change, update immediately (within 24 hours).

### 1.5 Archive Criteria

A dossier transitions to **archived** when:
- Voyage has disembarked (departure date has passed + 14 days)
- Final payment is reconciled and confirmed
- Client feedback has been collected (if applicable)
- All financial disputes are resolved

**Archived dossiers:**
- Remain in `~/Thunderbird/dossiers/` with `_ARCHIVED` suffix (e.g., `Westbrook_SilverNova_ARCHIVED.md`)
- Are moved to a `/archived/` subfolder annually (2025, 2026, etc.)
- Retain all original fields but new updates cease
- Are kept for 3 years for IRS/audit purposes, then permanently deleted

---

## 2. FPD (FINAL PAYMENT DATE) TRACKING

### 2.1 Where FPDs Live (Sources of Truth)

**Primary source:** Cruise line confirmation email or online account (e.g., Regent Seven Seas portal, Silversea.com, Viking.com)

**Secondary source:** Individual dossier field `final_payment_date` (must match cruise line)

**Tertiary reference:** Booking Master Google Sheet, column "FPD"

**Final reference:** `THUNDERBIRD_MASTER_PLAN.md` Part 5, trip-level FPD notes

⚠️ **Rule:** Always verify FPD against cruise line confirmation before alerting Commander. Do not rely on dossier alone — cruise lines sometimes move dates.

### 2.2 FPD Alert Cadence

| Days Until FPD | Action | Owner | Channel |
|---|---|---|---|
| **60 days** | Surface in morning briefing (informational) | COS | Hale brief |
| **45 days** | Escalate to Telegram + email memo | COS | Telegram + d2mconcierge draft |
| **30 days** | RED status, daily reminder to COS | COS | Hale brief + slab |
| **14 days** | CRITICAL — daily Telegram page if unpaid | COS | Telegram C2 only |
| **7 days** | URGENT — call client if not received | COS/Dani | Phone call + follow-up email |
| **0 days (FPD date)** | Confirm payment received same day; if not, escalate to Commander | COS/A9 | Telegram to Commander |

### 2.3 Escalation Rules

**When to escalate to Commander:**
1. Payment not received by FPD date (within 24 hours of FPD, if not in account)
2. Payment received but amount is incorrect (mismatch with invoice)
3. Client requests FPD extension (must be approved by Commander)
4. Payment flagged by financial processor (fraud alert, account issue, etc.)

**Escalation format (Telegram C2):**
```
🦅 FPD ALERT: [Client Name] | [Ship] | FPD: [date]
Amount due: [USD]
Status: [UNPAID / PARTIAL / FLAGGED]
Action: [Awaiting payment / Payment mismatch / Client requesting extension]
Recommend: [Proceed/Hold/Call client]
```

### 2.4 What to Do When Payment Posts

**Immediately upon receipt:**
1. Update dossier field `final_payment_date_received: [YYYY-MM-DD]`
2. Update dossier field `payment_status: paid-in-full` (or note partial if applicable)
3. Confirm amount matches invoice in dossier
4. Update Booking Master Sheet, column "Payment Status" → `PAID`
5. Update THUNDERBIRD_MASTER_PLAN.md if trip-level notation exists
6. Mirror to Google Drive `D2M Trip Dossiers/` folder
7. Log to A9 Finance queue for commission tracking

**Remove from alert rotation:** Payment is considered confirmed when:
- Bank deposit appears in d2mconcierge bank account AND
- Amount matches invoice in dossier

Do not rely on client email alone — wait for bank confirmation.

---

## 3. FOUR-STEP AUTO-DOSSIER PROTOCOL

The moment **any booking changes** (new booking, payment received, excursions booked, FPD updated, seat assignment changed), execute all four steps within **24 hours**.

### Step 1: Update Individual Dossier in ~/Thunderbird/dossiers/

**File:** `~/Thunderbird/dossiers/{LastName}_{FirstName}_{Ship}.md`

**What to update:**
- Any field that changed (payment status, seat assignment, excursion addition, FPD clarification, etc.)
- Add a **change log entry** at the top of the file:
  ```markdown
  ## CHANGE LOG
  - 2026-05-06: Payment received ($15,486). Status → TP2_Paid.
  - 2026-05-05: Excursions booked (3 ports, total $1,250).
  ```
- Verify all required fields for current phase are present (no `TBD` left blank unless unavoidable)
- Use ISO date format (YYYY-MM-DD) throughout
- Format USD amounts via `fmt_usd()` function (e.g., `$15,486.00` not `15486`)

**Verification:**
```bash
# Ensure file is readable and has no syntax errors
cat ~/Thunderbird/dossiers/{LastName}_{FirstName}_{Ship}.md
```

### Step 2: Update Booking Master Google Sheet

**Sheet:** [Booking Master Google Sheet] (location: Drive root, shared with wing)

**Columns to update:**
| Column | Value | Example |
|--------|-------|---------|
| Client Name | Full legal names | Furlow, John / Furlow, Missy |
| Ship | Vessel + Line | Grandeur (Regent Seven Seas) |
| Sailing Date | YYYY-MM-DD | 2026-08-29 |
| FPD | YYYY-MM-DD | 2026-05-29 |
| Payment Status | PAID / BALANCE DUE / PARTIAL | PAID |
| Amount Paid | USD (formatted) | $15,486.00 |
| Amount Due | USD or $0.00 | $0.00 |
| Excursions | BOOKED / PENDING / NONE | BOOKED |
| Specialty Dining | BOOKED / PENDING / NONE | PENDING |
| TP Status | TP2 / TP3 / TP4 / TP5 / ARCHIVED | TP2_Paid |
| Last Updated | YYYY-MM-DD | 2026-05-06 |
| Dossier Link | Link to dossier file | [Link to markdown] |

**Verification:**
- Open sheet, find client row, verify all columns match current dossier state
- Check that "Last Updated" date is today or yesterday (not stale)
- Verify no red flags in conditional formatting (missing FPD, overdue payment, etc.)

### Step 3: Update THUNDERBIRD_MASTER_PLAN.md Part 5

**File:** `~/Thunderbird/THUNDERBIRD_MASTER_PLAN.md`

**Location:** Scroll to **Part 5: ACTIVE BOOKINGS** section

**What to update:**
If booking is on a **master trip** (multiple clients on same cruise), update the trip record:

```markdown
### Grandeur — Storied Scandinavia (Aug 29 – Sep 8, 2026)
**FPD:** 2026-05-29
**Clients:** Furlow (PAID) | Ely (PAID) | Nichols (BALANCE DUE $2,100)
**Excursions:** Furlow + Ely booked (3 ports). Nichols pending.
**Specialty Dining:** All 3 awaiting May 31 opening.
**Changes:** Itinerary adjusted Jan 23 (Copenhagen overnight moved, sea day → Kristiansand).
**Last Updated:** 2026-05-06
```

If booking is **not on a master trip** (standalone), create individual entry:

```markdown
### Silver Muse — Rome to Venice (Jun 23 – Jul 3, 2026)
**Client:** McLeod, Erik / McLeod, Julie
**FPD:** 2026-03-23 (PAID)
**Status:** TP3 — Specialty dining booked (Feb 23). Shore excursions pending (Jan 31 opening). Post-cruise hotel in selection phase.
**Last Updated:** 2026-05-06
```

**Verification:**
- Master plan is no more than 7 days stale (check "Last Updated" dates)
- Client names match dossier names exactly
- Payment status matches Booking Master sheet
- FPD dates match dossier `final_payment_date` field

### Step 4: Mirror to Google Drive — D2M Trip Dossiers Folder

**Destination Folder:** `D2M Trip Dossiers` (Drive ID: `1QbbW4hapyfgG6c6Iv94OxtjhySuf2zou`)

**Process:**
1. Export individual dossier markdown as PDF or Google Doc
   - Use script: `core/booking/thunderbird_dossier.py` → `export_to_drive()` function
   - Or manually: copy markdown → paste to Google Doc → share with wing (`johnloucks3@gmail.com`, `jbzsolutionsllc@gmail.com`)

2. Organize in Drive by trip or client:
   - Folder: `/D2M Trip Dossiers/Grandeur_Scandinavia_Aug2026/`
   - File: `Furlow_John_Dossier.pdf` (updated version)

3. Verify Drive file has correct sharing:
   - Shared with: `johnloucks3@gmail.com`, `jbzsolutionsllc@gmail.com`
   - Permission: Viewer (read-only)

**Verification:**
```bash
# Check that Drive copy exists and is recent
# Use MCP: files_list(query="Furlow", folder_id="1QbbW4hapyfgG6c6Iv94OxtjhySuf2zou")
# Expected: File updated within 1 day of local dossier change
```

### Verification Checklist — All Four Steps

- [ ] Dossier file updated locally (~/Thunderbird/dossiers/)
- [ ] Change log entry added to dossier
- [ ] All USD amounts formatted via `fmt_usd()`
- [ ] All dates in ISO format (YYYY-MM-DD)
- [ ] Booking Master Sheet row updated
- [ ] Last Updated date in sheet is today
- [ ] THUNDERBIRD_MASTER_PLAN.md Part 5 updated
- [ ] Drive `D2M Trip Dossiers/` folder mirrored
- [ ] Drive file shared with correct users (read-only)

---

## 4. DATA QUALITY STANDARDS

### 4.1 Required vs Optional Fields Per Phase

| Field | TP0.5 | TP1 | TP2 | TP3+ | Retention |
|-------|-------|-----|-----|------|-----------|
| Client Names | ✅ Required | ✅ | ✅ | ✅ | Permanent |
| Ship | ❌ | ✅ Required | ✅ | ✅ | Permanent |
| Booking Conf# | ❌ | ❌ | ✅ Required | ✅ | Permanent |
| FPD | ❌ | ⚠️ Estimate | ✅ Required | ✅ | 3 years post-disembark |
| Cabin Assignment | ❌ | ⚠️ Preference | ✅ Required | ✅ | 3 years post-disembark |
| Air PNR | ❌ | ⚠️ Preference | ✅ Required (if air needed) | ✅ | Permanent |
| Emergency Contacts | ❌ | ❌ | ✅ Required | ✅ | Permanent |
| Dietary/Medical | ❌ | ❌ | ✅ Required | ✅ | Permanent, mark CONFIDENTIAL |
| Excursions | ❌ | ❌ | ❌ | ⚠️ Booked or NONE | 1 year post-disembark |
| Specialty Dining | ❌ | ❌ | ❌ | ⚠️ Booked or NONE | 1 year post-disembark |

**Legend:**
- ✅ Required: Must be present, not TBD
- ⚠️ Preference/Estimate: Fill if known, mark TBD if not
- ❌ Not applicable at this phase

### 4.2 Fabrication Rule

**NEVER fabricate data.** If a required field is unknown:
- Mark as `TBD` (To Be Determined)
- Mark as `NEEDED` (awaiting client input)
- Add a **follow-up reminder** in the dossier:
  ```markdown
  ## FOLLOW-UP NEEDED
  - [ ] Confirm dietary restrictions (Missy has gluten allergy — verify severity, cross-contamination risk)
  - [ ] Obtain emergency contact for Justin (waiting for confirmation email)
  ```

Do not guess cabin numbers, prices, or dates. Let the absence show so COS or A-staff can follow up.

### 4.3 Price Formatting

**Rule:** All USD amounts must be formatted via `fmt_usd()` function.

**Examples:**
```markdown
AMOUNT_PAID: $15,486.00         ✅ Correct
AMOUNT_PAID: $15486             ❌ Wrong (no comma/decimals)
AMOUNT_PAID: 15486              ❌ Wrong (no $)
AMOUNT_PAID: USD 15,486.00      ❌ Wrong (redundant)
```

If integrating with Python, use:
```python
from thunderbird_utils import fmt_usd
amount = fmt_usd(15486.00)  # Returns "$15,486.00"
```

### 4.4 Date Format Rule

**Rule:** All dates YYYY-MM-DD with timezone if relevant.

**Examples:**
```markdown
DEPARTURE_DATE: 2026-08-29          ✅ Correct
DEPARTURE_TIME: 04:30 PM (local)    ✅ Correct
FINAL_PAYMENT_DATE: 05/29/2026      ❌ Wrong (MM/DD/YYYY format)
FPD: May 29                          ❌ Wrong (no year, ambiguous)
```

### 4.5 Gap Detection — Using thunderbird_dossier_scanner.py

The dossier scanner runs **daily at 6:45 AM** and detects:
- FPDs within 14 days with payment not confirmed
- Unassigned seats on confirmed flights
- Missing passport verification status
- Validation touchpoints overdue (>45 days since TP1 sent)
- Insurance gaps (coverage not confirmed)
- Portal upload status not confirmed

**Manual scan (on demand):**
```bash
cd ~/Thunderbird
python3 core/booking/thunderbird_dossier_scanner.py
```

**Output example:**
```
[WARNING] Furlow — FPD APPROACHING: Final payment due 2026-05-29 (22 days)
[INFO] McLeod — Missing post-cruise hotel confirmation
[CRITICAL] Kuklinski — Validation email sent 2026-03-15 (>45 days, no booking yet)
```

### 4.6 How to Run a Gap Sweep

**Weekly (Monday morning):**
1. Run scanner: `python3 core/booking/thunderbird_dossier_scanner.py`
2. Review output, group by severity (CRITICAL → WARNING → INFO)
3. Create follow-up tasks in mission board for each gap
4. Assign to A-staff (A2 for research gaps, A3 for logistics, A9 for finance)
5. Track to resolution

**Monthly (end of month):**
1. Run scanner against all dossiers
2. Export report: `thunderbird_dossier_scanner.py --export csv`
3. Send to COS for strategic review (e.g., "validation success rate = 78%")
4. Identify patterns (e.g., clients delaying on port excursions, suggest earlier messaging)

### 4.7 What to Do with Flagged Gaps

| Gap Type | Action | Owner | Timeline |
|----------|--------|-------|----------|
| Missing passport verification | Email client requesting scan/confirmation | Dani | Within 48 hours |
| Missing dietary restrictions | Call client to confirm | Dani | Within 1 day |
| Unassigned flight seats | Check airline, assign or flag for manual selection | A3 | Within 3 days of flight |
| Insurance not confirmed | Follow up with quote/policy options | A9 | Within 5 days |
| FPD approaching unpaid | Alert Commander via Telegram | COS | 14 days before FPD |

**Log all gap resolutions** back to dossier under "FOLLOW-UP NEEDED" section.

---

## 5. RETENTION AND PURGE POLICY

### 5.1 Record States

| State | Definition | Duration | Location |
|-------|-----------|----------|----------|
| **Active** | Voyage not yet departed OR within 14 days post-disembark | From TP0.5 through TP3 + 14 days post-voyage | ~/Thunderbird/dossiers/ |
| **Completed** | Voyage disembarked >14 days ago; final payment received; no outstanding issues | 1 year | ~/Thunderbird/dossiers/ (suffix: `_ARCHIVED`) |
| **Archived** | Completed + 1 year elapsed; moved to annual subfolder | 3 years (IRS/audit) | ~/Thunderbird/dossiers/archived/{YEAR}/ |
| **Purged** | Archived >3 years; legal hold expires | Deleted permanently | N/A |

### 5.2 What Gets Deleted vs Archived

| Item | Action | Rationale |
|------|--------|-----------|
| Individual dossier (TP2 completed, archived) | Archive 3 years, then delete | IRS retention (Reg. 1.461-5) for voyage deduction proof |
| Supplemental dossier (insurance, visa issue) | Archive with parent trip dossier | Context for future bookings |
| Master trip dossier (all clients disembarked) | Archive as group; keep all individual links | Shared itinerary history for repeat clients |
| Booking Master Sheet rows | Keep indefinitely (Google Sheet version history) | Sheet grows, old rows stay, sortable by year |
| THUNDERBIRD_MASTER_PLAN.md entries | Keep indefinitely (git history) | Strategic reference for repeat trips |
| Drive mirror files | Keep indefinitely (Google Drive auto-version) | Shared context for wing members |
| Payment receipts / invoices | Archive 7 years (tax/audit) | Attached to dossier or A9 finance folder |

### 5.3 Archive Procedure

**Trigger:** Voyage disembarked + 14 days elapsed AND final payment confirmed

**Steps:**
1. Rename dossier file: `{LastName}_{FirstName}_{Ship}.md` → `{LastName}_{FirstName}_{Ship}_ARCHIVED.md`
2. Move to subfolder: `~/Thunderbird/dossiers/archived/{YEAR}/`
3. Update Booking Master Sheet: Column "Status" → `ARCHIVED`
4. Update THUNDERBIRD_MASTER_PLAN.md: Move entry to "Archived Bookings" section with completion note
5. Drive mirror: Mark folder `_ARCHIVED` or move to `/Archive/` subfolder
6. Git commit: `git add -A && git commit -m "Archive: [Client] [Ship] [Dates]"`

**Example:**
```bash
# Local
mv ~/Thunderbird/dossiers/Furlow_John_Grandeur.md \
   ~/Thunderbird/dossiers/archived/2026/Furlow_John_Grandeur_ARCHIVED.md

# Google Sheet: Update "Status" column to "ARCHIVED"

# THUNDERBIRD_MASTER_PLAN.md: Move Grandeur entry to "## ARCHIVED TRIPS" section

# Drive: Move or mark archived

# Git
git add -A
git commit -m "Archive: Furlow, Grandeur Scandinavia (Aug 29 – Sep 8, 2026)"
```

### 5.4 Purge Schedule

**Annual purge (every January):**
```bash
# Find archived dossiers >3 years old
find ~/Thunderbird/dossiers/archived/ -name "*.md" -mtime +1095 -type f

# Verify no legal hold (tax/audit) applies
# Then delete
rm ~/Thunderbird/dossiers/archived/{YEAR-3}/*.md
```

**Before deletion:**
1. Verify voyage disembarked >3 years ago
2. Verify final payment received and reconciled
3. Confirm no outstanding disputes or chargebacks
4. Check IRS statute of limitations (7 years for certain deductions)

**When in doubt, keep.** Archiving is cheap; deletion is permanent.

---

## 6. WEEKLY MAINTENANCE CHECKLIST

**Day:** Monday morning, 08:00 MT  
**Owner:** COS (Hale) or delegated A-staff (A3)  
**Time:** ~30 minutes  
**Tool:** This checklist + dossier_scanner.py

### Dossier Freshness
- [ ] Run gap scanner: `python3 core/booking/thunderbird_dossier_scanner.py`
- [ ] Review all dossiers; confirm no file is >7 days stale
- [ ] Check "Last Updated" date in each dossier header

### FPD Monitoring
- [ ] Scan dossier folder for "FINAL_PAYMENT_DATE" fields
- [ ] Identify any FPD ≤60 days away (not yet alerted)
- [ ] Verify against cruise line portal (cruise line is source of truth, not dossier)
- [ ] Add 60-day alert tasks to mission board if applicable
- [ ] Check for any FPD reached in past 7 days; confirm payment received

### Booking Master Sheet
- [ ] Open sheet, sort by "FPD" ascending
- [ ] Verify all TP2+ entries have FPD populated
- [ ] Check "Last Updated" column: all rows ≤7 days old (not counting archived)
- [ ] Identify any rows with "BALANCE DUE" + FPD < 30 days; escalate

### THUNDERBIRD_MASTER_PLAN.md
- [ ] Open Part 5 (ACTIVE BOOKINGS)
- [ ] Verify all trips with disembark date within 14 days are being actively monitored
- [ ] Check "Last Updated" date on each entry: none >7 days stale

### Drive Mirror
- [ ] Sample 3 random dossiers
- [ ] Verify Drive mirror file exists and updated within 1 day of local dossier change
- [ ] Check folder sharing: `johnloucks3@gmail.com` + `jbzsolutionsllc@gmail.com` (Viewer)

### Gap Resolution
- [ ] Review mission board "Dossier Gap" tasks
- [ ] Confirm all CRITICAL gaps from last week are resolved or escalated
- [ ] Create new tasks for this week's gaps (from scanner output)
- [ ] Assign tasks to A-staff (A2 research, A3 logistics, A9 finance, Dani client-facing)

### Archive & Retention
- [ ] Scan for any voyages disembarked >14 days ago (check departure dates)
- [ ] Identify candidates for archiving this month
- [ ] Verify payment reconciliation complete (A9 sign-off)
- [ ] Move to `archived/{YEAR}/` folder if ready

### Git Commit (Weekly Summary)
```bash
cd ~/Thunderbird
git add -A
git commit -m "Weekly dossier maintenance: [X] gap fixes, [Y] FPD alerts, [Z] archives"
```

---

## 7. INTEGRATION WITH AUTOMATED SYSTEMS

### 7.1 Morning Briefing Integration

Daily at 6:45 AM, `thunderbird_morning_briefing.py` runs the dossier scanner and injects findings into the brief:

```markdown
## DOSSIER ALERTS
- 🔴 [CRITICAL] Kuklinski — FPD 2026-05-29 (22 days, payment not confirmed)
- 🟡 [WARNING] McLeod — Post-cruise hotel selection pending (needed by May 20)
- ⚪ [INFO] Westbrook — Excursions now open (May 1), deadline May 24
```

**Action:** COS reviews brief, creates mission board tasks for each alert.

### 7.2 Telegram C2 Integration

Commander can query dossier status via Telegram:

```
/dossier Furlow
→ Returns: FPD, payment status, excursions, specialty dining, last updated
```

**Implementation:** MCP tools integrate dossier scanner output → Telegram gateway → formatted message to Commander.

### 7.3 Booking Master Sheet Webhooks

When Booking Master Sheet is updated (new row, payment status change), n8n workflow triggers:
1. Update dossier file (if row has "Link to Dossier")
2. Update THUNDERBIRD_MASTER_PLAN.md
3. Mirror to Drive
4. Git commit

**Reduces manual steps; keeps records in sync automatically.**

---

## 8. TROUBLESHOOTING & EDGE CASES

### Issue: FPD in Dossier Doesn't Match Cruise Line Portal

**Root Cause:** Cruise line moved FPD (rare but happens)

**Resolution:**
1. Verify with cruise line portal (source of truth)
2. Update dossier `final_payment_date` to match cruise line
3. Update Booking Master Sheet
4. Note discrepancy in dossier change log
5. Alert Commander if FPD moved earlier (may affect payment plan)

### Issue: Client Has No Email; Dossier Field Empty

**Root Cause:** Unusual but possible (older clients, agency bookings)

**Resolution:**
1. Mark field: `CONTACT_EMAIL: PHONE ONLY`
2. Record phone number in `CONTACT_PHONE`
3. Add note: "Client prefers phone communication; use SMS for time-sensitive alerts"
4. Never fabricate email

### Issue: Cabin Assignment Unavailable at TP2

**Root Cause:** Cruise line hasn't assigned cabins yet (normal early in booking window)

**Resolution:**
1. Mark field: `CABIN_ASSIGNMENT: TBD (awaiting cruise line assignment, expected [date])`
2. Set reminder 30 days before departure to check again
3. Once assigned, update dossier immediately

### Issue: Payment Received But Amount Doesn't Match Invoice

**Root Cause:** Client underpaid, overpaid, or submitted partial payment

**Resolution:**
1. Do NOT mark dossier as `paid-in-full` yet
2. Document: `PAYMENT_STATUS: partial ($X received, $Y due)`
3. Escalate to A9 Finance + Commander immediately
4. Create mission board task: "Reconcile payment discrepancy — Client [Name]"
5. Follow up with client for clarification (Dani)

### Issue: Dossier File Corrupted (Bad Markdown Syntax)

**Root Cause:** Manual edit introduced syntax error, or merge conflict

**Resolution:**
1. Check git history: `git log --oneline ~/Thunderbird/dossiers/{file}.md`
2. Revert to last known good version: `git checkout HEAD~1 -- path/to/file.md`
3. Re-apply changes manually
4. Verify syntax: `python3 -m markdown {file}.md` (should not error)
5. Commit: `git commit -m "Fix: Repair dossier syntax error (merge conflict)"`

---

## 9. QUICK REFERENCE — FILE LOCATIONS

| Item | Path | Owner | Update Frequency |
|------|------|-------|------------------|
| Individual dossiers | `~/Thunderbird/dossiers/{LastName}_{FirstName}_{Ship}.md` | COS / A-staff | Within 24 hours of change |
| Master trip dossiers | `~/Thunderbird/dossiers/DOSSIER_{Ship}_{Region}_{MonthYear}.md` | COS | Weekly |
| Archived dossiers | `~/Thunderbird/dossiers/archived/{YEAR}/` | COS | Annual review |
| Booking Master Sheet | Google Drive (shared) | A9 / COS | Daily |
| THUNDERBIRD_MASTER_PLAN.md | `~/Thunderbird/THUNDERBIRD_MASTER_PLAN.md` Part 5 | EXEC / COS | Weekly |
| Gap scanner | `core/booking/thunderbird_dossier_scanner.py` | System (daily 6:45 AM) | Automated |
| Drive mirror folder | Google Drive → D2M Trip Dossiers (ID: 1QbbW4hapyfgG6c6Iv94OxtjhySuf2zou) | COS | Within 24 hours of dossier change |

---

## 10. SIGN-OFF & REVISION HISTORY

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2026-05-07 | Initial SOP: Dossier lifecycle, FPD tracking, 4-step protocol, quality standards, retention, weekly checklist | Hale, COS |

---

**Approved by:** Col Victoria "Iron Vic" Hale, Chief of Staff, Thunderbird Wing

*This SOP is canonical. All dossier work conforms to this standard. Questions or updates: escalate to COS.*
