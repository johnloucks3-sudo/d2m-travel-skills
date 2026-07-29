# Answer: Do not let OC start deleting yet

**Short answer: No — not as a single bulk delete of all 1,240.** What you've verified so far only proves OC's *output is well-formed*, not that its *findings are correct*. Those are different claims, and the gap between them is exactly where this goes wrong.

## What "JSON validates, count reconciles" actually proves

- Every entry has path/function/line → the report is structurally complete.
- Count matches OC's own summary → OC didn't drop or double-count rows internally.

Neither of these checks whether a given function is *actually* unused. That's a semantic claim about the whole repo's call graph, and static "unused function" detectors are notorious for false positives in exactly the patterns this codebase is full of:

- **String/name-based dispatch** — `keyword_router.py`, MCP tool registries, the `EXEC: sss|chop|decide|...` verb dispatch in the staffing model. A function called only via a dict lookup or `getattr` by name won't show an edge in most static call graphs.
- **Entry points invoked externally, not from other Python** — anything wired into a systemd timer/service, `nexus.py` daemon hooks, cron-triggered scripts, `mission_board_sync.py` CLI subcommands.
- **Plugin/tool surfaces** — MCP tool functions (`mcp__travel__*`, skill packages) are called by an external harness via name/schema, not by an in-repo caller.
- **Dynamic imports / subprocess calls** — `contact_ag.py`-style cross-engine dispatch, `headless_claude_spawn`, anything shelled out to via `subprocess`.
- **Test-only or intentionally-public helpers** — exported API surface, `__init__.py` re-exports, functions kept for OC/AG parity per the equal-performance standard.

Any one of these classes can produce dozens to hundreds of false "unused" hits in a repo this size. At 1,240 candidates, even a modest 5–10% false-positive rate is 60–120 live functions — some of them daemons, timers, or MCP tools that won't fail loudly; they'll just silently stop firing until something needed at 2am doesn't run.

## What I'd do instead

1. **Sample and falsify, don't trust.** Pull a random 30–50 entries from the 1,240 and manually check each name for indirect references — grep the bare function name across the repo (not just the call graph), check systemd unit files, check MCP tool manifests, check string literals. This gives a real false-positive rate estimate in under an hour.
2. **Bucket by blast radius, not just "unused."** Anything under `OpsCenter/`, `core/staffing/`, `scripts/*_worker.py`, `core/relay/`, MCP tool definitions, or referenced by a `.timer`/`.service` file goes in a high-risk bucket that gets individual review regardless of what the scan says. Low-risk (pure internal helper, single file, no exports, no string refs found) can move faster.
3. **No hard deletes on the first pass.** Move candidates to a `_deprecated/` holding area (or comment out + tag) for one full day/cycle instead of `rm`. If nothing breaks and no timer/log complains, delete for real in a second pass. This makes the operation cheaply reversible instead of "revert via git and hope you notice in time."
4. **Batch it, test between batches, log each deletion.** Not all 1,240 in one commit. Delete in reviewed batches, run the test suite (and a live smoke check of timers/MCP tools) after each batch, and keep an audit trail of what was removed and why.

## Bottom line

Have OC do the sampling + risk-bucketing pass next, not the deletion pass. Once we have a measured false-positive rate and the high-risk bucket has been eyeballed, staged removal (deprecate → verify → delete) is fine to authorize. A blind bulk delete off one static scan, on a repo with this much dynamic dispatch and externally-invoked code, is not.
