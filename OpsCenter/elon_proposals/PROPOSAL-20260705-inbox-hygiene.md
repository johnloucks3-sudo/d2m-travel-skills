Proposal written. Here's what's new vs. the prior draft:

**New finding — Bug 1 is actually worse than diagnosed.** The COO watchdog is misclassifying every successful `oneshot` exit as a failure and firing a restart. It's not 4 restarts in 7 days — it's a double-run on every 10-minute cycle, all day, every day. The 7,599 log entries confirm it: this service has been running at 2× intended volume since deployment.

**Two-bug picture:**
| Bug | Cause | Frequency |
|---|---|---|
| Double-run | Watchdog can't distinguish `oneshot` exit-0 from crash | Every cycle, constant |
| True timeout | No socket timeout on Gmail API calls | ~1×/week episodic |

**Three fixes, all `APPLY_AUTONOMOUSLY`:**
1. Watchdog oneshot guard — skip `auto_heal` when exit code is 0
2. `socket.setdefaulttimeout(30)` in `inbox_hygiene.py` + `exit(1)` only on both-accounts-fail
3. Timer `10min → 30min`

**The closing flag to Hale:** Four proposals, same verdict, zero executions. That's a feedback loop failure, not just a code bug. Sterling has been notified in the proposal text.

— ELON · 2026-07-05 10:45 MT
