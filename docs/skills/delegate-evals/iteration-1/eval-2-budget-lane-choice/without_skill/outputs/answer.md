# Budget Allocation: Refactor + Security Review at 70% Weekly Limit

**Bottom line: security review gets your remaining Claude budget. The refactor goes to a cheaper/different lane.**

## Split

**Security review of the auth module → you (Claude), now, prioritized.**
- High stakes, low tolerance for missed findings — this is exactly where the strongest available reasoning should be spent, not rationed.
- Auth code is usually small relative to a "big refactor," so it's a bounded draw on the remaining 30%.
- Do this first while budget is fresh, not squeezed at the end of the 30-hour window.

**Big refactor → route around the constrained resource.**
- Refactors are typically large and mechanical: consistent patterns applied across many files, not judgment-dense per file.
- Options, in order of preference:
  1. **A cheaper/different model or tool** (local model, a lower-cost API tier, an IDE-integrated assistant) for the bulk mechanical transformation, with you spot-checking a sample rather than authoring every change.
  2. **Chunk it and interleave**: do the highest-risk or highest-ambiguity files yourself in short, tight sessions; hand boilerplate-pattern files to scripting (codemod/AST tool) instead of LLM generation at all where the transformation is regular enough.
  3. If neither is available and it must be Claude: do the refactor in small, reviewable increments and stop the moment budget gets tight enough to threaten the security review — the review is the one that can't slip.

## Why this order, not the reverse

- Refactor risk is caught by tests/CI/code review after the fact. A missed auth flaw is caught by an attacker.
- Refactors degrade gracefully if done with a weaker tool (worst case: some inconsistency, cleanup PR later). Security review does not degrade gracefully — a shallow pass gives false confidence, which is worse than no review.
- 30 hours / 30% budget is enough for one careful pass at a *scoped* auth review; it is not enough for both a careful auth review and a fully Claude-authored large refactor. Something has to give, and it should be the lower-stakes, more mechanical item.

## If the refactor can't wait and can't be offloaded

Narrow its scope now: identify the subset of the refactor that's actually blocking something this week, do only that slice yourself, and explicitly defer the rest past the budget reset rather than burning the security-review budget to finish it early.
