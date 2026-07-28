Proposal complete. **File:** `/home/john/Thunderbird/OpsCenter/elon_proposals/PROPOSAL-20260724-d2m-icelandair-warm.md`

**TL;DR:**
- **Root Cause:** Icelandair session expires after ~41 hours server-side. The warm-ping (every 15min) refreshes the Cloudflare cookie but can't prevent account-level logout. Session dies → escalation fires → watchdog restarts → same session still dead → restart loop.
- **Fix:** Disable OnFailure auto-restart for this service only. Accept manual re-login every 35 days (standing order). **Can execute autonomously.**
- **Alternative Paths:** Commander decides if we want (B) automated re-login via Playwright (risky) or (C) Icelandair API migration (requires research).
- **Decision:** QUEUE_FOR_COMMANDER — technical path is clear, but this is a policy choice (manual vs automated vs API).

Proposal is ready for review. Thanks
