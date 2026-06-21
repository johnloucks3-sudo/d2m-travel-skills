**✅ Proposal written to:** `/home/john/Thunderbird/OpsCenter/elon_proposals/PROPOSAL-20260612-d2m-correspondence-sync.md`

---

## ELON Analysis Summary

**Incident:** INC-20260612T135256Z-886802 — `d2m-correspondence-sync` crashed 8 times in 7 days, 3x at 06:00 MT today alone. Auto-heal failed.

**Root cause:** The service has **zero resilience to OAuth token refresh timeout**. When `creds.refresh()` hangs (happens during Gmail API backoff / rate-limiting), the entire Python process exits with code 1. The script crashes instead of skipping that account and continuing. The 06:00 MT run hit this; 08:00 MT manual run succeeded because the OAuth cache had time to recover.

**Why this recurs:** 
- No timeout on the refresh call (unbounded hang risk)
- No try/except around token operations
- No skip-account fallback logic
- Systemd's exponential retry makes it worse (hammers the API faster)

**The fix:** Three-part.
1. **Code:** Add 5-second timeout + try/except + account skip logic to `load_gmail_service()`
2. **Config:** Systemd `Restart=on-failure` with sane limits (3 restarts, 60-sec intervals) + OnFailure alert
3. **SO:** Permanent standing order — "OAuth Refresh Resilience" — documents the skip behavior and alert protocol

**Decision:** `APPLY_AUTONOMOUSLY` — This is pure infrastructure robustness (no domain expert lane crossing). No business logic changes. Ready for Hale to execute and test same day.

**Result if fixed:** Service stays alive even if one Gmail account is temporarily offline. Partial work happens (at least one account gets scanned). Hale gets paged on the 3rd failure so she can fix the root auth issue. No more silent cascading restarts.

— 14:05 MT
