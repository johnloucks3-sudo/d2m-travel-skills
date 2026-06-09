# Dossier Conventions & FPD Rules
## Dreams2Memories Travel, LLC | Thunderbird OS
*Schema v2.0 — Updated 2026-06-09 (Sterling A7 / Harlan A9)*

---

## Dossier File Naming
- Individual: `{LastName}_{FirstName}_{Ship}_{Type}.md` (e.g., `Westbrook_SilverNova_Personal.md`)
- Master trip: `DOSSIER_{Ship}_{Region}_{MonthYear}.md` (e.g., `DOSSIER_SilverNova_Pacific_Apr2026.md`)
- Supplemental: `{LastName}_{Topic}.md` (e.g., `Nichols_Allianz_Coverage_Brief.md`)

---

## YAML Frontmatter — Required (All Active Client Dossiers)

Every active client dossier MUST open with a YAML frontmatter block. Fields marked `[REQUIRED]` block WF-17 if absent.

```yaml
---
client: [REQUIRED] Short name for brief display
full_name: [REQUIRED] Full legal names as on passport
cruise_line: [REQUIRED]
ship: [REQUIRED]
booking: [REQUIRED] Confirmation number from cruise line
departure: [REQUIRED] YYYY-MM-DD
return: YYYY-MM-DD
cabin: Cabin number and category

# Payment status [REQUIRED]
payment_status: [paid_in_full | deposit_only | balance_due | fpd_overdue]

# FPD tracking [REQUIRED if payment_status != paid_in_full]
fpd: YYYY-MM-DD
fpd_amount: 00000.00
fpd_verified_date: YYYY-MM-DD       # Date last confirmed against portal/TESS
fpd_source: portal                  # portal | TESS | dossier | memo

# Balance tracking (add when balance exists)
balance_due: 00000.00
balance_due_verified_date: YYYY-MM-DD
balance_due_source: portal          # portal | TESS | dossier | memo

# Commission (add when known)
commission_amount: 00000.00
commission_verified_date: YYYY-MM-DD
commission_source: TESS             # TESS | sheet | memo

status: active | prospect | complete | archived
relationship: client | friend | prospect
---
```

---

## Financial Field Freshness Rules (Harlan A9 — Binding)

1. **Every dollar amount requires `_verified_date` and `_source`** — no exceptions.
2. **Source hierarchy (authoritative → least):** portal > TESS > dossier > memo
3. **Memo is never an acceptable source** for any dollar amount in a client email (Pipeline Integrity Rule 4).
4. **Freshness threshold:** Any financial field with `_verified_date` older than 30 days is STALE.
   - STALE fields must be re-verified before use in any client product.
   - Validation script flags automatically: `python3 scripts/validate_dossier.py`
5. **Conflict rule:** Portal figure is authoritative when portal and dossier disagree. Resolve before WF-17.
6. **Harlan sign-off required** for any financial field in a client-facing email: "Confirmed: $X as of [date], source: [portal/TESS/dossier]."

---

## Required Fields (All Active Dossiers)
1. **Client name(s)** — full legal names as on passport
2. **Ship / cruise line** — vessel name and operator
3. **Booking confirmation #** — from cruise line
4. **Departure date** — embarkation date
5. **Payment status** — `paid_in_full | deposit_only | balance_due | fpd_overdue`
6. **Cabin assignment** — number and category (mark `NEEDED` if unknown)
7. **Air travel** — PNR, airline, routes, seat assignments (mark `N/A` if none)
8. **Emergency contacts** — at least one per traveler (mark `NEEDED` if missing)
9. **Dietary / medical** — allergies, restrictions, medications (mark `NONE` if none)
10. **Transfers** — airport-port, port-hotel, all ground transport

---

## PRODUCTION-LOCK — Dossier Write Authority

| Field Type | Write Authority | Hale's Role |
|---|---|---|
| Financial fields (`fpd_amount`, `balance_due`, `commission_amount`, any `$`) | Harlan (A9) — must include `_verified_date` + `_source` | Stage diff; do not commit |
| Experience / action items (excursions, dining, accessibility) | Reyes (A8) | Route ticket; do not write |
| Narrative sections (descriptions, summaries) | Luna (A6) / Dani (A3) | Route ticket; do not write |
| Structural fields (names, dates, booking #, cabin) | Hale may update with primary-source trace | Commit with source citation |

**Violation test:** If Hale wrote a financial field without Harlan sign-off — PRODUCTION-LOCK violation. Sterling flags at Sunday audit.

---

## FPD (Final Payment Date) Rules
- **Track FPD in every dossier** — field: `fpd` (ISO date)
- **Alert at 60 days** — surface to Commander via morning brief
- **Alert at 45 days** — escalate: Telegram + email
- **Alert at 30 days** — RED status, daily reminder until resolved
- **FPD source of truth:** cruise line portal — NOT dossier (verify before alerting)

---

## Auto-Dossier Protocol (4 Steps)
On any booking change:
1. Create/update dossier in `~/Thunderbird/dossiers/`
2. Update Booking Master Google Sheet
3. Update `THUNDERBIRD_MASTER_PLAN.md` (Part 5)
4. Mirror to Google Drive — `D2M Trip Dossiers/`

---

## Quality Standards
- No fabricated data — if unknown, mark as `NEEDED` or `TBD`
- Prices in USD with two decimal places — never raw integers
- All dates in ISO format (YYYY-MM-DD)
- Guest forms: link to Google Form pre-fill URL when available
- Run `python3 scripts/validate_dossier.py` before any client product exits WF-17

---

## Validation
```bash
# Check all dossiers
python3 scripts/validate_dossier.py

# Check one dossier
python3 scripts/validate_dossier.py --dossier dossiers/Ely_Darrow_Regent_3096289.md

# JSON output for automation
python3 scripts/validate_dossier.py --json
```

Exit code 0 = all pass. Exit code 1 = failures present. Sterling runs weekly in Baldrige sweep.
