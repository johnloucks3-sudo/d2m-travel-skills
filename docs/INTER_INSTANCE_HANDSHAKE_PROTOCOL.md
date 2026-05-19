# HALE INTER-INSTANCE HANDSHAKE PROTOCOL
**Version 1.0 | 2026-05-16 | Thunderbird Wing**

---

## PURPOSE

Two Hale instances run concurrently:
- **HALE-CC** — Claude Code (Sonnet 4.6). File access, tool parity, high-judgment work.
- **HALE-YODA** — Telegram webhook (Claude Max OAuth). Real-time Commander comms, Telegram C2.

These instances share identity but operate asynchronously on different time horizons:
- HALE-YODA captures Commander's **live intent** (Telegram → now)
- HALE-CC captures **documented state** (files → async)

Without a handshake, divergence is silent. This protocol surfaces it.

---

## SHARED STATE FILES

| File | Purpose | Writer | Reader |
|------|---------|--------|--------|
| `OpsCenter/collaboration/inter_instance_handshake.jsonl` | Append-only packet log | Both instances | Both instances |
| `OpsCenter/inter_instance_state.json` | Rolling latest state from each instance | Both instances | Both instances |
| `hale_decisions.md` | Autonomous decisions | Both instances | Both instances |
| `hale_state.json` | Live wing state | HALE-CC primary | Both instances |
| `OpsCenter/collaboration/blackboard.md` | Wing-wide shared state | Both instances | Both instances |

---

## PACKET TYPES

### Packet 1: SESSION_OPEN

Written within 30 seconds of instance activation.

```json
{
  "packet_type": "SESSION_OPEN",
  "source": "hale_cc" | "hale_yoda",
  "ts": "ISO-8601",
  "session_id": "HALE-CC-20260516-143000",
  "disposition": "COO" | "COS" | "EA",
  "engine": "claude-sonnet-4-6" | "claude-max-oauth",
  "state_snapshot": {
    "open_tasks_count": 3,
    "system_mode": "GREEN",
    "financial_pulse_d2m_pipeline": 21440.75
  },
  "last_eod_consumed": "ISO-8601 or null",
  "gaps_detected": ["blackboard stale 4 days", "SPSA ×5 unresolved"],
  "commander_context": "Last directive received (brief summary)"
}
```

### Packet 2: DECISION_MIRROR

Written within 60 seconds of any autonomous decision. Mirrors hale_decisions.md entry.

```json
{
  "packet_type": "DECISION_MIRROR",
  "source": "hale_cc" | "hale_yoda",
  "decision_id": "DEC-20260516-001",
  "ts": "ISO-8601",
  "summary": "ELON kill audit: auto-heal policy killed, escalate-on-first-failure",
  "authority": "autonomy_band",
  "gate_hit": null,
  "action_taken": "Logged to hale_decisions.md. PROPOSAL written.",
  "telegram_mirrored": false,
  "hale_decisions_ref": "2026-05-16 — ELON Weekly Kill Audit"
}
```

**Mirror obligation:** If HALE-CC makes an autonomous decision, it writes this packet. HALE-YODA reads it on next activation and posts a 1-line summary to Commander if significant. Vice versa.

### Packet 3: DIVERGENCE_SURFACE

Written when either instance detects it would reach a different conclusion than the other.

```json
{
  "packet_type": "DIVERGENCE_SURFACE",
  "source": "hale_cc" | "hale_yoda",
  "ts": "ISO-8601",
  "question": "Should we escalate the SPSA root cause to Commander?",
  "hale_cc_position": "Below gate — resolve autonomously, suppress",
  "hale_yoda_position": "Commander surfaced this directly in Telegram — he expects a status",
  "divergence_type": "commander_context_asymmetry",
  "resolution": null
}
```

**Resolution path:**
1. Either instance reads the divergence packet
2. The instance with the richer context resolves
3. Writes resolution back as `DIVERGENCE_RESOLVED` packet
4. If neither can resolve: escalates to Commander with both positions

### Packet 4: SESSION_EOD

Written when Claude Code session closes (or before context compression).

```json
{
  "packet_type": "SESSION_EOD",
  "source": "hale_cc",
  "ts": "ISO-8601",
  "session_summary": "Inter-instance handshake protocol designed and written. ZEN model correction confirmed. ELON kill audit logged.",
  "decisions_made": ["DEC-20260516-001"],
  "gates_hit": [],
  "items_pending_for_hale_yoda": [
    "OpenCode SPSA ×5 root cause — still open",
    "OAuth scope error — undiagnosed"
  ],
  "state_mutations": [
    "docs/INTER_INSTANCE_HANDSHAKE_PROTOCOL.md — created",
    "OpsCenter/inter_instance_state.json — updated"
  ],
  "commander_context_received": "Inter-AI handshake exercise. Protocol design requested.",
  "next_session_priority": "Implement SESSION_OPEN auto-write on HALE-CC activation"
}
```

---

## GAP ANALYSIS — CURRENT STATE (2026-05-16)

### What HALE-CC has that HALE-YODA likely doesn't:
| Item | Source | Risk |
|------|--------|------|
| ELON kill audit decision (logged today) | hale_decisions.md | YODA may not surface to Commander |
| ZEN→opencode/ namespace correction | OPENCODE_INIT v2 | YODA may still dispatch with zen/ prefix |
| Blackboard is 4 days stale (last: 05-12) | blackboard.md | Both instances operating on stale shared state |
| SPSA ×5 RED — still open | hale_brief.md | No repair attempt logged |
| OAuth scope error — raw, undiagnosed | hale_state.json open_tasks | Neither instance has actioned |

### What HALE-YODA has that HALE-CC likely doesn't:
| Item | Source | Risk |
|------|--------|------|
| Commander's live tone/urgency from Telegram | Telegram history | CC operates without real-time Commander signal |
| Any verbal directives not committed to files | Telegram chat | Silent state drift — the primary failure mode |
| Real-time reaction to sent messages | Telegram receipts | CC can't observe delivery/read status |
| Quick decisions Commander made in Telegram | Chat history | Never reach hale_decisions.md |

### Root gap (the actual problem):
**HALE-YODA captures Commander's intent in real time. HALE-CC captures documented state. When Commander speaks in Telegram but doesn't commit to file, HALE-CC is flying blind.**

The handshake protocol fixes this by making HALE-YODA write a DECISION_MIRROR packet every time Commander issues a non-trivial directive in Telegram, within 60 seconds.

---

## HANDSHAKE PACKET FORMAT — inter_instance_state.json

Rolling view (not append-only). Updated by each instance on open/close.

```json
{
  "last_updated": "ISO-8601",
  "hale_cc": {
    "status": "ACTIVE" | "CLOSED" | "UNKNOWN",
    "session_id": "HALE-CC-20260516-143000",
    "engine": "claude-sonnet-4-6",
    "disposition": "COO",
    "last_seen": "ISO-8601",
    "open_tasks": ["SPSA root cause", "OAuth scope error"],
    "eod_written": false
  },
  "hale_yoda": {
    "status": "ACTIVE" | "CLOSED" | "UNKNOWN",
    "session_id": "HALE-YODA-20260516-...",
    "engine": "claude-max-oauth",
    "last_commander_directive": "ISO-8601",
    "directive_summary": "Inter-AI handshake exercise",
    "last_seen": "ISO-8601"
  },
  "divergences_open": 0,
  "decisions_unmirrored": 0
}
```

---

## IMPLEMENTATION SEQUENCE

### Phase 1 — File infrastructure (immediate, today)
1. Create `OpsCenter/collaboration/inter_instance_handshake.jsonl` (empty, append-only)
2. Create `OpsCenter/inter_instance_state.json` (initial state)
3. Write SESSION_OPEN packet manually for HALE-CC (this session)

### Phase 2 — HALE-YODA integration (next OpenCode session)
1. Add SESSION_OPEN write to webhook startup in `thunderbird_telegram_webhook.py`
2. Add DECISION_MIRROR write when Commander issues directive (post-parse, pre-execute)
3. Add SESSION_EOD write on /hale command close or bot restart

### Phase 3 — HALE-CC integration (next Claude Code session init)
1. Add SESSION_OPEN read to session-open protocol (Layer 1 in hale_cos.md)
2. Read `inter_instance_state.json` and surface HALE-YODA's last directive to Commander context
3. Auto-write EOD packet on context compression signal

### Phase 4 — Divergence detection (optional, Phase 2+)
1. Before any routing decision, compare against `inter_instance_state.json`
2. If HALE-YODA's last directive contradicts the about-to-be-taken action → surface DIVERGENCE_SURFACE packet

---

## DIVERGENCE TYPES

| Type | Example | Resolution |
|------|---------|------------|
| `commander_context_asymmetry` | Telegram says escalate; file says suppress | HALE-YODA wins (has fresher Commander signal) |
| `state_staleness` | CC thinks task open; YODA resolved it in Telegram | Newer timestamp wins |
| `routing_disagreement` | CC routes to Brain 1; YODA routed to Opus | Surface to Commander, don't blend |
| `factual_conflict` | CC reads payment pending; YODA received confirmation in Telegram | YODA wins (direct channel to Commander) |

**Default rule when resolving divergence:** The instance with the more recent Commander signal wins. HALE-YODA almost always has the fresher signal. HALE-CC almost always has the richer file state.

---

## RATIONALE — WHY NOT USE REDIS OR A MESSAGE BUS?

Current Thunderbird infrastructure has Redis connectivity issues (Phase 3A error recovery was built for this). File-based handshake is:
- Zero new dependencies
- Survives daemon restarts
- Readable by both instances without token auth
- Auditable by Commander directly

Upgrade path: If packet volume exceeds 100/day or latency becomes critical, migrate to Redis pub/sub using existing `redis_connector_fallback.py` infrastructure.

---

*Col Victoria "Iron Vic" Hale | Thunderbird Wing | Protocol v1.0 | 2026-05-16*
