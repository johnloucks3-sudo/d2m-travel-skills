**Root cause:** `cache-cleanup.timer` nukes `~/.cache/ms-playwright` nightly with no reinstall step — confirmed the dir is empty right now. `tess-token-keepalive`'s Playwright fallback login then fails until an unrelated process happens to reinstall Chromium, which is why it looks like "auto-heal" 5x/7d. Distinct from the 3 prior fixes already shipped for this unit (log dup-write, stale creds, unhandled timeout) — none touched the cache wipe.

Proposal written: `OpsCenter/elon_proposals/PROPOSAL-20260805-thunderbird-generic-remediate@tess-token-keepalive.md`. Decision: **APPLY_AUTONOMOUSLY** (config_change, zero client/financial gate). Fix: append `playwright install chromium` to `cache-cleanup.service` right after the `rm -rf`, plus an immediate one-time reinstall since the cache is empty now.

Not yet applied — flagging before executing since it edits a live systemd unit outside the repo (`~/.config/systemd/user/cache-cleanup.service`). Want me to apply it now?
