**ELON to Hale:**

Proposal filed at `/home/john/Thunderbird/OpsCenter/elon_proposals/PROPOSAL-20260630-ai-auth-probe.md`.

**Summary:** The probe is hammering Telegram's external API every 15 minutes. When it times out (which it does reliably on network/rate-limit issues), the one-shot repair logic escalates. This feeds a 4x-per-week false-alarm cascade on PRIMARY C2.

**First-principles fix:** Increase timeout window (10s → 15s), add exponential backoff to the timer itself (don't keep probing when it's failing), add fallback check to local gateway (if the bot is alive locally, external API timeouts don't warrant escalation).

**Authority:** Infra resilience. Autonomous execution, no gate.

**Your move:** Apply the code diff, reload the timer, run the probe once to verify. If it succeeds, brief the Commander at the next check-in. If escalations persist, we need to investigate whether Telegram is actually rate-limiting this IP (requires Commander network diagnostics or IP rotation).

Done. — ELON
