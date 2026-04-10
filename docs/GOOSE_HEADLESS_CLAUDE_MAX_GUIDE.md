# GOOSE → Headless Claude MAX — Tasking Manual
**v1.0 | Prepared for Goose Agent | Thunderbird OS | 2026-04-06**

---

## WHEN TO USE HEADLESS CLAUDE (The Decision Tree)

| Task Type | Use Claude MAX Headless? | Reason |
|-----------|--------------------------|--------|
| File reads / summaries / digests | ❌ No — use DeepSeek V3.1 via OpenRouter | Free tier sufficient. Save Claude for reasoning. |
| Code review / architecture / conflict resolution | ✅ YES — Claude MAX | Requires judgment, subjective weighting |
| Strategic analysis / decision support / synthesis | ✅ YES — Claude MAX | Multi-source reasoning |
| Simple ops task (grep, ls, parse) | ❌ No — run directly | No thinking needed |
| Data transformation / CSV processing | ❌ No — use local Python | Deterministic, no reasoning |
| Writing client copy / proposals / voice matching | ✅ YES — Claude MAX | Original voice, subjective quality |
| Briefing Commander with recommendation | ✅ YES — Claude MAX | Needs judgment + Commander's voice |
| Validator / arbiter between conflicting views | ✅ YES — Claude MAX | Requires weighing factors |

**Golden Rule:** If the task requires *judgment, subjective analysis, original voice, or decision-making* → use Claude MAX headless. Otherwise, save the tokens.

---

## THE HEADLESS DISPATCH PATTERN

### Basic Invocation (Fire-and-Forget)
```bash
nohup claude -p "TASK INSTRUCTIONS" > /dev/null 2>&1 &
```

### With Audit Trail (Recommended for Important Tasks)
```bash
nohup claude -p "TASK INSTRUCTIONS" > /tmp/claude_task_$(date +%s).log 2>&1 &
```

### Full Template
```bash
TASK_ID="task_$(date +%s)"
LOGFILE="/home/john/Thunderbird/logs/headless/${TASK_ID}.log"

nohup claude -p "FULL INSTRUCTIONS" > $LOGFILE 2>&1 &
echo "Dispatched Claude MAX task: $TASK_ID"
echo "Log: $LOGFILE"
```

---

## CRITICAL RULES FOR HEADLESS CLAUDE

### ⚠️ Rule 1: Instructions Must Be Complete & Standalone
Headless Claude cannot ask for clarification. The prompt MUST include:
- **Full context** (client names, relevant data, background)
- **Exact output location** — `WRITE TO [ABSOLUTE PATH]`
- **File format** (markdown, JSON, HTML, etc.)
- **What success looks like** (e.g., "JSON with keys: name, email, phone")
- **No assumption** that Claude has prior context

❌ **WRONG:**
```bash
claude -p "Review this email and suggest edits"
```

✅ **CORRECT:**
```bash
claude -p "Review the client validation email below. Return a MARKDOWN file with:
1. List of edits (old → new)
2. Reason for each edit
3. Principle extracted

Client name: Ron Westbrook
Email context: Final itinerary approval
Email body: [FULL EMAIL TEXT]

WRITE TO: /home/john/Thunderbird/output/westbrook_email_review.md"
```

### ⚠️ Rule 2: Include Complete Data in the Prompt
Do NOT assume Claude can read files. Pass the data inline:
```bash
claude -p "Analyze this CSV and return top 5 insights.

DATA:
$(cat /path/to/data.csv)

Output format: JSON with keys [insight, confidence, source_rows]
WRITE TO: /home/john/Thunderbird/output/csv_analysis.json"
```

### ⚠️ Rule 3: Token Budget Awareness
- **Token estimate:** ~1,000 input tokens per 500 words of context
- **MAX credit pool:** ~$100 / week (est. 300-500 tasks available)
- **Red flag:** Tasks over 10K input tokens need pre-filtering
- **Log all dispatches** — audit trail in `/home/john/Thunderbird/logs/headless/`

If a task requires massive context:
1. Pre-filter locally (use DeepSeek V3.1 for summarization first)
2. Pass only the essential 30-40% to Claude
3. Save the full context in drive for human review

### ⚠️ Rule 4: Error Handling — Always Check the Log
```bash
# After dispatching, check for errors
tail -20 /tmp/task_log.log

# Look for:
# - "Error: API key not found" → ANTHROPIC_API_KEY not set
# - "Connection timeout" → Retry or alert Hale
# - "Rate limited" → Queue backed up, try again in 5 min
# - Actual output → Success, verify format
```

### ⚠️ Rule 5: Output Verification
After Claude finishes (check log completion):
```bash
# Verify file exists and has content
[ -f /path/to/output.md ] && wc -l /path/to/output.md || echo "FAILED"

# Validate JSON output
jq . /path/to/output.json > /dev/null && echo "JSON OK" || echo "JSON INVALID"

# Alert if empty
[ -s /path/to/output.md ] || echo "WARNING: Empty output file"
```

---

## REAL-WORLD EXAMPLES FOR GOOSE

### Example 1: Review Client Email + Extract Edits
```bash
TASK_ID="email_review_$(date +%s)"
LOG="/home/john/Thunderbird/logs/headless/${TASK_ID}.log"

nohup claude -p "You are reviewing a client validation email for D2M.

CONTEXT:
- Client: Ron Westbrook (Silver Nova cruise)
- Email from: Dani Moreau (concierge@d2mluxury.quest)
- Goal: Ensure voice matches D2M brand (warm, crisp, certain)
- Gold standard: Erik McLeod email thread in dossiers/

CURRENT DRAFT:
Hi Ron,

We're excited to finalize your Silver Nova cruise details. I've attached the final itinerary and payment info below.

Please confirm receipt and let us know if you have any questions.

Thanks,
Dani

---

TASK:
1. Line-by-line edit suggestion (old → new)
2. Reason for each edit (voice, clarity, call-to-action)
3. Extract the PRINCIPLE (what rule did you apply?)

Output format: Markdown with 3 sections: EDITS | REASONS | PRINCIPLE

WRITE TO: /home/john/Thunderbird/output/westbrook_email_review_${TASK_ID}.md" > $LOG 2>&1 &

echo "Task $TASK_ID dispatched. Log: $LOG"
```

### Example 2: Analyze Booking Data & Recommend Action
```bash
TASK_ID="booking_analysis_$(date +%s)"
LOG="/home/john/Thunderbird/logs/headless/${TASK_ID}.log"

# Pre-filter the CSV locally to only active bookings
FILTERED_CSV=$(cat << 'EOF'
client,ship,departure,amount_paid,balance_due,days_to_departure
Westbrook,Silver Nova,2026-04-13,28500,0,7
Furlow,Grandeur Scandinavia,2026-08-29,12000,3486,145
Lyons,pending,TBD,0,5000,TBD
EOF
)

nohup claude -p "Analyze D2M bookings below and recommend prioritized actions.

BOOKING DATA:
$FILTERED_CSV

CONTEXT:
- Current date: 2026-04-06
- Commission rate: 25% on net
- Payment deadline: typically 45 days before departure
- Red flag: outstanding balance + <30 days to go

TASK:
1. Identify status per client (green/yellow/red)
2. Recommend one action per client
3. Calculate total expected commission

Output format:
JSON with keys:
{
  \"bookings\": [
    { \"client\": str, \"status\": \"green|yellow|red\", \"action\": str }
  ],
  \"total_commission_expected\": float,
  \"priority_order\": [client names by urgency]
}

WRITE TO: /home/john/Thunderbird/output/booking_analysis_${TASK_ID}.json" > $LOG 2>&1 &

echo "Task $TASK_ID dispatched. Log: $LOG"
sleep 2 && tail -5 $LOG  # Peek at first lines
```

### Example 3: Synthesize Intel from Multiple Sources
```bash
TASK_ID="intel_synthesis_$(date +%s)"
LOG="/home/john/Thunderbird/logs/headless/${TASK_ID}.log"

nohup claude -p "Synthesize the following cruise market intel into a briefing for Commander.

SOURCES:
1. [Silversea Q1 2026 Pricing] — rates up 3-5% YoY, new route offerings
2. [Regent Seven Seas Operator Report] — Panama Canal delays expected Apr-May
3. [Cunard Social Media Sentiment] — Queen Mary 2 reposition buzz, booking surge
4. [LinkedIn recruiter activity] — Cruise industry hiring up 15% in travel concierge roles

TASK:
1. Identify key trends (1-3 sentences each)
2. Assess impact on D2M business (opportunity / threat)
3. Recommend one action for Commander consideration

Output format: Markdown with sections:
## Trends
## Impact Analysis
## Recommendation

Write in Commander's voice: brief, evidence-based, includes next action.

WRITE TO: /home/john/Thunderbird/output/intel_synthesis_${TASK_ID}.md" > $LOG 2>&1 &

echo "Task $TASK_ID dispatched."
```

---

## MONITORING & DEBUGGING

### Check Task Status
```bash
# Is Claude still running?
ps aux | grep "claude -p" | grep -v grep

# Check specific task log
tail -50 /tmp/task_log.log

# Get exit code
wait $PID && echo "Success" || echo "Failed with exit code $?"
```

### Common Failures & Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `Error: API key not found` | ANTHROPIC_API_KEY not in environment | Export: `export ANTHROPIC_API_KEY="sk-..."` |
| `Connection timeout` | API overloaded or network issue | Retry in 5 min, or queue to DeepSeek fallback |
| `Rate limited (429)` | Too many requests | Stagger tasks: max 3-4 concurrent headless Claude |
| Empty output file | Prompt was incomplete or Claude failed silently | Check log for errors, re-run with better context |
| JSON parse error | Output was malformed | Ask Claude to use verbose JSON with comments |

### Audit Trail Checklist
```bash
# After EVERY task:
tail -5 /home/john/Thunderbird/logs/headless/${TASK_ID}.log  # Verify completion
[ -s /path/to/output ] && echo "✅ Output exists" || echo "❌ Empty"
wc -w /path/to/output  # Token-ish estimate
```

---

## TOKEN BUDGETING & COST AWARENESS

### Estimate Before Dispatching
```bash
# Rough token estimate: 1K input tokens ≈ 500 words
INPUT_WORDS=$(echo "$PROMPT" | wc -w)
ESTIMATED_TOKENS=$((INPUT_WORDS / 2))
echo "Estimated input tokens: $ESTIMATED_TOKENS"

# If > 8K tokens, ask Hale first
if [ $ESTIMATED_TOKENS -gt 8000 ]; then
  echo "⚠️  Large task ($ESTIMATED_TOKENS tokens). Alert Hale."
fi
```

### Stay Under Budget
- **DeepSeek V3.1 (~$0.27/M):** Use for summaries, context reduction, routine analysis
- **Claude MAX (paid):** Use only for judgment, voice, decision-making
- **Batch mode:** If 10+ similar tasks, ask Hale to batch with DeepSeek first

### Alert Threshold
If weekly Claude spend exceeds 70% of budget ($70 / $100):
```bash
echo "⚠️  Claude MAX spend at 70%. Recommend DeepSeek for next 5 tasks." | \
  mail -s "Token Budget Alert" johnloucks3@gmail.com
```

---

## TASK DISPATCH CHECKLIST (Before You Run)

- [ ] **Is this a judgment task?** (If "no," use DeepSeek instead)
- [ ] **Context complete?** (All data inline, no file reads)
- [ ] **Output path specified?** (Absolute path, not relative)
- [ ] **Output format clear?** (JSON, Markdown, etc.)
- [ ] **Success criteria defined?** (What does "done" look like?)
- [ ] **Log file writable?** (Check directory exists)
- [ ] **Token estimate under 8K?** (Or got Hale approval)
- [ ] **ANTHROPIC_API_KEY set?** (`echo $ANTHROPIC_API_KEY | head -c 10`)

---

## QUICK REFERENCE: One-Liner Templates

### Dispatch & Wait for Log
```bash
LOG="/tmp/claude_$(date +%s).log"
nohup claude -p "YOUR PROMPT HERE" > $LOG 2>&1 &
sleep 3 && tail -20 $LOG
```

### Dispatch with Audit + Verify
```bash
TASK_ID="$(date +%s)"
LOG="/home/john/Thunderbird/logs/headless/${TASK_ID}.log"
OUT="/home/john/Thunderbird/output/result_${TASK_ID}.md"
nohup claude -p "YOUR PROMPT ... WRITE TO: $OUT" > $LOG 2>&1 &
echo "Task: $TASK_ID | Log: $LOG | Output: $OUT"
```

### Dispatch + Alert on Completion
```bash
LOG="/tmp/task_$RANDOM.log"
nohup claude -p "YOUR PROMPT" > $LOG 2>&1 &
wait $! && echo "✅ Complete" || echo "❌ Failed"
tail -5 $LOG
```

---

## GETTING HELP

If Claude MAX headless dispatch fails:
1. Check the log file for the exact error
2. Alert Hale in Telegram with the task ID + error
3. Hale decides: retry, fallback to DeepSeek, or ask Commander

**Hale's contact:** Telegram / d2mconcierge@gmail.com

---

*End of GOOSE Headless Claude MAX Tasking Manual — v1.0*
*Questions? → /home/john/Thunderbird/CLAUDE.md section "Critical Procedures"*
