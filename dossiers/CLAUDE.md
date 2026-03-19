# Dossiers — Conventions & Booking Protocol

## Auto-Dossier (Mandatory on Every Booking Create/Confirm/Update)
1. Create or update dossier in `~/Thunderbird/dossiers/`
2. Update Booking Master Google Sheet — client name, email, dates, booking ID
3. Update `THUNDERBIRD_MASTER_PLAN.md` — Part 5 voyage manifest, commission summary, deadlines, client action tracker
4. Mirror dossier to Google Drive — `D2M Trip Dossiers/` folder

A booking without a dossier is incomplete. A dossier without current data is dangerous.

## Naming Convention
`DOSSIER_[Line]_[ClientLastName]_[Destination]_[MonYYYY].md`
Example: `DOSSIER_Regent_Loucks_Scandinavia_Aug2026.md`

## FPD (Final Payment Deadline)
- Always document FPD in dossier header
- Flag unknown FPD as `FPD: UNKNOWN — TESS pull needed`
- Priority alert at 30-day warning — escalate to Commander

## Google Sheets Tabs
| Tab | Contents |
|-----|----------|
| Booking Master | One row per booking — supplier, client, costs, dates, booking ID |
| Daily Itinerary | Port-by-port — date, port, arrival/departure, notes |

## TESS Integration
- `tess_get_booking`, `tess_get_trip` — pull live invoice/payment status
- `tess_upload_document` — attach confirmations to booking record
