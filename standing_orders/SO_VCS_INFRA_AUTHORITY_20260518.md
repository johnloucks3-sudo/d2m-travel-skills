# STANDING ORDER — VCS INFRASTRUCTURE AUTHORITY
## Thunderbird Wing, Dreams2Memories Travel, LLC
**SO Number:** SO-VCS-INFRA-20260518
**Issued:** 2026-05-18
**Authority:** Chief Gen John "Yoda" Loucks
**Effective:** Immediately
**Supersedes:** Nothing — extends SO-2026-05-04 into infrastructure domain explicitly

---

## COMMAND

Ms. Victoria "Victory" Hale, SES-6 (VCS) is hereby granted **full authority over all Thunderbird Wing infrastructure** — designation, deployment, maintenance, modernization, and retirement — in concert with JET and TALON.

Commander's directive (verbatim): *"Make it so."*

---

## AUTHORITY

### VCS Authority — Infrastructure Domain
VCS owns without Commander gate:
- Designation of T1/T2/T3 infrastructure tiers (pending Sterling validation + Commander selection)
- Staffing of all infrastructure maintenance and modernization assignments
- Directing JET and TALON to build, repair, restart, or retire any infrastructure component
- Approving Sterling's verification protocols and graduation thresholds
- Killing or sunsetting any T3 or deprecated infrastructure (ELON proposes, VCS approves)
- Issuing infrastructure-specific SOs and procedures

### Autonomy Level — Infrastructure
SO-2026-05-04 (95% autonomy, four gates) applies. For infrastructure specifically:
- No client sends involved → WF-17 gate does NOT apply
- No financial commitments → financial gate does NOT apply
- No new client contacts → new client gate does NOT apply
- No strategy direction changes → strategy gate does NOT apply

**Result: VCS operates at effective 100% authority on all infrastructure decisions.**
Commander receives infrastructure reports, not infrastructure permission requests.

---

## ENGINE COMMAND STRUCTURE

| Engine | Instance | Role under VCS |
|--------|----------|----------------|
| **JET** | Hale-OC (OpenCode / DeepSeek ZEN) | Build authority — all infrastructure construction, repair, and automation |
| **TALON** | Hale-OC second instance | Overflow build + parallel workstreams when JET is engaged |
| **VCS (Hale-CC)** | Claude Code / Sonnet | Design authority, verification oversight, staff coordination, Commander interface |

VCS directs JET and TALON. JET and TALON report to VCS via `OpsCenter/collaboration/opencode_outbox.md`. VCS surfaces to Commander only at structural gates or on Commander request.

**JET and TALON are not peers of VCS. They are subordinate engines under VCS command.**

---

## STAFF ASSIGNMENTS — INFRASTRUCTURE

### MAINTAIN Lane (keep T1/T2 alive)
| Staff | Mandate | Reports to |
|-------|---------|-----------|
| **Sterling (A7)** | Verification protocol + SLA tracking for all T1 systems. Hourly → weekly per graduation. | VCS |
| **Castillo (A5)** | Operating tempo — T1 restart SLA, modernization clock, weekly infra review | VCS |
| **Harlan (A9)** | Cost/API burn tracking per T1 component. Flags drift. No spend authority. | VCS |

### MODERNIZE Lane (fix what's broken, kill what's dead, automate what's manual)
| Staff | Mandate | Reports to |
|-------|---------|-----------|
| **ELON (A12)** | Weekly kill audit expanded to infra scope. One kill + one modernization per week. Proposes; VCS approves. | VCS |
| **Sterling (A7)** | Metrics-driven infra modernization targets. Feeds ELON. | VCS |
| **Castillo (A5)** | Modernization tempo — ELON proposes, Castillo ensures it ships | VCS |

---

## INFRASTRUCTURE TIERS (Working — pending Sterling validation)

### T1 — Mission-Essential (Wing stops if dead)
1. OAuth / token refresh timers (`claude-token-monitor.timer`, `claude-oauth-keepalive.timer`)
2. Tasking watcher (`d2m-tasking-watcher.service`)
3. MCP Server (port 8765)
4. Telegram gateway (D2MC2C + Dani bots)
5. TESS JWT auth
6. OpenCode / JET (Big Pickle)

### T2 — Operationally Important (Wing degrades)
1. Email C2 (n8n ETB 001 + `gmail_thread_reply`) — T1 upon T2 exercise completion
2. Signal gateway (YOGA:8080 / `thunderbird_signal_gw.py`) — T1 upon T2 exercise completion
3. Drive sync (rclone)
4. Headless Claude spawn infrastructure
5. `hale_shared_state.jsonl` cross-instance sync
6. Unified classifier (`core/comms/hale_unified_classifier.py`)

### T3 — Supporting (Survivable)
1. Chrome debug port 9222 — OFFLINE. ELON: decommission or fix.
2. Redis connectors — Phase 3A partial, single-POF risk. ELON: assess.
3. Legacy Haiku supervisor patterns — naming confusion. ELON: retire.

**Note:** Sterling refines this list. Commander selects final T1. VCS enforces.

---

## VERIFICATION (Sterling mandate)
- Sterling designs hourly checker: `scripts/verify_comms_health.py`
- Graduation threshold: Sterling sets (likely 95%+ over N days → weekly)
- Commander reviews Sterling's graduation criteria before it takes effect
- Failures route: `hale_decisions.md` + Telegram page if T1 goes red

---

## REPORTING
- **Daily:** VCS includes infra health in morning brief (system health table)
- **Weekly:** Castillo's business review includes infra modernization progress
- **On failure:** VCS pages Commander immediately if T1 goes red and auto-restart fails
- **On graduation:** Sterling notifies Commander when weekly cadence achieved

---

## REFERENCE
- **Autonomy charter:** `standing_orders/SO_HALE_REAL_AUTONOMY_20260504.md`
- **T2 exercise:** `standing_orders/SO_T2_HALE_SEAMLESS_COMMS_20260518.md`
- **Infrastructure plan:** Hale staff paper 2026-05-18 (conversation record)
- **JET/TALON:** `OpsCenter/hale_shared_state.jsonl`

---

*SO-VCS-INFRA-20260518 | Thunderbird Wing | Issued: 2026-05-18 | Authority: Gen Loucks | VCS: Victoria "Victory" Hale, SES-6*
*"Make it so." — Commander, 2026-05-18*
