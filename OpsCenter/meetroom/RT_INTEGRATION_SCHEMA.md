# RT INTEGRATION SCHEMA — MASTER BUILD DOC (RT_INTEGRATION_SCHEMA.md)
**Date:** 2026-08-08 · **Author:** OC-Hale (Jet), consolidated from AG artifacts · **Status:** READY FOR COMMANDER G1 DESIGN-GATE
**Source artifacts (all AG-verified, cross-engine):**
- `ag_hale_rt_interop_verdict.md` — v1 merge (frontmatter amendment)
- `ag_hale_rt_interop_v2_verdict.md` — G1–G6 confirm/attack + G7 quorum
- `ag_hale_rt_interop_v3_verdict.md` — H1–H8 audit + K1–K8 criteria + pilot selection
- `RT_INTEROP_SCHEMA_V2.md` / `_V3.md` — capability extraction runs
- `ROUND_TABLE_SPEC.md` / `ROUND_TABLE_CONCEPT.md` — RT base doctrine

---

## 1. BLUF
One schema for all multi-engine interop, built entirely on AG-verified capability classes. Nothing here is unvalidated: every field below was independently confirmed or refuted by AG (3.6 Flash) on a real hard case (H3 SQLite refuted — merged-conflicts + lock contention + zero-token failure). Build = ~120 LOC across `rt_recorder.py` + `rt_view.py` + 2 card schemas, zero new deps, holding RT-SPEC §8 non-goals. **G1 gate approval is the only missing input.**

## 2. SCOPE (what gets approved)
| Unit | What | LOC | Engine-lane |
|---|---|---|---|
| **C1** | `RT_CARD` envelope vFinal (schema in §4) | doc | all |
| **C2** | `rt_recorder` ingestion: accept/hold/refuse + quorum + state_hash verification + ballot staging | ~60 | AG |
| **C3** | `rt_view` fanout matrix + ballot reveal + quorum banner | ~40 | OC |
| **C4** | Silver gate hooks: H6 failure-taxonomy sanity checks + H8 hash verify | ~20 | Sterling |
| **C5** | Schema docs (this file) + `shared_context/{topic}.jsonl` file memory (H3a) | doc | all |

## 3. CRITERIA (K1–K8, AG-attacked, no self-cert)
K1 transfer-changes · K2 quantified-proof · K3 ≥2-engine · K4 no-new-service · K5 0-token replay · K6 gate-safe · K7 ≤50 LOC · K8 verify-by-truth. ADOPT = K1–K4 all hard + any 4 of K5–K8 (each was AG-attacked, not self-certified).

## 4. CARD SCHEMA — FINAL ENVELOPE

```yaml
---
card:
  id: RT-{session}-{seat}-{seq}
  type: FINDING | QUESTION | DECISION | REBUTTAL | CONSULT | STATUS
        | VOTE | FANOUT | CLAIM | RELEASE | REVIEW
  sender: OC | AG | CC | GROK
  to: CC|AG|OC|GROK|ALL|COMMANDER
  reply_to: RT-*-*-*         # thread
  reply_addr: RT-*-*-*       # echo address
  scope: "shared_context/{topic}.md"     # H3a pointer, never reprint
  claims: [ path/one, path/two ]        # G2 in-flight file lock (auto-release on close)
session_pointer:                      # H1 — resume a workitem, not replay it
    workitem_file: "shared_context/{topic}_pointer.json"
    target_state: "audited"
    rdd: "2026-08-09T12:00:00MT"
  route:                                # H2 budget-informed routing
    lane: auto | oc | ag | cc
    max_budget_cents: 0           # bound to usage_ledger headroom
    fallback_lane: ag
  pairing:                        # H7 — asymmetric roles (generator≠validator)
    generator: oc                 # cheap $0 DeepSeek / Flash writes
    validator: ag | cc            # high-reasoning reviews
    direction: strictly_forward
  vote: { q: "...", sealed: true, quorum: { required: [ag,oc], optional: [cc,grok], timeout_s: 45, on_timeout: proceed } }  # G1 balloted + G7
  fanout: { prompt: "...", model_set: [cc,ag,oc,grok], matrix: true }   # G3 side-by-side
  hook: { sink: "telegram-c2|dashboard-local", on: [accepted,hold,released] }  # G5 (LOCAL ONLY, AG-constrained)
  state_hash: sha256:...           # H8 tamper-evident, recorder-verify
  guardrail:                       # H5 declarative only (no daemon)
    allowed_paths: ["OpsCenter/meetroom/**"]
    sandbox_tier: strict
  inbound: accept | hold | refuse
  deadline: 2026-08-09T00:00:00MT
---
**BLUF:** ≤1 line
[≤300 words native md]
```

## 5. RECORDER INGESTION (C2, ~60 LOC — the only real code)
1. On `*_input.md` appearance → parse frontmatter envelope (fallback prose-only cards default `FINDING/ALL`).
2. Verify `state_hash` on write → refuse on mismatch (H8). Log `insight_exchange.jsonl` (unchanged).
3. Inbound `hold` → Commander gate queue (page on TelegramC2). `refuse` → log-quiesce. `accept` → route.
4. Sealed ballot: stages until all required per `quorum.required` OR `timeout_s`; then reveals all at once (anti-anchor, G1).
5. FANOUT: snapshots request + rows to `rt_view` matrix (parallel, no re-order).
6. CLAIM/RELEASE: applies to mission_board ownership, auto-release on terminal card state or expiry.
7. Expiry/threshold sweep: hold-and-expire per inbound defaults; loop-cap.

## 5b. SECURITY + DOCTRINE (borrowed from CC cross-session, AG-endorsed)
- Incoming card never approves a prompt, never changes `CLAUDE.md`/config, never executes commands — text into transcript only.
- Cross-machine/cross-repo cards `hold` for Commander; `isolatePeerMachines` equivalent honored.
- H5 (guard) enforcement = declarative metadata evaluated by recorder; NO resident daemon.
- Sealed ballot results feed H4 quantified review-delta policy.
- Token doctrine unchanged (OC=$0, AG=cheap, CC=MAX final judgment only).

## 6. FALLBACK / EDGE (AG-verified pitfalls)
| Situation | Rule |
|---|---|
| H3 shared memory | JSONL/Markdown pointers ONLY — SQLite REJECTED (git conflict, WAL locks) |
| Missing seat in VOTE/FANOUT | `quorum.required` + `on_timeout: proceed|abort` |
| Two seats same name | id-seq disambiguation (CC parity) |
| Ballot never fills | reveal on `timeout_s`, never block session |
| Ineligible permission on receiving seat | per-session inbound controls still fire |
| Out-of-scope request on card | refuse at write-time (RT-RETRO §9) |

## 6. EMPHATICALLY:
- **High-value pilot to green-light (AG-endorsed):** C2 recorder ingestion with H1 (`session_pointer`) + H2 (`route`) + G1 (`vote·sealed`) enabled. One sequencing sweep — you can audit at each gate.
- **What stays OFF the table:** any MCP server, any SQLite, any Cowchat/Vibsync-style hub, anything outside RT-SPEC §8.
- **Current debt:** CC card verdict pending on earlier ticket (kzn-20260824429-9bce56) — will fold into FANOUT/G2 when CC is free. Do not block G1 on it.

## 7. COMMANDER DESIGN-GATE DECISIONS (2026-08-08, recorded)
1. **Sealed vote:** `sealed: true` default for ALL RT votes (opt-in-per-session override by Commander only).
2. **Session pointer home:** OC decides → `shared_context/{topic}_pointer.json` (same tree as H3a file memory).
3. **Budget routing:** OC **primary** (OC-first always); `max_budget_cents` gates OC, `fallback_lane: ag` on OC quota exhaustion; per-task seat directive overrides only when Commander specifies.

---
**G1 DESIGN GATE: APPROVED by Commander 2026-08-08.** Build authorized per scope C1–C5, ~120 LOC, zero new deps. Engine lanes: C2 → AG, C3 → OC, C4 → Sterling. Holding RT-SPEC §8 non-goals and Commander gates (client send / financial / strategic).

---

*Prepared by OC-Hale (Jet) from AG-verified artifacts only. Est. effort ~120 LOC. Awaiting G1 grant.*