# 17:30 MT Nomination Ping — Execution Report

**Task requested:** Deploy `thunderbird-1730-nomination.service`/`.timer` (17:30 MT EOD nomination ping, APPLY_AUTONOMOUSLY).

**Finding:** Already deployed — under a superseding implementation. No new unit created.

## What's actually live

`agents/thunderbird_1730_nomination.py` was split 2026-07-04 (see script docstring) from a single
daily 17:30 fire into a **2x/day half-rotation** design: 0530 MT (half 1) + 1730 MT (half 2), each
covering half the sector list, full daily coverage across both. This lives in two enabled units:

| Unit | Schedule | Status |
|---|---|---|
| `thunderbird-nomination-half1.timer` | 05:30 MT daily | **enabled**, last fired 2026-07-06 05:30, lock written |
| `thunderbird-nomination-half2.timer` | **17:30 MT daily** | **enabled**, last fired 2026-07-05 17:30 (success — sent to Commander, lock written), next fire **2026-07-06 17:30:00 MDT** |

Verified via `systemctl --user list-timers` and `journalctl --user -u thunderbird-nomination-half2.service`:
- 2026-07-05 17:30:03 MDT: message built, sent to Commander, send-lock written (`nomination_sent_20260705_half2.lock`). Clean success.
- (An earlier same-day 14:41 manual/test fire failed on a transient proxy error to Telegram — unrelated to the timer itself, and the 17:30 scheduled fire succeeded regardless.)
- 2026-07-06: half1 already fired 05:30 (lock present: `nomination_sent_20260706_half1.lock`); half2 next fire confirmed for 17:30:00 MDT today.

## The named unit is a stale duplicate

`thunderbird-1730-nomination.service`/`.timer` (created 2026-06-10, **disabled**) is the pre-split,
single-fire predecessor. Its `ExecStart` calls the script with **no `--half` argument**, but the
script's argparse now has `--half` as `required=True`. Enabling this old timer as originally
instructed would either:
1. **Error on every fire** (missing required arg) — the more likely outcome, since no one patched
   the old unit file when the split shipped, or
2. If someone patched it to pass `--half 2`, **duplicate the Commander ping** at the exact same
   17:30 MT slot the half2 timer already covers.

Neither outcome is wanted. **Action taken: left `thunderbird-1730-nomination.timer` disabled,
untouched.** No new service/timer created — would have been redundant infrastructure at best,
broken/duplicate at worst.

## Recommendation

Delete or archive the stale `thunderbird-1730-nomination.service`/`.timer` unit files to prevent
a future session from re-enabling them under the same misunderstanding. Not deleted in this pass
(destructive/irreversible-adjacent, low urgency, no functional impact while disabled) — flagging
for Commander/Hale sign-off rather than removing unilaterally.

## Verification commands used

```
systemctl --user list-timers thunderbird-nomination-half1.timer thunderbird-nomination-half2.timer --all
systemctl --user is-enabled thunderbird-nomination-half1.timer thunderbird-nomination-half2.timer
journalctl --user -u thunderbird-nomination-half2.service --since "2026-07-04" --no-pager
ls OpsCenter/nomination_sent_20260706*
```

— Confirmed by direct systemd/journal inspection, not self-report.
