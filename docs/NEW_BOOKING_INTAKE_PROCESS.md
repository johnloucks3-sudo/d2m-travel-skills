# NEW BOOKING INTAKE PROCESS
## Dreams2Memories Travel, LLC — Thunderbird Wing
*Owner: V. Hale, VCS · Created: 2026-06-20 · Version: 1.0*
*Formalized from Loucks Silver Nova May 2027 (506101-26) intake — first complete run through all 5 systems.*

---

## PURPOSE

This document captures the end-to-end process for logging a new booking across all five Wing systems, with autonomy rules that allow Hale to complete the intake without Commander involvement.

---

## GROUND TRUTH HIERARCHY (Pipeline Integrity Rules 1–5)

```
Silversea/Regent/Viking portal (live, same session)
    ↓  [primary — always wins on conflict]
Agency PDF / Booking Confirmation PDF
    ↓  [ground truth document — never a memo]
Client Dossier (.md in Drive)
    ↓  [derived — must match Agency PDF exactly]
Booking Master Sheet (EARA D2M Thunderbird v2)
    ↓  [derived — single row per booking]
TESS CRM
    ↓  [derived — operational record]
Itinerary / lifecycle products
    [presentation output — NOT ground truth]
```

**Rule:** Dollar amounts, dates, and booking numbers must always trace to the Agency PDF or live portal. When portal and Agency PDF disagree, portal wins. Flag discrepancies before WF-17.

---

## THE FIVE SYSTEMS

| System | What it stores | Who updates it | Autonomy |
|--------|---------------|----------------|----------|
| **Google Drive** | Agency PDF + Guest PDF (raw source docs) | Hale (upload on receipt) | AUTO |
| **Client Dossier** | All booking data, financial, Harlan sign-off | Hale (builds from Agency PDF) | AUTO |
| **Booking Master** | One row per booking, all key fields | Hale (adds row on confirmation) | AUTO |
| **TESS CRM** | Trip + Booking records | Hale (via `/tess-trip` skill) | AUTO |
| **TESS FPD** | Final payment date on booking record | Hale (manual correction after API) | AUTO |

---

## STEP-BY-STEP INTAKE PROCESS

### Step 0 — Trigger
**New booking confirmed** = Agency PDF received (email or portal download). This is the start signal.

### Step 1 — Save PDFs to Google Drive (< 5 min)
- Upload Agency PDF and Guest PDF to the client's Drive folder
- Naming convention: `{BookingRef}_Agency.pdf` and `{BookingRef}_Guest.pdf`
- Parent folder: create if new client, or use existing client folder
- ✅ **Autonomy: FULL** — no Commander gate

### Step 2 — Extract Ground Truth Data from Agency PDF

Pull these fields verbatim from the Agency PDF:

| Field | Source field on Agency PDF |
|-------|---------------------------|
| Booking # | "BOOKING #:" |
| Ship | "SHIP:" |
| Embark date | "EMBARK DATE:" |
| Debark date | "DEBARK DATE:" |
| Suite/Cabin | "SUITE / CATEGORY:" |
| Total charge | "TOTAL CHARGE:" or "TOTAL CHARGE $" |
| Deposit paid | "CREDIT CARD RECEIVED:" |
| Balance due | "BALANCE DUE:" / "CASH BALANCE:" |
| FPD | "FINAL PAYMENT [date]" in Payment Schedule |
| Commission (gross) | "TOTAL COMMISSION $" (TA copy only) |
| Commission rate breakdown | Line items under TRAVEL AGENT COMMISSION |
| D2M share | Commission × 0.80 (our split with host agency C&TU is 80%) |
| Net due | Commission deducted from balance — for wire planning |

**Harlan sign-off format** (embed in dossier):
```
Commission: $X,XXX.XX · D2M 80% = $X,XXX.XX
Harlan sign-off: "Confirmed $X,XXX.XX as of {date}, source: Agency PDF {ref}"
```

### Step 3 — Create / Update Client Dossier
- File: `dossiers/DOSSIER_{Client}_{Ship}_{MonthYear}.md`
- Template: follow existing dossier format (see `DOSSIER_Loucks_SilverNova_May2027.md` as gold standard)
- Required sections: VOYAGE OVERVIEW, TRAVELERS, FINANCIAL SUMMARY, WF-17 exception (if applicable), PHASE CHECKLIST
- Embed Harlan sign-off in financial section
- ✅ **Autonomy: FULL**

### Step 4 — Add Row to Booking Master (EARA D2M Thunderbird v2)

**Sheet ID:** `1GFjUe8RvP-GT4YHGn0DYv_BEAZGXlYfwEicFrm8ANuU`

Minimum required fields per row:
- Created Date, Client Name, Booking ID, Client Email, Trip Name, Itinerary, Start Date, End Date, Trip Type, Destination, Supplier, Confirmation Number, Status
- Total Cost, Commission, D2M Share, Amount Paid, Balance Due, Payment Due Date, Final Payment Date
- Travelers count, Lead Traveler, Ship Name, Stateroom Category, Stateroom Number
- Notes: include segment details, commission breakdown, agency name, source doc reference

**Use Google Workspace MCP** (`google-workspace-johnloucks3`) to append row.

✅ **Autonomy: FULL**

### Step 5 — Log in TESS CRM (use `/tess-trip` skill)

Two-step process (documented in full at `/home/john/.claude/skills/tess-trip/SKILL.md`):

**Step 5a — Create Trip (Playwright UI — POST /Trip API is broken)**
- Login: `johnloucks3@gmail.com` / see `config/roboform_credentials.md`
- Navigate: Trip Management → Trips → "+" 
- Fill: Trip Type=Vacation, Start/End dates (use pressSequentially), Description
- Save → capture TripID from URL

**Step 5b — Create Booking (REST API)**
```python
from core.booking.thunderbird_tess_crm import TESSWriteClient
c = TESSWriteClient()
result = c.create_booking(
    booking_number="506101-26",
    tour_operator_id=15221,  # Silversea
    tour_operator_name="Silversea Cruises",
    trip_id=TRIP_ID,
    start_date="2027-05-05T00:00:00",
    end_date="2027-05-29T00:00:00",
    package_price=34450.00,
)
```

**Step 5c — Fix FPD** (known issue: REST API seeds FPD from a template booking)
- Navigate to the booking in TESS UI → edit Final Payment Date field
- Or via direct API PATCH if endpoint supports it
- FPD must match Agency PDF exactly

✅ **Autonomy: FULL** — TESS is an internal system, no Commander gate

### Step 6 — Update Mission Board

Add or update a mission:
```
python3 OpsCenter/mission_board_sync.py add "Intake complete: {Client} {Booking#}" "..." P2
```
Or mark existing intake mission complete.

✅ **Autonomy: FULL**

### Step 7 — AM Brief Entry

Add the new booking to the Client Wire table in the next AM brief. It will auto-populate from Booking Master on the next brief generation cycle.

---

## COMMISSION RULES

| Cruise Line | Host Agency | Agency Rate | D2M Split | Notes |
|-------------|-------------|-------------|-----------|-------|
| Silversea | Cruises & Tours Unlimited (C&TU), Jacksonville FL | 16% base + 1% NTB | 80% D2M | NTB = New To Brand bonus |
| Regent Seven Seas | Nexion (host) | Varies | 70/30 or 80/20 | Check each booking's TA copy |
| Viking Ocean | Nexion (host) | Varies | 80/20 | Check each booking's TA copy |

**Commission formula (Silversea):**
```
Commissionable = Total Charge − Port Expenses/NCF
Gross Commission = Commissionable × 0.17 (16% + 1% NTB)
D2M Share = Gross Commission × 0.80
```

**Harlan's role:** Independent verification. His sign-off must appear in the dossier before any client email touches dollar amounts (Rule 5, SO-PIPELINE-INTEGRITY-20260528). No separate ledger needed — the dossier IS his record.

---

## KNOWN TOUR OPERATOR IDs (TESS)

| Cruise Line | TourOperatorID |
|-------------|----------------|
| Silversea Cruises | 15221 |
| Regent Seven Seas | (look up: `GET TourOperator?companyName=Regent`) |
| Viking Ocean | (look up: `GET TourOperator?companyName=Viking`) |
| Disney Cruise Line | 14460 |

---

## AUTONOMY RULES — MAX AUTONOMY TABLE

| Decision | Autonomy Level | Rule |
|----------|---------------|------|
| Upload PDFs to Drive | 🟢 AUTO | Internal file management |
| Create/update dossier | 🟢 AUTO | Internal document |
| Add Booking Master row | 🟢 AUTO | Internal data system |
| Create TESS Trip + Booking | 🟢 AUTO | Internal CRM |
| Fix TESS FPD after creation | 🟢 AUTO | Data correction |
| Flag commission discrepancy | 🟡 NOTIFY Commander | Financial data conflict |
| Resolve discrepancy > $100 | 🔴 COMMANDER GATE | Financial commitment |
| Send client validation email | 🔴 WF-17 GATE | Client-facing send |
| Book flights/hotels | 🔴 COMMANDER GATE | Financial commitment |

**Default posture:** Hale completes Steps 1–6 in full on receipt of the Agency PDF. Commander sees the intake in the next AM brief. No confirmation loop.

---

## CHECKLIST (copy for each new booking)

```
NEW BOOKING INTAKE — {Booking#} {Client} {Ship} {Departure}
Received: {date}
Source: Agency PDF / portal

[ ] Step 1: PDFs uploaded to Drive ({Booking#}_Agency.pdf + _Guest.pdf)
[ ] Step 2: Ground truth data extracted from Agency PDF
[ ] Step 3: Dossier created/updated (dossiers/DOSSIER_{name}.md)
        Harlan sign-off embedded: $X,XXX.XX gross · $X,XXX.XX D2M
[ ] Step 4: Booking Master row added (EARA D2M Thunderbird v2)
[ ] Step 5a: TESS Trip created (TripID: _______)
[ ] Step 5b: TESS Booking created (BookingID: _______)
[ ] Step 5c: TESS FPD corrected to {date}
[ ] Step 6: Mission board updated
[ ] Step 7: Next AM brief will reflect booking
[ ] TESS FPD correction: [ ] done / [ ] pending manual fix
```

---

## REFERENCE — Loucks Silver Nova May 2027 (FIRST COMPLETE RUN — Gold Standard)

| System | Status | Details |
|--------|--------|---------|
| Agency PDF in Drive | ✅ | `506101-26_Agency.pdf` — uploaded 2026-06-10 |
| Guest PDF in Drive | ✅ | `506101-26_Guest.pdf` — uploaded 2026-06-10 |
| Dossier | ✅ | `dossiers/DOSSIER_Loucks_SilverNova_May2027.md` |
| Booking Master | ✅ | Row dated 6/10/2026, all fields populated |
| TESS Trip | ✅ | TripID 1736213 — created 2026-06-20 |
| TESS Booking | ✅ | BookingID 2430698 — created 2026-06-20 |
| TESS FPD | ⚠️ | Shows 02/12/2026 — needs correction to 12/06/2026 |
| Harlan sign-off | ✅ | In dossier: $5,517.18 gross · $4,413.74 D2M · verified 2026-06-10 |
| Commission | ✅ | $5,517.18 (16% + 1% NTB on $32,454) |

**One open item:** TESS BookingID 2430698 has FPD 02/12/2026 (template default). Needs correction to 12/06/2026. Hale to fix via TESS UI on next session open.

---

*— V. Hale, VCS · Thunderbird Wing · 2026-06-20*
*Canonical: `docs/NEW_BOOKING_INTAKE_PROCESS.md`*
