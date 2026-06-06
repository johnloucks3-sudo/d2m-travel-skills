---
name: silversea-ta
description: "Silversea TA portal API access: session management, voyage pricing, per-category availability. Triggers on: silversea, silversea TA, silver nova price, silver muse price, silversea availability, silversea rate, TA portal silversea, silversea booking"
---

# /silversea-ta — Silversea TA Portal API Access

Discovered 2026-06-06. Fully reverse-engineered. Pure `requests` library — no browser needed for pricing reads.

## Architecture

The Silversea TA portal (`my.silversea.com`) runs an ASP.NET Core backend with a LANSA booking engine embedded in an iframe (`/re/lansa.html`). The booking engine exposes a clean REST API at `/re/api/` that returns JSON with live TA pricing and availability.

**Auth mechanism:** Session cookies only — no Bearer token needed for read operations.
- `myssid` = ASP.NET session token (Session-scoped, server-side, refresh via login)
- `ASP.NET_SessionId` = secondary session cookie
- `CF_VERIFIED_DEVICE_*` = Cloudflare device verification (expires 2027-07-01 — guard this)

## Credentials & Files

| Item | Location |
|---|---|
| Credentials | `config/portal_creds.json` → key `silversea` |
| Cookie file | `~/.playwright/cookies_silversea.json` |
| Scraping intel | `scraping_intel/silversea.json` |
| Session state | `OpsCenter/state/silversea_session.json` |
| Cookie refresh daemon | `scripts/silversea_cookie_refresh.py` |
| Full scraper | `scripts/silversea_ta_scraper.py` |
| Metronome health | `OpsCenter/metronome.py` → `_check_silversea_api_session()` |

**Agency code:** 179350 (Nexion LLC / Travel Leaders Network)
**Agent ID:** 32995587

## Key API Endpoints

All endpoints base: `https://my.silversea.com/re/api/`

### 1. Voyage List with Pricing

```
GET /re/api/voyages?CurrencyCod=USD&FareCod=S3%23U3&MarketCod=FT&PageNum=1&PageSize=50&Published=Y
```

**Filter parameters:**
- `SailDateFrom=YYYY-MM-DD` / `SailDateTo=YYYY-MM-DD` — date range
- `CabinCategoryCod=CV` — specific cabin category (see category codes below)
- `FareCod=S3` — single fare code, or `S3%23U3` for multiple (URL-encoded `#`)
- `Published=Y` — live voyages only

**Returns per row:** `VoyId`, `VoyCod`, `MinFare` (pp), `Voydays`, `SailDate`, `ShipCod`, `CabinCategoryCod`, `Availability`, `FareCod`, `SpecialOffer`, `TcDesc`

**Availability values:** `OK` = open, `FEW` = limited, `GTY` = guarantee only, `OUT` = sold out

### 2. Session Health Check

```
GET /re/apix/get/Params
```
Returns `{"Role": "Travel Agent", "IndividualId": "32995587", "AgencyCod": "179350", ...}`
If session dead → 401 or redirects to login.

### 3. Agency Info

```
GET /re/api/agencies?AgnCod=179350
```

### 4. My Bookings

Navigate to `https://my.silversea.com/MyBookings` — scrape with Playwright.

## Ship + Cabin Category Codes

Source: `https://my.silversea.com/re/json/shipCabinCategories.json`

### Silver Nova (ShipCodWings = SN)
| Code | Category |
|---|---|
| VI | Vista Suite (no veranda) |
| CV | Classic Veranda Suite |
| SV | Superior Veranda Suite |
| DX | Deluxe Veranda Suite |
| PV | Premium Veranda Suite |
| ME | Medallion Suite |
| PM | Premium Medallion Suite |

### Silver Muse (ShipCodWings = SM or MU)
| Code | Category |
|---|---|
| VI | Vista Suite |
| CV | Classic Veranda |
| SV | Superior Veranda |
| DX | Deluxe Veranda |
| ME | Medallion Suite |

### Silver Moon (ShipCodWings = MO)
Same as Muse: VI, CV, SV, DX (no Medallion).

## Fare Codes

| Code | Description | Notes |
|---|---|---|
| U3 | All-Inclusive Fare | Standard TA bookable rate |
| S3 | All-Inclusive Plus Fare | Upgraded (premium drinks, Wi-Fi, excursion credit) |
| TA | Travel Agent Fare | ~60% below rack — often OUT or GTY only |
| T5 | Interline (UK/EU/AP only) | ~55% below rack — rarely available |
| LM | Last Minute Savings | Check when within 90 days of departure |
| SP | Special Fare | Promo-specific |

**The ★SPECIAL flag** on a voyage means an active promotion exists on silversea.com. The TA portal shows rack rate; the promotion must be applied separately at booking. Call Silversea Group Desk with voyage code to confirm promo applicability for the booking.

## Standard Pricing Pull — Python Pattern

```python
import requests, json
from pathlib import Path

COOKIE_FILE = Path.home() / ".playwright" / "cookies_silversea.json"
cookies_raw = json.loads(COOKIE_FILE.read_text())

session = requests.Session()
for c in cookies_raw:
    domain = c.get("domain", "").lstrip(".")
    if domain and ("silversea" in domain or "cloudflare" in domain):
        session.cookies.set(c["name"], c["value"], domain=domain, path=c.get("path", "/"))

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, */*",
    "Referer": "https://my.silversea.com/re/lansa.html",
    "X-Requested-With": "XMLHttpRequest",
}

# Pull all categories for a specific voyage
voy_cod = "SN270505010"
cats = [("CV","Classic Veranda"),("DX","Deluxe Veranda"),("SV","Superior Veranda"),
        ("PV","Premium Veranda"),("ME","Medallion Suite"),("PM","Premium Medallion")]
fares = ["U3","S3","TA","T5","LM"]
date_from, date_to = "2027-05-05", "2027-05-06"

results = []
for cat_cod, cat_name in cats:
    for fc in fares:
        url = f"https://my.silversea.com/re/api/voyages?CurrencyCod=USD&FareCod={fc}&MarketCod=FT&PageNum=1&PageSize=20&Published=Y&SailDateFrom={date_from}&SailDateTo={date_to}&CabinCategoryCod={cat_cod}"
        r = session.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            data = r.json()
            voy = next((v for v in data if v.get("VoyCod") == voy_cod), None)
            if voy and voy.get("MinFare"):
                results.append({
                    "cat": cat_name, "fare": fc,
                    "pp": voy["MinFare"],
                    "avail": voy.get("Availability"),
                    "special": bool(voy.get("SpecialOffer"))
                })

results.sort(key=lambda x: x["pp"])
for r in results:
    print(f"{r['cat']:<25} {r['fare']}  ${r['pp']:,}pp  {r['avail']}")
```

## Session Refresh

Session expires when `myssid` server-side session dies (hours to days). Refresh:

```bash
python3 scripts/silversea_cookie_refresh.py
# OR
python3 scripts/silversea_ta_scraper.py --check
```

The refresh script auto-runs daily at 05:00 via `thunderbird-silversea-session.timer`.

## Metronome Health Check

`_check_silversea_api_session()` in `OpsCenter/metronome.py`:
- Runs every tick (5 min), deduped daily
- Probes `/re/apix/get/Params` for `Role: Travel Agent`
- Alerts to relay (D2M Channels) — not D2MC2C
- Also monitors CF_VERIFIED_DEVICE expiry (30-day warning)

## Why Each Site Is Different

| Portal | Auth method | Anti-bot | Cookie TTL | Notes |
|---|---|---|---|---|
| Silversea my.silversea.com | OIDC → ASP.NET session | Cloudflare (CF_VERIFIED_DEVICE bypasses) | Hours–days | REST API fully open with session cookies |
| Regent rssc.com | ASPXAUTH cookie | Akamai | ~72h | Firefox-only; headless Chrome blocked |
| Viking viking.com | Azure B2C | Standard | N/A | Consumer account only — no TA portal yet |

Each site requires independent cookie harvesting and a site-specific refresh daemon. The `scraping_intel/` directory is the registry — one JSON file per portal documenting login flow, selectors, and API endpoints.
