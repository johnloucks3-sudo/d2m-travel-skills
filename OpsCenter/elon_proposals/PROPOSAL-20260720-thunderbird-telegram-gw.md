**Proposal written to `/home/john/Thunderbird/OpsCenter/elon_proposals/PROPOSAL-20260720-thunderbird-telegram-gw.md`.**

---

## Summary

**ROOT CAUSE:** OOM-kill recurrence — not a network or Telegram API failure. The service is configured with a 512 MB memory ceiling (`MemoryMax`) that's incompatible with spawning Claude Code subprocesses. After loading personas and starting context polling, the service hits the limit within 5–45 seconds, gets killed by kernel OOM, restarts after 10 seconds, and repeats. The system is under 77% memory pressure (10.3Gi / 13Gi), leaving no buffer.

**FIX:** Increase `MemoryMax` from 512 MB to 2 GB via systemd override. Reflects realistic demand for a P0 C2 service under Python + subprocess load. Config-only, no code changes.

**VERIFICATION:** 
1. Run 15 minutes without OOM-kill entries in journalctl.
2. RSS memory stable <1.5 GB under idle polling.
3. Send `/status` to D2MC2C bot — response received within 10 seconds, no restart.

**RECOMMENDATION:** Apply autonomously. No permission gates — this is infrastructure tuning within Hale's standing authority (SO-2026-05-04). If the fix fails, the diagnosis points directly to a memory leak in service code (escalate with profiling evidence).

Thanks.
