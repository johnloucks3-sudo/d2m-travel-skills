BLUF: First live Instructor Mode test — a small, real, checkable piece of Item #16 (self-repair coverage), not the full pilot yet. Wire `OnFailure=` alerting onto 3 named services that currently have none. You're the builder here; I'm asking what you need before you start, not just checking your work after.

## Silver front frame (checkable done + named ground truth)
- **Done means:** each of the 3 named `.service` files below has an `OnFailure=thunderbird-alert@%n.service` line added to its `[Unit]` section, matching the existing pattern exactly (see below). Nothing else in those files changes.
- **Ground truth:** `grep -c "OnFailure=" ~/.config/systemd/user/<file>.service` prints `1` for each of the 3 files, `0` currently.

## Include (exact scope)
Edit exactly these 3 files, nothing else:
- `~/.config/systemd/user/thunderbird-mcp.service`
- `~/.config/systemd/user/ttyd-terminal.service`
- `~/.config/systemd/user/cloudflared.service`

## Exclude
- Do not touch any other `.service` or `.timer` file.
- Do not run `systemctl daemon-reload`, `systemctl restart`, or `systemctl enable/disable` on anything — file edits only, I'll reload and verify separately.
- Do not modify `ExecStart=`, `Environment=`, or anything outside the `[Unit]` section.

## The exact pattern to copy (already live on 11 other services — do not invent a variant)
```ini
[Unit]
Description=...   (existing line, unchanged)
...               (existing lines, unchanged)
OnFailure=thunderbird-alert@%n.service
```
Real example already in production, `d2m-fpd-alert.service`:
```ini
[Unit]
Description=D2M FPD Alert — Final Payment Deadline Monitor
Wants=network.target
StartLimitBurst=3
StartLimitIntervalSec=300
OnFailure=thunderbird-alert@%n.service
```
Add `OnFailure=thunderbird-alert@%n.service` as a new line inside `[Unit]`. If a file
doesn't already have `StartLimitBurst=`/`StartLimitIntervalSec=`, you may add
`StartLimitBurst=3` and `StartLimitIntervalSec=300` alongside it (matches the
production pattern, prevents alert spam on a crash loop) — but the OnFailure=
line itself is the only strictly required change.

## First action
As your first tool call: `cat ~/.config/systemd/user/thunderbird-mcp.service` — read the
real file before editing anything.

## Question for you — what do you need to succeed?
Before you start editing: is anything here ambiguous, missing, or would make this
harder than it should be? You've cracked supplier portals harder than this — if
the scope, the pattern, or something about these 3 files needs more from me before
you can do this cleanly, say so. If nothing's in the way, say READY and go.

Write your answer to `oc_hale_input.md` in this same directory before editing any
files, even if your answer is just "READY, no questions."
