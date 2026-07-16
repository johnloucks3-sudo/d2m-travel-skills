
## Morning Intel Brief - Airline Route Monitoring Sweep (URGENT - Communication Failure)

**Timestamp:** 2026-06-27T01:40:22.926910

Commander,

Roger — Completed the two-step airline route monitoring sweep as directed. Below is a summary of the findings:

**1. Airline Route Change Scan & Client Impact Analysis:**

*   **Articles Scanned:** 24
*   **Route Change Articles:** 24
*   **Client Impacts Detected:** 9
*   **Critical Impacts:** 9

**2. Client Impacts Detected:**

Critical impacts were detected for the following clients related to route changes and news impacting their tracked airports (SEA and DEN) and relevant airlines:

*   **Westbrook, Ron & Lindy (Silver Nova Trans-Pacific Apr 23–May 11):** 3 critical impacts related to Seattle (SEA) airport and United, Delta, Alaska, and American Airlines.
*   **Loucks, Justin & Ryan:** 6 critical impacts related to Denver (DEN) airport and Alaska Airlines.

**3. Telegram Alert Status:**

Wilco — Attempted to send immediate Telegram alerts for the detected client impacts. However, the alert function failed with the error: `Telegram alert failed: No module named 'thunderbird_telegram'`.

**Action Taken:** The full details of the impacts, including all 9 critical alerts, have been logged to `/home/john/Thunderbird/output/airline_alerts.json` for your review.

**URGENT - Communication System Failure:**

This brief is being delivered to `OpsCenter/collaboration/blackboard.md` because both direct email sending (via `gmail_send_as_persona`) and Gmail draft creation (via `gmail_create_draft_sync` due to an unexpected `persona_id` argument) have failed. The `thunderbird_telegram` module is also missing, preventing Telegram alerts.

I will prioritize investigating and resolving these critical communication pathway issues immediately.

Thanks,

Hale

<!-- COMMANDER-READY:START -->
## COMMANDER-READY (2026-07-16 15:30 UTC)
### Last 24h decisions (0)
- (none)

### Open P0/P1 nags (10)
- [P0] MCLEOD-2984034-FPD-TRIGGER
- [P0] MISSION-COMMANDER-196-CALL
- [P1] MCLEOD-SILVER-MUSE-WELCOME-HOME
- [P1] MCLEOD-2984034-TP11-SEND
- [P0] LOUCKS-3122006-FPD-ALERT
- [P1] MISSION-802-ITINERARY-BUILD
- [P1] MISSION-802-FORMAT-REVIEW
- [P1] SCANDI-PORTAL-REVIEW
- [P0] SCANDI-PORTAL-SEND
- [P0] MISSION-317-SPENCER-CALL-REMINDER
- (none)

### Blockers (0)
- (none)

### Startup hook
## STATE BRIDGE BRIEFING — 2026-07-16 09:30

### Since last session (2026-07-16 15:00:01 → still open)

**Recent commits (no in-DB delta — showing git log):**
- `bd41dbacd` docs(kuklinski): log passive-disengagement relationship note  _67 minutes ago_
- `b6d4ad39d` feat(email-intel): client self-sufficiency signal detector  _67 minutes ago_
- `838f079bb` fix(telegram): fleet-wide flood suppression — mute list + cooldown dedup  _70 minutes ago_
- `02738c8df` fix(oom): rewrite fix_memory_ceilings.sh generator to per-unit layout  _2 hours ago_
- `00f45f122` feat(delegation): cross-Hale task-delegation design + Phase-0 routing library  _2 hours ago_

_No changes since last session — continuing clean._

### Current state snapshot
**Most recently touched watched files:**
- `hale_state.json` (53s ago)
- `OpsCenter/collaboration/blackboard.md` (30m ago)
- `dossiers/GROUP_Kuklinski_VikingMars_Panama_Dec2026_TRACKER.md` (1.1h ago)
- `hale_brief.md` (1.1h ago)
- `dossiers/Nichols_Regent_3078056.md` (1.1h ago)
- `dossiers/Westbrook_SilverNova_Personal.md` (1.1h ago)
- `dossiers/grandeur_group_logistics_matrix_20260702.md` (1.1h ago)
- `dossiers/McLeod_Erik_Melissa_SilverMuse_Complete.md` (1.1h ago)

**Mission board:** 83 open (7 P0, 53 P1)
  - 🔴 MISSION-001: Resolve Regent cookie expiration — restore session access
  - 🔴 MISSION-011: Close Regent cookie expiration P0 — restore session access
  - 🔴 MISSION-033: Close Regent cookie P0 — restore authenticated agent-portal session
  - 🔴 MISS
<!-- COMMANDER-READY:END -->

## Block 5 — Nichols Draft + McLeod TESS Verify (2026-07-16)

**TASK 1 — Nichols follow-up draft (DRAFT ONLY, not sent):**
Created Gmail draft ID `r-3125559690830503669` (johnloucks3 account, Dani/A3 persona) to Larry Nichols (larry.nichols4811@gmail.com, CC heidi.nichols1@yahoo.com). Subject: "Quick check-in — Stockholm transfer ahead of your Aug 16 payment." Warm, low-pressure check on the ARN→At Six Stockholm sedan 3-bag capacity concern raised 2026-07-13, ahead of the Aug 16 final transfer payment. No send — staged for Commander review/approval.

**TASK 2 — McLeod TESS verification (REAL FINDING, not assumed):**
Verified booking 2984034 (TESS internal BookingID 2256103, TripID 1631588) via `tess_get_booking`/`tess_get_trip`/`tess_search_bookings`. Result: `PaymentsAndItemizations.Itemizations = []`, `ReceiptCount=0`, `PaymentCount=0`, `ActualPackagePrice == PackagePrice` ($13,398.00 — no discount/credit line anywhere on the booking).

**Finding: the $200 Regent FCC is NOT recorded or applied against booking 2984034 in TESS.** It exists on the Regent/Pavlus side (Gale Hotel complaint, Dec 2025, per Erik McLeod's Jul 13 forwarded documentation) but has never been entered into TESS or confirmed linked to this booking.

Updated `dossiers/McLeod_Grandeur_LesserAntilles_Dec2026_TRACKER.md` (FCC row status, open-items table, action-item checklist) and logged the finding to MISSION-044 on the mission board. **The staged FCC confirmation draft (r6302915235413543112) remains BLOCKED — do not send it as-is**, since it promises confirmation that isn't real yet. Next step (not done here, not a send): Harlan or whoever holds the Pavlus/Regent contact needs to either book the $200 credit into TESS against 2984034 or get written Regent/Pavlus confirmation, before FPD Jul 22 (6 days out).

Side note flagged for Harlan/Block 2 (commission recon): TESS `PackagePrice` ($13,398.00) doesn't match the Jul 13 invoice Grand Total ($12,948.00) — a $450 gap, consistent with the already-logged balance-delta pattern on this booking. Not resolved here — flagged for the commission-reconciliation pass.

Files: `dossiers/McLeod_Grandeur_LesserAntilles_Dec2026_TRACKER.md`, `OpsCenter/mission_board.json` (MISSION-044 log entry). Committed `3056d154`.

## Block 4 — Scandinavia Itinerary Prep (2026-07-16)

**Status: WF-17 HELD. Nothing sent to Furlow, Ely-Darrow, or Nichols. MISSION-618 NOT marked complete.**

**Task 1 — PDF regen (DONE):** Regenerated `cruises_web/itinerary_grandeur_{furlow,elydarrow,nichols}.pdf` from the current Jul-16 HTML via weasyprint (the Jul-16 builder `scripts/build_grandeur_baltic_itineraries.py` emits HTML only, no PDF path — regen was a direct weasyprint render of the current HTML). Render-verified with `pdftoppm`: route-map SVG renders correctly with all 5 port markers, gold `#c8a400` brand color present, ship photo displays, per-couple segregation confirmed (no cross-couple names/data). 6 pages each.

**Task 2 — Deliverable format (CRITICAL FINDING):** PDF is **not** the real client-send channel. `config/client_portals.json` + the Furlow dossier's `SCANDI-PORTAL-SEND` reference confirm the actual deliverable is the live per-couple portal (`furlow`/`elydarrow`/`nichols`.d2mluxury.quest, served from `output/Grandeur_Scandinavia_Portal/*/html/index.html` by `scripts/client_portal_server.py`). **That portal HTML is dated 2026-07-03 and does not contain this mission's own Jul-16 rebuild fixes** — confirmed by direct diff: the live portal HTML has zero occurrences of the route-map SVG or the `#c8a400` gold brand color that the Jul-16 `cruises_web` rebuild added to fix MISSION-618's original bug report (wrong-subject images, off-canon brand, no route map). **MISSION-618's own stated goal — "rebuild via Pexels search→view→verify pipeline before any client send" — is not actually satisfied at the real send surface.** The fix landed in `cruises_web/` (an artifact that isn't linked from the portal and has no confirmed downstream consumer) but not in the portal that's actually gated to send 2026-07-20. Recommend a distinct **PORTAL-RESYNC ticket** run through the JET→TALON→Hale dual-brain pipeline (`output/Grandeur_Scandinavia_Portal/PLAN.md`) before that date. Did **not** attempt this resync myself: (1) out of this block's commit scope, (2) a naive HTML copy-over would bypass the `SCANDI-PORTAL-REVIEW` QC checklist that specifically guards Amy Ely-Darrow's Parkinson's/medical-detail segregation, so it needs the full reviewed pipeline, not a shortcut.

**Task 3 — Regent port narrative (FLAG WAS STALE):** RSSC's own official port-catalog copy for Warnemünde/Copenhagen/Kristiansand/Oslo already exists in the repo (`validations/rssc_scrape/extracted_port_details.json`, sourced from `ports_catalog_full.json`, captured live 2026-07-14/15) — contra MISSION-618's own "S2 narrative partial — no Regent scraped port pages" flag. Did not inject it verbatim: the current `cruises_web` HTML narrative (port_data notes + factbook intel, per-port "intel-content" expandable sections) already reads as strong, and RSSC's own official Kristiansand (port code KRS) copy contains a genuine content typo — it describes "Kristiansund" (a different, more northerly Norwegian city) instead of Kristiansand. Confirmed via the raw catalog entry: `id: KRS, name: Kristiansand, longName: "Kristiansand, Norway"` but `description` text says Kristiansund throughout — this is RSSC's own website error, not a scrape artifact. Flagging so nobody later copy-pastes that description into client copy.

**Task 4 — Dossier reconciliation (DONE, read-only):** Reconciled the 3 individual dossiers against `GROUP_Grandeur_Scandinavia_Aug2026_TRACKER.md` item #7 ("HOLD until final COS version confirmed"). No evidence anywhere in the repo that a "final COS version" was ever confirmed since the tracker was wired 2026-06-09 — the HOLD is still technically open, so **individual dossiers were not overwritten.** Suites match exactly across all 3 couples; Ely-Darrow and Nichols insurance status match between tracker and dossier. **One real conflict found and corrected:** the tracker's blanket "Travel insurance (incl. CFAR): MOOT — all 3 couples (declined/closed)" line is wrong for Furlow — the Furlow dossier documents an active, still-open Chase Sapphire Reserve card-benefit partial-coverage gap (no standalone policy), explicitly flagged internally as "Commander should know... do not raise unprompted." Root cause: the tracker's insurance line appears to have over-generalized the Nichols-specific Commander arbitration (same 2026-06-09 date, "CFAR dropped, all 3 couples") onto Furlow's separate and still-open question. Corrected the tracker's own summary tables (not the dossier) to point back to the dossier as ground truth, and logged the full diff in the tracker's new reconciliation note.

**Task 5 — Kristiansand live-confirm (DONE, real source, not guessed):** Found and used an existing live RSSC portal capture (`validations/rssc_scrape/3071222_Furlow_deep.json`, captured 2026-06-02 from rssc.com) showing Furlow's confirmed excursion "Explore Kristiansand on Foot" dated **Sep 06, 2026, 10:00** — cross-confirmed by the Nichols and Ely-Darrow scrape captures, which both show "Kristiansand (1 Day(s) in Port)" as the day immediately before their Sep 7 Oslo excursions. This corrects the port_data file's prior inferred Sep 5 to the RSSC-confirmed Sep 6 — updated `dossiers/port_data/FurlowElyNichols_Grandeur_2026-08-29_ports.md` accordingly (day-slot table, confidence caveats, and data-sources section). Note: the current HTML/PDF already had this right ("Sep 6 · time TBC") — this task closed a gap in the port_data reference file, not the client-facing build.

**Files touched (commit scope):** `cruises_web/itinerary_grandeur_{furlow,elydarrow,nichols}.pdf` (regenerated), `dossiers/port_data/FurlowElyNichols_Grandeur_2026-08-29_ports.md` (Kristiansand correction), `dossiers/GROUP_Grandeur_Scandinavia_Aug2026_TRACKER.md` (item #7 status + insurance reconciliation note), `OpsCenter/mission_board.json` (MISSION-618 log entry — status left `in_progress`, not marked done/sent).

## Block 1 — C2 Fabric Delegation Wiring (2026-07-16)

Took the Phase-0 cross-Hale delegation library (`core/relay/task_delegation.py`) LIVE by binding it to the already-approved C2 Fabric bus (Gate-4 was a stale-header doc bug, not a real gate — confirmed `hale_decisions.md:6098`).

**Built:** `core/relay/delegation_wiring.py` — `delegate_mission()` validates the routing rationale via `route_task()` (validate-don't-manufacture: honest "direct assignment" / "routing validated" / "OVERRIDE" rationale, no fabricated task_type), fires `relay_handoff()` (read-only import of the PROTECTED `wing_relay.py`, best-effort), and mirrors the ticket lifecycle (`proposed→assigned→in_progress→pending_review→done/blocked`) onto `hale_bus_state.json` via `record_channel_event()` on the `console` channel (filterable by `ref=mission_id`). `certify_mission()` RAISES `DelegationError` on self-certification (certifier==assignee) or missing artifact (§3.5 anti-theater).

**Real wiring (not another unused building block):** `OpsCenter/mission_board_sync.py::add_mission()` now fires delegation when `assigned_to` is a real cross-Hale seat (CC/OC/AG) — persona-name/unassigned missions are untouched. Added a genuine caller: the `EXEC: delegate SEAT :: title :: criteria [:: PRIO :: task_type :: certifier]` CLI verb (`cmd_delegate` + `process_exec_command` branch). `cmd_complete()` now gates delegated-ticket completion through the cross-seat certifier check. Added a repo-root `sys.path` bootstrap so the bare CLI resolves `core.*`.

**Verified:** 13 regression tests pass (`tests/test_delegation_wiring.py`) — routing correctness, bus event written+read-back (both `c2_fabric_write` AND `c2_fabric_read` HALE_BUS_PATH monkeypatched to tmp, relay stubbed so no Telegram POST), cross-seat certifier rejection at both assignment and certify, CLI `delegate` verb end-to-end. Phase-0 self-test still 7/7. Ground-truth check: a bare (non-pytest) `process_exec_command("delegate OC :: ...")` wrote a real `delegation_assigned` event readable via `unified_visibility_brief()`.

**Anti-theater note:** seat delegation now REQUIRES `acceptance_criteria` (PDTAC "T") — `delegate_mission` raises without it. `certified_by` defaults to CC and must differ from the assigned seat.

Files: `core/relay/delegation_wiring.py` (new), `OpsCenter/mission_board_sync.py`, `tests/test_delegation_wiring.py` (new). Did NOT touch the protected `wing_relay.py` or other blocks' tickets.

---

## Block 7 — Web-Intel + AI SDK Integration (2026-07-16)

**Author:** Block-7 agent (Opus). Discipline: verify vs ground truth, honest real-vs-idea split. Commit `011144be2` (scoped to 6 files, gitleaks clean, 37 tests pass).

### 1. Camofox wired into escalation chain — REAL, TESTED ✅
- `core/web/smart_fetch.py`: added **Tier 4 = Camofox** (`http://127.0.0.1:9377`, REST stealth camoufox browser), opt-in via `allow_camofox_tier=True`, tried only after CloakBrowser (Tier 3) fails. `_run_camofox()` = start→open-tab→GET snapshot, with one auto-restart on `session_expired` (Camofox sessions are stateful and expire between calls — verified behavior).
- **Live-verified:** forced tiers 1–3 to fail, fetched `https://example.com` → `tier_used=4, status=200`, real snapshot content returned. Default path (no flag) confirmed to NOT invoke Camofox → offline tests stay hermetic.
- Opt-in (not always-on) on purpose: heavier + session-stateful; CloakBrowser remains the default escalation tier.

### 2. MISSION-629 free-text search gap — REAL FIX SHIPPED (different tool choice) ✅
- Root: anansi only does `fetch <URL>`; `fare_watch_centrav.py`/`hotel_scan.py`/`transfer_scan.py` passed raw NL queries → empty output. Correctly diagnosed last night as a dead end *in anansi's current form*. The plan's "different tool choice" is now built.
- Added `smart_fetch.search(query, engine="auto")`: **SearXNG** (`127.0.0.1:8890`, JSON metasearch) primary — **live-verified**, 18 real results for "cheapest flight COS to GRB September 2026" (Expedia/Kayak/Google links). CLI: `python3 -m core.web.smart_fetch --search "<query>"`.
- **Camofox `@google_search` macro fallback = UNVERIFIED / KNOWN-FRAGILE (honest correction).** On live test it was actually broken (opened `about:blank`, which Camofox rejects — "only http/https allowed"); fixed to open on an https URL, after which macro navigate 200s but `/links` extraction still returns empty and the stateful session churns (google.com tab-open intermittently `session_expired`). Labeled as such in code; it only ever fires behind SearXNG in `engine="auto"`. **SearXNG is the real fix; do not rely on the macro fallback standalone.**
- **NOT yet done (honest):** the 3 scan scripts are not yet rewired to call `search()` — that's a follow-up (touches Block 3/6 scan code). The tested primitive exists; wiring the callers + closing MISSION-629 is the remaining step.

### 3. Claude Agent SDK (Managed Agents) pilot — BLOCKED by TWO faults, both proven ⛔ (honest)
- Attempted a real run on the repo venv → `AttributeError: 'Beta' object has no attribute 'sessions'`.
- **Fault 1 — wrong SDK:** installed `anthropic==0.86.0` (requirements.txt pins `0.84.0`). Its `client.beta` exposes only `files/messages/models/skills` — **no `sessions`/`agents`/`environments`**. Module targets `0.111.0`.
- **Isolated-venv pilot (zero blast radius, per advisor):** `python -m venv` + `pip install anthropic==0.111.0` → the Managed Agents API surface **is present** (`environments`/`agents`/`sessions` all resolve). So the SDK path is real. Fired the real end-to-end run against the live API →
- **Fault 2 — no real API key (decisive):** the call reached Anthropic and returned **HTTP 401 `invalid x-api-key`**. `ANTHROPIC_API_KEY` in `.env` is a **literal placeholder — `sk-ant-dummy00...` (59 chars)**. A plain `messages.create` with it also 401s → the key is a dummy, not merely the managed-agents path. **No real managed-agent run is possible until a real key is provisioned (secrets work — explicitly OUT of scope today) AND the SDK is bumped.** The Jun 19–20 cache/ledger entries predate this dummy key.
- **Net:** the pipeline is **broken on two axes**, not "unused." This kills the `core/ci/self_observability.py` ci-fix-agent path the plan hoped would dodge the cgroup-kill race — it can't run at all here.
- **Did NOT upgrade** the repo SDK (0.86→0.111 = 25 releases across **67 anthropic importers** incl. Telegram C2/email voice/memory embeddings — high-risk shared-dep change; deliberate isolated session, not a burn window). Isolated venv was cleaned up.
- **Shipped:** preflight guard (`_require_managed_agents`) at `run_task`/`_get_or_create_environment`/`_get_or_create_agent` → clear actionable `RuntimeError` pointing callers at the `claude -p` fallback instead of a cryptic AttributeError. 4 regression tests. **Recommendation:** managed-agents cloud (cgroup-race sidestep) is a good idea, gated on BOTH a real API key AND an isolated SDK bump.

### 4. Gemini SDK health check — HEALTHY ✅ + safe allowlist expansion
- `core/gemini_bridge/mcp_function_bridge.py` bridge live: 14/14 `tests/test_gemini_bridge_safety.py` pass; `build_function_declarations()` builds 107 tool declarations; send/financial tools still blocked even when forced into the caller set (mechanism intact).
- **Added 4 read-only flight-search siblings** to `SAFE_ALLOWLIST` (`search_google_flights`, `search_kiwi_flights`, `kiwi_place_autocomplete`, `search_flights_flightaware`) — airport-code/date/pax params only, no PII/send/financial, direct peers of already-listed flight tools. Deliberately excluded `get_client_airports` (reads client dossiers/PII). Dated comment follows the file's own deliberate-expansion discipline.

### CDP (port 9222) evaluation — CAPABILITY CONFIRMED, honestly bounded
- Ground truth: 9222 not running; **no pre-existing CDP pattern in the codebase** (docs grep hits were false positives). Python `playwright` not installed; existing browser automation is Node (`tools/cloak/*.mjs`). Chrome 150 IS installed.
- **Capability test (real):** launched `google-chrome-stable --headless=new --remote-debugging-port=9222` on a throwaway profile → `/json/version` returned `Chrome/150` + live `webSocketDebuggerUrl` (the exact surface `connect_over_cdp` attaches to); page targets enumerable. Cleaned up (killed chrome, removed profile, 9222 closed). **The CDP plumbing works on this box.**
- **Honest bound (no overclaim):** the best human-gated candidate is Centrav (MISSION-001/011/033/037/046), but its blocker is **OTP/CAPTCHA = a genuine human-decision wall CDP does NOT defeat**. CDP's real value is driving a *real, already-authenticated* Chrome (human logs in once → attach headlessly, reuse the OTP-authenticated session, avoid "looks-automated" detection). That needs a persistent CDP-Chrome service + the human's real profile — infra + auth work, NOT stood up in this window. **Verified-viable capability, deferred as a scoped next step; does not "unlock every human-gated portal."**

### Net: now actually wired vs. still an idea
- **Wired + tested:** Camofox Tier 4; `search()` free-text (SearXNG); Gemini allowlist +4; managed-agents failure guard.
- **Good idea, deferred (honest):** rewire 3 scan scripts onto `search()` + close MISSION-629; managed-agents cloud pilot (needs BOTH a real `ANTHROPIC_API_KEY` — currently a dummy — AND an isolated SDK bump to ≥0.111.0); persistent CDP-Chrome session-reuse service (needs infra + human login); Camofox `/links` macro-search extraction (currently returns empty — SearXNG covers the need).

---

## Block 3A — Door County Dining + Excursion Plan (2026-07-16)

**Author:** Block-3A agent. Sibling to Block 3 (air/logistics) — did not touch flight/scraper files.

**Deliverable:** `dossiers/DoorCounty_Dining_Excursion_Plan_Sep2026.md` — real dining + excursion plan for John & Susan Loucks's Country House Resort trip, Sep 7–14, 2026. Live-verified (WebSearch, 2026) rather than assumed:

- **Fish boil:** White Gull Inn confirmed Wed/Fri/Sat/Sun only, $28.75/adult, (920) 868-3517 — still unbooked. Pelletier's (nightly, (920) 868-3313) noted as backup for other nights.
- **Wine trail, ranked by fit** (not an equal list): Stone's Throw (all-grape, closest to John's dry Cab/Malbec palate) > Simon Creek (broadest range, best shared-afternoon pick) > Orchard Country/Lautenbach's (cherry identity + Susie's whites) > Door Peninsula (free tours) > von Stiehl (Algoma, ~60-70 min south — flagged as a long-haul day trip, not a default stop, given the low-distance preference).
- **Fine dining:** CHOP live-confirmed open + reservable 2026 (closed Sundays — flagged so it isn't booked against Sep 13). Added Pearl Wine Cottage and La Sirena (both Ephraim) as additional culinary-fit options beyond what the dossier already had.
- **Excursions, mobility-flagged honestly:** Eagle Tower is the standout — verified fully ADA-accessible (850-ft ramp, ≤5% grade, 16 rest points), no-stairs alternative to the 100-step climb. Eagle Bluff Lighthouse grounds flat, but tower interior = stairs (optional). Cana Island flagged **partial/conditional** (causeway can flood, unpaved island paths, steep tower stairs) — not oversold as clean-flat. Washington Island Ferry accessibility **not confirmed** in research — flagged for Commander to verify directly with the operator, not asserted.

**Caught and fixed a real day-of-week bug:** verified via calendar calc that Sep 7, 2026 is a Monday (not the day the existing dossier's EXCURSIONS table assumed). White Gull's Wed/Fri/Sat/Sun boil nights are actually **Sep 9/11/12/13**, not the Sep 10/12/13 figure a same-day sibling edit had just introduced — corrected in `DOSSIER_DoorCounty_SisterBay_Sep2026.md` along with a pointer to the new plan doc. Also flagged the old sample flow's Cave Point kayak + 150-ft bluff hike as off-profile for the confirmed no-adventure/low-mobility preference (kept for history, struck through, not deleted).

**No purchases or reservations made.** All booking-required items (fish boil call, CHOP OpenTable link, wine tour add-ons, ferry accessibility check) flagged as Commander actions — this is the Commander's own trip, no WF-17 gate, but no financial commitment authority was exercised.

**Commit:** `8c4fb592` — scoped to the 2 dossier files only (other agents' concurrent dossier edits left untouched).

**File conflict note:** `DOSSIER_DoorCounty_SisterBay_Sep2026.md` was mid-edit by the Block 3 (air) sibling when this agent first read it — re-read before editing, no clobber.

---

## Nichols/Group Larger Vehicle Research (2026-07-16)

**Author:** Dani (A3), assigned by team-lead. Task: proactive alternative to the 3-separate-sedan ARN→At Six Stockholm transfer for the Grandeur group (Furlow 3071222, Ely-Darrow 3096289, Nichols 3078056), triggered by Larry Nichols' 2026-07-13 luggage-capacity flag.

**Real pricing found (Kiwitaxi, live scrape, ARN→Stockholm City, Aug 27 2026, 6 pax):**
| Vehicle | Cap (pax/bags) | Price/vehicle (net) |
|---|---|---|
| **Minibus 7PAX ("Best Choice")** | 7 / 7 | **$130** |
| Minibus 10PAX | 10 / 10 | $244 |
| Comfort (current sedan class) | 4 / 3 | $99 |

**Current sedan cost (real, from Project Expedition Hold-w/o-Payment reminder emails — not estimated):** PE184710612 (Furlow), PE184711812 (Ely-Darrow), PE184712212 (Nichols) — all three **$132.13 each = $396.39 total**, client-facing price, due Aug 16. Each sedan capped at 3 bags — the exact number Larry Nichols flagged as short 2026-07-13.

**Comparison:** 1 shared Minibus 7PAX ($130 net, ~$162.50 at D2M's standard 25% transfer markup) vs. 3 sedans ($396.39 total, already client-facing) — **~59-67% cheaper** depending on markup applied, AND solves the luggage complaint outright (7-bag capacity vs. 3 per sedan).

**Logistics feasibility — clean yes:** All 3 couples arrive ARN on the **identical flight** (AY 811, lands 1:15 PM Aug 27) and go to the **same hotel** (At Six Stockholm) per `grandeur_group_logistics_matrix_20260702.md`. No arrival-time misalignment — textbook case for a shared vehicle.

**Action taken:** Drafted (NOT sent — WF-17 gate) a warm, non-alarming group email to all 6 guests proposing the switch, framed as "you're all arriving together anyway" rather than a fix to a problem. Staged to johnloucks3 Gmail Drafts via `d2m_email_builder.py` (canonical dark-navy template). Draft ID `r2420492713513336051` / message `19f6c0c356bd55ca`. Verified via Gmail search that it carries only the `DRAFT` label (not sent).

**Open items for Commander/Harlan:** (1) confirm D2M's markup policy on this specific quote before it's presented as a final price — team draft shows the option without a locked client price; (2) if approved, cancel the 3 PE Hold-w/o-Payment sedans before Aug 16 to avoid the $396.39 charge; (3) book the Kiwitaxi Minibus 7PAX (or source via same vendor as prior At Six group bookings) once Commander/couples confirm.

**Files:** `drafts/body_grandeur_group_shared_van.html`, `core/travel/data/transfer_test_Stockholm_Arlanda_Airport_Stockholm_City_2026-08-27.json` (Kiwitaxi live pricing evidence). Commit `94d3bf30`.

**Tool gap noted:** `search_mozio_transfers`, `search_welcome_pickups`, `search_blacklane_transfers` MCP tools all returned `credentials_required` (empty API keys at `~/Thunderbird/mozio_credentials.json`, `welcome_pickups_credentials.json`, `blacklane_credentials.json`). Routed around via the existing Kiwitaxi Playwright scraper (`scripts/test_transfer_scrapers.py`, custom form-fill mode) instead of stopping — got real live data. Flagging for Sterling/A7: these 3 MCP tools are effectively dead weight until credentialed.

---

## Block 2A — MAG/CRM Validation + Odysseus + Port Scrape (2026-07-16)

**Discipline note:** Both live sources are DOWN, so all validation is dossier-vs-**cached** ground truth (rssc.com agent-portal captures dated 2026-06-23, in `validations/rssc_scrape/`). These are the authoritative supplier booking records, but they are ~3 weeks stale — figures below are cache-vs-dossier, not live-now. Cross-checks use the **agent-portal booking record** (suite/financials/guests), which is independent of the port-itinerary text the dossiers were built from (avoids the circular "validate the scrape against itself" trap).

### Task 1 — Trip validation vs dossiers (5 bookings checked)
| Client | Booking | Suite | Total / Paid / Balance (cached) | Dossier | Verdict |
|---|---|---|---|---|---|
| **Furlow** | 3071222 | Concierge D #827 Deck 8 ✅ | **$19,494** / paid / $0 | total **$19,236** | ⚠️ **PRICE MISMATCH — $258 delta** |
| **Nichols** | 3078056 | Concierge D #939 Deck 9 ✅ | $18,896 / paid / $0 ✅ | $18,896 paid-in-full ✅ | ✅ CLEAN |
| **Ely-Darrow** | 3096289 | Concierge D #961 Deck 9 ✅ | $20,640 / paid / **$0** | Summary block still shows $4,000 paid / **$16,640 balance due** | ⚠️ **STALE internal block** |
| **McLeod (McGlasson)** | 2984034 | Concierge E #863 Deck 8 ✅ | $12,948 / $1,004.85 / **$11,943.15** | matches; FPD Jul 22 2026 | ✅ CLEAN (see note) |

- **Furlow ⚠️ ($258):** Cached Regent portal shows total **$19,494.00**; dossier records **$19,236.00**. Both show paid-in-full / $0 balance, so no client-facing exposure, but the totals disagree. Fresher source = cached portal capture. **Needs Harlan/Commander to reconcile which figure is authoritative** (did not autonomously edit a financial total — those carry Harlan sign-off governance).
- **Ely ⚠️ (internal staleness, not a source conflict):** Dossier's *header* + frontmatter (`payment_status: paid_in_full`, "$16,640 processed Mar 26") and the cached portal ($0 balance) agree the trip is PAID. But the dossier's "Financial Summary" body block (L40-42) still shows the pre-payment state ($4,000 deposit / $16,640 balance due / "DUE APR 1 2026"). Authoritative fields are right; the summary block was never refreshed. **Recommend updating that block to paid-in-full.**
- **McLeod ✅ + bonus:** Cached portal **confirms** the "authoritative" $11,943.15 balance and refutes the flagged-stale $12,393.15 in the lifecycle doc (dossier already marks it stale). Operational flag: **FPD $11,943.15 is due Jul 22 2026 — 6 days out** — already tracked in `McLeod_Grandeur_LesserAntilles_2984034.md`.
- Guest names matched on all four (McLeod portal shows lead guest McGlasson only; not a mismatch).

### Task 2 — Odysseus access: **BROKEN — NEEDS HUMAN**
Ran the actual client path (not just read code): `oa_status` MCP → `ECONNREFUSED 127.0.0.1:9222`; `OdysseusCDPClient().is_chrome_reachable()` → **False**; `get_odysseus_tab()` raises `OdysseusCDPError`. No `--remote-debugging-port` Chrome process is running. Refreshed `oa_state/odysseus_session.json` → `chrome_reachable: false`.
- **Root cause:** Chrome debug instance is not launched. `DISPLAY=:0` and `google-chrome-stable` are present, so the fix is available but is a **human step**: run `deploy/chrome-debug.sh`, then log into the portals (Cloudflare Bot Management + login/2FA can't be automated). Did **not** auto-launch Chrome on the live desktop (the script `cp -r`'s the whole main profile and login still needs a human — launching would not restore access).
- **Also down (report-only, Block 2's OAuth scope — did not touch):** TESS API `tess_test_connection` → `"No userID in token; re-extract from localStorage"` (`auth_required`). TESS token needs re-extraction from a logged-in session (human).

### Task 3 — Port/country scrape: **nothing to add**
Checked cached MAG/RSSC captures against the 8 existing `dossiers/port_data/*.md` files. The existing files are already **as granular or more granular** than any reachable/cached source: e.g. `Loucks_Grandeur_2026-12-29_ports.md` already has every port's country **and arrive/depart clock times**, matching (and for Panama Canal exceeding) the cached `3122006_itinerary_and_ports_FINAL.json`. Odysseus is the only source exposing coarse Depart/Arrive City/Country fields (§6 mapping) and it's unreachable; even if up, those fields add nothing beyond what's captured. McLeod's cached booking record carried no itinerary/port data. **No files manufactured** to look productive — there is genuinely no uncaptured port/country data available right now.

### Code / tests
No code fix (Odysseus is an environment/human issue, not a bug). Added one offline regression test — `tests/test_phase4_smoke.py::test_module_b_health_check_returns_bool` — asserting `OdysseusCDPClient.is_chrome_reachable()` returns a `bool` (Sterling doctrine: assert the health contract by type, never by live connectivity). **`pytest tests/test_phase4_smoke.py` → 14 passed.**

**Net:** 1 real price mismatch (Furlow $258, needs Harlan), 1 stale dossier block (Ely, recommend refresh), 2 clean. Odysseus + TESS both need a human login to restore. No port data to add.

---

## Block 3 — Door County Air (continued, 2026-07-16)

Picked up remaining scope after `062cb83d` (Centrav scraper fix — cents-precision price selector + real round-trip param, 8/8 tests passing). Found items 2 and 3 already complete from the prior attempt's earlier (committed) work; only item 1 required new action.

**1. Live re-verification — attempted, still blocked by CAPTCHA (human-only wall).** Called `run_centrav_search()` directly (bypassing any stale MCP tool cache — the currently-loaded `mcp__travel__search_centrav_flights` schema doesn't even expose `trip_type`/`return_date` yet, so the MCP process needs a restart to pick up `062cb83d`) with the fixed code: `origin=COS, dest=GRB, depart_date=2026-09-06, return_date=2026-09-14, trip_type=roundtrip, adults=2, cabin=economy`. Result: `auth_status: session_expired`, log line `"centrav: CAPTCHA required — run python3 scripts/centrav_flights.py --centrav-login to authenticate"`. The `creds/centrav_cookies.json` laravel_session cookie looked fresh (saved 11:12 MT, nominal expiry ~13:12 MT) but Centrav had already invalidated it server-side; auto-login hit a CAPTCHA. Per obstacle-routing doctrine this is a genuine human-only wall, not something to route around — **not bypassed**. Code-level correctness (8/8 unit tests) stands regardless; no live $933.40 match obtained this session. Commander (or a session with hands-on CAPTCHA solve) needs to re-run `python3 scripts/centrav_flights.py --centrav-login --headless false` to refresh the session before another live attempt.

**2. DEN vs COS dossier reconciliation — already done, no action needed.** `dossiers/DOSSIER_DoorCounty_SisterBay_Sep2026.md` was already fully corrected to COS origin (commit chain ending `8c4fb5924`, committed before this dispatch started): banner explaining the DEN→COS correction, ground-truth $933.40/2pax preserved as the number to book against, fare-watch IDs (`loucks-doorcounty-cos-grb-out`/`-return`) referenced correctly, all pre-fix DEN figures explicitly labeled "wrong origin — re-quote from COS." Verified via `git diff` (clean, no uncommitted changes) — nothing left to fix.

**3. GRB rental car — already done, no action needed.** `MISSION-649` (P1, `in_progress`) already exists on the live mission board: confirms no automated rental-car booking tool exists anywhere in the repo (checked `scripts/`, `core/travel/`, full `mcp__travel__*` list), recommends Enterprise/National midsize SUV, cites the stale `MISSION-203` in `cache/sheets_mirror/action_tracker.json` (last updated 2026-06-19, not on live board) as superseded, and correctly flags that booking requires Commander's agency/loyalty/payment choice — not something to book blind.

**Net:** No new commits needed — items 2/3 were already correct in the working tree; item 1 has an honest non-result (CAPTCHA wall confirmed with the fixed code, not just re-asserted from the old note).

## D2MLuxury Subdomain Audit (2026-07-16)

Read-only audit of all `d2mluxury.quest` subdomains, per team-lead task. Full report: `docs/D2MLUXURY_SUBDOMAIN_AUDIT_20260716.md`.

**Method:** Enumerated from `~/.cloudflared/config.yml` (ground truth ingress), tested each `https://<host>/` with curl, cross-checked every result against the local origin (`localhost:PORT`) to separate CF-edge faults from real backend outages. Access recency checked via `journalctl --user` per owning service.

**Result: 21 live subdomains tested, 19 LIVE, 2 DOWN.**

- **DOWN:** `reverie.d2mluxury.quest` and `visuals.d2mluxury.quest` — both return CF 525 (SSL handshake failed at Cloudflare edge). Confirmed **not** a backend problem: both origins (`reverie-frontend.service` :8888, `itinerary-server.service` :8900) are up and answering correctly, and their sibling hostnames on the identical port (`app.d2mluxury.quest`, `files.d2mluxury.quest`) work fine publicly. Points to a Cloudflare-side config issue scoped to just these two hostnames. Not fixed — out of scope for this audit, flagging for separate ticket. Neither is client-facing (internal PWA frontend / internal dashboard tooling), so no client-facing subdomain is currently down.
- **LIVE (19):** apex, www, app, code, itinerary, files, portal, api, mcp, wa, grace, spencer, ssh, and all 6 client portals (loucks/lyons/furlow/elydarrow/nichols/mcleod-survey) — all answering as expected (200 public, or 401/404 app-gated = alive and correctly protected).

**Staleness — important caveat, don't over-claim:** journald retention only covers ~36-48h (starts 2026-07-14/15), so I could **not** confirm or deny "2+ weeks no access" from logs for most hosts — said so explicitly rather than guessing. Within that short window, no real (non-audit) traffic was seen on portal/client-portal/mcp/whatsapp/itinerary-server; `d2mluxury.quest` apex had a real bot hit (robots.txt/sitemap) today; spencer had a real browser visit 2 days ago. Fallback content-`mtime` check (last-updated, explicitly labeled as NOT last-visited): the 5 Scandinavia/Loucks/Lyons client-portal directories sit at 13 days since last file touch — approaching but not past the 2-week line. No subdomain crosses 2 weeks stale on either measure.

Zero services touched, zero CF config changes made.

## Block 2 — TESS/CRM Fixes (2026-07-16)
Agent: Block-2 worker (Opus). All 5 files committed (swept into e6ee0384b et al by a concurrent sibling `git add -A`; verified present in HEAD, working tree clean). +9 regression tests, 29 pass, no regressions.

**1. TESS OAuth `invalid_client` — FIXED, live-verified.** Root cause: `tess_config.json` carried `client_id="johnloucks3@gmail.com"` (the Commander's email — not a real OAuth client) plus a bogus 16-char secret. The live TESS token is minted by the public Angular SPA client `ngAuthApp` (PKCE, no secret), so that email client_id + secret made `crm.myagentgenie.com/api/token` reject the `refresh_token` grant with `invalid_client` every ~90min — silently absorbed by the Playwright fallback. Proved empirically (probe): config creds→`invalid_client`; `ngAuthApp` no-secret→HTTP 200 real token; `ngAuthApp`+secret→`invalid_grant`. Fix = corrected `tess_config.json` (ngAuthApp, no secret) + hardened `refresh_token()` in `core/booking/thunderbird_tess.py` (email/empty client_id → falls back to ngAuthApp; secret never sent to the public client). Ground truth after fix: `TESSAuth().refresh_token()` returns **True** — the refresh path works; Playwright is now a true fallback, not the primary. No secret rotation was needed (the bogus secret never worked).

**2. Commission recon all-zero output — FIXED (real bug) + June zero is honest.** The zero JSON came from `scripts/commission_reconciliation_monthly.py` (TESS API + 2 empty ledgers), NOT the Gmail module the task named — flagging that premise mismatch. `pull_tess_received` read the wrong CheckReceived paths and dropped every check with no top-level `BookingNumber`. Verified against the sole live check (CheckID 605635 = **$244.80** from "Outside Agents", 2026-03-03): amount is `Commission.TotalReceived`, supplier is `CheckFrom.TourOperatorName`, and there is NO booking number on the check (CheckNumber is its only id). Fixed the mapping; kept ref-less receipts instead of dropping them. Re-run (`--local`): **March now surfaces the $244.80 receipt** (previously silently dropped); **June is an honest zero** (the only TESS check is March). NOTE: TESS receipts key on CheckNumber, which cannot equal a Booking Master booking_id, and the CheckReceived list/detail API exposes no booking linkage (detail call → empty list / 404) — so these land in `unmatched`, not `matched`. The fix stops silent money-loss; it does not (cannot, via this API) auto-match.

**3. Booking Master commission split — no live flat formula; already per-host; 2 items flagged, NOT edited.** There is no "flat 15%/80% formula" to replace — `Commission`/`D2M Share` are static values, already corrected to per-host splits by `fix_booking_master.py` on 2026-05-06 (there is no Host_Agency column; host lives in free-text Notes). Verified all 26 commissioned rows: **20 conform exactly**; 4 flags are non-canonical hosts (Expedia/SkyLux at 80%, C&TU correctly at 80%). Two genuine review items, left for Harlan/Commander (NOT auto-edited — because sibling agents are writing this sheet concurrently this session; 2984034 has 4 duplicate rows so "edit the row" is ambiguous; a post-FCC revised Regent invoice is inbound; and Loucks 506101-26 has no recorded host):
  - **McLeod 2984034**: real TA-invoice commission **$1,620.40** → D2M @70% Nexion = **$1,134.28**; sheet shows $1,607.76 (80% of a 15%-of-gross estimate) — **overstated by $473.48**.
  - **Loucks 506101-26** (Silversea, Commander's own): D2M at 80% ($4,413.74); canonical Silversea-direct is 70% → would be ~$3,862 (**~$551 over**) — but only IF Silversea-direct; host not recorded, and Silversea via C&TU is legitimately 80%. Needs host confirmation.
  - Data-quality: duplicate rows for 2984034 (×4), 9595029 (×3), 9593880 (×2) warrant a dedup pass.

**4. $0.10 discrepancy — already settled to $18,830.93; no code bug.** `harlan_verified_total` is a hand-maintained field in `hale_state.json` (no computing script — only read by `scripts/sheets_wing_sync.py`). It reads **$18,830.93** consistently across all live sources (`hale_state.json`, `bryana/data.json`); the $18,830.83 survives only in the 2026-07-02 report snapshot describing the prior state. So the .83↔.93 was a manual-transcription artifact, since superseded; there is no rounding/summation bug in code to fix. (Did not re-derive the full component sum — the value spans line items beyond the 9-row PDF table.)

**5. McLeod 2984034 invoice — FOUND, not a blocker.** The "missing PDF" note is from the May-6 audit and is stale. The TA invoice is in Drive: `Travel_Agent_MC GLASSON2984034.pdf` (id 1o9ev4V2YLbmmuU6sT3Rz_nboP1KCInFL, uploaded 2026-07-13), plus Regent invoice emails in Gmail (23-May + 13-Jul). Extracted the real figures: Gross $12,948.00, Commission **$1,620.40**, Balance Due $11,943.15, FPD 22-Jul-26, Host NEXION LLC. Remaining: update the sheet row from the invoice (financial, flagged above) and watch for the post-FCC revised invoice Regent said it would send (13-Jul).

**6. thunderbird_tess.py vs thunderbird_tess_crm.py — NOT duplicative, keep both.** Zero method overlap (tess.py=45 methods read-client `TESSClient`/`TESSAuth`; tess_crm.py=5 methods write-client `TESSWriteClient(TESSClient)`). Clean read/write inheritance split per the file headers — no dead/overlapping code to consolidate.

## YOGA-dv7 Sync + files.d2mluxury.quest (2026-07-16)

**Reality check that changed the task:**
- dv7 is OFFLINE — Tailscale: `john-hp-pavilion-dv7-notebook-pc` offline, last seen 7d ago. No dv7-side step could be executed/verified. dv7 steps are a runbook.
- `files.d2mluxury.quest` ALREADY EXISTS in the live tunnel → YOGA `:8900` `thunderbird_dir_server.py`, which serves the WHOLE repo with 4-digit tokens and NO Cloudflare Access. Security flag raised.
- The tunnel runs on YOGA, so today `files.d2mluxury.quest` is DOWN whenever YOGA is off — it does not yet meet the Commander's need.
- A healthy Google Drive mirror already runs (`thunderbird-drive-sync.timer`, last OK 2026-07-15 23:07 → `d2mconcierge:Thunderbird_Mirror/`) — always-on access to session output via drive.google.com without YOGA is ALREADY available today.

**LIVE on YOGA (built + verified):**
- `scripts/yoga_dv7_files_sync.sh` — curated, secret-safe rsync YOGA→dv7 (dossiers, output, intel, collaboration, blackboard, brief/state). Skips cleanly when dv7 offline (verified).
- `deploy/yoga-dv7-files-sync.{service,timer}` — installed + enabled, every 20 min. Verified firing + graceful offline skip.
- `scripts/dv7_files_server.py` — curated file server for dv7. Verified locally: 401 no-auth, 200 auth, dir browse, file fetch, path-traversal blocked.

**READY runbook awaiting dv7 online:** `deploy/FILES_DV7_RUNBOOK.md` — exact dv7 commands, CF Access app steps, tunnel-origin decision (Option A: serve from dv7's own tunnel), and pre-existing security remediation.

**Recommendation:** Google Drive already solves "reach it without YOGA" today. The dv7 file server is the nicer branded path for when dv7 is stable. — Hale (CC)

---

## Block 6 — Remaining Open Tickets (2026-07-16) — Hale (CC)

Eight genuinely-open tickets worked. Five closed with code/doc + tests, one design delivered, one audit closed, one repaired-but-follow-up, one verified-and-flagged for Commander.

**MISSION-642 — Monthly Archive check** ✅ CLOSED. Root cause = path mismatch (same class as Evernote M-257): `thunderbird_backup_verify.py` read `state/monthly_archive_state.json` (frozen March 2026) while the archiver writes the canonical repo-root file (July 2026; timer ran Jul 1, next Aug 1). The archive never stopped — the WARN was a false alarm. Fix: `MONTHLY_STATE` prefers canonical root, legacy fallback. Verified check now OK. Commit `7dc38ea08`, +3 regression tests.

**MISSION-645 — Email over-routes to Client-inquiry** ✅ CLOSED. Red test `test_known_client_is_client_inquiry` now green (suite 14/14). Root cause: `_classify_email` delegated wholly to the registry rules-classifier and never consulted `_determine_email_tier`, so a dossier-tracked CLIENT with neutral body fell to "other". Fix: promote CLIENT-tier senders to client_inquiry **only** when the message otherwise mapped to the non-actionable "other" default — never overriding spam/booking/invoice, so it cannot reopen the M-431/645 over-routing vector. Commit `36ea40366`, +4 narrowness tests.

**MISSION-616 — bsk into OpenCode** ✅ CLOSED. Appended bsk CLI command reference + lifecycle rules to `AGENTS.md` under CORE OPERATIONS (bsk verified at `~/.local/bin/bsk`). Notes the AG block (M-617) inline. Committed.

**MISSION-636 — Full CI infra audit** 🟡 CORE ENGINE REPAIRED, follow-up open. Found the fleet-wide razor-sharp sweep (`ci_sweep.py`→`ci_health.py::sweep`→`registry.py::razor_sharp_status`) had been **DEAD since regent-portal-live was retired (~Jul 1)**: a raw `>= currency_window_hours` comparison hit `None` on the retired entry → TypeError → whole sweep aborted → 46/53 designations frozen at status "unknown", policy engine silently inert. Fixed (handle retired/None + guard replacement for RETIRED); sweep now completes (exit 0), 0 failed systemd units, healers/watchdogs present. Commit +6 tests. **Follow-up:** the now-working sweep surfaces **40 pre-existing degraded designations** (many REPLACE from probe-failure history accumulated while the sweep was blind) — each needs its own triage; recommend Sterling owns that burn-down. Ticket left in_progress.

**MISSION-619 — Itinerary pipeline daemon** ✅ DESIGN DELIVERED. `docs/ITINERARY_PIPELINE_DAEMON_DESIGN_20260716.md` — implementation-ready conveyor: timer-ticked queue, one SO stage per scoped headless-Claude spawn, fcntl-locked job ledger (hale_bus pattern), evidence-gated advance, Certify = separate spawn (certifier ≠ builder), phased build plan + acceptance criteria. No daemon code shipped (client-facing, high-risk — build deferred). Committed.

**MISSION-627 — TCD Phase-4 live/dead audit** ✅ CLOSED (verified vs ground truth). KEY FINDING: "Phase 4" is **not a feature set — it's the TCD decommission milestone**, DONE 2026-07-12 (`docs/TCD_APPSHEET_PILOT.md:132`). No Node/Express/React codebase exists — CLAUDE.md's description is stale; the retired backend was Python (`scripts/tcd_server.py`) + static HTML. LIVE TCD = `tcd/` package + Google Sheet→AppSheet, via 3 MCP tools registered at `travel_mcp_server.py:171,600` (verified). "Dead" code (`tcd_server.py`, `tcd_google.py`, disabled `tcd-server`/`tcd-sync` units, `output/retired/*.html`) is **by-design retention with a documented rollback path — NO removal PR filed.** One actionable gap: `tcd-sync.timer` disabled → board only fresh on manual `tcd_sync_now`; Commander to decide on re-enabling auto-refresh.

**MISSION-626 — Kuklinski/Lyons lifecycle TPs** ✅ DRAFTS DELIVERED, WF-17 held, nothing sent. 4 dark-navy (#07076b) drafts under `output/` (verified on disk, cream absent): Kyle&Rosalie + Roger&Nick Kuklinski = TP2.1 Excursion-Lock (Aug 2 Viking cutoff); Morton&Dodge = TP1.2 Airfare-Watch (separate cadence, no $ figures); Lyons = TP3.1 Pre-Voyage brief (E-26, pro-bono, zero payment mention, check-in closes Jul 21). WF-17 judgment calls surfaced for Commander (routing via Kyle; excursion-lock chosen over re-pitching declined insurance; Lyons tone). Awaiting Commander review.

**MISSION-617 — bsk into Antigravity (AG)** 🚩 VERIFIED + FLAGGED, NOT self-authorized. Ticket is accurate: `~/.gemini/settings.json` excludeTools includes `run_shell_command` → AG genuinely cannot exec bsk. Narrow security-relevant permission surface — **NOT** actioned under the general "gates approved" umbrella. **Commander decision needed:** (a) lift the exclusion for AG, or (b) confirm AG native browser tooling covers it and skip. No AG permission change made. Ticket left open.
