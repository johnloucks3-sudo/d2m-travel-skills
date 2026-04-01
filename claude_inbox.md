---
task_id: "WATCHER_FIX_1775014920363"
priority: "HIGH"
model: "claude-3-7-sonnet-20250219"
context_files:
  - "/home/john/Thunderbird/OpsCenter/claude_inbox_watcher.py"
  - "/home/john/Thunderbird/OpsCenter/task_processor.py"
  - "/home/john/Thunderbird/OpsCenter/overwatch.log"
output_destination: "/home/john/Thunderbird/OpsCenter/collaboration/watcher_fix_proposal.md"
---

# TASK: FIX THE WATCHER DAEMON (A7 & COMMANDER DIRECTIVE)

You are being called upon to assist Goose.
The `thunderbird-inbox-watcher.service` (running `claude_inbox_watcher.py`) frequently fails silently or hangs. It uses `watchdog` on `claude_inbox.md`, but recently had a 480s timeout and just stopped processing entirely until manually restarted. 

**Directives:**
1. Analyze `claude_inbox_watcher.py`.
2. Diagnose why the file system `on_modified` events stop triggering or get stuck after a subprocess timeout.
3. Provide the exact Python code to patch the watcher so it self-heals from `mcp2cli` timeouts and guarantees it never drops a queued task in `claude_inbox.md`.
4. Output your patched code and explanation to `watcher_fix_proposal.md`.

// EOF
