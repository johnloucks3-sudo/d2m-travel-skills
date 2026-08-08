**Proposal complete.** The recurring remediation storm is caused by a missing script file: `claude-process-watch.service` tries to run `/home/john/Thunderbird/scripts/claude_process_watch.py` every 20 minutes, the file doesn't exist (no git history), and restarting a service with a missing dependency is futile. The proposal recommends retiring the timer and masking the service to stop the 20-minute failure cycle and remediation noise loop. This is a structural issue (unrecoverable by restart) and safe to retire since the script was never implemented.

Proposal written to `/home/john/Thunderbird/OpsCenter/elon_proposals/PROPOSAL-20260805-thunderbird-generic-remediate@claude-process-watch.md`.

Thanks.
