---
name: trip-dossier-generator
description: >
  Compile a complete client trip dossier from booking confirmations, supplier contacts,
  hotel details, flight records, and travel documents. Produces a structured dossier
  file and optionally a branded PDF summary. Use when asked to create, build, or update
  a client dossier, compile trip details, or generate a travel package summary.
license: MIT
compatibility: Claude Code 2.0+, Claude Cowork, Cursor, Gemini CLI, Goose
metadata:
  author: Dreams2Memories Travel, LLC
  version: 0.1.0
  category: travel-operations
  vertical: luxury-cruise-travel
allowed-tools:
  - Read
  - Write
  - Bash
---

# Trip Dossier Generator — D2M Travel Operations

Builds a structured dossier from all booking components for a client trip.

## Dossier Sections (13-section canonical layout — SO-TripValidation_v1)

1. Client profile (travelers, preferences, specials)
2. Cruise booking (ship, voyage, cabin, booking ref)
3. Flight details (inbound/outbound, confirmation numbers)
4. Pre-cruise hotel
5. Post-cruise hotel
6. Transfers (port, airport, hotel)
7. Shore excursions
8. Specialty dining reservations
9. Insurance (policy number, coverage dates, emergency contact)
10. Payment schedule (FPD paid, balance due date)
11. Supplier contacts
12. Emergency / escalation contacts
13. Notes and special requests

## Process

1. Collect all booking confirmations for the trip
2. Extract structured data per section
3. Validate completeness — flag any missing required fields
4. Write dossier to `/home/john/Thunderbird/dossiers/<client-name>/`
5. Optionally generate branded PDF summary (D2M stationery)
6. Run `validate_dossier.py` to confirm all 13 sections pass

## Hard Rules

- ❌ NEVER create a dossier without running `validate_dossier.py` to check completeness
- ❌ NEVER store unencrypted passport or document numbers outside the dossier directory
- ❌ NEVER send dossier directly to client — it is an internal operational document

## scripts/

- `extract_booking_data.py` — parses confirmations into structured fields
- `validate_dossier_completeness.py` — checks all 13 sections
- `generate_dossier_pdf.py` — branded PDF summary (internal use)
