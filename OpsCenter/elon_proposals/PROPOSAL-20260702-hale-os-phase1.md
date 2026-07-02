# PROPOSAL — HALE-OS Phase 1: OC Worker + Live Split Mission
**ID:** PROPOSAL-20260702-hale-os-phase1  
**Author:** ELON (A12) — Adoption & Disruption  
**Date:** 2026-07-02  
**Decision:** ADOPT — zero new spend, zero Commander gates crossed  
**Status:** PENDING COMMANDER AWARENESS (no approval required — operational lane)

---

## WHAT PHASE 0 SHIPPED TONIGHT (5 artifacts, fully integrated)

| Artifact | File | Value |
|---|---|---|
| Wing Org chart | `config/wing_org.yaml` | Single source of truth — change one line, re-compile everything |
| Lane compiler scaffold | `scripts/wing_org_compile.py` | Declare once → generate CC agent prompts + OC configs |
| Brain-Bridge board | `OpsCenter/brain_bridge_board.json` | CC↔OC task handoff, claim/complete protocol, DOGFOOD plan live |
| OC agent config | `config/opencode_agents.generated.json` | oc-scout-1 (DeepSeek) + oc-scout-2 (Grok-4) declared and scoped |
| Integration scoreboard | `scripts/integration_scoreboard.py` → `OpsCenter/integration_scoreboard.json` | Objective measure of 100% Integration progress |

**Current score: 83/100** — Seat 100 · Plane 100 · Memory 66 · Process 66.  
Two gaps remain: `scripts/opencode_worker.py` (OC task executor) and Graphiti wired into `.mcp.json`.

---

## WHAT PHASE 1 ADDS (next 7 days)

### Deliverable 1 — `scripts/opencode_worker.py` (Day 1–2)
The OC task executor: polls `brain_bridge_board.json` for unclaimed OC-lane tasks, claims one, shells out to `opencode` CLI, writes result back to board, marks complete. This is the missing wire between the board spec (which exists) and actual OC execution. One file, ~120 lines. Process score goes from 66 → 99.

### Deliverable 2 — Live Split Mission (Day 3–5)
Run a real Wing task (target: Dembe intel sweep on a cruise segment) as a split plan on the board:
- OC T1: DeepSeek scouts the segment (oc-scout-1)
- OC T2: Grok-4 cross-checks pricing (oc-scout-2)
- CC T3: Hale synthesizes + merges into dossier (cos-hale)

This proves the CC↔OC pipeline end-to-end on real work — not a dogfood stub.

### Deliverable 3 — Graphiti MCP wire (Day 5–7)
Add Graphiti to `.mcp.json` → Memory score goes from 66 → 99. Runbook already exists (`docs/GRAPHITI_SELFHOST_RUNBOOK.md`). This is a config change, not a build.

---

## 7-DAY TIMELINE

| Day | Action | Owner | Score Impact |
|---|---|---|---|
| 1 | `opencode_worker.py` shell + board-poll loop | ELON → Sterling review | Process 66→99 |
| 2 | Smoke test worker vs. board DOGFOOD plan | ELON | Validates loop |
| 3–4 | Design live split mission (Dembe intel) | Hale + ELON | — |
| 5 | Execute live split, verify CC merge | All three planes | Plane confirms 100 |
| 6 | Wire Graphiti into `.mcp.json` | ELON | Memory 66→99 |
| 7 | Run scoreboard, target ≥95 | ELON | — |

---

## LEVERAGE MATH

- Phase 0 cost: 1 session, ~0 net new token spend (compiler + board are read/write JSON, free tier)
- Phase 1 cost: OC worker build ~60 min Sonnet; live split mission runs on OC free-tier (DeepSeek/Grok-4 via Poe, zero Claude tokens)
- **Every research task that moves to OC frees ~4K–12K Sonnet tokens per run.** At current burn (9 runs/day active), that's 36K–108K tokens/day returned to client-voice and synthesis work
- **Zero new subscriptions, zero Commander gates, zero client-path risk**

---

## RISK

**Nil** on Commander's three gates:
- No client send
- No financial commitment
- Not strategic (>90d or >$5K) — this is operational plumbing, reversible in one config revert

**Only credible risk:** OC worker hangs on `opencode` CLI timeout → board task stays "claimed" indefinitely. Mitigation: 5-minute claim TTL with auto-release baked into the worker on Day 1.

---

## RECOMMENDATION

Execute Phase 1 in lane. ELON self-assigns deliverables 1 and 3; Hale co-owns the live split mission design on Day 3. Sterling reviews `opencode_worker.py` before merge (code lane). No Commander action required.

**Target score by 2026-07-09: ≥95/100.**

— ELON (A12) · Adoption & Disruption · 2026-07-02
