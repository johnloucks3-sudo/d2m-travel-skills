Proposal updated. ELON analysis complete.

**Root cause confirmed:** Transient DNS failures crash the service. Log trace shows `error: Unable to find the server at gmail.googleapis.com` at 18:35:54, followed by watchdog restart at 18:36:14. Service exits with status 1 on any unhandled network exception, triggering the 4x/week restart pattern.

**Proposed fixes documented:**
- **Option 1 (deployed):** Wrapper script with 30s timeout + graceful exit — already in place, awaiting 48h monitoring window
- **Option 2 (recommended if Option 1 fails):** Code-level resilience with exponential backoff retry logic — requires Hale's greenlight to modify protected file

**Decision: QUEUE_FOR_COMMANDER** — Hale to review monitoring results and determine whether to escalate to code-level fix.

Proposal written to `/home/john/Thunderbird/OpsCenter/elon_proposals/PROPOSAL-20260614-thunderbird-commander-directive-sweep.md`.
