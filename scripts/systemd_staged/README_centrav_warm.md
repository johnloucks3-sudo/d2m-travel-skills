# Centrav Warm-Keepalive — STAGED (review before enabling)

MISSION-200. These two unit files keep the Centrav B2B agent session alive without
repeated manual logins. They are STAGED here — **not enabled**. Enabling is the review gate.

## Pieces
- `scripts/centrav_session_warm.py` — warm-ping. Opens the persistent Firefox profile
  (`core/travel/data/centrav_ff_profile`) headless, GETs an authenticated Centrav page,
  and **only if still authenticated** re-saves cookies to `core/travel/data/centrav_session.json`.
  Non-destructive: dead session / profile lock / any error → SKIP, session.json untouched.
- `d2m-centrav-warm.service` — oneshot runner. `SuccessExitStatus=0 2 3` (2/3 are safe-skip, not failures).
- `d2m-centrav-warm.timer` — `OnBootSec=5min` + `OnUnitActiveSec=75min` (margin under the ~90 min idle TTL).

## One-time human bootstrap (already supported)
Run `scripts/centrav_serve.py` once → solve reCAPTCHA + email-OTP, keep "Remember this Browser"
checked. That writes the trust cookie into the persistent profile. After that the warm-ping
holds the session for days with no human in the loop.

## Install (DO AFTER REVIEW — not done by the build)
```
cp scripts/systemd_staged/d2m-centrav-warm.service ~/.config/systemd/user/
cp scripts/systemd_staged/d2m-centrav-warm.timer   ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now d2m-centrav-warm.timer
systemctl --user list-timers | grep centrav-warm
```

## Manual test anytime
```
.venv/bin/python scripts/centrav_session_warm.py --check   # report only, never writes
.venv/bin/python scripts/centrav_session_warm.py           # warm + refresh if authenticated
```
Exit: 0 warmed · 2 dead (needs manual login) · 3 skipped (locked/busy).
