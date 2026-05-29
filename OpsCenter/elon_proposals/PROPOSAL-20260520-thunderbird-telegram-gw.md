**Proposal written.** 

🦅

**Pattern flagged:** Your Telegram gateway is crashing every ~10 minutes. Systemd restarts it 212 times per week. The auto-healer is masking the root cause instead of fixing it — a classic waste pattern.

**The proposal recommends:** Disable auto-heal, expose the actual crash reason, fix it properly. Hale can do this autonomously during off-hours (lower Telegram load).

**Key insight:** The system *appears* healthy because it keeps restarting. Actually broken. 30 restarts per day means either a memory leak, deadlock, or timeout handler firing on a loop.

**Next move:** Either way, you'll want the logs before Hale investigates. Want me to pull the full journalctl output now, or should Hale handle the diagnosis phase tomorrow morning?
