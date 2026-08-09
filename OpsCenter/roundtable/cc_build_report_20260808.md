# CC BUILD REPORT — Email C2 / Tasking Redesign
**Spec:** `OpsCenter/roundtable/build_spec_20260808.md` (Round Table 2026-08-08)
**Executor:** Hale-CC · **Branch:** `claude/tcd-appsheet-phase0` · **Date:** 2026-08-08
**Status:** 🟢 GREEN — both required checks pass. Not committed (per guardrail).

```
D1 directive_executor      [████████████████████] 100%
D2 email_mode_classifier   [████████████████████] 100%  (no change required)
D3 directive sweep receipt [████████████████████] 100%
D4 tests                   [████████████████████] 100%  16/16 pass
D5 retirement banners      [████████████████████] 100%
OVERALL                    [████████████████████] 100%
```

---

## 1. PATHS CHANGED

| File | Δ | Deliverable | Protected? |
|---|---|---|---|
| `core/comms/directive_executor.py` | +345/−~20 | D1 | No |
| `core/comms/email_mode_classifier.py` | **0 — pristine** | D2 | No |
| `OpsCenter/run_commander_directive_sweep.py` | +67/−12 | D3 | **Yes** (waived) |
| `OpsCenter/dispatch_and_email.py` | +34/−3 | D3 (support) | **Yes** (waived) — *deviation, see §5.1* |
| `tests/test_email_modes.py` | +187 | D4 | No |
| `OpsCenter/email_c2.py` | +7 | D5 | No |
| `OpsCenter/email_task_ingest.py` | +7 | D5 | **Yes** (waived) |

`git diff --stat` (build scope): **6 files, 604 insertions, 43 deletions.**

### What each change does

**D1 — `directive_executor.py`.** Constants `ACKED / _DEFAULT_SEAT="OC" / _JUDGMENT_SEAT="CC" / _URGENT_HOURS=8 / _STANDARD_HOURS=24`. Pure helpers `_pick_seat`, `_deadline_hours`, `_action_line`, `_mission_rdd`, `_render_receipt`, plus `_own_words` / `_is_ack_only` (quoted-matter stripping so a forwarded thread's "Thanks" is not misread as an ack). `_create_email_mission` forwards WHO/RDD/ACTION through to `mbs.add_mission` instead of hardcoding `"unassigned"`. `route_email` takes `thread_id`, `message_id_id`, `previous_mission_id`; dispositions ACK → close ticket, TASKING/CC → create mission, FYI → create-then-close. Thread↔ticket linkage persisted to `OpsCenter/email_thread_missions.json` via `_thread_index_put/_get`. `execute_directive` and the verify gate are untouched.

**D3 — `run_commander_directive_sweep.py`.** `route_email(...)` now receives `thread_id` and `message_id_id`. When it returns a `receipt`, that receipt **is** the reply — substituted for the model prompt, not appended after it, so the Commander gets one email per letter and the existing `if rc == 0:` processed-marking gate is untouched. Fetch, auth validation, dedup, labelling, the d2mc loop, and the protected-file banner are all unchanged. `previous_mission_id` is deliberately not passed: `route_email` resolves the thread's own ticket from its index, so no lookup logic lives in the protected file.

**D5 — retirement.** Both files carry the required banner and a `THUNDERBIRD_RETIRED_EMAIL=1` guard in `__main__` that exits 0 before polling. Default behaviour unchanged (guard is opt-in), so live timers are unaffected. No functional code removed; no files deleted.

---

## 2. PYTEST OUTPUT (final)

```
$ python3 -m pytest tests/test_email_modes.py -q
................                                                         [100%]
16 passed in 0.08s
```

16 tests collected. Coverage of the D4 asks:

| D4 requirement | Test | Result |
|---|---|---|
| CC now creates a mission (TASKED, id not None), renamed | `test_route_email_cc_creates_a_mission` | ✅ |
| FYI creates a lightweight mission, closed | `test_route_email_fyi_files_a_closed_mission` | ✅ |
| ACK `"Roger."` + `previous_mission_id` → ACKED, mission closed | `test_ack_closes_the_referenced_ticket` | ✅ |
| WHO/RDD populated (`assigned_to != 'unassigned'`, criteria non-empty, deadline present) | `test_tasking_populates_who_rdd_and_action` | ✅ |

Beyond the spec's four, the suite also holds: ACK by thread lookup with no `previous_mission_id`; ACK with no open ticket → LOGGED + still replies; urgent letter pulls the RDD in (8h < 24h); and every mode leaves with a DISPOSITION block. The six original classifier tests still pass unchanged.

Silver's FRONT gate is **not** stubbed in the fixture — it is the gate the new acceptance criteria have to satisfy, and stubbing it would let a broken spec ship green. Only its logging targets and the two live side effects of the seat-delegation path (`delegation_wiring._notify_handoff` Telegram handoff, `mirror_stage_to_bus` C2 bus write) are redirected to `tmp_path`.

## 3. IMPORT CHECK OUTPUT

```
$ python3 -c "import core.comms.directive_executor"
$ echo $?
0
```

Literal output is empty — clean import, exit 0. All five touched Python files also pass `python3 -m py_compile`.

### 3.1 Supplementary — `_literal_body()` exercised directly
The `--literal-body` path (§5.1) is the least test-covered code in the build and the whole of D3 rests on it, so it was run rather than inferred:

```
$ python3 -c "... from OpsCenter.dispatch_and_email import _literal_body ..."
[LITERAL] selftest — 86 chars, model not invoked
RETURN:
DISPOSITION — TASKING
WHO:         OC
RDD:         2026-08-10
TICKET:      MISSION-001
FILE MATCHES RETURN: True
LINE COUNT: 4
```

Multi-line receipt survives intact (internal newlines and column alignment preserved; `.strip()` only trims the ends), the `--output` artifact matches the returned body byte-for-byte, and no model was invoked. Two adjacent checks also cleared: `_routed` is referenced only inside its own `try` (lines 509–513) so the `except` path cannot hit an unbound name, and `load_wing_context()` is annotated `-> str` and returns `"Wing state unavailable."` rather than `None` on total failure — so the receipt branch's `wing_ctx.splitlines()` cannot raise.

## 4. SAMPLE RECEIPT BLOCKS

Captured from a **live `route_email` call**, not hand-written from reading `_render_receipt`. The capture harness replicated all eight monkeypatches from the `isolated_board` fixture (board path, lock path, directive ledger, execution log, thread index, Silver ledger + decisions, both `delegation_wiring` stubs), so nothing touched the real mission board, `hale_decisions.md`, Telegram, or the C2 bus. Harness was a throwaway at `/tmp/capture_receipts.py`; nothing was added to the repo.

### 4.1 TASKING letter
Input: `Fwd: Wave Pointe confirmation` / "Add to Loucks dossier, confirm flight arrangements including flight number, times, layover." → `status=TASKED mode=TASKING who=OC`

```
DISPOSITION — TASKING
WHO:         OC
RDD:         2026-08-10T04:27:06.154688+00:00
ACTION:      Add to Loucks dossier, confirm flight arrangements including flight number, times, layover.
DELIVERABLE: MISSION-001 on the board; OC verifies against OpsCenter/directive_executions.jsonl by RDD
TICKET:      MISSION-001
```

### 4.2 ACK letter
Input: solo `"Roger."` in the same thread, **`previous_mission_id` omitted** — the ticket was resolved from the thread index alone, which is exactly the path the sweep uses. → `status=ACKED`

```
DISPOSITION — ACK
WHO:         —
RDD:         —
ACTION:      Roger.
DELIVERABLE: Acknowledged, ticket MISSION-001 closed
TICKET:      MISSION-001
```

### 4.3 Board row after the ACK — ground truth, not the receipt's own claim

```json
{
  "id": "MISSION-001",
  "status": "closed",
  "assigned_to": "OC",
  "source": "email",
  "certified_by": "CC",
  "acceptance_criteria": "Add to Loucks dossier, confirm flight arrangements including flight number, times, layover. — verifiable against the receipt row in OpsCenter/directive_executions.jsonl",
  "deadline": "2026-08-10T04:27:06.156455+00:00"
}
```

The hardcoded `"unassigned"` defect is closed: real seat, real suspense, real criteria, and certifier ≠ assignee.

---

## 5. DEVIATIONS FROM SPEC

### 5.1 `dispatch_and_email.py` edited — an 11th file, and a protected one 🟡
**Spec text:** D3 — *"the prompt must produce the receipt text passed directly, **NOT re-imagined by the model**."*
**Deviation:** added an opt-in `--literal-body` flag (+34 lines) and made `--prompt` conditionally required. The sweep passes the receipt through it.
**Reason:** the requirement is not achievable through a prompt. The first implementation of D3 in the working tree did it the obvious way — a "relay this text EXACTLY, verbatim" instruction wrapped around the receipt — and Haiku obeying an echo instruction is still a model re-imagining the text. A receipt whose entire value is that it states precisely what the machine did with the letter cannot be a receipt the model might restate. `--literal-body` skips the model call outright. I replaced the prompt-echo with it.
**Authority:** the file is #2 of the 10 protected (`core/policy/rules_registry.py:86`), covered by the spec header's *"Commander authorized edit of ALL files including the 10 protected."* It is **not** on the explicit do-not-edit list (contact_ag / wing_relay / engine_limits / task_templates). Its banner is intact; default behaviour is unchanged when the flag is absent; the sweep's subprocess pattern is unchanged.
**Flagging this loudest** because it is the one file I touched that the spec does not name as a deliverable target. Reversible in isolation: drop the flag and restore the prompt-echo block.

### 5.2 `wing_digest` does not exist 🟡
**Spec text:** D3 — *"receipt blocks + wing_digest line."*
**Deviation:** no `wing_digest` artifact, function, or file exists anywhere in the repo — the only occurrence of the string is the spec itself. Interpreted as the wing-state one-liner and implemented as `WING: <first line of load_wing_context()>` appended to the receipt.
**Reason:** the alternative was inventing an artifact. Trivial to repoint if OC meant something specific.

### 5.3 `_create_email_mission` passes two kwargs the spec did not enumerate 🟢
**Spec text:** D1.2 — *"forward ALL to `mbs.add_mission(..., assigned_to=, source="email", acceptance_criteria=, deadline_hours=)`."*
**Deviation:** also passes `certified_by=_certifier_for(assigned_to)` and `ground_truth_sources=[...]`.
**Reason:** required, not optional. Assigning a real seat puts the ticket on the cross-Hale delegation path (`add_mission → delegate_mission`), which Silver's FRONT gate refuses without a named ground-truth source and a certifier distinct from the assignee. Without both, every TASKING letter would produce a `DelegationError` and no ticket. The spec's own note anticipates this ("add_mission is CROSS-HALE delegation-aware"). Acceptance criteria are additionally passed through `_checkable_criteria()`, which appends the receipt-row reference when Silver's `is_checkable()` rejects a bare one-line order.

### 5.4 Spec's premise "currently pristine @HEAD" was already false 🟢
D1 was fully implemented in the uncommitted working tree before I started, and D4's fixture had been updated (though the test bodies had not — 2 tests were failing). See §6.

### 5.5 Retirement banner placed after the shebang, not at line 1 🟢
**Spec text:** D5 — *"PREPEND, keep old banner."*
**Deviation:** inserted at line 2, immediately after `#!/usr/bin/env python3`, above the existing protected banner.
**Reason:** literal prepending breaks the shebang. Read as "first banner," not "first line." Old banners intact. Cosmetic note: `email_task_ingest.py` now has two adjacent `# ====` separator lines where the new banner meets the old — left as-is rather than editing a protected file for aesthetics.

### 5.6 The ACK deliverable has no production route for the dominant case 🔴
Recorded, not fixed — D3 forbids touching the paths involved. This is the most important finding in the report and it is stronger than a generic coverage gap.

`route_email` has exactly **one** call site (`run_commander_directive_sweep.py:497`, in the jl3 loop). Traced against real code, an ACK reaches it only in a minority of cases:

| Path a Commander "Roger." can take | Reaches `route_email`? | What actually happens |
|---|---|---|
| Reply to Hale's own receipt (Hale replies **from** d2mconcierge, so his reply is **To: d2mconcierge**) | ❌ | jl3 loop skips at line 435 (`if d2m_is_to and not d2m_is_cc: continue`) → falls to the d2mc loop → matches that loop's own `_ACK_PHRASES` set (`roger / wilco / done`) at line ~707 → labelled and `continue`. **Silently dropped.** |
| Reply in a CC-mode thread (To: someone else, Cc: d2mconcierge) | ✅ | Routes normally; `_close_ack_ticket` fires |
| Letter with a command prefix, neither To nor Cc d2m | ✅ | Routes normally |

**Consequence:** for the single most common ack in the system — the Commander answering the receipt this build just taught the Wing to send — `_is_ack_only`, `_close_ack_ticket`, the thread index, and the `ACKED` status are **live in tests and dead in production**. The d2mc loop's ack-skip predates this build and was written to stop reply ping-pong; it now also intercepts the ack before the ticket-closing logic can see it. The two mechanisms are in direct conflict and the older one wins.

The same line-435 skip means letters sent straight TO d2mconcierge get no receipt at all — the GOAL's "no silent drops" is delivered for CC'd and prefixed letters only.

**Opinion — this is OC's next item, ahead of anything else.** The fix is small and lives entirely in the two places D3 fenced off: route the d2mc loop's ack branch through `route_email` before it drops the message, and call `route_email` in the d2mc loop generally. I did not touch either, as instructed. **The ACK deliverable should not be reported to the Commander as working end-to-end until this lands** — it is correct code on a path his acks do not travel.

### 5.7 Concurrent writer observed in the working tree 🔴
Two files changed underneath me mid-edit, both times caught by the Edit tool's staleness check rather than silently clobbered:
- `tests/test_email_modes.py` — went from 2 failing tests to a complete, passing 15-test D4 implementation between my read and my edit (22:21). My D4 edit was rejected; on re-read the requirements were already satisfied, so I kept the landed work rather than overwriting it. Count moved 15 → 16 during the session.
- `OpsCenter/run_commander_directive_sweep.py` — D3 landed via the prompt-echo approach at 22:22. My edit was rejected; I re-read and replaced the prompt-echo with the `--literal-body` wiring (§5.1).

An `opencode` process was live throughout. **This means the tree state in this report is a snapshot, and OC should re-run both checks immediately before committing.** No work was lost in either collision, and the final state is green — but I cannot certify the tree is quiescent.

---

## 6. GUARDRAIL COMPLIANCE STATEMENT

I complied with every guardrail in the spec. Verified, not asserted:

| Guardrail | Status | Evidence |
|---|---|---|
| No changes to `core/policy/*`, `.claude/settings.json`, `opencode.json` | ✅ | `git status --short` on all three returns empty |
| Do NOT edit `contact_ag.py` / `wing_relay.py` / `engine_limits.py` / `task_templates.py` | ✅ | `git status --short` on all four returns empty |
| Keep authorization banner text in PROTECTED files | ✅ | Banners in `run_commander_directive_sweep.py`, `dispatch_and_email.py`, `email_task_ingest.py` unmodified; D5 banner added above, not over, the existing one |
| Do NOT send ANY email; do NOT call `gmail_gmail_send`; plan-only | ✅ | No send executed. Receipt capture ran under full tmp isolation with Telegram + C2 bus stubbed. The one `dispatch_and_email.py` invocation was a no-arg validation that exits 2 before any send path |
| Do NOT commit — OC commits after review | ✅ | No `git commit`, `git add`, or `git push` run. All changes uncommitted in the working tree |
| Both checks must pass | ✅ | 16 passed; import exit 0 (§2, §3) |

Additionally, per Wing doctrine: the three Commander gates (client send, financial commitment, strategic direction) were not approached. No client-facing content produced. Nothing was emailed, drafted, or queued for send.

**One thing this report does not claim:** I have not run an independent cross-engine ground-truth check on this work. The spec assigns that to the final independent-seat review before close-out, so it is OC's gate, not mine. Everything above is CC's own verification against real command output.

---

## 7. RECOMMENDATION (opinion)

1. **Commit as-is** — the build meets the spec and both gates are green.
2. **Re-run both checks first** (§5.7) — the tree had a concurrent writer.
3. **Review §5.1 explicitly** before committing. It is the one change that touches a protected file the spec did not name. If OC disagrees, reverting to prompt-echo is a two-line change to the sweep plus dropping the flag — but the receipt would then be model-generated, which I read as contrary to the spec's own words.
4. **Fix §5.6 before this is briefed to the Commander as done.** The ACK deliverable is dead on the path his acks actually travel — the d2mc loop drops "Roger." before `route_email` ever sees it. Everything else in the build works; this one line item does not, and reporting it as delivered would be the exact class of unverified completion claim SO-2026-07-19 exists to prevent.
