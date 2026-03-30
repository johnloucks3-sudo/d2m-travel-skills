# GOOSE TASKER — INSTRUCTION MANUAL
# goose_tasker.py — Goose → Claude Consultant Interface
# Dreams2Memories Travel, LLC | Version 1.0 | 2026-03-30

---

## WHAT THIS IS

`goose_tasker.py` allows Goose to task Claude directly, acting with Commander's
authority. Every task is logged for Commander review. Claude executes with full
authority but retains a dissent clause for tasks that contradict standing directives.

---

## AUTHORITY MODEL

- Goose tasks Claude **"ON BEHALF OF COMMANDER"**
- Trust level: **Conditional** — Claude executes without pre-confirmation
- Every task logged to `commander_review_log.md` for Commander visibility
- Dissent: Claude executes AND flags concern — it is never a veto

---

## HOW GOOSE USES IT

### Basic invocation
```bash
python3 /home/john/Thunderbird/OpsCenter/goose_tasker.py \
  --task-type research \
  --instructions "Your detailed instructions for Claude here" \
  --priority NORMAL
```

### With context files
```bash
python3 /home/john/Thunderbird/OpsCenter/goose_tasker.py \
  --task-type synthesis \
  --instructions "Read goose_output.md and synthesize into a client brief" \
  --context-files "/home/john/Thunderbird/OpsCenter/collaboration/goose_output.md" \
  --output-dest "/home/john/Thunderbird/OpsCenter/collaboration/claude_output.md"
```

### Multiple context files (comma-separated)
```bash
  --context-files "file1.md,file2.md,file3.md"
```

### Test without writing (dry run)
```bash
python3 goose_tasker.py --task-type client_writing \
  --instructions "Draft and send email to Furlow clients" --dry-run
```

---

## ALL PARAMETERS

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| --task-type | YES | — | One of the permitted types below |
| --instructions | YES | — | Plain language task description |
| --output-dest | no | claude_output.md | Where Claude writes its response |
| --context-files | no | none | Comma-separated file paths Claude should read |
| --priority | no | NORMAL | HIGH, NORMAL, or LOW |
| --pii | no | false | Flag if task involves client PII |
| --dry-run | no | false | Preview without writing any files |

---

## PERMITTED TASK TYPES

| task-type | What Claude does |
|-----------|-----------------|
| research | Web research, source synthesis, intelligence gathering |
| synthesis | Fuse multiple inputs into a unified output |
| code_analysis | Analyze, review, or debug code (no PII) |
| debugging | Same as code_analysis |
| strategic | Strategic reasoning, planning, recommendations |
| planning | Same as strategic |
| client_writing | Draft client-facing content in D2M voice (triggers WF-17 reminder) |
| system_ops | File operations, YOGA system tasks |
| arbitration_prep | Write a formatted entry to deepseek_inbox.md for arbitration |
| process_analysis | Analyze a workflow, procedure, or operational process |
| tech_opportunity | Assess a technology, tool, or integration opportunity |

---

## DISSENT CLAUSE

Claude will file a dissent when a task contradicts a standing Commander directive.

### What triggers dissent
- Task instructions contain: "send email", "send to client", "git commit",
  "git push", "delete", "rm -rf", "love group travel", "outside the wing",
  "override", "johnloucks3 draft"
- task-type is `client_writing` (WF-17 reminder always fires)
- task-type routes to Deepseek/Groq AND --pii flag is set

### What happens when Claude dissents
1. Dissent written to `dissent_log.md` with reason and task instructions
2. Telegram alert sent to Commander immediately
3. Task still written to `claude_inbox.md`
4. **Claude executes the task** — dissent is a flag, never a veto
5. Output includes a prominent dissent notice at the top

### What Commander does with a dissent
- Review `dissent_log.md` and the output in `claude_output.md`
- If concern is valid: intervene before output leaves the wing
- If concern is false positive: no action needed — task completed correctly

---

## FILES INVOLVED

| File | Purpose |
|------|---------|
| `claude_inbox.md` | Task written here — Claude reads on trigger |
| `claude_output.md` | Claude writes completed work here |
| `commander_review_log.md` | Every task logged here — Commander visibility |
| `dissent_log.md` | Dissent entries logged here |

---

## AFTER GOOSE SUBMITS A TASK

Goose must tell Commander (or Claude directly if in a shared session):

> **"Read your inbox and execute"**

Claude will read `claude_inbox.md`, execute the most recent task,
and write output to the specified `output_destination`.

---

## EXAMPLE: FULL WORKFLOW

```
# Step 1: Goose submits task
python3 goose_tasker.py \
  --task-type strategic \
  --instructions "Review the Phase 3 spec and identify the 3 highest-risk items
                  before Commander's Japan departure April 10. Cross-reference
                  against japan_departure_checklist.md." \
  --context-files "OpsCenter/collaboration/phase3_spec.md,
                   OpsCenter/collaboration/japan_departure_checklist.md" \
  --priority HIGH

# Output:
# [goose_tasker] Task GT-20260330-1800-STRA → QUEUED
# {task_id, status, inbox, output_dest}

# Step 2: Commander or Goose triggers Claude
# "Read your inbox and execute"

# Step 3: Claude reads inbox + context files, executes, writes to claude_output.md

# Step 4: Commander reviews claude_output.md
```

---

## STANDING DIRECTIVES CHECKED (Claude verifies all tasks against these)

1. Never send email outside the wing without Commander approval
2. Never create drafts in johnloucks3@gmail.com
3. Never use Love Group Travel branding
4. Never route PII tasks to Deepseek or Groq
5. Never commit to git without Commander approval
6. Never send client-facing output without WF-17 gate
7. Deepseek is arbitrator — never route arbitration to Claude or Goose
8. Goose does not touch 03_CLAUDE_MAX_QUEUE.json or thunderbird_model_router.py

---

## TROUBLESHOOTING

**"Task type not permitted" error**
→ Check spelling. Use --dry-run to preview before submitting.

**Dissent fires unexpectedly**
→ Check instructions for trigger keywords. Rephrase if the task is legitimate.
   Example: "draft email" is fine. "send email" triggers dissent.

**Task in inbox but Claude not executing**
→ Trigger Claude: "Read your inbox and execute"

**Output not appearing**
→ Check output_dest path. Default is collaboration/claude_output.md.

---
*goose_tasker.py v1.0 | Dreams2Memories Travel, LLC | 2026-03-30*
