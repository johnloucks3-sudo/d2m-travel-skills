# Answer: Do not start deleting yet

**No — hold the deletion.** The three checks you listed (JSON validates, every entry
has path/function/line, count reconciles with OC's own summary) all verify the
**shape** of OC's report. None of them verify the **substance** of its claim that
these 1,240 functions are actually unused. Schema-valid is not the same as correct.

## Why this specific pattern is a known failure mode

This is the exact trap the delegation playbook warns about: acceptance criteria that
check structure and count, and say nothing about the subject of the finding. The
canonical example is a "stub audit" that returned a schema-perfect JSON file with 40+
entries and valid verdicts — and it had grepped compiled binaries like `/usr/bin/docker`
for a string pattern and reported byte offsets as evidence. Every criterion passed.
Zero real findings. Same shape of risk here: a static "no call site found" sweep is
notorious for false-positiving on:

- Dynamic dispatch / reflection (`getattr`, string-based routing, dependency injection)
- Decorator-registered or config-driven callbacks (routes, Celery/cron tasks, event
  handlers, plugin hooks)
- Public API / `__all__` exports and library entry points called only by external
  consumers
- Test-only helpers and fixtures (used, but not from "production" call sites the
  sweep may have scoped to)
- String-literal invocation (dynamic imports, CLI subcommand dispatch)

OC's own summary reconciling with the count only proves OC's report is internally
consistent — not that the underlying detection method (whatever it is) correctly
identifies dead code. "It validates" was never a claim about correctness.

## Why this matters more here than usual

Deleting 1,240 functions is close to irreversible in practice even under git: no one
is going to line-by-line diff a 1,240-function deletion to catch the handful that were
actually live. A quiet wrong answer here is expensive. This is exactly the kind of
task that should get independent verification before it executes, not after.

## What to do before authorizing any deletion

1. **Sample and verify against ground truth yourself** (or via an independent
   engine) — pull ~30–50 entries at random from the 1,240 and grep the codebase for
   each function name, specifically checking the false-positive categories above
   (dynamic dispatch, decorators, exports, test usage, string-literal calls).
2. **Ask OC what its exclusion boundaries were**, explicitly — did the sweep exclude
   generated code, vendored/third-party directories, `__init__.py` re-exports, and
   test fixtures, or just fail to flag them as used? Don't assume a boundary was
   applied because the count looks plausible.
3. **Add a value that can only be right if the work was really done**: e.g., "repo
   still builds and the test suite still passes after deleting a sample batch of N
   functions." That's mechanically checkable; "JSON validates" is not evidence of
   correctness.
4. **If the sample turns up any false positives**, don't proceed to mass deletion —
   send the specific false-positive pattern back to OC as a new exclusion rule and
   re-run the sweep, rather than hand-filtering 1,240 entries yourself.
5. **Delete in small batches with tests run after each batch**, never as one
   1,240-function sweep — batching turns an irreversible mistake into a caught one.

## Bottom line

Validate the sample against real call sites first. Only after that holds up, greenlight
a scoped, batched deletion — never authorize the full 1,240-function delete off schema
validation and a self-reported count alone.
