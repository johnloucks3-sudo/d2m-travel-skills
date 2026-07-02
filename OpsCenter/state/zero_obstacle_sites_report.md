# Zero-Obstacle Public Pricing Sites — Access Survey
*Dembe A2 | 2026-07-02 | curl-verified, no cookies, no login | v2 — Full D2M Category Coverage*

---

## CRUISE SITES

### ✅ OPEN

**vacationstogo.com** — `200 / 113KB`
- URL: `https://www.vacationstogo.com/regent_seven_seas_cruises.cfm`
- Regent Seven Seas page loads fully. Cruise line dropdown includes Regent, Silversea, Viking, Seabourn, Oceania, Cunard, Ponant — full luxury tier coverage.
- CAVEAT: Prices not embedded in static HTML (JS/AJAX loaded). The page structure is present; pricing requires a browser render or targeted API call.
- Assessment: **HIGH VALUE.** VTG weekly email blast (vtgmail@list.vacationstogo.com) delivers live rack prices in plain text — Regent suite ~$24,700, Silversea ~$18,460 as of 2026-06-26. Email feed is the real asset.

**cruiseweb.com** — `200 / full body`
- URL: `https://www.cruiseweb.com`
- Full Next.js SPA loads. Promotional pricing signals in static HTML: "Up to 40% Off, $300 OBC" on Regent; "$500 OBC + Free Upgrade + Free Beverage" on Viking Ocean.
- Assessment: **MODERATE.** Promo/deal tracking only. Specific fares require headless browser.

**cruisedirect.com** — `200 / accessible`
- URL: `https://www.cruisedirect.com/cruise-line/regent-seven-seas-cruises`
- Page loads with Regent branding. "All prices are per person" confirmed in static HTML. No dollar figures — React SPA, fares client-side.
- Assessment: **MODERATE.** Architecture open; fares require JS render.

### ⚠️ PARTIAL — Accessible, pricing JS-rendered or URL stale

**silversea.com** — `404 / 845KB` — Site open, URL path changed
- /cruises.html returns 404 but full Gatsby/SSR app loads (845KB). "Expedition Cruises," "Signature Cruises," "World Cruises" confirmed in body. Not bot-walled.
- Action: Find correct current URL path (try /en/cruises or /cruises/all).

**vikingcruises.com** — `404 / 154KB` — Site open, URL path stale
- /oceans/cruises/all-cruises.html returns 404 but 154KB body loads. Site is accessible.
- Action: Find correct current URL path.

**shoretrips.com** → ventureashore.com — `200 / 100KB`
- Redirects to ventureashore.com. "Cruise Shore Excursions, Tours & Activities" confirmed. No static prices.
- Assessment: Accessible; needs headless browser for pricing.

### ❌ BLOCKED

**cruises.com** — `200 / 212 bytes` — Incapsula JS challenge (deceptive 200)
**cheapcruises.com** — `200 / 212 bytes` — Identical Incapsula fingerprint
**cruisecritic.com** — `403 / 776 bytes` — Hard bot wall
**expedia.com** — SPA shell only, no content via curl
**cruiselinesreview.com** — `000 / 0` — Dead/unreachable

---

## EXCURSION SITES

### ✅ OPEN — Prices in Static HTML

**getyourguide.com** — `200 / 844KB` — **P0 EXCURSION SOURCE**
- Shore excursion search: `https://www.getyourguide.com/s/?q=shore+excursion`
- **Live prices confirmed:** $80, $85, $100, $111, $141, $143, $157, $168, $205, $228 per person
- Transfer search also open: `https://www.getyourguide.com/s/?q=airport+transfer` — prices $7–$80 confirmed
- Covers Mediterranean, Baltic, Caribbean, all major cruise ports.
- Assessment: **IMMEDIATELY ACTIONABLE.** Direct curl + grep. No browser needed.

**tiqets.com** — `200 / 260KB` — **Museum tickets and attractions**
- URL: `https://www.tiqets.com/en/`
- **Live prices confirmed in static HTML:** $19, $29, $29, $30, $37, $43, $43, $47, $54, $89
- Museum tickets, skip-the-line passes, attraction entry — ideal for pre/post cruise port days.
- Assessment: **HIGH VALUE for port attraction pricing.** Static HTML extraction works today.

### ✅ OPEN — Structure Accessible, Prices Partial

**shoreexcursionsgroup.com** — `200 / 3.07MB` — **Largest open excursion catalog**
- Caribbean shore excursions confirmed. 3MB payload likely contains JSON price data embedded.
- Static `$` grep returned empty — run `grep -oP '"price":[0-9.]+'` for JSON extraction.
- Assessment: **HIGH POTENTIAL.** Needs deeper JSON parse on port-specific URLs.

**civitatis.com** — `200 / 217KB` — Spanish-market leader, global coverage
- URL: `https://www.civitatis.com/en/`
- "Civitatis – Guided Tours & Experiences around the World" confirmed. Prices in HTML: $9 visible (likely minimums/UI elements). Port-specific pages likely have fuller pricing.
- Assessment: **MODERATE.** Homepage prices sparse; port-level pages needed.

**headout.com** — `200 / 1.3MB` — Curated experiences
- Full 1.3MB load. Vatican Museums, Rome, Eiffel Tower, Burj Khalifa confirmed in schema.org structured data.
- Price found: $87. Port city coverage confirmed (Rome, Paris, Dubai).
- Assessment: **MODERATE.** Large payload, structured data present — worth a deeper schema.org extraction pass (`grep -oP '"price":"[0-9.]+"'`).

**privatetoursrome.com** → privatetoursofrome.com — `200 / 409KB`
- Full site loads. Private Rome/Civitavecchia port tours confirmed. No prices in static HTML.
- Assessment: **PARTIAL.** Single-port use only; prices on individual tour pages.

### ❌ BLOCKED

**viator.com** — `403 / 778 bytes` — Tripadvisor bot wall, all paths blocked

---

## TRANSFER / GROUND TRANSPORT SITES

### ✅ OPEN — Prices in Static HTML

**kiwitaxi.com** — `200 / 227KB` — **Best private transfer source**
- "Book Airport Transfers in Advance at Affordable Prices" confirmed. Transfer context confirmed.
- **Prices in static HTML:** $9, $13, $3,000 range (likely city → airport options)
- Worldwide coverage: airports and intercity rides.
- Assessment: **HIGH VALUE for private transfer pricing.** Curl-accessible today.

**getyourguide.com** (transfers) — See excursion section — also covers airport transfers $7–$80

### ✅ OPEN — Structure Accessible, No Static Prices

**shuttledirect.com** — `200 / 93KB`
- Full site loads (93KB). No dollar prices extracted from static HTML.
- Airport shuttle/transfer service. Prices likely require quote/search form submission.
- Assessment: **PARTIAL.** Accessible; prices need form interaction or headless browser.

**jayride.com** — `200 / 54KB`
- Transfer marketplace. "Compare transport options to and from your airport," LHR confirmed as example.
- No static prices — "Call to book" / "N/A" visible in static layer, suggesting quote-based.
- Assessment: **PARTIAL.** Accessible; not curl-extractable for prices. Good for transfer option discovery.

**rentalcars.com** — `200 / 366KB`
- "Cheap Car Rental, Price Match Guarantee" confirmed. Full page loads.
- No prices in static HTML — search-form driven, prices load after form submit.
- Assessment: **PARTIAL.** Site open; pricing requires search query execution.

### ❌ BLOCKED

**viator.com** (transfers) — `403` — Same bot wall as excursion paths
**rome2rio.com** — `403 / 5.7KB` — Bot-walled despite real error body
**raileurope.com** — `403 / 774 bytes` — Hard bot wall

---

## TOUR / EXPERIENCES SITES

### ✅ OPEN — Prices in Static HTML

**airbnb.com/experiences** — `200 / 744KB` — **Rich price data**
- URL: `https://www.airbnb.com/s/experiences`
- **Live prices confirmed:** $2, $20, $24, $25, $29, $31, $35, $36, $39, $42, $45+ — full price ladder visible
- Covers local experiences globally. Useful for port-day activity pricing.
- CAVEAT: $2 outlier suggests some UI element pricing mixed in. Range $20–$45 is the real signal for entry-level experiences.
- Assessment: **HIGH VALUE.** Prices embedded in static HTML. Useful for port experience benchmarking.

**tiqets.com** — Listed under Excursions above. Also covers museums and tours.

### ✅ OPEN — Structure Accessible, Prices Partial

**civitatis.com** — Listed under Excursions above. $9 minimum prices visible.

**headout.com** — Listed under Excursions above. $87 visible; schema.org data extractable.

**klook.com** — `200 / 168KB` — Asia-heavy, global
- URL: `https://www.klook.com/en-US/activity-list/europe/`
- 168KB full page load. No prices extracted from static HTML — JS-rendered pricing.
- Assessment: **PARTIAL.** Site accessible; prices require headless browser.

### ❌ BLOCKED / RATE-LIMITED

No hard blocks in this category beyond viator.

---

## HOTEL SITES

### ❌ BLOCKED / RATE-LIMITED

**hotels.com** — `429 / 27KB` — Rate-limited immediately
- Search URL returned 429 (too many requests) — aggressive rate limiting on first curl hit.
- Assessment: **BLOCKED by rate limiting.** Not viable via curl. Expedia Group property.

**booking.com** — `200 / 3.9KB` — Likely CAPTCHA/challenge page
- 3.9KB body on a hotel search = challenge page, not results. Full results pages are typically 300KB+.
- Assessment: **EFFECTIVELY BLOCKED.** Returns a challenge/CAPTCHA shell.

---

## CONSOLIDATED ACTIONABLE SUMMARY

| Priority | Site | Category | Pricing Status | Method |
|---|---|---|---|---|
| **P0** | getyourguide.com | Excursions + Transfers | ✅ Live prices in HTML | curl + `grep -oP '\$[0-9,]+'` |
| **P0** | tiqets.com | Tours/Attractions | ✅ Live prices in HTML | curl + grep on city/attraction URLs |
| **P0** | VTG email feed | Cruise | ✅ Live rack prices weekly | Parse vtgmail@list.vacationstogo.com |
| **P1** | kiwitaxi.com | Transfers | ✅ Prices in HTML | curl + grep on route-specific URLs |
| **P1** | airbnb.com/experiences | Tours/Experiences | ✅ Prices in HTML | curl + grep; filter $20+ range |
| **P1** | shoreexcursionsgroup.com | Excursions | ⚠️ JSON embedded | `grep -oP '"price":[0-9.]+'` on port URLs |
| **P1** | headout.com | Tours | ⚠️ Schema.org data | `grep -oP '"price":"[0-9.]+"'` extraction |
| **P2** | cruiseweb.com | Cruise deals | ⚠️ Promo copy only | Headless browser for fare tables |
| **P2** | civitatis.com | Tours | ⚠️ Sparse static prices | Port-specific URLs needed |
| **P2** | shuttledirect.com | Transfers | ⚠️ No static prices | Headless browser or form API |
| **P2** | silversea.com | Cruise | ⚠️ URL stale | Fix URL path, then curl |
| **P2** | vikingcruises.com | Cruise | ⚠️ URL stale | Fix URL path, then curl |
| **SKIP** | hotels.com / booking.com | Hotel | ❌ Rate-limited/blocked | Alternatives needed |
| **SKIP** | viator.com | Excursions/Transfers | ❌ Hard 403 all paths | —  |
| **SKIP** | rome2rio / raileurope | Transport | ❌ 403 | — |
| **SKIP** | cruises.com / cheapcruises | Cruise | ❌ Incapsula | — |

## KEY FINDINGS

**Best zero-obstacle sources by category:**
- **Excursions:** GetYourGuide (live prices, curl-ready today)
- **Attractions/Museums:** Tiqets (live prices, curl-ready today)
- **Transfers:** Kiwitaxi (prices in HTML), GetYourGuide (transfers also covered)
- **Local Experiences:** Airbnb Experiences (rich price ladder $20–$45+)
- **Cruise pricing:** No OTA serves Regent/Silversea/Viking in static HTML — VTG email feed is best zero-obstacle source
- **Hotels:** Both major OTAs (Booking, Hotels.com) are effectively blocked via curl — hotel pricing requires either headless browser or a different source (Kayak API, direct hotel brand sites, or aggregator APIs)

**Information gaps:**
1. Hotel pre/post cruise pricing has no clean zero-obstacle source identified. This is the biggest gap.
2. Rail Europe (403) leaves European train pricing uncovered — Trainline.com and DB (Deutsche Bahn) not yet tested.
3. Klook has strong Asia-Pacific coverage but prices are JS-rendered — relevant for any Pacific itineraries.

*— Dembe, A2 | Confidence: HIGH on access status | MODERATE on pricing depth (JS-render gap persists for hotels/cruise) | 2026-07-02*
