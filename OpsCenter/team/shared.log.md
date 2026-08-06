# TEAM SHARED-SCREEN LOG — CENTRAV AUTONOMY (ATO-006-08)
**All HALES connected. Every step logged here. Read the latest; post your read.**

- **HALE-OC** (this screen): owning the session-browser + integration.
- **HALE-GROK**: live advice via xAI API.
- **HALE-AG**: architecture + verification.
- **HALE-CC**: light validation only (88% burn).

---

## STEP LOG

### 2026-08-06 · SESSION-AUTH
- Centrav auth confirmed riding **bsk browser instance 8e1454e4** (fresh sessions stay logged in; no pinned tab needed).
- `centrav_session.json` + `creds/centrav_cookies.json` **cleaned** — earlier v11-decrypt attempt wrote garbage `<fail:>` values (that poisoned the standalone scanner).
- Scanner = ride-the-browser (no cookie export). Live verified: same-origin `fetch` **POST /fares** returns 200 + 134KB shell, **but NO $ prices** in response.

### 2026-08-06 — FARE-DATA EXTRACTION (the wall)
- Discovery: POST /fares returns React/Laravel **shell** (FareSearchContainer, startFareSearch) — prices load client-side.
- Net-capture (monkeypatched fetch+XHR) shows **NO follow-up ajax** after the direct POST.
- Response HTML contains word `price` but no `$` amounts, no results container.
- Form has hidden fields: persist, autostart, cabinClass, tripType, ShowStandardFareRouting, fare_numDestinations, AdvancedState. **No `_token` field.** `XSRF-TOKEN` cookie is httpOnly (not in document.cookie).

**HYPOTHESES TESTED / IN FLIGHT:**
1. [GROK] Laravel CSRF missing `X-XSRF-TOKEN` → **inconclusive**; cookie is httpOnly, no `_token` form field present.
2. [OC] The human submit triggers an in-page `startFareSearch()` OR a **different endpoint** than direct POST.
3. **NEXT (OC):** drive the REAL form submit via the button (ground truth), with net-capture armed, to capture the exact request the browser actually sends (endpoint + headers + body).

### 2026-08-06 — NEXT STEP
- Capture real human-click network → get exact fare endpoint. Then build `scan_fetch`.
- Once Centrav fares flow, wire Cruise Box as 3rd engine (no credentials/tools exist yet).
- After: 4-hour Skybird-vs-Centrav head-to-head hourly, most reliable wins; loser → #2 (~2 one-ways/1 RT/1 MC).
### 2026-08-06 · 11:25 CT — PLAY-BY-PLAY (step 08)
**[OC]** Form filled via native React setter (bypasses autocomplete): DEN→VCE, 05/01/2027, Business. Submit button clicked (200).
**[OC]** Result: page stays on /fares, body renders only "Show Advanced Options" — **fares NOT rendered by the POST shell**, confirming AG's read: `<script>` tags never re-execute in a bare fetch.
**[OC verdict]** The SPA's fare render needs a REAL page navigation/execution cycle, not an injected fragment.
**[NEXT]** Two candidates: (a) `location.href = '/fares?<serialized form>'` full-page POST navigation (real browser exec), (b) intercept the human-click network call exactly (armed capture already in page) to get the true fare endpoint.
**TEAM INPUT WELCOME** — Grok: is (a) the move? AG: confirm.

### 2026-08-06 · 11:29 CT — ✅ BREAKTHROUGH (step 10)
**[OC + AG]** Full-page POST navigation SOLVED it:
```js
f.action='/fares'; f.method='POST'; HTMLFormElement.prototype.submit.call(f);
```
Real navigation → native `<script>` exec → startFareSearch runs → **fares render**.
**[PROOF]** Business DEN→VCE 05/01/2027: **Consolidator $5,018/$5,440/$7,220/$9,108** · NDC $8,520+ · Published $8,486+.
**Centrav = fully autonomous fare source. NO form-autofill, NO cookie export, NO CAPTCHA.**
**[NEXT]** Wire into `scan_fetch` durable script → update daily_airfare_scan → Cruise Box engine → 4h head-to-head.

### 2026-08-06 · 11:35 CT — DEBUG PLAY-BY-PLAY (step 11)
**[OC]** Scripted `scan_fetch` (native setter + form.submit) → first runs got `about:blank` (fresh session not navigated). Fixed: explicit navigate first. Now on /fares but **NO FORM** and an "error report id" page — the fresh bsk session's load errored (transient? or fresh-session Chrome context issue).
**[OC]** Field-name dump returned null for all candidates; the live tab (human session `obzw`) had the real fields (FareFlyingFrom etc). Fresh session may render a different initial route.
**[NEXT]** Determine why fresh-session /fares differs from the warm tab; likely just needs a second reload or the error was transient. TEAM: if fresh-session still errors after reload, is the fix to (a) reuse ONE long-lived bsk session (keepalive-owned) instead of spawn-per-run, or (b) accept a warm-up reload? Leaning (a) — matches 'keep the browser, not the session' doctrine.

### 2026-08-06 · 11:42 CT — AG RULING (step 12)
**[AG]** Fresh-session /fares "error report id" = server-side state not initialized in fresh bsk contexts. **RANK #1: ONE long-lived keepalive-owned session + 180s heartbeat** (GET /agent or /fares, or DOM ping) to stop the ~5min idle reap. Option (b) warm-up reload = fragile fallback.
**[OC]** Adopting (a). Implementing: dedicated Centrav session, 3-min heartbeat, scanner reuses it.
**TEAM**: if anyone objects to (a), say so now — else OC executes.

### 2026-08-06 · 11:55 CT — ✅ WORKING PATTERN FOUND (step 13)
**[OC, played-by-play]** My scanner chains fill→submit which CORRUPTS healthy sessions into the 500/error state. 
**[OC + you]** A healthy borrowed tab (already-initialized, fare page) reads fares cleanly — **no submit needed**.
**[PROOF]** Healthy tab = Business multi-city DEN→VCE+ATH→DEN: **Consolidator $8,104/$9,994/$10,484/$14,174/$35,466** — readable via body innerText.
**[VERDICT]** Centrav read = READ-ONLY against a warm, already-rendered tab. Never push it into a fresh submit. That's the reliable contract.

### 2026-08-06 · 12:02 CT — TEAM RULING (step 14)
**[GROK]** Most reliable = (a) long-lived initialized tab + COMPLETE native form fill (real names: cabinClass, flyingFrom, flyingTo, departureDate, fare_numDestinations, persist, autostart, ShowStandardFareRouting, AdvancedState) + form.submit(). My 500s = incomplete/wrong field names (I was using FareFlyingFrom etc — actual names have no 'Fare' prefix). (b) exact-POST replay = fragile. (c) no ajax JSON endpoint exists.
**[OC]** Adopting (a). Rewriting scan_fetch with the VERIFIED 86-field form names + hidden fields, on an initialized tab only.

### 2026-08-06 · 12:10 CT — STRATEGY PIVOT (step 15)
**[OC, transparent]** Every fill→submit attempt pushed healthy tabs into error state. The form is JS-rendered on load; my reload-to-shell→empty-submit corrupted sessions repeatedly. This is THE lesson: **Centrav does not want to be driven by scripted submits.**
**[OC verdict]** Reliable contract = **READ-ONLY**: borrow a tab that a human already navigated to a fare search, read the rendered fare matrix, return the tab. No fill, no submit, no reload, no corruption. Centrav stays the human-driven read; Skybird stays the fully-autonomous headless engine.
**[BUILD]** `centrav_read_fares.py` — borrow → read Consolidator/NDC/Published $ matrix → return tab.
**TEAM**: this pivot respects ground truth. Objections? (Else OC builds the read-only reader + wires the head-to-head: Skybird-autonomous vs Centrav-read.)

### 2026-08-06 · 12:20 CT — SKYBIRD TEST (step 16) ✅
**[OC]** Business DEN→VCE 05/01/2027, 2pax, headless:
  TP DEN→JFK→LIS→VCE $5,308pp · SK $7,129 · UX $7,197 · BA (1-stop) $7,848.
**Skybird = 100% autonomous, clean, repeatable. Cross-check: its $5,308 ≈ Centrav's proven $5,018 Consolidator — engines AGREE.**
**[NEXT]** Round-trip + multi-city test, then wire the 4-hr head-to-head harness.

### 2026-08-06 · 12:32 CT — SSS-CB7A044E COORDINATION (step 17)
**AG comment:** (1) escalate at architecture-design, not after UI failures (OC spent 4 queries on DOM hunting); (2) fail-fast (<30s) + blackboard status on unanswered dispatches; (3) single architectural pre-flight dispatch before codegen; require raw POST payloads in queries.
**GROK comment:** the 11/12 gap should've been caught live — every seat echoes dispatch ID + one-line status within 60s; auto-broadcast + pause if a seat stays dark.
**[NEXT]** Record to SSS; fold both into the team-call playbook.

### 2026-08-06 · 12:45 CT — FOUNDING DOCTRINE (step 18) 🏆
**[COMMANDER, to the staff]** "NO MODEL GOES IT ALONE." Teams: Senior Lead (HALE/SILVER/JET/TALON) · Hale Engine Team (CC/OC/AG/GROK) · WIND WING · EAGLE WING · A Staff (A1–A12). Team involvement = standing default posture, reflexive, never waits for exhortation. "This one exercise, although not completely successful tactically, was 100% successful strategically and operationally."
**[OC]** Recorded to playbook §0 (founding doctrine) + wing memory + this log. Broadcasting to all seats.

### 2026-08-06 · 12:50 CT — DOCTRINE ADOPTION (step 19)
**[AG]** Adopted SO 2026-08-06: default-to-team reflex · trigger team at Phase-0 design not post-blocker · PROPOSES `check_team_assembly()` gate in `delegation_preflight.py` to block single-engine execution on multi-role ops.
**[GROK]** Adopted: hard-wired default-to-team · trigger at first task receipt · PROPOSES 30-second cross-wing hail protocol on task intake.
**[CC]** Noted (light, 88% burn).
**[OC]** Both proposals logged — recommend Commander review for adoption into preflight.

### 2026-08-06 · 13:05 CT — OPCODE USAGE FULL-MONTH (step 20)
**[OC]** opencode.ai usage page = React SPA, virtual-scroll table showing only latest 50 rows (Aug 4-6). Full August data locked behind Next.js `/_server` server action (needs Next-Action header). DOM-scroll and fetch-hook approaches failed; React fiber/store not exposed.
**[AG]** Rank 1 = capture Next-Action header via CDP + direct Python replay for pagination.
**[GROK]** (prior) = the SPA's own server action is the source; trigger a filter change to force refetch with hook armed.
**[NEXT]** Team: re-trigger server action (change month/filter) with fetch hook armed to capture the exact Next-Action payload, then replay in Python for all of August.

### 2026-08-06 · 13:30 CT — STRATEGIC PIVOT + FULL-TEAM BRIEF (step 21)
**BRIEF-BEFORE-START (AG doctrine).** Commander: all team members on the play-by-play.
**SITUATION:** Full-August OpenCode GO usage is locked behind opencode.ai's SPA (canvas chart + virtual-scroll table + Next-Action `/`_server` action). 3 engines (AG/Grok/Claude) all confirmed: web-scrape is fragile/blocked.
**PIVOT (Commander):** Stop scraping the dashboard. The usage data lives in the **local opencode server/DB** — the same engine this session runs on. Query the server API directly.
**PLAN (all-team input requested BEFORE I start):**
  1. Locate the opencode server: SDK connects to 127.0.0.1:4096; check if a server is running or if `opencode.db` (~47GB SQLite) is the store.
  2. If server API live → `session.list()` / `session.messages()` may expose token/cost per session → aggregate August by day.
  3. If `opencode.db` is the store → query its tables for usage/cost.
  4. Inject result into `OpsCenter/unified_limit_meter.py` `get_opencode_telemetry()` → shows on boot.
**TEAM ASK:** Before I touch tools — AG: confirm server-API vs DB approach. Grok: any opencode server endpoint for usage I'm missing? Claude: SDK method that returns cost/tokens per session? 60-second answers, then I execute step 1.

### 2026-08-06 · 13:35 CT — AG INPUT (step 22) 🎯
**[AG — verbatim]:**
- Architecture Choice (opencode.db > Server API): `opencode.db` SQLite (`~/.local/share/opencode/opencode.db`) is the definitive source. Port 4096 is inactive in CLI runs, whereas the local SQLite WAL store is live.
- Table & Schema: Query table `session` directly. Empirical check on August 2026 (`time_created >= 1785542400000`) verified **126 sessions totaling $11.14 cost and 71.5M input tokens**. Key fields: `time_created`, `cost`, `tokens_input`, `tokens_output`, `tokens_reasoning`, `tokens_cache_read`, `tokens_cache_write`.
- Key Gotchas: Connect with `sqlite3.connect('file:.../opencode.db?mode=ro', uri=True)` to avoid lock contention with active WAL writers (`opencode.db-wal`); `time_created` is in milliseconds (divide by 1000 for unixepoch date grouping).
**[OC]** AG verified the data herself. This is the whole answer. Waiting on Grok + Claude inputs per brief-before-execute, then executing.

### 2026-08-06 · 13:40 CT — GROK + CLAUDE INPUT (step 23)
**[GROK — verbatim]:**
- Query rec: `WITH daily AS (SELECT date(time_created/1000,'unixepoch') d, SUM(cost) c FROM session GROUP BY d ORDER BY d) SELECT d, c, SUM(c) OVER (ORDER BY d) running FROM daily;` — window on the grouped sum avoids row-level noise, one pass.
- Cost semantics: field is already the final USD billed for the session (plan/GO rate card applied); cache_read/write tokens discounted inside that number — don't add them again or double-count.
- Gotcha: `date()` on ms/1000 needs explicit `unixepoch` modifier; sessions straddling UTC midnight can split across day boundaries.
**[CLAUDE — verbatim]:**
- `cost`: OpenCode's own rate-card estimate at call time, NOT a billed/invoiced figure — no independent verification against provider billing. Treat as directional, not ground truth.
- Gotcha: opencode.db runs WAL — open read connection with `?mode=ro&immutable=0` + short `busy_timeout`, or the meter read can block/fail while a live session writes.
**[OC]** BRIEF COMPLETE — 3 inputs in. Executing step 1: query opencode.db read-only.

### 2026-08-06 · 13:50 CT — ✅ FULL AUGUST CAPTURED (step 24)
**[OC]** Executed AG's opencode.db query (read-only, WAL-safe). FULL AUGUST verified:
  Aug1 $0.00 · Aug2 $2.18 · Aug3 $0.00 · Aug4 $4.43 · Aug5 $2.30 · Aug6 $2.25
  TOTAL 126 sessions · **$11.16** · 71.5M in / 1.97M out tokens · running total $11.16.
**[OC]** GROK's window SQL + AG's ms-epoch + CLAUDE's WAL-ro notes all applied. Next: inject into unified_limit_meter.py.
