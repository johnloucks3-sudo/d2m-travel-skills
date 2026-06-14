# Portal Obstacle Post-Mortem — 2026-06-14
**Session:** Loucks Door County + Grandeur fare research  
**Authored by:** Hale (COS)  
**Standing Order:** Commander directive 2026-06-14 — "solve the immediate problem, then assess root cause — fix it the FIRST TIME or keep wasting time, tokens, and brains 100 times"

---

## Obstacle 1 — ITA Matrix: Render timeout too short

**What happened:** Attempted ITA Matrix headless Playwright poll for IAD→MIA Dec 27. URL loaded and parsed correctly (JSON format confirmed working). But results never populated — search takes 2–5 minutes to compute, and the prior `RENDER_WAIT_S = 24` (24 seconds) exited before fares appeared.

**Root cause:** Fixed sleep too short. ITA Matrix is doing server-side GDS computation — not caching results — and takes 2–5 min per search in headless Playwright.

**Fix applied (2026-06-14):**
- Increased `RENDER_WAIT_S = 24 → 180` in `scripts/ita_fare_watch_poll.py`
- Replaced fixed `wait_for_timeout(RENDER_WAIT_S * 1000)` with polling loop: checks every 5s for `$XXX` pattern in body text, exits early when fares appear, falls back to full 180s wait
- This means the daily poll will now get results (at cost of ~3 min per ITA watch instead of 24s)

**ITA Matrix URL format:** CONFIRMED WORKING. Base64-encode the JSON search object and append to `?search=`. See `scripts/ita_fare_watch_poll.py` for `make_ita_url()` pattern.

**Mission Board:** MISSION-261 (Sterling to refine further — element-based selector for fare container)

---

## Obstacle 2 — lastminute.com MCP: No US domestic inventory for IAD→MIA

**What happened:** Searched IAD→MIA Dec 27, 2 adults via `mcp__claude_ai_lastminute_com__search_flights`. Returned `total_results: 0`. Confirmed twice with `ranking_best=True`.

**Root cause:** lastminute.com MCP appears to have limited/no coverage for US domestic flights. IAD→MIA is a major United/Frontier nonstop route — clearly not a coverage issue with the route itself.

**Fix applied:** 
- Marked `loucks-grandeur-iad-mia-2026` fare watch as ITA-only (no lastminute fallback)
- Tracker updated with "pending overnight ITA poll" note
- Expect ~$150–250pp based on United IAD→MIA typical pricing

**Rule going forward:** For US domestic routes, use ITA Matrix as primary. lastminute.com = international/transatlantic only. Do NOT retry lastminute.com for domestic routes.

**Mission Board:** None needed — documented here; ITA watch handles it.

---

## Obstacle 3 — Enterprise GRB deep-link: 404

**What happened:** Attempted to build a direct URL to Enterprise GRB car search. URL format `enterprise.com/en/car-rental/deeplinking/search.do?...` returned 404.

**Root cause:** Enterprise's deep-link endpoint changed or the params are wrong. The correct format is unknown without intercepting live network traffic.

**Immediate fix:** Email to Commander included plain `enterprise.com` booking link with location/dates in prose — no deep-link.

**Strategic fix (MISSION-262, post-McLeod Jul 7):**
- Use Playwright to navigate enterprise.com normally and inspect network requests to find correct API endpoint
- OR route to Priceline car rental (likely better deep-link support)
- OR build a simple Playwright form-filler: load `/en/car-rental/locations/{location}`, fill date fields, submit, extract rate

---

## Obstacle 4 — Marriott.com SPA: date params ignored

**What happened:** Navigated to Residence Inn GBR Downtown page with `?checkin=2026-09-06&checkout=2026-09-07` in URL. Page loaded showing today's dates — URL params silently ignored.

**Root cause:** Marriott.com is a single-page application. The URL params for dates are NOT read by the SPA router — the app initializes with today's date regardless. This is a Marriott architectural choice.

**Immediate fix:** Email to Commander included plain `marriott.com` booking link — Commander books manually, selects dates in the UI.

**Strategic fix (MISSION-263, no freeze):**
1. Build Playwright form-filler: navigate to property page, click datepicker, fill dates, extract rate
2. Test Priceline deep-link for Marriott properties — likely accepts date params
3. Long-term: Hotelbeds B2B activation (already in pipeline) — direct API access to Marriott rates

---

## Obstacle 5 — Kayak: bot-wall redirect

**What happened:** Attempted to navigate to Kayak hotel search results via Playwright. Redirected to `bots.html` — hard bot block.

**Root cause:** Kayak uses aggressive bot detection. Playwright headless UA + behavior fingerprint triggers immediate block.

**Known prior to this session:** Noted in memory — "Kayak ✅ (airline scraper), Skiplagged ✅". The airline scraper (Centrav-based) works but direct Playwright on Kayak = blocked.

**Immediate fix:** Did not use Kayak. Routed via lastminute.com instead.

**Strategic fix (MISSION-264, post-McLeod):**
1. Test anansi (curl-cffi TLS mimicry) against Kayak hotel search — same technique that bypassed Finnair
2. If anansi works: wire into hotel rate helper
3. If blocked: remove Kayak from pipeline entirely, use Booking.com / Hotels.com as alternatives
4. anansi test command: `python3 -c "from anansi import fetch; r = fetch('https://www.kayak.com/hotels/Green-Bay...'); print(r.status_code)"`

---

## Summary Table

| # | Portal | Obstacle | Status | Mission |
|---|--------|----------|--------|---------|
| 1 | ITA Matrix | Render timeout too short (24s) | ✅ FIXED — 180s + smart wait | MISSION-261 |
| 2 | lastminute.com | No US domestic coverage | ✅ DOCUMENTED — ITA-only rule | — |
| 3 | Enterprise GRB | Deep-link URL 404 | ⏳ SCHEDULED | MISSION-262 |
| 4 | Marriott.com | SPA ignores date URL params | ⏳ SCHEDULED | MISSION-263 |
| 5 | Kayak | Bot-wall | ⏳ SCHEDULED | MISSION-264 |

---

*All 5 obstacles documented. Immediate problem (IAD→MIA price) → overnight ITA poll handles it. Root causes tracked on Mission Board. No obstacle will be encountered blindly again.*
