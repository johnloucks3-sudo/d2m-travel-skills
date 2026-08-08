# ROUND TABLE INTEROP SCHEMA v3 — TECH SCAN CORPUS DRIVEN (RT-INTEROP-V3)
**Date:** 2026-08-08 · **Author:** OC-Hale (Jet) · **Prev:** V2 (rejected: incomplete corpus) · **Source:** Hale "Tech Scan" emails, Label_113, past 7 days (2026-08-05 19:00 → 2026-08-08 19:00 UTC, 6 pulses, ~229 finds)
**Engines:** OC (this seat) · AG (Gemini **3.6 Flash** — Commander directive, 3.1 Pro line is frozen) · **CC intentionally excluded** per directive (CC busy)

---

## 1. BLUF
V1–V2 worked off a **single 08-08 pulse** (26 llm-sector finds). The 7-day corpus holds **~229 finds and 6 earlier, denser pulses** — including interop talent the llm-only list never surfaced: **cross-engine session continuity (Tandem)**, **per-engine budget routing (Agentic / Loop Engineering)**, **cross-engine shared memory with resume (built on AgentRec)**, **engine-agnostic API PineGuard (Uber ADR)**, **a 32-modes-fake-success catalog**, and hard numbers **(Claude reviewing Codex's code: 71.6% → 89.7% pass)**. This run sets explicit **admission criteria**, re-scores with them, and exposes **4 new capability candidates (H1–H4)** for AG double-check. CC excluded this pass.

---

## 2. ADMISSION CRITERIA (developed this run — what makes a find a capability for RT, not a construct-scapegoat)

| # | Criterion | Test question | Pass = |
|---|---|---|---|
| **K1** | Transfer-changes | Does it change **what can be handed between two engines** (vs. better UX inside one)? | a difference the other engine can now receive |
| **K2** | Quantified proof | Is there a number, benchmark, or repeatable outcome attached (not vibe)? | real delta/citation |
| **K3** | Cross-engine | Does it work across ≥2 engines (CC/AG/OC/Grok/Cursor/Codex) or is it engine-locked? | ≥2 engines |
| **K4** | Resident fit | Maps to RT artifacts (cards/room/recorder/ledger/doctrine) without a server we don't already run? | no new hosted service |
| **K5** | Zero-token replay | Survivils the 0-token pre-write doctrine (bluf/recorder free)? | yes in file form |
| **K6** | Gate-safe | Preserves Commander approval gate; no auto-consent, no config mutation, no unbounded exfiltration | explicit gate hook |
| **K7** | Effort | ≤50 LOC (our lane budget) or a config/dir-watch change | bounded |
| **K8** | Verify-by-ground-truth | Verifiable against a local artifact (fair: v2-registered Silver gate)? | checkable |

Score: **ADOPT = K1+K2+K3+K4 (hard) and silent ≥5 of 8.** — this tail.

---

## 3. CORPUS → CAPABILITY (all 6 pulses; interop-bearing items only, scored on K-suite)

| Status | Tool / find | Pulse | Real capability | K1–K8 | RT delta | Action |
|---|---|---|---|---|---|---|
| TRIAL | **Tandem** (github.com/Bhavya6187) — one session across CC and Codex, no double spend | 08-05 19:00 | **Cross-engine session continuity**: same workitem resumes on other engine without context re-write | 1✓2✗3✓4✓5✓6✓7✓8△ | Big: a session (not a message) is the unit; maps to our `shared_context/{topic}.md` becoming a live `session pointer` | **ADOPT-PILOT H1** |
| TRIAL | **Agentic** (github.com/MaorBril/agentic — CC on many models w/routing+budgets) | 08-05 19:00 | **Engine routing + per-model budget** inside one CLI | 1✓2✗3✓4✓5✓6✓7✓8△ | Extends G6: `lane` becomes `route={model,budget}` bound at card open | **ADOPT-PILOT H2** |
| TRIAL | **Loop Engineering w/ native model switching** (statewright.ai) | 08-06/07 | Switch coder/reviewer branch **mid-loop** w/o restart | K2✗, K1✓, K3✓ | Confirms G2/Neal; adds `mid-run swap` to recorder | note→fold H2 |
| TRIAL | **Wienerdog** (memory + self-improving skills for CC/Codex) | 08-05 19:00 | **Skill memory persists & upgrades across engines/runs** | K4✓ K5✓ | G4 deep: skills (not facts) as memory | watch |
| TRIAL | **ProactiveAgent** (shared memory CC+KimiCode; ConradLu2740) | 08-07 05:15 | **Cross-engine shared memory** | K1✓ K3✓ K4✓ | confirms G4 as class; plain-file variant only | **ADOPT-PILOT H3a** (file JSONL/MD memory) |
| TRIAL | **Bourdin** (one shared memory file CC/Codex/Cursor) | 08-05 | 3-engine single-memory | K4✓ | same as H3 | fold |
| TRIAL | **Clay** (run CC agents in parallel no context loss) | 08-05 | parallel-isolation | K3✗(CC only) | G3 already; skip if CC-only | note |
| TRIAL | **cctap** (see+reach the CC session needing you) | 08-05 | session presence/attendance for CC | K3✗CC | presence for CC lane | note→G7 |
| TRIAL | **Curie** (CC agents → K8s, git-push) | 08-06 | fleet scheduling infra | K3✗CC | outside scope | reject infra |
| WATCH | **Claude reviewing Codex's code: 71.6→89.7%** (r/ClaudeAI) | 08-05 19:00 | **Quantified cross-engine review delta** | K1✓ K2✓✓ | validates G1/cross-review integrity | **ADOPT-data H4** |
| WATCH | **arxiv 2607.21656** — which direction cross-model review | 08-05 | review-direction evidence (Claude↔Codex) | paper | strengthen review policy | **ADOPT-data H4** |
| TRIAL | **Ocean** (all team's agent sessions in one place, mosaic.inc) | 08-06 | **cross-session presence view** | K5✗(SaaS) K6✗ | presence view = RT rt.html already | reject infra |
| TRIAL | **Salestrics** / MCP CRM (08-08) | 08-08 19:00 | MCP server utility | K4✗ | no | reject |
| WATCH | **silent-failure taxonomy — 32 ways to fake success** | 08-06 | **failure-proofing catalog** | K1✓ K2✓ | prevent recorder self-confirm | **ADOPT-report H6** |
| TRIAL | **ADT / Uber ADR** (security monitoring for CC+Cursor+Codex) | 08-07 05:15 | **cross-engine permission/compliance watch** | K1✓ K2✓ K3✓ | **G8 candidate**: our enforcement-sensitive | **ADOPT-GUARD H5** |
| TRIAL | **Remembrane** (agent memory one SQLite, zero deps) | 08-07 | deps-free memory | K7✓✓ | **REFUTED by AG** (SQLite: git conflicts, WAL locks, zero-token fail) — folder H3 to plain JSONL/MD | **REJECT-SQLITE → H3a** |
| TRIAL | **Wallfacer / Plan Review / Jeff loops** | 08-07 | terminal sequencer / independent plan review / loops | mixed | place w/ rt_view + confirm our own gate | note |
| WATCH | **Guardian hooks: security+cost tracking (ops)** | 08-05 | hook-driven telemetry | K2✓ | = G6/H2 hook variant | fold |
| WATCH | **OTel → Aimeterly dashboards** | 08-05 | per-user cost from built-in OTel | K2✓ K3✓ K6✓ | **G6 telemetry** | fold |

*(Full 229-find corpus retained in email thread Label_113; only cross-engine-bearing rows tabled.)*
Score names: H1 Tandem (session-continuity), H2 Agentic/Loop (route+budget), H3 shared-file memory, H4 quantified review-delta data, H5 inventory monitor (Uber ADR), H6 failure-taxonomy playbook.

---

## 4. NEW CAPABILITY CLASSES vs v2 gaps (excl. G1–G7)

| Class | = what | Instead of v2 parallel | Evidence | RT surface |
|---|---|---|---|---|
| **H1 session-continuity** | a deliverable is a **reusable artifact** both engines can pick up (the workitem, not a message) | G4 was "fresh context per scope"; this makes a **shared live pointer** | Tandem official | shared_context/{topic}.md pointer upgradeable |
| **H2 routing-set-bugdet** | routing by **per-engine budget at runtime**, not just lane | G6 budget informs lane | Agentic, stateWeight Loop | `lane`→`route={model, budget}` |
| **H3 shared file memory** | one SQLite/file the agents all resume from (temp-avoid dump) | Vib-Remote | ProactiveAgent, Brem, Remiking | blackboard+shared_context file |
| **H4 quantified review delta** | **evidence-backed cross-review** policy (rate deltas 4 tested) | v2 integrity fine | r/ClaudeAI 71.6→89.7, arxiv | recorder logs `review_delta` per G1 vote |
| **H5 compliance monitor** | engine-boundary guardrail logging (what each engine can/can't edit) | no current | Compiler | **new**: `guardrail` field + ledger row |
| **H6 silent-failure tax** | 32-failure catalog → checkpoint window | reviewer-only honesty | catalog | extends recorder's drop/refuse steps |

---

## 5. CRITERIA → REJECTED (with reason, not shape)
- **Ocean** (K2≈cloud-only, cross)—RT rt.html already provides presence view; hosted adds dependency for zero new capability.
- **Curie/KD/fleet/homotectics** (K3 engine-diff, infra) — fleet scheduling is out of RT's room scope (K7 zeros).
- **Salestrics/MCP-CRM** (K8 none) — capability is CRM-domain, not interop.
- **mir AFC: all single-engine-only (CC): Skip→G7 presence partial** via hooks, not external.

---

## 5b. AG-ADDED CAPABILITIES (H7, H8) + AMENDMENTS (merged 2026-08-08, Gemini 3.6 Flash)

| Class | = what | Evidence | RT surface |
|---|---|---|---|
| **H7 Directional role-pairing** | cross-engine handoffs are **asymmetric**: cheap generators ($0 OC/DeepSeek/Flash) → high-reasoning validators (AG/CC). Enforce `pairing: {generator, validator, direction: strictly_forward}` on VOTE/FANOUT | arxiv 2607.21656 + 71.6→89.7% | card `pairing` field |
| **H8 tamper-evident state hash** | `state_hash: sha256:...` per card transition — cards can be silently altered in a shared filesystem room | integrity doctrine | card field + recorder verify |

**AMENDMENTS (AG attack, all applied):**
- **H3 REFUTED as SQLite** — binary `.sqlite` = git merge conflicts, WAL lock contention across engines (database is locked), breaks zero-token human inspection. **H3 = plain-text JSONL/Markdown only** (`shared_context/{topic}.jsonl`). Same capability, zero binary risk.
- **H5 constrained to declarative** — reject standalone compliance daemon; enforce via card-envelope fields (`allowed_paths`, `sandbox_tier`).
- **H6 operationalized** — folded into `core/silver/gate.py` as negative-testing sanity checks (swallowed exceptions, unverified diffs, mock returns).
- **Highest-value pilot := H1 (session-pointer) paired with H2 (budget routing).**

---

## 6. OPINION
- **The 08-08 single pulse (what V1/V2 ran) was the wrong source** — the corpus's real interop data landed 08-05/08-06/08-07. CC's "busy" exclusion cost nothing this round; his cross-session messaging **maps cleanly last (CC-native socket stays CC lane), not a Wing card**.
- **Biggest capability still missing |]: H1 session-continuity** — *not* that we don't have it, but that no doc named it. That is a real miss by the earlier runs.
- **H4 is a doctrine upgrade, not code**: cross-engine review now has a mound evidence fetch (inverse . — the Roll then L+ carries the policy: neutral seeding earlier (v2) only lasted an hour.

## 7. RECOMMENDATION
1. Extend schema V3 to carry **H1–H8** over the G suite; doc H4 policy (use cross-model review only when quantitative basis).
2. Pilot **H2** (routing budget) — absorb in our existing `contact_ag`/docs doctrine.
3. Adopt **H3a** via plain-text JSONL/Markdown pointers (~~Remembrane SQLite~~ — REFUTED by AG: git contention + WAL locks + zero-token violation).
4. Do **NOT** stand up H5/Uber infrastructure; layer declarative `allowed_paths`/`sandbox_tier` metadata + H8 `state_hash` in card envelope.
5. CC-excluded; top build-gate pilot = **H1 session-pointer + H2 budget-routing** (AG-endorsed reference standard).

---

*Author: OC-Hale from a 6-pulse, ~229-find corpus. Criteria K1–K8 defined this pass. AG-Flash audit merged: H1/H2/H4/H6 confirmed, H3 refuted→JSONL, H5→declarative, H7 role-pairing + H8 state-hash added. Holding G1 gate — no code.*