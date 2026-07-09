# Pulse Phone C2 — Operator's Manual

**Claude-Pulse v0.1.0** · Installed 2026-07-09 · Auth token: registered (Commander)

---

## 1. What It Is

A phone notification bridge between Claude Code and your phone. When Claude
finishes its turn, you get a push notification with sound on your phone telling
you to come back to the keyboard. No more staring at a terminal waiting.

## 2. Daily Use

There is nothing to do. It runs silently.

When you finish typing and Claude starts working:

- **Walk away.** Go make coffee, take a walk, whatever.

When Claude finishes:

- Your phone buzzes: **"Claude finished (Thunderbird)"** with message
  **"Your turn in Thunderbird"**.
- A desktop popup fires on your Ubuntu machine too.
- Come back and type.

That's it. That's the whole loop.

## 3. Kill Switch

Pulse can be silenced or restored with one command.

| Command | Effect |
|---|---|
| `python3 scripts/pulse-kill.py status` | Show state, hook count, dashboard, auth |
| `python3 scripts/pulse-kill.py disable` | Remove both Pulse hooks. Backup saved. |
| `python3 scripts/pulse-kill.py enable` | Restore hooks from backup. Restart dash. |
| `python3 scripts/pulse-kill.py test` | Fire a test push to your phone right now |

**Examples:**

```
python3 scripts/pulse-kill.py status     # check state
python3 scripts/pulse-kill.py disable    # silence the bridge
python3 scripts/pulse-kill.py test       # verify phone receives it
python3 scripts/pulse-kill.py enable     # bring it back
```

`enable` only restores Pulse hooks — all other hooks (Wing keyword router,
session save, etc.) are never touched.

When you `disable`, a backup is saved to
`~/.claude/settings.json.pulse-backup`.

## 4. What Gets Sent Over the Wire

**Stop hook (phone buzz):**

```
Title:  Claude finished (Thunderbird)
Body:   Your turn in Thunderbird
Tags:   white_check_mark
Auth:   Bearer token (write-only, ntfy.sh)
```

No PII. Just the project name and "your turn".

**Notification hook (tool-use events):**

These are the detailed pings that fire during Claude's turn. A PII scrubber
runs before anything leaves the machine. All of these are replaced:

```
Client names like "Furlow" or "Kuklinski"  →  [CLIENT]
Absolute file paths like /home/john/...    →  [PATH]
Email addresses                            →  [EMAIL]
Booking IDs like 3071222-26                →  [BOOKING]
Phone numbers                              →  [PHONE]
```

The raw event data never reaches ntfy.sh. The dashboard at
http://127.0.0.1:4317 shows the full local view with no redaction.

## 5. Files

| File | Purpose |
|---|---|
| `~/.claude-pulse.json` | Config: ntfy topic, auth token, dashboard port |
| `~/.claude/settings.json` | Hook definitions (Stop, Notification) |
| `scripts/pulse-stop-authenticated.js` | Stop hook — authenticated ntfy push |
| `scripts/pulse-notify-scrubbed.js` | Notification hook — PII scrub + auth |
| `scripts/pulse-kill.py` | Kill switch — enable/disable/status/test |
| `/tmp/claude-pulse-src/` | Pinned source clone (commit 0337afe) |
| `~/.claude/.pulse/` | Pulse runtime data (stop debounce, logs) |

## 6. Recovery

**Dashboard died?** It restarts automatically on `enable`. For manual restart:

```
pkill -f claude-pulse 2>/dev/null; nohup claude-pulse >/dev/null 2>&1 &
```

**Hook file deleted?** The backup at `settings.json.pulse-backup` has the full
correct settings. Restore with `pulse-kill.py enable`.

**ntfy topic compromised?** Commander re-registers at https://ntfy.sh/app,
generates a new topic + access token. Hale updates `~/.claude-pulse.json`.

**Whole thing is annoying?** `python3 scripts/pulse-kill.py disable` — zero
Pulse hooks, zero phone noise. Wing hooks unaffected.

## 7. Quick Reference

```
┌─────────────────────────────────────────────────────┐
│  You type → Claude works → Phone buzzes → You type  │
│              ↑_________________________↓             │
│                 (authenticated ntfy.sh)              │
└─────────────────────────────────────────────────────┘

Stop hook (30s debounce) → Desktop + phone push
Notification hook (each tool call) → PII-scrubbed detail push
Kill switch → python3 scripts/pulse-kill.py <cmd>
```
