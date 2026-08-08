# RT-MISSION — AUTONOMOUS MISSION-BOARD OPERATION
**Seats:** AG → CC → OC · **Commander delegated the stack to HALE-OC (2026-08-07).** GO to design + implement low-tempo autonomy. OC assembles + executes; seats converge on the MODEL.
**Ground truth (verified 08-07):** Mission Board 240 total, 172 open (91 pending_review, 35 active, 35 in_progress), 19 P0 open. TCD = 361 items. Duplicate P0s exist (Regent cookie x4). Board file fights TCD sync (recover_lost_tcd_closures exists). Promoter auto-P2→P1 at 21d (adds noise). `OnFailure=thunderbird-generic-remediate@%N` already live wing-wide.

## PROPOSED MODEL (OC) — "claim-and-decay ledger," 3 pillars
1. **CLAIM-ONLY, no assignment:** nightly claim sweep; each agent pulls only its lane; unclaimed ≥14d auto-RETIRES (one-line why-dropped) to archive.
2. **STREAM IS THE SOURCE:** append-only event journal = truth; board + TCD become derived reads (kills sync divergence — recover_lost_tcd_closures obsolete).
3. **ON-EVENT spawning, zero-poll:** task born only on a real event (CI FAIL, FPD deadline, dossier edit, Commander directive). No timer-noise tasks. Reuse OnFailure + CI probes → task creation, not memory-write.

## YOUR SEAT ASK (≤300w, BLUF-first): challenge the trio. Where does claim-only drop real work? Is ledger-as-source overkill vs existing? Which pillar ships first, which is a trap? Give one better idea if you have it.
