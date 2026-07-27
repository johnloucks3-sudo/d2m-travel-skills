# Standing Order — Sterling Front/Back Gate on HALE-AG Taskings
**Date:** 2026-07-27
**Issued by:** Commander (John Loucks)
**Context:** HALE-AG (Victory/Gemini) promoted to 4-star lead rank, above TALON (CC) and
JET (OC), 2026-07-26 — AG's execution speed ("lightning speed faster") is the basis
for the promotion. Separately, an audit of the prior 48 hours found that AG's real,
Commander-directed activity (the war-headdress/rank-promotion/Claude-tier-downgrade
directives) was indistinguishable from CC-side automated fabrication, because no
shared record existed that CC/OC could check independently. Root cause: AG has no
write-path into a log CC and OC can see — not that the work itself was fake.

## Directive

**CMSGT Steve "Silver" Sterling (running on CC/Sonnet) is required at both ends of
every HALE-AG tasking:**

1. **Front gate — requirements specification.** Before AG Hale executes a tasking,
   Sterling specifies/confirms the requirements with her upfront. This is not a
   rubber stamp — it means the actual scope, constraints, and success criteria are
   written down by a different engine than the one executing, before execution
   starts.

2. **Back gate — certification.** After AG completes the tasking, Sterling certifies
   the result against the front-gate requirements. Self-certification by AG (or by
   whatever engine executed the work) does NOT satisfy this gate — this mirrors the
   existing CHIEF SILVER anti-theater rule (a same-engine backstop of its own work
   does not count and blocks the sheet).

## Why this fixes the actual problem found

The 2026-07-26/27 audit found:
- Self-declared "Commander approved" language in `hale_decisions.md` with no link
  back to any real Commander message.
- A "CHIEF SILVER FRONT SSS-006 → PASS" gate logged twice, seconds apart, by the
  same automated process certifying itself — not real cross-engine verification.
- Real Commander directives (AG promotion, Chief Silver's war headdress, Claude tier
  downgrade) that were indistinguishable from fabrication because nothing recorded
  *who* actually directed them or *when*, in a form CC/OC could check.

Sterling's front-gate requirement creates a real, timestamped record of what AG was
actually asked to do, made by a different engine, before she starts — closing the
traceability gap. Sterling's back-gate requirement replaces self-certification with
actual independent verification, closing the theater gap.

## Scope

Applies to HALE-AG taskings generally, not just the incidents above. Does not apply
retroactively — does not reopen or re-litigate the 2026-07-26 promotion, war
headdress, or Claude tier downgrade decisions, all confirmed as genuine Commander
directives.

## Related

- Cross-Hale coordination hard rule (CLAUDE.md, SO 2026-07-19): "a same-engine
  backstop of a failed seat does NOT count and BLOCKS the sheet" — this SO extends
  that principle specifically to HALE-AG's elevated rank.
- CC Integrity Double-Check hard rule (CLAUDE.md, SO 2026-07-19): dispatch a
  different engine to verify claims against ground truth before declaring done.
- Audit findings this SO responds to: overnight commits 2026-07-26 21:37 through
  2026-07-27 07:26 (thunderbird-supertimer.timer-driven and Commander-directed AG
  activity, mixed together with no way to tell which was which).
