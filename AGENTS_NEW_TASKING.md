# Thunderbird Tasking Process & Cross-Agent Coordination
<!-- REVISED: 2026-04-07 by Hale — 5 errors corrected (model name, task injection format, default routing, budget section, service name) -->

## CANONICAL INBOX/OUTBOX LOCATIONS

### Claude (Sonnet 4.6, MAX OAuth)
- **Inbox:** `/home/john/Thunderbird/claude_inbox.md`
- **Outbox:** `/home/john/Thunderbird/OpsCenter/collaboration/claude_outbox.md`
- **Purpose:** Client copy, strategy, architecture, judgment calls

### OpenCode (deepseek-chat-v3.1, ~$0.27/M tokens)
- **Inbox:** `/home/john/Thunderbird/OpsCenter/collaboration/opencode_inbox.md`
- **Outbox:** `/home/john/Thunderbird/OpsCenter/collaboration/opencode_outbox.md`
- **Purpose:** Bulk ops, scanning, research, summarization, file operations

### Nexus Daemon (Task Router)
- **Routing logic:** `OpsCenter/keyword_router.py`
- **Mission tracking:** `OpsCenter/mission_board.json`
- **Coordination:** `OpsCenter/collaboration/wing_comms.md`

## TASKING PROTOCOL - 7-STEP FLOW

### 1. TASK INJECTION
```bash
# Standard format — append a full task block. Watcher triggers on ^status: UNREAD
cat >> /home/john/Thunderbird/claude_inbox.md << TASK

---
# Wing Autonomy - Self-Healing Protocol (2026-05-01)
Effective immediately, all infrastructure must implement the **Self-Healing Loop**:
1. Diagnose error (Auth/Rate-Limit/Module/Network).
2. Apply programmatic fix (rotation/backoff/flush).
3. Retry exactly ONE (1) time.
4. If failed: Transition to `ESCALATED` state. 

**NO BLIND RETRIES OR DEATH SPIRALS.**

**Last Updated:** 2026-05-01 | **Effective Immediately** | **Commander: John Loucks**
