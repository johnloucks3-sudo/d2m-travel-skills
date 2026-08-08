Proposal written. The recurring remediation loop is caused by `zen-usage-guard` — a monitoring tool, not a systemd service — remaining in the auto-remediation tracking state despite never existing as a real service. Each auto-heal attempt fails immediately because systemctl can't find the unit, triggering the next cycle.

**Fix:** Remove the stale `zen-usage-guard` entry from the remediation state file and exclude it from tracking. This is a pure state cleanup that Hale can execute autonomously in under 5 minutes.

Detailed proposal with verification test written to `/home/john/Thunderbird/OpsCenter/elon_proposals/PROPOSAL-20260805-thunderbird-generic-remediate@zen-usage-guard.md`.
