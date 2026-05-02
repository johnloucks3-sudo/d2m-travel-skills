# BRIEFING BOARDS SYNC GUIDE
**COS Operational Reference for Dual-Domain Coordination**

*Effective: 2026-05-01*

---

## THE SETUP

Two identical briefing boards exist:

| Board | Location | Domain | Read by |
|-------|----------|--------|---------|
| **OpenCode Board** | `/home/john/Thunderbird/OpsCenter/collaboration/opencode_briefing_board.md` | OpenCode (Gemini) | OpenCode reads on every dispatch |
| **Claude Board** | `/home/john/Thunderbird/OpsCenter/collaboration/claude_briefing_board.md` | Claude Code (Haiku) | Claude Code reads on startup |

**COS (Hale) runs in OpenCode domain and maintains both boards.**

---

## WHEN TO POST A DECISION

### Category A: Enterprise-Wide (Post to BOTH boards)

**Decision affects:** Both Claude Code AND OpenCode (most decisions)

**Example:**
- YSB protocol change
- Budget/token limit update
- Priority shift affecting both domains
- New tool deployment used by both
- Client change affecting client-facing staff in both domains
- Owner/COS directive

**Process:**
1. Decide in Owner/COS meeting
2. Write decision in YSB format
3. Post IDENTICAL text to opencode_briefing_board.md + claude_briefing_board.md
4. Both domains read → both post ACKs
5. COS confirms both ACKs → decision is LIVE

**Timeline:** Post within 2 hours of decision. Both ACKs typically arrive within 1-2 hours of boards being updated.

### Category B: OpenCode-Only (Post to OpenCode board only)

**Decision affects:** OpenCode only (Claude Code doesn't need to know)

**Example:**
- DeepSeek fallback configuration
- Gemini-specific cost optimization
- OpenCode token limits (separate from Claude)
- Internal OpenCode workflow change

**Process:**
1. Post to opencode_briefing_board.md only
2. OpenCode reads → posts ACK
3. Claude Code doesn't need to read (no cross-domain impact)

### Category C: Claude-Only (Post to Claude board only)

**Decision affects:** Claude Code only (OpenCode doesn't need to know)

**Example:**
- Sonnet escalation triggers
- Claude-specific voice or template updates
- Client-specific Claude assignments
- Claude token limits (separate from OpenCode)

**Process:**
1. Post to claude_briefing_board.md only
2. Claude Code reads → posts ACK
3. OpenCode doesn't need to read (no cross-domain impact)

---

## DECISION POSTING TEMPLATE

### For Enterprise-Wide Decisions (post to BOTH boards)

Copy-paste this to BOTH boards, fill in details:

```markdown
## [DECISION-###] [TITLE]

**Date:** YYYY-MM-DD  
**Owner:** John Loucks [or "COS Hale" if delegated]  
**Urgency:** HIGH / MEDIUM / LOW  
**Effective:** Immediately / [Date]  

**Decision:** [What is being decided? 2-3 sentences.]

**Why:** [Why does this matter? What problem does it solve?]

**Details:** [Specific requirements, changes, timelines]

**File reference:** [If applicable, link to full documentation]

**Applies to:** [Both domains / OpenCode only / Claude only]

**Domain A (OpenCode) ACK:** [ ] Pending  
**Domain A ACK timestamp:** —

**Domain B (Claude Code) ACK:** [ ] Pending  
**Domain B ACK timestamp:** —

**Status:** [PENDING both ACKs / LIVE after both ACKs received]
```

### For Domain-Specific Decisions (post to one board only)

Copy-paste to the appropriate board only:

```markdown
## [DECISION-###] [TITLE]

**Date:** YYYY-MM-DD  
**Owner:** John Loucks  
**Urgency:** HIGH / MEDIUM / LOW  
**Effective:** Immediately / [Date]  

**Decision:** [What is being decided?]

**Applies to:** [OpenCode only / Claude Code only]

**ACK:** [ ] Pending  
**ACK timestamp:** —
```

---

## COS CHECKLIST FOR EVERY DECISION

Before posting, ask:

- [ ] Is this an enterprise-wide decision OR domain-specific?
- [ ] If enterprise-wide: Will I post to BOTH boards with identical content?
- [ ] Does the decision have a file reference (documentation, code, protocol)?
- [ ] Is the urgency level clear (HIGH/MEDIUM/LOW)?
- [ ] Is the effective date/time specified?
- [ ] Is the impact on each domain clearly stated?
- [ ] Have I left space for ACK timestamps?
- [ ] Will I check back for ACKs within 2-3 hours?

---

## WORKFLOW: POSTING TO BOTH BOARDS

**Step 1: Compose the decision**
```
YSB format (or clear executive summary)
Includes: Background, decision, impact, effective date, file reference
```

**Step 2: Post to OpenCode board**
```
Edit /home/john/Thunderbird/OpsCenter/collaboration/opencode_briefing_board.md
Add decision section with ACK placeholders
```

**Step 3: Post to Claude board**
```
Edit /home/john/Thunderbird/OpsCenter/collaboration/claude_briefing_board.md
Add IDENTICAL decision section with ACK placeholders
```

**Step 4: Alert both domains**
```
OpenCode: Reads briefing board automatically on next dispatch (within minutes)
Claude Code: Reads on next startup (within hour typically)
```

**Step 5: Monitor ACKs**
```
Check both boards for ACK timestamps
OpenCode typically ACKs within 15-30 min
Claude Code typically ACKs within 1 hour
```

**Step 6: Confirm decision is LIVE**
```
Both boards show ACK timestamps → Decision is now active across both domains
Post update to decision: "Status: LIVE — Both domains acknowledged [timestamp]"
```

---

## SYNC GATE: THE RULE

**RULE:** Enterprise-wide decisions are NOT live until BOTH boards show ACKs.

**Why:** Ensures both Claude Code and OpenCode are operating on same information.

**Exception:** If one domain hasn't ACK'd within 4 hours, Owner/COS can escalate to activate decision anyway (with note: "Activated pending [Domain] ACK").

---

## EXAMPLE: YSB PROTOCOL DEPLOYMENT

**Timeline:**

| Time | Action | Board |
|------|--------|-------|
| 14:00 | COS writes YSB decision | Draft |
| 14:05 | COS posts to OpenCode board | opencode_briefing_board.md |
| 14:05 | COS posts to Claude board | claude_briefing_board.md |
| 14:07 | OpenCode reads briefing board (auto-check) | ✓ |
| 14:12 | OpenCode posts ACK | opencode_briefing_board.md: "ACK 14:12" |
| 14:30 | Claude Code starts session, reads briefing board | ✓ |
| 14:32 | Claude Code posts ACK | claude_briefing_board.md: "ACK 14:32" |
| 14:35 | COS confirms both ACKs present → marks LIVE | Both boards: "Status: LIVE" |
| 14:36 | YSB protocol now active across both domains | ✅ |

---

## RAPID-FIRE DECISIONS

**For low-urgency decisions that don't need immediate sync:**

You can post to one board, let that domain ACK, then post to other board next day. Just mark them clearly as "staged" decisions.

Example:
```markdown
**Status:** [STAGED] Posted to OpenCode board 2026-05-01. Will post to Claude board tomorrow.
```

---

## CONFLICT RESOLUTION

**If one domain flags a conflict** (e.g., Claude Code says "This conflicts with OpenCode implementation"):

1. OpenCode domain has priority on technical implementation details
2. Claude Code domain has priority on client-facing language/voice
3. COS arbitrates if unclear
4. Owner makes final call if COS can't resolve

**Process:**
```
Claude ACK: "Read — Conflict with OpenCode's X implementation"
→ COS investigates both implementations
→ COS posts clarification to BOTH boards
→ Domains re-ACK with updated understanding
```

---

## MONITORING & HEALTH

**COS weekly checklist:**
- [ ] Both boards updated with latest decisions?
- [ ] All decisions have ACK timestamps?
- [ ] Any decisions stuck without ACKs for >4 hours?
- [ ] Any flagged conflicts unresolved?
- [ ] Both domains operating on same enterprise-wide decisions?

**Red flags:**
- Decision on board for 4+ hours without ACK = escalate to Owner
- One domain flagging repeated conflicts = system breakdown, investigate root cause
- Decisions drifting between boards (different content) = COS error, realign

---

## TOOLS TO MAINTAIN BOARDS

**To add a decision:** Edit the markdown file, add new decision section, save

**To confirm ACKs:** Read both boards, verify ACK timestamps in both

**To track what's outstanding:** Look for `[ ] Pending` in ACK lines (unfilled checkbox = not ACK'd yet)

**To mark LIVE:** Update status section to "Status: LIVE — OpenCode ACK [time], Claude Code ACK [time]"

---

## REFERENCE

- **Owner Memo (organizational structure):** `/home/john/Thunderbird/OpsCenter/OWNER_MEMO_TWO_DOMAINS_20260501.md`
- **YSB Protocol (briefing format):** `/home/john/Thunderbird/OpsCenter/YSB_BRIEFING_PROTOCOL.md`
- **Both boards:** Linked from this guide

---

*COS Operational Reference — Maintain both boards to keep domains synchronized.*  
*No copy-paste between sessions. Boards are live, persistent, and auto-read by both domains.*
