# WAR ROOM — CRITICAL INFRASTRUCTURE (CI) AUDIT & REFORM
## Hale-OC (Jet) · For Commander · 2026-08-07 · Lane: Hale-owned (ci/process)
**Sources (links):**
- [`standing_orders/SO_CI_RAZOR_SHARP_20260620.md`](../../standing_orders/SO_CI_RAZOR_SHARP_20260620.md) — original CI doctrine + replacement triggers
- [`standing_orders/SO_TOTAL_CI_20260701.md`](../../standing_orders/SO_TOTAL_CI_20260701.md) — TOTAL CI expansion, 6-point qualification standard
- [`config/ci_registry.json`](../../config/ci_registry.json) — source of truth (53 skills)
- [`output/CI_DASHBOARD.md`](../../output/CI_DASHBOARD.md) — live health board (run 2026-08-07T12:08)
- [`core/ci/ci_auto_repair_engine.py`](../../core/ci/ci_auto_repair_engine.py) — self-repair engine (1,106 LOC)
- [`core/ci/self_observability.py`](../../core/ci/self_observability.py) — F2T2EA armed-overwatch (468 LOC)
- `scripts/ci_sweep.py` · `scripts/keepalive_supervisor.py` · `core/ci/ci_health.py`
- systemd inventory: `~/.config/systemd/user/*.timer` = **253** units; `*.service` = **325** units

---

## 1. BLUF
**The CI program has become a self-made problem.** Scope ballooned from **5 technical skills (06-20) to 53 entries (07-01 TOTAL-CI)**, every one keeper=Whetstone, and **52 of 53 have no accountable owner** — so the fix-load collapses onto OC (cheapest lane), exactly as the Commander observed. The board shows **10 REPLACE + 2 RED + 40 permanent-DULL**; the DULLs are a **mechanism artifact (30-day re-eval clock stuck since 06-20/07-01)**, not real degradation — so the board is simultaneously alarm-blind and alarm-deaf. **253 timers / 181 firing daily** is more energy spent monitoring itself than on the work it targets. **Recommend tiering 53 → ~20 true CI, a per-skill owner map, and decoupling "stale-currency" from genuine failure.**

---

## 2. SITUATION
| Board reading (2026-08-07) | Count |
|---|---|
| 🟡 DULL (currency overdue only) | 40 |
| 🔁 REPLACE | 10 |
| 🔴 RED (real, now) | 2 (LiteLLM router 5.1s · qdrant-memory) |
| ♻ RETIRED | 1 (regent-portal-live) |
| Active workarounds | 5 (target 0) |
| systemd user timers / services | 253 / 325 (181 fire ≤24h) |
| CI skills with an accountable owner | **1 of 53** |
| CI skills keeper | **Whetstone × 53** |

### The two RED/REPLACE cases that are not real failures
* **fare-watch-amadeus (49), github-actions (15), home-dir (28), infisical (7)** all carry `active_workaround: DORMANT — awaiting Commander API keys / not migrated`. These are **not tool failures** — they are **unfunded / not-yet-entrusted capabilities wearing REPLACE paint.** Flagging them as failing CI is wrong doubly: no tool-repair can fix them, and the true owner is a Commander key decision.
* **excursion-engine (50)** — probe fails when Chrome/Makeoff:9222 off; engine stages a notification regardless (documented workaround). Genuinely chronic → candidate for RETIRE or re-scope, not a keeper-fix.

### The permanent-DULL bug (root cause found)
* Registry `last_reeval` is pinned at **2026-06-20 / 2026-07-01**; cadence is **30 days**. Today is **08-07** — every skill is >30d past re-eval, so RAZOR_SHARP ⇒ **DULL by the clock alone**, regardless of the probe returning **ok / 2,000ms**.
* **Effect:** the ship is simultaneously (a) telling us *everything* is stale — dead to real DULL — and (b) silently absorbing the 12% REPLACE/RED it still lists. Nobody is authorized to act, so nobody does.

---

## 3. CHANGES RECOMMENDED (Hale-approved; Commander to concur)

### PC-1 · CI DESIGNATION — replace "is anything" with 3 tiers
**Why.** SO_TOTAL_CI spun the gate to *"anything required for autonomous/TP/ARC ops"* — every build made itself CI. Generic categories (survey generators, retired Reverie, n8n, ttyd) are monitoring theatre, not runtime.
**A skill is Tier-1/Tier-2 CI only if it passes ALL three:**
1. **Revenue / client** — a client-facing product or a fork of cash depends on it now.
2. **No tolerable fallback** — the one manual path is too degraded for the trip.
3. **Failure ≤24h is costly** — being dark hurts a client or the ledger, not just the board.
Failure any → **PATCH** (health-only, daily, no page) or **RETIRE** (drop from registry).

| Tier | Meaning | Alerting | Exits (current registry) |
|---|---|---|---|
| **T1 · Critical** | revenue / client hard-stop | subdaily + page | portal-access · gmail-accounts · c2-fabric · telegram-relay · d2m-inbox-triage · cloudflared-tunnel · cruise-db-site · qdrant-memory · credential-keepalive |
| **T2 · Important** | has usable manual fallback, must not silently rot | daily, page | headless-dispatch · web-fetch · cloak · litellm-router/gateway · lifecycle TP·dossiers·itinerary·validations · fare-watch · arc · dani-identity |
| **T3 · PATCH** | degradable; no revenue-stop | daily batch, no page | reverie · ttyd · n8n · tailscale · evernote · hotel/transfer scan · surveys · gdrive-mx · pii · nominatim · tech-adoption |

### PC-2 · PARED-DOWN — what leaves the CI board today
Drop or demote (net 53 → **~20 CI**, rest PATCH/Retire):
- **RETIRE:** reverie-app (frontend, api retired 07-01) · github-actions (no CI running, no key) · regent-portal-live (already) · self-observability probe stack consolidation.
- **PATCH-T3:** travel surveys · booking surveys · hotel-scan · transfer-scan · evernote · nominatim · ttyd · n8n · tailscale · home-dir-health · infisical · tech-adoption.
- **Re-scope/PATCH:** fare probes (on-demand per recent war-room) except a single revenue check.

### PC-3 · The DULL fix — decouple "stale" from "broken"
- **RAZOR_SHARP = probe GREEN + window current** (as designed). Full stop.
- **re-eval** becomes a `needs-recert` tag on the one item past its period — a 30-day clock does **not** nuke the whole board into DULL.
- Auto-stamp `last_reeval` for any skill with 3+ consecutive GREEN sweeps and no open workaround; force re-cert only on a material tool/API/policy change.
- Net effect: board = **GREEN or RED**, nothing permanent-limbo DULL.

### PC-4 · SHARED FIX-BURDEN — end the OC-solo repository
Observed: keeper= **Whetstone × 53**, accountable-owner unset **52/53**. In practice the cheapest lane (OC/DeepSeek) absorbs every repair because it's free and "hand-it-to-me." The result is OC becomes the Wing's **entire fix capacity** — a one-seat bottleneck for the whole CI estate. Shared burden is a structure, not a slogan:
1. **Split keeper by domain**, not one alias:
   - **A1 Moreau (Ops):** timers, systemd, keepalives, portals, docker (healthchecks, inloop, qdrant service)
   - **A2 Dembe (Intel):** fare/tour/cruise data feeds, crawls, competitive intel
   - **A7 Sterling (Platform):** registry, probes, diagnostics, auto-repair engine quality
   - **A9 Harlan (P&C):** ledger/finance-adjacent (revenue, proposal/validation to client)
   - **A14 Whetstone:** stays relief (n+1), **available, not default**
   - **OC:** fast one-off gap-filler — **never the standing owner**
2. **keeper ≠ fixer.** keeper = free window currency; **fixer = who owns the incident** on REPLACE. Recoin both at registration.
3. **REPLACE by tier:** T1 → CC (Claude) first look · T2 → A7/A3 · OC only for OC-native platform bugs — independent verification per existing SO.
4. **Prevent the 1-had bottleneck permanently:** if any skill is chronically one-slot, that's the org's fault, not the fix's.

### PC-5 · REALITY-GRADE CHECK INTERVALS
Windows cross **1h → 840h** and **182 timers fire daily**. Right-size:
- **T1:** ≤30 min only for session/financial-gate (credential-keepalive 3h→30m; gmail/c2/telegram hourly or event-driven). `ci-sweep.timer` stays daily.
- **T2:** daily sweep only — no mid-day timers.
- **T3 / PATCH:** weekly or on-demand.
- **Self-repair philosophy: put this into code, not people.** Fast self-heal only where it's safe+cheap (OAuth refresh, supertimer restart, timer restart). Portal/Captcha/B2B-fare re-auth = **manual on-demand** (the recent war-room commits already moved centrav this way — extend the same doctrine). **Target: 253 → <80 units; 181/day → <40.**

---

## 5. RULE-EXEC & DECISIONS WANTED
- **P2 — CI presence audit + tier assignment** (the 20-line sweep return). Result: a small, honest board.
- **P2 — REPLACE "storm":** 10 items, each within 24h: **REPLACE | RETIRE | un-freeze (drop dormant-but-flagged paradigm)**. No REPLACE unowned >48h.
- **P2 — multi-owner wiring:** add `assigned_owner` + `fixer` fields; set per PC-4; commit after audit.
- **REPORT — instrument "who fixes what":** auto-attribution in the incident log, 2-week rebalance report to Commander.

---

## 6. NEXT STEPS
1. **Commander**: concur / amend on PC-1…PC-5 (no spend gate touched).
2. **Hale-OC**: run the one-shot re-tier sweep + owner migration against the registry (daily, blade-level).
3. **CC/A7** independently verify the migrated registry & tier table (cross-engine double-check).
4. Commit + publish the pruned board; trip = 40-DULL noise gone, 10-REPLACE resolved, OC no longer sole fixer.

— V. Hale, VCS (Hale-OC) · sources verified (registry · dashboard · SOs · systemd) · closed 2026-08-07