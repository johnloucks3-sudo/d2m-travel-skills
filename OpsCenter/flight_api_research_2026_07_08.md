# Travel Agent Flight Pricing API Research
**Mission**: Find APIs for real-time DEN-GRB pricing (Sep 6-14, 2 pax)  
**Context**: Potential $62/pp error fare on Kayak requires verification  
**Status**: 🔄 IN PROGRESS (4 agents researching in parallel)  
**Started**: 2026-07-08 12:21 MT  
**Token Budget**: 20% remaining / 32 hours  
**Hale**: Coordinating research, deploying agents, aggregating findings

---

## RESEARCH PHASE 1 — Preliminary Findings

### ✅ Accessible Sources (HTTP 200)
1. **ITA Matrix** (matrix.itasoftware.com)
   - Status: 200 ✅ | Tier: 1 (HTTP, no bot wall)
   - Type: Google's flight pricing engine
   - Access: Public URL-based API
   - **Finding**: Successfully loaded via smart_fetch tier 1; base64 JSON query format works
   - **Next**: Verify pricing extraction from responses

2. **Sabre Developers** (sabre.com/developers)
   - Status: 200 ✅ | Mentions: REST, APIs
   - Access: Public documentation available
   - **Next**: Agent to map flight search endpoints + auth requirements

3. **Skyscanner Partnerships** (skyscanner.com/partnerships)
   - Status: 200 ✅
   - Access: Public partnership page
   - **Next**: Agent to document API terms + developer signup

4. **Travel Communities** (FlyerTalk, Airline Geek, blogs)
   - Status: 200 ✅ | All accessible via tier 1 HTTP
   - **Next**: Search for DEN-GRB specific error fare discussions

### ⚠️ Blocked/Unavailable
- Kayak Business API: 404 (site restructured?)
- Google Flights Partner Program: 404 (may have been deprecated)
- Amadeus homepage: 200 but JS-heavy navigation (agent investigating)

### 🔴 Known Challenges
- Modern OTA sites render pricing with JS → markdown extraction fails
- Most OTA sites require browser-based interaction
- Kayak/Google/Skyscanner have documented internal APIs but undocumented pricing endpoints

---

## EARLY INTEGRATION FEASIBILITY RANKING

| Tier | Option | Auth | Complexity | Pricing Access | Notes |
|------|--------|------|-----------|----------------|-------|
| **EASY** | ITA Matrix | None | Low | Via URL params | Public, no login; base64 JSON format |
| **EASY** | Amadeus Free | API Key | Low | JSON response | Free tier: 1K/month; public docs |
| **MEDIUM** | Sabre API | OAuth/Key | Medium | SOAP/XML | 90% of agencies; agent verifying signup |
| **MEDIUM** | Skyscanner | Partner | Medium | API or RSS | Partnership required |
| **HARD** | United B2B | Corporate | High | Direct | Requires agency credentials |
| **RESEARCH** | Kayak undoc. | Reverse-eng. | High | Via scraping | Already working via stealth scraper |

---

## AGENTS DEPLOYED (Running in Parallel)

| Agent | Task | Focus | ETA Report |
|-------|------|-------|------------|
| amadeus-research | Deeper documentation review | Free tier availability, endpoint structure, auth method, pricing inclusion | 5-10 min |
| sabre-research | BargainFinder API deep dive | Sabre Red App endpoint, SOAP/REST options, travel agency signup requirements | 5-10 min |
| united-api-research | United B2B program research | Air Plus API docs, corporate requirements, credential setup, rate limits | 5-10 min |
| travel-blogs-research | Community research | DEN-GRB error fares, alert service data sources, FlyerTalk threads | 5-10 min |

---

## DEN-GRB SPECIFIC FINDINGS

### Market Context
- **Route**: Denver (DEN) to Green Bay (GRB) — small airport, thin market
- **Demand**: Off-peak (early Sep 2026)
- **Inventory**: Low across all sources
- **Anomaly**: Kayak showing $62/pp → likely error or hidden-city fare

### Earlier Scrape Results
- **Kayak (standard scraper)**: $62/pp outbound | No return pricing
- **Google Flights**: Loaded OK but JS-rendered prices not captured
- **United.com**: Loaded (tier 3 escalation for return)
- **ITA Matrix**: 200 OK but pricing not in markdown output (JS rendering)

### Key Question
Is $62/pp a booking error, hidden-city routing, or stale cache artifact?

---

## IMPLEMENTATION ROADMAP (Pending Agent Results)

### Phase 1: Determine API Access (Next 4 hours)
1. Amadeus: Can we use free tier? ✓ Agent investigating
2. Sabre: Do indie agencies have access? ✓ Agent investigating
3. United: Is B2B API available to non-corporate partners? ✓ Agent investigating
4. Error fares: Do alert services have data feeds? ✓ Agent investigating

### Phase 2: Build Wrappers (If Phase 1 succeeds)
1. Amadeus Python client (requests + JSON parsing)
2. ITA Matrix URL builder + response parser
3. Error fare aggregator (FlyerTalk + blogs + alert services)
4. Continuous monitor for DEN-GRB anomalies

### Phase 3: Deploy & Verify (2-4 hours)
1. Test each API against DEN-GRB Sep 6-14
2. Cross-validate results
3. Verify $62/pp Kayak price
4. Integrate into flight_stealth_sites.json for ongoing monitoring

---

## RESOURCE CONSTRAINTS & STRATEGY

**Token Budget**: 20% remaining for 32 hours
- Each agent: ~2-3K tokens for research report
- Each API wrapper: ~1-2K tokens for implementation
- Testing & validation: ~2-3K tokens
- **Total estimate**: 10-15K tokens for complete research + basic implementation
- **Conservative budget remaining**: Sufficient for research + Phase 2 prep

**Strategy**: 
- ✅ Keep agents running in parallel (minimize serial delay)
- ✅ Use only HTTP tier 1 for research (no browser overhead)
- ✅ Focus on documented APIs first, undocumented reverse-engineering as fallback
- ✅ Save implementation for after agent reports (gather intel first)

---

## EXPECTED AGENT REPORTS

Each agent will return JSON with:
- API endpoint URL
- Authentication requirements  
- Rate limits (calls/day, calls/month)
- Pricing data inclusion (yes/no/partial)
- Access barriers (free/paid/partnership/corporate)
- Integration difficulty estimate
- Sample request/response (if available)
- Alternative sources or workarounds

---

**Next Update**: Aggregate agent findings + present options to Commander with implementation roadmap.
