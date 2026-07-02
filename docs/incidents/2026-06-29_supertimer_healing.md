# INCIDENT: Supertimer Bot Silent Failures — 2026-06-29

**Severity:** Critical — 7 of 12 bots had thousands of consecutive failures, undetected for days.

## Root Causes & Fixes

### 1. Playwright Browsers Missing
- **Symptom:** `infra_bot`, `client_bot` crashed: `BrowserType.launch: Executable doesn't exist at .../firefox/firefox`
- **Fix:** `.venv/bin/playwright install firefox chromium`
- **Why it happened:** System reinstall or venv rebuild didn't include browser binaries

### 2. TESS OAuth Token Expired
- **Symptom:** `infra_bot`: `invalid_client` on TESS portal login
- **Fix:** Regenerated TESS OAuth 2.0 + PKCE tokens via `tess_authorize` MCP tool
- **Why it happened:** Tokens expired silently; no alerting on OAuth failure

### 3. `no_proxy` Contains `fd00::/8` or `*.local` — httpx CRASHES
- **Symptom:** `httpx.InvalidURL: Invalid port: ':'` on `httpx.Client()` init. Affects Gemini API, Qdrant, and all proxy-routed HTTP. The error occurs at **Client construction time**, not request time.
- **Root cause:** httpx's `no_proxy` parser does NOT support:
  - IPv6 CIDR notation (`fd00::/8`)
  - Wildcard domains (`*.local`)
  These cause URL parsing to fail.
- **Fixed in all locations:**
  - `~/.bashrc` lines 316-317
  - `~/.profile` lines 33-34
  - `~/.bash_profile` lines 20-21
  - `/home/john/Thunderbird/.env` (added no_proxy)
  - `systemctl --user set-environment no_proxy=...` (systemd cache)
- **Current `no_proxy` value:**
  ```
  localhost,127.0.0.1,::1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,169.254.0.0/16
  ```

### 4. backup_bot drive-sync Timeout
- **Symptom:** `backup_bot` consistently timed out on `drive-sync` task
- **Fix:** Extended timeout from 300s → 600s; added `**/centrav_ff_profile/**` to rclone exclude filter
- **Why it happened:** `centrav_ff_profile` (Firefox cache from Centrav scraper) has thousands of tiny files that take 5+ minutes to sync

## Key Architectural Lesson

The `build_env()` function in `supertimer/leader.py` uses `env.setdefault()`:
```python
env.setdefault(k.strip(), v.strip())  # .env values do NOT override inherited env
```
This means `.env` file changes only apply to vars NOT already in the environment. To override systemd-inherited vars, you must use `systemctl --user set-environment` or add `Environment=` to the service unit.

## Verification

```bash
$ python3 scripts/ci_probe_supertimer_health.py
RAZOR_SHARP supertimer-health: 12 bots, 0 in failure storm

$ python3 api/thunderbird_preflight.py | grep Overall
Overall: GREEN
```
