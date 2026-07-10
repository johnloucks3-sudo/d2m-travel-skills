# TESS Credential Rotation — Ready for Commander Input

**Live status (2026-07-06 16:05 MT):** `tess_token.json` has a valid `access_token`
(43 min remaining at last check) but an **empty `userID`** — the 90-min OAuth
refresh cycle renews the access/refresh token pair but does not carry `UserID`.
Result: `--test` fails with `"No userID in token; re-extract from localStorage"`.
This is a genuine credential gap, not a false alarm — confirmed live, not from
a stale proposal file.

**Fix requires ~90 seconds of Commander action** (no OAuth admin portal, no
client ID/secret — this account authenticates via browser session, not the
PKCE flow `tess_authorize.sh` assumes for a different/legacy endpoint).

---

## Step 1 — Commander: capture the token blob

1. Open a browser and log in at **https://crm.myagentgenie.com**
2. Open DevTools (**F12**)
3. Go to **Application** tab → **Local Storage** → `https://crm.myagentgenie.com`
4. Find the key named **`authenticationData`**
5. Copy its full value (a JSON blob containing `token`, `refreshToken`, etc.)

## Step 2 — Run the rotation script

```bash
bash /home/john/Thunderbird/scripts/rotate_tess_credentials.sh '<paste the authenticationData JSON here>'
```

Wrap the pasted value in single quotes exactly as shown. The script will:
1. Inject the token into `tess_token.json` via `thunderbird_tess.py --inject-token`
2. Confirm `userID` is populated (fails loud if not)
3. Run `--test` to verify the live connection
4. Restart `tess-token-keepalive.timer` so the 90-min auto-refresh picks up
   the new session

## Step 3 — Done

No further action. Auto-refresh resumes on the existing 90-min cadence. If
`--test` still fails after injection, the blob was stale (re-copy from a
freshly loaded page, not a cached tab) or the account session itself needs a
re-login.

---

### Notes for the record
- Real credential file is `/home/john/Thunderbird/tess_token.json` — there is
  no `config/tess_credentials.json` in this system; that path does not exist
  and nothing reads it.
- `scripts/tess_authorize.sh` (OAuth2 PKCE against `auth.outsideagents.com`)
  is a separate/legacy flow for a different backend host and does not apply
  to the current `crm.myagentgenie.com` session-based auth — do not use it
  for this rotation.
- `rotate_tess_credentials.sh` wraps the existing, already-built
  `--inject-token` handler in `core/booking/thunderbird_tess.py` rather than
  reimplementing token parsing.
