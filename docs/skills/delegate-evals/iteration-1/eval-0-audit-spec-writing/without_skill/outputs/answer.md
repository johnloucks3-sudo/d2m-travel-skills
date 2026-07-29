# Task Spec: Audit Python Scripts Launched by systemd User Timers

## 1. Objective

Produce a single inventory file that classifies every Python script launched by a
systemd **user** timer on this host as one of:

- **REAL** — the script does the work its name/timer implies (has functioning
  logic, hits real I/O — files, network, subprocess — and would produce an
  observable side effect if run)
- **STUB** — the script is a placeholder: mostly `pass`, `TODO`/`FIXME`
  comments, `NotImplementedError`, hardcoded/fake return values, or logic that
  never actually calls out to do anything
- **PARTIAL** — some functions/branches are real, others are stubbed (mixed)
- **UNREACHABLE** — the ExecStart target does not resolve to a script on disk
  (moved/deleted/typo'd path)

This does not require running the scripts — it's a static read-and-judge audit.

## 2. Scope — how to build the list (do this first, don't skip)

1. Enumerate every unit: `ls ~/.config/systemd/user/*.timer` (currently 240
   timer files; expect the exact count to drift — re-count, don't hardcode 240).
2. For each `<name>.timer`, find its paired `<name>.service` in the same
   directory and read the `ExecStart=` line(s). Ignore `ExecStartPre=`/`ExecStartPost=`.
3. **Filter to Python only.** Roughly 56 of the ~240 ExecStart lines are NOT
   Python — they're `/bin/bash script.sh`, `/bin/true`, `/bin/sleep`,
   `goose-d2m run --recipe ...yaml`, `ttyd`, inline `bash -c "..."` one-liners,
   etc. Exclude these from the audit entirely; list them separately in an
   "excluded — non-Python ExecStart" section of the output so the Commander
   can see the filter was applied deliberately, not silently.
4. For Python ExecStart lines, extract the actual script path:
   - Direct form: `.../python3 /home/john/Thunderbird/path/to/script.py <args>`
     → target is `path/to/script.py`.
   - Module form: `python3 -m tcd.sheet_sync` → target is the module's source
     file (resolve `tcd/sheet_sync.py` relative to the repo/venv, not the
     dotted string itself).
   - Multiple timers sometimes point at the **same** script (e.g. daily +
     weekly variants calling one script with different args). De-duplicate by
     resolved file path, but list every timer name that maps to it — one row
     per unique script, with a `timers` column that can hold multiple names.
5. Expect roughly 210 unique Python script paths across ~184 Python-launching
   services (these are estimates from a preliminary scan on 2026-07-29, not a
   promise — the real count is whatever step 1-4 produces).

## 3. Classification rubric (apply per script, in this order)

Work through these checks top to bottom. First match wins — record which rule
fired, not just the verdict.

1. **File missing** → `UNREACHABLE`. Note the path that was expected.
2. **File exists but under ~15 lines of actual code** (imports + a `print` or
   a single `pass`) → `STUB`.
3. **Any of these present, and they gate the script's main effect** (not just
   in a comment/docstring) → `STUB`:
   - `raise NotImplementedError`
   - a function whose entire body is `pass` or `...` where that function is
     what the script's `main()`/entrypoint calls
   - `# TODO: implement` / `# FIXME` sitting where real logic should be, with
     no logic after it in that code path
   - hardcoded return of fake/canned data where the script's job (per its
     filename and any docstring) is to fetch or compute something live
4. **Script has real control flow AND at least one of:** a network call
   (`requests`, `httpx`, `google-api`, `smtplib`, MCP/tool call), a subprocess
   call, a file write/read outside of just logging, or a DB/API client call
   that isn't mocked → `REAL`.
5. **Some functions meet the REAL bar, others meet the STUB bar** (e.g. the
   alerting path is implemented but the actual data-fetch function is a stub
   returning `{}`) → `PARTIAL`. List which functions are which.
6. Anything not resolved by 1-5 → flag as `NEEDS-HUMAN-REVIEW` with a one-line
   reason. Do not force a REAL/STUB verdict you're not confident in — a wrong
   confident verdict is worse than an honest "unsure."

**Do not infer "real" from the filename or docstring alone.** A file named
`fpd_auto_update.py` with a docstring claiming it "auto-updates FPD dates"
that actually just logs and returns is a STUB, not a REAL, despite the name.

## 4. Output format

One file: `/home/john/Thunderbird/OpsCenter/audits/systemd_timer_script_audit_<YYYYMMDD>.md`

A markdown table, one row per unique script:

| Script path | Timer(s) | LOC | Verdict | Rule fired | Evidence (file:line) |
|---|---|---|---|---|---|

Plus three summary sections at the top of the file:
- **Counts**: total timers scanned, Python-launching services, unique scripts,
  and a verdict breakdown (`REAL: N, STUB: N, PARTIAL: N, UNREACHABLE: N,
  NEEDS-HUMAN-REVIEW: N`).
- **Excluded (non-Python ExecStart)**: list of timer names filtered out per
  §2.3, so the exclusion is auditable.
- **Top-line risk list**: every STUB or UNREACHABLE script whose timer runs
  more often than once per hour (i.e., it's burning wall-clock cycles doing
  nothing) — sort this list by run frequency, most frequent first.

## 5. Batching (this is a ~210-script job — don't send it as one shot)

Split into batches of 25 scripts per OpenCode dispatch, grouped alphabetically
by resolved path (not by timer name) so duplicates from step 2.4 land in the
same batch. Each batch is a self-contained task: same rubric (§3), writes to
the same output file (append, don't overwrite), reports back batch number and
row count written. ~9 batches expected. Sequence them; don't parallelize
against the same output file (write races).

## 6. Acceptance criteria (checkable — this is what verify_and_record checks against)

1. **Coverage**: row count in the output table equals the unique-script count
   from §2.5, cross-checked by `wc -l` against the deduplicated path list —
   zero scripts silently dropped.
2. **No unresolved paths without a verdict**: every row has one of REAL /
   STUB / PARTIAL / UNREACHABLE / NEEDS-HUMAN-REVIEW — no blank verdict cells.
3. **Evidence column populated for every non-REAL verdict**: STUB, PARTIAL,
   and UNREACHABLE rows must cite a specific file:line or "path not found" —
   a verdict with no evidence is treated as a failed row.
4. **Exclusion list matches the filter**: spot-check 5 excluded entries against
   their actual ExecStart lines — confirm none of them are secretly Python
   (e.g., a `bash -c "python3 ..."` wrapper that should have been included).
5. **Rubric rule cited per row**: the "Rule fired" column references §3's
   numbered list (1-6) for every row, not free text — this is what makes the
   audit re-checkable without re-reading every script.
6. **Spot-check pass rate ≥ 90%**: pull a random 20-script sample from the
   final table, independently re-read those 20 scripts, and confirm the
   verdict matches. ≥18/20 agreement required to accept the batch; below that,
   the whole batch it came from gets re-run, not patched row-by-row.
7. **No claimed run**: OpenCode reports completion only after the output file
   exists on disk with the row count from criterion 1 — a summary claim
   without the file is treated as not done.

## 7. What NOT to do

- Don't execute any of the audited scripts. Static read only — some of these
  scripts send real client emails or make real bookings; running them is out
  of scope and would violate the client-send gate (WF-17) if triggered.
- Don't "fix" stubs found along the way. This is an audit, not a repair pass —
  flag it, don't touch it. (A follow-up repair task gets scoped separately
  once the inventory is in hand.)
- Don't guess a verdict to keep the row count moving — use
  `NEEDS-HUMAN-REVIEW` per §3.6 rather than force REAL/STUB.
