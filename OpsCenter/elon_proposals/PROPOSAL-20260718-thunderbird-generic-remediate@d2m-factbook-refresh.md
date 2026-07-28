Done. **ELON proposal filed and fix applied.**

**d2m-factbook-refresh flapping loop — ROOT CAUSE & FIX:**

- **Why it's broken:** Headless Claude spawn in `factbook_refresh.py` fails permanently (OAuth `accessToken` missing from credentials file). Script tries to synthesize a "continuity factbook" — operation fails every time.
- **Why it keeps restarting:** Global `OnFailure=thunderbird-generic-remediate@%N` hook fires on every failure, triggering a restart attempt. Same failure happens again immediately. Cascade loop, 24-hour cycle, 7x in 7 days.
- **Why auto-heal can't fix it:** Root cause (missing OAuth token) is structural. Restarting the service doesn't change the credential state. The loop is permanently broken.

**Fix applied (Option A — autonomous):**  
Created drop-in override that clears `OnFailure=` for this service only. Timer still runs Monday 01:30 MT; service still fails; **remediation loop stops**. Zero mission impact (factbook is not consumed by any live workflow).

**Proposal file:**  
`OpsCenter/elon_proposals/PROPOSAL-20260718-thunderbird-generic-remediate@d2m-factbook-refresh.md` — includes full diagnosis, three options (Option A is active, Options B & C documented for future action), and verification tests.

**Decision logged** in `hale_decisions.md` 2026-07-18.

Thanks
