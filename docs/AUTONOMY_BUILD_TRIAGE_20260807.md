# AUTONOMY BUILD PROGRAM — TRIAGE & SEQUENCING
**Date:** 2026-08-07 | **Selected:** 30 of 37 ideas | **Executor:** CC solo (OC offline/credits exhausted, no AG this pass)

## BLUF
30-item program, NOT a 7-day sprint. Inventory pass found roughly half already have live infrastructure (timers, functions) — these are WIRE/EXTEND, not BUILD. Sequenced into 6 tranches, cheapest/highest-confidence first. Budget: CC 7-day meter at 8% now, cap growth at 5%/day (Commander ceiling), hard stop for today at 13% seven_day_pct. Tranche 1 started this session.

## BUDGET LEDGER
| Metric | Value |
|---|---|
| 7-day used (start of session) | 8% → 11% (Tranche 2 complete) |
| 5-hour used | 11%, resets 2026-08-08 07:00 UTC |
| Commander ceiling | ≤5%/day growth |
| Today's stop-line | 13% seven_day_pct |
| Verification gate | CC INTEGRITY DOUBLE-CHECK requires cross-engine (OC/AG) ground truth — **unavailable this session** (OC $0 credits). All "done" marks below are self-verified only, flagged UNVERIFIED per doctrine's own escape hatch. Re-run cross-engine check when OC credits reset. |

## TRANCHE 2 — RESULT (4/5 wired live, 1 blocked — see below)
| # | Idea | Outcome |
|---|---|---|
| 29 | Competitive fleet intel & promo yield monitor | ✅ **WIRED** — `scripts/competitive_intel_weekly_scan.py` was fully built (delta-threshold undercut alerting, HIGH-flag-only Telegram) but never had a timer. Created `d2m-competitive-intel-weekly.timer` (Tue 09:00 MT). Dry-run confirmed live (8 sources scanned, 1 real HIGH flag: Embark Beyond partner_update). |
| 18 | Booking-calendar-triggered port/excursion intel | ✅ **WIRED** — new `scripts/port_intel_freshness_trigger.py`, weekly timer (Mon 07:00 MT). Scope note: detection+notify only, not auto-research — no reliable per-booking port list exists outside freeform dossier markdown/TESS, so it flags gaps to Dembe rather than guessing at ports. Verified: 13 known bookings, 1 in trigger window, correctly checked. |
| 34 | Zero-click shore excursion & dining portfolio builder | ✅ **WIRED, blocked on separate outage** — `core/booking/post_booking_materials_pipeline.py` already fully built (4-doc packet incl. excursion comparison + port dining guide, Drive upload+verify). Never had a timer — created `post-booking-materials.timer` (15 min). **TESS auth confirmed dead**: refresh token expired, Playwright Chromium binary missing, vault password stale — pre-existing, unrelated to this build. Timer is safe/idempotent; will self-activate once TESS is repaired. |
| 37 | VIP client onboarding & preference extractor | ✅ **WIRED** — new `scripts/vip_onboarding_extractor.py`: reads existing `client_inbox_queue.jsonl`, filters to new (non-known-client) `client_inquiry` senders, runs `parse_client_inquiry()` (Haiku), attempts live TESS `create_client`, always stages JSON locally as fallback. Timer every 15 min. Verified live: 4 real inquiries scanned, all correctly matched to known clients (no false "new lead" positives), 0 crashes. |
| 26 | Post-booking fare drop / stateroom arbitrage engine | ⛔ **BLOCKED, deferred honestly** — daily cruise fare-recheck engine (`fare_watch_alert.py`) already exists and is already timer-wired (09:30 MT daily); the real gap is auto-creating a watch when a booking confirms, and a commission-delta calc. Did not build blind: (1) TESS is down (same outage as #34) so the integration is untestable end-to-end right now; (2) **no price field has ever been confirmed in a TESS booking payload anywhere in this codebase** — `get_booking()`'s own docstring notes the direct-fetch endpoint 500s and nobody has verified what a real booking object's price field is called; (3) **no commission-rate table exists in the repo** — fabricating a commission % for a financial calc would be a real correctness risk, not a shortcut. Needs: TESS repaired → one live payload inspected for the actual price field → Harlan confirms/supplies commission rates. Flagging for Commander rather than guessing. |

**Opinion:** 4 of 5 Tranche 2 items were genuinely cheap — the underlying capability already existed, built by someone, and simply never had a trigger connected. #26 is the one item this session where "just wire it" wasn't honest — two separate unknowns (price field, commission table) sit under the missing timer, and guessing at either risks a bad financial number reaching a client-facing re-fare decision. Recommend routing #26's price-field question to whoever fixes TESS next, and a direct ask to Harlan for the commission table before any build attempt.

## TRANCHE 3 — INVESTIGATION ONLY, NO SHIP (stopped clean at budget line)
Budget hit 11% seven_day_pct (2% short of today's 13% stop-line) after investigation; both items examined turned out riskier than the triage estimate, so stopped rather than rush gate-critical code. Real findings banked for next session:

| # | Idea | Finding |
|---|---|---|
| 7 | Anomaly detection + auto-response playbooks | **Partially blocked — Commander-held decision.** `thunderbird-sentinel.timer` has run `/bin/true` (a no-op) since 2026-06-10 — its source `OpsCenter/sentinel/thunderbird_sentinel.py` was deleted and never committed. The stub's own comment says: "Rebuild scope is Commander-held." Separately, `thunderbird_coo_watchdog.py` already does tiered self-heal + restart-count-limited escalation for systemd services (overlaps #16) — but there is no anomaly-TYPE → playbook registry (e.g. "Gmail 401" → `heal_oauth()`) the way CLAUDE.md's own example describes. `heal_oauth()` exists; `escalate_with_context()` does not. Needs Commander's call on sentinel rebuild scope before touching this. |
| 14 | Self-certifying mission close | **More built than expected, gap is subtler than "wire it."** `cmd_complete()` in `mission_board_sync.py` already gates cross-Hale delegated-mission closes on a `verification_artifact` + cross-seat `certified_by` via `delegation_wiring.certify_mission_and_record()` before allowing completion — real integrity control, not a rubber stamp. The actual gap: it *requires* the artifact to already be set by the closer, it doesn't *generate* its own verification suite at close-time. Extending gate-critical completion code with under 2% budget margin for fixing a mistake was the wrong trade — deferred to next session with full budget. |
| 23, 15, 3, 9 | (remaining Tranche 3) | Not yet investigated this session. |

**Opinion:** Correct call to stop rather than push a rushed change into mission-close integrity code — that system already carries a real anti-theater gate (delegation certification) and a bad edit there is worse than a missed tranche. Next session: get Commander's ruling on sentinel rebuild scope for #7, then finish 23/15/3/9 with full daily budget before touching #14's gate logic.

## METHOD
Each item classified before sequencing:
- **WIRE** — capability exists, just needs a trigger/timer connected. Minutes-hours.
- **EXTEND** — real infrastructure exists, needs a feature added on top. Hours-a day.
- **BUILD** — no evidence found in codebase. New capability. Days.

Staff labels are ownership/routing tags for the tracker — no OC/AG spawns this pass (Commander directive: solo, no other HALEs right now).

---

## TRANCHE 1 — VERIFY/WIRE (Owner: Sterling/Hale) — STARTED THIS SESSION
| # | Idea | Class | Finding |
|---|---|---|---|
| 17 | Staleness-triggered dossier refresh | **WIRE — confirmed live** | 3 timers already running: `d2m-dossier-freshness.timer`, `thunderbird-dossier-freshness.timer`, `dossier-validation-sweep.timer`. No build needed — closing as satisfied, UNVERIFIED (self-check only). |
| 24 | Pre-answered status digest | **WIRE — confirmed live** | `d2m-commander-digest.timer` → `scripts/d2m_commander_digest.py` already running daily. Needs content audit (does it actually anticipate "where's X"?) before fully closing — EXTEND if gaps found. |
| 21 | Auto FPD/balance-due sweep w/ draft dunning | **EXTEND — sweep done, dunning missing** | `fpd-auto-update.timer` → `core/ops/fpd_auto_update.py` runs the sweep. Grep confirms **no draft-dunning-email logic present** — real gap, real work. |
| 16 | Silent-failure self-repair loop | **EXTEND — partial, real gap found** | `restart_flap_detector.py` + `crash_reporter.py` exist, but only **11 of 326** systemd services have `OnFailure=` wired (3.4% coverage). Genuine gap, not "mostly done." |
| 13 | Sentiment/urgency pre-triage on inbound | **VERIFY PENDING** | `d2m_inbox_triage.py --apply` runs on timer; classify/score functions exist elsewhere in repo but wiring into that specific script not yet confirmed — next check. |

## TRANCHE 2 — EXTEND (Owner: Dembe/Harlan)
| # | Idea | Class |
|---|---|---|
| 29 | Competitive fleet intel & promo yield monitor | EXTEND — `run_competitive_surveillance` exists, needs timer + delta-threshold alerting |
| 18 | Booking-calendar-triggered port/excursion intel | EXTEND — `scan_anchor_dates`/`compute_booking_anchors` exist, needs intel-fetch trigger |
| 34 | Zero-click shore excursion & dining portfolio builder | EXTEND — search tools + excursion-analysis skill exist, needs auto-trigger on booking confirm |
| 37 | VIP client onboarding & preference extractor | EXTEND — `auto_enrich_client` exists (1 file), needs `parse_inquiry`→CRM wiring |
| 26 | Post-booking fare drop / stateroom arbitrage engine | EXTEND — `fare_watch` infra is extensive (53 files), needs re-fare staging + commission-delta calc on top |

## TRANCHE 3 — EXTEND (Owner: Sterling/Hale, orchestration layer)
| # | Idea | Class |
|---|---|---|
| 7 | Anomaly detection + auto-response playbooks | EXTEND — sentinel/watchdog timers exist, needs a playbook registry (alert-type → action) |
| 23 | Chop-chain auto-advance | EXTEND — `sss_coordinate`/`sss_decide` exist, needs auto-advance-on-checkable-criteria logic |
| 15 | Auto-generated status papers from action log | EXTEND — `staff_summary_sheet.py` + `sss_render.py` exist, needs auto-generation-on-demand wiring |
| 14 | Self-certifying mission close | EXTEND — mission board + Silver gate (`core.silver.gate`) exist, needs auto-attach-evidence-before-close |
| 3 | Credential monitor w/ predictive auto-heal | EXTEND — keepalive-supervisor/oauth_refresh_all/deadman exist, needs 48h-predictive layer + secondary-cred fallback |
| 9 | Adaptive lane concurrency sizing | EXTEND — `billing-budget-guard.timer` + static `DEFAULT_CAPS` exist, needs dynamic burn-rate throttling |

## TRANCHE 4 — BUILD (Owner: Hale, core orchestration)
| # | Idea | Class |
|---|---|---|
| 1 | Priority-based auto-escalation | BUILD (small) — 0 hits, needs age-check on mission board + escalation routing |
| 6 | Decision matrix auto-refresh | BUILD/EXTEND — `tcd-sync.timer` exists, auto-categorize/route not confirmed |
| 4 | Cross-lane load balancing | BUILD (medium) — 0 hits, needs lane-health metric feed before dispatch |
| 8 | Verification caching w/ TTL | BUILD (small-medium) — `integrity_check.py` exists, no cache layer |
| 2 | Predictive task batching | BUILD (medium) — 0 hits |

## TRANCHE 5 — BUILD (Owner: Dani, client-facing — higher risk, needs scope decision)
| # | Idea | Class |
|---|---|---|
| 11 | Client portal self-service deflection | EXTEND — portal :8925 live, needs doc/payment/itinerary self-serve endpoints |
| 10 | Batch-approve client draft queue | BUILD (medium) — **blocked on Commander scope call**: Sterling wants per-item spot-check kept mandatory; Dani wants full batching. Recommend: cap to documents/status drafts only, exclude free-text replies, until Commander rules. |
| 25 | Cross-persona task handoff without human router | BUILD (medium-large) — routing engine on task metadata |
| 27 | Zero-touch pre-departure milestone broadcast | BUILD (medium) — L-90/60/30/14/1 triggers on top of existing anchors |
| 5 | Outcome recording + learning loop | EXTEND — recording exists (`delegation_outcomes.py`), learning/auto-adjust layer is BUILD |

## TRANCHE 6 — BUILD, largest scope / external-dependency risk (Owner: Dembe/Harlan)
| # | Idea | Class |
|---|---|---|
| 31 | Self-healing itinerary-app sync daemon | BUILD (large) — external API dependency, scope TBD |
| 33 | Predictive client re-engagement / voyage anniversary trigger | BUILD (large) — needs historical booking cadence analysis |
| 35 | Emergency port alteration / disruption sentinel | BUILD (large) — needs AIS/weather feed integration; may not be reachable, flag before committing budget |
| 36 | Commission split & host-agency tier optimizer | BUILD (large) — needs host-agency tier data, may require manual data entry (external dependency) |

---

## OPINION
- Tranches 1-3 (16 items) are the real near-term win: mostly wiring/extension on infrastructure that already exists. This is where the 5%/day budget should go first.
- Tranche 4 (5 items) is CC's own seed infra — genuinely new but small-to-medium scope each.
- Tranche 5's #10 needs your ruling before build starts (Sterling/Dani split, flagged above).
- Tranche 6 (4 items) carries real risk of external-dependency dead ends (AIS feeds, host-agency tier data access, Travefy-equivalent sync API). Recommend scoping-call before spend, not blind build.

## RECOMMENDATION
Proceed Tranche 1→2→3 in order, ~day-per-tranche pace at current budget ceiling, report progress via Telegram (short) / email (extensive) per your mobile routing. Hold Tranche 5 item #10 for your scope ruling. Flag Tranche 6 items for a go/no-go before spend once external-dependency reachability is checked.
