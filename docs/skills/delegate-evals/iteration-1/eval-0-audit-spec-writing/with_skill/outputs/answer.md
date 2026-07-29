# Task spec: audit every timer-launched Python script for stub vs. real implementation

## Routing decision

**Lane: OC (Jet).** This is mechanical work with a boundary I can draw exactly —
classify N known files against a fixed rubric, cite line-numbered evidence, emit
structured output. No design judgment, no client voice, no synthesis across
sources. It's a bad fit for AG (nothing to independently review yet — AG comes in
*after* OC reports, as the cross-engine check) and a waste of the MAX bucket to
self-execute (183 files × read-and-classify is exactly the volume this skill
warns against burning CC tokens on).

The failure mode this skill calls out by name — "audit every timer-invoked
script for stubs" turning into grepping `/usr/bin/docker` for `NotImplementedError`
and reporting byte offsets as evidence — is *this exact task*. So the scope is not
left for OC to discover. I built and froze the file list myself first.

## Where to start

```
cd /home/john/Thunderbird
```

All manifest paths are absolute, so `cd` only matters for reproducing the
generation command below if the manifest is ever regenerated.

## The frozen manifest (Include — nothing else)

I enumerated every `systemctl --user` timer on this box, resolved each one's
paired `.service` unit's `ExecStart=` to the Python file it actually launches
(resolving `%h` → `/home/john`, resolving relative paths against the repo root,
and resolving four `-m module.path` invocations to their source files), and
deduplicated. Ground truth, run just now:

- 245 `.timer` unit files total, 172 currently active/listed
- 187 raw `ExecStart=` lines reference a `.py` path (directly or via `-m`)
- 6 excluded (see below) → **185 files in the frozen manifest**

Manifest file (one absolute path per line, committed alongside this spec):
`/home/john/.claude/skills/delegate-workspace/iteration-1/eval-0-audit-spec-writing/with_skill/outputs/timer_python_scripts_manifest.txt`
SHA256: `df9e48b518d4bfc863f1207792e11c06068f7134d30a4616be12546f1213e514`

Regeneration command (for reproducibility only — OC does not re-run this; OC
audits the frozen list above):

```bash
cd /home/john/Thunderbird
for u in $(systemctl --user list-unit-files --all --no-pager | grep '\.timer' | awk '{print $1}'); do
  svc="${u%.timer}.service"
  systemctl --user cat "$svc" 2>/dev/null | grep -E '^ExecStart=' | head -1 | sed "s|^|$svc | "
done
```

**Explicitly excluded, with reason (OC must not add these back in):**

| Path / reference | Reason excluded |
|---|---|
| `/home/john/.claude/gcp_gemini_costs.py` | Outside the Thunderbird repo — different codebase, different owner |
| `/home/john/claude_token_counter.py` | Outside the Thunderbird repo |
| `core/cost_dashboard/collectors/openrouter.py` | Timer references it; file does not exist on disk (dangling `ExecStart`, service is broken — a *different* finding, log separately, do not classify as STUB) |
| `OpsCenter/kuklinski_jul15_creative_chain_trigger.py` | Same — dangling reference, file missing |
| `scripts/check_poe_health.py` | Same — dangling reference, file missing |
| `scripts/mcleod_daily_itinerary.py` | Same — dangling reference, file missing |

If OC believes a file belongs in the audit that isn't in the manifest, it goes
in a `flagged_additional_candidates` field in the output — OC does not silently
expand the working set. That is the one interpretive judgment call OC is allowed
to record but not act on.

## The rubric

Four verdicts, defined by what's *in the file*, not by its filename or its
timer's name:

- **REAL_IMPLEMENTATION** — has at least one function whose body is more than a
  docstring, and at least one line matching a real I/O operation (file write,
  subprocess call, network call, DB call, systemctl call, MCP call, etc.)
- **PARTIAL_STUB** — has real I/O evidence, but the ratio of stub-bodied
  functions to real ones is at or above 1:1 — i.e., a meaningful fraction of
  what it claims to do isn't there yet
- **STUB** — every function body is empty/`pass`/`...`/`raise NotImplementedError`
  (after stripping docstrings), or the whole file is under 15 lines with no I/O
  at all
- **MISSING / SYNTAX_ERROR / UNREADABLE** — the file can't be classified at all
  (shouldn't occur inside the frozen manifest — all 185 already verified to
  parse; report immediately as a manifest-integrity discrepancy if it does)

## The tool (run it, don't narrate it)

`/home/john/.claude/skills/delegate-workspace/iteration-1/eval-0-audit-spec-writing/with_skill/outputs/stub_detector.py`

```
python3 stub_detector.py <path>
```

Parses the file with `ast` (never executes it), classifies every top-level
function body as stub or real, greps for a fixed list of I/O markers with line
numbers, greps for TODO/FIXME/NotImplementedError with line numbers, and prints
one JSON object. I ran it against all 185 manifest files as a calibration pass
before writing this spec:

```
{'REAL_IMPLEMENTATION': 183, 'PARTIAL_STUB': 2, 'STUB': 0}
```

Two files landed on PARTIAL_STUB: `core/ai_infra/daemons/router_health_daemon.py`
and `scripts/ci_sentinel.py`. **Zero STUB verdicts is the finding I trust least**
— per this skill, a perfect-looking record is a signal to check harder, not
proof there's nothing to find. That's why the acceptance criteria below require
OC to hand-inspect every PARTIAL_STUB and a random sample of REAL_IMPLEMENTATION
verdicts rather than accept the tool's output as-is.

## Required output

One JSON file at `/home/john/.claude/skills/delegate-workspace/iteration-1/eval-0-audit-spec-writing/with_skill/outputs/audit_results.json`:

```json
{
  "manifest_sha256": "df9e48b518d4bfc863f1207792e11c06068f7134d30a4616be12546f1213e514",
  "generated_at": "<ISO-8601 timestamp>",
  "entries": [
    {
      "script_path": "/home/john/Thunderbird/OpsCenter/metronome.py",
      "verdict": "REAL_IMPLEMENTATION",
      "detector_output": { "...": "raw stub_detector.py JSON for this file" },
      "evidence_lines": [
        {"line": 214, "quote": "<exact text of that line in the file>", "why": "one sentence"}
      ],
      "human_note": "one sentence, only required for PARTIAL_STUB/STUB, and for any REAL_IMPLEMENTATION verdict OC disagrees with the detector on"
    }
  ],
  "summary": {"REAL_IMPLEMENTATION": 0, "PARTIAL_STUB": 0, "STUB": 0, "total": 185},
  "flagged_additional_candidates": [],
  "dangling_timer_references": ["core/cost_dashboard/collectors/openrouter.py", "..."]
}
```

## Acceptance criteria — every one is a command, not an opinion

1. **Set equality with the manifest.**
   `jq -r '.entries[].script_path' audit_results.json | sort -u` must produce a
   file byte-identical to `timer_python_scripts_manifest.txt` (`diff` exits 0).
   No additions, no omissions, no duplicates.
2. **Count integrity.**
   `jq '.entries | length' audit_results.json` == 185, and
   `jq '.summary | .REAL_IMPLEMENTATION + .PARTIAL_STUB + .STUB' audit_results.json`
   == the same 185.
3. **Evidence is real, not narrated.**
   For every entry, `sed -n '<line>p' <script_path>` must contain the exact
   `quote` text cited at that line number. A script (I will run this, not OC)
   spot-checks 100% of PARTIAL_STUB/STUB entries and a random 20% of
   REAL_IMPLEMENTATION entries.
4. **Detector re-run matches.**
   `python3 stub_detector.py <script_path>` re-run by me must produce the same
   `verdict` field embedded in `detector_output` for every entry — if OC's
   embedded detector output doesn't match a fresh run, that entry is rejected
   as fabricated, not "close enough."
5. **No verdict from filename or docstring alone.**
   Any entry whose only cited evidence is a comment, a docstring, or the
   filename itself (no line from `io_evidence` or `todo_evidence`, no quoted
   executable line) fails review regardless of which verdict it claims.
6. **PARTIAL_STUB and STUB entries carry a human_note that names the specific
   missing capability** (e.g., "sends no email, `_notify()` at line 88 is
   `pass`"), not a restatement of the tool's field names.
7. **Dangling references logged, not classified.**
   The 4 files with no on-disk target must appear under
   `dangling_timer_references`, not silently dropped and not given a
   REAL_IMPLEMENTATION/STUB verdict they can't earn.
8. **Zero-STUB is not accepted at face value.**
   If `summary.STUB == 0`, OC's submission must include, for every
   PARTIAL_STUB entry plus at least 15 randomly chosen REAL_IMPLEMENTATION
   entries (I will supply the random seed/list), a `human_note` confirming
   manual read-through — not just the detector's say-so. Missing notes on
   any of those 17 entries is an automatic UNVERIFIED, not a pass.
9. **`py_compile` sanity.** `python3 -m py_compile <script_path>` must exit 0
   for every entry classified REAL_IMPLEMENTATION or PARTIAL_STUB (a file that
   doesn't even compile can't be "real").

## Verification (before I record this as done)

Per this skill's rule — never accept the report as the result — I run
criteria 1–4 and 7/9 myself as raw commands against whatever OC returns, and
hand-read the 2 PARTIAL_STUB files plus a 10-file random sample end to end
before trusting the 183/2/0 split. If the independent read turns up even one
REAL_IMPLEMENTATION verdict that's actually a stub the detector's marker list
missed, I widen the marker list, re-run the whole batch, and treat the original
submission as DISCREPANCY, not PASS.

## Recording

Outcome goes through `core.staffing.delegation_outcomes.record_outcome()` —
PASS, DISCREPANCY, or UNVERIFIED, never upgraded past what criteria 1–9
actually establish. If OC can't be reached or times out, that's UNVERIFIED on
the whole batch, not a silent retry-as-self-execute.
