# HALE Agent Tasking — Quick Reference
**Copy/paste patterns for common task dispatch scenarios**

---

## Pattern 1: Simple OpenCode Task (DeepSeek V3.1, $0)

```python
from OpsCenter.opencode_headless_claude_dispatch import dispatch_to_headless_claude

result = dispatch_to_headless_claude(
    task_description="[YOUR TASK HERE]",
    output_file_path="/home/john/Thunderbird/output/[filename].txt",
    task_name="[short-name]",
    task_type="research"  # or "intelligence", "analysis"
)

if result["status"] == "SPAWNED":
    print(f"✅ Spawned (PID {result['pid']})")
```

**Use for:** Research, summarization, intelligence gathering, lightweight analysis.

---

## Pattern 2: Claude Code with Escalation (Sonnet/Opus, $$ or free)

```python
from OpsCenter.headless_claude_fallback import dispatch_with_fallback

result = dispatch_with_fallback(
    task_description="[YOUR TASK HERE]",
    output_file_path="/home/john/Thunderbird/output/[filename].md",
    task_name="[short-name]",
    max_retries=1
)

if result["escalated"]:
    print(f"⚠️ Escalated to Claude Code")
if result["status"] in ["SPAWNED", "ESCALATED_TO_CLAUDE_CODE"]:
    print(f"✅ Running (PID {result['pid']})")
```

**Use for:** Judgment calls, voice-matched copy, complex analysis, fallback when OpenCode fails.

---

## Pattern 3: Agent SDK (Full MCP Access)

```python
from core.ai_infra.thunderbird_personas import invoke_persona_sdk

result = invoke_persona_sdk(
    persona="HALE",  # COS, A2_DEMBE, A3_MOREAU, etc.
    prompt=f"""
    [YOUR TASK + CONTEXT HERE]
    
    WRITE output to /home/john/Thunderbird/output/result.json
    """,
    output_file="/home/john/Thunderbird/output/result.json",
    model="claude-sonnet-4-6"
)

if result["status"] == "EXECUTED":
    print(f"✅ Completed with MCP tools")
```

**Use for:** Tasks needing tool access (Gmail, Drive, TESS, MCP integration).

---

## Pattern 4: Arbitration (DeepSeek R1, $0)

```python
from openrouter_deepseek import call_deepseek_reasoning

result = call_deepseek_reasoning(
    prompt="""
    DECISION: [Question]
    
    POSITION A: [First argument]
    POSITION B: [Second argument]
    
    DECIDE: [Single sentence answer]
    """,
    max_tokens=500
)

print(f"Decision: {result['text']}")
```

**Use for:** Tie-breaking, judgment calls, arbitration between conflicting recommendations.

---

## Standard Task Descriptions (Copy & Modify)

### Research Task
```
Conduct a comprehensive [research topic]. 

Sources:
- [Source 1]
- [Source 2]
- [Source 3]

Format as:
- Markdown with sections for each key finding
- Include source links for every citation
- Actionable summary at top

Output to /home/john/Thunderbird/output/[name].md
```

### Intelligence Sweep
```
Run a daily intelligence sweep on [topic].

Scan:
1. [Area 1]
2. [Area 2]
3. [Area 3]

Output as JSON:
{
  "timestamp": "ISO-8601",
  "items": [
    {
      "source": "...",
      "headline": "...",
      "link": "...",
      "relevance": "high|medium|low",
      "action_item": "..."
    }
  ]
}

Output to /home/john/Thunderbird/output/[name]_{DATE}.json
```

### Client Email Draft
```
Draft a [email_type] email for [client_name].

Context:
- [Detail 1]
- [Detail 2]
- [Detail 3]

Email should:
1. [Requirement 1]
2. [Requirement 2]
3. [Requirement 3]

Format: HTML-wrapped body (no stationery yet)
Sign-off: [Persona name]
Voice: [tone description]

Do NOT send. Output as HTML body only.
Output to /home/john/Thunderbird/output/[name]_email.html
```

### Analysis Task
```
Analyze [topic] and recommend [decision point].

Data:
[Provide or reference data]

Analysis should include:
- Summary of key findings
- Recommendation with reasoning
- Confidence level (high/medium/low)
- Risk assessment if applicable
- Next steps

Format as Markdown with sections.
Output to /home/john/Thunderbird/output/[name]_analysis.md
```

---

## Four Gates (Hold for Commander)

```python
# If result includes any of these, surface to Commander:

if result.get("hit_gate") in ["client_send", "financial_commit", "new_client_contact", "strategy_direction"]:
    surface_to_commander(result)
    # Task halts until Commander approves
```

---

## Task Monitoring

```python
# Check status of active tasks
from OpsCenter.task_audit_log import load_active_tasks

active = load_active_tasks()
for task in active:
    print(f"{task['task_id']}: {task['task_name']} ({task['status']}) PID {task['pid']}")
    if task["status"] == "SPAWNED" and elapsed_seconds > task["sla_minutes"] * 60:
        alert_cos(f"⚠️ {task['task_id']} exceeded SLA")
```

---

## Output File Conventions

All task outputs MUST be written to:
```
/home/john/Thunderbird/output/
  ├── [task_name]_YYYYMMDD.json    (structured data)
  ├── [task_name]_YYYYMMDD.md      (markdown reports)
  ├── [task_name]_YYYYMMDD.html    (email bodies)
  └── [task_name]_YYYYMMDD.txt     (plain text)
```

**Mandatory prompt instruction:**
```
WRITE your complete output to /home/john/Thunderbird/output/[filename]
Do NOT output to stdout. All output goes to file.
```

---

## Error Handling

```python
if result["status"] == "SPAWNED":
    # Task running
    pass
elif result["status"] == "ESCALATED_TO_CLAUDE_CODE":
    # OpenCode failed, Claude Code now running
    log(f"Escalated: {result.get('escalation_reason')}")
elif result["status"] == "FAILED":
    # Both tiers failed
    alert_cos({
        "task_id": task_name,
        "error": result.get("error"),
        "log_file": result.get("log_file")
    })
```

---

## Common Personas (Agent SDK)

```python
# Invoke by name:
invoke_persona_sdk(persona="HALE", ...)        # Col Victoria Hale (COS)
invoke_persona_sdk(persona="A2_DEMBE", ...)    # Lt Col Marcus Dembe (Research)
invoke_persona_sdk(persona="A3_MOREAU", ...)   # Danielle Moreau (Concierge)
invoke_persona_sdk(persona="A5_CASTILLO", ...) # Lt Col Ryan Castillo (Strategy)
invoke_persona_sdk(persona="A9_HARLAN", ...)   # Victor Harlan (Finance)
invoke_persona_sdk(persona="CH_WASHINGTON", ...)  # Col James Washington (Ethics)
invoke_persona_sdk(persona="A12_ELON", ...)    # ELON (Innovation)
```

---

## Cost Tracking

```
Brain 1 (DeepSeek V3.1): $0/task via OpenRouter free tier
Brain 2 (Claude Sonnet): $0/task (free escalation tier)
Brain 3 (Claude Opus): $$ per task (from MAX budget)
Arbitration (DeepSeek R1): $0/task via OpenRouter free tier
Local Python: $0 (no LLM)
```

Track all spend in `hale_state.json` → `financial_pulse.cost_tracking`.

---

*— Iron Vic | Thunderbird Wing | Quick Reference v1.0*
