# POINT PAPER: HALE VIRTUAL MEETROOM CAPABILITY

**BLUF:** Repurpose the existing CLI dispatcher pipeline to sequence the 4 core HALE engines synchronously, saving to JSONL, and driving a local CLI-based terminal visualizer to avoid new databases or complex UIs.

## 1. IDEAS (Concept & Mechanics)
- **Naming:** `HALE_MEETROOM` or `WAR_ROOM_LIVE`.
- **Layout:** A clean CLI terminal interface using Python `rich`. Shows engine avatars/tags (🔴 [CC], 🟢 [AG], 🔵 [OC], 🟡 [Grok]), speaking sequentially.
- **Sequencing Mechanics:** Not true simultaneous pub/sub. Synchronous turn-based polling (Orchestrator script pings each engine in a defined order).
- **Visual Play-by-Play:** Once all answers are collected/JSON-logged in step 3, Step 4's "play-in" is just a script printing the logged JSONL lines to stdout with artificial `time.sleep()` delays for human readability.

## 2. AVOID-THE-BUILD (Cheapest Path)
**Current Ground Truth (Ran `find` for `meeting`, `a2a`, `blackboard`; `grep_search` on `run_staff_meeting` and `a2a_broadcast`):**
- `run_staff_meeting` / `crew_staff_meeting` (`core/ai_infra/thunderbird_personas.py`): Currently sequences the 11 fictional D2M personas, not the 4 core engines.
- `a2a_broadcast` (`core/ai_infra/thunderbird_a2a.py`): Fire-and-forget sync function for D2M personas.
- `Blackboard` (`OpsCenter/collaboration/blackboard.md`): Used for async state sharing, not sequential play-by-play.
- `Telegram C2`: Chronological, but spamming the Commander's phone for engine-to-engine banter is a violation of C2 protocol.

**Recommendation:** Do NOT build a new system. 
- Use a simple Python orchestrator script (`run_meetroom.py`) that loops through the 4 engines via their existing CLI dispatchers (`contact_ag.py`, `dispatch_oc`, etc.). 
- Save the outputs to a single `meetroom_transcript.jsonl`. 
- Build a 50-line playback script (`play_meetroom.py`) that reads the JSONL and prints it to the terminal with colors and a typing delay.

## 3. CONCERNS (Risks)
- **Context Window & Cost:** Passing the full growing transcript to every engine iteratively will exponentially increase token burn. Hits the $10/mo OpenRouter hard cap quickly.
- **Overlap & Single-Writer:** If run asynchronously, concurrent writes will trigger the `blackboard_conflict_resolver.py` (which is active per the `find` output). Must run *synchronously* (turn-based).
- **Session Limits:** MAX buckets (CC) and OpenRouter (OC) have separate limits. Cross-engine validation rules (SO 2026-07-31) apply.

## 4. BEST-PRACTICE BRAINSTORM/PATH (Execution)
- **Artifacts:** Generate `<topic>_meetroom_plan.md` before execution.
- **Gates:** Apply the Silver Gate (`is_checkable()`) before finalizing the To-Do list.
- **De-dup:** Appoint **ONE** engine (e.g., OC / Jet, as it is the $0 lane) as the Orchestrator to generate the To-Do list from the collected transcript.
- **Path:** 
  1. `run_meetroom.py --topic "X"` calls CC, AG, OC, Grok sequentially.
  2. Saves outputs to `OpsCenter/meetroom/transcript_X.jsonl`.
  3. Orchestrator reads JSONL, summarizes into `todo_X.md`.
  4. Commander runs `play_meetroom.py transcript_X.jsonl` to watch the simulated meeting in the terminal.
