# Google Flights Reverse-Engineered Search (CRACKED 2026-08-05)

Query Google Flights programmatically via its shareable `tfs` itinerary token. A simple AI can build the URL and open it in any browser — no API key, no UI automation.

## Trigger
"google flights", "crack google flights", "tfs token", "reverse engineered flights"

## THE CONTRACT — tfs token (decoded byte-by-byte)

**Search URL:**
```
https://www.google.com/travel/flights?tfs=<BASE64URL_PROTOBUF>&tfu=KgIIAw
```

The `tfs` param is a URL-safe base64 protobuf. **Round-trip DEN→ORD (Aug 15→22) token, verified live:**
```
CBwQARoeEgoyMDI2LTA4LTE1agcIARIDREVOcgcIARIDT1JEGhJqBwgBEgNPUkRyBwgBEgNERU5AAUgBcAGCAQsI____________AZgBAQ
```
(Decodes to hex, ASCII strings visible: `2026-08-15`, `DEN`, `ORD`, `ORD`, `DEN`)

**Protobuf field map (round-trip):**
| Field | Content |
|---|---|
| `0a 12` | date slice — `0a 0a "<YYYY-MM-DD>"` (e.g. `0a0a323032362d30382d3135` = "2026-08-15") |
| `6a 07 08 01 12 03 "<ORIGIN>"` | outbound origin airport code |
| `72 07 08 01 12 03 "<DEST>"` | outbound dest airport code |
| `1a 12 6a 07 08 01 12 03 "<DEST>"` | return origin (= outbound dest) |
| `72 07 08 01 12 03 "<ORIGIN>"` | return dest (= outbound origin) |
| `40 01` | flag |
| `48 01` | one-way=0 / round-trip=1 |
| `70 01` | flag |

**One-way token (same route, no return slice):**
```
CBwQARoeEgoyMDI2LTA4LTE1agcIARIDREVOcgcIARIDT1JEGhJqBwgBEgNPUkRyBwgBEgNERU5AAUgBcAGCAQsI____________AZgBAQ
```
(tfs above IS the round-trip; one-way drops the `1a 12` return slice and sets `48 01`→`48 00`.)

## HOW A SIMPLE AI BUILDS A SEARCH
1. **Construct the tfs proto bytes** from the field map (pure string/byte building — no UI).
2. Base64url-encode (no padding, `-`/`_`).
3. URL = `https://www.google.com/travel/flights?tfs=<b64>&tfu=KgIIAw`
4. Open in a browser; parse fares from the results DOM (rows with `$NNN`).

## INTERNAL API ENDPOINTS (captured live — for the ambitious path)
All are POST `https://www.google.com/_/FlightsFrontendUi/...` with `f.req=<urlencoded JSON>` + `at=<auth>`:
- `/data/batchexecute?rpcids=H028ib` — airport code search/autocomplete. Body `["DEN",[1,2,3,5],null,[2],1]`.
- `/data/batchexecute?rpcids=BVAT3` — **itinerary token builder**. Body encodes the slice graph: `[[[[["DEN",0]],[["ORD",0]]],[[["ORD",0]],[["DEN",0]]]]]` = round-trip origin/dest pairs.
- `/data/travel.frontend.flights.FlightsFrontendService/GetCalendarPicker` — fare calendar; body embeds `[[[["DEN",0]]],[["ORD",0]]]` + dates.
- `/data/batchexecute?rpcids=tDoGIe` — airport metadata.
**Caveat:** these need `at=` (session auth token from the page) + `f.sid` — NOT directly callable from a bare script without the page session. The tfs-URL path avoids this entirely.

## UI FORM (only if needed — fragile, prefer tfs URL)
- Inputs: `input[aria-label='Where from?']`, `input[aria-label='Where to? ']`, Departure, Return.
- Fill airport code → click the suggestion option (`@e4 "Denver International Airport (DEN)"`).
- Dates via datepicker: click Departure field → click the day gridcell → return gridcell → "Done. Search for one-way flights..." button.
- Results render as `$NNN` rows. Verify with `document.body.innerText` + regex `/\$\s?[0-9][0-9,]*/`.

## VERIFIED LIVE (2026-08-05)
- DEN→ORD round-trip Aug 15→22 2026: dates confirmed in calendar ($308/day on grid).
- tfs token decodes to correct protobuf (2026-08-15, DEN, ORD, ORD, DEN).

## MULTI-CITY MAY 2027 — STATUS (2026-08-05, clock-limited)
- **Business (2 pax) multi-city DEN→VCE 05/01 + ATH→DEN 05/30** attempted via both UI and constructed tfs.
- **Constructed multi-city tfs** (fields per map below): 
  `CBwQARoSCgoyMDI3LTA1LTAxBwgBEgNERU4HCAESA1ZDRRoSCgoyMDI3LTA1LTMwBwgBEgNBVEgHCAESA0RFTkABSAFwAYIBCwj___________8BmAEB`
  Structure = `08 1c 10 01` + `[1a 12 | 0a 0a date | 6a airport | 72 airport]` per leg ×2 + trailer `40 01 48 01 70 01 82 01 0b 08 ff... 98 01 01`.
- ⚠️ **Unverified:** direct navigation to tfs URL renders the Explore landing, NOT results — the tfs token opens the SPA search but results need the full in-session search flow (or the token/tfu combination is incomplete). Round-trip token showed the same behavior when navigated cold. **Do not trust the multi-city token for live fares yet.**
- **UI multi-city was as fragile as ITA's** — auto-copied destinations, "Where else?" stray fields, fill-selector focus errors. Commander's verdict from ITA applies here too: **prefer Centrav B2B + RapidAPI for Business-class May 2027.**

## NOTES / CONSTRAINTS
- **RapidAPI path exists separately**: `core/travel/thunderbird_google_flights_search.py` (DataCrawler, 150 req/mo). Returned **HTTP 429** on 2026-08-05 — free quota may be exhausted. Check before relying on it.
- Google Flights shows consumer fares (not B2B net). For Business-class May 2027 (DEN→VCE 05/01 + ATH→DEN 05/30) cross-check Centrav B2B.
- tfs URL opens the SPA — results may need a few seconds to render; the landing/Explore page shows if the token is malformed or session state is off.
- **Recommendation for May 2027 fares:** use Centrav B2B (`search_centrav_flights`) + RapidAPI Google Flights (once 429 clears) — both are far more AI-friendly than the tfs-SPA path. ITA Matrix baseline: American $6,201 · Lufthansa $7,337 · United $8,230.
