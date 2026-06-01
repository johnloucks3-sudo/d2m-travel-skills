# MCP Tools Research — D2M Integration Candidates
*Generated: 2026-03-18*
*Research by: Thunderbird OS / Claude Sonnet 4.6*

---

## McLeod Client Intel — Real-World Validation

Before the matrix: the McLeod/McGlasson email thread (Silver Muse Mediterranean, Jun–Jul 2026) provides live confirmation of which services real D2M clients are already using independently:

- **GetYourGuide** — Erik booked ALL Rome excursions directly (Colosseum, Florence Uffizi/David, Vatican). This is the #1 validation that GYG is client-facing and the missed commission is real money.
- **Blacklane** — Silversea uses Blacklane for Private Executive Home Transfers. Erik is actively waiting on Blacklane confirmation for his FCO transfer. Direct D2M API access would let Dani proactively provide status/alternatives.
- **Michelin Guide** — Erik shared direct guide.michelin.com URLs for Moma (1 star, $130 tasting menu) and Cipasso Bistrot (Mention). Clients already check Michelin; D2M needs to lead that conversation.
- **Trenitalia** — booked directly by client. Not an API integration target; just note it.
- **FreeNow** — John recommended this European taxi app for Rome. Consumer app, no API needed.
- **Venezia Taxi / water taxis** — manual phone booking. Current gap in D2M toolkit.

---

## 1. LOCAL CITY MAPS

### Google Maps Platform
- **API Docs:** https://developers.google.com/maps/documentation
- **MCP Server:** `@cablate/mcp-google-map` (npm, 17 tools: geocode, directions, search_places) — community-maintained, actively updated. The official `@modelcontextprotocol/server-google-maps` is **deprecated** as of 2025. Google's official replacement is **Maps Grounding Lite** (remote MCP, currently beta). Also available: `@googlemaps/code-assist-mcp` (for building with Maps Platform, not live queries).
- **Pricing:** New subscription model (Nov 2025+): **Starter $100/mo** (50K calls, Dynamic Maps + Geocoding only), **Essentials $275/mo** (100K calls, Maps/Routes/Places/Environment), **Pro $1,200/mo** (250K calls). Pay-as-you-go still available: Essentials SKUs 10K free/mo then $2–7/1K; Pro SKUs 5K free/mo; Enterprise 1K free/mo.
- **Rate Limits:** Varies by SKU and plan; subscription tiers include pooled monthly call budgets with overage at standard PAYG rates.
- **B2B Fit:** Excellent. Port city maps, walking routes to excursion pickup points, hotel-to-pier directions — all high value for Dani's pre-cruise briefings. Essentials plan ($275/mo) is the right tier for D2M volume.
- **Client Links:** https://maps.google.com · https://www.google.com/maps/place/ (deep-link to specific venue)
- **Notes:** Official Maps Grounding Lite MCP is in beta — monitor for GA. For now, `@cablate/mcp-google-map` via stdio is the practical path. Install: `npm install -g @cablate/mcp-google-map`.

---

### Mapbox
- **API Docs:** https://docs.mapbox.com/api/
- **MCP Server:** `@mapbox/mcp-server` (npm — **official, maintained by Mapbox Inc.**). Also `@mapbox/mcp-devkit-server` (developer-focused variant). Full docs at https://docs.mapbox.com/api/guides/mcp-server/
- **Pricing:** Maps API: 50K free loads/mo, then $5/1K up to 200K, $3/1K above 200K. Geocoding, routing, and other products billed separately; volume discounts via sales. Free tier is generous for development and low-volume production.
- **Rate Limits:** Not publicly specified; enterprise/volume via sales.
- **B2B Fit:** Strong alternative to Google Maps. Custom-styled maps (branded for D2M), better developer ergonomics, and the official npm MCP server is a genuine advantage. Port overlays, custom cruise route maps, excursion location maps are all viable use cases.
- **Client Links:** https://www.mapbox.com/maps/ (product showcase)
- **Notes:** The official `@mapbox/mcp-server` is the most polished, officially-supported location intelligence MCP available as of 2026. Strong candidate for D2M custom mapping alongside Google.

---

### OpenStreetMap / Nominatim
- **API Docs:** https://nominatim.org/ · https://operations.osmfoundation.org/policies/nominatim/
- **MCP Server:** None found. No npm or PyPI package. Would require custom wrapper.
- **Pricing:** Free (public instance). Self-hosted Nominatim is free software.
- **Rate Limits:** **1 request/second max** on the public instance. Recommended soft limit: ~2,500 requests/day. No bulk queries, no grid reverse-geocoding permitted. Production use requires self-hosting or a paid provider (Geocode.Earth, LocationIQ — ~$50–200/mo).
- **B2B Fit:** Development/testing only. Not suitable as a primary source at D2M production volume without self-hosting.
- **Client Links:** https://www.openstreetmap.org/
- **Notes:** Use for prototyping only. Self-hosting on YOGA is feasible but resource-intensive. Paid Nominatim hosting is the cleaner path if OSM data is specifically needed.

---

### Foursquare Places API
- **API Docs:** https://docs.foursquare.com/developer/reference/places-api-overview · https://foursquare.com/developer/
- **MCP Server:** `foursquare/foursquare-places-mcp` (GitHub — **official from Foursquare**, Python-based). Install: clone repo + follow `fsq-server-python/README.md`. Requires Python + `uv`. Currently **local-use only**; remote production MCP server noted as "in the works."
- **Pricing:** $200 free developer credits/mo. Pro endpoints: 10K calls free, then $15 CPM (up to 100K), $12 CPM (up to 500K), down to $1.25 CPM at scale. Premium endpoints from $18.75 CPM. No contracts.
- **Rate Limits:** Not publicly specified; see Developer Console. Enterprise: customizable.
- **B2B Fit:** Good for POI discovery — "find restaurants near cruise pier," "what's within walking distance of the port." 100M+ places in 1,500+ categories, with photos, ratings, and real-time popularity data. Complements Google Maps; does not replace it.
- **Client Links:** https://foursquare.com/ (consumer Swarm/City Guide context)
- **Notes:** 100M place database with strong category filtering is well-suited for port city enrichment. The official MCP server is a genuine advantage. Free $200 credit/mo makes this cost-free at D2M's likely volume.

---

## 2. GEOCACHING

### Geocaching.com API (Groundspeak / HQ)
- **API Docs:** https://api.groundspeak.com/documentation · https://partnerships.geocaching.com/api-documentation · https://apidevelopers.geocaching.com
- **MCP Server:** None found. No npm or PyPI package. Custom wrapper required against the REST API.
- **Pricing:** Partner program (application required). No public free tier listed. Partners receive test + live tokens after approval. Rate limits: 60 calls/min per user, 1,200/min per consumer key, 6,000/min per IP.
- **Rate Limits:** See above — tiered by user/key/IP. Generous for most use cases once approved.
- **B2B Fit:** Niche but genuinely differentiating for D2M. "Geocaches within 5 miles of Nassau port" is a memorable add-on for adventure-oriented clients. The application process screens for apps that replicate core Geocaching services — a luxury travel concierge does not, so approval is likely.
- **Client Links:** https://www.geocaching.com/ (consumer app — shareable with adventure-oriented clients)
- **Notes:** Auth via OAuth 2.0 + PKCE. Apply at apidevelopers.geocaching.com. Lead time for approval is unknown; apply now. The c:geo Android app can serve as client-side complement; no API integration needed on the client's end.

### OpenCaching API
- **API Docs:** https://www.opencaching.us/okapi/ (US node) · https://www.opencaching.de/okapi/ (European nodes)
- **MCP Server:** None found.
- **Pricing:** Free, open API. No approval process.
- **Rate Limits:** Varies by node; generally permissive for reasonable use.
- **B2B Fit:** Smaller cache database than Geocaching.com but fully open. Good for prototyping geocache features before Geocaching.com partnership is approved. European nodes (DE, PL, NL) have decent coverage for Mediterranean ports.
- **Client Links:** https://www.opencaching.us/
- **Notes:** Zero barrier to entry. Start here for prototyping; migrate to Geocaching.com once partnership is approved.

---

## 3. EMPLOYMENT / RELOCATION INTEL

### BLS.gov — Bureau of Labor Statistics API
- **API Docs:** https://www.bls.gov/developers/home.htm · https://www.bls.gov/bls/api_features.htm
- **MCP Server:** None found (no official package). PyPI has unofficial helper libraries (`bls`, `bls-api`).
- **Pricing:** **Completely free.** V1: no registration required. V2: free registration for higher quotas and calculated change data.
- **Rate Limits:** V1: 25 series/query, 10 years/series, 500 daily queries (unauthenticated). V2: 50 series/query, 20 years/series, 500 daily queries (registered key).
- **B2B Fit:** High value for relocation clients. BLS provides unemployment rates, median wages by occupation (OES dataset), job openings by metro area (JOLTS), and industry employment counts by county (QCEW). Free and authoritative — cite directly to clients with confidence.
- **Client Links:** https://www.bls.gov/data/ · https://www.bls.gov/oes/ (occupational wages by area)
- **Notes:** Immediate action: query the Omaha/Douglas County MSA (CBSA code 36540) for the Loucks family relocation — unemployment rate, median wages in target occupations, job openings by industry. Register for V2 key at bls.gov. No cost, no approval delay.

### USAJOBS API
- **API Docs:** https://developer.usajobs.gov/ · https://developer.usajobs.gov/guides/
- **MCP Server:** None found.
- **Pricing:** **Free.** API key via registration form at developer.usajobs.gov. Contact: access@usajobs.gov.
- **Rate Limits:** OPM reserves the right to set limits; specific numbers in the Rate Limiting guide. Standard developer use is unconstrained in practice.
- **B2B Fit:** Differentiating for military/federal clients relocating (Colorado Springs client base is heavily military/federal). Federal job searches with clearance filters, pay grade, agency type, and location are valuable for that demographic.
- **Client Links:** https://www.usajobs.gov/ (consumer job search — send clients directly)
- **Notes:** Endpoints: `/api/Search`, `/api/HistoricJoa`, plus 40+ code list endpoints for occupational series, pay plans, security clearance levels. Registration is straightforward.

### Indeed API
- **API Docs:** https://docs.indeed.com/
- **MCP Server:** None found.
- **Pricing:** Sponsored Jobs API now charges **$3 USD/call** for accounts below their monthly sponsorship spend threshold (effective Feb 1, 2026 for most markets). The older free Job Search API is largely deprecated.
- **Rate Limits:** 500 results per page max; access requires approved partnership.
- **B2B Fit:** Low. The free-API era is over. Access now requires either direct partnership or significant sponsorship spend. Not cost-effective for D2M's occasional relocation research use case. Use BLS + USAJOBS instead.
- **Client Links:** https://www.indeed.com/ (direct consumer use — send clients here)
- **Notes:** Skip API integration. Scraping is ToS violation and actively enforced.

### Glassdoor API
- **API Docs:** https://www.glassdoor.com/developer/index.htm
- **MCP Server:** None found.
- **Pricing:** Official API closed to public since 2021. Requires direct partnership and approval.
- **Rate Limits:** Not publicly available.
- **B2B Fit:** Low as an API. Glassdoor employer reviews and salary data are valuable for relocation clients, but the API is inaccessible without formal partnership. Share consumer site directly with clients.
- **Client Links:** https://www.glassdoor.com/Reviews/ (employer reviews) · https://www.glassdoor.com/Salaries/ (salary benchmarks)
- **Notes:** Browser-based research by Dani is the practical path. No API integration.

### ZipRecruiter API
- **API Docs:** https://www.ziprecruiter.com/partner/documentation/
- **MCP Server:** None found.
- **Pricing:** Partner-only access; negotiated pricing.
- **Rate Limits:** Per partner agreement.
- **B2B Fit:** Wrong side of the market for D2M. ZipRecruiter API is designed for job-posting partners (employers, HR platforms), not for job market research. Skip.
- **Client Links:** https://www.ziprecruiter.com/ (consumer job search — send relocating clients here)
- **Notes:** Not an integration target.

### LinkedIn Jobs API
- **API Docs:** https://learn.microsoft.com/en-us/linkedin/talent/job-postings/api/overview
- **MCP Server:** None found (prohibited by LinkedIn ToS for third-party redistribution).
- **Pricing:** Requires official LinkedIn Partner status + signed API agreement with strict data restrictions.
- **Rate Limits:** Restricted; partner-specific.
- **B2B Fit:** None for D2M. LinkedIn prohibits storing or redistributing data to third parties. Scraping is actively enforced against.
- **Client Links:** https://www.linkedin.com/jobs/ (send clients directly — LinkedIn is a direct-to-consumer tool only for D2M purposes)
- **Notes:** Do not attempt API integration.

---

## 4. HOME VALUES / REAL ESTATE

### Zillow / Bridge API (BridgeDataOutput)
- **API Docs:** https://bridgedataoutput.com/docs/platform/API/bridge · https://www.bridgeinteractive.com/developers/bridge-api/ · https://www.zillowgroup.com/developers/
- **MCP Server:** `sap156/zillow-mcp-server` (GitHub, Python/FastMCP — community-maintained, uses Zillow Bridge API). Also available via Apify MCP actor: `apify.com/jdtpnjtp/zillow-property-building-intelligence/api/mcp`.
- **Pricing:** Bridge API: enterprise/custom — contact BridgeDataOutput. Unofficial RapidAPI wrapper: 100 free requests/mo; paid tiers above that. Apify actor: pay-per-run (~$0.25–1.00 per run).
- **Rate Limits:** Bridge API: enterprise SLA. RapidAPI wrapper: free tier = 100/mo.
- **B2B Fit:** Good for relocating clients. Zestimate valuations, active listing search, neighborhood price trends, days-on-market. The community MCP server makes this integrable today. Best use: "what can my budget buy in Omaha" style queries.
- **Client Links:** https://www.zillow.com/ (primary consumer tool — send clients here for browsing)
- **Notes:** Zillow Bridge ToS restricts commercial redistribution; review before building client-facing tools. Internal research use (Dani briefing a client) is the safer path.

### Rentcast API
- **API Docs:** https://developers.rentcast.io/ · https://developers.rentcast.io/reference/billing-and-pricing
- **MCP Server:** None found on npm or PyPI.
- **Pricing:** Free tier: **50 API calls/month free forever**. Paid developer plans: subscription model billed monthly. Consumer product: Pro $12/mo (annual) or $19/mo (monthly). API pricing separate — visit developers.rentcast.io for current API plan rates.
- **Rate Limits:** Plan-dependent; no public hard caps.
- **B2B Fit:** Excellent for rental market research. 140M+ property records, rent estimates (AVM), active for-rent listings, market trends by ZIP code. Perfect for relocating clients comparing rental vs. buy options. Free 50 calls/mo is enough for D2M's occasional relocation research.
- **Client Links:** https://www.rentcast.io/ (consumer rent estimate tool)
- **Notes:** REST API, comprehensive docs at developers.rentcast.io. High priority for integration — unique rental-market data, zero cost to start.

### ATTOM Data Solutions
- **API Docs:** https://api.developer.attomdata.com/docs · https://www.attomdata.com/solutions/property-data-api/
- **MCP Server:** None found.
- **Pricing:** 30-day free trial API key available. Production: enterprise pricing, roughly ~$500/mo for basic access. Custom quotes only.
- **Rate Limits:** Enterprise SLA; custom.
- **B2B Fit:** Premium-tier real estate data (75+ data points/property, sales history, AVM, neighborhood demographics, school ratings). Enterprise pricing makes it prohibitive for D2M's current relocation volume. The free 30-day trial is worth testing.
- **Client Links:** https://www.attomdata.com/
- **Notes:** If D2M builds a relocation advisory practice, ATTOM becomes more viable. For now, Zillow Bridge + Rentcast covers the use case at far lower cost.

### HouseCanary
- **API Docs:** https://www.housecanary.com/resources/developer-tools · https://www.housecanary.com/pricing
- **MCP Server:** None found.
- **Pricing:** **Starts at $79/mo** ($790/yr). Per-endpoint fees: $0.30–0.50 (basic endpoints), $4.00–6.00 (premium). Free test API key available in Developer Center.
- **Rate Limits:** Customizable for enterprise.
- **B2B Fit:** Strong AVM with 36-month price forecasts, 75+ data points, comparable properties. The $79/mo entry point is accessible for D2M. Best use case: giving clients a valuation + 3-year appreciation forecast for a target neighborhood before they commit to a relocation city. The 36-month forecast capability is genuinely differentiating.
- **Client Links:** https://www.housecanary.com/
- **Notes:** Trusted by mortgage lenders and SFR REITs — data quality is high. Request free test API key first to evaluate.

### Redfin
- **API Docs:** **No public API.** Redfin explicitly does not offer a developer API.
- **MCP Server:** None (no API to wrap).
- **Pricing:** N/A
- **B2B Fit:** Consumer tool only. Direct clients to https://www.redfin.com/ for listing search and market data tools.
- **Notes:** The consumer site has excellent days-on-market and sale-to-list ratio data — point clients there directly.

### Realtor.com
- **API Docs:** No formal public developer API. Connections Plus API exists for lead management (real estate professionals), not property data research. Unofficial RapidAPI wrapper available.
- **MCP Server:** None official. Apify actor available.
- **Pricing:** RapidAPI wrapper: 100 free requests/mo. Official access: formal partnership with Move, Inc. required.
- **B2B Fit:** Moderate. The consumer site (realtor.com) is better for clients to browse directly. Zillow Bridge API provides more reliable programmatic access.
- **Client Links:** https://www.realtor.com/
- **Notes:** Send clients to realtor.com for browsing. Use Zillow Bridge API for programmatic queries.

---

## 5. LOCAL RESTAURANTS

### Yelp Fusion AI
- **API Docs:** https://docs.developer.yelp.com/ · https://business.yelp.com/data/products/places-api/ · https://docs.developer.yelp.com/docs/plans
- **MCP Server:** `Yelp/yelp-mcp` (GitHub — **official from Yelp**, Apache 2.0, Python). Exposes `yelp_agent` tool — natural language queries, multi-turn conversation, optional restaurant reservation booking. Install: clone + `make install`. Requires Python 3.10+ and `uv`.
- **Pricing:** 30-day free trial. After trial: **Starter $7.99/1K calls** (300/day, 15 base attributes), **Plus $9.99/1K calls** (500/day, 23 attributes, 3 photos), **Enterprise $14.99/1K calls** (500/day, 66 attributes, 12 photos, Review Highlights, 20 AI API calls/day). Over 150K/mo: contact sales.
- **Rate Limits:** Starter: 300 calls/day. Plus/Enterprise: 500 calls/day.
- **B2B Fit:** Excellent. Natural language restaurant discovery is exactly what Dani needs for port city dining recommendations. The McLeod thread shows clients independently researching Rome restaurants — this gives Dani a programmatic way to do the same research proactively and lead the conversation.
- **Client Links:** https://www.yelp.com/ (reviews and direct booking links — shareable for every business)
- **Notes:** Enterprise tier is the right choice for luxury concierge use (Review Highlights, full photos, AI API access). Start with the free 30-day trial on the official MCP server. The natural language query "Find Michelin-mentioned restaurants within 10 minutes walking of Baglioni Hotel Regina in Rome" is exactly what this handles.

### Google Places API (restaurant filter)
- **API Docs:** https://developers.google.com/maps/documentation/places/web-service
- **MCP Server:** Same as Google Maps — `@cablate/mcp-google-map` includes `maps_search_places`.
- **Pricing:** Bundled with Google Maps Platform subscription. Places Text Search / Nearby Search: Essentials tier at 10K free/mo then ~$5/1K.
- **Rate Limits:** Per Maps Platform subscription tier.
- **B2B Fit:** Strong complement to Yelp. Google Places has broader international coverage — critical for Mediterranean ports where Yelp coverage is sparse. Use Google Places for non-US ports, Yelp for US cities.
- **Client Links:** https://maps.google.com/ (shareable Google Maps links for any restaurant)
- **Notes:** Practical split: Google Places for international port research (Rome, Venice, Dubrovnik, Split), Yelp for US cities (NYC, Miami, Seattle).

### OpenTable
- **API Docs:** https://docs.opentable.com/ · https://dev.opentable.com/
- **MCP Server:** None found on npm/PyPI/GitHub.
- **Pricing:** Affiliate/partner program — no cost to join if approved. Directory API provides restaurant data + reservation links. Full booking API has separate commercial terms.
- **Rate Limits:** Per partner agreement.
- **B2B Fit:** Good for US and major international city reservations. Most practical integration: embed OpenTable reservation deep-links into client dining proposals and itineraries. Full programmatic booking capability requires deeper partnership.
- **Client Links:** https://www.opentable.com/ (consumer — link directly from dining proposals to reservation page)
- **Notes:** Apply for affiliate access at dev.opentable.com. Sandbox available for testing. API Sandbox launched for partner testing. Primary value is generating clickable reservation links for Dani's dining recommendations.

### Resy
- **API Docs:** No official public developer portal. Reverse-engineered consumer API documented unofficially.
- **MCP Server:** `musemen/resy-mcp-server` (community-built on LobeHub — uses unofficial consumer API).
- **Pricing:** No official public API pricing. Consumer API access via app registration (undocumented for third-party developers).
- **Rate Limits:** Undocumented; unofficial. No stability guarantees.
- **B2B Fit:** Low as a formal API. Resy covers premium restaurants in major US cities (NYC, LA, Chicago, SF). For D2M's luxury clients, the consumer site and Resy app are the right tools. The community MCP server builds on an unofficial API with no stability guarantees.
- **Client Links:** https://resy.com/ (consumer — primary US luxury dining reservation tool; send clients directly)
- **Notes:** Monitor for official API release. For now, Resy is a "share the link" service, not an API integration target. Recommend to clients as a tool for the hardest-to-get US reservations.

### TheFork (La Fourchette)
- **API Docs:** https://docs.thefork.io/B2B-API/introduction
- **MCP Server:** None found.
- **Pricing:** B2B API — pricing set by contract with TheFork. Requires partnership application.
- **Rate Limits:** Default level per contract; negotiable.
- **B2B Fit:** HIGH PRIORITY for D2M. TheFork is the dominant restaurant booking platform in France, Spain, Italy, Netherlands, Belgium, Portugal, and Australia — exactly where D2M's Mediterranean cruise clients need dining help. The B2B API supports full booking flows, guest profile syncing (allergies, preferences), and menu/availability access. This is effectively the Resy of Europe.
- **Client Links:** https://www.thefork.com/ (consumer — strong in Italy, France, Spain; shareable booking links)
- **Notes:** Apply for B2B API access at docs.thefork.io. High priority given D2M's Mediterranean portfolio. The McLeod Rome restaurant list (Sistina 52, Enea, Le Colonnette, etc.) would have been faster to research and bookable via TheFork API.

### Michelin Guide
- **API Docs:** https://developer.michelin.com/en (official developer portal — login required to view full catalog)
- **MCP Server:** None found (no official or maintained community MCP server).
- **Pricing:** Official API: enterprise, application and commercial agreement required. No public pricing. Community scrapers exist (GitHub: `NicolaFerracin/michelin-stars-restaurants-api`) but are not for commercial use per Michelin ToS. Apify scraper actor listed as deprecated.
- **Rate Limits:** Not publicly available.
- **B2B Fit:** High aspirational fit; gated access in practice. The McLeod email directly confirms clients use guide.michelin.com for restaurant selection (Erik shared direct links to Moma and Cipasso Bistrot). D2M providing Michelin-aware recommendations is the luxury differentiation clients expect. Practical paths: (1) Apply for official developer access; (2) Use Yelp Enterprise + Google Places with "Michelin" keyword filtering; (3) TheFork surfaces Michelin-recognized restaurants in its UI.
- **Client Links:** https://guide.michelin.com/us/en (share directly with clients — as Erik did in the email thread)
- **Notes:** Apply for access at developer.michelin.com. The portal exists and has a catalog (only visible post-login). Worth a formal application given D2M's luxury positioning.

---

## 6. TRANSPORTATION (PRIVATE / LUXURY)

### Blacklane
- **API Docs:** https://www.blacklane.com/en/business-integrations/ · https://partner.blacklane.com · business@blacklane.com
- **MCP Server:** None found.
- **Pricing:** Commission-based model. No upfront fees publicly disclosed. Enterprise pricing via direct negotiation with Blacklane. Travel agency program: https://www.blacklane.com/en/travel-agencies/leisure/
- **Rate Limits:** Not publicly specified.
- **B2B Fit:** HIGHEST PRIORITY in this category. The McLeod thread provides direct, real-money validation: Silversea uses Blacklane for Private Executive Home Transfers, and Erik is actively waiting on Blacklane confirmation for his FCO transfer. If D2M had direct Blacklane API access, Dani could provide booking status, pricing, and alternatives proactively rather than clients waiting on Silversea as an intermediary. Coverage: 500+ cities, 50+ countries. GDS integrations: Sabre, Amadeus, Travelport. Blacklane has a specific leisure travel agency program.
- **Client Links:** https://www.blacklane.com/ (consumer booking — sharable for self-booking)
- **Notes:** Contact leisure travel agency program at https://www.blacklane.com/en/travel-agencies/leisure/ immediately. This is a direct revenue and service quality opportunity on active bookings. The McLeod situation would have been handled proactively by Dani instead of reactively by Erik.

### Welcome Pickups
- **API Docs:** https://partner.welcomepickups.com/travel-api/ · https://welcomepickups.gitbook.io (public API docs)
- **MCP Server:** None found.
- **Pricing:** **Zero platform fees.** Commission earned on every completed booking (rate set at onboarding). No minimum sales requirements.
- **Rate Limits:** Not specified.
- **B2B Fit:** Strong. 350+ cities globally, verified English-speaking drivers, fixed prices (no surge), flight-tracking for arrivals, white-label option. Specifically designed for travel agencies. No-fee model makes this risk-free to integrate.
- **Client Links:** https://www.welcomepickups.com/ (consumer booking — can be booked on behalf of clients)
- **Notes:** Apply at partner.welcomepickups.com. Dedicated account manager included. Zero risk — apply immediately alongside Blacklane to ensure coverage across all ports where one or the other may have gaps.

### Mozio
- **API Docs:** https://developer.mozio.com/ · https://webflow.mozio.com/travel-agents
- **MCP Server:** None found.
- **Pricing:** **Zero platform fees.** Commission-based. Travel Agent Booking Tool (no API integration required) available immediately. Agents set their own commission per booking (flat fee or % of reservation value). PayPal withdrawal for commissions.
- **Rate Limits:** Not published.
- **B2B Fit:** Good aggregator. 3,000+ ground transport providers across 180 countries. The Travel Agent Booking Tool (no API needed) lets Dani start booking transfers for clients today at no cost. API integration available for volume partners.
- **Client Links:** https://www.mozio.com/ (consumer booking)
- **Notes:** Register as a travel agent at https://webflow.mozio.com/travel-agents — immediate access to the agent dashboard. Zero-risk starting point. For API integration, contact business-partners@mozio.com.

### Talixo
- **API Docs:** https://talixo.com/developers/
- **MCP Server:** None found.
- **Pricing:** B2B pricing via sales; no public pricing.
- **Rate Limits:** Not published.
- **B2B Fit:** Moderate. B2B ground transportation compliance-focused, 1,100+ cities in 130+ countries. Strong GDS distribution. Corporate travel compliance focus makes it more relevant for business travelers than D2M's luxury leisure model. Blacklane and Welcome Pickups are better fits.
- **Client Links:** https://www.talixo.com/
- **Notes:** Lower priority. Contact talixo.com/developers if Blacklane and Welcome Pickups have coverage gaps in a specific market.

---

## 7. EXCURSIONS / ACTIVITIES

### Viator Partner API
- **API Docs:** https://docs.viator.com/partner-api/ · https://partnerresources.viator.com/ · https://travelagents.viator.com/
- **MCP Server:** None found on npm/PyPI/GitHub.
- **Pricing:** **Free to join.** Basic API Access available immediately upon creating affiliate account. Full + Booking Access requires API certification (no additional fee). Commission: **8–12%** per completed booking. $50 minimum payout threshold.
- **Rate Limits:** Per API agreement; not publicly specified.
- **B2B Fit:** HIGHEST PRIORITY in this category. McLeod email confirms Erik booked ALL Rome excursions via GetYourGuide rather than D2M. Viator has 300K+ experiences in 2,500 destinations. If Dani had Viator integration, D2M would capture excursion commissions on every client trip. McLeod Rome excursions alone (Colosseum ~$150pp, Florence ~$120pp, Vatican ~$150pp × 2 guests) represent ~$50–80 in missed commission.
- **Client Links:** https://www.viator.com/ (consumer — 300K+ tours with verified reviews), https://travelagents.viator.com/ (agent booking center)
- **Notes:** Two integration paths: (1) Register at travelagents.viator.com — start capturing commissions on active clients immediately, no API integration required. (2) Apply for Partner API access — deeper automation for Dani-initiated booking suggestions. Start with path 1 today.

### GetYourGuide API
- **API Docs:** https://integrator.getyourguide.com/ · https://code.getyourguide.com/partner-api-spec/ · https://github.com/getyourguide/partner-api-spec (OpenAPI spec on GitHub)
- **MCP Server:** `curiousdev21/remote-mcp-server-authless` (community-built, deployed on Cloudflare Workers). Tools: `search_tours`, `get_tour_details`, `get_tour_availability`, `get_tour_options`, `get_tour_price_breakdown`, `get_tour_reviews`. Requires `GYG_API_KEY` env var.
- **Pricing:** Commission-based partnership. No public API cost. Commission via Integrator Portal partner agreement (typically competitive with Viator at 8–12%). Access via https://integrator.getyourguide.com/.
- **Rate Limits:** Not publicly specified; per partner agreement.
- **B2B Fit:** HIGHEST PRIORITY — equal to Viator. The McLeod email is definitive: Erik explicitly booked all Rome excursions via GetYourGuide, not Viator. GYG has particularly strong European coverage, which is critical for D2M's Mediterranean portfolio. The community Cloudflare MCP server is immediately deployable for testing.
- **Client Links:** https://www.getyourguide.com/ (consumer — shareable activity links, reviews visible to clients as verification)
- **Notes:** Apply for Integrator Portal access at integrator.getyourguide.com immediately. The community MCP server is a working starting point while awaiting official API credentials. This is the single highest-ROI API integration for D2M based on live client behavior documented in the McLeod email thread.

### Musement API (TUI Musement)
- **API Docs:** https://www.tuimusement.com/ · TravelExchange platform API (B2B distribution channel)
- **MCP Server:** `mcp__dreams2memories__search_tours_musement` — **already integrated in D2M's MCP server**.
- **Pricing:** B2B commission model via TravelExchange. Contact TUI Musement for partner access.
- **Rate Limits:** Per partner agreement.
- **B2B Fit:** Already in the toolkit. TUI Musement is expanding aggressively in 2026 (Jet2 partnership launched, 750 multi-day tours added to TravelExchange in 30+ countries). Strong and growing Mediterranean coverage.
- **Client Links:** https://www.tuimusement.com/us/ (consumer — activities by destination)
- **Notes:** Verify current integration status. Run a test query against an active client port (e.g., Dubrovnik for McLeod June 30 port call) to confirm live inventory is returning. Re-evaluate integration quality quarterly as TUI Musement expands.

### Klook API
- **API Docs:** https://klook.gitbook.io/
- **MCP Server:** None found.
- **Pricing:** B2B partner program; commission-based. Pricing via Klook partnership agreement.
- **Rate Limits:** Real-time availability and pricing; limits per agreement.
- **B2B Fit:** Moderate for D2M's primary markets. Klook is dominant in Asia-Pacific (HK, Japan, Korea, Singapore, SE Asia). For D2M's current portfolio (Mediterranean, Caribbean, Alaska, Scandinavia), Viator and GYG have better coverage. Worth applying if Asian itineraries become part of D2M's portfolio.
- **Client Links:** https://www.klook.com/ (consumer — best for Asia-Pacific destinations)
- **Notes:** Table for now. Apply when D2M books Asia cruises regularly.

### Airbnb Experiences
- **API Docs:** No public API. Airbnb does not offer an Experiences booking API for third parties.
- **MCP Server:** None (no API).
- **B2B Fit:** None via API. Consumer tool only.
- **Client Links:** https://www.airbnb.com/experiences/ (share directly with clients for unique local experiences)
- **Notes:** Not an integration target. Mention in recommendations; clients must book directly.

### Peek Pro
- **API Docs:** No dedicated public developer API found. Peek Pro is tour-operator management software (POS, booking system for operators) — not a booking aggregator.
- **MCP Server:** None found.
- **B2B Fit:** Wrong side of the market. Peek Pro is software FOR tour operators. D2M's integration targets are Viator/GYG, which aggregate inventory from operators running Peek Pro. Skip.
- **Notes:** Not an integration target. Operators on Peek Pro distribute inventory via Viator and GYG.

---

## 8. FLIGHTS & BOOKING

### Amadeus for Developers
- **API Docs:** https://developers.amadeus.com/ · https://developers.amadeus.com/pricing
- **MCP Server:** Multiple community servers (none officially supported by Amadeus, all use official Self-Service APIs):
  - `@privilegemendes/amadeus-mcp-server` **(npm — most complete)**: flight search, booking, price analysis, cheapest dates, airport info
  - `donghyun-chae/mcp-amadeus` (GitHub): Flight Offers Search API integration
  - `fiqcodes/amadeus-mcp-server` (GitHub): flights + hotels + activities + city info, auto USD conversion
  - `pratikjadhav2726/mcp-amadeusflights` (GitHub, TypeScript): multi-city, price optimization, airline info
- **Pricing:** Test environment: **free** (2K requests/mo Flight Offers Search, 3K Flight Offers Price, 10 TPS). Production: free monthly quota retained, then pay-as-you-go. Specific production rates at developers.amadeus.com/pricing.
- **Rate Limits:** Test: 10 TPS. Production: varies by API and plan.
- **B2B Fit:** Excellent. Industry standard. 400+ airlines, real-time pricing, seat availability, booking. Self-Service tier accessible without GDS accreditation. Multiple community MCP servers deployable today. D2M's existing `compare_flights` and `search_flights` tools may already use Amadeus — verify the integration and layer the MCP servers on top.
- **Client Links:** N/A (API/data layer; D2M builds the client-facing output)
- **Notes:** `@privilegemendes/amadeus-mcp-server` (npm) is the most complete and immediately deployable option. Install: `npx @privilegemendes/amadeus-mcp-server`. Start with the test environment (free). Amadeus Self-Service is the right tier for D2M before pursuing full GDS accreditation.

### Duffel API
- **API Docs:** https://duffel.com/docs · https://duffel.com/pricing
- **MCP Server:** No dedicated Duffel MCP server found. `HaroldLeo/google-flights-mcp` (GitHub) uses Google Flights data, not Duffel.
- **Pricing:** **Pay as You Go (no upfront fee):** $3.00/confirmed flight order, 1% of total for Managed Content, $2.00/paid ancillary, $0.005/excess search (above 1500:1 search-to-book ratio), 2% FX surcharge. Enterprise: bespoke pricing, volume discounts, own IATA accreditation option. No IATA required for self-service.
- **Rate Limits:** Not specified for standard tier; enterprise SLA.
- **B2B Fit:** Strong complement or alternative to Amadeus. 300+ airlines, no IATA required, transparent per-booking pricing. The $3/booking fee is extremely low versus traditional GDS transaction fees. Clean, modern API with instant booking confirmation and change/cancellation handling in real-time.
- **Client Links:** N/A (API/data layer)
- **Notes:** Duffel vs. Amadeus: Duffel = cleaner API, no accreditation needed, pay-per-booking model. Amadeus = more comprehensive, more MCP servers available, industry standard. Recommended path: Amadeus for search and price comparison, evaluate Duffel for ticketing if GDS accreditation is not in near-term plan.

### Skyscanner API
- **API Docs:** https://developers.skyscanner.net/docs/intro · https://www.partners.skyscanner.net/
- **MCP Server:** None found.
- **Pricing:** Partner-only; must apply at partners.skyscanner.net. Not self-service — requires approval and dedicated account manager. RapidAPI has unofficial wrappers but unreliable.
- **Rate Limits:** Per partner agreement.
- **B2B Fit:** Moderate. Skyscanner is strongest for comparative/inspirational searches (cheapest month, flexible dates) rather than direct booking. 1,300+ supply partners in 52 markets. But the approval process is opaque and partner-gated. For D2M's booking workflow, Amadeus or Duffel provides more reliable B2B access.
- **Client Links:** https://www.skyscanner.com/ (consumer — useful for clients comparing options)
- **Notes:** Apply via partners.skyscanner.net if desired. Do not block D2M's flight API roadmap on Skyscanner approval — proceed with Amadeus first.

### Kiwi.com Tequila API
- **API Docs:** https://tequila.kiwi.com/ · https://kiwicom.github.io/margarita/docs/tequila-api
- **MCP Server:** None found.
- **Pricing:** Free to build and test. Production access via Travelpayouts platform requires **50,000+ MAU** for full access. Direct Tequila access for smaller partners: negotiated case-by-case.
- **Rate Limits:** MAU-gated for full production; specifics per agreement.
- **B2B Fit:** Low for D2M's current scale. The 50K MAU requirement blocks full Tequila access for a boutique agency. Kiwi's strength (multi-city, "anywhere" flexible searches) is not D2M's primary use case (clients already have destinations set). Covered by Amadeus.
- **Client Links:** https://www.kiwi.com/ (consumer — useful for flexible/budget client segments)
- **Notes:** Table for now. Revisit if D2M builds a consumer-facing search portal.

### Expedia TAAP / Rapid API
- **API Docs:** https://www.expediataap.com/ · https://partner.expediagroup.com/en-us/solutions/build-your-travel-experience/rapid-api
- **MCP Server:** None found.
- **Pricing:** TAAP: no setup cost, no minimum sales. Requires qualifying agency credentials (IATA, ARC, CLIA, or True). Commission on bookings. Rapid API: enterprise partnership, months-long onboarding, selective vetting.
- **Rate Limits:** TAAP: consumer-level. Rapid API: enterprise SLA.
- **B2B Fit:** TAAP is immediately accessible if D2M has CLIA credentials — primarily useful for hotel bookings (Expedia's strength) rather than flights. The Rapid API integration is enterprise-level and too heavy for D2M's current scale. TAAP provides a booking portal for packages and hotels.
- **Client Links:** https://www.expedia.com/ (consumer — send clients for price comparison)
- **Notes:** If D2M has CLIA, register for TAAP at expediataap.com — no cost, commission on hotel bookings. Rapid API is a 12–24 month horizon item if D2M builds a consumer booking portal.

---

## Priority Integration Roadmap

### Tier 1 — Immediate (Week 1–2, zero or near-zero cost)
| # | Service | Action | Why |
|---|---------|---------|-----|
| 1 | **GetYourGuide** | Apply at integrator.getyourguide.com; deploy community Cloudflare MCP server | McLeod trip proves clients are using GYG right now — missed commissions on active bookings |
| 2 | **Viator Travel Agent Center** | Register at travelagents.viator.com | Start capturing excursion commissions on McLeod, Furlow, and all active clients immediately; no API needed |
| 3 | **Mozio Travel Agent Portal** | Register at webflow.mozio.com/travel-agents | Zero cost, immediate ground transfer booking capability for port city gaps |
| 4 | **Welcome Pickups** | Apply at partner.welcomepickups.com | Zero fees, commission earnings, 350+ cities including all Mediterranean ports |
| 5 | **BLS API V2** | Register at bls.gov for V2 key | Free; query Omaha MSA for Loucks family relocation — actionable this week |
| 6 | **Rentcast API** | Sign up at rentcast.io/api | 50 free calls/mo; rental market data for relocation clients |

### Tier 2 — Near-Term (Month 1)
| # | Service | Action | Why |
|---|---------|---------|-----|
| 7 | **Yelp Fusion AI** | Start 30-day trial; deploy `Yelp/yelp-mcp` | Official MCP server, natural language restaurant discovery, Enterprise AI tier for luxury curation |
| 8 | **Blacklane Travel Agency** | Contact blacklane.com/en/travel-agencies/leisure/ | Direct revenue from Silversea clients; Dani takes over transfer coordination from Silversea |
| 9 | **Amadeus Self-Service** | Register at developers.amadeus.com; deploy `@privilegemendes/amadeus-mcp-server` | Flight search and pricing backbone; test environment free |
| 10 | **Foursquare Places** | Sign up for developer account; deploy `foursquare/foursquare-places-mcp` | $200 free credits/mo; 100M place database for port city POI searches |

### Tier 3 — Medium-Term (Month 2–3)
| # | Service | Action | Why |
|---|---------|---------|-----|
| 11 | **Google Maps Platform** | Essentials plan ($275/mo); deploy `@cablate/mcp-google-map` | Port city maps, walking routes, hotel-to-pier directions in client briefings |
| 12 | **Mapbox** | Free tier; deploy `@mapbox/mcp-server` (official npm) | Custom-styled port maps branded for D2M |
| 13 | **TheFork B2B API** | Apply at docs.thefork.io | European restaurant reservations — critical for Mediterranean portfolio |
| 14 | **Michelin Developer Portal** | Apply at developer.michelin.com | Understand what's available; luxury brand alignment |
| 15 | **Zillow Bridge / community MCP** | Deploy `sap156/zillow-mcp-server` | Relocating client home value research |
| 16 | **HouseCanary** | Request free test API key | 36-month price forecasts for relocation clients; $79/mo if valuable |

### Tier 4 — Long-Term / Monitor
| # | Service | Notes |
|---|---------|-------|
| 17 | **Duffel API** | Evaluate as Amadeus complement for ticketing without GDS accreditation |
| 18 | **Geocaching.com Partnership** | Apply now; niche differentiator for adventure clients; lead time unknown |
| 19 | **Klook** | If Asian itineraries grow in D2M portfolio |
| 20 | **Skyscanner Partner API** | If consumer-facing search portal is built |
| 21 | **ATTOM Data** | If relocation services scale; starts ~$500/mo |
| 22 | **USAJOBS API** | Free; register and build for military/federal relocation clients |

---

*Pricing verified as of March 2026. Verify before purchasing. All priority rankings informed by live client intelligence from McLeod/McGlasson email thread (Silver Muse Mediterranean, Jun–Jul 2026).*

---

## Claude.ai Marketplace MCPs — Discovered 2026-03-18

*These are OAuth-connected integrations available through claude.ai Settings → Integrations. They operate in the claude.ai web UI — they are NOT the same as YOGA's dreams2memories MCP server. Evaluate each for: (a) value in claude.ai conversations, and (b) whether a standalone MCP server or API exists for YOGA/Thunderbird OS integration.*

---

### TIER A — GAME CHANGERS

#### lastminute.com MCP ⭐⭐⭐ — HIGHEST PRIORITY
- **What it does:** "Search, compare and book flights, dynamic packages (flight + hotel) and hotels across global airlines and hotel suppliers" — a full GDS aggregator pre-built as MCP.
- **D2M Impact:** This could replace Centrav browser automation entirely. lastminute.com operates as a B2B aggregator (Bravofly/Rumbo parent company) with access to hundreds of airlines and hotel chains. Dynamic packages = flight + hotel in a single query — exactly what our clients need for air-inclusive proposals.
- **Centrav comparison:** Centrav = D2M-specific agent portal (NDC + consortium fares). lastminute.com = broader GDS-level inventory without the portal overhead. May be complementary, not a full replacement.
- **Standalone API:** lastminute.com (Lm Group) has a Partner API (lmgroup.net). Worth investigating whether the claude.ai MCP token can be replicated in a server-side context, or if a separate partner API key is available.
- **Action:** Test immediately in claude.ai. If live flight search works, request standalone API access for YOGA. Could give Dani live flight + hotel search without waiting for any other Tier 2 registrations.
- **Category:** Flight + Hotel Search

#### Apify MCP ⭐⭐⭐
- **What it does:** Access to 1,000s of pre-built Apify Actors (scrapers, automation bots) — Regent portal scraper, Silversea content, cruise pricing, virtually anything web-based.
- **D2M Impact:** Could replace our entire custom Playwright scraper suite. Actors for Regent Seven Seas, Silversea, Viator, GetYourGuide, OpenTable, and virtually any site already exist in the Apify store. Pay-per-use vs. maintaining custom code.
- **Pricing:** Free tier (monthly compute credits). Paid from ~$49/mo. Usage-based.
- **Standalone MCP:** `@apify/actors-mcp-server` — official npm package, installable on YOGA.
- **Action:** Install `@apify/actors-mcp-server` on YOGA. Browse Apify store for existing Regent/Silversea scrapers before writing custom Playwright code.
- **Category:** Universal Web Automation

---

### TIER B — HIGH OPERATIONAL VALUE

#### Trivago MCP
- **What it does:** Hotel price comparison across hundreds of booking sites — instant competitor rate intelligence.
- **D2M Impact:** Dani can run Trivago comparisons in real-time to confirm our TAAP/Expedia rates are competitive. Client objection handling ("can I find it cheaper?") answered instantly.
- **Standalone API:** Trivago has a Business API for travel companies. The claude.ai integration may be consumer-facing only.
- **Category:** Hotel Price Intelligence

#### Fever Event Discovery MCP
- **What it does:** Live entertainment and events database — concerts, shows, experiences worldwide.
- **D2M Impact:** For every port city in client itineraries — Dani can surface live events happening during the client's stay. Fills the gap between Viator/GYG structured tours and spontaneous local experiences. Venice, Barcelona, Rome, Athens — all covered.
- **Standalone API:** Fever has a Partner/Distribution API. Worth requesting access.
- **Category:** Events & Activities (port city coverage)

#### TomTom Maps MCP
- **What it does:** Real-time maps, routing, traffic, and geocoding with live traffic data.
- **D2M Impact:** Port city briefings with live routing — "your ship arrives at Fusina Terminal; traffic to Hilton Molino Stucky is 25 min by water taxi." Better than static Google Maps for day-of client support. Real-time traffic for airport transfers.
- **Standalone MCP:** TomTom has a developer API and official MCP server. Installable on YOGA.
- **Action:** Evaluate vs. current Google Maps / Mapbox plan. TomTom live traffic may be the differentiator.
- **Category:** Maps & Navigation (real-time)

#### DirectBooker MCP
- **What it does:** "Compare hotels, then book direct" — hotel comparison with direct booking deep-links.
- **D2M Impact:** After showing a client 3 hotel options, provide direct booking links. Complements TAAP rate comparison with consumer-facing booking flow. Could also be used for rate validation against Expedia TAAP.
- **Category:** Hotel Comparison + Booking

---

### TIER C — OPERATIONAL INFRASTRUCTURE

#### DocuSign / SignNow / SignWell MCPs
- **What they do:** Digital signature and document execution.
- **D2M Use:** Client service agreements, authorization forms, trip modifications requiring signature. Currently we have no formal e-signature flow — this fills that gap.
- **Recommendation:** SignWell — free tier allows 3 docs/mo, unlimited if hosted. Good for low-volume client agreements. Escalate to DocuSign if volume grows.
- **Action:** Enable SignWell via claude.ai. Create a D2M "Terms of Service / Booking Authorization" template.

#### Calendly MCP
- **What it does:** Appointment scheduling integrated directly into Claude conversations.
- **D2M Use:** Dani or Naia (EXEC) can offer to schedule a discovery call directly in a proposal email response. Commander can schedule client calls without back-and-forth email. Replaces manual scheduling.
- **Action:** Enable in claude.ai. Create D2M Calendly templates (30-min discovery, 60-min planning session).

#### Zapier MCP
- **What it does:** Connect 7,000+ apps with workflow automation triggered from Claude.
- **D2M Use:** Any integration gap in our MCP stack that Zapier already covers (Stripe, QuickBooks, WhatsApp, SMS, etc.). Safety net for connectors we can't build natively.
- **Notes:** Use sparingly — Zapier zaps add latency and cost. Use for one-off connectors, not high-frequency workflows.

#### n8n MCP
- **What it does:** Open-source workflow automation — self-hosted, no per-task cost.
- **D2M Use:** Could replace some of our systemd timers and Python cron jobs with visual workflow graphs. Better for complex multi-step automations with branching logic.
- **Notes:** Already self-hostable on YOGA. If we install n8n on YOGA, it could orchestrate our morning brief, email sweep, and intel runs with a GUI instead of Python scripts.
- **Evaluation:** High long-term value. Defer until Tier 1 is stable.

#### PDF by Anthropic MCP
- **What it does:** Superior PDF reading and extraction compared to standard file handling.
- **D2M Use:** Booking confirmation PDFs, cruise documents, insurance certificates, airline eTickets — all parsed with better fidelity. Extract specific fields (booking numbers, dates, cabin numbers) without manual parsing.
- **Action:** Enable in claude.ai immediately — zero cost, instant value for booking doc handling.

---

### EXISTING MCPs CONFIRMED IN MARKETPLACE (Already Live or Noted)
| Service | Status | Note |
|---------|--------|------|
| Gmail | Active (claude.ai) | Separate from YOGA dreams2memories MCP; use YOGA's for automation |
| Google Calendar | Active (claude.ai) | Same — YOGA's MCP for Thunderbird automation |
| Notion | Available | D2M doesn't use Notion currently |
| Canva | Active (claude.ai) | EXEC (Naia) tool — proposal visuals, social graphics |
| GitHub | Available | YOGA codebase management |
| Slack | Available | D2M doesn't use Slack currently |

---

### Action Summary — Claude.ai Marketplace
| Priority | Service | Action |
|----------|---------|--------|
| **IMMEDIATE** | lastminute.com | Enable in claude.ai. Test live flight search. Research standalone API for YOGA. |
| **IMMEDIATE** | PDF by Anthropic | Enable in claude.ai. Zero cost, instant value. |
| **WEEK 1** | Apify | Enable + install `@apify/actors-mcp-server` on YOGA. Browse store for Regent/Silversea actors. |
| **WEEK 1** | Fever | Enable in claude.ai. Test port city event coverage. |
| **WEEK 1** | Trivago | Enable in claude.ai. Test hotel rate comparison. |
| **WEEK 2** | TomTom | Evaluate vs. Google/Mapbox. Enable if live traffic is the differentiator. |
| **WEEK 2** | SignWell | Enable + create D2M booking authorization template. |
| **WEEK 2** | Calendly | Enable + create discovery call template. |
| **MONTH 1** | Zapier | Enable as connector safety net. |
| **EVALUATE** | n8n | Consider for YOGA self-hosting to replace systemd timer complexity. |
