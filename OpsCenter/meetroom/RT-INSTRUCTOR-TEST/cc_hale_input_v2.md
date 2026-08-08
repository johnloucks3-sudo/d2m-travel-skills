BLUF: Round 2 of the same real task. Round 1 taught us something real: writes to
paths outside this repo (like `~/.config/systemd/user/`) get silently blocked
without explicit permission, so this round asks for STAGED file content inside
the repo instead — no permission issue, and CC applies it to the real path.

## What actually happened last round (for your context, not a correction of you)
`opencode run` without `--auto` auto-rejects writes to paths outside
`/home/john/Thunderbird`. `~/.config/systemd/user/*.service` is outside this
repo. That's a permission boundary on the tool, not something you did wrong.

## Silver front frame (checkable done + named ground truth)
- **Done means:** 3 new files exist under
  `OpsCenter/meetroom/RT-INSTRUCTOR-TEST/staged/`, one per service, each
  containing the FULL corrected content of that service file (original content
  + one added `OnFailure=thunderbird-alert@%n.service` line in `[Unit]`).
- **Ground truth:** each staged file's `[Unit]` section contains exactly one
  `OnFailure=thunderbird-alert@%n.service` line; nothing else differs from the
  original file's content.

## Steps
1. `cat ~/.config/systemd/user/thunderbird-mcp.service` — read the real current content.
2. Write the SAME content to `OpsCenter/meetroom/RT-INSTRUCTOR-TEST/staged/thunderbird-mcp.service`, with `OnFailure=thunderbird-alert@%n.service` added as a new line inside `[Unit]`. Nothing else changed.
3. Repeat step 1-2 for `ttyd-terminal.service` and `cloudflared.service`.
4. Do not touch the real files in `~/.config/systemd/user/` — only write to the `staged/` directory inside this repo.
5. Do not run any `systemctl` command.

## First action
As your first tool call: `cat ~/.config/systemd/user/thunderbird-mcp.service`

## What do you need to succeed?
If anything here is unclear or the staged/ directory doesn't exist yet, say so
in your summary — otherwise just do the 3 staged writes, all inside this repo,
where you already have write access.
