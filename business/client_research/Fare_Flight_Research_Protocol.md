# Fare & Flight Research Protocol
## Dreams2Memories Travel, LLC · Research SOP

**Version:** 1.0 · **Date:** April 7, 2026  
**Owner:** A2 (Dembe) · **Status:** Draft  
**Template:** Kuklinski Panama Canal Example

---

## Overview

Comprehensive fare and flight research protocol using event-driven architecture. Integrated with client lifecycle anchor dates to provide automated price monitoring, flight option comparison, and best-value recommendations.

## Core Components

### 1. **Fare Watch Automation**
- **Trigger:** Booking confirmation + 24 hours
- **Scope:** Cruise fare monitoring across major lines (Viking, Regent, RSSC, Oceania, Silversea)
- **Tools:** 
  - MCP `thunderbird_fare_watch` tools
  - Cruise line API integration
  - Google Sheets price tracker
- **Frequency:** Weekly sweeps for first 90 days, daily at T-180, T-90, T-60

### 2. **Flight Research Matrix**
- **Trigger:** T-270 days from embark (9 months)
- **Scope:** Premium economy/business class options, alliance partners, positioning flights
- **Data Points:**
  - Airline alliances (Star Alliance, OneWorld, SkyTeam)
  - Positioning airports (major hub accessibility)
  - Seasonal pricing patterns
  - Historical price data (past 3 years)
- **Tools:**
  - MCP `thunderbird_flight_search`
  - ITA Matrix integration
  - Google Flights API
  - Kayak/Expedia scraping

### 3. **Best Price Tracking**
- **Methodology:** 
  1. Establish baseline at booking
  2. Monitor for price drops (cruise + air)
  3. Alert threshold: 5% decrease or $500+ savings
  4. Automate rebooking logic for fare advantages
- **Alerts:** Telegram + email to A3 for client approval

### 4. **Cruise Line Pricing Integration**
- **Direct API:** RSSC, Viking, Regent
- **Scraping:** Oceania, Silversea, Seabourn (Playwright stealth)
- **Commission Tracking:** Ensure D2M commission maintained on rebookings

## Kuklinski Panama Canal Case Study

### Client Context
- **Booking:** Viking Mars, Panama Canal, Dec 17–27, 2026
- **Group:** Kuklinski (Kyle & Rosalie), Kuklinski (Roger & Nick), Morton (Josh & Erica)
- **FPD:** April 8, 2026
- **Cruise Fare:** $15,496 base (Viking Jr Suite)

### Research Implementation

**Phase 1: Initial Setup (Booking + 24h)**
```python
# MCP Tool Call Example
mcp__dreams2memories__fare_watch_register(
    client="Kuklinski",
    voyage="Viking Mars Panama Canal 2026-12-17",
    baseline_price=15496,
    alert_threshold=0.05,  # 5%
    monitoring_frequency="weekly"
)
```

**Phase 2: Flight Research (T-270: Mar 22, 2026)**
- Airport options: IAH, DFW, DEN, LAX, SFO
- Positioning flights to Ft. Lauderdale (FLL)
- Premium economy vs business analysis
- Viking Air Plus evaluation

**Phase 3: Price Drop Monitoring**
- Weekly fare sweeps until T-180
- Daily monitoring T-180 → T-90
- Real-time alerts for group discounts

## Integration Points

### With Lifecycle Engine
- **Anchor Date:** Booking → Fare watch activation
- **Anchor Date:** T-270 → Flight research initiation  
- **Anchor Date:** T-180 → Intensive monitoring
- **Anchor Date:** FPD → Final price lock validation

### With Staff Workflow
1. **A2 Dembe:** Research execution, matrix creation
2. **A9 Vic:** Price validation, commission impact
3. **A3 Dani:** Client presentation, approval routing

### With Google Forms Protocol
- **T-270:** Flight preference survey
- **T-180:** Budget confirmation form
- **T-90:** Final flight selection

## Templates & Outputs

### 1. Flight Comparison Matrix
```csv
Airline,Class,Price,Alliance,Layovers,Duration,Flexibility,Notes
United,Premium Economy,$2,150,Star Alliance,1,9h20m,Standard,Position: IAH→FLL
Delta,Comfort+,$2,320,SkyTeam,1,8h45m,Good,Medallion benefits
American,Business,$3,890,OneWorld,0,8h15m,Excellent,Flagship service
```

### 2. Price Tracking Dashboard
- **Google Sheet:** `Fare_Watch_Kuklinski_2026-12-17`
- **Visual:** Line chart with baseline + current
- **Alerts:** Conditional formatting for drops ≥5%

### 3. Recommendation Template
- **Format:** Client-facing PDF with D2M branding
- **Content:** Top 3 options with rationale
- **Timeline:** Delivered T-240 days (client decision window)

## Quality Assurance

### Validation Checklist
- [ ] All major airlines checked (Big 3 + Southwest, JetBlue)
- [ ] All alliance options explored
- [ ] Seasonal patterns accounted for
- [ ] Historical data variance ≤15%
- [ ] Commission impact analyzed
- [ ] Client preferences incorporated

### Escalation Triggers
- Price increase ≥10% from booking
- No viable flight options within budget
- Alliance changes affecting points/status
- Commission structure threatened

## Next Steps

1. **Implement automation scripts** for weekly sweeps
2. **Build Google Sheets templates** for all active clients  
3. **Train A2 Dembe** on MCP fare/flight tools
4. **Integrate with mission board** for tracking
5. **Create client presentation templates**

---

**Approval:** A3 Dani → Commander Yoda  
**Revision Schedule:** Monthly review, update with new tools/data sources