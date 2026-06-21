**Proposal written.** Let me brief Hale on the finding:

---

## ELON BRIEF — TESS Keepalive Auto-Heal Pattern (3× in 7d)

**Root Cause:** Duplicate timers (`tess-keepalive.timer` + `tess-token-keepalive.timer`) firing simultaneously every 90 minutes. Log shows duplicate entries at identical timestamps. When OAuth token refresh fails (persistent `invalid_client` 400 error), the script falls back to Playwright. Playwright login sometimes fails on transient errors (DNS timeout on 2026-06-13 15:55:13). Service exits code 1 → watchdog detects failure and restarts. The dual-layer "redundancy" is actually creating the problem.

**Fix (Ready for Autonomous Execution):**

| Phase | Action | Owner | Time | Reversible |
|-------|--------|-------|------|-----------|
| 1 | Disable duplicate timer (`tess-token-keepalive`) | Hale | 5m | ✅ Yes |
| 2 | Add retry logic for transient errors in `thunderbird_tess.py` | Hale | 15m | ✅ Yes |
| 3 | Verify (check logs after 90-min cycle) | Hale | 90m | — |
| C | Investigate `invalid_client` errors (long-term) | Harlan/Dembe | TBD | — |

**Recommendation:** Execute Phases 1–2 now. If watchdog continues firing after both changes, it's the OAuth credentials issue (Phase C) — escalate to Harlan.

**Proposal file:** `/home/john/Thunderbird/OpsCenter/elon_proposals/PROPOSAL-20260613-tess-keepalive.md`

---

The proposal is structured and ready. **Hale: this is autonomous if you approve the approach.** Command if you want to review first, or I can kick off Phase 1 immediately (disable the duplicate timer).
