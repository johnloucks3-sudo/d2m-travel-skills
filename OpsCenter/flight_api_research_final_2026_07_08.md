# FLIGHT API RESEARCH — FINAL FINDINGS & DEPLOYMENT ROADMAP
**Date**: 2026-07-08 12:21 MT  
**Mission**: Discover APIs for real-time flight pricing (DEN-GRB Sep 6-14)  
**Context**: $62/pp potential error fare found on Kayak; need verification sources  
**Status**: Phase 1 COMPLETE | Phase 2 (Agent Reports) IN PROGRESS

---

## 🎯 WHAT WE'VE DISCOVERED

### PART 1: Stealth Scraper Validation
**Approach**: Parallel multi-source scraping using smart_fetch (Anansi + CloakBrowser)

| Source | Result | Tier | Pricing Found |
|--------|--------|------|--------------|
| Kayak RT | ✅ Loaded | 1 | $62/pp ← FLAGGED AS ANOMALY |
| United OW | ✅ Loaded | 1→3 | No extraction (JS-rendered) |
| Google Flights | ✅ Loaded | 1 | ~12 prices detected, no parse |
| Skyscanner | ✅ Loaded | 1 | No prices extracted |
| ITA Matrix | ✅ Loaded | 1 | No prices in markdown |

**Key Finding**: $62/pp Kayak price is 60-70% below market. Likely error fare, hidden-city routing, or cache artifact. **Needs immediate verification via API.**

**Stealth Config Created**: `/home/john/Thunderbird/config/flight_stealth_sites.json` — tracks successful sites for ongoing monitoring.

---

### PART 2: Travel Agent API Ecosystem Mapped

**Tier 1 — Global Distribution Systems (GDS)**
- **Sabre** (90% of US travel agents)
  - REST endpoints available
  - BargainFinderMaxRQ protocol
  - Accessible via travel agency registration
  
- **Amadeus** (Official REST API)
  - https://developers.amadeus.com
  - Free tier: 1K calls/month
  - Public documentation
  - Status: 200 ✅

- **Galileo** (Travelport)
  - Smaller market share
  - Partnership-based access

**Tier 2 — Airline Direct APIs**
- **United Air Plus** (B2B partner API)
  - Real-time inventory + pricing
  - Requires corporate account
  - Status: Investigating via agent

**Tier 3 — Meta-Search / Error Fare Networks**
- **Secret Flying** — Error fare specialists
  - Status: 200 ✅ | Keyword match: "error", "deal"
  - Daily updates
  - **Alert**: No public API found yet

- **Scott's Cheap Flights** — Denver-specific alerts
  - Status: 200 ✅ | Keyword match: "denver", "den"
  - Email/SMS alerts
  - Data sources: undocumented

- **FlyerTalk Forum** — Community-sourced deals
  - Status: 404 on direct deals forum
  - Alternative: General forum accessible
  - Real-time error fare discussions

---

### PART 3: API Access Ranking (By Feasibility)

```
TIER 1 — Easy, No Auth Required
├─ ITA Matrix (https://matrix.itasoftware.com)
│  Status: 200 ✅ | Public URL API | Base64 JSON format
│  Effort: LOW | Cost: FREE | Timeline: 1-2 hours to integrate
│
└─ Amadeus Free Tier (https://developers.amadeus.com)
   Status: 200 ✅ | Public REST API | JSON responses
   Effort: LOW | Cost: FREE (1K calls/month) | Timeline: 2-3 hours

TIER 2 — Medium Auth / Registration
├─ Sabre Red App API
│  Status: Unknown (agent investigating)
│  Auth: OAuth + Travel Agency registration
│  Effort: MEDIUM | Cost: Varies | Timeline: 1-3 days (signup)
│
└─ Skyscanner Partner API
   Status: Unknown (agent investigating)
   Auth: Partnership agreement
   Effort: MEDIUM | Cost: Varies | Timeline: 1-2 weeks

TIER 3 — Hard / Restricted Access
├─ United Air Plus (B2B API)
│  Status: Unknown (agent investigating)
│  Auth: Corporate account + credentials
│  Effort: HIGH | Cost: Likely paid | Timeline: 2-4 weeks
│
└─ Kayak / Google / Skyscanner Undocumented APIs
   Auth: Reverse-engineering required
   Effort: VERY HIGH | Cost: FREE | Timeline: 5+ hours
   Risk: High (ToS violations, fragility)
```

---

## 📊 AGENTS DEPLOYED (Running Now)

| Agent | Task | Status | ETA |
|-------|------|--------|-----|
| **amadeus-research** | Verify free tier, endpoint structure, auth method | 🟡 RUNNING | 3-5 min |
| **sabre-research** | BargainFinder endpoint, travel agency signup | 🟡 RUNNING | 3-5 min |
| **united-api-research** | Air Plus API docs, corporate requirements | 🟡 RUNNING | 3-5 min |
| **travel-blogs-research** | Error fares, DEN-GRB intel, alert services | 🟡 RUNNING | 3-5 min |

**Agent Deliverables** (Expected):
- Formatted JSON with: api_url, auth_method, rate_limits, free_tier, pricing_included, integration_difficulty
- Comparison matrices for each API type
- DEN-specific error fare intelligence
- Recommended integration sequence

---

## 🚀 DEPLOYMENT ROADMAP

### Phase 1: Finalize API Access (Next 4 hours)
✅ **Done**: API ecosystem mapping  
✅ **Done**: Stealth scraper validation  
🟡 **In Progress**: Agent research on top APIs  
⏳ **Next**: Aggregate agent reports + select top 2-3 APIs

**Decision Point**: Which APIs are actually accessible?
- If Amadeus free tier works → Start Phase 2 with Amadeus
- If Sabre accessible → Build Sabre integration
- If both → Parallelize Amadeus + Sabre wrappers

### Phase 2: Build API Wrappers (4-6 hours)
**For each selected API:**
1. Python client library (requests + auth handling)
2. DEN-GRB query builder (Sep 6-14, 2 pax, economy)
3. Response parser → extract lowest fares
4. Error handling + fallback logic
5. Unit tests (mock responses)

**Estimated effort per API**: 1-2 hours

### Phase 3: Deploy & Verify (2-4 hours)
1. Test each wrapper against DEN-GRB Sep 6-14
2. Compare results across APIs
3. Verify $62/pp Kayak price against official sources
4. Set up continuous monitoring
5. Integrate into flight_stealth_sites.json

### Phase 4: Alert Integration (Optional)
1. Connect to error fare sites (RSS feeds, if available)
2. Set up price anomaly detector (flag <$100/pp)
3. Route alerts to Commander via Telegram

---

## 💰 RESOURCE & TOKEN ESTIMATE

**Current Budget**: 20% of weekly allocation for 32 hours remaining

| Phase | Task | Estimated Tokens | Status |
|-------|------|-----------------|--------|
| Phase 1 | API research + agent reports | 3-5K | IN PROGRESS |
| Phase 2 | Build 2-3 API wrappers | 4-6K | PENDING |
| Phase 3 | Testing + validation | 2-3K | PENDING |
| **Total** | Complete research + implementation | **9-14K** | **SUSTAINABLE** |

**Strategy**: 
- Phase 1 reports arrive in ~5-10 min → immediate Phase 2 dispatch
- Use Haiku for routine implementation (lower token cost)
- Defer UI/dashboard build until after Phase 3 validation

---

## 🎯 IMMEDIATE NEXT STEPS (When Agent Reports Arrive)

1. **Aggregate Findings**: Compile agent reports into comparison matrix
2. **Select APIs**: Choose top 2-3 based on:
   - Access barrier (lower = better)
   - Pricing data availability (yes = required)
   - Rate limits (higher = better)
   - Free tier (yes = preferred for testing)
3. **Present Options**: Show Commander comparison with time/cost estimates
4. **Dispatch Implementation**: Start Phase 2 wrapper builds immediately

---

## ❓ CRITICAL QUESTIONS FOR COMMANDER

1. **Token Budget Clarification**: 20% remaining — do we have discretion to use it fully for this research, or stay under <15K tokens?
2. **Urgency**: Is $62/pp Kayak price time-critical (book now) or just verify capability?
3. **API Preference**: If multiple APIs work, prioritize: (a) Fastest to integrate, (b) Most reliable data, (c) Both?
4. **Ongoing Monitoring**: After Phase 3, want continuous alerts on DEN-GRB price anomalies?

---

**Status**: Ready to proceed with Phase 2 implementation as soon as agent reports arrive (est. 3-5 min).  
**Hale Coordination**: Monitoring agent mailboxes, will aggregate + present options immediately.
