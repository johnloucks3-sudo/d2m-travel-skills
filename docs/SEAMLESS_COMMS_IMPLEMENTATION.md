# SEAMLESS COMMS ARCHITECTURE — IMPLEMENTATION STATE
## Email · Telegram · Signal
**Date:** 2026-07-06 | **Supersedes:** docs/HALE_COMMS_ARCHITECTURE_PLAN_v1.md (2026-05-18 — stale, see note below)

---

## WHY THIS DOC EXISTS

`docs/HALE_COMMS_ARCHITECTURE_PLAN_v1.md` was written 2026-05-18 against an
n8n/Gmail-centric architecture. Since then AgentMail became PRIMARY C2
(CLAUDE.md, 2026-07-06) and most of the plan's Phase 1/2 deliverables were
independently built and wired in. Re-implementing them from the old plan
would have duplicated live code. This doc records what's ACTUALLY true today,
verified file-by-file, plus the one genuinely new piece (Signal) and the one
real gap that was found and closed (Commander's own email trigger).

---

## 1. EMAIL — WORKING, ONE GAP CLOSED

| Component | State | Where |
|---|---|---|
| Thread-aware reply (In-Reply-To/References) | ✅ Live | `core/email/thunderbird_gmail.py:2377` `gmail_reply_in_thread()`, in `TOOL_REGISTRY` |
| Autonomous headless-spawn reply for named-waiver friends | ✅ Live | `core/email/hale_email_responder.py` — Bryana Jarboe, Susan Loucks (Hale voice track) |
| AgentMail as PRIMARY C2 (not Gmail/n8n) | ✅ Live | `core/email/agentmail_listener.py` (WebSocket, real-time) |
| **Commander's own email → autonomous in-thread reply** | 🆕 **Built this session** | same file, see below |

**Gap found:** `hale_email_responder.py`'s trigger set was named-waiver
friends only — Commander emailing `hale-thunderbird@agentmail.to` got no
autonomous reply, only a silent queue entry until the next Console session.

**Fix:** added `COMMANDER_EMAIL = "johnloucks3@gmail.com"` as a second
trigger class alongside the waiver list. Commander messages get a distinct
prompt (no "waived friend" framing, full three-gate doctrine stated
explicitly) and reply via `AgentMailClient.reply_to_message()` on the CONDOR
inbox (`hale-thunderbird@agentmail.to`) — in-thread, not a new thread every
time. No waiver-list involvement; this is within-wing (SO 24 MAR 2026), no
gate required.

**Bug found and fixed (pre-existing, unrelated to this scope but blocking
the fallback path):** `agentmail_listener.py`'s Telegram fallback notifier
called `thunderbird_telegram_gw.py send <text>` — that subcommand doesn't
exist. The script's actual CLI is `--relay <text> --source <name>`. Fixed
in both `agentmail_listener.py` and the new `core/signal/signal_relay.py`
(which copied the same wrong pattern before being corrected). Verified live:
a real relay send now returns `{"status": "sent", "returncode": 0}`.

**Success signal (plan's own test):** verified via unit test — Commander
sender classification + AgentMailClient wiring. Full live test requires
Commander to actually send `hale-thunderbird@agentmail.to` a message and
observe the timer-driven reply (`deploy/hale-email-responder.timer` cadence)
— not exercised live in this session (would require an inbound message not
under our control to fabricate safely).

---

## 2. TELEGRAM — ALREADY SOLVED, VERIFIED NOT REBUILT

| Plan item | State | Where |
|---|---|---|
| 4096-char chunking, paragraph/word-boundary aware | ✅ Live | `core/communication/thunderbird_telegram_fmt.py: split_message()` |
| XML-bleed / markdown safety | ✅ Live | same file: `md_to_telegram()` (telegramify-markdown) + `strip_markdown()` fallback |
| Stateful per-chat conversation context | ✅ Live | `core/learning/thunderbird_conversation_bridge.py`, wired into `core/communication/thunderbird_telegram_c2.py` |
| Shared dispatch/classification brain | ✅ Live | `OpsCenter/telegram_hale_router.py: should_use_hale()` / `get_hale_response()` |

Nothing new was built here — the plan's Phase 2 items #4, #5, #6 already
exist and are wired. Verified by direct import + unit test
(`tests/test_seamless_comms.py::test_telegram`), not by filename inspection
alone.

---

## 3. SIGNAL — BUILT THIS SESSION (genuinely new)

signal-cli (JVM build, v0.14.5) installed to `vendor/signal-cli-0.14.5/`
(no sudo, no native-lib dependency — works on any Linux with a JRE; this
host has OpenJDK 25).

| File | Purpose |
|---|---|
| `core/signal/signal_cli_adapter.py` | Thin wrapper: `is_linked()`, `link_device()`, `send_message()`, `receive_messages()`. Every function degrades to a structured result (never raises) when the device isn't linked yet. |
| `core/signal/signal_router.py` | Polls for new messages, dispatches each through the **existing** Hale brain (`telegram_hale_router.get_hale_response()` — one classifier, three channels, no new logic duplicated), replies to the same sender. State: `OpsCenter/state/signal_router_seen.json`. |
| `core/signal/signal_relay.py` | Fallback: if a Signal send fails, notify via Telegram relay (`--relay`) rather than silently losing the message. Also pushes the one-time device-link ask to Telegram the moment it's generated. |

**Architecture note (from the locked Commander decisions in the old plan,
carried forward):** signal-cli links as a SECONDARD DEVICE to Commander's
own Signal account (719-291-0742) — this is Personas/hale_cos.md's existing
Channel Registry entry ("Signal | 719-291-0742 (linked to YOGA) |
Commander only | Plain, concise — Hale only, no Dani"). Not a separate bot
identity; Hale reads/replies through Commander's own linked account.

**The one human-only wall, already staged:** device linking requires
scanning a QR/URI in the Signal app once. Attempted live this session —
`link_device()` produced a real, valid link URI:

```
sgnl://linkdevice?uuid=xd9AB0w2MZRYY8ZQ42kwGQ%3D%3D&pub_key=BfM4fleAJxY0bAH8oyYRYaFF2xnH6XiiqbpKSCf5VXhn
```

This is single-use and will have expired by the time this doc is read —
re-run `python3 -c "from core.signal import signal_cli_adapter as a; print(a.link_device())"`
to generate a fresh one when ready to link. The relay already pushed the
ask to the Telegram system-relay channel (D2M Channels) as a live test of
`signal_relay.relay_link_pending_notice()` — confirmed `{"status": "sent",
"returncode": 0}`.

**Everything downstream of that one scan works unattended** — `signal_router.py`
is ready to run on a timer the same way `hale_email_responder.py` does.

---

## SLA / FORMAT PER CHANNEL (as actually implemented)

| Channel | Format | Brain | Notes |
|---|---|---|---|
| Email (AgentMail) | Plain/HTML, in-thread reply | Sonnet (headless spawn) | Named-waiver friends + Commander (this session) |
| Telegram | MarkdownV2, chunked at 4096 | `telegram_hale_router` substrate selection (haiku/sonnet/opus) | Live, unchanged |
| Signal | Plain text | Same shared `get_hale_response()` as Telegram | Live pending one device-link scan |

---

## TEST SUITE

`tests/test_seamless_comms.py` — tests against the plan's SUCCESS SIGNALS,
not a file manifest:
- Email: TOOL_REGISTRY wiring + Commander-trigger classification + AgentMailClient import
- Telegram: chunking produces valid ≤4096 chunks from >4096 input; markdown-strip removes bleed; ConversationBridge importable
- Signal: binary present; adapter/router degrade cleanly pre-link (no exceptions); relay callable

Run: `/home/john/Thunderbird/.venv/bin/python3 tests/test_seamless_comms.py`
Result at time of writing: **12/12 passed**.

Cross-channel live send/receive test (task on all 3 channels, verify all 3
reply within SLA) requires the Signal device-link step above to complete
first — Email and Telegram paths are independently verified live in this
session (Telegram relay send confirmed; email wiring unit-tested since
fabricating a live Commander inbound isn't something to safely simulate).
