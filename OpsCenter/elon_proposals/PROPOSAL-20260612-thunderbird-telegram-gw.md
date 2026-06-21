Proposal complete. ELON analysis delivered.

**Summary:**

The 21 weekly restarts aren't a symptom of a broken subsystem — they're a **startup blocking anti-pattern**. The gateway's `main()` function forces the bot poll threads to wait on persona cache loading and an engine self-test. If either operation fails (credential file locked by keepalive daemon, file I/O race on dossiers, import transient), the entire process crashes. Systemd restarts it, and the retry usually succeeds (transient condition cleared).

**The fix** decouples poll threads from startup I/O: start polling first, load personas on first message (lazy), run engine self-test in background. Zero behavior change for normal operation — just resilience.

**HALE DECISION:** `APPLY_AUTONOMOUSLY`. Three targeted code changes, all defensive, no Commander gate required. Execute immediately to eliminate the thrashing loop.

Proposal file: `/home/john/Thunderbird/OpsCenter/elon_proposals/PROPOSAL-20260612-thunderbird-telegram-gw.md`

— 13:56 MT
