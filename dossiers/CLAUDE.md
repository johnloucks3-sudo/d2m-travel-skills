# Dossier Conventions & FPD Rules
## Dreams2Memories Travel, LLC | Thunderbird OS

---

## Dossier File Naming
- Individual: `{LastName}_{FirstName}_{Ship}_{Type}.md` (e.g., `Westbrook_SilverNova_Personal.md`)
- Master trip: `DOSSIER_{Ship}_{Region}_{MonthYear}.md` (e.g., `DOSSIER_SilverNova_Pacific_Apr2026.md`)
- Supplemental: `{LastName}_{Topic}.md` (e.g., `Nichols_Allianz_Coverage_Brief.md`)

## Required Fields (All Dossiers)
1. **Client name(s)** — full legal names as on passport
2. **Ship / cruise line** — vessel name and operator
3. **Booking confirmation #** — from cruise line
4. **Departure date** — embarkation date
5. **Cabin assignment** — number and category
6. **Payment status** — paid/balance/FPD with amounts
7. **Air travel** — PNR, airline, routes, seat assignments
8. **Emergency contacts** — at least one per traveler
9. **Dietary / medical** — allergies, restrictions, medications
10. **Transfers** — airport-port, port-hotel, all ground transport

## FPD (Final Payment Date) Rules
- **Track FPD in every dossier** — field: `final_payment_date`
- **Alert at 60 days** — surface to Commander via morning brief
- **Alert at 45 days** — escalate: Telegram + email
- **Alert at 30 days** — RED status, daily reminder until resolved
- FPD source of truth: cruise line confirmation, NOT dossier (verify before alerting)

## Auto-Dossier Protocol (4 Steps)
On any booking change:
1. Create/update dossier in `~/Thunderbird/dossiers/`
2. Update Booking Master Google Sheet
3. Update `THUNDERBIRD_MASTER_PLAN.md` (Part 5)
4. Mirror to Google Drive — `D2M Trip Dossiers/`

## Quality Standards
- No fabricated data — if unknown, mark as `NEEDED` or `TBD`
- Prices in USD via `fmt_usd()` — never raw numbers
- All dates in ISO format (YYYY-MM-DD) with timezone where relevant
- Guest forms: link to Google Form pre-fill URL when available
