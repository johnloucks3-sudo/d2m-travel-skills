# Centrav B2B Air Pricing Techniques — Archived Jun 30 2026

## Re-Auth Technique (Interactive)
Centrav OAuth/CAPTCHA gates cannot be automated. The flow is:
```
commander → centrav_serve.py (on YOGA display)
           → headless Firefox profile launches visible
           → Commander enters username/password
           → CAPTCHA appears (human solves)
           → OTP sent to phone (Commander enters)
           → "Remember this Browser?" → Check YES → Submit
           → Cookies written to `core/travel/data/centrav_ff_profile/cookies.sqlite`
```
- `trustId` (base64 312-char trust token) + `laravel_session` are the critical cookies
- Session persists ~24h then needs re-auth
- MCP headless Firefox CANNOT do this alone — requires human-in-loop

## Firefox Lockfile Cleanup
When Playwright headless Firefox crashes mid-session, these files lock the profile:
```
core/travel/data/centrav_ff_profile/.parentlock   # symlink to Firefox process
core/travel/data/centrav_ff_profile/lock          # lock file
```
Fix: `rm -f .parentlock lock` from profile directory before retry.

## Cabin Restriction for International Routes
**Critical technique discovered Jun 30:**
- Centrav search with `cabin: "all"` on international connecting routes (RIC→PTY, RSW→PTY) times out
- These routes have no direct flights: RIC→IAD/CLT/ATL→PTY (multiple connection options × 4 cabin classes × fare families = explosion)
- Fix: restrict to `cabin: "economy"` (or "business") for single-cabin search
- Domestic direct routes (DEN→MIA) handle `cabin: "all"` fine

## Centrav vs Amadeus Pricing Delta
| Route | Centrav (pp) | Amadeus (pp) | Savings |
|-------|-------------|-------------|---------|
| RIC→PTY Dec 16 | $785 | $862 | 9% |
| FLL→RIC Dec 27 | $194 | $636 | 69% |
| RSW→PTY Dec 16 | $627 | $1,378 | 55% |
| DEN→MIA Dec 18 biz | $904 | N/A (no biz on GDS) | — |
| MIA→DEN Dec 29 biz | $910 | N/A (no biz on GDS) | — |

**Centrav B2B is authoritative source.** Always use Centrav first; Amadeus is fallback only.

## Airport Search Limitation
- `search_airports` returns empty for RIC, PTY, MIA but works for RSW
- Root cause unknown — `search_flights` works with direct IATA codes regardless
- Bypass: skip airport search, use IATA codes directly in `search_flights`

## Fare Watch File Management
Two JSON formats coexist:
- **Dict format (active):** `core/travel/data/fare_watches.json` — `{"watch_id": {fields}}`
- **Array format (stale/inactive):** `data/fare_watches.json` — `{"watches": [{fields}]}`
- Script reads from `core/travel/data/` via `Path(__file__).parent / "data" / "fare_watches.json"`
- Restore from `.bak.20260616` in same directory if file zeroed

## Centrav Warm-Ping Bug Fix
```python
# BROKEN: query_selector checks DOM presence (always true after page load)
page.query_selector("#LogoutButton")

# FIXED: locator checks actual visibility
page.locator("#LogoutButton").is_visible()
```

## Loucks Turkish Airlines Business (Confirmed)
- DEN→IST→VCE / ATH→IST→DEN
- $7,904 total for 2 pax ($3,952 pp)
- Re-verified Jun 29 AND Jun 30 — price stable
- Centrav B2B booking ready when Commander directs
