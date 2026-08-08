BLUF: KAIZEN item #2 — `scripts/kaizen_report.py`. Renders `mission_board.json` + `delegation_outcomes.jsonl` real state into a mechanical status report, no CC narration. Read-only against both files.

## Silver front frame
- **Done means:** `scripts/kaizen_report.py` exists, compiles, and `--dry-run` (default) prints a report showing correct real counts against the actual files (verify against: 101 pending_review, 42 in_progress, 38 cancelled, 37 active, 31 completed, 4 rolled_up, 4 closed, 3 in_coordination — confirmed real counts as of now).
- **Ground truth:** output counts match those exactly.

## Include
Create exactly one file: `scripts/kaizen_report.py`. Read-only against `OpsCenter/mission_board.json` and `OpsCenter/delegation_outcomes.jsonl` — never write to either.

## Exclude
- No systemd timer/service — separate step after verified.
- Do not touch `mission_board.json` or `delegation_outcomes.jsonl`.
- `--live` sends via `notify()` — do NOT actually call it during your own build/testing; only I will run `--live` after review.

## Report content (mechanical assembly, no narrative generation)
From `mission_board.json`'s `missions` list:
- Count by status (the 8 real values: pending_review, in_progress, cancelled, active, completed, rolled_up, closed, in_coordination).
- List of missions with `priority in ("P0","P1")` AND `status in ("active","in_progress","in_coordination","pending_review")` — these are the "still open, still matters" items. Show `id`, `title`, `assigned_to`, `status`.

From `delegation_outcomes.jsonl` (JSONL — one JSON object per line):
- Count by `verdict` over the last 24 hours (`ts` field, ISO format) — PASS / DISCREPANCY / UNVERIFIED counts.
- List of DISCREPANCY/UNVERIFIED rows from the last 24h, showing `seat`, `ticket_id`, `discrepancy_detail` (truncate to 150 chars).

## Steps
1. `json.loads(Path("OpsCenter/mission_board.json").read_text())["missions"]`.
2. Read `OpsCenter/delegation_outcomes.jsonl` line by line, `json.loads()` each, skip malformed lines silently (matches the existing convention in `core/staffing/delegation_outcomes.py`'s own `_read_rows()` — same defensive pattern).
3. Build the report as described above.
4. `--dry-run` (default): print report as readable text (not raw JSON — this is meant to be human-scannable, like a mini status board — use simple `===` section headers and `-` bullet lists, no fancy formatting library).
5. `--live`: same output, plus one `notify()` call (`from core.comms.commander_channel import notify`, kind="ops", urgency="WINDOW", dedup_key="kaizen-report-daily") with the report text as `body_md`.

## First action
As your first tool call: `python3 -c "import json; d=json.load(open('OpsCenter/mission_board.json')); print(len(d['missions']))"` — confirm you're reading the real file (253+ missions) before writing anything.

## What do you need to succeed?
This is fully specified — every field and count is named above. If the real files don't match what's described (different field names, different status set), say so in your result instead of guessing past it.
