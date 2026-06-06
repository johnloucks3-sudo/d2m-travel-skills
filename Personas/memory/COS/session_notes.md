# COS Session Notes
Running log of session insights, observations, and context.

### 2026-03-21 16:54 UTC
[decision] STANDING ORDER — D2M Email Build Protocol (2026-03-21):
1. Concept → iterate until facts are right (bullets)
2. EXEC converts to bullets in Commander's voice
3. Commander approves final — paragraphs/bullets NUMBERED for easy dictation (e.g. "change 3", "kill 7")
4. COS sends

Goal: codify into autonomous send pipeline. Queue discipline: all pending docs send FIRST, then new drafts.
Commander callsign: Yoda. Established via Telegram C2 2026-03-21.

### 2026-03-22 14:26 UTC
[decision] STANDING PRINCIPLE (Commander, 2026-03-22): D2M does NOT take credit for what it did not do. The accurate framing of D2M's value: "Once the direction is clear or the decision is made, we provide options." Applied to Furlow group — clients chose the cruise, assembled their own group, Regent chose the hotel, ports were predetermined, clients booked their own flights. D2M contributed: port/excursion research, options presentation, data recording and organization, itinerary image downloads. All final decisions were the clients'. This principle applies to ALL future AI capability descriptions and client-facing materials.

### 2026-03-22 23:05 UTC
[decision] STANDING ORDER AMENDMENT — EMAIL SEND GATE (22 MAR 2026): Commander amended the send gate. The Wing MAY send to johnloucks3@gmail.com — this address is considered internal/within the wing, no vulnerability. Prohibition on sending to ANY other outside address remains fully in force. Original order issued 21 MAR 2026.

### 2026-03-24 13:55 UTC
[decision] STANDING ORDER 2026-03-24: Morning Intelligence Brief — two permanent changes ordered by Commander:
1. LINKS STANDARD — every article, source, and data point in the morning brief MUST include a clickable hyperlink. No exceptions. This is not optional formatting — it is required content.
2. REGENT + VIKING ADDED — Regent Seven Seas and Viking (river + ocean) are now explicitly tracked in the daily intel sweep alongside Silversea, Cunard, Oceania, Seabourn, AmaWaterways, and Ponant. Route changes, deployments, promotions, and news for both lines must appear in the CRUISE INTEL section of every brief.

### 2026-03-27 13:27 UTC
[preference] STANDING ORDER 27 MAR 2026 — Report Format Standard: JSON format used in World Intel and Tech Intel briefs is now the standard for ALL reports. Commander confirmed "well done" on that format. Apply to: morning briefs, intel sweeps, incubator digests, sitreps, innovation briefings, world intel reports, tech monitor outputs. Full send to johnloucks3@gmail.com (no drafts in d2mconcierge for intel/briefs).

### 2026-06-05 17:16 MT [auto-monitor]
[heartbeat] SESSION=IDLE | TOKEN=STALE (7208s old) | INBOX_PENDING=8 | ACTIVE_TASKS=0 | QDRANT=DOWN

### 2026-06-05 17:16 MT [MISSION-111-FOLLOWUP — Capability Audit + Infrastructure Repair]

[directive] Commander ordered: improve HALE memory persistence, organizational/planning ability, project oversight, build/project staying time. HALE+ELON+Dembe+Sterling exercise.

[infrastructure] OPUS model correction: 4.8 does not exist. Canonical model = claude-opus-4-6.

[fix] auto_session_monitor.sh was MISSING for 2.5 months (since ~Mar 2026). Service was failing every 10 min with status 203/EXEC. Created script at OpsCenter/auto_session_monitor.sh. Now fires correctly. Monitors: session processes, token freshness, inbox pending, mission board tasks, Qdrant health.

[fix] Qdrant vector memory server was NOT running. Docker image was present (qdrant/qdrant:latest). Started container with persistent storage at data/qdrant_storage/. Systemd service created: ~/.config/systemd/user/qdrant.service (enabled, auto-start). Initial index: 221 files, 448 chunks, ~142K tokens estimated.

[audit-elon] 10 underexploited systems found: Qdrant semantic memory (now fixed), Mem0 shared memory (built, unconnected), persona memory dirs (stale since Mar 27), commander directive sweep (inactive), session checkpoint (built, not wired), mission board (0 tasks), 4 MCPs installed but not in mcp.json (apify/foursquare/mapbox/yelp), multi-agent framework (unused), hale substrate chain (unused), context7 MCP (wired, unused).

[audit-dembe] mem0ai v1.0.5 already installed. qdrant-client v1.17.1 already installed. 4 MCP servers in mcps/ (apify, foursquare, mapbox, yelp) downloaded but not configured. Commented-out travel MCPs: skiplagged, kiwi, trivago, ferryhopper, airbnb, ticketmaster.

[active-projects] 
  - Bryana onboarding (drafts in drafts/bryana_*.html)
  - Spencer Grand Tour flight deadline Jun 10 (T-5)
  - Nichols TP 0.5 due today
  - McLeod departure Jun 18 (T-13)
  - Loucks Dossier Atlas Mediterranean 2027

[model-routing] Opus = claude-opus-4-6. No 4.7 or 4.8 exists.

[next-session] Mission board has 0 tasks — needs population. Inbox has 8 PENDING/UNREAD items. Qdrant now searchable — use memory_search MCP tool for context retrieval.

### 2026-06-05 17:26 MT [auto-monitor]
[heartbeat] SESSION=IDLE | TOKEN=STALE (7809s old) | INBOX_PENDING=8 | ACTIVE_TASKS=0 | QDRANT=DOWN

### 2026-06-05 17:31 MT [auto-monitor]
[heartbeat] SESSION=IDLE | TOKEN=STALE (8135s old) | INBOX_PENDING=8 | ACTIVE_TASKS=56 | QDRANT=UP

### 2026-06-05 17:36 MT [auto-monitor]
[heartbeat] SESSION=IDLE | TOKEN=STALE (8409s old) | INBOX_PENDING=8 | ACTIVE_TASKS=56 | QDRANT=UP

### 2026-06-05 17:37 MT [auto-monitor]
[heartbeat] SESSION=IDLE | TOKEN=STALE (8493s old) | INBOX_PENDING=8 | ACTIVE_TASKS=56 | QDRANT=UP

### 2026-06-05 17:38 MT [auto-monitor]
[heartbeat] SESSION=ACTIVE (1 procs) | TOKEN=STALE (8520s old) | INBOX_PENDING=8 | ACTIVE_TASKS=56 | QDRANT=UP

### 2026-06-05 17:46 MT [auto-monitor]
[heartbeat] SESSION=ACTIVE (1 procs) | TOKEN=STALE (9013s old) | INBOX_PENDING=8 | ACTIVE_TASKS=56 | QDRANT=UP

### 2026-06-05 17:56 MT [auto-monitor]
[heartbeat] SESSION=ACTIVE (1 procs) | TOKEN=STALE (9615s old) | INBOX_PENDING=8 | ACTIVE_TASKS=58 | QDRANT=UP

### 2026-06-05 18:06 MT [auto-monitor]
[heartbeat] SESSION=ACTIVE (1 procs) | TOKEN=STALE (10216s old) | INBOX_PENDING=9 | ACTIVE_TASKS=66 | QDRANT=UP
