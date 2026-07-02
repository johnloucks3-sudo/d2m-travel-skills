# Cruise Discovery Tool — Client Workflow
**Date:** 2026-07-02 | **Author:** ELON (A12) | **Mission:** MISSION-804

---

## Current State of the Tool

**Database:** `data/master_cruise.db` exists on disk but is **empty** (0 tables, 0 rows). The build that loaded 15,354 sailings is recorded in `scripts/build_master_cruise_db.py` and project memory, but the DB was not persisted to the current filesystem state.

**API endpoint:** `d2mluxury.quest/cruises` is **offline** as of 2026-06-29 (`d2m-dashboard.service` died). The public-facing UI is down.

**Query script:** `scripts/query_cruise_db.py` — **created 2026-07-02** (did not exist prior).

**Immediate action before this workflow is operational:** Run `python3 scripts/build_master_cruise_db.py` to repopulate the DB. The script and schema exist; the data needs to be re-ingested.

---

## The Use Case

When a prospect or client asks "what cruises are available for [dates/destination]?" the Wing uses the master cruise DB to deliver a fast, data-grounded answer — not a generic Google/GYG search result. This gives D2M a 30-second research capability that a solo advisor using consumer OTAs cannot match.

**Scope:** Regent Seven Seas, Silversea, Seabourn, Viking Ocean. (Princess/Discovery coverage is lighter — prioritize luxury lines.)

---

## Workflow

### Step 1 — Inquiry Arrives
Client inquiry comes in via email, web form, or Telegram. Can be from existing clients ("what else sails the Mediterranean in May?") or prospects ("we want a luxury cruise in the Caribbean next winter").

### Step 2 — Dani Extracts Parameters
Dani pulls the four dimensions:
- **Destination** (region or port: "Mediterranean", "Caribbean", "Norway", specific port)
- **Dates** (specific or flexible: "May 2027", "Q4 2026–Q1 2027")
- **Party size** (important for suite availability)
- **Line preference** (or "open" if prospect doesn't know yet)

If any parameter is missing, Dani asks one question before querying.

### Step 3 — Wing Queries the DB
```bash
python3 /home/john/Thunderbird/scripts/query_cruise_db.py \
  --destination "Mediterranean" \
  --months "05 06" \
  --line "Silversea" \
  --limit 10 \
  --pretty
```

Other examples:
```bash
# Caribbean, Q4 any line
python3 scripts/query_cruise_db.py --destination "Caribbean" --months "11 12 01"

# Regent any destination, 2027
python3 scripts/query_cruise_db.py --line "Regent" --months "01 02 03 04 05 06" --limit 15

# Seabourn Mediterranean May
python3 scripts/query_cruise_db.py --line "Seabourn" --destination "Mediterranean" --months "05"
```

### Step 4 — Results: Top 5 Matches
Output: JSON array. Key fields per sailing:
- Ship name, cruise line
- Sail date, duration, embark/disembark ports
- Itinerary name / destination description
- Pricing caveat: **no prices in DB** (see Gaps section)

Dani surfaces the top 3–5 matches to Commander for review, formatted as:
> "Three options match: Silver Nova May 5 (21 nights, Piraeus→Civitavecchia, $price TBD), Silver Dawn May 12 (14 nights, Barcelona→Lisbon, $price TBD), Seabourn Ovation May 3 (12 nights, Rome→Athens, $price TBD). Want me to pull pricing on any of these?"

### Step 5 — Pricing (2-Hour SLA)
DB has no prices. For pricing:
- **Centrav B2B portal** (air is good; cruise pricing depends on feed availability)
- **Perx** (`scripts/perx_intel_monitor.py`) for Silversea pricing signals
- **Direct portal** — Regent B2B (MISSION-214/820 for session restore), Viking, Silversea agent portal
- **Manual** — call cruise line group desk for group quotes

Communicate to client: "I'll have pricing on those options for you within 2 hours."

### Step 6 — Proposal via Standard Pipeline
Once top sailing + pricing confirmed:
1. Pull/build client dossier if prospect
2. Dembe: destination intel + competitive pricing validation
3. Dani: proposal draft (client-voice email with 2–3 options)
4. WF-17 → Commander sends

---

## Query Script

`/home/john/Thunderbird/scripts/query_cruise_db.py` — created 2026-07-02.

Supports:
- `--destination` — partial match across destination, ports, itinerary name, ship name, embark/debark
- `--months` — by number ("05 06") or name ("may jun"), handles both sail_date and departure_date columns
- `--line` — partial cruise line match
- `--limit` — default 10, override as needed
- `--pretty` — human-readable JSON output

Handles gracefully: empty DB (tells you to rebuild), missing columns (returns schema), missing DB file.

---

## Gaps

### Gap 1 — DB Is Empty (P0 blocker)
`data/master_cruise.db` file exists but has no tables. Must run `scripts/build_master_cruise_db.py` to repopulate before the query workflow is operational. The builder exists; the data pipeline needs to run.

### Gap 2 — No Pricing in DB
Discovery is the use case. Pricing is a second step, always. Communicate the 2-hour SLA clearly to clients; it frames D2M as thorough, not slow.

### Gap 3 — d2mluxury.quest UI Offline
The public URL (`d2mluxury.quest/cruises`) is down since Jun 29. Until `d2m-dashboard.service` is restored, use the local query script only. This is not a client-workflow blocker (the script works locally) but eliminates the "share the link with client" use case.

### Gap 4 — Viking / Princess Coverage
Viking Ocean and Princess discovery sailings are less complete in the DB. Regent, Silversea, and Seabourn are the priority lines; query results are more reliable there.

---

## Integration Into Dani's Intake Flow

**When this is fully operational:**

Add to `OpsCenter/keyword_router.py` or Dani's intake handler:
- Keyword triggers: "cruise options", "what sailings", "any cruises", "cruise search", "looking for a cruise"
- Action: auto-call `query_cruise_db.py` with extracted parameters before drafting Dani's response

This eliminates the manual step. Client asks → Wing auto-queries DB → Dani shapes the answer. Five-second research cycle.

---

## Next Build Priority

1. **Rebuild the DB** — run `scripts/build_master_cruise_db.py` (MISSION-804 P0 blocker)
2. **Restore d2m-dashboard.service** — brings the public URL back online
3. **Wire query script into Dani intake** — keyword triggers auto-query on cruise inquiries
4. **Add price-request hook** — after DB returns results, auto-trigger Centrav/Perx pricing pull for top match
5. **Duffel integration** — once DUFFEL_API_KEY set, add live flight pricing alongside cruise results for complete trip quotes

---

*MISSION-804 | Owner: Dani (client workflow) + ELON (tech) | DB rebuild: Sterling (code gate)*
