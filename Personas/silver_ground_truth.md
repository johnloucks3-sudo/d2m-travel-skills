# SILVER'S GROUND TRUTH
## CMSgt Steve "Silver" Sterling — living log of internal-ops findings
*Companion to `silver_sterling_command_chief.md`. This is where Silver keeps what he's learned — the standard he holds people to comes from here, not from memory. Load on demand when running `--internal-ops` or reviewing wing hygiene.*

---

## ENTRY 2026-07-04 — The Duplication Pattern (Commander directive — Silver on internal processes)

**Commander's complaint, verbatim:** "too many duplicate triplicate 80 copies of the same message over several weeks... 79 action items in my daily report for months... eliminate frustrating flood of the same message over and over... invades my other computer programs on laptop AND phone."

**The pattern, found across FOUR independent systems today — it is the same bug wearing four uniforms:**

Every one of these was **level-triggered** (re-fires every run while a condition holds) instead of **edge-triggered** (fires once when a condition *starts*, stays silent while it persists unchanged). That is the root cause. Not four bugs — one bug, four locations.

1. **Mission board** (`OpsCenter/mission_board_sync.py`) — `cmd_add` had zero duplicate check. Same work got a new MISSION-#### every time it was re-surfaced: MISSION-214/820/1511/1523 (Regent portal auth, 4x), MISSION-SEC-05/1510/1522 (GitHub credential rotation, 3x). Fixed: `_find_open_duplicate()` blocks creation, logs to the existing open mission instead.
2. **Staff-tasking timer** (`OpsCenter/staff_tasking_timers_system.py`) — dedup was a 24h *cooldown*, not a one-time gate. An overdue-but-still-PENDING task (Kuklinski/Westbrook TP-1.4) re-injected into `claude_inbox.md` every single day 2026-06-30 → 2026-07-04. Fixed: dedup_key once written, never re-injects for that key, period.
3. **Commander directive sweep** (`core/email/thunderbird_commander_inbox.py`) — self-generated Wing broadcasts (daily brief, compressed brief, inbox digest, "✅ Answer" acks) ship with subject "(no subject)" — the noise-pattern filter only checked the subject, so it missed all of them and re-tasked the Wing's own broadcast as a new "Commander directive" mission every day. Fixed: filter now checks subject **and** first 300 chars of body; added the missing patterns.
4. **Credential health check → Telegram** (`scripts/credentials_health_check.py`) — `alert_hours_ahead` set *larger* than the credential's natural rotation window (regent_cookies: 48h threshold on a ~7h auto-refreshing cookie; gmail_token: 24h threshold on an hourly OAuth access token with a refresh_token). A perfectly healthy, auto-refreshing credential is "about to expire" *by definition*, forever. Separately: its Telegram import (`from OpsCenter.thunderbird_telegram_gw import send_telegram_message`) has never actually existed — the alert call always silently failed, so this one never reached a phone, only the local brief log. Fixed both: tightened thresholds to genuine-problem level, added one-and-done dedup, and the broken import is now moot (dedup gates it either way — flag if this needs a real working send path).
5. **Wing → Commander paging** (`core/comms/wing_page.py`) — the doctrine already defined P2 = "informational, no action needed," but nothing enforced it; any caller could page D2MC2C at P2. Fixed: P2 now logs to `wing_page_maintenance_log.jsonl` instead of paging Telegram at all. P0/P1 now carry one-and-done dedup by fingerprint (level+source+problem) — `clear_page_dedup()` resets one when the Commander wants a fresh recurrence to page again.

**The check, going forward (Silver's own gate — `scripts/silver_gate.py --internal-ops`):**
- Duplicate OPEN mission-board entries (same normalized title, >1 open ID).
- Re-injected UNREAD inbox tasks (same task_id injected UNREAD more than once without being read/closed).
- Board hygiene via `brain_bridge` (pending/claimed items left undeclared).
- Run PASS at close of this session: 0 findings.

**The test for any new automation from this point on:** *does this fire once when something changes, or does it fire every time it's checked?* If the second — it's the same bug in a fifth uniform. Ask before building it.

---

## ENTRY 2026-07-04 — Gmail: two separate bugs under one complaint

**Commander's ask:** "fix the gmail send problem from d2m to johnloucks3 inbox and from d2m to johnloucks3 drafts." Looked like one bug. Was two, unrelated except by address.

1. **Drafts:** `gmail_create_draft_sync()` hard-coded the d2mconcierge account and *refused* (`RuntimeError`) to stage anywhere else — a policy frozen at MISSION-180 (pre-2026-06-20), superseded since by SO_TP_DRAFT_ROUTING_20260620 (Commander reviews/comments from johnloucks3, can't format in d2m drafts). Every current client TP draft (`build_grandeur_preview_drafts.py` — the live Furlow/Ely-Darrow/Nichols Scandinavia portal work) was staging in the wrong mailbox. Fixed: defaults to johnloucks3 now, `stage_in="d2mconcierge"` is the explicit opt-out. Live-tested: draft created, found, and confirmed in johnloucks3's own Drafts.
2. **Inbox:** d2mconcierge→johnloucks3 mail wasn't landing in the wrong *tab* — it was missing the `INBOX` label entirely (delivered, then silently archived; only a `CATEGORY_*` label remained). 47 messages found in that state on the live test. Cause not fully root-caused (no `gmail.settings.basic` scope to inspect filters) — but the fix is durable and in-scope: `scripts/inbox_restore.py` (new 5-min timer) adds `INBOX` back, which — unlike category-label removal (reasserted by Gmail's classifier, confirmed this morning's revert of `primary_router.py`) — verified stable on recheck.
3. **Unresolved, needs Commander:** the wrong-*tab* problem (Promotions/Updates instead of Primary) needs a Gmail *filter*, which needs `gmail.settings.basic` scope — neither token has it. That's a one-click OAuth re-consent, not something to build blind. Flagged, not built.

---

## STANDING QUESTION FOR SILVER TO CARRY
Before any new persona/script/timer ships: **"When this condition is still true tomorrow, does it speak again, or does it stay quiet?"** If nobody can answer that in one sentence, it isn't ready.
