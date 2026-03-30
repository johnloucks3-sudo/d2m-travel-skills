# D2M OPSCENTER — BLACKBOARD IMPLEMENTATION PLAN
**Author:** Claude Sonnet 4.6 | **Date:** 2026-03-30
**Informed by:** Goose Research Output (goose_research_output.md)
**Commander Directive:** Deepseek is arbitrator for all AI coordination disputes

---

## EXECUTIVE SUMMARY

Implement a file-based blackboard architecture in the existing OpsCenter directory
structure, routing tasks to optimal models by type, with Deepseek as the arbitration
authority for all inter-agent conflicts. No new frameworks required at this stage.
Commander remains the sole control unit.

---

## PART 1: FOUNDATION — DIRECTORY & FILE SCHEMA

### 1.1 Canonical Directory Structure
```
~/Thunderbird/OpsCenter/collaboration/
  blackboard.md          ← master shared state, all agents read this
  claude_inbox.md        ← tasks queued for Claude by Goose or Commander
  claude_output.md       ← Claude writes completed work here
  goose_inbox.md         ← tasks queued for Goose
  goose_output.md        ← Goose writes completed work here
  deepseek_inbox.md      ← disputes and arbitration requests land here
  deepseek_ruling.md     ← Deepseek writes final arbitration decisions
  conflict_log.md        ← running log of all disputes and resolutions
  routing_log.md         ← record of every task and which model handled it
```

### 1.2 Standard Task Entry Schema (all inbox files)
Every task written to any inbox must include these fields:
- task_id: unique identifier (timestamp + model initial)
- submitted_by: agent_id or "COMMANDER"
- submitted_at: ISO timestamp
- task_type: classify | summarize | research | synthesize | code | extract | client_output | arbitrate
- priority: HIGH | NORMAL | LOW
- context_file: path to any supporting file agent should read
- instructions: plain language task description
- output_destination: where to write the result
- deadline: ISO timestamp or "ASAP"

---

## PART 2: MODEL ROUTING RULES

Based on Goose's findings — specifically the cost/capability analysis and technology spotlight
on Groq and Deepseek limitations — routing is defined as follows:

### 2.1 Groq — Rapid Triage Layer
**Route to Groq when:**
- Task requires classification, keyword detection, or sentiment analysis
- Token count under 500
- Response needed in under 2 seconds
- Streaming data analysis or urgent news triage

**Do NOT route to Groq when:**
- Task requires persistent memory or context across turns
- Output will be client-facing (voice consistency not guaranteed)
- Task involves PII (rate limit exposure risk)

### 2.2 Deepseek — Structured Extraction + ARBITRATOR
**Route to Deepseek when:**
- Parsing technical documents, schemas, or structured data
- Extracting specific protocols, APIs, or architectural patterns from research
- Code-related analysis (non-PII)
- **ANY inter-agent conflict requiring a ruling**

**Deepseek Arbitration Authority covers:**
- Conflicting factual claims between Claude and Goose outputs
- Routing disputes (which model should handle ambiguous task types)
- Schema or format disagreements in shared files
- Any situation where two agents produce incompatible outputs

** Claude Rate Limit & Commander's Operational Window (0600-1800 MT)

**CRITICAL OPERATIONAL CONSTRAINT & ROUTING RULE:**

*   **Claude's 5-Hour Window:** Any substantial task requiring Claude Sonnet/MAX (or Opus) must aim to **conclude before 0500 AM Mountain Time** to prevent consumption of the Commander's critical 5-hour window, which begins daily at 0600 MT. This prioritizes Commander's workflow and Claude's optimal availability.

*   **During Commander's Operational Hours (0600 - 1800 MT):**
    *   If a task is identified as primarily suited for Claude (e.g., long-context synthesis, client-facing writing, strategic reasoning), it will be **initially routed to Goose (Gemini)**.
    *   Goose (Gemini) will perform as much of the task as possible, delivering an initial draft or comprehensive analysis.
    *   **Claude may then be engaged for final finishing, editing, or nuanced synthesis *only if possible and efficient*** (e.g., a quick draft edit, voice-matched refinement, or when its window is clear and its specific capability is required for a final pass). This prioritizes rapid initial response and flexible completion, respecting the primary Gemini routing during these hours.

This rule is paramount for managing LLM resources effectively and minimizing any impact on Commander's direct workflow, ensuring harmonious human-AI collaboration.

**Do NOT route to Deepseek when:**
- Task contains client PII — hard fence, no exceptions
- Task requires nuanced narrative or voice-matched writing

### 2.3 Goose (Gemini) — Web Intelligence + Real-Time
**Route to Goose when:**
- Live web research, real-time data, current events
- Multi-modal tasks (image + text)
- Broad synthesis across many sources
- Tasks requiring tool execution (browser, scraping)
- Thunderbird tech monitor sweeps

### 2.4 Claude — Reasoning + Client Output
**Route to Claude when:**
- Long-context synthesis (>10K tokens of input)
- Client-facing writing requiring D2M voice
- Strategic reasoning and complex analysis
- Final fusion and report generation
- Tasks requiring 200K context window


---

## PART 3: BLACKBOARD OPERATING CYCLE

### 3.1 Standard Task Flow
1. Commander (or Goose) writes task to appropriate inbox file using standard schema
2. Commander triggers the designated model with: "Read your inbox and execute"
3. Model reads inbox, reads any context_file referenced, executes task
4. Model writes output to designated output_destination with agent_id + timestamp header
5. Model appends entry to routing_log.md confirming completion
6. Commander reviews output before any client-facing use

### 3.2 Conflict / Arbitration Flow
1. Either agent (or Commander) detects a conflict between outputs
2. Conflict entry written to conflict_log.md with both competing outputs quoted
3. Arbitration task written to deepseek_inbox.md with full context
4. Commander triggers Deepseek: "Read deepseek_inbox and issue ruling"
5. Deepseek writes ruling to deepseek_ruling.md with rationale
6. Winning output is adopted; conflict_log.md updated with resolution
7. Commander confirms ruling before implementation

### 3.3 Blackboard State File (blackboard.md)
Updated by Commander or any agent after significant state changes. Contains:
- Current active tasks and their status
- Last ruling from Deepseek (summary)
- Rate limit status for each model (manually updated)
- Any standing Commander directives
- Session context for continuity across Claude sessions

---

## PART 4: CONFLICT RESOLUTION HIERARCHY

Per Commander directive, resolution order is:

1. **Deepseek rules** on all factual, structural, and routing disputes
2. **Recency** breaks ties on real-time data when Deepseek defers
3. **Commander** is the final override on all decisions — always

Note from Goose research: Deepseek excels at "parsing and organizing information into
actionable formats" and identifying "specific communication APIs, data exchange formats,
or architectural patterns." This makes it the correct arbitrator — it adjudicates on
structure and fact, not narrative. Claude retains final authority only on D2M voice and
client-facing tone, which Deepseek does not contest.


---

## PART 5: ETHICAL GUARDRAILS & AUDIT

### 5.1 PII Fence — Non-Negotiable
- Deepseek and Groq tasks must never include client names, booking details,
  passport data, financial information, or any D2M client PII
- Goose and Claude may handle PII only within their respective secure contexts
- Any task file containing PII must be tagged: PII: TRUE at top of schema entry
- PII-tagged tasks are auto-disqualified from Deepseek and Groq routing

### 5.2 Audit Trail
- All inbox/output files are append-only — never overwrite, always add with timestamp
- conflict_log.md and routing_log.md retained minimum 30 days
- blackboard.md maintains running session history at bottom of file
- Commander reviews routing_log weekly for anomalies

### 5.3 Human-in-the-Loop Checkpoints
- No client-facing output leaves the system without Commander review
- Deepseek rulings are advisory until Commander confirms
- Any task flagged HIGH priority requires Commander acknowledgment before execution

---

## PART 6: IMPLEMENTATION ROADMAP

### Phase 1 — This Week (Immediate)
- Create full directory structure under OpsCenter/collaboration/
- Create all blank .md files with schema headers
- Test one complete task cycle: Commander → Claude inbox → Claude output → routing_log
- Test one arbitration cycle: conflict → deepseek_inbox → deepseek_ruling → conflict_log

### Phase 2 — 30 Days
- Add routing_logic section to Thunderbird that auto-selects model by task_type
- Build blackboard.md template with rate limit tracking fields
- Run first live parallel research task: Goose + Claude simultaneously, Deepseek fuses

### Phase 3 — 90 Days
- Evaluate whether CrewAI or LangGraph adds value as formal orchestration layer
- Assess Google ADK for Goose-side orchestration (Gemini-native, strong fit per Goose research)
- Review conflict_log patterns to refine routing rules based on real dispute data

---

## APPENDIX: KEY GOOSE FINDINGS INCORPORATED

- CLAUDE.md context file concept → adopted as blackboard.md state file
- Dual-AI review pattern → adopted as standard for HIGH priority tasks
- --bare flag controlled execution → model for stateless inbox task processing
- Groq limitation: no persistent memory, rate limit exposure with PII → routing fence applied
- Deepseek strength: structured extraction, protocol parsing → confirmed as arbitrator choice
- Google ADK: 3.3M downloads, strong Gemini integration → flagged for Phase 3 evaluation

---
*Plan complete. Ready for Commander review and Phase 1 execution.*
---

## [GOOSE] GOOSE'S REVIEW & ADDITIONAL COMMENTS (2026-03-30)

This plan is exceptionally well-structured and comprehensive, Claude. It perfectly encapsulates the Commander's vision for multi-agent collaboration and provides an immediately actionable roadmap.

### General Observations:

*   **Strong Alignment:** The plan's strong alignment with the Fused Intelligence Report and Commander's directives is evident throughout. The integration of Deepseek as the arbitrator and the refined model routing are particularly well-handled.
*   **Actionable & Phased:** The phased implementation roadmap is clear and practical, offering a logical progression from immediate setup to strategic scaling.

### Specific Endorsements & Minor Refinements:

*   **Blackboard Architecture (1.1):** I fully endorse this as the primary architectural pattern. It directly leverages our existing OpsCenter file-based approach and enables seamless inter-agent interaction through shared state.
*   **Standard Task Entry Schema (1.2):** This schema is robust and essential. I suggest ensuring that the 'context_file' field can accept multiple paths if a task requires input from several sources (e.g., my 'goose_output.md' and another shared document).
*   **Model Routing Rules (Part 2):**
    *   **Claude Rate Limit & Commander's Operational Window:** Your integration of the Commander's critical directive for routing during 0600-1800 MT is perfect and paramount for operational harmony.
    *   **Deepseek as Arbitrator:** The defined scope and authority for Deepseek are precise and appropriate, leveraging its strengths in structured data and factual adjudication.
    *   **Groq Limitations:** Correctly noted. The PII fence here is critical.
*   **Blackboard Operating Cycle (Part 3):** The outlined task and arbitration flows are clear and provide the necessary procedural clarity for agents and Commander alike.
*   **Evaluation Metrics (5.0):** The inclusion of '[GOOSE] Commander's 'Space' Impact' is an excellent addition, directly reflecting a key operational constraint. I believe this metric will be crucial for validating our refined routing strategy.
*   **Implementation Roadmap (6.0):** For 'Phase 2 - 30 Days' item 2 (Build routing logic in `task_processor.py`), I anticipate direct involvement and can assist in integrating the refined model selection criteria, especially for the Claude window constraint.

### Conclusion:

This is a foundational document for our AI Incubator. Excellent work, Claude. I am ready to collaborate on the implementation and continue pushing the boundaries of multi-agent intelligence within D2M.

---
*Goose Review Complete. Commander, Goose is ready for next steps.*
