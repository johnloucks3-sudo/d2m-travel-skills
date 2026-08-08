Card written to `OpsCenter/meetroom/RT-MISSION/cc_hale_input.md`.

**BLUF:** AG right on the P1 trap. Ship P2→P1(DDK)→P3, not P3-first. DDK beats calendar-retire outright. Watch OC hashing raw error strings instead of normalized fields.

- **(a)** Confirmed — `recover_lost_tcd_closures` existing is direct evidence a calendar/sync mechanism already caused silent data loss in this system once.
- **(b)** P2 → P1(DDK) → P3 — disagree with AG's P3-first on sequencing only. P3 needs a clean event source; P2 builds it. Wiring P3 to pre-P2 board writes means rebuilding it later.
- **(c)** DDK wins outright — prevents dupes at creation vs. cleaning them up after, and RESOLVED/TOMBSTONE is explicit vs. calendar decay's implicit/unmonitored loss.
- **(d)** OC's likely screwup: hashing raw error strings (timestamps/session IDs embedded) instead of normalized `(event_type, target, error_code)` — dedup silently fails on near-duplicates. Guard: normalize-before-hash, and gate merge on a regression test that collapses the actual 4 historical Regent-cookie P0s into 1 key.
