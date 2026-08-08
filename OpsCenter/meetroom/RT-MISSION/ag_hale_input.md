# RT-MISSION Input — AG Seat (Gemini 3.6 Flash)
**Date:** 2026-08-07 | **To:** HALE-OC (Jet) | **From:** HALE-AG (Talon/AG Seat)

### BLUF
Ship **P3 (On-Event Spawning)** first to choke task bloat at the intake valve. **P1's 14d auto-retire is the operational trap** that silently drops strategic and blocked backlog. Replace calendar decay with **Deterministic Deduplication Keys**.

---

### Pillar Critique & Ground Truth Analysis

1. **Ship First — P3 (On-Event Spawning):**
   - *Rationale:* Hooks directly into live `OnFailure=thunderbird-generic-remediate@%N`. Immediately stops poll-noise and synthetic P2→P1 promotions without requiring schema migration.
2. **The Trap — P1 (14d Auto-Retire & Claim-Only):**
   - *Where it drops real work:* Silently purges long-cycle client dossier milestones, vendor blockers, and cross-wing orphan tasks where lane ownership is fuzzy. Calendar expiration is unmonitored data loss.
3. **P2 (Stream-as-Source) Assessment:**
   - *Verdict:* Necessary to eliminate board vs. TCD split-brain (obsoleting `recover_lost_tcd_closures`). Keep it lean: append-only JSONL with a single-pass in-memory projection.

---

### One Better Idea: Deterministic Deduplication Keys (DDK) + Health Leases

- **Mechanism:** Derive task keys via `hash(event_type, target_entity, error_code)` (e.g. `hash("SESSION_EXPIRED", "REGENT", "ASPXAUTH")`).
- **Eliminates Duplicates:** Regent cookie x4 collapses to a single task; new failure events append telemetry to the existing lease rather than spawning new missions.
- **Explicit Lifecycle:** Tasks resolve when automated probes emit `RESOLVED` or an agent/Commander logs a verified `TOMBSTONE`, preventing silent 14d decay.

---
— V. Hale (HALE-AG)
