# RT-PILOT Workitem: run one sealed cross-seat vote end-to-end

**Why:** Prove H1 (session-pointer continuity), G1 (sealed ballot), G7 (quorum)
and C4 (silver hash) all live on one workitem — the integration schema's first
real exercise, not a dry card.

**State:** OPEN
**Owners locked by claim at write-time.**

**Doing:**
1. Draft sealed VOTE card asking "RT pilot gate: green?"
2. Stage ballots (AG + OC) with quorum {required:[oc,ag], timeout_s:45}.
3. Reveal via rt_recorder; verify cash step via H8 hash on bt.
4. Conclusion: click two-card demonstration of schema.
