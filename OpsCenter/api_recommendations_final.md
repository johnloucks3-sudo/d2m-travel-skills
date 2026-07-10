# FLIGHT API RESEARCH — FINAL RECOMMENDATIONS
**Date**: 2026-07-08 12:31 MT  
**Status**: All agent reports in ✅  
**Token Used**: ~8K (within budget)

---

## 🚨 CRITICAL FINDING: $62/pp Kayak Price Is UNVERIFIED

**Research Result**: Checked against 6 error-fare tracking sites, FlyerTalk, and travel blogs.

| Source Checked | Result |
|---|---|
| Secret Flying | ❌ No DEN-GRB Sep 2026 entry |
| Going (Scott's Cheap Flights) | ❌ No DEN-GRB Sep 2026 entry |
| Airfarewatchdog | ❌ No DEN-GRB Sep 2026 entry |
| FlyerTalk mistake-fares | ❌ No thread found |
| Fly4Free | ❌ No DEN-GRB Sep 2026 entry |
| Blog/travel community | ❌ Zero discussion |

**Possible Explanations**:
1. **Genuine glitch** — surfaced on Kayak only, not yet propagated to trackers (rare but possible)
2. **Hidden-city routing** — DEN→X→GRB connection where GRB is not the ticketed endpoint (legal but risky)
3. **Kayak extraction artifact** — our scraper picked up stale/partial price from cache
4. **Scraper false positive** — not a real available booking

**RECOMMENDATION**: Do NOT book this fare for a client without:
- ✅ Verification via at least one API (Amadeus, ITA Matrix, or Sabre)
- ✅ Confirmation it's nonstop DEN-GRB (not hidden-city)
- ✅ Awareness of United's Feb 2023 CoC amendment (aggressive error-fare cancellation policy)

---

## 📊 FINAL API COMPARISON & DEPLOYMENT ROADMAP

### TOP RECOMMENDATION: Start with Amadeus (Tier 1)

```
🥇 AMADEUS FREE TIER (Easiest Start)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Endpoint:       https://api.amadeus.com/v2/shopping/flight-offers
Auth:           Simple API key (free signup at developers.amadeus.com)
Rate Limit:     1,000 calls/month (free tier)
Pricing Data:   ✅ YES (JSON responses, highly reliable)
Response Time:  ~800ms per query
Coverage:       200+ airlines
Integration:    ✅ EASY (standard REST)

Cost:           $0 (free tier sufficient for testing/monitoring)
Timeline:       Build wrapper in 2-3 hours
Success Prob:   HIGH (public API, well-documented)

NEXT STEP: (1) Sign up at developers.amadeus.com
           (2) Get API key
           (3) Test DEN-GRB query
           (4) Build Python wrapper
```

### SECOND CHOICE: ITA Matrix (No Auth)

```
🥈 ITA MATRIX (Most Open)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Endpoint:       https://matrix.itasoftware.com/search?q=<base64_json>
Auth:           None required (public URL API)
Rate Limit:     None documented (reasonable use assumed)
Pricing Data:   ✅ YES (embedded in HTML response)
Response Time:  ~2-3s per query
Coverage:       All airlines (Google's routing engine)
Integration:    🟡 MEDIUM (response parsing required)

Cost:           $0 (completely free)
Timeline:       Build wrapper in 3-4 hours (HTML parsing trickier than JSON)
Success Prob:   MEDIUM (subject to Google's terms, could change anytime)

NEXT STEP: (1) Build base64 JSON query encoder
           (2) Fetch response HTML
           (3) Parse prices via regex/BeautifulSoup
           (4) Test DEN-GRB query
```

### THIRD CHOICE: Sabre API (B2B Option)

```
🥉 SABRE RED APP (Travel Agency B2B)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Endpoint:       https://www.sabre.com/developers/ (signup required)
Auth:           OAuth2 + travel agency registration
Rate Limit:     Varies by plan
Pricing Data:   ✅ YES (SOAP/XML format)
Response Time:  ~500ms per query
Coverage:       200+ airlines
Integration:    🟡 MEDIUM (SOAP XML parsing)

Cost:           Contact sales (varies, typically $1-10K/month)
Timeline:       4-7 days (approval process) + 2-3 hours build
Success Prob:   MEDIUM-HIGH (requires travel agency credentials)

BLOCKER: We need to verify D2M has IATA/ARC accreditation or partner status
NEXT STEP: (1) Contact Sabre sales
           (2) Provide D2M agency credentials
           (3) Await approval
           (4) Get API keys
```

### NOT RECOMMENDED: Direct United API

```
❌ UNITED AIR PLUS (Skip — Sales-Gated)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Status:         Partner/sales-gated NDC only
Auth:           NDC gateway (no self-serve signup)
Timeline:       2-4 weeks (sales cycle)
Cost:           Unknown (likely $5-20K+/month)
Effort:         HIGH (corporate account required)

ALTERNATIVE: Use Duffel aggregator instead
  • Covers 300+ airlines including United
  • Developer-friendly REST API
  • Self-serve signup (no airline relationship needed)
  • Similar pricing to direct United API
  • Recommended timeline: 1-2 hours

DUFFEL INFO:
  Endpoint:    https://api.duffel.com/
  Auth:        API key (self-serve signup)
  Timeline:    2-3 hours
  Cost:        Varies (freemium model available)
```

---

## 🎯 DEPLOYMENT SEQUENCE (Recommended)

### Phase 1: Immediate (Next 2 hours)
```
START HERE: Amadeus Free Tier
1. Sign up at developers.amadeus.com → get API key
2. Build Python client wrapper (requests + JSON parsing)
3. Test DEN-GRB Sep 6-14 query
4. Compare results vs Kayak $62/pp claim

Objective: Get ONE verified source working
Expected Result: Real pricing for DEN-GRB (likely $90-150/pp)
```

### Phase 2: Secondary Verification (2-3 hours)
```
ADD: ITA Matrix (no auth required)
1. Build URL encoder (base64 JSON format)
2. Test DEN-GRB query
3. Parse pricing from HTML response
4. Cross-validate vs Amadeus

Objective: Get TWO independent sources agreeing
Expected Result: Confidence in real market pricing
```

### Phase 3: B2B Option (Optional, 4-7 days)
```
INVESTIGATE: Sabre or Duffel
1. Determine if D2M has travel agency credentials
2. Evaluate Duffel vs Sabre (Duffel faster)
3. Sign up + test API
4. Integrate into monitoring

Objective: Add B2B/commercial access
Expected Result: Wholesale pricing + inventory data
```

---

## 📋 ACTION ITEMS FOR COMMANDER

### IMMEDIATE (Do Now)
1. ✅ **Verify $62/pp Kayak price** — Not corroborated by any error-fare site
   - Options: (a) Try to book at $62 to confirm availability, (b) Treat as suspicious, (c) Ignore
   - Recommendation: Treat as suspicious until verified by Amadeus/ITA

2. ✅ **Authorize Amadeus API signup** — Free tier, no cost
   - Sign up at: https://developers.amadeus.com
   - Takes <5 minutes
   - Get API key immediately usable

### NEXT (4-6 hours)
3. Dispatch Python wrapper build for Amadeus (2-3 hours)
4. Test DEN-GRB query + compare vs Kayak price
5. If Amadeus ≠ Kayak → Flag Kayak as unreliable source

### LATER (Optional, 4-7 days)
6. Evaluate Sabre or Duffel for B2B pricing access
7. Set up continuous monitoring for DEN-GRB price anomalies

---

## 💰 TOTAL COST ESTIMATE

| Component | Cost | Timeline |
|-----------|------|----------|
| Amadeus API | $0 (free tier) | 2-3 hours |
| ITA Matrix | $0 (free) | 2-3 hours |
| Sabre API | $1-10K/month | 4-7 days |
| Duffel API | $0-500/month (varies) | 1-2 hours |
| **Total for MVP** | **$0** | **4-6 hours** |

---

## ✅ FINAL RECOMMENDATION

**Build Amadeus + ITA Matrix (NO COST, 4-6 hours)**

This gets you:
- ✅ Real-time verified pricing for DEN-GRB
- ✅ Cross-validation from 2 independent sources
- ✅ Ability to spot error fares vs market pricing
- ✅ Continuous monitoring capability
- ✅ Zero cost to start

**Then add Duffel later** if you need B2B/wholesale rates.

---

**Status**: Ready for implementation dispatch.  
**Token Budget**: 8K used of 40K available — **80% remaining for Phase 2 build**.  
**Next**: Await Commander approval to proceed with Amadeus + ITA wrappers.
