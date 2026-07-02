# CI PROBE RESULTS — 2026-07-02
*Run: 2026-07-02 05:03 UTC | Engine: ci_daily_routine.py → ci_sweep.py → ci_health.py*
*Probed: 45 tools | Last_verified stamped: YES*

---

## SCORECARD

| Status | Count | % |
|---|---|---|
| RAZOR_SHARP | 31 | 68.9% |
| DULL | 11 | 24.4% |
| RED | 1 | 2.2% |
| REPLACE | 2 | 4.4% |
| UNKNOWN | 0 | 0% |

**Total probed: 45 | Streak: 0/7 | Cadence: DAILY (holds until 7 consecutive 100% days)**

---

## RED — Immediate Action Required

### MCP Server Registry
- **Status:** RED | probe=FAIL | 25ms
- **Detail:** No mcpServers configured in `~/.claude/settings.json` or `/home/john/Thunderbird/.mcp.json` — MCP access depends on plugins only (filesystem/playwright/sequential-thinking loaded via plugin mechanism).
- **Client-affecting:** No (internal tooling)
- **Fallback:** Manual MCP server config restore from CLAUDE.md
- **Action:** Whetstone to audit current MCP plugin configuration; determine if mcpServers block is needed or if plugin-based loading is now canonical. CI auto-repair attempted and failed (Telegram SSL timeout during page). Sterling notified.

---

## REPLACE — Keys/Commander Action Blocking (Not Operational Failures)

### Flight Fare Watch — Amadeus API
- **Status:** REPLACE | probe=FAIL | 3 consecutive failures
- **Detail:** No Amadeus watches checked in last 8h — `amadeus_fare_watch.py` may not be running in supertimer. 6 watches total, 0 ever checked.
- **Client-affecting:** PARTIAL — Centrav B2B (fare-watch-centrav) and ITA Matrix (fare-watch-ita) cover air pricing. Amadeus is the native API lane, not browser-dependent.
- **Active workaround:** DORMANT — awaiting Commander API keys (Amadeus prod keys). Not an ops failure; Commander action required.
- **Fallback:** Centrav B2B + ITA Matrix (both RAZOR_SHARP)
- **Action:** Commander provides Amadeus API credentials → Wing activates `amadeus_fare_watch.py` in supertimer.

### GitHub Actions CI/CD
- **Status:** REPLACE | probe=FAIL | 3 consecutive failures
- **Detail:** GraphQL error — cannot resolve repository `johnloucks3-sudo/thunderbird-os`. GITHUB_TOKEN likely expired or repo renamed.
- **Client-affecting:** NO (CI pipeline, not client path)
- **Active workaround:** DORMANT — awaiting valid GITHUB_TOKEN PAT.
- **Fallback:** Manual git push + local test run
- **Action:** Commander rotates GITHUB_TOKEN (valid PAT with repo scope) → Wing wires into secrets.

---

## DULL — Probe Passes But Registry Flags Incomplete

These 11 tools all passed their efficacy probes (probe=ok). DULL = registry metadata gap or active_workaround logged, not operational failure.

| Tool | DULL Reason |
|---|---|
| Headless AI Dispatch | Detail says RAZOR_SHARP but registry shows DULL (staleness flag in registry metadata) |
| Credential & OAuth Keepalive | `room_res_cookies` expired -0.4h ago (tightest credential) |
| Armed Overwatch | Probe passes — DULL from registry cadence gap |
| Email Handling | Last run 3h ago, 0 delivered (no gap); probe RAZOR_SHARP internally |
| Client-Path Canary | 3 tools eligible for graduation: d2m-gmail-send (day 17), lifecycle-email-generator (day 14), dossier-pii-writer (day 12) — all zero defects. Graduate immediately. |
| Supertimer Bot Health | 12 bots, 0 failure storms; Firefox firefox-1509. Probe RAZOR_SHARP. |
| Regent Portal Live Session | No timestamp in status file — no confirmed live session (MISSIONS 214/820 open) |
| Cloudflare Tunnel | Service active, d2mluxury.quest HTTP 401 (auth required — expected). GREEN. |
| Tailscale Mesh VPN | Running, 5 peers, self=yoga. GREEN. |
| Healthchecks.io | HTTP 200 on :8123. GREEN. |
| Infisical — Secrets Manager | HTTP 200 on /api/status. GREEN. Active workaround: secrets not yet migrated from file-based creds. |

---

## RAZOR_SHARP (31/45) — Confirmed Good

Portal Access · Web Fetch · Tech Scout · Dani Identity · Fare Watch Centrav · Fare Watch ITA · Competitive Intel APIs · Cruise Intel Cache · Klaviyo · LiteLLM Routing · Nominatim · OpenCode CLI · PII Governance · n8n · ttyd · Google Drive OAuth · Evernote Backup · Master Cruise DB · Reverie App · Qdrant Vector DB · Lifecycle Dossiers · Lifecycle TP Scheduler · Lifecycle Arc Router · Lifecycle Validations · Lifecycle Itinerary Generator · Travel Survey Generator · Booking Survey Generator · Cruise Proposal Engine · E-180 Excursion Trigger · Hotel Price Scan · Transfer Price Scan

---

## API REGISTRY (bonus — ran post-sweep)
- Total credentials: 20 | OK: 17 | Warnings: 3 | Errors: 0
- Warnings (pending/disabled — not active failures): Pinecone [DISABLED] · Duffel Flight Search [PENDING] · ElevenLabs TTS [PENDING]
- Sheets sync failed during run (API error writing api_registry_status.json to Drive — written locally at `config/api_registry_status.json`)

---

## IMMEDIATE FIXES NEEDED (priority order)

1. **Commander action — MCP Registry (RED):** Determine if mcpServers config block is still needed vs plugin-only loading. Whetstone audits, Hale decides.
2. **Commander action — Regent Portal cookies (DULL):** MISSIONS 819/820 still open. No live session confirmed. Contact window opens Jul 7 (McLeod FPD). Manual re-auth before Jul 7.
3. **Commander action — room_res_cookies expired** (inside credential-keepalive DULL): -0.4h expired. Refresh needed.
4. **Client-Path Canary graduations (DULL → can clear):** 3 tools at day 12-17 zero defects. Graduate per SO_TECH_VANGUARD_ELEVATION_20260621 §2a. Per Commander directive 2026-07-01 canary is Hale-advisory — Wing graduates all 3. [HALE EXECUTES]
5. **Commander action — Amadeus/GitHub keys (REPLACE):** Both blocked on Commander-provided secrets. Not time-critical today. Note for next session.

---

*Generated by Hale · ci_daily_routine.py · 2026-07-02 05:03 UTC*
*streak reset to 0 (was: unknown) · cadence: DAILY*
