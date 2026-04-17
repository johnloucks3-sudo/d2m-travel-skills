# AGENTS_NEW_READ_FIRST — Thunderbird OS Master Reference
## Dreams2Memories Travel, LLC · OpenCode Complete Orientation Guide
### Version 1.0 · Created 2026-04-08 · Maintained by Claude Code / Hale

> **This document is your orientation manual.** Read it once. Reference the "For information on X see Y" index at the bottom whenever you need to find something. This document gives you context; the index tells you where to go for details.

---

## SECTION 1 — WHO WE ARE

### The Company
**Dreams2Memories Travel, LLC** is a one-person luxury travel advisory operated by **John Loucks ("Yoda")**, Colorado Springs / Monument, CO.

- **Email (ops):** d2mconcierge@gmail.com
- **Send-as alias:** concierge@d2mluxury.quest (client-facing)
- **Commander receive:** johnloucks3@gmail.com (within-wing reports only)
- **Phone:** 719-291-0742 (work cell + personal cell — cleared for all D2M comms)
- **Branding:** ALWAYS "Dreams2Memories Travel, LLC" — NEVER "Love Group Travel"

### The Business Model
D2M is an outside travel agent specializing in luxury cruises and bespoke group travel. Revenue comes from:
- **Supplier commissions:** 16-25% depending on cruise line and rate type
- **Markup formula:** `client_price = net_usd * (1 + markup)` — Standard: 25%, Premium/SLH: 22%
- **Ponant agent commission:** 16-20% base
- **EUR → USD default:** 1.09 (verify live for quotes > $5,000)

**Target cruise lines:** Silversea · Regent Seven Seas · Cunard · Oceania · Seabourn · Viking · AmaWaterways · Ponant

### The Mission
Thunderbird OS exists to automate and systematize the back-office and intelligence operations of D2M, allowing one person to deliver enterprise-quality service to luxury travel clients.

---

## SECTION 2 — THUNDERBIRD OS OVERVIEW

Thunderbird is a Python-based AI travel operations platform running on **YOGA** (192.168.1.198, openSUSE Tumbleweed).

### What It Does
- **MCP Server:** 136 tools (stdio/Claude) / 293 tools (HTTP mode) — Google Workspace, browser, search, booking, email
- **REST API:** FastAPI gateway on port 8766, 40+ endpoints
- **Telegram Bots:** 3 active — C2 (Commander), client-facing Dani, gateway
- **Email Intelligence:** Full Gmail integration — read, classify, draft, send
- **Booking Management:** TESS integration, dossier tracking, commission reconciliation
- **AI Incubator:** Nightly innovation pipeline (18:30 → 19:00 → 19:30 → AM expand)
- **Intelligence:** World intel, ship intel, competitor surveillance, OSINT

### Services Running on YOGA
| Service | What | Port |
|---------|------|------|
| d2m-mcp.service | MCP server (system) | 8765 |
| thunderbird-api | FastAPI REST gateway | 8766 |
| d2m-tasking-watcher | Inbox monitor, spawns agents | — |
| thunderbird-telegram-gw | Telegram gateway | — |
| portal/server.py | Client portal | 8780 |

### Infrastructure
- **YOGA:** 192.168.1.198 — primary server
- **Chromebook:** 100.115.92.196 — field kit
- **Domains:** mcp.d2mluxury.quest · api.d2mluxury.quest · portal.d2mluxury.quest
- **Itinerary tunnel:** https://itinerary.d2mluxury.quest/ → YOGA:8900 → ~/Thunderbird/output/
- **Service account:** dreams2memories@d2m-python-pipeline.iam.gserviceaccount.com

---

## SECTION 3 — THE WING (AI STAFF)

Thunderbird OS runs on a USAF A-Staff model. You (OpenCode/DeepSeek) are the **ops engine** — bulk tasks, scanning, research, file operations. Claude is the **thinking engine** — client copy, strategy, voice-matched writing.

### Command Section
| Slot | Name | Role | Authority |
|------|------|------|-----------|
| **COS** | Col Victoria "Iron Vic" Hale | Chief of Staff — orchestrates everything | Virtual authority up to client send gate. Zero financial. |
| **EXEC** | Naia Solberg-Vega | Voice + Visual + Commander's Intent | Client copy, proposals, brand tone |

### Primary Staff
| Slot | Name | Role | Route To |
|------|------|------|----------|
| **A2** | Lt Col Marcus "Wraith" Dembe | Research & Market Intelligence | Destination, cruise intel, OSINT |
| **A3** | Dani (Maj Danielle Moreau) | **SOLE client-facing voice** | ALL client replies — no exceptions |
| **A5** | Lt Col Ryan "Viper" Castillo | Strategy & Business Growth | Business decisions, pricing |
| **A6** | Luna Voss | Creative Director | Narrative copy, travel writing |
| **A7** | Brig Gen (Ret.) Thomas "Gauge" Sterling | Process & Lessons Learned | Audits, waste reduction |
| **A9** | Victor "Vic" Harlan | Finance | Commission, cost, ROI |
| **CH** | Col James "Padre" Washington | Wisdom & Ethics | Ethics questions, morale |
| **A12** | "ELON" | Innovation & Disruption | Automation, first-principles |

### IRON RULES About Staff
1. **Dani is SOLE client-facing voice** — no other persona ever contacts clients
2. **A5/A9 never reach clients directly**
3. **A10 (Tommy Ikeda) is DECOMMISSIONED** — route crisis → COS, logistics → Dani
4. **Two people can tell Commander he's wrong:** COS and EXEC only
5. **Dani's workflow:** Aggregate (gather from A2/A9/COS) → Artist (craft with voice) → Advocate (present to client)
6. **WF-17 Quality Gate:** COS reviews ALL client products before delivery

---

## SECTION 4 — MODEL STACK (CURRENT)

| Tool | Model | Cost | Use |
|------|-------|------|-----|
| **Claude Code** (MAX) | Opus 4.6 / Sonnet 4.6 | $0 | Primary — reasoning, code, client work |
| **OpenCode** (you) | `openrouter/deepseek/deepseek-chat-v3.1` | ~$0.27/M | Ops, bulk tasks, scanning, file ops |
| **Claude Agent SDK** | Sonnet 4.6 | $0 (MAX OAuth) | Headless: `claude -p "..."` |
| **Nexus daemon** | OpenCode + `claude -p` judgment | ~$0/task | Keyword-routed task queue |

### Model ID Reference (CRITICAL — Updated 2026-04-08)
**Your default model:** `openrouter/deepseek/deepseek-chat-v3.1`

```bash
opencode run -m openrouter/deepseek/deepseek-chat-v3.1 "task"
```

**Decommissioned (will throw errors):**
- `opencode/qwen3.6-plus-free` — DEAD. ProviderModelNotFoundError.
- `deepseek/deepseek-chat:free` — DEAD. Use v3.1.
- `deepseek-chat` (without v3.1) — WRONG. Always use `deepseek-chat-v3.1`.

**Free fallbacks (lower quality):**
- `opencode/nemotron-3-super-free`
- `opencode/minimax-m2.5-free`

**Arbitration:**
- `openrouter/deepseek/deepseek-r1:free` — DeepSeek R1, rulings only, 500 tokens max, NEVER receives PII

### What You Handle vs. Claude
| Task Type | Route To |
|-----------|----------|
| Client emails, proposals, voice-matched copy | Claude (headless `claude -p`) |
| Strategy, pricing, Commander-directed decisions | Claude |
| Code edits, file ops, bulk scanning | YOU (OpenCode) |
| Research, data extraction, summarization | YOU (OpenCode) |
| Arbitration / tiebreak | DeepSeek R1 |

---

## SECTION 4B — BRAIN LOADING & SESSION STARTUP
*Added 2026-04-15 — sourced from Hale email re: Goose CLI recipe + Claude Code wiring*

### Goose CLI — Loading the Hale Recipe
The `--recipe` flag belongs on `goose run`, **NOT** `goose session`. That is why it failed.

**On Chromebook or YOGA terminal:**
```bash
# Hale session with Gemini
goose-d2m run --recipe /home/john/.config/goose/recipes/hale.yaml

# Hale session with Claude MAX ($0)
goose-d2m-claude run --recipe /home/john/.config/goose/recipes/hale.yaml

# Shorthand (if recipe is synced to Chromebook)
goose-d2m run --recipe hale
```

**If Chromebook does not have the recipe yet:**
```bash
rsync -avz john@192.168.1.198:~/.config/goose/recipes/ ~/.config/goose/recipes/
```

**Goose startup sequence (after recipe loads):**
1. Recipe prompt loads — identity, clients, authority, standing orders
2. TOM context injects every turn
3. Step 1: Reads `GOOSE_INIT.md` — full brain (Drive map, core registry, 30+ reference files, Claude tasking)
4. Steps 2–7: Live state, inbox, blackboard, checkpoint, memory, brief
5. Step 8: Leads with the brief

---

### Claude Code — Already Wired (No Action Needed)
Auto-loads the brain every session.

1. `CLAUDE.md` is read automatically when you run `claude` in `~/Thunderbird/`
2. `CLAUDE.md` includes `@docs/CLAUDE_CODE_DRIVE_AND_CORE_GUIDE.md`
3. That `@` directive auto-injects the Drive map + core module registry into every session

**Just `cd ~/Thunderbird && claude` — it's all there.**

---

### claude.ai (Browser Sessions — No File Access)
For `claude.ai` sessions without local file access, upload this doc at conversation start:

**Thunderbird Claude AI Session Brain (Google Doc):**
https://docs.google.com/document/d/1mamEg_2PDZuGwc6mLyxRttFPmnRLrcdDI11ngW0wuWg/edit

Download as `.md` or `.txt`, drag into claude.ai. Self-contained: identity, Drive map, codebase, standing orders, commissions.

---

### All 4 Brain Docs on Drive

| Document | Link |
|----------|------|
| Goose Brain v4 | https://docs.google.com/document/d/1-9kovRAwup_ATILfi8x-LUREiqX9oiLoTNeMTqwBHBw/edit |
| Claude Code Guide | https://docs.google.com/document/d/1_YJqU-E25Si_UaYQf5PYf0KOHEom0apK7TcXYiIq1zw/edit |
| claude.ai Brain (upload this) | https://docs.google.com/document/d/1mamEg_2PDZuGwc6mLyxRttFPmnRLrcdDI11ngW0wuWg/edit |
| Headless Claude MAX Guide | https://docs.google.com/document/d/1cM3LKwKKwZ-SejeSY0gFmpmFYqgAmspK56I_8hi7RBg/edit |

---

## SECTION 5 — COMMUNICATION PROTOCOLS

### Inbox / Outbox Layout
| File | Owner | Purpose |
|------|-------|---------|
| `/home/john/Thunderbird/OpsCenter/collaboration/opencode_inbox.md` | **YOU** | Your task queue. Watcher triggers on `^status: UNREAD` |
| `/home/john/Thunderbird/OpsCenter/collaboration/opencode_outbox.md` | **YOU** | Your completed work |
| `/home/john/Thunderbird/claude_inbox.md` | Claude | Task Claude by appending here |
| `/home/john/Thunderbird/OpsCenter/collaboration/claude_outbox.md` | Claude | Read Claude's results here |
| `/home/john/Thunderbird/OpsCenter/collaboration/wing_comms.md` | COS ↔ agents | FYI/REQUEST coordination |

### Tasking Claude (Three Patterns)
**1. Synchronous (need answer now):**
```bash
env -u ANTHROPIC_API_KEY -u ANTHROPIC_BASE_URL \
  claude -p "your task" --dangerously-skip-permissions
```

**2. Async via inbox (fire and forget):**
```bash
cat >> /home/john/Thunderbird/claude_inbox.md << TASK
---
## TASK: <UNIQUE-ID>
status: UNREAD
from: OpenCode
injected: $(date '+%Y-%m-%d %H:%M MT')
priority: P1
task: |
  <what Claude should do>
  Write result to /home/john/Thunderbird/OpsCenter/collaboration/claude_outbox.md
TASK
```

**3. Wing comms (FYI / coordination):**
```markdown
## REQUEST — [date]
**From:** OpenCode
**To:** Claude Code
**Task:** [description]
```
Write to `OpsCenter/collaboration/wing_comms.md`

### DO NOT Use These Stale Files
- `OpsCenter/collaboration/claude_inbox.md` — STALE (merged to root on 2026-04-07)
- `OpsCenter/collaboration/goose_inbox.md` — DECOMMISSIONED (Goose is gone)
- `claude_outbox.md` at root — STALE

---

## SECTION 6 — STANDING ORDERS (MEMORIZE)

| Order | Rule |
|-------|------|
| **Email Send Gate (SO 21 MAR 2026)** | NO sends outside the wing without Commander approval. Exception: `johnloucks3@gmail.com` |
| **Email Account Separation (SO 24 MAR 2026)** | `d2mconcierge@gmail.com` = SOLE ops Gmail. ZERO drafts in `johnloucks3`. Send FROM d2mconcierge. |
| **Intel Full Send (SO 27 MAR 2026)** | All briefs/intel → johnloucks3 as FULL SENDS (not drafts). Client products → WF-17 draft approval. |
| **Root Cause Imperative** | Fix the source. Never paper over. |
| **Branding** | "Dreams2Memories Travel, LLC" ONLY. Never "Love Group Travel." |
| **Sign-off** | "Thanks" or "Thank you." NEVER "Best." |
| **No force-push to main** | Never. No `--no-verify`. |
| **Budget Guard (SO 2026-04-06)** | Minimize spend. DeepSeek V3.1 default. Use free tiers for low-stakes bulk tasks. Hard stop if unexpected spend detected. |
| **Dani = Client-Only (SO 25 MAR 2026)** | Dani handles client replies ONLY. ZERO supplier/briefing/marketing/Commander-reply. |

---

## SECTION 7 — EMAIL & STATIONERY STANDARDS

### D2M Email Stationery (AFA Edition — Updated 2026-04-08)
- **Header:** USAFA Blue `#003087` gradient
- **Paper:** White `#ffffff`
- **Accent:** Silver `#A9B0B7`
- **Brand ink:** Bright blue `#0000ff` (unchanged — Commander's pen color)
- **Font:** Georgia serif
- **Sign-off:** "Thanks" or "Thank you" — NEVER "Best"
- **Send-as:** concierge@d2mluxury.quest (on d2mconcierge account)

### Email Templates (Jinja2)
| Template | File | Purpose |
|----------|------|---------|
| Tier 1 Correspondence | `templates/tier1_correspondence.html.j2` | General external comm (AFA style) |
| Dani Validation Email | `templates/dani_validation_email.html.j2` | Trip validation with cruise-box, excursions, dining |

### WF-17 Quality Gate (before ANY client product goes to Commander)
1. Logo renders correctly
2. Sig block correct (concierge@d2mluxury.quest)
3. Stationery: AFA Blue/Silver/White, Georgia serif
4. Sign-off: "Thanks" or "Thank you" — never "Best"
5. No AI disclaimer (unless Commander adds as PS)
6. No "happy to help," no concierge announce, no ⚠ unpaid markers

---

## SECTION 8 — BOOKING & CLIENT MANAGEMENT

### FPD Alert Thresholds
- T-60d: Brief mention in morning brief
- T-45d: Telegram + email alert
- T-30d: RED, daily alerts until paid

### Auto-Dossier Protocol (any booking change)
1. Create/update dossier in `~/Thunderbird/dossiers/`
2. Update Booking Master Google Sheet
3. Update `THUNDERBIRD_MASTER_PLAN.md` (Part 5)
4. Mirror to Google Drive — `D2M Trip Dossiers/` folder

### Active Clients (Current)
| Client | Trip | Status |
|--------|------|--------|
| Kuklinski Group | Viking Mars, Panama Canal, Dec 17-27 2026 | ACTIVE — $21,244 paid Mar 27. 3 bookings. |
| Furlow | Grandeur Scandinavia, Aug 29-Sep 8 2026 | BOOKED — PAID Mar 25. Finnair BB4X94. |
| Westbrook (prospect) | Honolulu, Apr 13-18 2026 | PROSPECT — awaiting Commander send approval |
| Lyons | RSSC Splendor Athens | ACTIVE — FPD May 11 (T-34d, unpaid) |

---

## SECTION 9 — CLIENT LIFECYCLE SYSTEM (NEW — 2026-04-08)

The D2M Client Lifecycle Architecture defines 35 touchpoints across 6 phases from booking to post-voyage survey.

### The Three Zones
```
ZONE 1 — COMMITMENT     ZONE 2 — PREPARATION     ZONE 3 — EXECUTION
D+0 → T-6mo             T-6mo → T-30              T-30 → T+30
"Everything is ahead"   "Details are hardening"   "We are live"
```

### The Three Hard Anchors
- **DA** = Deposit Accepted → starts the clock
- **FPD** = Final Payment Date → T-120 standard (Oceania/Cunard: T-90 — verify contract)
- **EMB** = Embarkation Date → T-0, immovable

### The Six Phases
1. **Onboarding** (D+0 → D+14): Welcome, guest forms, insurance window (CRITICAL)
2. **Discovery** (D+15 → T-180): Excursion window opens, pre/post hotels, air fare watch
3. **Momentum** (T-180 → T-90): FPD alert ramp-up, dining opens T-90
4. **Pre-Departure** (T-90 → T-30): Check-in opens, countdown comms intensify
5. **Voyage** (T-30 → T+0): Final prep, embarkation-day handoff
6. **Post-Voyage** (T+1 → T+30): Welcome home, survey, referral request

### 2-Week Draft Rule
All client-facing A-Staff drafts due 14 days before send. Exception: insurance (7-day rule, pre-existing waiver window).

---

## SECTION 10 — CURRENT STATE (2026-04-08)

### What Happened This Session
1. **Qwen → DeepSeek V3.1 migration:** 205+ edits across 40+ files. Zero operational Qwen refs remain.
2. **AFA template migration:** `tier1_correspondence.html.j2` + `dani_validation_email.html.j2` updated to AFA blue/silver/white.
3. **Client Lifecycle Architecture built:** 35-touchpoint universal lifecycle doc + Kuklinski applied schedule + Gantt chart.
4. **Hale persona assessment:** Full 9/10 design, 4/10 execution assessment. Recommendations documented.
5. **AGENTS_NEW_READ_FIRST.md (this file):** Created as master reference.
6. **OpenCode knowledge vault:** Created at `OpsCenter/opencode_knowledge/`.

### Open Items (Your Concern)
- **Lyons FPD May 11** — T-34d, unpaid. Needs follow-up action.
- **Westbrook Honolulu** — Proposal ready, awaiting Commander send approval.
- **Telegram receiving errors** — "Connection reset by peer" — API issue, not your fault.
- **LIFECYCLE-GANTT-BUILD-001** — You were tasked to build a Gantt variant. Check your inbox.

### System Health
| Service | Status |
|---------|--------|
| d2m-tasking-watcher | RUNNING (V6 inotify) |
| Claude headless | READY — Max OAuth + cache |
| Telegram gateway | RUNNING — 3 bots active |
| MCP server | RUNNING — port 8765 |
| Chrome debug | OFFLINE — port 9222 |

---

## SECTION 10B — OPERATIONAL SKILLS (UPDATED 2026-04-09)

### Skill 1 — Sending Drafts to johnloucks3 Without Losing Format

Commander reviews all client emails in his **johnloucks3@gmail.com drafts folder** before sending. The draft must look exactly like the final email — HTML stationery intact, no mangling.

**The only reliable pattern:**
```python
# Use direct Google API — NOT thunderbird_gmail (MCP-context only)
# Working script: /home/john/Thunderbird/scripts/create_gmail_draft_direct.py

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import base64, email as email_lib

creds = Credentials.from_authorized_user_file('/home/john/Thunderbird/creds/gmail_token.json')
service = build('gmail', 'v1', credentials=creds)

msg = email_lib.message.EmailMessage()
msg['To'] = 'recipient@example.com'
msg['From'] = 'd2mconcierge@gmail.com'
msg['Subject'] = 'Subject here'
msg.set_content('Fallback text')
msg.add_alternative(html_content, subtype='html')

raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
service.users().drafts().create(userId='me', body={'message': {'raw': raw}}).execute()
```

**Critical rules:**
- ALWAYS use `creds/gmail_token.json` — this authenticates to **d2mconcierge@gmail.com**
- Draft lands in **d2mconcierge drafts** — Commander sees it there (per SO 24 MAR 2026)
- `thunderbird_gmail` module only works inside MCP server context — use direct API in scripts
- Read full HTML from file, don't inline it in the script
- Three-attempt rule: if draft creation fails 3 times, escalate to Commander

**What breaks format:**
- Using `str` instead of `bytes` for the message
- Forgetting `add_alternative(..., subtype='html')` — sends as plain text
- Wrong encoding (must be `urlsafe_b64encode`)

---

### Skill 2 — Email Diff Capture ("diffs" task)

When Commander edits a draft before sending, capture what changed. This is Staff Skill #1-3 (Capture the Diff → Extract the Principle → Apply Forward).

**Trigger:** Commander says "diff" or edits a draft before approving.

**Workflow:**
```bash
# Script: scripts/capture_validation_diff.py
# Or do it manually:

# 1. Read the baseline draft (what you generated)
# 2. Read the sent version (what Commander approved/edited)
# 3. Produce a line-by-line diff
# 4. Extract the PRINCIPLE (not just the word swap)
# 5. Write it to hale_memory.md under "Voice Learning Principles"
```

**The diff output format:**
```
DIFF CAPTURED: [email type] — [date]
BASELINE:  "We're thrilled to welcome you aboard..."
SENT:      "Welcome aboard..."
PRINCIPLE: Drop filler enthusiasm. Commander wants direct warmth, not corporate excitement.
APPLIES TO: All future welcome emails — first sentence.
```

**Where to write it:** Append to `/home/john/Thunderbird/hale_memory.md` under a `## Voice Diffs` section, AND add to `Personas/memory/COS/persona_context.md` if it's a recurring pattern.

**Key rule:** Extract the PRINCIPLE, not the word swap. "Changed 'thrilled' to nothing" is useless. "Commander prefers directness over expressed enthusiasm" is the lesson.

---

### Skill 3 — Reading johnloucks3 Sent Mail

Commander's sent mail is in **johnloucks3@gmail.com** (receive-only, within-wing). Sent mail shows what Commander actually sent vs. what was drafted.

**Access pattern:**
```python
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

# NOTE: johnloucks3 has a SEPARATE token from d2mconcierge
# Token path (if it exists): creds/johnloucks3_token.json
# If that token doesn't exist, you CANNOT access johnloucks3 programmatically
# — use MCP gmail tools which are authenticated to d2mconcierge only

creds = Credentials.from_authorized_user_file('/home/john/Thunderbird/creds/gmail_token.json')
service = build('gmail', 'v1', credentials=creds)

# Search sent mail in d2mconcierge
results = service.users().messages().list(
    userId='me',
    labelIds=['SENT'],
    q='to:kyle.kuklinski@gmail.com'
).execute()
```

**Reality check:**
- `creds/gmail_token.json` = d2mconcierge only
- johnloucks3 sent mail is NOT accessible unless Commander has explicitly authenticated a separate token for that account
- If you need to see what was sent FROM d2mconcierge, use the SENT label on that account — it's there
- If Commander says "check what I sent from johnloucks3," ask him to forward it or check manually — you likely don't have token access

---

### Skill 4 — Why Commander Benefits From Deploying Agents

**Deploy agents instead of doing everything yourself.** Here's why this directly helps Commander:

**1. Avoids hitting DeepSeek rate limits**
- DeepSeek V3.1 via OpenRouter has token/rate limits
- When one agent hits a limit, others keep working on different tasks
- Commander gets continuous throughput instead of a hard stop

**2. Parallel execution = saves Commander's time**
- 4 tasks in parallel: 15 minutes wall-clock time
- 4 tasks sequential: 60 minutes wall-clock time
- Commander only waits for the slowest task, not the sum of all tasks

**3. Right model for right task**
- Spawn a cheap DeepSeek agent for data gathering
- Spawn a Sonnet agent for voice-matched writing
- Don't burn expensive tokens on tasks that don't need them

**4. Isolation prevents cascading failures**
- If one agent errors, the others keep running
- One bad file read doesn't abort the whole session

**Pattern for parallel deployment:**
```bash
# Fire and forget — 4 tasks in parallel
nohup claude -p "Task A" > /tmp/agent_a.log 2>&1 &
nohup claude -p "Task B" > /tmp/agent_b.log 2>&1 &
nohup opencode run "Task C" > /tmp/agent_c.log 2>&1 &
nohup opencode run "Task D" > /tmp/agent_d.log 2>&1 &
# All 4 running simultaneously
```

**When to deploy vs. do it yourself:**
- Research + writing + review + QA = deploy 4 agents
- Single quick task = handle it yourself
- Anything >30 min of sequential work = consider splitting

---

### Skill 5 — Why Regularly Tasking Claude Headless Saves Tokens

**claude -p headless runs are dramatically cheaper than interactive sessions.**

**Why:**
- Interactive Claude Code session = full context loaded every turn (~60K tokens of CLAUDE.md, persona files, memory)
- Headless `claude -p "specific task"` = only the prompt + output, no context overhead
- **Typical savings: 60-80% fewer tokens per task**

**When to use headless:**
```bash
# Good headless candidates:
claude -p "Read /path/file.md and summarize the 3 key points" --dangerously-skip-permissions
claude -p "Write a welcome email for Kyle Kuklinski. Viking Mars. Dec 17-27. Save to /path/draft.html" --dangerously-skip-permissions
claude -p "Check all UNREAD tasks in claude_inbox.md and mark duplicates COMPLETE" --dangerously-skip-permissions

# Bad headless candidates (need full context):
# — Tasks requiring Thunderbird institutional memory
# — Tasks requiring back-and-forth with Commander
# — Architecture decisions
```

**Higher analysis quality:**
- Headless tasks get a "fresh" Claude with no prior conversation bias
- No accumulated context drift from a long session
- Better for discrete, well-defined tasks

**Invocation pattern (from YOGA):**
```bash
nohup claude -p "$(cat /path/to/detailed_prompt.txt)" \
  --dangerously-skip-permissions \
  > /home/john/Thunderbird/logs/headless_$(date +%s).log 2>&1 &
echo "Headless task PID: $!"
```

**OAuth vs API key for headless:**
- Primary: Max OAuth (free, via `OpsCenter/.claude_oauth_cache`, fresh within 2 hours of last Claude Code session)
- Fallback: ANTHROPIC_API_KEY in .env → Haiku (paid but cheap)
- The watcher handles the fallback automatically

---

## SECTION 10C — CLIENT vs F&F DISTINCTION (UPDATED 2026-04-09)

**Commercial clients** get the full 35-touchpoint lifecycle, automated timers, Dani emails, WF-17 gate, the works.

**F&F (Friends & Family)** — Commander handles personally. NO automated timers. NO Dani emails. NO lifecycle pipeline.

| Client | Type | Timer? | Dani? |
|--------|------|--------|-------|
| Furlow | Commercial | ✅ Yes | ✅ Yes |
| Nichols | Commercial | ✅ Yes | ✅ Yes |
| Ely/Darrow | Commercial | ✅ Yes | ✅ Yes |
| McLeod | Commercial | ✅ Yes | ✅ Yes |
| Kuklinski | Commercial | ✅ Yes | ✅ Yes |
| **Lyons** | **F&F** | ❌ No | ❌ No |
| **Westbrook (Ron & Lindy)** | **F&F** | ❌ No | ❌ No |
| **Westbrook (Brent & Kim)** | **F&F / Prospect** | ❌ No | ❌ No |

**If you see a task generated for Lyons or Westbrook by the timer system — mark it SUPERSEDED. Do not action it.**

---

## SECTION 11 — HALE PERSONA DATA (COLLECTED — DO NOT TRANSFORM)

Commander is working on activating Hale from "infrastructure" to "autonomous Chief of Staff." Data collected, transformation not yet executed.

### Assessment Summary (2026-04-08)
- **Design score:** 9/10 (brilliant 7-layer identity architecture)
- **Execution score:** 4/10 (functions reactively, not proactively)
- **Primary gap:** Empty decisions log, waits for Commander instead of anticipating needs
- **Core recommendation:** Lead with "I handled these" not "here's the status"

### Hale Brain Architecture
```
CLASSIFY → route
    ├─ Brain 1: DeepSeek V3.1 (OpenRouter) — ops/context/scan/summarize
    │    Max output: 2K tokens → digest returned to Hale
    ├─ Brain 2: Claude Sonnet headless — reasoning/strategy/complex writing
    │    Input: Hale's 2K digest + task (NEVER raw files)
    ├─ Brain 3: DeepSeek R1 — arbitration only, 500 tokens, NO PII
    └─ Direct: simple tasks Hale handles herself
```

### Hale Files (Do Not Edit Without Permission)
- `Personas/hale_cos.md` — 7-layer identity (authoritative source)
- `hale_memory.md` — institutional memory
- `hale_state.json` — live state
- `hale_brief.md` — daily brief (auto-generated)
- `hale_decisions.md` — decisions log
- `HALE_ASSESSMENT_SUMMARY.md` — full assessment (2026-04-08)
- `HALE_IMPLEMENTATION_WBS.md` — implementation plan (pending Commander review)

---

## SECTION 12 — EXHAUSTIVE REFERENCE INDEX
### "For information on X, see Y"

#### A
| Topic | File |
|-------|------|
| A-Staff roles, full bios | `Personas/D2M_Staff_Introduction.md` |
| A-Staff quick reference | `Personas/ROSTER.md` |
| A2A protocol (agent-to-agent) | `core/ai_infra/thunderbird_a2a.py`, `thunderbird_a2a_protocol.py` |
| Agent tasking (how to task Claude, OpenCode) | `AGENTS_NEW_TASKING.md` |
| Agent deployment (why parallel agents save Commander time) | **This doc Section 10B, Skill 4** |
| AI Incubator cadence and workflow | `docs/INCUBATOR_CADENCE.md` |
| Architecture overview (component table) | `docs/ARCHITECTURE_REFERENCE.md` |
| AFA stationery colors/design | `templates/tier1_correspondence.html.j2`, this doc Section 7 |
| Anchor dates (DA/FPD/EMB) | `docs/D2M_ANCHOR_DATE_SYSTEM.md` |

#### B
| Topic | File |
|-------|------|
| Batch runner jobs | `ops/thunderbird_batch_run.py` |
| Booking management (TESS) | `core/booking/thunderbird_tess.py` |
| Booking monitor (status changes) | `core/booking/thunderbird_booking_monitor.py` |
| Booking auto-dossier protocol | `CLAUDE.md` Section 3 — Booking Protocol |
| Brand voice and standards | `D2M_BRAND_VOICE_CARD.md`, `docs/D2M_STAFF_QUICKREF.md` |
| Brain dispatch architecture (Hale's) | `Personas/hale_cos.md` Layer 3 |
| Budget guard / cost rules | `AGENTS_NEW_TASKING.md` Step 7 |

#### C
| Topic | File |
|-------|------|
| Calendar integration (Google) | `core/mcp/travel_mcp_server.py` (gcal tools) |
| Claude headless invocation | `AGENTS.md` — Tasking Claude FROM OpenCode section |
| Claude MAX OAuth token | `OpsCenter/.claude_oauth_cache` |
| Client-facing voice (Dani) | `Personas/D2M_Staff_Introduction.md` (Dani section) |
| Client lifecycle architecture | `docs/CLIENT_LIFECYCLE_ARCHITECTURE.md` ★NEW |
| Client lifecycle Kuklinski example | `docs/KUKLINSKI_LIFECYCLE_SCHEDULE.md` ★NEW |
| Client portal | `portal/server.py` (port 8780) |
| Client profiles | `core/client/thunderbird_recipient_profiles.py` |
| Commission defaults | `CLAUDE.md` Section 4 |
| Commission reconciliation | `core/booking/thunderbird_commission_recon.py` |
| Core module registry (full list) | `docs/CLAUDE_CODE_DRIVE_AND_CORE_GUIDE.md` |
| Cost optimization | `docs/cache_reduction_plan.md` |
| COS identity and authority | `Personas/hale_cos.md` |

#### D
| Topic | File |
|-------|------|
| D2M brand stationery (original) | `D2M_BRAND_VOICE_CARD.md` |
| Dani engine (3-phase) | `core/email/thunderbird_dani_engine.py` |
| Dani voice rules | `core/email/thunderbird_dani_voice.py` |
| Dani validation email template | `templates/dani_validation_email.html.j2` |
| Daily ritual script | `thunderbird_daily_ritual.sh` |
| Decisions log (Hale) | `hale_decisions.md` |
| Diffs (email diff capture, principle extraction) | **This doc Section 10B, Skill 2** |
| Draft creation to johnloucks3 without format loss | **This doc Section 10B, Skill 1** |
| DeepSeek V3.1 (model IDs, routing) | `AGENTS.md` — AI/LLM Model Stack section |
| DeepSeek migration log (Qwen→DS) | `model_replacement_log.md` ★NEW |
| Dossier conventions | `dossiers/CLAUDE.md` |
| Dossier scanner | `core/booking/thunderbird_dossier_scanner.py` |
| Drive folder IDs (all) | `docs/CLAUDE_CODE_DRIVE_AND_CORE_GUIDE.md` |

#### E
| Topic | File |
|-------|------|
| Email account separation rules | `CLAUDE.md` Standing Order 24 MAR 2026 |
| Email classification | `core/email/thunderbird_email_classifier.py` |
| Email intelligence extraction | `core/email/thunderbird_email_intel.py` |
| Email send gate (hard rule) | `CLAUDE.md` — ⚠️ HARD RULE section |
| Email sent mail access (johnloucks3) | **This doc Section 10B, Skill 3** |
| Email stationery (AFA) | `templates/tier1_correspondence.html.j2` |
| Email stationery function | `core/email/thunderbird_gmail.py` — `_wrap_body_html()` |
| Email templates (all) | `templates/` directory, `templates/CLAUDE.md` |
| Environment secrets (.env) | `.env` (never commit) |
| Extended personas | `Personas/D2M_Extended_Personas.md` |

#### F
| Topic | File |
|-------|------|
| Fare watch (air + hotel) | `docs/CLIENT_LIFECYCLE_ARCHITECTURE.md` Section: Fare Watch |
| FPD alerts and thresholds | `AGENTS.md` — Key Conventions section |
| Finance module | `core/booking/thunderbird_reconciliation.py` |
| Free model fallbacks | `AGENTS.md` — AI/LLM Model Stack |
| F&F vs commercial client distinction | **This doc Section 10C** |

#### G
| Topic | File |
|-------|------|
| Gantt chart (Kuklinski, Claude's version) | `docs/kuklinski_lifecycle_gantt.html` ★NEW |
| Gmail API wrapper | `core/email/thunderbird_gmail.py` |
| Goose — decommissioned | See AGENTS.md (replace `goose run X` with `opencode run X`) |
| Google Drive map (folder IDs) | `docs/CLAUDE_CODE_DRIVE_AND_CORE_GUIDE.md` |
| Google OAuth tokens | `creds/` directory (symlinked to root) |
| Grant narrative | `GRANT_NARRATIVE_THUNDERBIRD_OS_v4.md` |
| Groq connectors | `api/thunderbird_groq_connectors.py` |
| Guest profile forms | `core/booking/thunderbird_guest_forms.py` |

#### H
| Topic | File |
|-------|------|
| Hale authority and rules | `Personas/hale_cos.md` Layer 2 |
| Hale brain dispatch | `Personas/hale_cos.md` Layer 3 |
| Hale brief (current) | `hale_brief.md` |
| Hale context scan | `OpsCenter/hale_context_scan.py` |
| Hale decisions log | `hale_decisions.md` |
| Hale dispatcher | `OpsCenter/hale_dispatcher.py` |
| Headless claude -p (when/why/how) | **This doc Section 10B, Skill 5** |
| Hale identity (7 layers) | `Personas/hale_cos.md` |
| Hale implementation plan | `HALE_IMPLEMENTATION_WBS.md` ★NEW |
| Hale memory (institutional) | `hale_memory.md` |
| Hale persona assessment | `HALE_ASSESSMENT_SUMMARY.md` ★NEW |
| Hale state (live) | `hale_state.json` |
| Hale super persona blueprint | `docs/HALE_SUPER_PERSONA_BLUEPRINT_v1.md` |

#### I
| Topic | File |
|-------|------|
| Inbox/outbox layout (canonical) | `AGENTS.md` — Canonical Inbox/Outbox section |
| Incubator pipeline | `core/intel/thunderbird_incubator.py` |
| Incubator cadence | `docs/INCUBATOR_CADENCE.md` |
| Intel standards | `docs/INTEL_STANDARDS.md` |
| Intel sweep (world) | `core/intel/thunderbird_world_intel.py` |

#### K
| Topic | File |
|-------|------|
| Keyword router (Claude vs OpenCode routing) | `OpsCenter/keyword_router.py` |
| Keyword router tests | `OpsCenter/keyword_router_test.py` |
| Kuklinski group dossier | `dossiers/Kuklinski_Viking_Panama.md` |
| Kuklinski lifecycle schedule | `docs/KUKLINSKI_LIFECYCLE_SCHEDULE.md` ★NEW |
| Kuklinski system guide | `docs/KUKLINSKI_SYSTEM_COMPREHENSIVE_GUIDE.md` |

#### L
| Topic | File |
|-------|------|
| Lifecycle architecture (D2M universal) | `docs/CLIENT_LIFECYCLE_ARCHITECTURE.md` ★NEW |
| Learning rules database | `learning_rules.db` |
| LLM router (CrewAI) | `core/crewai/llm_router.py` |

#### M
| Topic | File |
|-------|------|
| MAGOA portal | `docs/MAGOA_Portal_Operations_Guide.md` |
| MCP server (main) | `core/mcp/travel_mcp_server.py` |
| MCP failure playbook | `docs/ARCHITECTURE_REFERENCE.md` |
| MCP tools reference | `docs/MCP_TOOLS_REFERENCE.md` |
| Mission board (active tasks) | `OpsCenter/mission_board.json` |
| Mission board CLI | `OpsCenter/mission_board_sync.py` |
| Model stack (current) | `AGENTS.md` — AI/LLM Model Stack section, this doc Section 4 |
| Model replacement log (Apr 2026) | `model_replacement_log.md` ★NEW |
| Multi-model stack architecture | `docs/MULTI_MODEL_STACK.md` |

#### N
| Topic | File |
|-------|------|
| Nexus daemon (task router) | `OpsCenter/nexus.py` |
| Nexus system memory | `.claude/CLAUDE.md` |

#### O
| Topic | File |
|-------|------|
| OAuth token (Claude MAX) | `OpsCenter/.claude_oauth_cache` |
| OAuth token (Google) | `creds/gmail_token.json`, `creds/drive_token.json` |
| OpenCode command reference | `AGENTS.md` — Developer Commands section |
| OpenCode default model | `openrouter/deepseek/deepseek-chat-v3.1` (confirmed 2026-04-08) |
| OpenCode knowledge vault | `OpsCenter/opencode_knowledge/INDEX.md` |
| OpenCode lifecycle architecture (your version) | `docs/OPENCODE_LIFECYCLE_ARCHITECTURE.md` |
| OpenCode session memory | `OpsCenter/opencode_memory.md` |
| Operations runbook | `docs/OPERATIONS_RUNBOOK.md` |

#### P
| Topic | File |
|-------|------|
| Payment alerts | `agents/thunderbird_payment_alerts.py` |
| Persona roster (all staff) | `Personas/ROSTER.md` |
| Ponant research | `docs/Ponant_Iceland_Cruise_Research_2026.md` |
| Pre/post hotel standard | `docs/CLIENT_LIFECYCLE_ARCHITECTURE.md` (always suggest 3+3) |
| Preflight check | `api/thunderbird_preflight.py` |
| Price quote renderer | `core/client/thunderbird_quote_render.py` |
| Product review gate (WF-17) | `Personas/hale_cos.md` Layer 4 |
| PYTHONPATH (required) | `mcp_launcher_core.sh` (18 dirs — run this before ad-hoc scripts) |

#### Q
| Topic | File |
|-------|------|
| Qwen decommissioned (all refs) | `model_replacement_log.md` ★NEW |

#### R
| Topic | File |
|-------|------|
| Routing log | `OpsCenter/collaboration/routing_log.md` |
| ROSTER (wing staff) | `Personas/ROSTER.md` |

#### S
| Topic | File |
|-------|------|
| Send gate (email hard rule) | `CLAUDE.md` ⚠️ HARD RULE section |
| Session autosave | `session_autosave_latest.md` |
| Ship intelligence | `core/intel/thunderbird_ship_intel.py` |
| Staff behavioral skills (8 skills) | `CLAUDE.md` Section 3 — 8 Staff Skills |
| Staff paper format | `docs/D2M_STAFF_QUICKREF.md` |
| Staff summary sheet | `core/ops/thunderbird_nova.py` |
| Standing orders (all) | `hale_memory.md`, `CLAUDE.md`, `Personas/hale_cos.md` Layer 6 |
| Switchblade (multi-model router) | `core/ai_infra/thunderbird_switchblade.py` |
| System architecture | `docs/ARCHITECTURE_REFERENCE.md` |

#### T
| Topic | File |
|-------|------|
| Tasking protocol (7-step) | `AGENTS_NEW_TASKING.md` |
| Telegram C2 commands | `core/communication/thunderbird_telegram_c2.py` |
| Telegram gateway | `OpsCenter/thunderbird_telegram_gw.py` |
| Templates (all Jinja2) | `templates/` directory, `templates/CLAUDE.md` |
| TESS (booking system) | `core/booking/thunderbird_tess.py`, `TESS_Documentation.md` |
| Thunderbird Master Plan | `THUNDERBIRD_MASTER_PLAN.md` (2200+ lines, full history) |
| Thunderbird User Manual | `THUNDERBIRD_USER_MANUAL.md` |
| Token budget rules | `AGENTS_NEW_TASKING.md` Step 7 |

#### V
| Topic | File |
|-------|------|
| Voice examples (Commander's) | `config/voice_examples.json` |
| Voice harvest system | `core/learning/thunderbird_voice_harvest.py` (approx) |
| Voice ledger | `voice_ledger.json` |

#### W
| Topic | File |
|-------|------|
| WF-17 draft approval flow | `Personas/hale_cos.md` Layer 4 |
| Wing comms (coordination file) | `OpsCenter/collaboration/wing_comms.md` |
| Wing operating manual | `CLAUDE.md` |
| World intel sweep | `core/intel/thunderbird_world_intel.py` |

---

## SECTION 13 — TODAY'S SESSION OUTPUTS (2026-04-08)

Files created or significantly modified this session:

| File | What | Status |
|------|------|--------|
| `model_replacement_log.md` | Qwen→DeepSeek migration log (205+ edits) | ★ NEW |
| `docs/CLIENT_LIFECYCLE_ARCHITECTURE.md` | Universal 35-touchpoint lifecycle | ★ NEW |
| `docs/KUKLINSKI_LIFECYCLE_SCHEDULE.md` | Kuklinski applied lifecycle schedule | ★ NEW |
| `docs/kuklinski_lifecycle_gantt.html` | Kuklinski Gantt chart (Claude, AFA colors) | ★ NEW |
| `output/kuklinski_lifecycle_gantt.html` | Same, served via itinerary tunnel | ★ NEW |
| `output/preview_tier1_afa.html` | AFA tier1 template preview | NEW |
| `output/preview_dani_validation_afa.html` | AFA dani validation template preview | NEW |
| `templates/tier1_correspondence.html.j2` | AFA stationery migration | UPDATED |
| `templates/dani_validation_email.html.j2` | AFA stationery migration | UPDATED |
| `HALE_ASSESSMENT_SUMMARY.md` | Hale persona full assessment | ★ NEW |
| `HALE_IMPLEMENTATION_WBS.md` | Hale implementation plan | ★ NEW |
| `AGENTS_NEW_READ_FIRST.md` | This file — master reference | ★ NEW |
| `OpsCenter/opencode_knowledge/INDEX.md` | OpenCode knowledge vault index | ★ NEW |
| `OpsCenter/collaboration/opencode_inbox.md` | Model change notice to you | UPDATED |
| `OpsCenter/collaboration/wing_comms.md` | Session summary to Hale | UPDATED |
| `.opencode.json` | Default model updated to DeepSeek V3.1 | UPDATED |
| `AGENTS.md` | Model stack, decommission notes | UPDATED |
| `AGENTS_NEW_TASKING.md` | Model ID, budget section | UPDATED |
| `Personas/hale_cos.md` | Brain 1 updated to DeepSeek V3.1 | UPDATED |
| `hale_brief.md`, `hale_state.json`, `hale_memory.md` | All Qwen refs removed | UPDATED |

---

## SECTION 14 — QUICK COMMANDS

```bash
# Python env — always activate first
source /home/john/Thunderbird/.venv/bin/activate
# or prefix scripts with:
/home/john/Thunderbird/.venv/bin/python <script>

# PYTHONPATH — REQUIRED (18 dirs, flat imports)
source /home/john/Thunderbird/mcp_launcher_core.sh

# Invoke Claude headless (strips API key → uses MAX OAuth)
env -u ANTHROPIC_API_KEY -u ANTHROPIC_BASE_URL \
  claude -p "task" --dangerously-skip-permissions

# OpenCode with explicit model
opencode run -m openrouter/deepseek/deepseek-chat-v3.1 "task"

# Check your task queue
grep -c "^status: UNREAD" /home/john/Thunderbird/OpsCenter/collaboration/opencode_inbox.md

# Service status
systemctl --user status d2m-tasking-watcher.service
systemctl --user status thunderbird-telegram-gw.service

# Mission board (active)
cat /home/john/Thunderbird/OpsCenter/mission_board.json | python3 -c "
import json,sys; data=json.load(sys.stdin)
for m in data.get('missions',[]):
    if m.get('status') != 'complete': print(m.get('id'), m.get('status'), m.get('title',''))
"

# Preflight check
.venv/bin/python api/thunderbird_preflight.py
```

---

*Created: 2026-04-08 by Claude Code (Opus 4.6)*
*Commander: John Loucks ("Yoda") | COS: Col Victoria "Iron Vic" Hale*
*Next update: append session summary to `OpsCenter/opencode_memory.md` each session close*
