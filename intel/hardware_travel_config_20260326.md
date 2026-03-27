# THUNDERBIRD HARDWARE & JAPAN TRAVEL CONFIG
**Captured:** 26 MAR 2026 · 03:54 UTC
**Standing Order:** COS background capture

---

## FLEET ROSTER

| # | Asset | Specs | Status | Configured Role |
|---|-------|-------|--------|-----------------|
| 1 | **YOGA** | Lenovo 17" AMD Ryzen 7, 1TB, OpenSUSE Tumbleweed | **PRIMARY — ACTIVE** | Thunderbird home. MCP :8765, REST API :8766, Telegram bots, all services. Runs 24/7 unattended during Japan trip. |
| 2 | **dv7** | HP Pavilion dv7 17", upstairs, plugged in | **STANDBY — CONFIGURABLE** | Currently mirrors EARA. Open for any config we want. Can serve as Thunderbird backup node or dev sandbox. |
| 3 | **Chromebook HP 14** | HP 14", plugged in, SSH cape installed | **STANDBY — SKELETON LOAD** | Candidate for skeleton client (SSH to YOGA + Claude CLI). Can be loaded before Japan. |
| 4 | **Z-Fold 6** | Samsung Galaxy Z-Fold 6 | **MOBILE — GOES TO JAPAN** | Primary C2 handset in Japan. Telegram, Claude mobile. |

---

## JAPAN TRAVEL CONFIGURATION

**Departure:** 10 APR 2026
**Return:** 11 MAY 2026
**Days prep remaining:** 15 (as of 26 MAR)
**Days YOGA unattended:** ~31

### What Goes to Japan
| Asset | Role |
|-------|------|
| **Chromebook HP 14** | Primary travel workstation — Claude CLI via SSH tunnel to YOGA |
| **Samsung Z-Fold 6** | C2 handset — Telegram, mobile Claude, alerts |

### What Stays Home (Must Run Unattended)
| Asset | Must-Have Services |
|-------|--------------------|
| **YOGA** | MCP server, REST API, Telegram C2 bot, Telegram Dani bot, cloudflared tunnel, systemd timers, rclone sync |

---

## PRE-DEPARTURE CHECKLIST (by 09 APR)

- [ ] Verify YOGA cloudflared tunnel stable (api.d2mluxury.quest)
- [ ] Verify all systemd services set to auto-restart
- [ ] Load Chromebook skeleton: SSH config → YOGA, Claude CLI, mosh, tmux
- [ ] Test Chromebook → YOGA SSH tunnel end-to-end
- [ ] Configure dv7 for any desired role (backup node / dev sandbox)
- [ ] Verify Telegram C2 bot responsive from Z-Fold 6
- [ ] Test MCP tools over tunnel from Chromebook
- [ ] Confirm UPS / power stability on YOGA for 31-day unattended run
- [ ] Set YOGA sleep/hibernate to NEVER
- [ ] Cloudflare tunnel watchdog active

---

## TERMIUS ALIAS CHEATSHEET (Tested — 26 MAR 2026)
14 aliases · 2-char · phone-ready · deployed on YOGA via Termius

| Alias | Action |
|-------|--------|
| `tc`  | Restart Telegram C2 + status |
| `ss`  | System status dashboard (all 4 services) |
| `tl`  | Telegram C2 logs (last 30 lines) |
| `ar`  | Restart API gateway |
| `mr`  | Restart MCP server |
| `tr`  | Restart tunnel |
| `ds`  | Dossier gap scan |
| `ib`  | Commander inbox sweep |
| `mb`  | Morning briefing |
| `ei`  | Email intel sweep |
| `ti`  | Tech intel monitor |
| `is`  | Innovation scanner |
| `dl`  | List all client dossiers |
| `dr`  | Read a dossier (e.g. `dr furlow`) |

**Status:** All 14 tested. Commander confirmed operational 26 MAR 2026.
**Primary use:** Z-Fold 6 + Chromebook → Termius → YOGA during Japan trip.

---

## NOTES
- dv7 is fully configurable — no constraints. Good candidate for Thunderbird warm-standby.
- Chromebook skeleton = lightweight: SSH, mosh, tmux, Claude CLI. No heavy local installs needed.
- Japan connectivity: hotel WiFi + Z-Fold 6 hotspot as backup for Chromebook.
- Alias sheet is the primary C2 interface from mobile — commit it to muscle memory before APR 10.

---

## D2M TRAVEL APP — PRODUCT VISION
**Captured:** 26 MAR 2026 · 04:06 UTC
**Framing:** Rick Steves' AI Travel Assistant · Cruise + Luxury Focus

### Design Philosophy
- **HUD Window** = always-on concierge chat (AI assistant) — primary interface
- **Accordion Panels** = progressive disclosure of tools/data — no clutter
- **Link-out, don't duplicate** — traveler already has Google Translate, WhatsApp on their phone. Connect, don't rebuild.
- **Split-window optimized** — Z-Fold 6 / large phone split screen. App lives in one pane, map/browser in the other.

---

### ARCHITECTURE: HUD + ACCORDION

```
┌─────────────────────────────────┐
│  CONCIERGE CHAT (AI HUD)        │  ← Always visible. Ask anything.
│  "What time does the ship dock?"│
└─────────────────────────────────┘
│ ▼ MINI-BRIDGE                   │  accordion
│ ▼ MEDICAL                       │  accordion
│ ▼ TRANSLATOR                    │  accordion (links Google Translate)
│ ▼ WHATSAPP                      │  accordion (link-out)
│ ▼ MY LINK                       │  accordion (user-defined)
│ ▼ [+ ADD PANEL]                 │  expandable
└─────────────────────────────────┘
```

---

### CAPABILITY SET (REVISED — 26 MAR)

| # | Capability | Notes |
|---|-----------|-------|
| 1 | **Itinerary Hub** | Ship, cabin, ports, dates, flights, transfers — single source of truth |
| 2 | **Mini-Bridge** | GPS ship position (Starlink), route trace, previous ports, wind/speed(mph)/course on world sector map |
| 3 | **CruiseMapper** | Embed or deep-link — identify ships seen at sea by position |
| 4 | **Shore Excursion Planner** | Compare, book, track excursions per port |
| 5 | **Packing & Customs Tracker** | What fits in carry-on, declaration alerts by country |
| 6 | **Concierge Chat** | AI assistant — dining res, ship questions, port intel, recommendations |
| 7 | **Medical Advice** | Symptom checker, nearest medical facility, ship doctor contact, travel insurance hotline |
| 8 | **Translator** | Link-out to Google Translate. Do NOT rebuild. |
| 9 | **WhatsApp** | Quick-link panel. Already on phone — no duplication. |
| 10 | **My Link** | User-defined. Could be ship webcam, hotel, family group chat, anything. |
| 11 | **Live Weather** | Port-by-port, sea conditions, storm alerts |
| 12 | **Document Vault** | Passport, visa, insurance, booking confirms — offline accessible |

---

### MINI-BRIDGE DETAIL
The ship awareness panel — luxury traveler's version of the bridge:
- **Position:** Real-time GPS lat/long → plotted on world sector map
- **Route trace:** Ports visited (breadcrumb), next port bearing
- **Speed:** Knots → converted to mph display
- **Course:** Compass heading
- **Wind:** Direction + speed
- **CruiseMapper link:** "What ship is that on the horizon?" → tap → identify
- **Starlink note:** Most Silversea/Regent/Seabourn ships now Starlink-enabled. Smooth data at sea.

---

### WHAT WE DO NOT BUILD
Per Commander's directive — do not duplicate average traveler's phone:
- ❌ Navigation app (Google Maps exists)
- ❌ Full translator (Google Translate exists)
- ❌ Messaging (WhatsApp/iMessage exist)
- ❌ Camera features
- ❌ Currency converter (countless apps exist — link out if needed)
We **connect** and **contextualize** — we do not rebuild.

---

### DUAL-MODE ARCHITECTURE (Added 26 MAR · 04:13 UTC)

**The app has two primary modes — context-aware, auto-switched or manual toggle.**

---

#### 🌊 AT-SEA MODE — Command Center
When ship is underway or Commander is aboard:
- Mini-Bridge is **prominent / elevated**
- Ship position, speed, course, wind = primary real estate
- Dossier data surfaced: cabin, dining, port arrival times
- Concierge chat (Dani) always accessible
- Weather + sea state panel active

```
┌───────────────────────────┐
│  MINI-BRIDGE (prominent)  │  ← GPS, speed, course, wind
│  CONCIERGE CHAT (Dani)    │  ← Always present
│  ▼ EXCURSIONS             │  accordion
│  ▼ DINING / SHIP SCHEDULE │  accordion
│  ▼ DOCUMENT VAULT         │  accordion
│  ▼ MEDICAL                │  accordion
└───────────────────────────┘
```

---

#### 🗺️ ON-LAND MODE — Explorer Interface
When in port, city, or touring:
- Accordion menus organized by traveler intent:
  - **TRAVELING** — flights, transfers, logistics
  - **TOURING** — excursions, guided options, shore highlights
  - **EXPLORING** — spontaneous discovery, restaurant finder, CruiseMapper for ships in harbor
  - **EXPERIENCING** — dining res (OpenTable), cultural context, Dani recommendations
- Mini-Bridge collapses to status strip (ship is docked — position still shown)
- Concierge chat (Dani) always accessible

```
┌───────────────────────────┐
│  CONCIERGE CHAT (Dani)    │  ← Always present
│  ▼ TRAVELING              │  accordion
│  ▼ TOURING                │  accordion
│  ▼ EXPLORING              │  accordion
│  ▼ EXPERIENCING           │  accordion
│  [mini-bridge strip]      │  ← collapsed, ship status only
└───────────────────────────┘
```

---

### DOSSIER INTEGRATION
- All trip data **pre-loaded into app** from D2M dossier system
- No manual entry by traveler — itinerary, cabin, flights, excursions, contacts pulled automatically
- Dossier = the app's brain. Update dossier → app updates.
- Works offline (cached) — critical for at-sea or poor connectivity

---

### DANI — ALWAYS ON
- **Dani is permanently available** in both modes — not hidden behind a menu
- Backed by **full Thunderbird MCP suite**: live flight data, weather, excursion search, restaurant booking, ship intel, document vault
- Voice input: speak to Dani naturally — "What time do we dock in Civitavecchia?" → she knows because the dossier is loaded
- Fallback: if Dani is offline → static dossier data still accessible

---

### VOICE-FIRST OPTION
- **Minimal-button interface** as alternative UX mode
- Commander's preference: execute most functions by plain voice
- "Book a table at a seafood restaurant near the port tonight" → Dani executes
- "What's our speed?" → Mini-Bridge responds via voice
- Designed for Z-Fold 6 one-handed, at-sea, gloves-off luxury travel

---

### DEVELOPMENT VECTOR
**Platform:** Web app (PWA) — works on Z-Fold 6, Chromebook, any browser
**Split-window:** Designed for Z-Fold 6 wide mode + Chromebook dual-pane
**AI Backend:** Thunderbird MCP / Dani / concierge@d2mluxury.quest
**Ship data:** CruiseMapper API + MarineTraffic + NOAA weather
**Dossier source:** D2M Thunderbird dossier system → pre-loaded at trip start
**Voice engine:** TBD (native browser speech API / Whisper / ElevenLabs)
**Status:** ACTIVE DEVELOPMENT — Target: McLeod/McGlasson Jun 23 Silver Muse embark

---

## D2M TRAVEL APP — DEPLOYMENT ARCHITECTURE
**Captured:** 26 MAR 2026 · 04:18 UTC · Commander directive

### WHERE IT LIVES: 3-LAYER CLOUD

**LAYER 1 — FRONT DOOR (free)**
- Cloudflare Pages → `app.d2mluxury.quest`
- PWA static shell (React + Vite build)
- Global edge CDN, SSL auto-managed via existing CF account
- Zero cost

**LAYER 2 — BRAIN (~$10/mo)**
- *Hetzner CX21 VPS* (2vCPU / 4GB RAM — $7/mo)
- Python FastAPI backend (subset of Thunderbird API)
- Dossier data stored/served here — NOT YOGA-dependent
- Magic link auth (reuse existing `portal/server.py` code)
- SQLite → Supabase free tier for session/preference data
- 24/7 guaranteed uptime. Independent of home ISP.

**LAYER 3 — INTELLIGENCE (YOGA, existing)**
- Thunderbird MCP suite via Cloudflare tunnel → `api.d2mluxury.quest`
- VPS calls YOGA on demand (Dani, live flights, weather, excursions, dining)
- Graceful fallback: if YOGA down, static dossier data serves from VPS
- $0 incremental — existing infrastructure

### TECH STACK

| Component | Tech | Host | Cost |
|-----------|------|------|------|
| Frontend | React + Vite + PWA manifest | Cloudflare Pages | Free |
| Backend | Python FastAPI | Hetzner CX21 | ~$7/mo |
| Database | SQLite → Supabase free | VPS / Supabase | Free |
| Auth | Magic link (portal code reuse) | VPS | Free |
| Domain | app.d2mluxury.quest | Cloudflare (existing) | Free |
| AI/MCP | Dani + full MCP via YOGA tunnel | YOGA (existing) | $0 incremental |
| Ship data | CruiseMapper embed + NOAA API | CDN / NOAA | Free |
| Voice | Browser Speech API (Phase 2) | Client browser | Free |
| **TOTAL** | | | **~$7-10/mo** |

### USE CASE — MCLEOD / McGLASSON PILOT

**Client:** Erik McLeod & Melissa McGlasson
**Trip:** Silver Muse Mediterranean · Suite 617 · Voyage SM260623010
**Dates:** Jun 23 – Jul 3, 2026
**Route:** Rome (embark Civitavecchia) → multiple ports → Venice (Fusina disembark)

**Pre-loaded data (Day 1 — no manual entry by client):**
- Suite 617 · Silver Muse · all port arrival/departure times
- Flights: UA 177 (3D/3F), AC 817 (3A/4A), AC 1041 (2A/2C)
- Rome pre-cruise hotel (Baglioni area) + transfer options
- Venice departure: Stucky → Airport Boat Terminal (confirmed sequence)
- Rome & Florence excursion picks (Erik/Melissa starred GYG list, 10% discount flag)
- Dining priority: Venice seafood (top priority per Commander notes)
- Open item: Fusina → Stucky water taxi (research in progress)

**Killer demo moment (Fusina disembark, Jul 3):**
> Dani surfaces automatically: "Your ship has docked at Fusina. Water taxi direct
> to Stucky dock confirmed — meeting point at Fusina Gate B. Your bags are being
> offloaded. You have 2h 14min before VCE departure."

This is the moment they show every person on the ship.

### BUILD TIMELINE — 11 WEEKS TO JUN 23 EMBARK

| Phase | Window | Deliverable |
|-------|--------|-------------|
| Infra + shell | Apr 1–7 | VPS provisioned, PWA deployed, auth live, domain up |
| Dossier loader | Apr 8–14 | McLeod data auto-populates from D2M system |
| At-Sea Mode | Apr 15–28 | Mini-Bridge, ship position, NOAA weather live |
| Dani chat | May 1–10 | Concierge chat interface → MCP connected |
| On-Land Mode | May 11–20 | Accordion menus — Traveling/Touring/Exploring/Experiencing |
| Document Vault | May 21–31 | Offline PDFs, passport backup, offline caching |
| Commander beta | Jun 1–10 | Commander tests post-Japan return |
| McLeod handoff | Jun 12–20 | Magic link sent, onboarding call, walk-through |
| **EMBARK** | **Jun 23** | **Erik & Melissa board with app live** |

**NOTE:** Commander is in Japan Apr 10 – May 11. Phases 1-3 build is autonomous — wing executes.
Beta test window: Jun 1-10 (post-return).

---

## DEPLOYMENT DECISION — 26 MAR 2026 · 04:26 UTC

**Commander selected: OPTION 2 — Cloud-hosted, travel with him, Telegram-modifiable.**

Implications:
- App lives at `app.d2mluxury.quest` — accessible from Z-Fold 6, Chromebook, anywhere with browser
- Commander modifies app features, dossier data, and config **via Telegram C2 while in Japan**
- Wing deploys, Commander directs remotely — no Chromebook coding required in-country
- Telegram becomes the C2 interface for app iteration during travel

---

## CAPABILITY SET v4 — JOURNEY JOURNAL (Added 26 MAR · 04:26 UTC)

### Integration #3 — MAP / PHOTO / NOTES (Journey Journal)

**Problem Commander identified:** Serious travellers keep notes, but it's hard to maintain. Linking video + location + notes is powerful but fragmented across apps.

**Solution: Journey Journal** — built into the app as a native panel.

#### CORE CONCEPT
Every moment in a specific place can be linked:
```
[Video/Photo] ←→ [GPS Pin on Map] ←→ [Note(s)]
```
Tap a pin → see the photo + video you shot there + the note you wrote.
Tap a note → jump to the map location where you were.

#### JOURNAL MODES

| Mode | Trigger | Content |
|------|---------|---------|
| **Ad Hoc Capture** | Tap "+" anywhere in app | GPS auto-tagged. Add photo/video link, type note. 15-second minimum friction. |
| **End of Day Debrief** | Push notification at 8 PM (Commander-set time) | "How was today?" — structured or free-form. Day summary, highlights, regrets, what to do tomorrow. |
| **Port Entry Auto-Note** | App detects ship has docked at new port | Pre-populates: port name, date/time, weather, dossier excursion info. Commander adds impressions. |

#### DATA MODEL (per entry)
```
Journey Entry {
  timestamp: ISO 8601
  location: { lat, lon, name }        ← GPS auto-captured
  port_or_city: string                ← from dossier if at sea / port
  photo_links: [ URL, URL ]           ← link to phone camera roll / Google Photos
  video_links: [ URL ]                ← same — link-out, don't duplicate storage
  note: markdown text
  tags: [ "dining", "must_return", "ship", "shore" ]
  mood: optional emoji / 1-5 stars
}
```

#### MAP VIEW
- World/regional map with pins at each captured location
- Pin color = mode (green=ad hoc, blue=EOD, orange=port auto)
- Tap cluster → expand entries from that location
- Time-slider: replay the journey day by day
- Links to same map layer as Mini-Bridge (route trace)

#### WHAT WE DO NOT BUILD
- ❌ Camera — stays in phone camera app. We link, not capture.
- ❌ Video storage — Google Photos / iCloud already exist. We index, not store.
- ❌ Social sharing — this is a personal journal, not Instagram

#### WHY THIS WINS
Serious travellers already want to do this — pen-and-paper, Notes app, Instagram stories, all fragmented. This unifies location + media + words in one trip-aware context. At trip end: exportable as a travel memoir PDF with map and photos embedded.

---

### UPDATED ACCORDION STRUCTURE

**ON-LAND MODE** (adds Journal to Experiencing):
```
┌───────────────────────────┐
│  CONCIERGE CHAT (Dani)    │  ← Always present
│  ▼ TRAVELING              │  accordion
│  ▼ TOURING                │  accordion
│  ▼ EXPLORING              │  accordion
│  ▼ EXPERIENCING           │  accordion
│  ▼ JOURNEY JOURNAL        │  accordion ← NEW
│  [mini-bridge strip]      │  ← collapsed
└───────────────────────────┘
```

**AT-SEA MODE** (adds Journal to primary panels):
```
┌───────────────────────────┐
│  MINI-BRIDGE (prominent)  │  ← GPS, speed, course, wind
│  CONCIERGE CHAT (Dani)    │  ← Always present
│  ▼ EXCURSIONS             │  accordion
│  ▼ DINING / SHIP SCHEDULE │  accordion
│  ▼ JOURNEY JOURNAL        │  accordion ← NEW (EOD debrief prompt at sea)
│  ▼ DOCUMENT VAULT         │  accordion
│  ▼ MEDICAL                │  accordion
└───────────────────────────┘
```

---

### TELEGRAM MODIFICATION INTERFACE (NEW — 26 MAR)

Commander modifies the app from Japan via Telegram C2:

**Available Telegram commands (to be built):**
```
/app status          → Current build status, feature flags
/app note [text]     → Create a journey note from phone (GPS attached)
/app eod             → Trigger EOD debrief prompt now
/app feature [name] on|off  → Toggle feature flags remotely
/app dossier reload  → Pull fresh dossier data from YOGA
```

This means: Commander in Kyoto can tap Telegram, dictate a note, and it appears in the Journey Journal geotagged to Japan. The app evolves with him on the ground.

---

## STANDING ORDER — DANI BOT UNLOCK FOR COMMANDER (26 MAR 2026)

**Commander directive:** Wire dani_bot channel to accept Commander (Yoda) as a direct user.

### Current State
- dani_bot = client-facing only. Dani replies to clients via COS review gate.
- Commander communicates via **Telegram C2 bot** (separate channel).

### New State — Post-Unlock
- **dani_bot channel: unlocked for Commander.**
- Commander can talk directly to Dani on the dani_bot channel — same Dani the clients use.
- This is the **AI chat layer** for the travel app experience.
- Commander uses dani_bot to test Dani, simulate client experience, and interact while traveling.
- COS review gate: **bypassed for Commander** — he IS the Commander. Direct line to Dani.

### Build Task
- [ ] Detect Commander's Telegram user ID on dani_bot channel
- [ ] If sender = Commander (Yoda / johnloucks3 Telegram ID), route directly to Dani — no COS gate
- [ ] Dani responds to Commander with full MCP access (same as client mode)
- [ ] Log all Commander ↔ Dani conversations to session memory (same as client transcripts)
- [ ] Commander can use `/switch` or tap to toggle between C2 bot and Dani bot

### Why
- Travel app AI chat layer IS Dani
- Commander must be able to dogfood the exact Dani experience clients get
- Japan: Commander uses dani_bot as primary AI companion — not C2 bot — for trip intelligence

---

## OA PORTAL — DUPLICATION DECISION (26 MAR 2026)

**Commander directive:** Do NOT duplicate OA client portal by default. They have itinerary, bookings, vault.

### Decision Matrix

| Feature | OA Portal Has It | Build in D2M App? |
|---------|-----------------|-------------------|
| Itinerary | ✅ Yes | ❌ No — link out |
| Bookings | ✅ Yes | ❌ No — link out |
| Document Vault | ✅ Yes | ❌ No — link out |
| Mini-Bridge / Ship Position | ❌ No | ✅ Build |
| Dani Concierge Chat | ❌ No | ✅ Build |
| Journey Journal | ❌ No | ✅ Build |
| Shore Excursion Compare | ❌ No | ✅ Build |
| Medical / Translator | ❌ No | ✅ Link-out |

### Road-Use Consideration
Commander flagged: **MAY want to duplicate OA portal on the road** (itinerary + bookings + vault).
- Rationale: OA connectivity not guaranteed in Japan / at sea
- Decision: **Hold** — evaluate at Commander beta (Jun 1-10)
- If OA portal proves unreliable at sea → offline-cache itinerary + bookings in D2M app
- Keep offline dossier data in Document Vault as fallback (already planned)

### Action
- [ ] Test OA portal connectivity on Z-Fold 6 from Japan (hotel WiFi + ship WiFi)
- [ ] If OA offline >2x → escalate to Commander → build offline mirror
- [ ] Decision point: Commander beta Jun 1-10
