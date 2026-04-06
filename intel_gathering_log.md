# Intel Gathering — What Works and What Doesn't

## Site Access Matrix (as of Apr 4, 2026)

### ✅ BLOCKED — Don't Try
| Site | Error | Notes |
|------|-------|-------|
| Allianz.com | 403 Akamai WAF | Blocks all curl UAs including Googlebot/Bingbot |
| DuckDuckGo | CAPTCHA wall | "Select all ducks" — automated block |
| Google Cache | JS redirect | Can't render without browser |
| Wayback Machine | Garbled text | Returns alt-text noise, not page content |
| webScrape | 404s | Tool-level failures on cruise/insurance domains |

### ⚠️ PARTIAL — Loads But Limited
| Site | Status | Notes |
|------|--------|-------|
| DeluxeCruises.com | Loads (no WAF) | Monthly sub-pages are 404s (`april-2026.htm`, `may-2026.htm` don't exist). Main Silversea listing may load but no ship-detail pages found yet. |
| Chrome DevTools | DOWN | "Target closed" — Chrome unavailable in this environment |

### ✅ CONFIRMED WORKING
| Site | Status | Notes |
|------|--------|-------|
| iCruise.com | Loads | Ship overviews work. Need to dig deeper for itinerary details. |

## Key Intel Gathered
- **Westbrook Silver Nova departure from Yokohama**: 7:00 PM (confirmed)
- **Date**: April 23, 2026
- **Port**: Yokohama (Osanbashi — Harumi fix from earlier)

## Strategy Notes for Future Research
1. **iCruise.com** is the most promising unblocked path for itinerary lookups
2. **DeluxeCruises.com** loads but URL structure guessed wrong — need to find correct path (likely ship-by-name not by-month)
3. When cruise line sites are blocked, **try aggregator sites first** (iCruise, CruiseCritic, etc.) before line-direct
4. Chrome DevTools availability is intermittent — check before investing time
5. Never trust TESS for itinerary verification — it's been stale/wrong multiple times
6. **Dossier data integrity issue confirmed**: partial updates leave stale data in validation matrices (VJW case with Westbrook). Always cross-reference primary dossier against matrix.

## Commander Availability Notes
- Party of 4: Commander + Susan + Ron + Lindy Westbrook
- Silver Nova: Apr 23 – May 11 (Commander aboard)
- Apr 10–22: Commander on Chromebook + phone, reachable but limited
- Westbrook itinerary still shows old Yokohama port — CORRECTION NOT DELIVERED TO CLIENT