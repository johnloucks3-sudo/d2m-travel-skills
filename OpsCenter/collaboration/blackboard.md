
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
- Added `smart_fetch.search(query, engine="auto")`: **SearXNG** (`127.0.0.1:8890`, JSON metasearch) primary, **Camofox `@google_search` macro** fallback. **Live-verified:** "cheapest flight COS to GRB September 2026" → 18 real results via SearXNG (Expedia/Kayak/Google links). CLI: `python3 -m core.web.smart_fetch --search "<query>"`.
- **NOT yet done (honest):** the 3 scan scripts are not yet rewired to call `search()` — that's a follow-up (touches Block 3/6 scan code). The tested primitive exists; wiring the callers + closing MISSION-629 is the remaining step.

### 3. Claude Agent SDK (Managed Agents) pilot — BLOCKED, root-caused ⛔ (honest)
- Attempted a real end-to-end run → `AttributeError: 'Beta' object has no attribute 'sessions'`.
- **Ground truth:** installed `anthropic==0.86.0` (requirements.txt pins `0.84.0`). `client.beta` exposes only `files/messages/models/skills` — **no `sessions`/`agents`/`environments`**. The module targets `0.111.0` (a real PyPI version, up to 0.116.0 exists) that is NOT installed. Cache files (`.managed_env.json`, `.managed_agent_haiku.json`) + the 3 ledger entries date to Jun 19–20 → a newer SDK was briefly installed then downgraded. **The managed-agent path has been silently broken since ~Jun 20 — it is *broken*, not merely "unused" as the plan assumed.** This includes the `core/ci/self_observability.py` ci-fix-agent path the plan hoped would dodge the cgroup-kill race — it cannot, because it throws on this SDK.
- **Did NOT upgrade** the SDK (0.86→0.111 is 25 releases across **67 anthropic importers** incl. Telegram C2/email voice/memory embeddings — a high-risk shared-dep change; belongs in a deliberate isolated session, not a burn window).
- **Shipped instead:** preflight guard (`_require_managed_agents`) at `run_task`/`_get_or_create_environment`/`_get_or_create_agent` → raises a clear, actionable `RuntimeError` naming the installed version and pointing callers at the working `claude -p` fallback, instead of a cryptic AttributeError. 4 regression tests. **Recommendation:** cloud managed-agents as a cgroup-race sidestep is a genuinely good idea BUT requires the isolated SDK-bump session first.

### 4. Gemini SDK health check — HEALTHY ✅ + safe allowlist expansion
- `core/gemini_bridge/mcp_function_bridge.py` bridge live: 14/14 `tests/test_gemini_bridge_safety.py` pass; `build_function_declarations()` builds 107 tool declarations; send/financial tools still blocked even when forced into the caller set (mechanism intact).
- **Added 4 read-only flight-search siblings** to `SAFE_ALLOWLIST` (`search_google_flights`, `search_kiwi_flights`, `kiwi_place_autocomplete`, `search_flights_flightaware`) — airport-code/date/pax params only, no PII/send/financial, direct peers of already-listed flight tools. Deliberately excluded `get_client_airports` (reads client dossiers/PII). Dated comment follows the file's own deliberate-expansion discipline.

### CDP (port 9222) evaluation — CAPABILITY CONFIRMED, honestly bounded
- Ground truth: 9222 not running; **no pre-existing CDP pattern in the codebase** (docs grep hits were false positives). Python `playwright` not installed; existing browser automation is Node (`tools/cloak/*.mjs`). Chrome 150 IS installed.
- **Capability test (real):** launched `google-chrome-stable --headless=new --remote-debugging-port=9222` on a throwaway profile → `/json/version` returned `Chrome/150` + live `webSocketDebuggerUrl` (the exact surface `connect_over_cdp` attaches to); page targets enumerable. Cleaned up (killed chrome, removed profile, 9222 closed). **The CDP plumbing works on this box.**
- **Honest bound (no overclaim):** the best human-gated candidate is Centrav (MISSION-001/011/033/037/046), but its blocker is **OTP/CAPTCHA = a genuine human-decision wall CDP does NOT defeat**. CDP's real value is driving a *real, already-authenticated* Chrome (human logs in once → attach headlessly, reuse the OTP-authenticated session, avoid "looks-automated" detection). That needs a persistent CDP-Chrome service + the human's real profile — infra + auth work, NOT stood up in this window. **Verified-viable capability, deferred as a scoped next step; does not "unlock every human-gated portal."**

### Net: now actually wired vs. still an idea
- **Wired + tested:** Camofox Tier 4; `search()` free-text (SearXNG); Gemini allowlist +4; managed-agents failure guard.
- **Good idea, deferred (honest):** rewire 3 scan scripts onto `search()` + close MISSION-629; managed-agents cloud pilot (needs isolated SDK bump first); persistent CDP-Chrome session-reuse service (needs infra + human login).

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
