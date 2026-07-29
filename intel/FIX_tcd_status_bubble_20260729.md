# FIX: TCD Decision Board status/state bubble — 2026-07-29

## Root cause (one sentence)
`client-portal-server.service` — the long-lived process serving the live
TCD Decision Board at `tcd.d2mluxury.quest` (`tcd/web.py`, restored
2026-07-28 per `config/client_portals.json`) — was started at **03:09:24
MDT**, roughly 7.5 hours **before** commit `1b967d2ea` (10:43:00 MDT) landed
the actual status-pill fix (`_action_state()` + colored, labeled
`.status-pill.<state>` CSS/JS in `tcd/web.py`), so the running process kept
serving the old, dead `<span class="status-pill"></span>` (always empty,
`display:none`, only ever flipped client-side by JS that a page reload
wiped) out of its cached `sys.modules['tcd.web']` — a classic stale-daemon,
no-hot-reload gap, the same class of bug flagged in project memory for the
MCP daemon, just on a different service.

**This was not the code defect it looked like.** The fix already existed
correctly on disk. Nothing needed to change in the fixed file itself.

## Evidence
- `stat` on `tcd/web.py`/`tcd/writeback.py` showed mtime **2026-07-29
  08:44:01** (later touched/rewritten by commit `1b967d2ea`, committed at
  10:43 MDT) vs. `systemctl --user show client-portal-server.service
  -p ActiveEnterTimestamp` = **2026-07-29 03:09:24 MDT** — the service
  predates the fix.
- Before restart: `curl -H "Host: tcd.d2mluxury.quest" -u «REDACTED»:«REDACTED»
  http://127.0.0.1:8925/` returned HTML with the **old** CSS/markup:
  - `.status-pill { ...; display:none; }` with **no** `.approved/.held/
    .closed/.rejected/.modified` classes (0 matches).
  - No `PILL_LABELS`/`PILL_CLASS` JS (0 matches).
  - Every card's pill was the literal dead span: `<span
    class="status-pill"></span>` (× N, all cards, decided or not).
- `git show HEAD:tcd/web.py` byte-for-byte equals the working-tree file
  (confirmed via Python string compare) — the fix was fully committed, just
  not loaded into the running process.
- `git show 1b967d2ea -- tcd/web.py` confirms this commit is where
  `_action_state(row)` (derives decided/label/css_key from
  `status`/`stage`/comment markers) and the `.status-pill.approved/held/
  rejected/closed/modified` CSS + `PILL_LABELS`/`PILL_CLASS` JS were added —
  this *is* the "status/state bubble" feature the Commander asked for.
- The prior attempt (`9e2792e73`, "status-override fix") only fixed
  *persistence of the underlying `status` value* (Close no longer reverting
  to Open on the next 10-min sync via `tcd/overrides.py::apply_status` +
  `tcd/writeback.py::_handle_close`) — real and correct, but it never
  touched the *visual* bubble at all. `1b967d2ea` is the commit that
  actually built the visible/colored/labeled bubble; the Commander's "still
  not working" report landed in the ~30-minute window after that commit but
  before the daemon picked it up.

## What I changed
1. **Restarted the stale service**: `systemctl --user restart
   client-portal-server.service` — no code change, this is the actual fix.
2. Added `tests/test_tcd_web.py` (new file) — regression test for the
   `.status-pill` contract itself (see below), so a future revert of the
   bubble logic in `tcd/web.py` fails CI/pytest even if nobody notices the
   visual regression live.

No other files were modified. `git status --porcelain -- tcd/
scripts/client_portal_server.py` was clean before and after (the fix
commit was already committed; only the config state file
`config/tcd_stage_overrides.json` shows as modified, which is normal
runtime state, not part of this fix).

## Ground-truth verification (mandatory, done)
Fetched the actual live-served board HTML via `curl` against the running
service on `127.0.0.1:8925` with `Host: tcd.d2mluxury.quest` and Basic Auth
(`«REDACTED»:«REDACTED»`, from `config/client_portals.json`) —
**before** and **after** the restart:

**Before restart** (stale):
```
status-pill.approved/.held/.closed matches: 0
PILL_LABELS/PILL_CLASS matches:              0
<span class="status-pill"></span>  (dead, every card)
```

**After restart** (`systemctl --user restart client-portal-server.service`,
confirmed `active`):
```
status-pill.approved/.held/.closed/.rejected/.modified matches: 5
PILL_LABELS/PILL_CLASS matches:                                  4
<span class="status-pill show approved">APPROVED</span>   × 213 real cards
<span class="status-pill show held">HELD</span>            × 66 real cards
<span class="status-pill"></span>  (correctly empty/hidden) × 35 undecided cards
```
213 real Approved cards and 66 real Held cards on the live board now render
a visible, colored, labeled status bubble — this is real production data
from the actual Google Sheet / multi-tab mirror, not a synthetic test.

**Verdict: FIXED**, verified against ground truth (the actual served page,
not a self-report).

## Regression test added
`tests/test_tcd_web.py` — 8 tests against `tcd.web._action_state` and
`tcd.web._card`:
- Each terminal state (Approved via stage advance, Held/Rejected/Closed via
  `status`, Modified via comment marker) produces `(decided=True, LABEL,
  css_key)`.
- An undecided item produces `(False, "", "")`.
- `_card()` on a decided row must emit `<span class="status-pill show
  approved">APPROVED</span>` (visible, labeled, state-classed) and must
  **not** emit the bare dead `<span class="status-pill"></span>`.
- `_card()` on an undecided row must emit the bare hidden span (no `show`
  class) — confirms the test doesn't just always want a label.

Confirmed this test **fails** against the pre-fix code: `git show
9e2792e73:tcd/web.py` (the commit right before `1b967d2ea`) has **zero**
occurrences of `_action_state` — the function doesn't exist yet at that
revision, so `from tcd.web import _action_state` raises `ImportError`
against it. Confirmed it **passes** against current `tcd/web.py` (8/8,
`.venv/bin/python -m pytest tests/test_tcd_web.py -v`).

## Anything still broken / open items
- **Process hygiene gap, not yet closed**: there is no hot-reload and no
  auto-restart-on-deploy for `client-portal-server.service`. Any future
  `tcd/web.py`/`tcd/writeback.py`/`tcd/overrides.py`/`tcd/multi_tab.py` edit
  will silently not take effect on the live board until someone manually
  restarts the service — exactly the gap that caused this incident. This is
  the same class of problem as the documented MCP-daemon-needs-restart
  gotcha, just for a second daemon. Recommend either (a) a post-commit/
  post-deploy hook that restarts `client-portal-server.service` when any
  file under `tcd/` changes, or (b) adding it to the same watchdog pattern
  already used for the MCP daemons. Not built in this session — flagging
  for follow-up, not silently fixed.
- The known **AppSheet "Regenerate structure" gotcha** was investigated as
  a candidate root cause and **ruled out**: AppSheet's Enum/pill rendering
  of the `stage` column (P-D-T-A-C) is a separate, older surface
  (`tcd/item_model.py`, `tcd/staging.py`) from the live web board's
  `.status-pill` (`tcd/web.py`), and the Commander's specific complaint (the
  "recent guidance") maps to the web-board bubble, not the AppSheet stage
  pill. If the Commander's complaint is actually about the **AppSheet**
  pill specifically rather than the `tcd.d2mluxury.quest` board, that is a
  separate, unverified surface — flagging as **UNVERIFIED** for that
  specific case since I did not have AppSheet UI access to check it.
