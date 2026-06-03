# SO AMENDMENT — Trip Validation: Section C Process Changes
## SO-TripValidation_v1.1 | Amendment to SO-2026-06-03

**Effective:** 2026-06-03 | **Author:** Sterling (A7) per lessons learned | **Status:** DRAFT for Commander approval

---

## Change Record

| Version | Date | Author | Change |
|---------|------|--------|--------|
| 1.0 | 2026-06-03 | Hale (on Commander tasking) | Initial canonical format |
| **1.1** | **2026-06-03** | **Sterling (A7)** | **Section C process additions per lessons learned** |

---

## Changes to SO-TripValidation_v1.md

### 1. Add "Group Booking Ripple Map" to Section 2.1 (New row in Content Sections table)

Insert new section between existing §3 (Hotels & Lodging) and §4 (Transfers), renumbering subsequent sections:

| # | Section Title | Required Content | Primary Data Source |
|---|---|---|---|
| 3b | **Group Booking Ripple Map** | One row per shared booking/group arrangement: service name, primary booking reference, affected clients, non-affected clients, cancellation impact notes, status badge | Dossier cross-reference; live portal scrape; Commander notes log |

Move current §4 (Transfers) → §5, §5 (Excursions) → §6, etc. through §10 → §11. Summary sections §11–13 become §12–14.

**Hard rule:** Any shared booking (hotel group block, same-flight PNR group, shared transfer) that affects multiple clients in the same validation window must be documented in this section. Purpose: single source of truth for who is affected when a booking changes.

### 2. Add dossier freshness check to Session Startup checklist

Append to the Session Startup block (top of AGENTS.md, replicated in SO §3 Source Hierarchy):

**New rule (Source Hierarchy §3.1):**
> **Dossier Freshness Gate:** Before any validation begins, check all relevant dossier modification dates. If any dossier is >30 days stale (>30 days since last modification), flag to Hale. Hale decides: (a) proceed with dossier data + flag deltas, or (b) trigger portal rescrape before validation.

### 3. Add insurance surfacing to pre-validation checklist

Append to §5.3 (Insurance Gap Handling):

**New pre-validation step:**
> **Insurance Status Gate (Hale):** Before beginning any trip validation, confirm: "Insurance status known for every client on this booking?" If any client's insurance status is unknown (no policy on file, no card benefit guide checked, no dossier entry), surface to Commander before proceeding with validation.

### 4. Add seat status per-PNR to §2 (Flight Schedule)

Modify the Flight Schedule table required content to include:

**Additional column:** Seat Status (per-PNR, per-client). For shared flights (same flight number, same date), list each client's seat assignment separately — even if on the same booking. Replace any "group seat status" aggregate with per-client rows.

**Modified §2 row spec:**

| Column | Content |
|--------|---------|
| (existing columns +) | |
| Seat Assignment(s) | Per-client seat numbers; if not yet assigned → status badge |

---

## Implementation

Sterling applies these changes to `~/Thunderbird/ops/SO-TripValidation_v1.md`:
1. Renumber sections to accommodate new §3b
2. Add Group Booking Ripple Map section content and format specification
3. Add Freshness Gate to Source Hierarchy
4. Add Insurance Status Gate to §5.3
5. Update Flight Schedule column spec
6. Bump version from 1.0 to 1.1
7. Update Revision History table
8. Notify Hale for Wing distribution

**Approval:** Commander ______ **Date:** ______

*— Sterling (A7) | SO Amendment DRAFT | 2026-06-03*
