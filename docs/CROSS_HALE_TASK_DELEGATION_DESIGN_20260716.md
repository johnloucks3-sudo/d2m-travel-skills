# CROSS-HALE TASK DELEGATION DESIGN
## Splitting headless work across the three Hale seats (CC / OC / AG)
**Dreams2Memories Travel, LLC · Thunderbird Wing**
**Commander directive 2026-07-16 · Author: Hale (CC session) · Status: DESIGN — Phase-0 building block implemented, real-time bus GATED**

---

## 0. TL;DR

- **Usage reality (4 wks, 2026-06-18 → 07-16):** Claude MAX 20x peaked ~**75% of the overall weekly cap** once (Jun 28) and now sits ~**64%/64%**. There are **two real Claude ceilings, not one** — an overall-weekly cap (Opus-sensitive) and a Sonnet-weekly cap — plus a **15/day routine-run cap** (hit 39 runs in one week, W28). No recorded 100% cap-hit.
- **The Opus load is material, not negligible.** On Jun 28 the overall cap (75%) ran **~19 points above** Sonnet-only (56%). That gap is Opus/non-Sonnet — driven by CC interactive work and an **Opus-dominant OpenCode `/ask-opus` lane**.
- **CC and OC draw the SAME MAX meter.** OC's `/ask` dispatch lane logs `cost=0` (MAX OAuth). So **CC↔OC delegation buys parallelism and latency, NOT budget relief.** Only **AG (Antigravity/Gemini, a separate Google meter, $0 Claude cost)** adds throughput without touching the MAX bucket.
- **Routing recommendation:** two levers — (a) stop defaulting to Opus when judgment isn't required (relieves the overall cap), and (b) offload Claude-optional, large-context, and vision work to **AG** (relieves both Claude caps and the run cap).
- **Delegation spine already exists:** `mission_board.json.assigned_to` (the unit) + `wing_relay.relay_handoff()` / `relay_ack()` (the notification, already coded). The **locked real-time `hale_bus_state.json` bus (C2 Fabric Phase 1) is GATED at Commander Gate-4 and is NOT built here.**

---

## 1. USAGE ANALYSIS — 4 weeks (2026-06-18 → 2026-07-16)

### 1.1 What tracking actually exists (and its limits)
| Source | What it holds | Reliability |
|---|---|---|
| `OpsCenter/usage_ledger.json` | `manual_snapshots` (MAX-screen pastes), `routine_runs` (headless dispatches), `entries` (metered managed-agents), `total_usd` | Snapshots are hand-pasted & sparse; runs are auto-logged |
| `OpsCenter/collaboration/rate_limit_status.md` | Last MAX-screen reading (2026-07-07: 64%/64%, runs 3/15) | Point-in-time only |
| `.ask_usage_log` | OpenCode `/ask` (Sonnet) vs `/ask-opus` (Opus) inline dispatches, `cost=0` | Model + timestamp; **no headless entries** |
| `CLAUDE.md` blackboard budget line (git history) | Weekly %/Sonnet %/runs snapshots over time | Periodically refreshed snapshot, **not a continuous meter** — values repeat across many commits |
| `OpsCenter/bryana_usage_report_2026-07.json` | A **gifted client's** chatbot usage (3/750) | **Not Wing model usage** — excluded from this analysis |

> Note: `usage_ledger.json` / `rate_limit_status.md` live under `OpsCenter/`, not repo root. The `/usage` skill should confirm it reads those paths.

### 1.2 Claude MAX trend (from `usage_ledger.json` manual snapshots + blackboard git history)
Reset cadence: **Thursday 21:00 MT.** Snapshots taken at different points in the week are **not directly comparable** — read as levels, not a monotonic curve.

| Date | Overall weekly % | Sonnet weekly % | Overall − Sonnet (= Opus/non-Sonnet) | Runs |
|---|---|---|---|---|
| 2026-06-08 | 28 | 34 | −6 | 9/15 |
| 2026-06-09 | 34 | 41 | −7 | 2/15 |
| 2026-06-28 | **75** | 56 | **+19** | 9/15 |
| 2026-07-07 (post-reset) | 12 | 12 | 0 | 3/15 |
| 2026-07-07 | 64 | 64 | 0 | 3/15 |

**Reading:**
- The two `%` fields have **different denominators** (they cross over: Sonnet > overall on Jun 8-9). They are **two separate caps.**
- The **Jun 28 peak** shows the *overall* cap (75%) was the tighter one, pushed ~19 pts past Sonnet by **Opus/non-Sonnet**. Opus is a first-class consumer, not a rounding error.
- Defensible summary: **peaked ~75% of the overall weekly cap at least once in late June; no recorded 100% cap-hit; now steady ~64/64.**

### 1.3 Headless / routine dispatch load
- `routine_runs`: **60 headless dispatches** in the window — W27=9, **W28=39**, W29=12. Daily cap **15/15**; W28's 39/week is spiky but under ceiling.
- `entries` (the *metered* managed-agents lane): only **3 Haiku test entries** (Jun 19), `total_usd = $0.001152`. The metered lane is essentially **unused in production** — nearly all work runs flat-rate on MAX OAuth.

### 1.4 OpenCode `/ask` lane (`.ask_usage_log`)
- 80 dispatches Jun 1 – Jul 12, all `inline`, all `cost=0` (**MAX OAuth, not Poe points**).
- In-window (W25-W28): **Opus-dominant** — Opus {W25:3, W26:2, W27:4, W28:6} vs Sonnet only in W28 (7).
- **Implication:** `/ask-opus` is being used as the default OC escalation regardless of task complexity, and it **feeds the overall (non-Sonnet) cap** — the exact pressure seen on Jun 28.

### 1.5 The "20X Claude MAX" escalation — WHEN & WHY
- The **$200/mo 20x MAX tier predates the analysis window.** `docs/WAY_AHEAD_STRATEGIC_SESSION_20260601_COMPREHENSIVE.md` (2026-06-01) already shows *"MAX (20x): 8% used."*
- **Driver = the "Lily Pad Problem"** (same doc): ~$200/mo of **Grok** spend + **OpenRouter** multi-provider usage that still produced outages. The Wing **consolidated onto one stable Claude MAX 20x** as primary — see commits `637f8ef21` / `8e7561364` (2026-05-31, *"consolidate router to Claude MAX only"*) and OpenRouter retirement (**MISSION-267, 2026-06-15**).
- There is **no in-window upgrade transaction.** The Commander's *"20X claude MAX earn your keep"* (`hale_decisions.md:3050`) is **value-extraction pressure**, not an upgrade event.

### 1.6 Antigravity (AG) — WHEN added & usage impact
- **Wired 2026-07-13** (`GEMINI.md` identity + verified live, commit `f4fc2060a`); config dir `~/.gemini/antigravity` created **2026-07-12**; added to the CC relay **2026-07-14** (`7e013ab8f`); equal-performance SO **2026-07-14** (`05c45c5b3`).
- AG runs on **Google Antigravity (Gemini)** — a **separate Google meter, $0 Claude cost.**
- **Impact classification: pure additive capacity.** At only ~3 days old by the window's end, AG produces **no visible shift** in the aggregate CC/OC picture — and by construction it **never draws the Claude MAX bucket.** It is the only seat that adds throughput off the constrained meter.

### 1.7 Current model-routing logic — designed vs. drifting
- `core/ai_infra/thunderbird_model_router.py` `MODEL_STRATEGY` knows only **Sonnet-MAX + Gemini tiers**. There is **no Haiku, no Opus, no Fable** in the router.
- `CREW_MODEL_TIER` (SO-TOKEN-DISCIPLINE 2026-05-29) pins personas: HALE / A3 Dani / A6 Luna / A1 / EXEC → **Sonnet-MAX**; A2 Dembe → **Gemini Pro (1M ctx)**; A5/A7/A8 → **Gemini Flash-lite**; A9 Harlan → **Gemini Flash**. (OpenRouter/DeepSeek lanes were rewired to Gemini, MISSION-267.)
- **Drift finding:** the router governs the **persona → Gemini-offload** decision, but it does **NOT govern the Claude-tier choice** (Haiku vs Sonnet vs Opus). That choice happens **ad hoc** at the CC headless-spawn `--model` flag and OC's `/ask` vs `/ask-opus` — which is exactly **where the budget is spent.** The Opus-heavy `/ask` log is the visible symptom: the expensive tier is the *unmanaged* one.

---

## 2. ASSESSMENT — how allocation could improve (concrete)

### 2.1 Shift work to a planning phase before execution? — YES, for one specific class
Signals: Opus-dominant OC dispatch + a near-empty mission board (2 active) + repeated **"detection without execution"** lessons this session (e.g. supplier-email write-back that was *recommended* but never *executed*). These point to **execution tokens spent before success criteria are pinned.**
**Recommendation:** gate **Opus** dispatch behind a cheap **Sonnet/Gemini scope-check** that writes explicit **acceptance criteria first** (the PDTAC **T** stage). Trivial/mechanical tasks skip it; ambiguous or architecture tasks get the plan pass. This is a targeted fix, not a blanket "plan everything."

### 2.2 Shift more to headless vs interactive? — NOT for budget; yes for parallelism
The data says the cost lever is **model tier, not headless-vs-interactive**: interactive `/ask` and headless routine-runs **both** hit the same MAX meter, and the metered managed-agents lane is ~$0. Chasing "more headless" will **not** relieve the cap. Headless still earns its keep for **parallelism and instrumentation** (routine_runs is the only auto-logged lane). **Correct lever: right model + offload to AG**, independent of headless/interactive.

### 2.3 Task-to-model apportionment (grounded in observed task types)
| Tier | Route here | Evidence in this codebase |
|---|---|---|
| **Haiku** (mechanical/simple) | Factbook refresh, inbox triage, dossier sync, mission-board status writes, timestamp/label fixes, file moves, scrape-and-store, JSON validation | `08b1747e0` restored **haiku** for factbook-refresh; `07132f2f3` inbox-triage; done ad hoc today — **formalize it** |
| **Sonnet** (default/moderate) | Client-adjacent drafting (not sending), itinerary assembly, email-intel classification, research synthesis needing judgment, most PDTAC **T/A** work | Current CREW_MODEL_TIER default; `.ask` Sonnet lane |
| **Opus** (complex reasoning/judgment/architecture) | Cross-seat delegation design (this doc), C2-fabric reasoning, root-cause debugging (inbox crash-loop), master-plan restructuring, cross-seat arbitration, novel doctrine | Several tasks dispatched **this session** are genuine Opus work — but Opus should be the **criteria-gated exception**, per §2.1 |
| **Gemini** (via AG / router) | Large-context research (1M ctx: Dembe/A2 destination & market intel), vision / image QC, bulk parallel scrape+summarize — the **Claude-optional** work | Router already routes A2 → Gemini Pro; image-QC is MANDATORY per memory |
| **Fable** | **Undocumented internally.** Only external chatter (a scraped tech-harvest log) frames it as a creative / narrative / game-writing-tuned Anthropic model. **No config, not wired.** | `logs/tech_harvest_2026-06-21.json` only |

**Fable verdict:** do **not** wire it on speculation. It is a *candidate* only for pure long-form creative (Luna/A6 narrative), and only if a controlled A/B trial shows lift over Sonnet. No internal documentation exists to justify a production role today.

---

## 3. DELEGATION WORKFLOW DESIGN

### 3.0 First: reconcile with the Equal-Performance Standing Order (`05c45c5b3`, 2026-07-14)
The SO holds **all three seats to the same bar**. This design does **not** violate it:
- The SO governs the **behavioral** standard — independence, boldness, initiative, frankness, innovation. **Identical for CC, OC, AG.**
- This design governs **substrate fit** — context window, cost meter, model family. Routing bulk research to AG is **not a demotion**; it is putting the right *engine* on the right *load*. A seat's rank is not its task mix.

### 3.1 Routing criteria — CC vs OC vs AG (concrete, grounded in seat identity)

**CC — Claude Code (Opus/Sonnet on MAX). The hub.**
Owns: **judgment, architecture, multi-file code, client-voice-adjacent reasoning, cross-seat arbitration, and any Opus-grade task.** CC is the relay hub — **OC↔AG traffic is hub-routed through CC** today (bidirectional CC↔OC and CC↔AG; OC↔AG not yet direct). CC is the **default certifier** (§3.4): it can spend judgment to verify others' work.
*Route to CC when:* the task needs Claude-grade reasoning, touches client voice, is architecture/doctrine, or must arbitrate between seats.

**OC — OpenCode (Sonnet/DeepSeek via MAX OAuth + a separate Poe-points persona lane).**
Owns: **mechanical ops, scheduled sweeps, data pulls, scrapes, batch file ops, CI probes** — the *"ops/mechanical → JET default"* doctrine (`feedback_ops_route_to_jet_default`). Owns the **systemd routine-run lane** (15/day).
*Route to OC when:* the task is deterministic ops/mechanical, is already a scheduled sweep, or is a data pull that needs no judgment. **Caveat: OC's `/ask` lane draws the same MAX meter as CC — this buys parallelism, not budget.**

**AG — Antigravity/Gemini (separate Google meter, $0 Claude). The budget-relief valve.**
Owns: **large-context research (Gemini 1M ctx — market/destination intel), vision/image tasks, and bulk parallel Claude-optional work.**
*Route to AG when:* the task needs a big context window or vision, **or** is Sonnet-tier work that does **not** need Claude judgment/voice. AG runs on a free Google meter, so **Claude-optional work should default to AG at any weekly %** — there is no reason to spend the MAX bucket on it. AG is the only seat that adds throughput without drawing the MAX bucket.

**Decision order (first match wins):**
1. Needs Claude judgment / client voice / architecture / arbitration? → **CC**
2. Deterministic ops / scheduled sweep / data pull, no judgment? → **OC**
3. Large-context research **or** vision **or** Claude-optional bulk? → **AG**
4. Otherwise → **CC** (safe default; CC can re-delegate).

*Edge case — judgment **and** huge context:* step 1 wins (judgment routes to CC) even when context is large. If the context exceeds CC's window, **CC chunks it, or sub-delegates the research leg to AG** (Gemini 1M ctx) and keeps the judgment/synthesis on CC.

### 3.2 The unit of delegated work — a mission-board ticket
`OpsCenter/mission_board.json` is the durable truth. Existing fields: `id, title, status, priority, assigned_to, description, logs`. **Extend the schema** for delegation:
```
assigned_to          : "CC" | "OC" | "AG"        # the routing decision (§3.1)
acceptance_criteria  : str   # delegator-defined success check (PDTAC "T") — REQUIRED
verification_artifact: str   # assignee-filled: file path | commit hash | URL | sheet row
certified_by         : str   # a DIFFERENT seat than assigned_to (default "CC")
delegation_rationale : str   # one line: why this seat (substrate fit)
deadline             : ISO8601
```
Assignment is a **field write**, not a manual hand-off — an agent (or the AGY mission-board capability being built in parallel) sets `assigned_to` from §3.1.

### 3.3 Hand-off mechanism — existing relay primitives (already coded)
`core/relay/wing_relay.py` (a **protected file — do not modify**) already exposes exactly what's needed:
- **Notify a hand-off:** `relay_handoff(from_platform, to_platform, task, detail)` → posts `HANDOFF → {seat}` to the relay.
- **Acknowledge receipt:** `relay_ack(platform, mission_id, status)` → posts `ACK {mission_id} — {status}`.
- Inbox topology (drained by `thunderbird_telegram_gw.py::relay_poll_loop`): `opencode_inbox.md`, `claude_inbox.md`, `antigravity_inbox.md`. **OC↔AG must route through CC.**

The ticket is the **durable state**; the relay is the **notification layer**. They are complementary — a hand-off is *both* a `assigned_to` write *and* a `relay_handoff()` ping.

### 3.4 Completion / status reporting — lifecycle
```
proposed
   │  (delegator sets assigned_to + acceptance_criteria)   ← PDTAC T
   ▼
assigned ──relay_handoff()──► (seat)
   │  relay_ack(mission_id,"received")
   ▼
in_progress
   │  assignee writes verification_artifact, status→pending_review   ← PDTAC A
   ▼
pending_review
   │  CERTIFIER (≠ assignee, default CC) validates ARTIFACT CONTENT vs acceptance_criteria   ← PDTAC C
   ▼
done  (certified_by set)     — or —     blocked (artifact missing/incorrect → re-surface red)
```

### 3.5 Anti-theater controls — the crux (kills "detection without execution" & "SUCCESS theater")
These are hard requirements, each traceable to a failure pattern already found:

1. **Acceptance criteria set AT hand-off, validated on CONTENT — not presence.** A file *existing* ≠ a file *correct*. This is the supplier-email-writeback lesson (logs were *recommended*; nothing *executed* them). The certifier checks the artifact **against `acceptance_criteria`**, not that a file merely appeared.
2. **A named, machine-checkable verification artifact is mandatory to reach `done`.** File path (exists), commit hash (in `git log`), URL (HTTP 200), or sheet row (present). No artifact → cannot close.
3. **Cross-seat certification.** `certified_by` **must differ** from `assigned_to`. A seat never certifies its own work. Default certifier = **CC** (or the delegator). This kills self-attested SUCCESS.
4. **Independent ground-truth check, never self-report.** The certifier re-checks the artifact directly (memory: *verify vs ground truth*; *credential-doomsday false alarms* — never trust a self-reported 🟢).
5. **Watchdog expiry.** A ticket ACKed but with no artifact by `deadline` flips to **blocked/red** and re-surfaces (heartbeat doctrine) — no silent stalls.

### 3.6 Gate boundary — what is BUILT vs GATED
- **BUILT now (low risk, this session):** a pure **routing + ticket-schema library** — `core/relay/task_delegation.py` (a **non-protected** path; verified against the literal 10-file protected set in `core/policy/rules_registry.py`). It classifies a task → seat, and builds a delegation ticket with the extended schema. It **imports** `wing_relay` (read-only use) and **does not modify** any protected file, does not auto-fire relay, and does not write the mission board. It is a **building block** other seats / the AGY mission-board capability can call — **not a live-wired system.**
- **GATED — requires Commander Gate-4 approval (NOT built here):** the locked real-time visibility bus, `hale_bus_state.json` + `fcntl`/SQLite-WAL lock, from **C2 Fabric Phase 1** (`docs/UNIFIED_C2_FABRIC_PROPOSAL_20260706.md`). That proposal is explicitly pending **Gate 4 — Commander Decision**. This design **rides on already-live primitives** (mission_board.json + relay_handoff/relay_ack) precisely so it does **not** build past that gate. When the bus is approved, it becomes the real-time mirror of the same ticket lifecycle defined here.

---

## 4. ROLLOUT (post-approval, phased — no same-session build past Phase 0)
- **Phase 0 (done):** `task_delegation.py` classifier + schema library + self-test.
- **Phase 1 (needs the AGY mission-board capability, in flight by another agent):** wire `assigned_to` writes to call `route_task()`; emit `relay_handoff()` on assignment.
- **Phase 2 (Commander Gate-4):** promote the ticket lifecycle onto the locked `hale_bus_state.json` bus for real-time cross-seat visibility.
- **Metrics (Sterling, weekly, per C2-fabric doc):** delegation-close rate with valid artifact; self-certification violations (target 0); overall-weekly % vs Sonnet % gap (the Opus lever); share of Sonnet-tier work offloaded to AG.

---

*Grounded in: `OpsCenter/usage_ledger.json`, `.ask_usage_log`, `CLAUDE.md` blackboard git history, `core/ai_infra/thunderbird_model_router.py`, `core/relay/wing_relay.py`, `core/policy/rules_registry.py`, `OpsCenter/mission_board.json`, `docs/UNIFIED_C2_FABRIC_PROPOSAL_20260706.md`, `GEMINI.md`, `hale_decisions.md`. — Hale, 2026-07-16 MT*

---

## Addendum 2026-07-18 — USAF Staff Summary Sheet retrofit

Commander directive 2026-07-18: the **PDTAC** sequence (Propose→Decide→Task→
Accomplish→Certify) named in this design was an AI invention, not his mental model. His
model is the real Air Force **Staff Summary Sheet (AF Form 1768)** and the tasker
process it rides on (digitized DoD-wide as the **Task Management Tool (TMT)** / **CATMS**
/ ETMS2). Research confirmed PDTAC dropped the two load-bearing stages of real staff
process: the **OCR coordination (chop) chain** and the **suspense date**.

The restored model lives in `core/staffing/staff_summary_sheet.py` and adds five fields
to the mission-board ticket, additively (legacy `assigned_to` kept as a deprecated alias):

- **`opr`** — Office of Primary Responsibility; owns the action end to end.
- **`ocr_chain`** — ordered Office(s) of Coordinating Responsibility; the chop chain,
  each recording concur / concur-with-comment / nonconcur. A nonconcur is *recorded and
  routed to the decision authority to adjudicate*, never a veto.
- **`action_type`** — the AF Form 1768 action block: `COORD` / `APPR` / `SIG` / `INFO`.
- **`coordination_log`** — append-only chop trail (who, verdict, comment, when).
- **`suspense_date`** — the deadline-with-teeth (already a board field; now first-class).

Lifecycle: `drafted → in_coordination → coordinated → decided → tasked → accomplished →
closed`. The two mandatory overlays from this design are preserved unchanged: the
**CHIEF SILVER front + back gate** (no checkable "done" → no sheet; back-gate battery on
the artifact before close) and **anti-theater cross-seat/office certification** (the
certifier must differ from the OPR). The `delegate_mission()` wire is now OPR-aware
(reads `opr`, falls back to `assigned_to`), so this model and the older CC/OC/AG
delegation path share one bus. Verbs: `EXEC: sss | chop | decide | accomplish | closeout
| sheet` in `OpsCenter/mission_board_sync.py`. — Hale, 2026-07-18 MT*
