BLUF: Item #23 — chop-chain notify. Real production data confirmed: `mission_board.json`'s `missions` list has SSS-shaped entries (an `ocr_chain` field) mixed in with regular missions. 3 real ones are `status: in_coordination` with an office genuinely `pending`. Notify-only, no board mutation — the safest possible first version.

## Silver front frame
- **Done means:** `scripts/sss_chain_notify.py` exists, compiles, and running it (`--dry-run` default) against the real board correctly identifies exactly 3 sheets (SSS-005, SSS-006, SSS-007) as needing notification (CC pending on all 3, per real data already checked).
- **Ground truth:** dry-run output JSON matches this known-correct set.

## Include (exact scope)
Create exactly one new file: `scripts/sss_chain_notify.py`. Read-only against the board — never write to `mission_board.json` in this version (that's a bigger, separate design question about who "resolves" the pending state — not in scope here).

## Exclude
- No board mutation, ever, in this script.
- No systemd timer/service files — separate step after this is verified.
- Do not touch `core/staffing/staff_summary_sheet.py` or `comms/thunderbird_sss.py` — read `OpsCenter/mission_board.json` directly, nothing else.

## Real data shape (already confirmed — don't re-derive)
```python
# A mission with an ocr_chain field is an SSS. Example real entry:
{
  "id": "SSS-005",
  "status": "in_coordination",   # only this status means "actively waiting"
  "ocr_chain": [
    {"office": "CC", "status": "pending", "comment": "", "ts": ""}
    # some real entries have multiple offices; only ones with status=="pending" need notifying
  ],
  ...
}
# status values seen in ocr_chain entries: "pending", "concur", "concur_with_comment", "nonconcur"
# Only "pending" needs a notification. "closed" missions (even with pending entries in their
# chain, e.g. SSS-001) are DONE — closed via a different path (Commander override) — never notify on those.
```

## Steps
1. `json.loads(Path("OpsCenter/mission_board.json").read_text())["missions"]`.
2. For each mission with an `ocr_chain` key AND `status == "in_coordination"`:
   - For each entry in `ocr_chain` where `entry["status"] == "pending"`: add `{"sss_id": mission["id"], "title": mission.get("title", ""), "office": entry["office"]}` to a `needs_notify` list.
3. Build report: `{"needs_notify": [...], "scan_time": <now iso>}`.
4. `--dry-run` (default): print report as JSON, do nothing else.
5. `--live`: print report, then if `needs_notify` is non-empty, import `from core.comms.commander_channel import notify` and send ONE notify() call (kind="ops", urgency="WINDOW") listing all pending offices/sheets — one call for the whole batch, not one per item (avoid notification spam). Use `dedup_key="sss-chain-notify-scan"` so repeated runs with the same still-pending set don't re-page.

## First action
As your first tool call: `cat OpsCenter/mission_board.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d['missions']))"` — confirm you can read the real file before writing anything.

## What do you need to succeed?
This is a small, fully-specified read-only script. If anything about the real board's structure doesn't match what's described above, say so in your result rather than guessing past it.
