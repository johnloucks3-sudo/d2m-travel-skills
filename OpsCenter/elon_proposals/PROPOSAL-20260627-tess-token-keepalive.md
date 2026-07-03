**PROPOSAL COMPLETE:**  
`/home/john/Thunderbird/OpsCenter/elon_proposals/PROPOSAL-20260627-tess-token-keepalive.md`

## Summary

**Root Cause:** TESS OAuth credentials are invalid (400 invalid_client error). The keepalive service crashes every 90 minutes when it attempts token refresh, and the watchdog restarts it on schedule, creating a predictable loop. Token expired 30+ hours ago.

**Fix:** escalate_to_commander — credentials are strategic, not a code issue. Commander must rotate TESS credentials via admin portal or B2B API.

**Hale Decision:** QUEUE_FOR_COMMANDER  
Turnaround: 5 min to surface + 2 min to implement (once Commander supplies fresh credentials).

**Interim Mitigation:** If Commander is unavailable, mask the timer to stop restart noise — but only with explicit approval.

---

This proposal is ready for **Hale to route to Commander** with priority P0 and a short turnaround window. Once Commander supplies new TESS credentials, implementation is 2 minutes (update config + restart + verify).
