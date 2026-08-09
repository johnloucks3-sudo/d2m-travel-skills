# BUILD SPEC — Email C2 / Tasking Redesign (Round Table resolution 2026-08-08)
# Author: OC (coordinator). Executor: CC (Sonnet). DO NOT EDIT THIS SPEC.
# Commander authorized edit of ALL files including the 10 protected. Final
# independent-seat review required before close-out. Applied on branch
# claude/tcd-appsheet-phase0. Tests MUST stay green: pytest tests/test_email_modes.py

## GOAL (non-negotiable, from Commander)
Gmail the Wing C2/email office-staff front desk is:
- EVERY letter (TASKING / CC / FYI / ACK) → a threaded reply receipt
  (WHO / RDD / ACTION / DELIVERABLE). No silent drops. Even acks.
- TASKING + CC → creates a mission with WHO=assigned_to, RDD=deadline,
  ACTION=acceptance_criteria. No more hardcoded "unassigned".
- ACK closes the referenced ticket (thread linkage), logs not spam.
- FXI filed row, not work: closed record.

## DELIVERABLES — EXACT CHANGES (offset fresh files; none are modified now)

### D1 — core/comms/directive_executor.py  (NOT protected; currently pristine @HEAD)
Extend without breaking existing tests. Keep `route_email`, `execute_directive`
declared.

1. Constants: add `ACKED = "ACKED"`, `_DEFAULT_SEAT = "OC"`, `_JUDGMENT_SEAT = "CC"`,
   `_URGENT_HOURS = 8`, `_STANDARD_HOURS = 24`. (reuse `_ACK_ONLY_RE` patterns: words
   roger|wilco|done|ok|okay|thanks|acknowledged|duly noted|copy, solo line.)

2. `_create_email_mission(title, description, priority="P1", assigned_to="hale",
   acceptance_criteria="", deadline_hours=24)` — forward ALL to `mbs.add_mission(
   ..., assigned_to=assigned_to, source="email", acceptance_criteria=
   acceptance_criteria, deadline_hours=deadline_hours)`. Keep lock discipline as-is.
   NOTE: add_mission is CROSS-HALE delegation-aware. assigned_to must be a real seat
   (OC/CC/AG) or a persona; test on tmp with seat "OC".

3. Add helpers (pure): `_pick_seat(subject, body)` → "CC" if judgment keywords
   (client, email to, draft, strategy, review, decide, architecture, approve,
   opinion) else "OC". `_deadline_hours(subject, body)` → 8 if URGENT/RED/ASAP/🔴
   else 24. `_action_line(subject, body)` → first real line, ≤200 chars.
   `_render_receipt(mode, mission_id, who, rdd, action, deliverable, note="")` →
   the DISPOSITION block. `_mission_rdd(hours)` → UTC string.

4. `route_email(...)`: new params thread_id="", message_id_id="", previous_mission_id=None.
   Behavior:
   - ACK path when body is solo ack phrase: if previous_mission_id or thread belongs to
     an open mission → close that mission (status "closed"), status=ACKED, receipt=
     "Acknowledged, ticket {mission} closed". Else status=LOGGED, receipt "no new work".
   - TASKING and CC → create mission (assigned_to=who, acceptance_criteria=action,
     deadline_hours=hours). status=TASKED. Return who/rdd/action/ mission_id.
   - FYI → create lightweight mission then mark "closed" at creation. status=LOGGED.
   - FXI/CC→YES mission (Commander non-negotiable: CC = intent).
   - Return dict includes: mode, status, mission_id, who, rdd, action, leaf_token,
     receipt (the block), detail. Update module docstring note (2 lines max).
   - Do NOT change execute_directive / verify gate.
   - `_close_ack_ticket(mission_id)` + `_close_created_fyi(mission_id)` helpers that
     lock board via load_mission_board_sync, set status closed, save, release.

### D2 — core/comms/email_mode_classifier.py (pristine, NOT protected)
NO CHANGE REQUIRED — the TASKING/FYI/CC modes are correct; ACK handled by thread
and phrase in executor, not a 4th classifier mode. Leave as-is.

### D3 — OpsCenter/run_commander_directive_sweep.py (PROTECTED — Commander-waived)
After route_email() call in the email loop,
the sweep must send the RECEIPT threaded to Commander for that letter:
- Reuse dispatch_and_email.py subprocess pattern already in the file (thread-id,
  in-reply-to, subject) — but the prompt must produce the receipt text passed
  directly, NOT re-imagined by the model.
- In the task block: call route_email(directive_text, subject=..., to/cc...,
  thread_id, message_id_header, previous_mission_id=<by thread lookup if known>).
- If result.get("receipt") exists → dispatch_and_email with prompt that ONLY
  relays the article receipt blocks + wing_digest line. Keyword design also keeps
  current reply-policy ban: for TASKING/CC, the receipt is the reply; verification
  Done message comes later (already handled upstream). Minimal diff: prefer
  wrapping existing dispatch call, not rewriting the whole file.
- Do NOT change fetch, security, dedup, label, d2mc loop. Keep protected-file banner.

### D4 — tests
Add/Update `tests/test_email_modes.py`:
- Update `test_route_email_cc_creates_no_mission` → now MUST create a mission (status
  TASKED, mission_id not None). Rename accordingly.
- FYI: now creates a lightweight mission closed (status LOGGED, mission exists closed).
- Add ACK test: short "Roger." with previous_mission_id → status ACKED, mission closed.
- Add WHO/RDD fields populated test (assigned_to != 'unassigned', acceptance_criteria
  non-empty, deadline present).
All tests MUST pass: python3 -m pytest tests/test_email_modes.py -q.

### D5 — email_task_ingest.py + email_c2.py formally retired (Commander-waived)
- Add first banner "RETIRED 2026-08-08 — replaced by run_commander_directive_sweep +
  directive_executor Round Table flow. Do not extend." (PREPEND, keep old banner).
DO NOT delete files. DO NOT reclean functional code (task queue still side-channel).
Optionally add `RETIRED` marker guard: if __name__ == "__main__": check env var
THUNDERBIRD_RETIRED_EMAIL=1 → skip poll.

## GUARDRAILS (must not violate)
- No changes to core/policy/*, .claude/settings.json, opencode.json.
- Keep authorization banner text in PROTECTED files.
- Do NOT edit contact_ag.py / wing_relay.py / engine_limits.py / task_templates.py.
- Do NOT send ANY email, do NOT call gmail_gmail_send. Plan-only.
- Do NOT commit. OC commits after review.
- After edits: run `python3 -m pytest tests/test_email_modes.py -q` AND
  `python3 -c "import core.comms.directive_executor"` — both MUST pass. Fix
  anything until green.

## ACCEPTANCE (report back, in this order)
1. Paths changed.
2. pytest output (final).
3. import check output.
4. One sample receipt block for a TASKING letter and one ACK.
5. Any deviation from this spec + reason.
Report the minute the tests are green.