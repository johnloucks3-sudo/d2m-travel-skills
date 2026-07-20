# ROUTING TICKET — Excursion Confirmation & Dossier Write
**McLeod/McGlasson — SS Grandeur Lesser Antilles (booking 2984034)**
**Owner:** Reyes (A8) — Experience Layer, excursion write authority (PRODUCTION-LOCK)
**Routed:** 2026-07-19 by Hale
**Target Return:** ASAP — not client-facing, internal dossier update only

---

## WHY THIS TICKET EXISTS

Commander pasted a Regent guest-portal excursion cart export this session and
asked to add it to the McLeod Dec 2026 dossier. This is the **same booking**
(2984034) where the tracker already logged an identical set of excursions on
2026-07-16 from a live portal read via CDP, flagged explicitly:

> "Excursions CONFIRMED booked... **Route to Reyes** to confirm these are the
> final selections and note anything client-facing needed."
> — `dossiers/McLeod_Grandeur_LesserAntilles_Dec2026_TRACKER.md`, line 93

That item was never closed. The Commander's paste today is independent
confirmation of the same selections. Per `dossiers/CLAUDE.md` PRODUCTION-LOCK:
excursion/experience fields are your write authority, not Hale's — routing,
not committing.

## THE DATA (Commander-supplied, verbatim, 2026-07-19)

| Port | Excursion | Date/Time | Guests | Price |
|---|---|---|---|---|
| Miami (2 days in port) | *None selected* | — | — | — |
| Charlotte Amalie | Shipwreck and Turtle Cove | Dec 22, 2026, 08:30 | McGlasson, Melissa + McLeod, Erik | $0.00 |
| Roseau | River Tubing and Trafalgar Falls | Dec 23, 2026, 11:00 | Both | $0.00 |
| St. John's | Dickenson Bay Beach Break | Dec 24, 2026, 10:30 | Both | $0.00 |
| St. John's | Catamaran Sunset Cruise | Dec 24, 2026, **04:00** | Both | $0.00 |
| Basseterre | Foodie & Beach | Dec 25, 2026, 10:30 | Both | $0.00 |
| Tortola | Escape to Jost Van Dyke | Dec 26, 2026, 09:30 | Both | $0.00 |
| Cart total / Amount due | — | — | — | $0.00 |

**Flags for your review (do not silently resolve — confirm or correct):**
1. **"Catamaran Sunset Cruise" at 04:00** — a sunset cruise at 4 AM doesn't
   track; likely a portal export quirk (24h code, PM not rendered, etc.) for
   what should probably read 16:00/4 PM. Verify against the live portal or
   the confirmed-document source before this goes in as fact.
2. **$0.00 across every line, $0.00 amount due** — the 2026-07-16 tracker
   note assumed these are Regent-complimentary inclusions (Suite 863 is
   E-Concierge, upgraded — Regent's higher suite tiers typically include
   complimentary shore excursions). Confirm that reading rather than assume
   it; dossier rule is no fabricated data, mark `TBD` if genuinely unpriced.
3. **Naming note already resolved in the tracker:** the Dec 24 St. John's
   beach excursion appears in an older PDF as "Runaway Bay Beach Break" —
   the newer, dated, confirmed document (`Pre-Purchased Shore excursions and
   Onboard Items_2984034.pdf`, 7/13/2026) calls it **"Dickenson Bay Beach
   Break."** That's the name already used in the built client itinerary
   (`cruises_web/itinerary_grandeur_mcleod.html`) — keep it consistent.
4. **Miami — no excursions selected**, 2 days in port (pre/post-cruise city
   time, not a cruise touring day) — this is expected, not a gap.

## YOUR DELIVERABLE

1. Confirm (or correct, with source) the six port/excursion/time rows above.
2. Write the finalized excursion section into
   `dossiers/McLeod_Grandeur_LesserAntilles_2984034.md` (the per-booking
   dossier — NOT the multi-booking hub `McLeod_McGlasson_Multi.md`, which is
   relationship-context only per its own routing note).
3. Update `dossiers/McLeod_Grandeur_LesserAntilles_Dec2026_TRACKER.md`:
   - PER-ELEMENT STATUS row "Excursions" → from `⏳ PENDING` to `✅ CONFIRMED`
     (or whatever status your review lands on)
   - Close/update OPEN ITEM #6 ("Excursion research — 5 ports, Regent
     portal — Owner: A2 Dembe")
   - Resolve or explicitly carry forward the "STAGED FOR SIGN-OFF" block
     (lines 90–96) — that's the item this ticket closes out.
4. Note any accessibility/dietary tie-ins worth flagging for the client
   itinerary (e.g. beach/water-activity level, "Foodie & Beach" dietary
   considerations) per your usual experience-layer pass.

**Do not send anything client-facing** — this booking is still pre-FPD
(Jul 22, 2026) and the built itinerary is WF-17 HELD, not sent. This is a
dossier/tracker write only.

## SOURCE FILES
- `dossiers/McLeod_Grandeur_LesserAntilles_2984034.md` (write target)
- `dossiers/McLeod_Grandeur_LesserAntilles_Dec2026_TRACKER.md` (write target)
- `dossiers/McLeod_McGlasson_Multi.md` (relationship hub — reference only, do not write excursions here)
