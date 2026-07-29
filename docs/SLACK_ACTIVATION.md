# Slack activation — do this when you're back at YOGA

Everything is built and installed. This is the whole remaining job.
Workspace: `newworkspace-wya3670.slack.com`

---

## 1. Create the app (~60 seconds)

1. **https://api.slack.com/apps** → **Create New App** → **From an app manifest**
2. Pick workspace **newworkspace-wya3670**
3. Choose **YAML**, paste the contents of `config/slack_app_manifest.yaml`, → **Create**
4. Left sidebar → **Install App** → **Install to Workspace** → **Allow**

The manifest already sets Socket Mode and interactivity on, and requests only seven
scopes. There is no request URL to configure — Socket Mode makes an outbound
connection, so nothing on this machine is ever exposed to the internet.

## 2. Grab both tokens

| Token | Where | Prefix |
|---|---|---|
| Bot token | **OAuth & Permissions** → Bot User OAuth Token | `xoxb-` |
| App token | **Basic Information** → App-Level Tokens → generate one with scope `connections:write` | `xapp-` |

If the app-level token doesn't exist yet, create it on that page — Socket Mode
requires it and the bot token alone will not do.

## 3. Drop them in (one command)

```bash
printf 'SLACK_BOT_TOKEN=xoxb-REPLACE\nSLACK_APP_TOKEN=xapp-REPLACE\n' >> /home/john/Thunderbird/.env
```

## 4. Verify, then start

```bash
cd /home/john/Thunderbird

# posts a real test message to #d2m-command through the gate
python3 -m core.comms.slack_transport

# starts the button receiver
systemctl --user start slack-receiver.service
systemctl --user status slack-receiver.service --no-pager
```

Expected from the transport self-test:
```
auth.test OK — team=… bot=…
socket-mode app token: present
posted to #d2m-command ts=…
```

---

## What you get

- **#d2m-command** — the 06:30 and 18:30 consolidated briefs
- **#d2m-alerts** — `urgency=NOW` only (money at risk, client-critical dates)
- **Approve / Close / Defer buttons** on every item

A tap writes straight into `OpsCenter/state/commander_closures.jsonl`. That closure is
permanent — no regeneration can resurrect it, which is the fix for "I reduce my queue
and it keeps getting overridden." Defer is deliberately *not* a close: it leaves the
item on your desk but records that you looked, so a deferral is visible rather than
silent.

Slack sits **behind** the gate, not beside it. Everything it shows you has already been
deduped, format-checked and batched by `commander_channel.notify()`. It is a renderer,
not a second path — which is why adding it cannot reintroduce the duplicate problem.

## Telegram

Stays running until Slack proves 48h clean — two emails a day, both readable, no
duplicates, closures sticking. You are not left without a channel during the switch.
The teardown is tracked; it fires only after that gate passes.

## If it doesn't work

| Symptom | Cause |
|---|---|
| `exit code 2` | A token is missing or has the wrong prefix. Not a fault — the service deliberately won't thrash restarting against it. |
| `auth failed: invalid_auth` | Bot token wrong or app not installed to the workspace. |
| `apps.connections.open: invalid_auth` | App-level token missing the `connections:write` scope. |
| Buttons do nothing | `slack-receiver.service` isn't running. Check `logs/slack_receiver.log`. |
