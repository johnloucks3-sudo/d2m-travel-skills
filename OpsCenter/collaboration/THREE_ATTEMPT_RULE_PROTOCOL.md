# THREE-ATTEMPT RULE PROTOCOL

## Effective: April 8, 2026
## Commander Directive: John Loucks

### RULE DEFINITION
If any task cannot be completed after THREE legitimate attempts using proper system methods, automatically task Claude Code for assistance.

### ATTEMPT CRITERIA
Each attempt must:
1. Use correct system tools and protocols
2. Follow documented procedures  
3. Include proper error handling
4. Document the attempt and results
5. Wait appropriate time between attempts if needed

### TASKING PROCEDURE
When three attempts fail:

1. **Create Task in claude_inbox.md**
   ```
   ## TASK: [TASK-ID]
   status: UNREAD
   from: OpenCode
   injected: [timestamp]
   priority: P0
   task: |
     [Detailed description of failed task]
     [Three attempts made with results]
     [Specific assistance needed]
   ```

2. **Set Monitoring Timer**
   - Check status every 5 minutes
   - Alert if task remains UNREAD > 15 minutes
   - Escalate if no response > 30 minutes

3. **Document Resolution**
   - Once solved, document the solution
   - Create skill if applicable
   - Update protocols if needed

### GMAIL DRAFT/INBOX PROTOCOL (EXAMPLE)
Current status: Tasked to Claude Haiku for proper protocol
- Task ID: CLAUDE-HAIKU-GMAIL-PROTOCOL-001
- Priority: P0
- Status: UNREAD

### MONITORING SETUP
Task monitoring activated for:
- ✅ Gmail protocol task created
- ⏳ Waiting for Claude response
- ⏰ Next check: 5 minutes

---
*Protocol established per Commander directive - No shortcuts, only proper system methods*
