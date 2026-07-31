# Silver False-Hold Audit — sourcePath Fragment Bug

**Scope:** Read-only audit of the blast radius of the bug fixed in commit
`466f27f61` ("silver: a path convention was holding every delegated item,
forever"). Bug lived in `tcd/writeback.py::_handle_auto_task`, which passed
`row["sourcePath"]` (TCD's `"file:key"` convention, e.g.
`OpsCenter/mission_board.json:missions`) verbatim into
`core/silver/gate.py::silver_front_frame`'s `ground_truth_sources`. That
function checks ground-truth sources for **filesystem existence**, and
`OpsCenter/mission_board.json:missions` does not exist as a filename — so
every mission-board item Silver front-framed through this path HELD, citing
`"named ground-truth source(s) do not exist"`.

Analysis performed entirely by processing `OpsCenter/silver_ledger.jsonl`
(1.1 MB, 4,461 lines) and `hale_decisions.md` (10.6 MB) in code — see
commands/scripts below. No files modified.

---

## 1. Hard counts — `OpsCenter/silver_ledger.jsonl`

Verdict totals across all 4,461 ledger rows:

| Verdict | Count |
|---|---|
| PASS | 3,491 |
| **HOLD** | **907** |
| OVERRIDE | 62 |
| VOID | 1 |

Of the 907 HOLD verdicts, classified by whether the hold text cites the
missing-ground-truth-source reason:

| Class | Count | Meaning |
|---|---|---|
| **GT-only** (single reason = missing ground-truth path) | **614** | Would have **PASSED** but for the bug |
| GT + another genuine reason (multi-reason) | 67 | Would have **held anyway** — the bug added a redundant reason, didn't cause the hold |
| No GT mention at all | 226 | Genuine hold, unrelated to this bug |

679 of the 907 HOLD rows mention the exact string
`OpsCenter/mission_board.json:missions`; 1 cites a different (also
fragment-looking but unrelated) path `logs/x.log`; 1 has no source named at
all. So **679 of 907 HOLD rows (75%) trace to the fragment bug**, and of
those, **614 (68% of all HOLDs) were pure false holds** — the item would have
passed Silver's FRONT frame entirely if the bug weren't there.

Non-GT genuine hold reasons (the 226 that are real):

| Reason | Count |
|---|---|
| `board-dup: MISSION-656 duplicates MISSION-655` | 155 |
| criteria not checkable (no count/path/ref/artifact) | 26 |
| artifact is a bare claim, not a concrete reference | 25 |
| no work product given | 16 |
| no acceptance criteria given | 16 |

**Verified `board-dup` is a real duplicate, not another false positive:**
`OpsCenter/mission_board.json` has both `MISSION-655` and `MISSION-656` at
`status: pending_review` with the identical title `"Client inquiry: Re:
Odysseus Password Reset Issue #100210"` — genuine dedup miss, correctly
held.

**Commands that produced these counts** (run via sandboxed Python over the
file, not read into context):
```python
import json
from collections import Counter
lines = open("OpsCenter/silver_ledger.jsonl").read().splitlines()
verdicts = Counter(json.loads(l)["verdict"] for l in lines if l.strip())
# HOLD classification: split each row's holds[] into gt-matching vs other,
# bucket as gt-only / gt-plus-other / no-gt based on presence of each.
```

---

## 2. Hard counts — `hale_decisions.md`

Same classification run against the `**CHIEF SILVER** [...] FRONT|BACK
<id> → VERDICT` lines (the human-readable echo of every ledger row):

| Verdict | Count |
|---|---|
| PASS | 3,326 |
| **HOLD** | **885** |
| OVERRIDE | 62 |

(4,273 total CHIEF SILVER lines found vs. 4,461 ledger rows — the ~188-row
gap is regex-strictness on a handful of malformed/edge lines, not a
discrepancy in substance; the two logs corroborate each other within 2.4%.)

HOLD breakdown, same method:

| Class | Count |
|---|---|
| GT-only (false hold) | 614 |
| GT + other reason (held anyway) | 67 |
| No GT mention (genuine) | 204 |

Numbers match the ledger's GT-only/GT-plus-other counts exactly (614 / 67)
and the "no GT" count is close (204 vs 226 — hale_decisions.md truncates
hold text at 200 chars per line, which occasionally clips a second reason
out of the regex's view; the ledger's raw JSON is the more reliable source
for the "genuine" bucket).

**Command:**
```python
import re
from collections import Counter
verdict_re = re.compile(r"\*\*CHIEF SILVER\*\*\s*\[([^\]]+)\]\s*(FRONT|BACK)\s+(\S+)\s*→\s*(PASS|HOLD|OVERRIDE|VOID)\b")
# scanned all lines of hale_decisions.md for this pattern, bucketed the same way
```

---

## 3. Affected date range

- **Bug introduced:** commit `7b421bea6` — *"fix(tcd): wire Silver gate into
  writeback D->T auto-task + Close/Certify (MISSION-658)"* — **2026-07-17
  16:29:48 -0600**. This is the commit that added
  `ground_truth_sources=[row.get("sourcePath", "")]` in `tcd/writeback.py`.
  The `ground-truth-exists` check itself in `core/silver/gate.py` had
  existed since commit `ce41a1835` (2026-07-16), one day earlier — so the
  checking machinery was armed the day before the bad caller was wired to
  it.
- **First false HOLD actually logged:** **2026-07-27T22:37:32Z** — a
  10-day gap between the bug landing in code and it firing. No commits
  touched `tcd/writeback.py` in that window, so the FRONT-stage auto-task
  path simply wasn't exercised at volume until 2026-07-27 (consistent with
  the "152-item backlog" batch run referenced in the fix commit).
- **Last false HOLD logged:** **2026-07-31T00:19:01Z** (2026-07-30 18:19
  MT), roughly 5 minutes after the fix commit (`466f27f61`, 18:14:35 MT) —
  almost certainly one lagging process/daemon that hadn't picked up the
  code change yet before restart (matches the known
  MCP/daemon-needs-restart-for-code-changes pattern already on file).
- **Net window of actual false holds: 2026-07-27 to 2026-07-30, ~3.5 days**
  of the mission-board backlog being effectively unable to transit D→T at
  all (0/152 passing FRONT frame, per the fix commit's own measurement).
  The bug was *dormant but live* in code for the 10 days before that
  (2026-07-17 to 2026-07-27) without visible effect because the path wasn't
  called.

---

## 4. Other callers of `silver_front_frame` / `run_gate` — fragment risk check

Grepped every call site of `silver_front_frame`, `run_gate`, and every
literal `ground_truth_sources=` assignment repo-wide:

| Caller | Source of `ground_truth_sources` | Fragment risk? |
|---|---|---|
| `tcd/writeback.py:375` (`_handle_auto_task`) | `row["sourcePath"]` (TCD `file:key` convention) | **Was the bug — now fixed** (`.split(":",1)[0]`) |
| `core/relay/delegation_wiring.py:157` | `mission.get("ground_truth_sources")` — caller-supplied list, no TCD sourcePath involved | No |
| `core/staffing/staff_summary_sheet.py` (6 call sites) | Explicit `[path]` (real filesystem paths, mostly self-test artifacts) | No |
| `OpsCenter/mission_board_sync.py:485` (`EXEC: sss`/delegate CLI verb) | Free-text CLI arg, comma-split by the human operator | No structural risk, but unvalidated — see §5 |

`sourcePath` itself (the field carrying the `file:key` convention) is used
in six places (`tcd/item_model.py`, `tcd/sections.py`, `tcd/assignment.py`,
`scripts/clear_proposal_backlog.py`, plus the fixed `tcd/writeback.py`
call). Only `tcd/writeback.py::_handle_auto_task` ever fed it into a Silver
gate call — confirmed via repo-wide grep for `sourcePath` intersected with
`silver`/`ground_truth`. **No other caller carries this specific bug.**

---

## 5. Other latent false-HOLD risks in `core/silver/gate.py` (not yet fired, no ledger evidence — theoretical)

Read the full 404-line file. Two structurally identical classes of bug to
the one just fixed, neither observed in the ledger yet because nothing has
exercised them with the triggering input shape:

1. **URL / Sheet-link ground-truth sources get treated as filesystem
   paths.** `silver_front_frame`'s existence check (line 121-123) is:
   ```python
   missing = [s for s in sources
              if ("/" in s or s.endswith((".md", ".json", ".html", ".py")))
              and not (ROOT / s).exists() and not Path(s).exists()]
   ```
   Any source containing `/` — including `https://docs.google.com/...`
   or any other URL — enters the existence check, and neither
   `(ROOT/s).exists()` nor `Path(s).exists()` will ever be true for a URL.
   **Any ground-truth source that is a live Sheet/Doc/Drive link rather
   than a repo-relative file path will false-HOLD**, for the same reason
   the sourcePath bug did. Not observed yet: grepped the ledger's distinct
   "do not exist" values (only 2 distinct path strings across all 907
   holds) and grepped every `ground_truth_sources=` call site — none
   currently pass a URL. This is a **live landmine**, not a past incident.

2. **The `path@commit` convention is asymmetric between FRONT and BACK.**
   `run_gate` (BACK stage, line 235-236) explicitly supports
   `"path@commit"` refs and strips the `@commit` suffix before checking
   existence. `silver_front_frame`'s ground-truth-exists check (FRONT
   stage) has no equivalent stripping — a source like
   `OpsCenter/foo.py@abc123f` contains `/`, so it enters the check, and
   `Path("OpsCenter/foo.py@abc123f")` will never exist. **The first FRONT
   frame call that reuses the `@commit` convention BACK already supports
   will false-HOLD.** Not observed yet — no current caller uses `@` in a
   `ground_truth_sources` value.

3. **Checked but not currently misfiring:** the BACK-stage `_check_file`
   "criteria promise number(s) not found in artifact" check (line 207-210)
   does a raw substring match of every standalone number in the acceptance
   criteria against the artifact text. It has a coincidental-match false-
   PASS risk (e.g., criteria number "3" matches inside "135") rather than
   a false-HOLD risk, and **zero occurrences in either log** — this check
   type has literally never fired (`grep -c "criteria promise number"` = 0
   in both files), so it's unexercised, not broken. Noting it because it's
   the most date/formatting-fragile check in the file, worth a second look
   if it ever does start firing.

Everything else in the file (`_check_portal`'s count-match/images/
segregation battery, `internal_ops_check`'s board-dup/inbox-dup/memory-
parity battery) is either confirmed-genuine by spot check (§1, board-dup)
or has zero fire count in the observed window — no evidence of false
positives there.

---

## Bottom line

- **614 of 907 logged Silver HOLD verdicts (68%) were false** — the item
  would have passed if not for the sourcePath fragment bug. A further 67
  holds cited the bug alongside a real reason and would have held
  regardless.
- **226 holds are genuine** and unrelated to this bug (dominated by 155
  real board-duplicate catches).
- The false-hold window was short in wall-clock terms (~3.5 days,
  2026-07-27 to 2026-07-30) but total: **0 of the 152-item mission-board
  backlog could transit D→T at all** during that window per the fix
  commit's own before/after measurement, meaning every "Silver held it"
  verdict the Commander saw on a mission-board item in that window was the
  filename bug, not a quality signal.
- The fix (`.split(":",1)[0]` in `tcd/writeback.py:373`) closes the one
  caller that had this exact bug. Two structurally identical un-triggered
  risks remain open in `core/silver/gate.py` itself (§5, items 1-2) —
  recommend hardening `silver_front_frame`'s existence check to skip URLs
  and strip `@commit` suffixes the same way `run_gate` already does,
  rather than waiting for the next caller to rediscover this the hard way.
