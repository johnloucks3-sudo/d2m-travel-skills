# ROUND TABLE — Email C2 / Tasking Redesign
**OC + AG + CC · 2026-08-08 · Commander-directed**
**Chair: OC (Hale, OpenCode) · Seats: AG (Gemini), CC (Claude)**

## PROBLEM (as the Commander stated it)
"Improve this hodgepodge of email scanning and tasking/response code. A response
AND a task should flow from EVERY email I send — even an ack. When I CC someone,
there should be action, as interpreted by the email, and confirmation sent back
to me. Think in human terms: the COS/Hale is my Exec. I want to know what my
Exec is going to do with my letter/instructions — to WHOM a task is given, what
their RDD is, what actions were given, and what they are supposed to do."

## COMMANDER'S OPERATING SPEC (4 non-negotiables)
1. **Closed loop, every message.** Every email from Commander → a confirmation
   reply. No silent readings, no dropped acks. MOUSE.
2. **Tasking always.** A response AND a task flow from every email.
   `ack` still logs/acks the task. `tasking/CC` → an action owned by a seat.
3. **CC = action.** A CC email is still Commander intent; the receiving seat
   interprets it, acts, and confirms what it did.
4. **Staff-grade feedback.** Commander must see — for each task: WHO owns it
   (seat: COS/Dani/Sterling/Harlan/OC/CC/AG), RDD, action, deliverable.

## CURRENT-STATE FINDINGS (verified, 2026-08-08)
- **Multiple competing watchers on the same inbox, no shared dedup:**
  - `run_commander_directive_sweep.py` (2-min) → classifies TASKING/FYI/CC →
    mission board + headless reply, case-biased.
  - `email_task_ingest.py` (5-min) → separate JSON queue + opencode_inbox.md,
    sends "Task accepted" receipts, does NOT execute. Its watcher
    (thunderbird_tasking_watcher) is RETIRED — that path is orphaned.
  - `email_c2.py` `[WING]` engine → DISABLED.
  - `dispatch_and_email.py` → threaded reply sender.
  - `core/comms/directive_executor.py` + `core/comms/email_mode_classifier.py`
    → the classifier + verify-gated execution (a reply = verified work).
- **Deliverable:** acks/fyi/cc do not spawn tasks; CC logged no work;
  "" reply gate "only reply when verified" loses the closed-loop promise.
- **Job** isn't tasking efficiency — it's turn this into a human Exec model.

## ROUND TABLE QUESTIONS (each seat answers independently)
Q1. What is the SINGLE canonical email C2 flow? (one inbox, one classifier,
    one task store, one reply path) — name the survivors and the retired.
Q2. How do we guarantee "a task + a response" for EVERY email including acks
    and CCPU? Give the per-mode disposition matrix.
Q3. How do we expose WHO/RDD/ACTION/DELIVERABLE back to Commander for every
    task — the human-Exec feedback loop?
Q4. Where is AG and CC fit in execution (which tasks route to which seat, and
    via which native channel — AG=contact_ag, CC=/ask) without overloading
    either lane?
Q5. What owns verification of "done", and how do acks/CCs get their task
    closed without theater?

## OUTPUT FORMAT (all seats)
Return a point-paper: **PURPOSE · BACKGROUND · FINDINGS · DESIGN · OPINION ·
RECOMMENDATION**. Keep it tight. This is the design brief the Commander
approves prior to any build.