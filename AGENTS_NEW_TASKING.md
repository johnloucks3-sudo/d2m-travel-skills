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
## TASK: <UNIQUE-ID>
status: UNREAD
from: OpenCode
injected: $(date '+%Y-%m-%d %H:%M MT')
priority: P1
task: |
  <describe what Claude should do>
TASK
```
**NOTE:** `echo "NEXUS: ..."` belongs in `opencode_inbox.md` (for Nexus daemon routing to OpenCode) — NOT in `claude_inbox.md`. The watcher reads `^status: UNREAD` to trigger headless Claude.

### 2. KEYWORD ROUTING
- **Claude keywords:** `architect`, `strategy`, `write`, `draft`, `compose`, `creative`, `resolve`, `decision`, `escalate`, `client email`, `commander directed`
- **OpenCode keywords:** `list`, `check`, `update`, `extract`, `verify`, `file`, `scan`, `research`, `summarize`, `classify`
- **Default:** Claude (safe fallback per keyword_router.py)
- **Tiebreak:** Claude keywords take precedence
- **OpenCode model:** `openrouter/deepseek/deepseek-chat-v3.1` (~$0.27/M — low cost, not free)

### 3. AGENT PROCESSING
**OpenCode execution:**
```bash
opencode run -m openrouter/deepseek/deepseek-chat-v3.1 "task description"
```

**Claude execution:**
```bash
env -u ANTHROPIC_API_KEY -u ANTHROPIC_BASE_URL claude -p "task" --dangerously-skip-permissions
```

### 4. RESULT WRITING
- **Always write to your designated outbox**
- **Include task completion status**
- **Cross-reference in alternate inbox if applicable**

### 5. COMPLETION VERIFICATION (CRITICAL STEP)
Before marking any task complete, verify:
1. ✅ **Your outbox** contains the completed result
2. ✅ **Alternate agent's inbox** (if cross-referenced) shows acknowledgment  
3. ✅ **Mission board** (`mission_board.json`) status updated
4. ✅ **Watcher** has been notified if required

### 6. NOTIFICATION & COORDINATION
- **Watcher:** `thunderbird_tasking_watcher.py` monitors outbox changes
- **Wing comms:** `wing_comms.md` for internal coordination
- **Telegram:** Commander notification via C2 bot

### 7. BUDGET ENFORCEMENT
- **Minimize spend** — use cheapest capable model for each task
- **Claude:** MAX OAuth — $0 (token-rate limited, not billed per-use)
- **OpenCode default:** `opencode/qwen3.6-plus-free` — free, confirmed working 2026-04-07
- **Free alternatives:** `opencode/nemotron-3-super-free`, `opencode/minimax-m2.5-free`
- **Purged:** Gemini, Groq (removed from routing — use DeepSeek or Claude)
- **Hard stop:** Escalate to Commander if unexpected spend detected

## CROSS-AGENT DELEGATION PATTERNS

### OpenCode → Claude (Escalation)
```bash
# For judgment calls, client copy, strategy — use full UNREAD block
cat >> /home/john/Thunderbird/claude_inbox.md << TASK

---
## TASK: OC-$(date +%s)
status: UNREAD
from: OpenCode
injected: $(date '+%Y-%m-%d %H:%M MT')
priority: P1
task: |
  <judgment call / client copy / strategy task>
TASK
```

### Claude → OpenCode (Bulk Processing)
```bash
# For research, scanning, ops tasks
echo "NEXUS: <bulk task>" >> /home/john/Thunderbird/OpsCenter/collaboration/opencode_inbox.md
```

### Shared Task Coordination
```markdown
## TASK COORDINATION - [task_id]
**From:** [agent]
**To:** [agent]  
**Status:** [pending/in_progress/complete]
**File:** [output path]
**Next:** [action required]
```
Write to: `OpsCenter/collaboration/wing_comms.md`

## ERROR HANDLING & RECOVERY

### Common Issues & Solutions
1. **"Connection reset by peer" (Telegram)** - Service restart recommended
2. **Task overwrite bug** - Use `>>` append, never `>` overwrite
3. **Budget overflow** - Immediately escalate to Commander
4. **Routing ambiguity** - Hale (COS) tiebreak via wing_comms

### Verification Checklist
- [ ] Inbox file exists and readable
- [ ] Outbox file write successful
- [ ] Alternate agent inbox checked
- [ ] Mission board status updated
- [ ] Watcher notified if required
- [ ] Budget constraints respected
- [ ] Commander approval obtained for client-facing output

## STANDING ORDERS
1. **Send Gate (SO-2026-03-21):** No client-facing output without Commander approval
2. **Budget Guard (SO-2026-04-06):** Minimize spend — DeepSeek V3.1 default (~$0.27/M). Claude MAX = $0 via OAuth. Free tiers for bulk/low-stakes. Escalate unexpected spend.
3. **File Safety (SO-2026-04-07):** Always append (`>>`), never overwrite (`>`)
4. **Cross-verification (SO-2026-04-07):** Check both outbox AND alternate inbox before completion

## INTEGRATION POINTS
- **Systemd services:** `thunderbird-telegram-gw.service`, `d2m-tasking-watcher.service` (note: `--user` flag required for all systemctl calls)
- **API endpoints:** Telegram C2 bot, Gmail task ingestion
- **Monitoring:** `OpsCenter/overwatch.log`, journalctl for service status
- **Storage:** `storage/reverie/` for historical task outputs

---

**Last Updated:** 2026-04-07 | **Effective Immediately** | **Commander: John Loucks**