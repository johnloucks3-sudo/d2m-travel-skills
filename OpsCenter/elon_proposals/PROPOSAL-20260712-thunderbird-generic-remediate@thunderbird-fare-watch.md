Done. ELON proposal written to `/home/john/Thunderbird/OpsCenter/elon_proposals/PROPOSAL-20260712-thunderbird-generic-remediate@thunderbird-fare-watch.md`

**Summary:**

The fare-watch service is failing 3x/7d because it lacks pre-flight health checks for its Chrome CDP dependency. Each restart succeeds by coincidence, masking a systematic issue: stale browser sessions or transient Chrome unavailability. 

**Proposed fix:** Add pre-flight Chrome health probe + session freshness validation + diagnostic exit codes. This turns the symptom (flaky restarts) into a signal (health code → action).

**Status:** Queued for Commander approval of the standing order. Code changes can execute autonomously under "fix don't ask" for infra, but the operational policy (when to skip vs. alert) needs Commander sign-off.

*2026-07-12 21:25 MT*
