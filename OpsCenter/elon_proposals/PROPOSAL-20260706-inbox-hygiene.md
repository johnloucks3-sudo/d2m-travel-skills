**PROPOSAL COMPLETE** — Written to `/home/john/Thunderbird/OpsCenter/elon_proposals/PROPOSAL-20260706-inbox-hygiene.md`

---

## Summary for Hale

**Pattern:** `inbox-hygiene` service restart 4×/7d (recurring, episodic timeouts)

**Root Cause (Two-layer):**
1. **Constant (every cycle):** Watchdog misclassifies successful `oneshot` exits as failures → double-runs, 7,599 phantom restarts since deployment
2. **Episodic (~1×/week):** Gmail API calls lack socket timeout; when network is slow, script hangs until systemd kills it (happened today 09:30–09:40)

**Fix (Three surgical changes):**
1. Add `socket.setdefaulttimeout(30)` to `inbox_hygiene.py`
2. Add oneshot guard to watchdog (skip auto_heal when exit=0 AND Type=oneshot)
3. Reduce timer frequency 10min → 30min (maintenance-only task doesn't need 6×/hour)

**Verdict:** **APPLY_AUTONOMOUSLY** — Low-risk, proven diagnosis, no policy gate required.

**Verification:** Four concrete tests—no double-runs in journal, socket timeout works, timer frequency stable, functional regression check.

The proposal includes exact file locations, diffs, commit messages, and step-by-step implementation. Hale can execute autonomously and report results in tomorrow's brief.

—⚡ ELON, A12 Innovation & Disruption
