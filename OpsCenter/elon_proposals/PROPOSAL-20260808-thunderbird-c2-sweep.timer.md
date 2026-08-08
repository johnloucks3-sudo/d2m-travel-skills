Proposal written to `/home/john/Thunderbird/OpsCenter/elon_proposals/PROPOSAL-20260808-thunderbird-c2-sweep.timer.md`.

**Summary:**  
**Root cause:** Orphaned systemd unit referencing a deleted script (`c2_action_sweep.py`). Timer fires every 3 minutes, service fails, auto-repair can't fix missing script.

**Fix:** Disable and remove the retired unit (documented as RETIRED-ACTIVE-RESERVE in STACK_FRESHNESS.md).

**Decision:** APPLY_AUTONOMOUSLY — low-risk removal of documented dead code, reversible via git, no active mission attached.

Thanks
