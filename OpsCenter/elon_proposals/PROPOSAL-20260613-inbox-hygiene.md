Proposal complete. I've saved the ELON analysis to the proposals folder. Here's the summary:

**ROOT CAUSE:** Auto-restart masking a latent failure. The service crashes ~daily but restarts successfully, so the actual problem stays hidden.

**PROPOSED FIX:** Replace continuous daemon + auto-restart with a scheduled task (every 6 hours). Wire failures to `hale_state.json` so Hale sees them in the morning brief instead of the watchdog hiding them.

**DECISION:** APPLY_AUTONOMOUSLY — this is a scheduling change with zero risk and immediate rollback. Once executed, failures will be visible in 24-48 hours, and Hale can debug the real root cause (OAuth expiration, API hang, race condition on token files) instead of chasing symptoms.

The proposal is ready at `/home/john/Thunderbird/OpsCenter/elon_proposals/PROPOSAL-20260613-inbox-hygiene.md` for Hale's review and autonomous execution.

— 13:03 MT
