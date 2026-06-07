---
name: itinerary-builder
description: >
  Construct multi-day luxury trip itineraries from supplier data and booking confirmations.
  Verifies port timing, transfers, and dining reservations. Outputs a branded PDF ready
  for client delivery. Use when asked to build, generate, or create a trip itinerary
  from booking data, port schedules, or supplier confirmations.
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

# Itinerary Builder — D2M Travel Operations

Builds a complete, client-ready trip itinerary from raw booking data.

## Inputs Required

- Cruise booking confirmation (ship, voyage dates, cabin)
- Port schedule (arrival/departure times per port)
- Shore excursion bookings (if any)
- Specialty dining reservations (if any)
- Flight details (embarkation/debarkation)
- Hotel confirmations (pre/post cruise, if any)

## Output

- Branded PDF itinerary (D2M stationery: cream #f7f3ea, blue #0000ff, Georgia)
- Day-by-day narrative with port descriptions
- Transfer timing verification (flag gaps < 90 min)
- Dining schedule grid

## Process

1. Parse all input documents for key data fields
2. Build chronological day sequence
3. Verify transfer windows — flag any < 90 min as risk
4. Draft port narratives (2-3 sentences each, experiential not encyclopedic)
5. Assemble stationery-formatted PDF via `scripts/build_itinerary_pdf.py`
6. Route to WF-17 gate for Commander review before client delivery

## Hard Rules

- ❌ NEVER send to client without WF-17 Commander review
- ❌ NEVER guess transfer times — source from confirmation documents only
- ❌ NEVER use generic cruise-brochure language — write to the specific client

## scripts/

- `build_itinerary_pdf.py` — assembles PDF with D2M stationery (WeasyPrint)
- `parse_booking_confirmation.py` — extracts structured data from PDF/email confirmations
- `verify_transfer_windows.py` — flags timing risks

## references/

- `D2M_STATIONERY_SPEC.md` — color, font, layout spec
- `PORT_NARRATIVE_GUIDE.md` — tone and length standards for port descriptions
