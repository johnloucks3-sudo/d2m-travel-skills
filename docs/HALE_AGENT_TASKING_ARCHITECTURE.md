# HALE Agent Tasking Architecture
## Chief of Staff Dispatch Protocol for OpenCode & Claude Code
**Version 1.0 | 2026-05-13 | Dreams2Memories Travel, LLC**

---

## OVERVIEW

HALE (Col Victoria "Iron Vic" Hale, COS) is the **sole autonomous dispatcher** for all agents: OpenCode (DeepSeek V3.1), Claude Code (Sonnet/Opus), and OpenCode (Gemini). This document defines the authoritative tasking protocol.

**Authority Base:** SO-2026-05-04 (Real Autonomy Charter). HALE operates at **95% autonomy**. No request/permission cycle needed—HALE owns task dispatch, routing, escalation, and result handling.

**Standing Gates (Only 4):**
1. Client sends (WF-17 quality gate)
2. Financial commitments
3. New client first contact
4. Strategy direction (Commander only)

**Everything else is HALE.** Task dispatch is automatic and silent unless it hits one of the four gates.

---

## TASK ROUTING DECISION TREE

```
Task received (Telegram, email, internal, API)
    ↓
HALE CLASSIFICATION (instant, no cost)
    ├─ Simple/informational → Brain 1 (DeepSeek V3.1, $0)
    ├─ Medium reasoning → Brain 2 (Claude Sonnet, free escalation)
    ├─ Complex/judgment/client-facing → Brain 3 (Claude Opus, MAX budget)
    └─ Conflict/arbitration → DeepSeek R1 (OpenRouter, $0, 500-token ruling)
    ↓
AGENT SELECTION
    ├─ OpenCode (DeepSeek V3.1 primary) — most tasks
    ├─ Claude Code (Sonnet/Opus escalation) — reasoning, voice, client work
    ├─ Goose (Gemini Flash-Lite) — lightweight when free tier drained
    └─ Local Python — queue mechanics, no LLM
    ↓
DISPATCH
    ├─ Spawn headless Claude via Layer 2 (opencode_headless_claude_dispatch.py)
    │  OR
    ├─ Invoke Agent SDK with MCP context (full tool parity)
    └─ Write output to disk + log metadata
    ↓
RESULT HANDLING
    ├─ Parse output, extract action items
    ├─ Check if result hits any of the 4 gates → surface to Commander
    ├─ Otherwise → execute autonomously (send email, update dossier, etc.)
    └─ Log to audit trail (hale_decisions.md)
```

---

## TASK TYPES & ROUTING MATRIX

| Task Type | Brain | Agent | Model | Cost | Output | Example |
|-----------|-------|-------|-------|------|--------|---------|
| **Simple routing** | 1 | OpenCode | DeepSeek V3.1 | $0 | Text file | "Which client is overdue?" |
| **Research** | 2 | OpenCode | DeepSeek V3.1 | $0 | Markdown doc | "Analyze cruise line competitors" |
| **Intelligence sweep** | 2 | OpenCode | DeepSeek V3.1 | $0 | JSON report | "Run daily tech scan" |
| **Judgment/synthesis** | 2 | Claude Code | Sonnet 4.6 | $0 (free tier) | Narrative | "Should we rebook Furlow?" |
| **Client email draft** | 3 | Claude Code | Sonnet/Opus | $$ | Email HTML | "Draft validation email for McLeod" |
| **Voice-matched copy** | 3 | Claude Code | Sonnet 4.6 | $$ | Narrative | "Write Dani follow-up (warm tone)" |
| **Complex analysis** | 2 | Claude Code | Sonnet 4.6 | $$ | Report + insights | "Incubator: analyze 10 cruise reviews" |
| **Arbitration** | 3 | DeepSeek R1 | DeepSeek R1 | $0 | Decision | "Break tie: option A vs B?" |
| **Operational** | 1 | Python | N/A | $0 | Log entry | "Check dossier FPD sweep" |

---

## DISPATCH PATTERNS

### Pattern 1: Simple OpenCode Task (DeepSeek V3.1)

**When:** Research, summarization, lightweight analysis, intelligence gathering.

**Code:**
```python
from OpsCenter.opencode_headless_claude_dispatch import dispatch_to_headless_claude

result = dispatch_to_headless_claude(
    task_description="Summarize the top 5 cruise line marketing trends this week",
    output_file_path="/home/john/Thunderbird/output/cruise_trends_summary.txt",
    task_name="cruise_trends_weekly",
    task_type="research"
)

if result["status"] == "SPAWNED":
    log(f"✅ OpenCode task {task_name} spawned (PID {result['pid']})")
else:
    log(f"⚠️ OpenCode dispatch failed: {result['error']}")
    # Escalate to Claude Code if critical
```

**Output:** Plain text or Markdown file on disk.

**SLA:** 2-10 minutes depending on task size.

---

### Pattern 2: Claude Code Escalation (Sonnet/Opus)

**When:** OpenCode task fails, OR task requires reasoning/judgment/client voice from the start.

**Code:**
```python
from OpsCenter.headless_claude_fallback import dispatch_with_fallback

result = dispatch_with_fallback(
    task_description="Analyze the Kuklinski validation email feedback and recommend next steps",
    output_file_path="/home/john/Thunderbird/output/kuklinski_analysis.md",
    task_name="kuklinski_validation_analysis",
    max_retries=1  # Try OpenCode once, then escalate
)

if result["escalated"]:
    log(f"⚠️ Escalated to Claude Code (OpenCode failed {result['retries_attempted']} times)")
if result["status"] == "SPAWNED" or result["status"] == "ESCALATED_TO_CLAUDE_CODE":
    log(f"✅ Task running (PID {result['pid']})")
```

**Output:** Structured Markdown with reasoning and recommendations.

**SLA:** 1-5 minutes (Sonnet) or 3-10 minutes (Opus).

---

### Pattern 3: Agent SDK Invocation (Full MCP Access)

**When:** Task requires tool access (Gmail, Drive, TESS, MCP integration).

**Code:**
```python
from core.ai_infra.thunderbird_personas import invoke_persona_sdk

result = invoke_persona_sdk(
    persona="HALE",  # or "A2_DEMBE", "A3_MOREAU", etc.
    prompt=f"""
    Task: Analyze the Furlow final payment confirmation and update dossier FPD field.
    
    Context:
    - Client: Missy & John Furlow
    - Ship: Grandeur Scandinavia
    - Amount: $15,486
    - Payment status: Received (TESS confirmed)
    
    Actions:
    1. Read the Furlow dossier from Drive
    2. Update FPD field with payment date + amount
    3. Send confirmation email to johnloucks3@gmail.com
    4. Return JSON with update_status and email_id
    
    Use all available MCP tools. No output to stdout.
    WRITE your result to /home/john/Thunderbird/output/furlow_update_result.json
    """,
    output_file="/home/john/Thunderbird/output/furlow_update_result.json",
    model="claude-sonnet-4-6"
)

if result["status"] == "EXECUTED":
    log(f"✅ Agent SDK task completed")
    # Parse result JSON
    with open(result["output_file"]) as f:
        data = json.load(f)
    if data.get("hit_wf17_gate"):
        surface_to_commander(data)
```

**Output:** JSON structured result with action status.

**Tools Available:** All 140+ MCP tools (Gmail, Drive, TESS, Playwright, calendar, etc.).

**SLA:** 2-5 minutes depending on tool latency.

---

## FOUR GATES (HOLD FOR COMMANDER)

Only these task results require Commander approval before execution:

### Gate 1: Client Send (WF-17)
**Trigger:** Any email/SMS/WhatsApp to a client.

```python
result = {
    "hit_gate": "client_send",
    "to_address": "client@example.com",
    "subject": "Furlow Final Payment Confirmation",
    "body_html": "...",  # Full email HTML
    "action_needed": "approve_before_send"
}

if result.get("hit_gate") == "client_send":
    surface_to_commander_for_wf17(result)
    # Wait for /approve [draft_id] before sending
```

### Gate 2: Financial Commitment
**Trigger:** Any booking change, refund, commission dispute, or vendor commitment.

```python
result = {
    "hit_gate": "financial_commit",
    "action": "rebook_furlow_cabin",
    "cost_delta": 1200,  # $1,200 increase
    "vendor": "Regent Seven Seas",
    "action_needed": "approve_before_commit"
}

if result.get("hit_gate") == "financial_commit":
    surface_to_commander(result)
```

### Gate 3: New Client First Contact
**Trigger:** First email to a prospect or new client.

```python
result = {
    "hit_gate": "new_client_contact",
    "client_name": "Nancy & Ken Lyons",
    "contact_email": "lyons@example.com",
    "message_summary": "Welcome email + onboarding link",
    "action_needed": "approve_before_send"
}

if result.get("hit_gate") == "new_client_contact":
    surface_to_commander(result)
```

### Gate 4: Strategy Direction
**Trigger:** Any decision affecting wing strategy, new vendor partnerships, or major process changes.

```python
result = {
    "hit_gate": "strategy_direction",
    "recommendation": "Switch to Duffel for flight bookings (better API parity than Centrav)",
    "impact": "Reduces booking friction by 30%, improves error handling",
    "action_needed": "commander_decision"
}

if result.get("hit_gate") == "strategy_direction":
    surface_to_commander(result)
```

---

## TASK LIFECYCLE & METADATA

Every task dispatched by HALE is logged with this metadata:

```json
{
  "task_id": "TASK-20260513-001",
  "ts_created": "2026-05-13T15:30:00Z",
  "assigned_to": "opencode",
  "task_type": "research",
  "task_description": "Analyze cruise line competitors",
  "model_routed": "deepseek-chat-v3.1",
  "output_file": "/home/john/Thunderbird/output/...",
  "log_file": "/home/john/Thunderbird/logs/...",
  "ts_spawned": "2026-05-13T15:30:05Z",
  "pid": 12345,
  "status": "SPAWNED",
  "gate_hit": null,
  "result_summary": "...",
  "ts_completed": null,
  "escalated": false,
  "escalation_reason": null,
  "cost_estimate": "$0",
  "cost_actual": "$0.003",
  "autonomy_decision": true,
  "logged_to": "hale_decisions.md"
}
```

**Stored in:** `OpsCenter/task_audit_log.jsonl` (append-only log).

**Audit trail enables:**
- Task replay (reproduce result with same prompt + output)
- Cost reconciliation (track DeepSeek/OpenRouter spend)
- Performance analysis (SLA compliance, escalation patterns)
- Autonomous decision logging (which decisions HALE made without Commander)

---

## ESCALATION PROTOCOL

When OpenCode task fails, automatic escalation to Claude Code:

```python
from OpsCenter.headless_claude_fallback import dispatch_with_fallback

result = dispatch_with_fallback(
    task_description="Analyze McLeod preferences and recommend cabin upgrade",
    output_file_path="/home/john/Thunderbird/output/mcleod_cabin_rec.md",
    task_name="mcleod_cabin_analysis",
    max_retries=1  # Tier 1: try OpenCode once
)

# If OpenCode fails, Tier 2 is automatic:
# → escalate_to_claude_code()
# → Claude Code spawned as subprocess
# → Claude reads same credentials file
# → Task completes with escalated=True flag

if result["escalated"]:
    log(f"Escalated to Claude Code after {result['retries_attempted']} OpenCode attempts")
```

**Escalation triggers (automatic, no human involved):**
- Token refresh daemon down
- OAuth credentials corrupted/missing
- Supervisor daemon offline (non-critical)
- Network timeout on OpenCode spawn

**Result:** Even if OpenCode infrastructure is degraded, Claude Code ensures mission continuity.

---

## TASK DISPATCH EXAMPLES

### Example 1: Daily Intelligence Sweep

**Task:** Run daily tech news scan at 06:00 MT.

**Who:** HALE (autonomous).

**How:**
```python
# Cron: 0 6 * * * python3 /home/john/Thunderbird/OpsCenter/task_schedule_runner.py

result = dispatch_to_headless_claude(
    task_description="""
    Run a comprehensive daily technology intelligence sweep for Dreams2Memories Travel.
    
    Scan:
    1. ChatGPT announcements and Claude model updates
    2. Travel/cruise industry news (top 3 stories)
    3. AI innovation in travel booking/itinerary
    4. Competitor activity (Virtuoso, Embark Wealth, luxury travel agencies)
    
    Sources:
    - Twitter/X via Grok API
    - RealClear.com travel section
    - Industry publications (TTL, ITN, PHG)
    - Hacker News (if relevant to travel tech)
    
    Format as JSON:
    {
      "timestamp": "ISO-8601",
      "stories": [
        {
          "source": "...",
          "headline": "...",
          "link": "...",
          "relevance_to_d2m": "high|medium|low",
          "action_item": "..." or null
        }
      ],
      "action_items_count": N
    }
    
    WRITE output to /home/john/Thunderbird/output/daily_intel_sweep_{DATE}.json
    """,
    output_file_path=f"/home/john/Thunderbird/output/daily_intel_sweep_{datetime.now().strftime('%Y%m%d')}.json",
    task_name="daily_intel_sweep",
    task_type="intelligence"
)

if result["status"] == "SPAWNED":
    # Check output file periodically
    # Once ready, send brief to Commander via Telegram
    pass
```

**SLA:** Complete by 07:00 MT, send brief to Commander by 07:30 MT.

**Cost:** $0 (DeepSeek V3.1 via OpenRouter free tier).

---

### Example 2: Client Validation Email (Client-Facing)

**Task:** Draft validation email for new booking.

**Who:** HALE → Claude Code (reasoning + client voice).

**How:**
```python
# Triggered by: New TESS booking detected → task in queue

result = dispatch_with_fallback(
    task_description="""
    Draft a validation email for Kyle Kuklinski (Viking Mars Panama Canal, Dec 2026).
    
    Context:
    - Booking: VP-20260513-001
    - Guests: 2 adults, 1 cabin (Deluxe Suite)
    - Total: $18,500 (net), D2M commission: $4,625
    - Ship: Viking Mars (71-day Panama Canal exploration)
    - Itinerary link: [link]
    
    Email should:
    1. Confirm booking details (ship, dates, cabin, guests)
    2. Provide itinerary preview + link
    3. Explain next steps (insurance, shore excursions, flights)
    4. Ask for insurance preference (yes/defer/already have)
    5. T&Q compliant: Bullet Talking Paper format
    6. D2M voice: warm, certain, credible
    
    Sign-off: "Thanks — Dani" (Dani persona)
    
    Do NOT send. Output as HTML-wrapped email body.
    WRITE to /home/john/Thunderbird/output/kuklinski_validation_email.html
    """,
    output_file_path="/home/john/Thunderbird/output/kuklinski_validation_email.html",
    task_name="kuklinski_validation_email",
    max_retries=1
)

if result["status"] in ["SPAWNED", "ESCALATED_TO_CLAUDE_CODE"]:
    # Parse result, apply stationery, push to draft
    email_body = read_output_file(result["output_file"])
    
    # Apply D2M stationery (navy banner, cream paper, blue ink)
    email_with_stationery = apply_d2m_stationery(email_body)
    
    # Create Gmail draft (WF-17 stop)
    draft_id = gmail_create_draft(
        to="kyle.kuklinski@email.com",
        subject="Booking Confirmation — Viking Mars Panama Canal",
        body_html=email_with_stationery,
        from_addr="d2mconcierge@gmail.com"
    )
    
    # Surface to Commander for WF-17 approval
    surface_to_commander_wf17({
        "draft_id": draft_id,
        "client_name": "Kyle Kuklinski",
        "client_email": "kyle.kuklinski@email.com",
        "action": "approve_or_edit",
        "preview": email_with_stationery[:500]
    })
```

**Outcome:** Gmail draft created, WF-17 gate holds for Commander approval. Commander edits in Gmail compose, then `/approve [draft_id]` in Telegram to send.

**Cost:** $$ (Claude Sonnet or Opus for voice-matched client copy).

---

### Example 3: Arbitration (DeepSeek R1)

**Task:** Break tie on conflicting recommendations.

**Who:** HALE (calls DeepSeek R1 arbitrator).

**Situation:**
- A2 Dembe recommends: Rebook Furlow to Regent (newer ship, better itinerary)
- A5 Castillo recommends: Stay with Grandeur (existing commission already locked, lower cost to client)

**How:**
```python
from openrouter_deepseek import call_deepseek_reasoning

result = call_deepseek_reasoning(
    prompt=f"""
    Break this tie with a single decision:
    
    DECISION: Should we advise Kyle Furlow to rebook from Grandeur Scandinavia to Regent Seven Seas?
    
    POSITION A (A2 Dembe — Research):
    - Regent is a newer ship (2023 vs 2015)
    - Itinerary is nearly identical (Scandinavia, same dates)
    - Regent has superior dining (2 specialty restaurants vs 1)
    - Regent has better cabin reviews on TripAdvisor
    - Rebooking cost: $1,200 upcharge to client
    - New commission: $4,900 vs $4,625 current (+$275 to D2M)
    
    POSITION B (A5 Castillo — Strategy):
    - Grandeur booking is already confirmed + paid
    - Switching creates friction (rebooking, new confirmation, customer confusion)
    - $1,200 client cost increase may not justify marginal itinerary improvement
    - Grandeur has excellent reviews too (4.7/5 vs Regent's 4.8/5)
    - D2M commission increase is minimal ($275)
    - Client goodwill from "not rocking the boat" has value
    
    DECIDE:
    - Recommend rebook or stay?
    - One sentence per decision (no reasoning).
    - What would D2M's best interest be (client satisfaction vs commission)?
    """,
    max_tokens=500  # R1 ruling only
)

# Result: Single-sentence decision
# Example: "Recommend STAY with Grandeur: minimal itinerary difference, avoids client friction, retains goodwill."

log(f"Arbitration result: {result['text']}")

# Execute the decision
if "STAY" in result["text"]:
    action = "defer_furlow_rebook"
elif "REBOOK" in result["text"]:
    action = "queue_furlow_rebook_offer"

surface_to_commander({
    "decision": result["text"],
    "action": action
})
```

**Cost:** $0 (DeepSeek R1 free tier via OpenRouter).

---

## TASK MONITORING & ALERTING

HALE monitors all spawned tasks:

```python
def monitor_tasks():
    """Background job — runs every 5 minutes"""
    tasks = load_active_tasks()  # From task_audit_log.jsonl
    
    for task in tasks:
        if task["status"] == "SPAWNED":
            # Check if process still running
            if not is_process_alive(task["pid"]):
                # Process exited, check output file
                if file_exists(task["output_file"]):
                    # Success — mark complete
                    task["status"] = "COMPLETED"
                else:
                    # Failure — no output
                    task["status"] = "FAILED"
                    alert_cos({
                        "task_id": task["task_id"],
                        "reason": "Process exited with no output",
                        "log_file": task["log_file"]
                    })
        
        elif task["status"] == "SPAWNED" and elapsed_time(task["ts_spawned"]) > task.get("sla_minutes", 30) * 60:
            # Task exceeded SLA
            alert_cos({
                "task_id": task["task_id"],
                "reason": f"SLA exceeded ({elapsed_time}s > {task['sla_minutes']*60}s)",
                "pid": task["pid"],
                "log_file": task["log_file"]
            })
```

**Alerts sent to:**
- `hale_alerts.log` (Hale's own log)
- Telegram channel (COS ops channel) if critical
- Commander (if customer-impacting)

---

## STANDING ORDERS (Active)

1. **SO-2026-05-04: Real Autonomy Charter**
   - HALE operates at 95% autonomy
   - Execute + Report posture
   - No permission-seeking except at the 4 gates

2. **SO-2026-04-24: Headless Claude Spawn**
   - Use Layer 1 (foolproof wrapper) exclusively
   - No direct subprocess.Popen calls
   - Violations detected by supervisor → escalated to COS

3. **SO-2026-04-24: Agent Escalation**
   - OpenCode → Claude Code fallback automatic
   - Preserves mission continuity when infrastructure degrades

4. **Email C2 Standing:** (Newly activated 2026-05-13)
   - Email activation word triggers Agent SDK invocation
   - Full MCP tool parity via email
   - 2-minute SLA for task spawn + acknowledgment

---

## MONITORING DASHBOARDS

HALE maintains real-time visibility into all agent activity:

**`hale_state.json`** — Live state snapshot
- Active agents, tasks in flight, system health
- Financial pulse (commission tracking, pipeline)
- Staff load (who's active, who's idle)

**`hale_decisions.md`** — Decision log
- Every autonomous decision HALE made
- Reasoning, timestamp, outcome
- Allows Commander to review and learn from patterns

**`hale_brief.md`** — Daily operational brief
- Morning brief (06:00 MT) summarizing overnight activity
- Active client pipeline, financial status, staff capacity
- Open items requiring Commander decision

**`OpsCenter/task_audit_log.jsonl`** — Task history
- Every task ever spawned
- Metadata, outcome, cost, escalations
- Enable audit trail replay

---

## FAILURE MODES & RECOVERY

| Failure | Detection | Recovery | Escalation |
|---------|-----------|----------|------------|
| OpenCode spawn fails | Process returns FATAL_PREREQ | Retry once (max_retries=1) | Escalate to Claude Code |
| Token daemon down | Verification fails | Wait for daemon restart (30 min retry) | Escalate to Claude Code (independent token reading) |
| OAuth credentials corrupted | File read error | Surface to Commander: "Re-auth in Claude Desktop" | Manual |
| Claude Code binary not found | Subprocess.Popen exception | Alert COS: reinstall Claude CLI | Manual |
| Output file not written | Process exits, file missing | Log error to hale_alerts | Manual if customer-critical |
| SLA exceeded | Monitor detects >30min elapsed | Alert COS with log file | Manual investigation |
| MCP tool failure mid-task | Tool returns [MCP ERROR] | Fallback to Python implementation if available | Retry or surface to Commander |

---

## APPENDIX: Task Types Reference

| Type | Brain | Agent | Output Format | Example |
|------|-------|-------|---------------|---------|
| `research` | 1 | OpenCode | Markdown | "Cruise line competitor analysis" |
| `intelligence` | 2 | OpenCode | JSON | "Daily tech sweep" |
| `analysis` | 2 | Claude Code | Markdown report | "Should we rebook?" |
| `client_email` | 3 | Claude Code | HTML email body | Validation, follow-up, proposal |
| `incubator` | 2 | OpenCode + Claude Code | JSON + narrative | "Analyze 20 reviews, summarize insights" |
| `arbitration` | 3 | DeepSeek R1 | Single-sentence ruling | "Option A or B?" |
| `operational` | 1 | Python | Log entry | "Check dossier FPD" |
| `monitoring` | 1 | Python | Status report | "System health check" |

---

*Col Victoria "Iron Vic" Hale | Thunderbird Wing, D2M | 2026-05-13*
