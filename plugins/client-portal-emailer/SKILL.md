---
name: client-portal-emailer
description: >
  Draft and send personalized portal activation emails to clients with trip details
  formatted in D2M stationery. Handles the full email pipeline: compose → Dani 6-step
  chain → WF-17 gate → Gmail draft in d2mconcierge. Use when asked to send a portal
  email, activate a client portal, send trip access details, or draft a portal
  invitation for a specific client.
license: MIT
compatibility: Claude Code 2.0+, Claude Cowork, Cursor, Gemini CLI, Goose
metadata:
  author: Dreams2Memories Travel, LLC
  version: 0.1.0
  category: travel-operations
  vertical: client-communications
allowed-tools:
  - Bash
  - Read
  - Write
---

# Client Portal Emailer — D2M Travel Operations

Sends personalized portal activation emails via the D2M stationery pipeline.

## Dani 6-Step Chain (mandatory — zero steps skipped)

1. **Experience** — What is this client's trip? What will they feel when they open the portal?
2. **Narrative** — What story does this email tell? (First access to their journey, not a login link)
3. **Brand** — Apply D2M brand voice: warm, confident, not corporate, not pushy
4. **Voice** — Dani's specific voice: personal, short, specific to this client's details
5. **Facts** — Verify all data: portal URL, booking ref, trip dates, ship name — no errors
6. **WF-17** — Route to Commander for review. Never send directly.

## Email Components

- Personalized greeting using client's preferred name
- Trip summary (ship, dates, ports)
- Portal access link and login instructions
- What they'll find in the portal (dossier, documents, itinerary)
- Dani sign-off block

## Hard Rules

- ❌ NEVER skip the Dani 6-step chain
- ❌ NEVER send directly — always WF-17 gate, Commander sends
- ❌ NEVER use johnloucks3@gmail.com — d2mconcierge only
- ❌ NEVER use "Best" as sign-off — "Thanks" or "Thank you" only
- ❌ NEVER include 719-291-0742 in mass or template communications

## Process

1. Load client dossier from `/home/john/Thunderbird/dossiers/<client>/`
2. Run Dani 6-step chain
3. Build HTML email with D2M stationery (cream #f7f3ea, blue #0000ff, Georgia)
4. Pre-process: `scripts/gmail_template_stripper.py`
5. Create draft: `gmail_create_draft_sync()` → d2mconcierge → THUNDERBIRD-Commander-Review label
6. Surface to Commander for WF-17 review

## scripts/

- `build_portal_email.py` — generates stationery-formatted HTML from dossier data
- Delegates to: `core/email/thunderbird_gmail.py` → `gmail_create_draft_sync()`
