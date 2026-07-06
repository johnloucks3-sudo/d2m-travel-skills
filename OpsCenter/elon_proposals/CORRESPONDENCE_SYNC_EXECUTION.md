# EXECUTION — PROPOSAL-20260612-d2m-correspondence-sync

**Status: DEPLOYED — APPLY_AUTONOMOUSLY complete**
**Executed:** 2026-07-06 16:12 MT

## Pre-existing state
`d2m-correspondence-sync.timer` was already enabled/active (daily 06:00 MT) and the
`.service` unit already had `OnFailure=thunderbird-alert@%n.service` wired to the
existing Telegram alert path. What was **missing** was the actual resilience fix
the proposal called for — the code was still crash-prone and the unit had no
restart policy.

## Fix applied (3 parts, per proposal)

1. **Code** — `scripts/dossier_correspondence_sync.py`
   - `load_gmail_service()`: OAuth refresh now bounded by a 5-second `SIGALRM`
     timeout (`OAUTH_REFRESH_TIMEOUT_SEC`), raising `OAuthRefreshTimeout` instead
     of hanging indefinitely.
   - Per-account loop in `run_sync()`: `load_gmail_service()` and
     `fetch_sent_messages()` calls wrapped in try/except — a failing account
     (expired/hung refresh, API error) is logged and skipped; the other account
     still gets scanned and written.

2. **Config** — `/home/john/.config/systemd/user/d2m-correspondence-sync.service`
   - Added `Restart=on-failure`, `RestartSec=60`
   - Added `StartLimitIntervalSec=180`, `StartLimitBurst=3` (max 3 restarts per
     3-minute window — stops the exponential-hammer pattern that made the
     original incident worse)
   - `OnFailure=thunderbird-alert@%n.service` retained (already present)

3. **SO** — not authored as a separate standing order; the resilience contract
   is documented inline as a docstring on `load_gmail_service()` referencing
   INC-20260612T135256Z-886802, per Sterling's existing hard-rule on
   comments explaining non-obvious WHY. No new `@`-loaded doctrine file needed
   for a pure infrastructure fix.

## Verification (independent of self-report)
```
systemctl --user daemon-reload
systemctl --user enable --now d2m-correspondence-sync.timer   # already enabled; confirmed
systemctl --user start d2m-correspondence-sync.service
journalctl --user -u d2m-correspondence-sync.service -n 15
```
Result: `code=exited, status=0/SUCCESS`. Live run scanned both `d2mconcierge`
and `johnloucks3` (61 sent messages each, real Gmail API calls — not mocked),
0 new client emails matched (none new since last run), sync completed cleanly.
Python syntax verified via `ast.parse` before execution.

## Residual note
Multiple manual/other-triggered runs of this service appear in today's log
(06:00, 07:36, 10:50, 13:55, 16:12 MT) beyond the single 06:00 daily timer —
worth a look at whether another cron/agent is also invoking this script
directly. Not in scope for this proposal; flagging for Sterling's CI sweep.
