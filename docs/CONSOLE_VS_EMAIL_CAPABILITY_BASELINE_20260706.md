# Console vs Email — Capability Baseline & Parity Build
**Date:** 2026-07-06 · Built same session as Bryana's Wing-resources manual and quota tracker

## Baseline (before today's fix)

| Capability | Console (Claude Code) | Email (AgentMail), before |
|---|---|---|
| Rich content — attachments, images, HTML, tables | Yes | Yes (proven in the 4-turn thread test) |
| Real-time threading | Yes | Yes |
| **Tool access** (travel search, dossiers, TESS, docs, drive, etc.) | **Yes — full MCP toolset** | **No — inbound mail just sat in a queue file** |
| **Autonomous processing of a request** | **Yes — live reasoning in-session** | **No — required a human to open Console and notice the email** |
| Latency | Seconds (live conversation) | N/A — nothing happened until a human intervened |

**The real gap was never the channel — email already had attachments, images, and threading. The gap was that nothing was on the other end of the inbox.** An email from Bryana would sit unread until John or Hale happened to check.

## Fix built this session: `core/email/hale_email_responder.py`

- Watches the AgentMail inbound queue for messages from Hale-voice-track named-waiver senders (Bryana Jarboe, Susan Loucks — `config/wf17_named_waivers.json`). Arbitrary inbound mail does **not** trigger this — a safety boundary against prompt injection from unverified senders.
- Spawns a headless Claude agent (`claude --bg`) with the **same global MCP config Console uses** (`~/.claude/mcp.json`) — full travel search, dossier, TESS, Drive, and every other Wing tool.
- The spawned agent inherits `CLAUDE.md`/`Personas/hale_cos.md` automatically (same directory context as Console) — same three gates, same doctrine, no special exemption carved out for email.
- Drafts a complete, researched reply, writes it to a file; the responder then sends it back through the same waived AgentMail channel.
- Runs on a timer (`deploy/hale-email-responder.timer`, 5-minute interval) — email now "listens" continuously without a live Console session open.

## Baseline, after the fix

| Capability | Console | Email (now) |
|---|---|---|
| Tool access | Full MCP toolset | **Same full MCP toolset** (identical `--mcp-config`) |
| Doctrine/gates | CLAUDE.md auto-loaded | **Same CLAUDE.md auto-loaded** in the spawned session |
| Can research and act autonomously | Yes | **Yes — closed today** |
| **Latency** | Seconds (live, synchronous) | **Minutes, not seconds** (async: detect → spawn → research → write → send) |
| Real-time back-and-forth mid-thought | Yes (interactive) | No — each email is one complete round-trip, not a live conversation |

**Honest remaining difference — not a gap, a property of the channel:** email is inherently asynchronous. Console gives instant back-and-forth; email gives a complete, well-researched reply within a few minutes of sending. That's the natural shape of email, not something to "fix" further — matching it to Console's live-conversation speed would mean polling every few seconds, which burns AgentMail's rate limit and headless-spawn cost for no real benefit (nobody expects an email reply in 3 seconds).

**Capability is now equal. Latency is, correctly, not — and shouldn't be.**
