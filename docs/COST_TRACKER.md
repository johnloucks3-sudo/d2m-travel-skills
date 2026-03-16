# D2M Cost Tracker — AI & Cloud Services
## Dreams2Memories Travel, LLC
### Last Updated: 2026-03-06

---

## Monthly Subscriptions

| Service | Plan | Cost/mo | Account | Notes |
|---------|------|---------|---------|-------|
| **Anthropic Claude** | MAX 5x | $100 | johnloucks3@gmail.com | Covers Desktop + Code CLI. No separate API key in use. |
| **Cloudflare** | Free | $0 | johnloucks3@gmail.com | Domain DNS + named tunnel |
| **Porkbun** | d2mluxury.quest | ~$1/mo | jl3d2m | Domain registration |

## API Services (Pay-per-use / Free Tier)

| Service | Tier | Cost | Key Location | Monthly Limit |
|---------|------|------|-------------|---------------|
| **Groq** | Free | $0 | thunderbird_api.py:62 | 30 req/min, generous free tier |
| **Amadeus** (flights) | Test/Free | $0 | amadeus_credentials.json | 500 calls/month |
| **Hotelbeds** (hotels) | Test/Free | $0 | hotelbeds_credentials.json | Test tier — limited |
| **Twilio** (WhatsApp/SMS) | Trial | $0* | thunderbird_whatsapp.py:16 | *Trial credit ~$15, verified numbers only |
| **Google Gemini** | Free tier | $0 | itinerary_finishing_pipeline.py:39 | Key: AIzaSyC2aU... |
| **Google Custom Search** | Free tier | $0 | Phase1_MVP.py:29 | 100 queries/day free |
| **Unsplash** | Free | $0 | itinerary_finishing_pipeline.py:64 | 50 req/hour |

## Google Cloud / Workspace

| Service | Type | Cost | Account | Notes |
|---------|------|------|---------|-------|
| **GCP Service Account** | Free tier | $0 | dreams2memories@d2m-python-pipeline.iam.gserviceaccount.com | Drive, Sheets, Docs API |
| **Gmail OAuth** | Personal Gmail | $0 | johnloucks3@gmail.com | OAuth Desktop app — free |
| **Google Calendar API** | Free tier | $0 | via service account | Free with Google account |
| **Google Apps Script** | Free | $0 | johnloucks3@gmail.com | HUD web app hosting |

## Credential Files (~/Thunderbird/)

| File | Service | Sensitive |
|------|---------|-----------|
| credentials.json | GCP Service Account | YES |
| gmail_oauth_credentials.json | Gmail OAuth client | YES |
| gmail_token.json | Gmail OAuth token (auto-refresh) | YES |
| amadeus_credentials.json | Amadeus flight API | YES |
| hotelbeds_credentials.json | Hotelbeds hotel API | YES |
| api_key.txt | Thunderbird API internal auth | YES |

## Hardcoded Keys (should migrate to env/files)

| Key | File:Line | Service |
|-----|-----------|---------|
| gsk_Ipik... | thunderbird_api.py:62 | Groq |
| AIzaSyC2aU... | itinerary_finishing_pipeline.py:39 | Google Gemini |
| AIzaSyD0Yr... | Phase1_MVP.py:29 | Google Custom Search |
| c521728142... | Phase1_MVP.py:30 | Google Search Engine CX |
| H2Uq72fU... | itinerary_finishing_pipeline.py:64 | Unsplash |
| ACdc4e7b... | thunderbird_whatsapp.py:16 | Twilio Account SID |
| 0ec0f993... | thunderbird_whatsapp.py:17 | Twilio Auth Token |

---

## Estimated Monthly Total

| Category | Est. Cost |
|----------|-----------|
| Claude MAX 5x | $100 |
| Domain (Porkbun) | ~$1 |
| APIs (all free tier) | $0 |
| Cloud (all free tier) | $0 |
| **TOTAL** | **~$101/mo** |

## Action Items
- [ ] Check Twilio trial credit balance (dashboard.twilio.com)
- [ ] Monitor Amadeus usage — 500/mo limit on test tier
- [ ] Consider moving hardcoded keys to .env file for security
- [ ] Check Google Cloud Console billing for any surprise charges (console.cloud.google.com)
