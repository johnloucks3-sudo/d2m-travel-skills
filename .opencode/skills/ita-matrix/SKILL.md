# ITA Matrix Reverse-Engineered Fare Search

Query Google's ITA Matrix (matrix.itasoftware.com) WITHOUT a browser — build the base64-JSON search URL directly, open it in any headless browser (or let a simple AI fetch it), and parse the rendered results.

## ⚠️ LESSONS LEARNED (2026-08-05) — READ BEFORE USING

**ITA Matrix is NOT AI-friendly via the web UI.** Verdict from Commander after a full session: **"This is very complicated and NOT AI friendly. Tomorrow we will try Google Flights and Centrav."** Keep this skill for the URL-builder path (no UI), but prefer Google Flights / Centrav for day-to-day fare work.

Key session lessons:
1. **The URL builder WORKS and is validated.** The multi-city base64-JSON payload (below) is ground-truth — captured from ITA's own generated URL. Build the URL, hand it to a browser, parse results. That's the only AI-friendly path.
2. **Do NOT drive the UI form.** Angular Material form is fragile under automation: recent-route autocomplete pollutes fields ("DEN ⭢ ORD"), chips duplicate on Add Flight, input IDs shift every render, and the Commander had to hand-fix the form twice. Zero UI automation going forward.
3. **The web UI's results page confirms it works:** "DEN ⭢ VCE; ATH ⭢ DEN" title + fares rendered in ~60s. Business multi-city results came back: American $6,201 · Lufthansa $7,337 · United $8,230 (2 pax, May 2027).
4. **Commit technique (if you MUST use the UI):** type the 3-letter code, then **press Enter** (or click the field's floating label) to commit the chip. Clicking body/h1 navigates away. "Add Flight" copies the previous leg's dest as a duplicate chip — must delete it.
5. **The internal API endpoint** (`content-alkalimatrix-pa.googleapis.com/batch`, multipart gRPC) is NOT directly callable from Python without the page's session/auth plumbing — the URL + browser-render path is simpler and works.

## Trigger
"ita matrix", "matrix fare", "matrix.itasoftware", "reverse engineered flights"

## The reverse-engineered API contract (captured 2026-08-05)

**Search URL format:**
```
https://matrix.itasoftware.com/flights?search=<BASE64URL_JSON>
```
The `search` param is a URL-safe base64 (no padding, `-`/`_` instead of `+`/`/`) encoding a JSON object.

**One-way payload (verified live DEN→ORD):**
```json
{
  "type": "one-way",
  "slices": [{
    "origin": ["DEN"],
    "dest": ["ORD"],
    "routing": "", "ext": "", "routingRet": "", "extRet": "",
    "dates": {
      "searchDateType": "specific",
      "departureDate": "2026-08-15",
      "departureDateType": "depart",
      "departureDateModifier": "0",
      "departureDatePreferredTimes": [],
      "returnDateType": "depart",
      "returnDateModifier": "0",
      "returnDatePreferredTimes": []
    }
  }],
  "options": {
    "cabin": "COACH",          // COACH | PREMIUM-COACH | BUSINESS | FIRST
    "stops": "-1",             // -1 = no limit
    "extraStops": "1",
    "allowAirportChanges": "true",
    "showOnlyAvailable": "true"
  },
  "pax": {"adults": "1"}
}
```

**Multi-city payload (2 legs):**
```json
{
  "type": "multi-city",
  "slices": [
    {"origin": ["DEN"], "dest": ["VCE"], "dates": {"departureDate": "2027-05-01", "searchDateType": "specific", "departureDateType": "depart", "departureDateModifier": "0", "departureDatePreferredTimes": [], "returnDateType": "depart", "returnDateModifier": "0", "returnDatePreferredTimes": []}},
    {"origin": ["ATH"], "dest": ["DEN"], "dates": {"departureDate": "2027-05-30", "searchDateType": "specific", "departureDateType": "depart", "departureDateModifier": "0", "departureDatePreferredTimes": [], "returnDateType": "depart", "returnDateModifier": "0", "returnDatePreferredTimes": []}}
  ],
  "options": {"cabin": "BUSINESS", "stops": "-1", "extraStops": "1", "allowAirportChanges": "true", "showOnlyAvailable": "true"},
  "pax": {"adults": "2"}
}
```

## How a simple AI uses it

1. **Build the URL** — encode the JSON with `base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")`.
2. **Open** `https://matrix.itasoftware.com/flights?search=<b64>` in a headless browser (Playwright/Firefox) and wait ~2–5 min (ITA computes on the server; results render progressively).
3. **Parse** the results table from the DOM — flight rows contain `$PRICE`, airline, depart/arrive times, duration. Filter rows matching `/\$[0-9]/`.
4. Return `[{price, airline, depart, arrive, duration}, ...]`.

## Verified live results (DEN→ORD 2026-08-15, COACH)
All United nonstops **$229** — 9 departures 6:00 AM → 8:29 PM, durations 2h30m–2h43m.

## Notes / constraints
- No API key, no auth — pure URL + browser render.
- **Rate-limit:** ITA throttles rapid repeats — space searches ≥75s apart.
- Cabin codes: `COACH` / `PREMIUM-COACH` / `BUSINESS` / `FIRST`. Business/First not filed >~330 days out; use COACH for far dates.
- Existing wrapper: `core/travel/ita_matrix.py` (build_url + search_fare + Playwright poll). The `_slice()` helper builds one leg; `build_url()` handles one-way/round-trip; multi-city needs the 2-slice JSON above.
- The web UI form = Angular Material. Origin/Destination inputs are `#mat-input-2` / `#mat-input-3`, date is `#mat-input-18`, adults spinbutton, cabin combobox. Fill via `bsk fill` then confirm the autocomplete chip (`row "DEN cancel"` = accepted).
- **Airport entry (lesson from Commander, 2026-08-05):** type the **3-letter code** into the field, THEN **click elsewhere in the form** (blur the field) to commit it as a chip. Do NOT try to select from the autocomplete dropdown (fragile; the dropdown shows recent-route suggestions like "DEN ⭢ ORD" which pollute the field). The blur/click-elsewhere is what commits the code cleanly.
- **Multi-city form:** each leg has Origin/Dest/Date inputs. Leg 1 = mat-input-19/20/23, Leg 2 = mat-input-24/25/28 (IDs shift per session — re-scan). "Add Flight" adds a leg. Advanced controls may already be expanded.
- **Simplest path for a weak model:** don't drive the UI — build the base64 URL (pure string manipulation), hand it to a browser, parse the table. Zero UI automation.
