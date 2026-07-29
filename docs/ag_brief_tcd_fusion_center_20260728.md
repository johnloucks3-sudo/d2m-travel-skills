# AG Build Brief — TCD Fusion Center: Full Sheet Mirror + Gmail Draft Cards

Victory — this is a real build, not a research task. Implement every item below across
the listed files. The Commander's own words on scope: "Everything in this sheet should be
mirrored in the portal and appropriately described... along with the draft emails it is
the universe of what you require for me... ALL TABS in the sheet are to be included, if
they require a decision. We MAY include intel items later but not now."

Repo: `/home/john/Thunderbird`. All output paths must be **absolute**
(`/home/john/Thunderbird/...`) — relative paths land in your brain sandbox, not the repo.

## Spreadsheet ground truth (already read live this session — reuse, don't re-derive)

Spreadsheet id `1L7WWppZ7LB9Is5EUBp9zu6FThPghcyuGuB4IEQtYsUQ`, 9 tabs:

| Tab | Schema | Include? |
|---|---|---|
| **Items** | `id/inbox/type/priority/stage/title/from/date/snippet/body/link/sourcePath/comments/status/owner` | Yes — full mirror |
| **CommanderReview** | `Mission ID/Priority/Title/Status/Assigned To/Description/Link/CMDR ACTION/REMARKS` | Yes — canonical mission-decision source |
| **Missions** | Same mission schema + `updated_at/comments` | Yes, filtered + deduped vs CommanderReview |
| **ELON 77** | `Mission ID/Title/Status/Assigned To/Created/Priority/CMDR ACTION/REMARKS` | Yes, filtered + deduped vs CommanderReview + Missions |
| **TechScans** | Items-schema + `CMDR ACTION/REMARKS` | Only rows where `CMDR ACTION != "SEE REMARKS"` |
| **Next7** | Items-schema + `CMDR ACTION/REMARKS` | Only rows where `CMDR ACTION != "SEE REMARKS"` |
| **Sources** | `name/url/category/notes/CMDR ACTION/REMARKS` | **No — do not read.** Pure reference links, every row is `SEE REMARKS`. |
| **Ship Intel** | Ship reference table | **No — do not read.** Static reference, no decision semantics. |
| **Intel** | (unread) | **No — do not read.** Explicit Commander instruction: not now. |

**Critical cross-tab finding:** CommanderReview, Missions, and ELON 77 draw from the SAME
mission-ID space — MISSION-677 confirmed present in both CommanderReview and Missions;
MISSION-696 confirmed present in both CommanderReview and ELON 77 (identical titles, read
live this session). A naive mirror double/triple-lists the same mission. **You must dedupe.**

**Note on the `CMDR ACTION` column:** in the live samples, its value is Hale's own
pre-filled recommendation ("APPROVED", with reasoning in REMARKS as "HALE RECOMMENDS:
..."), not something the Commander set. Render it on the card as a labeled recommendation
("Hale recommends: ..."), never as if it were already the Commander's actual decision —
the real decision still flows through the existing click-to-act buttons.

## Build checklist

**0. Message-capture logging (do this first).** `core/relay/contact_ag.py` builds a peer
prompt and returns your stdout/stderr to the caller but never persists the exchange
anywhere durable. Patch it so every `contact_ag()` call appends a timestamped entry
(outbound prompt + your full reply: stdout/stderr/returncode) to
`/home/john/Thunderbird/OpsCenter/collaboration/routing_log.md`, keyed by `verdict_tag`.
Log the attempt regardless of success/failure — not just on `ok`.

**1. `tcd/mfr.py`** (new file) — `describe(item: dict) -> str`. Pure function, no I/O.
Produces one line: `WHO: ... · WHAT: ... · DEADLINE: ... · REC: ...`, dispatched by the
item's `type`/id-prefix:
- `alert-*`/`watch-*`: WHO=client/system, WHAT=condensed message, DEADLINE=trigger/suspense
  date if present, REC=priority-driven default.
- `mission-*`: WHO=owner, WHAT=title, DEADLINE=suspense date, REC=stage-based.
- `gmail-*` (inbound mail, not drafts): WHO=sender, WHAT=subject+snippet condensed,
  REC=reply-needed vs FYI based on unread/priority.
- `draft-*` (new, see #3): WHO=recipient, WHAT=one-line ask, DEADLINE, REC.
- `keep-*`: **title only, never the note body** — this is an existing, deliberate security
  rule (a prior incident put raw secrets from Keep notes into this less-protected store;
  do not regress it).
- `sms-*`: sender + text (same as existing snippet).
- `techscan-*`/`next7-*`: WHO="Tech Scans"/"Calendar", WHAT=title, REC=Hale's CMDR ACTION
  value labeled as a recommendation.
- everything else: generic WHO=source, WHAT=title, REC="review".

**2. `tcd/collectors.py`** — add `collect_gmail_drafts()`. `gmail_list_drafts`/
`gmail_list_drafts_sync` in `core/email/thunderbird_gmail.py` never wire up
`pageToken`/`nextPageToken` — hard capped at 25/50, silently drops anything past that (this
already bit an earlier 25-draft triage pass this session — do not repeat it). **Call the
raw Gmail API `drafts().list()` directly with a `pageToken` loop until `nextPageToken` is
absent** — mirror the existing raw-API pattern already in `collect_gmail()`
(`tcd/collectors.py` ~line 97, `messages().list()`) for both accounts in the existing
`GMAIL_ACCOUNTS` list. For each draft, `drafts().get(id=..., format="full")` for headers
(To/Subject/Date) + snippet + `message_id`. Emit `id=f"draft-{account}-{draft_id}"`,
`inbox="operational"`, `type="decision"`. Same fail-soft-per-account contract as
`collect_gmail()` (auth/API failure on one account returns `[]` for that account only).
Wire into `collect_all()`.

**3. `tcd/permalink.py`** — add a `fid.startswith("draft-")` branch to `derive_link()`.
`compose=` deep links are known-unreliable (do not use). Default link: the drafts-folder
URL `https://mail.google.com/mail/u/0/#drafts`. Test
`https://mail.google.com/mail/u/0/#drafts/<message_id>` once against one real draft — keep
it only if it reliably opens that specific draft; otherwise ship the folder link and lean
on the `describe()` MFR line so the Commander rarely needs to click through blind.

**4. `tcd/multi_tab.py`** (new file) — read the five non-Items decision-bearing tabs
(`CommanderReview`, `Missions`, `ELON 77`, `TechScans`, `Next7`) via the Sheets API,
normalize into the common item-dict shape (`id/inbox/type/priority/title/from/date/
snippet/body/link/status`):
- `CommanderReview`/`Missions`/`ELON 77`: `id=f"mission-{Mission ID}"` — **reuse the same
  id-prefix scheme `scripts/tcd_data.py::build_missions()` already uses** for the Items-tab
  mirror (grep it first) so dedup is a simple set-membership check, not a new scheme.
  Filter `Status in ("active","pending_review")`, `inbox="strategic"`, `type="decision"`.
  **Dedup precedence, in order:** (a) drop from Missions any Mission ID already in
  CommanderReview; (b) drop from ELON 77 any Mission ID already in CommanderReview or
  Missions; (c) drop any Mission ID that already appears in the Items-tab mirror via
  `build_missions()`. Log the count dropped as duplicate at each stage — do not silently
  merge.
- `TechScans`/`Next7`: already Items-shaped — skip any row where `CMDR ACTION ==
  "SEE REMARKS"`. Prefix ids with the tab name (`techscan-*`/`next7-*`, matching what's
  already live in the sheet) — grep for id collisions with the Items tab first.
- Do not read `Sources`, `Ship Intel`, or `Intel` at all.

**5. `tcd/web.py`**:
- `_pending_rows()`: remove the current id-prefix allowlist (`alert`/`watch` only) — admit
  all Items-tab rows, plus `multi_tab`'s deduped rows. Split `status in ("Closed",
  "Delete","Reference")` into a collapsed/secondary section per lane rather than hiding
  them — "mirrored" means present somewhere, not necessarily leading.
- `_card()`: use `mfr.describe(row)` as the primary description line, replacing the raw
  snippet/body fallback, for every item type.
- `render_board()`: add a "show closed/reference" collapse toggle per lane. Keep the
  existing strategic/operational/reference lane grouping.

**6. Guardrails — do not violate:**
- WF-17 stays absolute: no card's "Approve" action ever sends anything. Draft cards open
  the drafts-folder link for the Commander to review/send himself. No new send path, on
  any item type, under any circumstance.
- Do not touch `writeback.py`'s `DELEGATED_WORK_PREFIXES`.
- Approve/Modify/Hold/Reject/Close on ANY card (mission-shaped, tech-scan-shaped, or
  otherwise) writes back to the **Items** tab's existing override system only — do not add
  a new write path to CommanderReview/Missions/ELON 77/TechScans/Next7.

## Known items to re-verify by name (not to discover independently)

No prior draft-triage cache exists on disk. Your fresh summary pass over Gmail drafts must
explicitly report pass/fail on these five, by name — if your pass doesn't re-surface them,
that's a signal your summary pass is shallow, not that the issues resolved themselves:
- Three "sixty days" solo drafts (Furlow, Ely-Darrow, Nichols) — wrong-spouse salutations
- A Kotor excursion draft referencing an already-past Jul 22 sail date
- A Kuklinski auto-draft with no recipient set, referencing a near-term Jul 31 deadline

## AG self-check before reporting done

Report explicit pass/fail on each:
1. `collect_gmail_drafts()` loops on `pageToken`, does not call the capped MCP tool.
   State the real per-account draft count you found vs. what the collector returned.
2. `tcd/mfr.py::describe()` spot-checked against 3-4 real rows of different types — confirm
   the `keep-*` case does NOT include note body text.
3. Ran `python3 -m tcd.sheet_sync` for real; `draft-*` rows landed in the Sheet.
4. State the deduped mission count and show your work — how many raw rows in each of
   CommanderReview/Missions/ELON 77, how many dropped as duplicate at each precedence
   stage, how many remain.
5. Confirm `Sources`, `Ship Intel`, `Intel` are not read anywhere in your new code (grep
   for the tab name strings yourself and show the grep came back empty).
6. Confirm the routing-log patch (#0) produces a real entry — show the actual log line.
7. State pass/fail on each of the five known-flagged drafts above, by name.

Print a one-line verdict starting `AG-VERIFY DONE:` summarizing what you built and any
item above that did NOT pass. Do not claim something passed if you didn't actually run the
check — CC will independently re-verify every item in this self-check against ground
truth before this is reported to the Commander as done.
