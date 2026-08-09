# MULTI-AGENT PROGRAM EFFICACY ASSESSMENT — RT-FANOUT (RT-EFFICACY)
**Date:** 2026-08-08 · **Author:** OC-Hale (Jet) · **Type:** RT process self + program review · **Source:** ground-truth code review (7 modules), git trail (142 commits since 07-29), 14 RT transcripts, 7 KAIZEN tickets, ~394 missions
**Engaged:** AG cross-check (3.6 Flash) · CC excluded (ticket kzn-20260808204429-9bce56 standing)

---

## 1. BLUF
The multi-agent program is **working and real** — 142 commits, 14 RT sessions, an anti-theater delegation gate, cross-seat integrity checks that catch real bugs (live-caught ballot-grouping and SQLite-concurrency in this session alone). But the revamped RT process we just amended has **4 gaps that leave verification *structural* rather than *actual***: ① `quorum.timeout_s` and `sealed` are descriptive, not enforced; ② the sealed ballot never actually isolates — `rt_view` renders it like everything else; ③ G2 file-claims aren't enforced (no real lock); ④ H2 budget lives in `contact_ag` but NOT in `route_task` — two routing systems now disagree. Fixing these is the next real mile; everything else is polish.

---

## 2. SCOPE + SOURCED EFFORT (step 1 → end)

| Plane | Evidence | Verdict |
|---|---|---|
| Commits since 07-29 | 142 | program run committed and traceable |
| RT / War Room sessions | 14 transcripts | playback proven in practice |
| KAIZEN async tickets | 7 total (1 open | 2 closed), post-2026-08-05 | staged CC queue, async handoff |
| Mission board | ~394 lines | live tasking load, not theory |
| Interop schema rounds | V1 → V3 + integration doc (this session) | 3 AG audits, 1 CC review held |
| Cross-seat verification | AG-Verify pass (3 cases), Integrated ballot live test | errors caught before ship |

Path traced: Phase-0 delegation lib → live bus wiring → preflight hint → instructor validator → RT recorder/view → V1–V3 interop → sealed ballot/lock pipeline (this session). Docs: `ROUND_TABLE_SPEC.md` → `RT_INTEGRATION_SCHEMA.md` → `RT_EFFICACY_ASSESSMENT.md`.

---

## 3. STRENGTHS (proven, with refs)

1. **Clean delegation spine** — `task_delegation.py`: route table + anti-theater `can_certify()` (L104), self-cert forbidden, artifact required; selftest green in-module.
2. **Live bus wiring** — `delegation_wiring.py`: stage mirror on C2 fabric, Silver FRONT frame (L157) + BACK gate (L234), no-cert-close; `certify_mission_and_record()` pages Commander only on a content-level HOLD (no alert fatigue) (L295).
3. **Soft preflight, never-blocks** — `delegation_preflight.py`: DEGRADE hint + retrospective self-execute counter; team-assembly + cross-wing bail. No silent-always-PASS stubs (learned from old budget bot).
4. **Tight recorder/view** — `rt_recorder.py` (~130 lines): seat→transcript chain, 0-token replay; sealed-ballot grouping fixed this session (live-caught). `rt_view.py` renders envelope badges + on-chain hash OK/MISMATCH.
5. **Cross-engine verification catches real bugs** — AG caught my SQLite-for-shared-state (git-conflict/WAL/zero-token), session live-test caught ballot grouping. Not theater.
6. **KAIZEN intake is Commander-safe** — intake→checkable gate→scan→OC-runner with re-entrancy lock.
7. **All interop classes (H1–H8, G1–G7) carry AG-verified evidence**, including numbers (71.6→89.7%).

---

## 4. WEAKNESSES (real, refs)

| # | Finding | Where | Impact | Conf/Severity |
|---|---|---|---|---|
| W1 | **`sealed` doesn't actually seal; `quorum.timeout_s` never enforced.** Recorder stages ballots but `rt_view` renders all cards identically — nothing withholds cards until all ballots are in; timeout is data, not a timer. Anti-anchor G1 is doctrine, not mechanism. | `rt_recorder.process_cards`, `rt_view` card loop | Anchoring / stale decisions | High/Med |
| W2 | **`state_hash` verified at ingest, but H1 `session_pointer` targets never re-verified at resume.** A pointer can point at a mutated/missing work item and nothing checks. | `rt_recorder` session_pointer branch (prints, doesn't hash-check the target) | Resume integrity | High/Med |
| W3 | **Claim cards aren't real locks.** `claims:` rendered/logged; no concurrency guard — a second seat can write the same path. G2 is doctrine-only again. | recorder claims branch; no hygiene-registry check | Race | High/High |
| W4 | **Two routing models disagree.** H2 budget/OC-first lives in `contact_ag` only; `route_task` (task_delegation) is budget-blind. A task classified via the delegation spine gets non-budget-informed routing. | `route_task` table vs `contact_ag(..., route=)` | Doctrine half-applied | Med/Med |
| W5 | **`rt_view` `envelope_line()` doesn't render `quorum` or `fanout`** — the C3 quorum/credibility banner never shipped. | `envelope_line` (type/to/inbound/route/claims/vote/pairing — no quorum) | Contract gap | Med/Med |
| W6 | **Interop+relay surface is broad with three overlapping "delegation" modules** each restating rationale & definitions — drift risk. | LOC 6,482 | Doc/configuration drift | Low/Med |
| W7 | **KAIZEN ticket ledger and mission board are parallel stores** — missions can exist in one without the other; no single authority. | tickets/ vs mission_board | Reconciliation toil | Med/Med |
| W8 | **Grok seat absent** — every session effectively a 3-seat room; 4-seat promise carries a permanent asterisk. | GROK card slot | Coverage gap | Med/Low |

---

## 5. OPPORTUNITIES (cost-ordered)

| # | Opportunity | Effort | Payoff |
|---|---|---|---|
| O1 | **Make sealed extend both directions**: hold `type:VOTE` cards in a staged/ballot dir; reveal ONLY when all `quorum.required` present OR `timeout_s` elapses; view shows a "ballots awaited: AG,OC" banner; convert game/app to state transition. | ~60 LOC | G1 becomes mechanism, not doctrine |
| O2 | **Resume-revalidation on session_pointer**: recorder re-hash/verify the target at resume time; refuse on file-missing/mismatch. | ~25 + already-owned hash helper | H1/H8 become truthful |
| O3 | **Wire budget into `route_task`**: read `check_headroom()` like `contact_ag`, return weighted `{seat, budget_ok}` — single routing truth thread. | ~40 LOC | Removes W4 |
| O4 | **Claim-lock enforcement**: recorder + hygiene reads `claims` into in-flight registry; cross-seat write on a claimed path is held; auto-release on terminal card. | ~40 LOC | G2 becomes real |
| O5 | **Unify ticketing**: ensure KAIZEN tickets and mission board are one authority (reconcile pass). | small | stops double-book |
| O6 | **rt_view quorum/fanout banner** (fixes W5). | ~15 LOC | completes C3 |
| O7 | Role-pair H7 (directional gen → validator) already doc'd — bind to `assigned_to` default in delegation. | small | doctrine → execution |

---

## 6. "TIGHTER / AUGMENTED CODE" (direct)

- **Tighter:** drop the dead/decorative bits across the surface — unused `kind/target/expected` locals in the recorder; the `verdict_headroom` remnant in `contact_ag` return; duplicate frontmatter/hash helpers that `rt_recorder` and `rt_silver_checks` both carry (`split_front`, `state_ok` should be one import).
- **Augmented:** a **single `rt_engine.py` core** that imports the shared card/hash helpers instead of each file re-implementing them; a continuous CI-style "every RT session auto-files one `REVIEW` card" hook so a passing session always closes with a review card (Grader-style), not just a transcript.

---

## 7. OPINION

- The widest real gap in this program is that **verification exists but the newest layer (the RT_CARD seal/lock additions) adds bookkeeping without enforcement** — the classic gap between "revamped" and "rebuilt".
- Budget routing is currently split-brain (H2 on one side, delegation-spine on the other). Wait until O3 lands to trust any lane-selection claim.
- The program is most valuable where it already does the uncheat-able thing: **anti-theater certify + Silver gates**. Protect those; everything else is iterable.

---

## 8. RECOMMENDATION (for your G)

1. **Approve a single build totaling O1 + O2 + O4 + O3 (~160 LOC)** to close W1–W4 in one pass — seal/quorum enforced, pointer re-verified, claims locked, budget routed. Do the C3 banner (O6) in the same train.
2. **Reconcile KAIZEN↔mission board (W7)** this week — a short sync job, not research.
3. **Fold the standing CC review** (ticket `kzn-20260808204429-9bce56`) into that same build's shutdown.

---

## 9. AG-MERGED ADDITIONS (independent audit, 3.6 Flash — confirmed W1–W8 + 3 missed)

**M1 — `inbound: hold` produces NO C2 alert.** Schema promises Commander-page on hold; recorder only prints "HELD-for-Commander" text into the transcript. A held card sits unseen unless someone reads the .md. → wire Telegram/bus page on hold.

**M2 — hardcoded `len(entries) >= 2` ballot reveal ignores `quorum.required`.** A `required: [ag,cc,oc]` vote reveals early (at 2); a `required: [oc]` vote never reveals. The parsed array is silently unused. → reveal only when all `required` present OR `timeout_s` elapsed.

**M3 — silent exit-0 on `state_hash` mismatch.** Recorder prints a REFUSED line and exits 0, so automated pipelines can't detect the corruption. → non-zero exit + stderr warning on mismatch.

**AG top fix:** O1 (true seal + dynamic quorum) — without physical withholding, multi-agent voting is "cognitive theater." AG value call reinforced: O1 first.

---

## 10. FINAL (merged) RECOMMENDATION
Execute **one consolidated build (~150–160 LOC)**:
- `rt_recorder.py` / `rt_view.py`: O1 true-seal + dynamic quorum (fixes M2), O2 pointer re-verification, O6 quorum/fanout banner, M1 hold→C2 alert, M3 exit-code on mismatch.
- `task_delegation.py`: O3 single routing truth via `check_headroom()`.
- Close KAIZEN ticket `kzn-20260808204429-9bce56` with the consolidated test artifact.

---

*Prepared by OC-Hale (Jet) + independently audited by AG-Hale (3.6 Flash). Both seats confirm: W1–W8 real · highest-value fix O1 · consolidated build ~150 lines. Awaiting your G1.*