# SPSA Quick Start — For Commander
## Standard Problem Solving Approach | Dreams2Memories Travel

---

## WHAT YOU GET

Every morning (0631 MT) and evening (1700 MT), your brief includes a new section:

```
## 🚨 SPSA CASES

### 🔴 RED — Blocking Operations
SPSA-20260502-25089 | MCP server offline
> Recommendation: Restart service (0.2h)

### 🟡 YELLOW — Requires Decision Today
SPSA-20260502-FC6AD | Authentication required: TESS
> Recommendation: Re-authenticate (0.15h)
```

**What it means:**
- RED cases block operations. You get a Telegram alert immediately + they appear in your brief.
- YELLOW cases need a decision today. They appear in the brief. No urgent alert.
- Each case shows a 1-line recommendation + estimated time to implement.

---

## WHEN YOU GET A RED ALERT (Telegram)

**Example:**
```
SPSA RED — SPSA-20260502-25089

CASE: SPSA-20260502-25089
SEVERITY: 🔴 RED
SOURCE: incubator

PROBLEM:
MCP server is offline — blocks all integrations

FACTORS:
• Detected in hale_state.json
• All MCP integrations blocked
• Client API calls will fail

RECOMMENDED ACTION:
Restart service — MCP is critical path. Fast recovery + debug after.

TIMELINE: 0.2h
RISK: Medium — blocks client-facing systems
```

**Your options:**
1. **"OK, restart it"** → COS executes immediately, reports back when done
2. **"Investigate first"** → COS digs into root cause, comes back with deeper analysis + options
3. **"Defer to morning"** → COS tracks case, you review in morning brief with full context

---

## WHEN YOU SEE A YELLOW IN YOUR BRIEF

**Example from morning brief:**
```
SPSA-20260502-FC6AD | Authentication required: TESS
> Recommendation: Re-authenticate (0.15h)
```

**Your decision options:**
1. **"Do it now"** → 15-minute task. COS runs it, reports completion.
2. **"Schedule it for [time]"** → COS schedules, notifies you when ready.
3. **"Find another way"** → COS explores alternatives (e.g., defer financial reporting, use cached data).

---

## KEY FEATURES

### ✅ All cases have a recommendation
You never get a problem without a suggested path forward. COS always walks through options and picks the best one.

### ✅ Risk-based urgency
- **LOW risk** (quick, reversible): Auto-executed, you hear after it's done
- **MEDIUM risk** (config change, user-facing): Telegram alert + your decision required
- **HIGH risk** (destructive, financial impact): Full SPSA brief + formal decision

### ✅ Timeline estimates
Every recommendation includes estimated time. Plan your day knowing "authenticate TESS is 15 min" vs "investigate MCP issue is 2 hours".

### ✅ Lessons captured
When cases close, COS records what was learned. These go into weekly reports so you see patterns.

---

## COMMAND REFERENCE

### Check current cases
**In your brief:** Morning brief shows all active RED + YELLOW cases at the top of the SPSA section.

**Full list:**
```bash
python3 -c "from core.ops.thunderbird_spsa import get_active_cases; [print(f'{c.case_id}: {c.severity} | {c.problem_statement}') for c in get_active_cases()]"
```

### View full case details
When you get a RED alert or see a case in the brief, get the full 7-step problem breakdown:

```bash
python3 -c "from core.ops.thunderbird_spsa import load_case; c = load_case('SPSA-20260502-25089'); print(c.to_brief())"
```

**Output:**
```
CASE ID: SPSA-20260502-25089
STATUS: OPEN
SEVERITY: RED

═══════════════════════════════════════════════════════════════

DEFINE THE PROBLEM
MCP_SERVER is offline — blocks all integrations

DISCUSS FACTORS BEARING ON THE PROBLEM
• Detected in hale_state.json at 2026-05-02T01:38:10
• All MCP integrations blocked
• Client API calls will fail

GENERATE OPTIONS FOR SOLUTION
1. Restart service — systemctl --user restart thunderbird-mcp.service
   Trade-off: 5 minutes, immediate recovery
2. Investigate root cause — Check service logs and systemd status
   Trade-off: 30+ minutes, addresses root cause

RECOMMEND A SOLUTION
Option Restart service is best because: MCP is critical path. Fast recovery + debug after.
Timeline: 0.2h | Risk: Medium — blocks client-facing systems

— Hale, COS | D2M Travel
```

### Approve a recommendation (shorthand)
When COS sends "Here's my recommendation for case SPSA-20260502-25089, shall I proceed?":

Just say **"Yes"** or **"Approved"** in Telegram. COS executes immediately.

### Explore alternatives for a case
Say: **"SPSA-20260502-FC6AD: What's the risk if we just skip re-authenticating TESS and use last month's data?"**

COS will analyze that option, show you the trade-off, and let you decide.

---

## WHEN YOU RETURN FROM ABSENCE

When you come back after being away:
1. **Morning brief** shows you current RED + YELLOW cases (active problems)
2. **Weekly deep dive** (Monday) shows you closed cases + what was learned
3. **Jump to "Latest SPSA cases"** section in Telegram for summary of what happened while you were gone

COS handles all YELLOW cases while you're away (LOW-risk auto-execute rule still applies). You'll see them summarized when you return.

---

## TYPICAL WORKFLOW

### Morning (0631 MT)
You read the brief. SPSA section shows 0-3 active cases.
- 1 RED case: Telegram has already alerted you (last night or this morning)
- 0-2 YELLOW cases: Await your decision during the day

### During day
As you decide on YELLOW cases, COS executes and reports back. Cases close as they complete.

### Evening (1700 MT)
EOD summary shows you: "2 cases resolved today, 1 new case flagged." (Coming in next phase)

### Monday morning (0700 MT)
Weekly deep dive: "4 cases closed this week. Lessons: [pattern analysis]" (Coming in next phase)

---

## WHEN TO USE "DEFER" OR "INVESTIGATE"

**Say "investigate" if:**
- Root cause isn't obvious from the brief
- You want to understand before deciding
- Same problem has happened before (want to know if it's fixed this time)

**Say "defer" if:**
- You're in the middle of something urgent
- The case isn't blocking clients yet
- You want to batch this with other decisions

**Say "do it now" if:**
- It's quick (<30 min)
- It unblocks other work
- You want it off the books today

---

## REFERENCE

- **Full system docs:** `docs/SPSA_SYSTEM_INTEGRATION.md`
- **Case examples:** Check `logs/spsa/` directory for JSON cases
- **This brief runs daily at:** 0631 MT (after 0630 intake scan)
- **RED alerts arrive via:** Telegram C2 (same channel as morning briefs)

---

*SPSA is your structured decision framework. Every problem gets options. Every option gets a recommendation. Every decision gets recorded.*

---

**Questions? Ask COS:** 
- "What are my options for case SPSA-20260502-25089?"
- "When do I need to decide on SPSA-20260502-FC6AD?"
- "Show me a summary of all RED cases from the last week"

---

*Last updated: 2026-05-02 | COS*
