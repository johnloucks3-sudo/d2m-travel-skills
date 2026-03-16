# Thunderbird OS — Session Summary
## 2026-03-05 (Continued Session)

---

## What Was Built

### 1. Intel Scheduler (thunderbird_scheduler.py)
- APScheduler-based daemon running as systemd service `d2m-scheduler`
- **Schedule:** Morning Briefing 6:30AM, Tech Monitor 8AM, Ship Intel 5PM, Weekly Report Monday 7AM (all Mountain Time)
- Each job: runs sweep → saves JSON locally → uploads to Drive (Thunderbird_Intel) → creates Gmail draft
- Verified end-to-end: test sweep → Drive upload → Gmail draft created
- Fixed systemd 203/EXEC error (home dir permissions 700→711, switched to /usr/bin/python3.13 with PYTHONPATH)

### 2. Apps Script Salvage
- **thunderbird_fare_watch.py** — 5 MCP tools ported from AllegiantFareTracker.gs:
  - `fare_watch_add`, `fare_watch_check`, `fare_watch_list`, `fare_watch_history`, `fare_watch_remove`
  - Tracks flight/cruise/hotel prices, logs history, alerts on threshold breaches
  - Storage: `~/Thunderbird/data/fare_watches.json` + `fare_history.json`
- **thunderbird_ship_reference.json** — Salvaged from 68KB ship comparison Apps Script:
  - IMO numbers for 5 vessels (Silver Nova 9834629, Grandeur 9841216, World Navigator 9753750, World Traveller 9841419, World Voyager 9844146)
  - Full specs: tonnage, suite sizes, restaurant names, spa details, crew ratios
  - Alert email templates with tone guidance
- **Voice profile ingested** from Drive `EARA_Voice_Profile` doc + local `My Voice for EARA.docx`
  - Saved to `~/.claude/projects/-home-john/memory/voice_profile.md`
  - Note: Drive doc `127xvmk...` (Feb 19) is a Groq error dump, not a real profile
- MCP server now at **70 tools** (up from 53)
- Archived: createGoldStandardBrief.gs, generateItineraryFromSheets.gs, all duplicates

### 3. Thunderbird HUD v2 — Mobile Command Center
Three-layer architecture for Samsung Z Fold 6 Gmail integration:

**Layer 1: REST API Gateway (thunderbird_api.py)**
- FastAPI server on port 8766, systemd service `d2m-api`
- Groq Llama 3.3 70B (free tier) for AI summarization, draft replies, free-form queries
- Endpoints: `/api/ai/summarize`, `/api/ai/draft-reply`, `/api/ai/query`, `/api/send-to-evernote`, `/api/save-to-drive`, `/api/tool/{name}`, `/api/briefing`, `/api/fare-watches`
- API key auth via `~/Thunderbird/api_key.txt`

**Layer 2: Cloudflare Tunnel (d2m-tunnel service)**
- Quick tunnel exposes port 8766 over HTTPS
- URL changes on restart — check: `grep -oP 'https://[a-z0-9-]+\.trycloudflare\.com' ~/Thunderbird/tunnel.log | tail -1`
- Verified end-to-end from external URL

**Layer 3: Google Workspace Add-on (Apps Script)**
- `~/Thunderbird/workspace_addon/Code.gs` + `appsscript.json`
- Gmail contextual card: AI summarize thread, AI draft reply (D2M voice), contextual command window, save to Evernote/Drive, search similar
- Homepage HUD: command center query window, morning briefing, fare watches, ship/world/tech intel on demand
- AI draft reply → creates actual Gmail draft with one button
- Every result screen has To Evernote + To Drive export buttons
- Evernote sends to yodainva@gmail.com
- Drive saves to Thunderbird_Knowledge_Base by default
- Required additional OAuth scope: `https://www.googleapis.com/auth/script.locale`
- Test deployments only work on desktop; Android requires full Deploy > New deployment

---

## Files Created/Modified

| File | Action |
|------|--------|
| `thunderbird_scheduler.py` | Created (prior session) |
| `thunderbird_fare_watch.py` | Created — 5 MCP tools |
| `thunderbird_ship_reference.json` | Created — vessel database |
| `thunderbird_api.py` | Created — REST API + Groq AI |
| `workspace_addon/Code.gs` | Created — EARA-style HUD |
| `workspace_addon/appsscript.json` | Created — manifest with scopes |
| `workspace_addon/DEPLOY.md` | Created — deployment instructions |
| `deploy/d2m-api.service` | Created — systemd for API |
| `deploy/d2m-tunnel.service` | Created — systemd for tunnel |
| `deploy/d2m-scheduler.service` | Modified — fixed python path |
| `travel_mcp_server.py` | Modified — added fare_watch import/register |
| `api_key.txt` | Auto-generated — API auth key |
| `memory/voice_profile.md` | Created — John's email voice |
| `memory/MEMORY.md` | Updated — services, tool count |

---

## Running Services

```bash
systemctl status d2m-scheduler    # Intel reports on schedule
systemctl status d2m-api          # REST API + Groq AI (port 8766)
systemctl status d2m-tunnel       # Cloudflare tunnel to phone
```

---

## Pending / Next Steps

- **Named Cloudflare tunnel** or VPS for permanent URL (current quick tunnel URL rotates)
- **Android deployment** requires full Deploy > New deployment (not test)
- **learning.gs** — John mentioned this file but it doesn't exist locally or on Drive
- **Z Fold HUD enhancements** — could add client CRM lookup, booking pipeline triggers
- **Groq rate limits** — free tier is 6K TPM; if exceeded, consider Groq Dev Tier or switch to Gemini
- **VPS deployment** — SSE transport + API + tunnel scripts ready in `deploy/`

---

## Style Note
- John requested "more objective" tone — less filler, less emotional language, just facts and results
