# ROUND TABLE INTEROP SCHEMA v2 — AG-HALE AUDIT VERDICT
**Date:** 2026-08-08 · **Reviewer:** AG-Hale (Gemini 3.6 Flash — High) · **Author:** OC-Hale (Jet) · **Target:** `RT_INTEROP_SCHEMA_V2.md`

---

## 1. BLUF
**RT-INTEROP-V2 APPROVED WITH 1 CONSTRAINED REFINEMENT (G5) AND 1 PROPOSED ADDITION (G7).**
V2 successfully corrects V1's flat-rejection blindspot by isolating 6 structural capability gaps (G1–G6) rather than discarding capabilities based on surface tool names. All 3 adopt-pilots (VOTE, CLAIM/RELEASE, FANOUT) are **CONFIRMED** for trial. G5 requires strict guardrails to prevent unauthenticated egress and playback loop hazards. One critical missing capability identified: **G7 Quorum & Liveness Assertion**.

---

## 2. G1–G6 CAPABILITY GAP AUDIT (ATTACK / CONFIRM)

| Gap | Title | Proof Source | AG-Hale Audit Verdict | Rationale & Technical Guardrails |
|---|---|---|---|---|
| **G1** | **Sealed-Ballot Anti-Anchoring** | #16 Cowchat | **CONFIRM** | Sequential playback (`AG → CC → OC`) introduces severe cognitive anchoring. `type: VOTE` with isolated staging until all ballots arrive enforces genuine independent peer review, directly fulfilling Hard Rule #1 (Integrity Double-Check). |
| **G2** | **In-Flight File Claims / Live Lock** | #11 Vibsync | **CONFIRM** | Macro-level `assigned_to` in mission board does not prevent concurrent file edit collisions. Adding `claim_paths: [...]` and `type: CLAIM` / `type: RELEASE` prevents race conditions across parallel seat operations. *Must enforce auto-release on card completion/timeout.* |
| **G3** | **Same-Question Fan-Out** | #18 Alyph, #7 Bench | **CONFIRM** | RT's turn-based FIFO limits parallel triage. `type: FANOUT` distributes an identical prompt to `[cc, ag, oc]` simultaneously, allowing side-by-side comparative matrices in `rt.html` for rapid divergence detection. |
| **G4** | **Fresh-Context-Per-Scope** | #21 Neal, #22 Clear/Compact | **CONFIRM** | Monolithic multi-card session history induces context rot. Card-level `scope: "shared_context/{topic}.md"` enforces explicit context boundaries and resets, matching Wing token discipline doctrine. |
| **G5** | **Push Egress Webhooks** | #16 Cowchat, #9, #25 Hooks | **ATTACK (Partial / Constrained Refinement)** | **Attack:** Arbitrary outbound HTTP webhooks in cards create data exfiltration risks, loop hazards, and break the zero-token offline playback contract. External sends also violate Commander approval gates.<br>**Refinement:** Restrict G5 strictly to *local whitelisted sinks* (Telegram C2 alerts via existing wrappers, local dashboard event stream) triggered strictly by the local recorder upon terminal card states (`DECISION`, `RELEASED`). |
| **G6** | **Budget-Informed Routing** | #12 AIUsageBar, `usage_ledger` | **CONFIRM** | Hard caps ($10/mo OpenRouter, CC 5X MAX bucket preservation, OC $0 default) require live budget telemetry. Binding `lane: auto \| oc \| ag \| cc` to real-time quota headroom automates cost-optimal seat selection. |

---

## 3. ADOPT-PILOTS EVALUATION

1. **Pilot #1: Sealed Voting Card (`type: VOTE`)** — **CONFIRMED**
   - *Impact:* Zero new services; isolates ballots in staging before simultaneous commit; eliminates confirmation bias in multi-engine audits.
2. **Pilot #2: File Lock Claims (`type: CLAIM` / `type: RELEASE`)** — **CONFIRMED**
   - *Impact:* Protects filesystem integrity during simultaneous multi-engine execution; integrates directly with existing `mission_board` state.
3. **Pilot #3: Fan-Out Dashboard (`type: FANOUT`)** — **CONFIRMED**
   - *Impact:* High-leverage architecture and consensus accelerator; renders comparative multi-model evaluations directly into `rt.html`.

---

## 4. MISSED CAPABILITY (G7 ADDITION)

### **G7: Quorum & Liveness Assertion (`quorum` / `presence`)**
- **Source:** Cowchat presence/heartbeat + distributed consensus quorum.
- **The Gap:** When issuing a `type: VOTE` or `type: FANOUT` targeting multiple seats (`model_set: [cc, ag, oc, grok]`), the protocol lacks deterministic quorum and timeout handling. If a seat is unauthenticated (e.g., Grok), rate-limited, or offline, the session stalls indefinitely waiting for missing inputs.
- **Proposed Schema Extension:**
```yaml
quorum:
  required: [ag, oc]           # Minimum mandatory seats for valid action
  optional: [cc, grok]         # Optional / best-effort seats
  timeout_s: 45                # Fallback timer before proceeding
  on_timeout: proceed | abort  # Deterministic failure mode
```

---

## 5. FINAL RECOMMENDATION
1. Commit `RT_INTEROP_SCHEMA_V2.md` with G5 constrained to local sinks and G7 quorum metadata added.
2. Stage implementation of the 3 Adopt-Pilots into `rt_recorder.py` and `rt_view.py` once Commander G1 design gate is cleared.
3. Maintain zero-dependency, local file-based architecture (no external MCP servers or background socket daemons).

— *V. Hale (AG Seat Lead)*
