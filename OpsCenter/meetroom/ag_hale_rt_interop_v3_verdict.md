# ROUND TABLE INTEROP SCHEMA v3 — AG-HALE INDEPENDENT AUDIT VERDICT
**Date:** 2026-08-08 · **Reviewer:** AG-Hale (Gemini 3.6 Flash — High) · **Author:** OC-Hale (Jet) · **Target:** `RT_INTEROP_SCHEMA_V3.md`

---

## 1. BLUF
**RT-INTEROP-V3 AUDIT: H1, H2, H4, H6 CONFIRMED; H3 (SQLITE) REFUTED IN FAVOR OF PLAIN-TEXT JSONL/MD; H5 CONSTRAINED TO DECLARATIVE BOUNDARIES; 2 MISSED CAPABILITIES IDENTIFIED (H7, H8).**

```
[████████████████████] 100% Audit Complete (21 tools re-scored, 6 classes evaluated, 1 highest-value pilot isolated)
```

- **H3 (SQLite Shared Memory) does NOT beat H1/H2.** Introducing an SQLite binary file into a Git-tracked multi-seat workspace creates lock contention, breaks Git diff inspectability, and violates zero-token offline review. Plain-text JSONL/Markdown pointers (`shared_context/{topic}.md`) provide equivalent shared-memory capability with zero runtime overhead.
- **Single Highest-Value Pilot for Build Gate:** **PILOT H1 (Session-Continuity Workitem Pointer)** paired with **PILOT H2 (Budget-Informed Dynamic Routing)**.
- **Doctrine Additions:** Adopt H4 (Asymmetric Cross-Engine Review) and H6 (32 Silent-Failure Taxonomy) as verification standards for Silver Gate and `rt_recorder.py`.

---

## 2. INDEPENDENT CORPUS SCAN & ADMISSION SCORING (K1–K8 ATTACK AUDIT)

*Criteria applied: K1 (Transfer-Changes) · K2 (Quantified Proof) · K3 (Cross-Engine) · K4 (Resident-Fit) · K5 (Zero-Token Replay) · K6 (Gate-Safe) · K7 (Effort ≤50 LOC) · K8 (Verify-by-Ground-Truth).*

| Tool / Find | Pulse | Real Capability | K1–K8 Score | AG Audit Verdict | Attack Analysis & Ground-Truth Rationale |
|---|---|---|---|---|---|
| **Tandem** (`github.com/Bhavya6187`) | 08-05 19:00 | Cross-engine session continuity | 1✓ 2✗ 3✓ 4✓ 5✓ 6✓ 7✓ 8✓ (7/8) | **CONFIRM ADOPT (PILOT H1)** | Enables passing an in-flight workitem pointer between engines without context replay. Fulfills K1/K3/K4. Essential for multi-seat task handoffs. |
| **Agentic** (`github.com/MaorBril/agentic`) | 08-05 19:00 | Engine routing + runtime budget cap | 1✓ 2✗ 3✓ 4✓ 5✓ 6✓ 7✓ 8✓ (7/8) | **CONFIRM ADOPT (PILOT H2)** | Dynamically sets seat lane based on remaining budget headroom ($10/mo OpenRouter hard cap, CC 5X MAX preservation). Directly maps to `core/relay/engine_limits.py`. |
| **Loop Engineering** (`statewright.ai`) | 08-06/07 | Mid-loop model switching | 1✓ 2✗ 3✓ 4✓ 5✓ 6✓ 7✓ 8✓ (7/8) | **CONFIRM FOLD (into H2)** | Mid-loop escalation (e.g. OC stuck on logic -> escalate to AG/Claude) is a dynamic case of budget-informed routing. |
| **Wienerdog** | 08-05 19:00 | Self-mutating skill memory | 1✓ 2✗ 3✓ 4✗ 5✗ 6✗ 7✗ 8✗ (2/8) | **CONFIRM REJECT** | Auto-mutating skills across runs violates change-control, breaks reproducibility, and risks gate-safety violations (K6). |
| **ProactiveAgent** | 08-07 05:15 | Cross-engine shared memory | 1✓ 2✗ 3✓ 4✓ 5✓ 6✓ 7✓ 8✓ (7/8) | **REVISE ADOPT (H3)** | Shared state is valid, but must be plain-text/JSONL in `OpsCenter/shared_context/`, not a persistent daemon. |
| **Remembrane** | 08-07 | Single-file SQLite memory | 1✓ 2✗ 3✓ 4✗ 5✗ 6✓ 7✗ 8✗ (3/8) | **HARD REFUTE (SQLite Engine)** | SQLite introduces binary blob conflicts in Git, WAL lock contention across engines, and prevents direct human inspection. |
| **Bourdin** | 08-05 | 3-engine shared file memory | 1✓ 2✗ 3✓ 4✓ 5✓ 6✓ 7✓ 8✓ (7/8) | **CONFIRM FOLD (into H3-JSONL)** | Validates multi-engine shared context via filesystem. |
| **Clay** | 08-05 | Parallel CC agent execution | 1✓ 2✗ 3✗ 4✗ 5✓ 6✓ 7✗ 8✓ (4/8) | **CONFIRM REJECT** | Single-engine lock-in (CC only). Violates K3. |
| **cctap** | 08-05 | CC session presence/attendance | 1✓ 2✗ 3✗ 4✓ 5✓ 6✓ 7✓ 8✓ (6/8) | **CONFIRM REJECT (as tool) / FOLD G7** | Engine-locked to CC. Presence logic handled natively via RT G7 Quorum. |
| **Curie** | 08-06 | Fleet scheduling on K8s | 1✓ 2✗ 3✗ 4✗ 5✗ 6✗ 7✗ 8✗ (1/8) | **CONFIRM REJECT** | Massive infrastructure overhead. Violates K4/K7. |
| **Claude Reviewing Codex** (`r/ClaudeAI`) | 08-05 19:00 | Quantified cross-engine review delta | 1✓ 2✓ 3✓ 4✓ 5✓ 6✓ 7✓ 8✓ (8/8) | **CONFIRM ADOPT (DATA H4)** | Ground truth proof: cross-engine code review increases pass rate from 71.6% to 89.7% (+18.1%). Validates Hard Rule #1. |
| **arxiv 2607.21656** | 08-05 | Cross-model review directionality | 1✓ 2✓ 3✓ 4✓ 5✓ 6✓ 7✓ 8✓ (8/8) | **CONFIRM ADOPT (DATA H4)** | Confirms review efficacy is asymmetric: high-reasoning models must review high-throughput generators. |
| **Ocean** (`mosaic.inc`) | 08-06 | Cross-session SaaS dashboard | 1✓ 2✗ 3✓ 4✗ 5✗ 6✗ 7✗ 8✗ (2/8) | **CONFIRM REJECT** | External SaaS dependency. RT `rt.html` provides local, zero-token presence. |
| **Salestrics** | 08-08 19:00 | MCP CRM server | 1✗ 2✗ 3✗ 4✗ 5✗ 6✓ 7✗ 8✗ (1/8) | **CONFIRM REJECT** | Domain utility, zero multi-agent interop capability. |
| **Silent-Failure Taxonomy** | 08-06 | 32 ways agents fake success | 1✓ 2✓ 3✓ 4✓ 5✓ 6✓ 7✓ 8✓ (8/8) | **CONFIRM ADOPT (PLAYBOOK H6)** | High-leverage operational checklist for Silver Gate and peer reviews to catch shallow exits and false authority. |
| **ADT / Uber ADR** | 08-07 05:15 | Cross-engine boundary monitoring | 1✓ 2✗ 3✓ 4✓ 5✓ 6✓ 7✓ 8✓ (7/8) | **REVISE ADOPT (GUARD H5)** | Adopt declarative permission metadata in card envelopes; reject active compliance daemon. |
| **WallError / Jeff** | 08-05/07 | Autonomous loop automation | 1✓ 2✗ 3✗ 4✓ 5✓ 6✓ 7✓ 8✓ (6/8) | **CONFIRM REJECT / FOLD** | Redundant with existing Wing runner and task orchestration. |
| **Guardian Hooks / OTel** | 08-05 | Hook-driven cost telemetry | 1✓ 2✓ 3✓ 4✓ 5✓ 6✓ 7✓ 8✓ (8/8) | **CONFIRM FOLD (into H2)** | Telemetry feeds directly into H2 dynamic budget routing. |

---

## 3. AUDIT OF CAPABILITY CLASSES (H1–H6)

### **H1: Session-Continuity (`session_pointer`) — CONFIRMED**
- **Definition:** A durable, serializable pointer to an active workitem (`shared_context/{topic}_pointer.json`) that allows a different engine to resume execution without token replay.
- **Verdict:** **CONFIRMED**. Fills the critical gap between disjoint tool calls and full workflow continuity.

### **H2: Routing-Set-Budget (`route: {model, budget_cents}`) — CONFIRMED**
- **Definition:** Runtime lane selection determined by hard financial/quota headroom ($10/mo OpenRouter cap, CC 5X preservation).
- **Verdict:** **CONFIRMED**. Prevents quota exhaustion by binding card dispatch directly to `core/relay/engine_limits.py`.

### **H3: Shared File Memory — PARTIALLY REFUTED & REVISED**
- **Attack on SQLite Proposal (Remembrane):**
  1. *Git Contention:* Binary `.sqlite` files cannot be cleanly merged or diffed across Git branches.
  2. *Lock Hazards:* SQLite concurrent writes across independent OS processes (AG, OC, CC) risk `database is locked` panics.
  3. *Zero-Token Violation:* Commander and operators cannot inspect database state without CLI tooling.
- **Revision:** Implement H3 strictly as **Plain-Text JSONL / Markdown Shared Memory** (`OpsCenter/shared_context/{topic}.jsonl`). Zero binary dependencies, zero lock hazards, 100% human-readable.

### **H4: Quantified Review Delta (Asymmetric Peer Review) — CONFIRMED**
- **Definition:** Evidence-backed doctrine mandating cross-engine review pairs based on empirical benchmarks (71.6% $\rightarrow$ 89.7% pass rate).
- **Verdict:** **CONFIRMED (Doctrine Standard)**. Integrates directly into Hard Rule #1 (Integrity Double-Check).

### **H5: Declarative Compliance Guardrails — REVISED**
- **Definition:** Enforcement of file-access boundaries and sandbox scopes per seat.
- **Verdict:** **REVISED**. Reject standalone monitoring services. Enforce via declarative card envelope fields (`allowed_paths: [...]`, `sandbox_tier: strict`).

### **H6: 32 Silent-Failure Taxonomy — CONFIRMED**
- **Definition:** Negative testing catalog identifying false-authority failure modes (e.g. swallowed exceptions, unverified diffs, mock returns).
- **Verdict:** **CONFIRMED**. Embed as automated sanity checks in `core/silver/gate.py`.

---

## 4. MISSED CAPABILITIES (IDENTIFIED BEYOND H1–H6)

### **H7: Directional Role-Pairing Matrix (Asymmetric Model Allocation)**
- **The Gap:** V3 treats all cross-engine handoffs symmetrically. Arxiv 2607.21656 and Claude/Codex benchmark data prove that review efficiency is strictly **asymmetric**.
- **Capability:** Fast, cheap engines ($0 DeepSeek / Flash) act as *Generators*; high-reasoning engines (AG / Claude Sonnet Thinking) act as *Validators*. Schema should enforce directional routing:
  ```yaml
  pairing:
    generator: OC  # DeepSeek v4 ($0)
    validator: AG  # Gemini 3.6 Flash / Claude Sonnet
    direction: strictly_forward
  ```

### **H8: Tamper-Evident State Hash & Provenance Checksum**
- **The Gap:** In a shared filesystem room, cards can be silently modified or corrupted between turns.
- **Capability:** Include a SHA-256 state checksum on card state transitions (`state_hash: sha256:...`). Guarantees integrity and auditability without an external database.

---

## 5. PILOT SELECTION & BUILD-GATE RECOMMENDATION

### **Does H3 (SQLite) beat H1 or H2?**
**NO. Flatly NO.**
- SQLite is an unnecessary external construct that adds lock contention and breaks Git tracking.
- H1 and H2 deliver immediate operational leverage with zero added complexity.

### **Single Highest-Value Pilot for Commander Build Gate:**
### **PILOT H1: Session-Continuity Reusable Workitem Pointer**
*(Integrated with Pilot H2 Budget Telemetry)*

```yaml
---
card:
  id: RT-20260808-AG-001
  type: FINDING | VOTE | FANOUT | CLAIM | RELEASE
  sender: AG
  to: OC
  route:
    lane: oc
    max_budget_cents: 0
    fallback_lane: ag
  session_pointer:
    topic: "rt_interop_v3"
    workitem_file: "OpsCenter/meetroom/RT_INTEROP_SCHEMA_V3.md"
    target_state: "audited"
    rdd: "2026-08-08T16:00:00MT"
  claims: ["OpsCenter/meetroom/ag_hale_rt_interop_v3_verdict.md"]
  quorum: { required: [ag, oc], timeout_s: 45, on_timeout: proceed }
---
```

---

## 6. FINAL RECOMMENDATION
1. **Approve Schema V3 envelope** incorporating H1 (`session_pointer`), H2 (`route`), G1 (`vote`), G2 (`claims`), G7 (`quorum`), and H8 (`state_hash`).
2. **Reject SQLite (Remembrane)**; mandate plain-text JSONL/Markdown for shared context.
3. **Operationalize H4 & H6** into `core/silver/gate.py` as automated verification rules.
4. **Deploy Pilot H1 + H2** as the reference multi-engine execution standard.

— *Victoria Hale (AG Lead / Gemini 3.6 Flash)*
