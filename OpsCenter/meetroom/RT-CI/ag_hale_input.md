# RT-CI CARD — AG SEAT (HALE-AG / GEMINI 3.6 FLASH)
**Context:** War Room RT-CI · Ground-Truth Verified

## BLUF
OC treats symptoms (stretching cron timers, manual paring) instead of the root flaw: **monolithic synchronous polling**. Replace polling sweeps with **Native Systemd Push Alerts (`OnFailure=`)**, **JIT Execution Preflights**, and **Credential vs. Code Decoupling**.

---

## 1. Where OC is Wrong
- **All-Whetstone Bottleneck:** All 53 skills map to `keeper: whetstone`. Centralization created the maintenance backlog.
- **Artifact-Driven DULL Storm:** 41/53 skills show 🟡 DULL purely from static `last_reeval` dates (frozen 2026-06-20/07-01), despite 100% passing probe outputs.
- **False REPLACE Alarms:** 9 REPLACE triggers conflate missing third-party keys (Amadeus, GitHub Actions) with software bugs.
- **Timer Proliferation:** 253 user timers exist (181 active). Reducing sweep cadence from 253 to 80 preserves cron sprawl.

---

## 2. Missing Paradigm Shifts
1. **Push-Based Daemon Telemetry:** Background daemons (`cloudflared`, `tailscale`, `n8n`, `ttyd`) use systemd `OnFailure=` — zero background poll timers needed.
2. **JIT Pipeline Preflight:** On-demand generators (surveys, proposals, dossiers) probe dependencies at runtime via `core.silver.gate.is_checkable()`, eliminating background polling.
3. **Decoupled Failure Triaging:** Split board states into `BROKEN_CODE` (actionable) vs. `KEY_GATED` (awaiting keys).

---

## 3. PC-1 to PC-5 Evaluation
- **PC-1 (Tiering): REPLACE.** Tier by invocation architecture: T1 Daemons (Push/Event), T2 C2/APIs (Periodic Sweep), T3 Batch/Pipelines (JIT Preflight).
- **PC-2 (Paring): REFRAME.** Retire dead UI (Reverie frontend); convert local scrapers to JIT preflights; retain API bridges.
- **PC-3 (DULL Fix): KEEP & EXTEND.** Real-time probe status drives dashboard. Decouple quarterly review cadences into asynchronous audit logs.
- **PC-4 (Owner Map): KEEP.** Federate keepers: Dembe (C2/Network), Dani/Talon (Client/Travel), Sterling (PII/Gates), Whetstone (Core CLI).
- **PC-5 (Intervals): REPLACE.** Eliminate timers for JIT and daemon services; run <25 total timers for live C2 and fare monitoring.

— V. Hale, VCS
