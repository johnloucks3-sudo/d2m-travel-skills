# D2MConcierge OAuth Keepalive — Verification Report (No Code Change)
*2026-07-06 — Claude Code (Hale/TALON lane)*

## Task as received
Team-lead dispatched a fix for an alleged "datetime mismatch in google-auth" causing
intermittent `exit(1)` in the d2mconcierge OAuth keepalive, targeting
`OpsCenter/d2mconcierge_oauth_keepalive.py` with instructions to normalize all
datetime fields to UTC-aware before constructing `Credentials`.

## Finding: the named file does not exist; the premise does not match current evidence

**1. Wrong file path.** `OpsCenter/d2mconcierge_oauth_keepalive.py` does not exist.
The actual script (bound via `systemctl --user cat d2mconcierge-oauth-keepalive.service`)
is `scripts/d2mconcierge_mcp_oauth_refresh.py`.

**2. The datetime bug is already fixed — 26 days ago, zero recurrence.**
Git history on that file:
- `6f0d2c6` (2026-06-10 17:16 MDT) introduced the naive/aware subtraction without
  a tzinfo guard.
- `25ff27d` (2026-06-10 22:11 MDT) added the exact guard the task asked for:
  ```python
  if expiry_dt.tzinfo is None:
      expiry_dt = expiry_dt.replace(tzinfo=timezone.utc)
  ```

Log evidence (`logs/d2mconcierge_oauth_keepalive.log`, 5,890 lines, 2026-06-10 → today):
- `can't subtract offset-naive and offset-aware datetimes` appears **10 times, all
  between 14:43–20:48 MDT on 2026-06-10** — i.e., all *before* the 22:11 fix commit.
- **Zero occurrences of that error in the 26 days since.**
- All post-fix `❌` entries (109 total) are transient network failures: DNS
  resolution (`oauth2.googleapis.com`), `ConnectionResetError`, SSL EOF, proxy
  refused, read timeout. None are datetime-related. These self-heal on the next
  45-minute timer tick and require no code change — the timer already retries.

**3. Why the "normalize before constructing Credentials" instruction doesn't apply.**
`Credentials(...)` at line 58 is built with `token, refresh_token, token_uri,
client_id, client_secret, scopes` only — **no `expiry` is ever passed to the
constructor**. `creds.expiry` starts `None` and is set entirely by
`creds.refresh(Request())`'s internal (self-consistent, always-naive) datetime
math. There is no naive-vs-aware comparison inside `google-auth` for this call
path — the only comparison in this codebase is the one this script does itself
at line 77 (`expiry_dt - now_utc`), which the 2026-06-10 fix already guards.

**4. Current live state (verified, not self-reported):**
- `config/persona_gmail_token.json` expiry: `2026-07-06T22:52:21.729734` (naive,
  as expected — google-auth writes it naive, script re-adds UTC tzinfo on read).
- `systemctl --user status d2mconcierge-oauth-keepalive.service`: last run
  2026-07-06 15:52:22, `Main PID ... (code=exited, status=0/SUCCESS)`.
- `systemctl --user list-timers`: next run 16:37 MDT, on the normal 45-min cadence.
- installed `google-auth==2.49.0`.

## Action taken
None to the OAuth script — there is nothing to fix. Making a speculative code
change against a bug that isn't reproducing would be undocumented drift against
a working control (Sterling gate: "how will we know it worked?" — it already is).

## Recommendation
Close this task as **already resolved by commit 25ff27d9d (2026-06-10)**. If the
team-lead has a *different*, more recent failure signature (paste the actual
traceback/log line), re-open with that evidence — the current log shows none.
