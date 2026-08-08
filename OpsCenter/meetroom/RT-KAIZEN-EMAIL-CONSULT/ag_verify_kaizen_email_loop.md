# AG Cross-Engine Integrity Check: `core/email/kaizen_email_loop.py`

**Inspector:** HALE-AG (Antigravity Engine / Gemini 3.6 Flash)  
**Date:** 2026-08-08  
**Scope:** Independent verification of `core/email/kaizen_email_loop.py` (KAIZEN email loop).  
**Target Ground Truth Dependencies:** `core/relay/task_templates.py`, `core/email/thunderbird_gmail.py`, `core/email/email_conversation_agent.py`, `scripts/kaizen_runner.py`.

---

## 1. Executive Summary & BLUF

- **Verdict: PASS (with minor operational observations)**
- **Auto-Send Isolation:** Confirmed strictly gated. `gmail_send_as_persona()` is reachable **only** when `t.get("verified_reply") is True`. `verified_reply` is only written by `pass2_inbound()` upon an exact sender-match (`msg["from_addr"] == parent["submitted_email"]`).
- **Authority / Gate Escalation:** Confirmed immutable. `pass2_inbound()` constructs follow-up tickets using `parent.get("seat", "CC")`, `parent.get("gates") or []`, and `parent.get("verify_step", "")`. Inbound message content cannot inject elevated gates or modify the target seat.
- **Dry-Run Behavior:** Verified clean. Default invocation (`python3 core/email/kaizen_email_loop.py`) and `--dry-run` execute Pass 1 read-only and skip Pass 2 completely. Zero network API calls, zero state file writes, and zero ticket file updates occur.
- **Visual Progress Bar:** `[████████████████████] 100% Verified`

---

## 2. Point-by-Point Ground Truth Verification

### Question 1: Auto-Send Reachability & Sender Verification
* **Requirement:** Confirm `gmail_send_as_persona` is never called for an address unless proven via an inbound sender-matched reply (`verified_reply == True`).
* **Code Trace:**
  - In `pass1_outbound()` (lines 261–288):
    ```python
    verified = t.get("verified_reply") is True
    ...
    if verified:
        res = gmail_send_as_persona(...)
    else:
        res = gmail_create_draft_sync(...)
    ```
  - `verified_reply` provenance: Grepped repository-wide. Found only in `kaizen_email_loop.py:400` within `pass2_inbound()`.
  - In `pass2_inbound()` (lines 353–376):
    1. Extracts `parent_id` from `[KAI-(kzn-...)]` subject regex.
    2. Loads `parent` ticket file `OpsCenter/tickets/<parent_id>.json`.
    3. Evaluates `expected = parent.get("submitted_email").strip().lower()`.
    4. Evaluates `actual = msg.get("from_addr").strip().lower()` (where `from_addr` is parsed and lowercased by `email_conversation_agent.fetch_unread()`).
    5. If `not expected or actual != expected`, it triggers `_notify_unexpected_sender()`, marks the Gmail message as read, records `seen`, and **aborts** without creating a ticket.
    6. Only upon exact match does it write `verified_reply: True` into the follow-up ticket dict.
* **Finding:** No ticket originating outside `pass2_inbound` (e.g. `kaizen_intake_server.py`, `build_cc_task()`) carries `verified_reply=True`. Auto-send cannot trigger on initial submissions.

### Question 2: Authority & Gate Escalation via Inbound Email
* **Requirement:** Trace follow-up ticket construction in `pass2_inbound()` to determine if gates or seat can be altered/escalated by an email reply.
* **Code Trace (lines 379–393):**
  ```python
  follow = build_cc_task(
      f"[FOLLOW-UP to {parent_id}] {stripped}\n\n[Context: {(parent.get('spec') or '')[:300]}]",
      seat=parent.get("seat", "CC"),
      verify_step=parent.get("verify_step", ""),
      gates=parent.get("gates") or [],
      require_checkable=True,
  )
  ```
  - Inbound email content (`stripped`) is placed **exclusively** into the prompt string `task`.
  - `seat`, `verify_step`, and `gates` parameters are strictly drawn from the parent ticket on disk (`parent.get(...)`).
  - `require_checkable=True` is enforced, preventing vague verification escapes.
* **Finding:** An inbound email sender has zero control over `seat`, `gates`, or `verify_step`. Authority cannot escalate.

### Question 3: Dry-Run Network & File Safety
* **Requirement:** Verify dry-run mode (default / `--dry-run`) executes zero API calls and zero file writes.
* **Empirical Test:**
  - Ran: `python3 core/email/kaizen_email_loop.py --dry-run`
  - Output:
    ```
    [DRY-RUN] kaizen_email_loop — pass 1 OUTBOUND
    [DRY-RUN] pass 1 complete: 0 ticket(s) acted on
    [DRY-RUN] kaizen_email_loop — pass 2 INBOUND
    [DRY-RUN] Pass 2 INBOUND skipped — fetch_unread() is a Gmail network call; dry-run makes zero API calls
    [DRY-RUN] pass 2 complete: 0 follow-up ticket(s) created
    ```
  - Also tested default execution (`python3 core/email/kaizen_email_loop.py` without args) -> identical safe dry-run output.
* **Code Trace:**
  - `pass1_outbound()`: If `not live:`, prints `[DRY-RUN] ... WOULD AUTO-SEND/DRAFT` and `continue`s before calling Gmail API or `write_ticket()`.
  - `pass2_inbound()`: If `not live:`, logs skip message and immediately returns `0`.
* **Finding:** Completely safe and side-effect free.

---

## 3. Observations & Findings

All findings reported per USAF completeness doctrine:

1. **[LOW - Correctness/State Preservation] Set ordering when slicing processed IDs in `_save_processed` (Line 182)**
   - *Code:* `bounded = list(ids)[-PROCESSED_BOUND:]`
   - *Detail:* `ids` is a Python `set`. Converting an unordered `set` to a `list` does not guarantee chronological insertion order. If `len(ids) > 1000`, slicing `[-1000:]` may discard newer IDs rather than oldest IDs.
   - *Impact:* Extremely low in practice (1000 IDs is large for KAIZEN thread volume, and Gmail queries are filtered by `is:unread in:inbox`). If strict FIFO trimming is desired in the future, maintaining a list or deque in insertion order would be ideal.

2. **[INFO - Robustness] Parent verify_step Checkability Gate on Follow-Up (Line 389)**
   - *Code:* `build_cc_task(..., require_checkable=True)`
   - *Detail:* If a parent ticket was created with `require_checkable=False` (e.g. from the Commander intake form) and has an uncheckable `verify_step`, `build_cc_task` will raise `ValueError` on follow-up. Line 389 catches this exception, logs `follow-up build rejected (<e>) — mark_read, skipped`, and skips ticket creation.
   - *Impact:* Safe fail-closed behavior, though it means a follow-up to an uncheckable ticket will be skipped rather than downgraded.

3. **[INFO - Guardrail String Match] Broad 32+ Character Hex/Base64 Pattern (Line 95)**
   - *Code:* `re.compile(r"[a-zA-Z0-9]{32,}", re.IGNORECASE)`
   - *Detail:* The guardrail matches any contiguous alphanumeric token of 32+ chars. Common long strings (UUIDs without hyphens, hashes, long URLs/tokens) in a ticket result will trigger `blocked_guardrail`.
   - *Impact:* Deliberately blunt per spec ("do not try to be clever about it"); safely fails closed.

---

## 4. Final Verdict

**AG-VERIFY DONE: PASS** — `core/email/kaizen_email_loop.py` enforces strict auto-send isolation via `verified_reply`, prevents inbound gate/seat escalation, executes zero network/disk side-effects in dry-run, and adheres to all repository safety standards.
