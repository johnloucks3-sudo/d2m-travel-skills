# Standing Order — SILVER Front/Back Gate Across CC, OC, AG
**Date:** 2026-07-27 (revised same day — broadened from initial AG-only scope)
**Issued by:** Commander (John Loucks)
**Context:** HALE-AG (Victory/Gemini) promoted to 4-star lead rank, above TALON (CC) and
JET (OC), 2026-07-26 — AG's execution speed ("lightning speed faster") is the basis
for the promotion. Separately, an audit of the prior 48 hours found that AG's real,
Commander-directed activity (the war-headdress/rank-promotion/Claude-tier-downgrade
directives) was indistinguishable from CC-side automated fabrication, because no
shared record existed that CC/OC could check independently. Root cause: AG has no
write-path into a log CC and OC can see — not that the work itself was fake.

## Directive

1. **Front gate — joint criteria, SILVER final OK.** SILVER and HALE jointly develop
   the requirements/success criteria for a tasking upfront. Both contribute — this is
   not SILVER dictating in isolation — but **SILVER holds final sign-off** on the
   criteria before execution starts. Scope, constraints, and success criteria are
   written down before execution begins, not reconstructed afterward.

2. **Back gate — SILVER-only certification, all three engines.** SILVER has
   **exclusive backend certification authority over CC, OC, and AG** — not just AG
   taskings. No engine certifies its own work; self-certification (a same-engine
   backstop of its own output) does not satisfy this gate and blocks the sheet,
   regardless of which of the three engines produced the work.

3. **Roles are model-agnostic, not fixed engine assignments.**
   - **SILVER** can run on any high-performing analytical model — not locked to
     CC/Sonnet. The seat is defined by the role (independent, analytical,
     certification authority), not by which engine happens to be backing it.
   - **HALE** may be backed by a strong AG-side model when warranted (not
     restricted to a single fixed model either) — matching the same
     role-over-engine principle.

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

Applies across all three engines (CC, OC, AG) generally, not just AG taskings and not
just the incidents above. Does not apply retroactively — does not reopen or
re-litigate the 2026-07-26 promotion, war headdress, or Claude tier downgrade
decisions, all confirmed as genuine Commander directives.

## Related

- Cross-Hale coordination hard rule (CLAUDE.md, SO 2026-07-19): "a same-engine
  backstop of a failed seat does NOT count and BLOCKS the sheet" — this SO extends
  that principle specifically to HALE-AG's elevated rank.
- CC Integrity Double-Check hard rule (CLAUDE.md, SO 2026-07-19): dispatch a
  different engine to verify claims against ground truth before declaring done.
- Audit findings this SO responds to: overnight commits 2026-07-26 21:37 through
  2026-07-27 07:26 (thunderbird-supertimer.timer-driven and Commander-directed AG
  activity, mixed together with no way to tell which was which).
