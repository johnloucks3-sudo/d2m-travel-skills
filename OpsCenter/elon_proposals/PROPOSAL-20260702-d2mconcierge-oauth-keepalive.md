ELON proposal complete. Writing to file: `/home/john/Thunderbird/OpsCenter/elon_proposals/PROPOSAL-20260702-d2mconcierge-oauth-keepalive.md`

**Summary:**

The service failure is **datetime mismatch inside google-auth during refresh()**. The partial fix on lines 74-75 protects the expiry comparison, but google-auth internally compares naive vs aware datetimes during the OAuth2 handshake, causing intermittent exit(1). The watchdog catches it and restarts.

**ELON recommendation:** Normalize all datetime fields in the credentials JSON to UTC-aware BEFORE passing to the Credentials constructor. This is a defensive fix Hale can apply autonomously.

**MT — 2026-07-02 07:40**
