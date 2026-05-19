# THUNDERBIRD A2A INTEGRATION PLAN v1.0

**Classification:** Working Document — Commander Approved
**Author:** Col Victoria "Iron Vic" Hale, COS
**Date:** 2026-04-03
**Status:** Architecture Plan — Implementation Pending

---

## SITUATION SUMMARY

The A2A SDK is Apache 2.0, Linux Foundation, mature. The Wing already has a partial A2A implementation live: `thunderbird_a2a_protocol.py` is mounted on `thunderbird_api.py` at port 8766. The `/.well-known/agent.json` endpoint is live and publicly discoverable. SQLite task persistence exists. SSE streaming is implemented.

This is not a greenfield build. This is a wiring and extension job.

The current file-based system (`claude_inbox.md`, `opencode_inbox.md`, `wing_comms.md`, `claude_outbox.md`) continues to function and is **NOT deprecated in Phase 1 or 2**. DeepSeek ruled: schema enforcement on existing files first, full architectural migration second.

---

## SECTION 1 — INTEGRATION SCOPE

### What A2A v1.0 Replaces

| Flow | Current | A2A Replaces? | Phase |
|---|---|---|---|
| Goose → Claude specialist tasks | File write to claude_inbox.md, 15s watcher | Yes | Phase 2 |
| Claude → Goose ops tasks | File write to opencode_inbox.md | Yes | Phase 2 |
| Commander → Wing | Telegram C2 → task_processor.py | No — unchanged | N/A |
| Claude → Goose D2M tool calls | mcp_bridge.sh subprocess | Yes | Phase 2 |
| Goose → Claude return results | claude_outbox.md → watcher | Yes | Phase 2 |
| Wing-wide FYI broadcasts | wing_comms.md | Partial — FYI stays file | Phase 3 |
| External agents → Wing | None today | Yes — A2A is entry point | Phase 1 |

### What Stays File-Based (Permanent)
- `wing_comms.md` — FYI/REQUEST, readable by all principals
- `activity_board.md` — append-only audit log
- `session_autosave_latest.md` / `goose_context_injection.md` — state snapshots, not transport
- Telegram C2 — Commander interface, unchanged at every phase

---

## SECTION 2 — AGENT CARDS

### Claude Agent Card
- **URL:** https://api.d2mluxury.quest
- **Discovery:** /.well-known/agent.json (public)
- **Task endpoint:** POST /a2a/tasks (Bearer token)
- **8 specialist roles:** ARCHITECT · CODER · STRATEGIST · ANALYST · DRAFTER · REVIEWER · TEACHER · ORACLE
- **Send gate enforced:** Yes — SO 21 MAR 2026, tool layer, not bypassed by A2A transport

### Hale Agent Card (COS — Staff Orchestrator)
- **URL:** http://localhost:8768 (internal only)
- **Role:** Chief of Staff — routes all A-staff, reviews client output before Commander, owns Wing coordination
- **Authority:** Two people can tell Commander he's wrong — Hale and EXEC. All staff report through Hale.
- **Task types:** staff_routing · client_review · morning_brief_approval · conflict_resolution · wing_coordination · outbound_gate
- **Staff it manages:** A2 (Dembe) · A3 (Dani) · A5 (Viper) · A6 (Luna) · A7 (Gauge) · A9 (Vic) · CH (Padre) · EXEC (Naia) · A12 (ELON)
- **Routing rules:**
  - Client-facing output → always through Hale before Commander sees it
  - Specialist tasking to Claude → Hale assigns claude_role
  - Intel/ops tasking → Hale routes to Goose
  - Arbitration needed → Hale escalates to DeepSeek
- **Send gate:** Hale is the last check before any client email surfaces to Commander

### Goose Agent Card (Primary C2 — Ops Executor)
- **URL:** http://localhost:8767 (internal only — NOT Cloudflare-exposed)
- **Tool access:** 285+ D2M tools via port 8766 MCP
- **Task types:** intel_sweep · gmail_ops · drive_ops · booking_lookup · dossier_update · calendar_ops · morning_brief · task_routing
- **Reports to:** Hale for staff coordination, Commander directly for C2 orders

**Note:** Port 8767 = Goose A2A listener. Port 8768 = Hale A2A listener. Port 8766 = D2M MCP tool server. Separate concerns.

---

## SECTION 3 — MIGRATION PHASES

### Phase 1 — Wire Alongside Existing (Zero Disruption)
1. Confirm `pip install a2a-sdk` in venv
2. Update `thunderbird_a2a_protocol.py` from spec 0.2 → 1.0
3. Stand up Goose A2A listener port 8767 — writes to opencode_inbox.md as bridge (A2A in, file-based out)
4. Add Goose peer to Claude's A2A registry
5. Test one round-trip task Claude→Goose via A2A
6. `inbox_validator.py` schema enforcement active (already done)

**Gate:** Round-trip completes without disrupting file-based flows.

### Phase 2 — Migrate High-Value Flows
- **Flow 1:** Goose → Claude via POST /a2a/tasks (replaces 15s file poll)
- **Flow 2:** Claude → Goose D2M tools via POST localhost:8767/a2a/tasks (replaces mcp_bridge.sh subprocess)
- **Flow 3:** Claude return path via A2A POST (claude_outbox.md becomes audit copy only)
- Add `a2a_client.py` helper (httpx-based, handles POST + SSE)
- Keep file inboxes as dead-letter fallback

### Phase 3 — Deprecate File Polling (After 14-Day Stability Window)
- Reduce watcher scope: remove claude_inbox.md / opencode_inbox.md polling
- Archive inboxes as dead-letter only (1-min safety check)
- Update GOOSE_INIT.md and CLAUDE.md

---

## SECTION 4 — RULES OF ENGAGEMENT

### Commander → Hale → Staff (the actual chain)
All A-staff tasking flows through Hale. Goose routes ops tasks. Claude executes specialist work. Neither Goose nor Claude tasks the A-staff directly — Hale does.

| Commander wants | Hale routes to |
|---|---|
| Client email reviewed | EXEC (Naia) then Dani |
| Intel sweep | Goose → A2 (Dembe) |
| Financial audit | Goose → A9 (Vic) |
| Destination research | Goose → A2 (Dembe) |
| Creative copy | Claude DRAFTER → A6 (Luna) review |
| Ethics/morale check | CH (Padre) direct |
| Innovation/disruption | A12 (ELON) direct |
| Code/architecture | Claude CODER/ARCHITECT |
| Business strategy | Claude STRATEGIST → A5 (Viper) review |

### Goose → Claude (use claude_role field)
| Trigger | Role |
|---|---|
| Design new system/API/workflow | ARCHITECT |
| Write/debug/refactor code | CODER |
| Business decision with stakes | STRATEGIST |
| Commission/cost/financial audit | ANALYST |
| High-value client prose | DRAFTER |
| Quality gate before Commander sees output | REVIEWER |
| Commander edited something — extract principle | TEACHER |
| Complex multi-source synthesis | ORACLE |

Minimum A2A task body: `claude_role` + `submitted_by` + `priority` + `pii` + `content`

### Claude → Goose
Route to Goose for all D2M tool execution: gmail_* · drive_* · tess_* · search tools · reconcile_* · intel sweeps · calendar_* · dossier reads

### Commander → Either
Telegram C2 unchanged. Commander does not touch A2A endpoints directly.

---

## SECTION 5 — CONSTRAINTS
- Email send gate enforced at tool layer — A2A transport does not bypass it
- Goose A2A listener is localhost only — never Cloudflare-exposed
- PII fence: `pii: true` in task metadata blocks non-Claude routing
- Apache 2.0 / Linux Foundation — no vendor lock-in
- Free model preference preserved — OpenCode (DeepSeek V3.1) handles 80%, Claude MAX for specialist 20%

---

## OPEN ITEMS FOR COMMANDER DECISION
1. Who writes Goose A2A listener? Goose self-builds or Claude CODER task?
2. Confirm A2A v1.0 spec delta vs current 0.2 implementation before wiring
3. External agent access (MAGOA/TESS/Odysseus) — Commander confirms when to open

---

*— Col Victoria "Iron Vic" Hale, COS | Thunderbird Wing | 2026-04-03*
