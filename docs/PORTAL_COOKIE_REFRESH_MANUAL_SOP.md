# Manual Portal Cookie Refresh — SOP
*For when automated keepalive fails or credentials are missing*

**Last Updated:** 2026-06-08  
**Use Case:** Centrav (B2B flights) and Regent (Seven Seas booking portal)

---

## CENTRAV — 5 minutes

### Credentials
- **Email:** johnloucks3@gmail.com
- **Password:** `Canal4me!` (from config/portal_creds.json agent_universe entry, or ask Commander)
- **URL:** https://www.centrav.com/login

### Steps
1. **Open Firefox** (or any regular browser, not headless)
2. **Navigate:** https://www.centrav.com/login
3. **Fill login:**
   - Email: johnloucks3@gmail.com
   - Password: [from credentials above]
4. **Handle reCAPTCHA** (if appears): Complete puzzle
5. **Enter 6-digit OTP** (sent to johnloucks3@gmail.com)
6. **Wait for dashboard** to load (https://www.centrav.com/dashboard)
7. **Export cookies:**
   - Press **F12** to open Developer Tools
   - Tab: **Application** → **Cookies** → **https://www.centrav.com**
   - **Right-click** → **Export as JSON** (or copy all rows)
8. **Save to file:** `/home/john/Thunderbird/creds/centrav_cookies.json`
9. **Verify:** Run `python3 scripts/portal_keepalive.py --status` to confirm Centrav shows WARN or OK

### Troubleshooting
- **reCAPTCHA won't load:** Try a different browser or incognito mode
- **OTP never arrives:** Check spam folder, or request new OTP from Centrav
- **401 after OTP:** Password may have changed — check Commander

---

## REGENT (Seven Seas) — 5 minutes

### TWO ACCOUNTS — Export Both

#### Account 1: Direct D2M Account (REQUIRED)
- **Email:** jl3lovegrouptravel@gmail.com
- **Password:** Falcons4me!
- **Bookings:** Ely 3096289, Furlow 3071222, Nichols 3078056, McLeod 2984034
- **Cookie file:** `creds/regent_cookies.json`

#### Account 2: Outside Agents / OA Account (REQUIRED)
- **Email:** johnloucks3@gmail.com
- **Password:** Canal4me!
- **Bookings:** Loucks 3122006, McLeod 3114500
- **Cookie file:** `creds/regent_cookies_oa.json`

### Steps (Repeat for Both Accounts)

**CRITICAL:** Use **Firefox only** — Chromium is blocked by Akamai Bot Manager CDN

1. **Open Firefox** (normal window, not headless)
2. **Navigate:** https://www.rssc.com/agent/dashboard/#myBookings
3. **Log in** with account credentials (see above)
4. **Wait for dashboard** to fully load (shows your bookings)
5. **Export cookies:**
   - Press **F12** to open Developer Tools
   - Tab: **Application** → **Cookies** → **https://www.rssc.com**
   - **Right-click** → **Export as JSON** (or select all + copy)
6. **Save to file:**
   - Account 1 (direct D2M) → `/home/john/Thunderbird/creds/regent_cookies.json`
   - Account 2 (OA) → `/home/john/Thunderbird/creds/regent_cookies_oa.json`
7. **Verify:** Run `python3 scripts/portal_keepalive.py --status` to confirm Regent shows WARN or OK

### Troubleshooting
- **Login page redirects to itself:** Browser cookies may be poisoned — clear Regent cookies and retry
- **"Agent account not found":** Check email/password spelling
- **Akamai page ("checking browser..."):** Chromium was used by mistake. Use Firefox instead.

---

## Verification

After exporting both portals:

```bash
python3 scripts/portal_keepalive.py --status
```

Expected output:
```
centrav              OK             2026-06-XX HH:MM UTC
room_res             OK             2026-06-XX HH:MM UTC
```

If both show OK or WARN (not EXPIRED or SESSION_ONLY) → refresh successful

---

## When to Use This SOP

- ❌ Do NOT use this regularly — portal_keepalive.py should auto-refresh
- ✅ Use this when:
  - Keepalive fails 3+ times (see AM brief or portal_keepalive.log)
  - Cookies are about to expire (<48h) and keepalive didn't work
  - New credentials are set and need immediate activation
  - Troubleshooting keepalive behavior (to rule out credential issues)

---

## Related Files
- Config: `/home/john/Thunderbird/config/portal_creds.json`
- Keepalive script: `/home/john/Thunderbird/scripts/portal_keepalive.py`
- Logs: `/home/john/Thunderbird/logs/portal_keepalive.log`
- Cookies location: `/home/john/Thunderbird/creds/`
