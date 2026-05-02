# Silversea Spring 2027 Watch System
**n8n Automated Weekly Intelligence | Deployed 2026-04-25**

---

## Overview

Automated weekly monitoring system for two Silversea Silver Spirit voyages (Spring 2027). Runs every Monday at 08:00 MDT via n8n, scrapes 7 sources for pricing and travel advisor/interline rate signals, detects week-over-week price changes, and sends a structured HTML intelligence email to Commander.

---

## Target Voyages

| Voyage Code | Route | Dates | Nights |
|-------------|-------|-------|--------|
| SL270505016 | Lisbon → Copenhagen | May 5–21, 2027 | 16 |
| SL270521015 | Copenhagen → Norway → CPH | May 21–Jun 5, 2027 | 15 |

**Ship:** Silver Spirit (Silversea)

---

## Architecture

```
n8n Workflow (sW27watchV1abcd)
  │
  ├─ Schedule Trigger: cron 0 8 * * 1 (Monday 8 AM MDT)
  │
  ├─ Fetch All Sources (Code node)
  │   └─ 7 HTTP fetches with 15s timeout, graceful error handling
  │
  ├─ Parse Prices & Signals (Code node)
  │   ├─ JSON-LD price extraction (primary)
  │   ├─ Regex fallback (6 patterns)
  │   ├─ TA/interline signal detection (5 patterns)
  │   └─ FX rate parsing (EUR/USD)
  │
  ├─ Compare & Build Email (Code node)
  │   ├─ Week-over-week comparison via $workflow.staticData
  │   ├─ >5% threshold → ALERT banner
  │   ├─ HTML email assembly (D2M branding)
  │   └─ Writes payload to /tmp/silversea_report_payload.json
  │
  └─ Send Email (Code node + child_process)
      └─ Calls scripts/send_silversea_report.py
          └─ Gmail API via creds/gmail_token.json
              └─ FROM d2mconcierge@gmail.com TO johnloucks3@gmail.com
```

---

## Sources Monitored (7)

| # | Source | Type | What It Checks |
|---|--------|------|----------------|
| 1 | Silversea SL270505016 page | Price | Leg 1 per-person pricing |
| 2 | Silversea SL270521015 page | Price | Leg 2 per-person pricing |
| 3 | Silversea Deals page | Signal | Promotions, offers, discounts |
| 4 | Exchange Rate API | FX | EUR/USD live rate |
| 5 | CruiseCritic Silver Spirit | Signal | Ship ratings, reviews |
| 6 | Perx Travel / Interline Rate Desk | Signal | TA/interline rate availability |
| 7 | ID90 Travel | Signal | Interline cruise deals |

---

## Alert Thresholds

| Condition | Action |
|-----------|--------|
| Price change >5% week-over-week | Red ALERT banner in email, `[ALERT]` subject prefix |
| Price change <5% | Reported as normal WoW change |
| Source returns 404/error | Reported in "Source Issues" section (graceful degradation) |
| TA/interline rate signal detected | Listed in "Signal Detection" section |

---

## Files

| File | Purpose |
|------|---------|
| `workflows/silversea_spring2027_watch.json` | n8n workflow definition (imported via CLI) |
| `scripts/send_silversea_report.py` | Gmail API email sender (reads payload from JSON file) |
| `creds/gmail_token.json` | OAuth token for d2mconcierge@gmail.com (NOT synced to Drive) |

---

## n8n Instance Details

| Property | Value |
|----------|-------|
| Workflow ID | `sW27watchV1abcd` |
| n8n URL | https://n8n.d2mluxury.quest |
| n8n Service | `n8n.service` (system-level, User=john) |
| n8n Version | 2.12.3 |
| Database | `~/.n8n/database.sqlite` |
| API Key | Thunderbird MCP key (audience: public-api) |

---

## Week-over-Week Price Tracking

Prices are stored in `$workflow.staticData`:
```json
{
  "lastPrices": { "LEG1": 12500, "LEG2": 11800 },
  "lastRun": "2026-04-28T14:00:00.000Z"
}
```

First run establishes baseline. Subsequent runs compare against stored prices.

---

## Email Format

- **Header:** Navy (#1a237e) banner with week date and EUR/USD rate
- **Body:** Voyage pricing table, voyage details, signal detection table, sources list
- **Errors:** Amber warning box with source issues
- **Footer:** Next scan date, baseline status
- **Branding:** D2M stationery — Georgia serif, cream (#f7f3ea) background

---

## Maintenance

### Update Voyage URLs
When Silversea publishes Spring 2027 voyages, update URLs in the "Fetch All Sources" Code node via n8n UI at https://n8n.d2mluxury.quest.

### Deactivate
```bash
# Via API
curl -X POST -H "X-N8N-API-KEY: $API_KEY" \
  http://localhost:5678/api/v1/workflows/sW27watchV1abcd/deactivate
```

### Re-import After Edit
```bash
n8n import:workflow --input=/home/john/Thunderbird/workflows/silversea_spring2027_watch.json
# Then activate via API POST .../activate
```

### Check Execution History
```bash
# Via API
curl -H "X-N8N-API-KEY: $API_KEY" \
  "http://localhost:5678/api/v1/executions?workflowId=sW27watchV1abcd&limit=5"
```

---

## Deployment Log

| Date | Action | Result |
|------|--------|--------|
| 2026-04-25 | Initial deployment | Workflow imported, activated, 2 test emails sent successfully |
| 2026-04-25 | E2E test | 7 sources fetched (4 errors expected — voyages not published yet), email sent msgId=19dc44693730961c |

---

## Known Limitations

1. **Silversea voyage pages are JS-rendered SPAs** — static HTTP fetches may not capture dynamically loaded prices. JSON-LD and regex fallbacks attempt extraction; if both fail, reports "NOT_PARSEABLE."
2. **Spring 2027 voyages not yet published** — SL270505016 and SL270521015 pages currently return 404. Will auto-resolve when Silversea opens bookings.
3. **Perx/ID90 require authentication** — public pages checked for Silversea mentions only; full rate data requires logged-in scraping (future enhancement).

---

*Deployed 2026-04-25 | Hale, COS | Thunderbird Wing*
