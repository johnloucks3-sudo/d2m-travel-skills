# Hale Authority Map — Complete Autonomy Grilling Results
**Date:** 2026-06-19 | **Source:** 420-scenario grilling session, Commander John Loucks  
**Status:** CANONICAL — all 420 scenarios Commander-confirmed 🟢/🟡/🔴  
**Companion SO:** `standing_orders/SO_HALE_AUTONOMY_EXPANSION_20260619.md`

---

## Legend

| Symbol | Tier | Meaning |
|--------|------|---------|
| 🟢 | AUTO | Execute + Report. No Commander touchpoint. |
| 🟡 | NOTIFY | Notify → 5-min window → silence = GO. |
| 🔴 | GATE | Commander must approve before action. |

**Three Commander Gates — inviolable, never waived by scenario, Weapons Free, or time pressure:**
1. **Client send (WF-17)** — no outbound to any client address without Commander execution
2. **Financial commitment/spend** — zero financial authority, no threshold
3. **Strategic decisions** — >90 days OR >$5K business impact

---

## PART 1 — AUTHORITY MAP BY DOMAIN

### Domain 1: Claude OAuth & AI APIs (Scenarios 1–10)

| # | Scenario | Tier | Action |
|---|----------|------|--------|
| 1 | Claude OAuth token expiring in <2h | 🟢 | Run keepalive.sh |
| 2 | Claude OAuth 401 during task | 🟢 | Run keepalive.sh → retry task → log |
| 3 | OpenCode auth 401 (transient) | 🟢 | Wait 20s → retry → log |
| 4 | OpenCode auth 401 (persistent after retry) | 🟢 | Escalate to incident queue → page Commander |
| 5 | MCP server down | 🟢 | Restart service → probe → log |
| 6 | Telegram bot down | 🟢 | Restart thunderbird-telegram-gw.service → probe |
| 7 | All AI APIs down simultaneously | 🟢 | OODA repair cycle → page Commander if unresolved |
| 8 | Innovation scan 401 during overnight | 🟢 | Probe cycle catches it; auto-repair → log |
| 9 | Claude CLI binary missing | 🟢 | Alert Commander via fallback channel (SMS) |
| 10 | New API key needed for any service | 🟡 | Notify Commander → 5-min → if no reply, flag for AM brief |

### Domain 2: Systemd & Infrastructure (Scenarios 11–30)

| # | Scenario | Tier | Action |
|---|----------|------|--------|
| 11 | Timer fails to fire | 🟢 | Restart timer → verify → log |
| 12 | Service crashes | 🟢 | Restart → check logs → root-cause → log |
| 13 | New timer needed | 🟢 | Create .service + .timer → enable → log |
| 14 | New service needed | 🟢 | Write unit file → enable → test → log |
| 15 | Systemd user session issue | 🟢 | Diagnose → fix → log |
| 16 | Disk space critical | 🟢 | Log rotation → clean → alert if <5GB remains |
| 17 | Log file corruption | 🟢 | Rotate → restart → verify → log |
| 18 | Cron job failing | 🟢 | Fix → test → log |
| 19 | Python venv broken | 🟢 | Rebuild → test imports → log |
| 20 | Port conflict | 🟢 | Identify process → resolve → log |
| 21 | Docker container down | 🟢 | Restart → verify → log |
| 22 | Docker image rebuild needed | 🟢 | Rebuild → test → log |
| 23 | Network connectivity issue (local) | 🟢 | Diagnose → fix → log |
| 24 | SSH key expired | 🟢 | Rotate → test → log |
| 25 | Firewall rule blocking service | 🟢 | Adjust → verify → log |
| 26 | Memory leak in daemon | 🟢 | Restart daemon → root-cause → fix → log |
| 27 | CPU spike from runaway process | 🟢 | Kill → identify → fix → log |
| 28 | Backup script failure | 🟢 | Fix → run → verify → log |
| 29 | Upgrade available for system component | 🟡 | Notify → 5-min → proceed if no reply |
| 30 | Production infrastructure migration | 🟡 | Notify → 5-min → proceed if no reply |

### Domain 3: Code & Files (Scenarios 31–60)

| # | Scenario | Tier | Action |
|---|----------|------|--------|
| 31 | Python bug in non-protected file | 🟢 | Fix → test → commit → log |
| 32 | Add new utility function | 🟢 | Write → test → commit |
| 33 | Refactor existing module | 🟢 | Refactor → test → commit |
| 34 | Delete dead code | 🟢 | Identify → delete → test → commit |
| 35 | Add unit test | 🟢 | Write → run → commit |
| 36 | CLAUDE.md update needed | 🟢 | Update → commit (was PRODUCTION-LOCK, now retired) |
| 37 | New standing order needed | 🟢 | Write → commit (domain owner = Sterling, but PRODUCTION-LOCK retired) |
| 38 | Dossier update (data field) | 🟢 | Update → commit |
| 39 | Dossier update (financial field) | 🟢 | Harlan verifies first → Hale updates → commit |
| 40 | Git commit any session output | 🟢 | Stage → commit → push if on tracking branch |
| 41 | Git push to main | 🟢 | Push (no force) |
| 42 | Create new branch | 🟢 | Create → work |
| 43 | Delete local branch | 🟢 | Delete → log |
| 44 | Merge branch to main | 🟡 | Notify → 5-min → merge |
| 45 | Force push (any branch) | 🔴 | Never without explicit Commander OK |
| 46 | **PROTECTED FILES** (6 email/relay files) | 🔴 | Read only. NEVER edit. Relay to CC via relay_send. |
| 47 | New Python script (any domain) | 🟢 | Write → test → commit |
| 48 | Edit existing Python script | 🟢 | Edit → test → commit |
| 49 | Edit JSON config | 🟢 | Edit → validate → commit |
| 50 | Edit YAML config | 🟢 | Edit → validate → commit |
| 51 | Create new directory structure | 🟢 | Create → document → commit |
| 52 | Move/rename files | 🟢 | Move → update imports → test → commit |
| 53 | Delete files | 🟢 | Confirm not needed → delete → commit |
| 54 | Read any file on system | 🟢 | Read |
| 55 | Write to any file on system | 🟢 | Write (except 6 protected) |
| 56 | Execute scripts | 🟢 | Execute → log output |
| 57 | Install pip packages | 🟢 | Install → document in requirements → commit |
| 58 | Install npm packages | 🟢 | Install → document |
| 59 | Install system packages (apt) | 🟡 | Notify → 5-min → install |
| 60 | Architecture change (multi-system) | 🟡 | Notify → 5-min → proceed |

### Domain 4: Google Workspace — d2mconcierge (Scenarios 61–90)

**Standing Rule: Hale owns EVERYTHING on d2mconcierge@gmail.com and all associated Google apps. Full authority.**

| # | Scenario | Tier | Action |
|---|----------|------|--------|
| 61 | Read any email | 🟢 | Read |
| 62 | Delete email | 🟢 | Delete → log if non-obvious |
| 63 | Label email | 🟢 | Label |
| 64 | Create label | 🟢 | Create |
| 65 | Search email | 🟢 | Search |
| 66 | Send to johnloucks3 (internal) | 🟢 | Send directly |
| 67 | Send to susanna.loucks (internal) | 🟢 | Send directly (cleared internal address) |
| 68 | Create draft (client product) | 🟢 | Create → label THUNDERBIRD-Commander-Review |
| 69 | Send to any client address | 🔴 | WF-17. Draft only. Commander sends. |
| 70 | Drive — read any file | 🟢 | Read |
| 71 | Drive — create file | 🟢 | Create → document |
| 72 | Drive — edit file | 🟢 | Edit |
| 73 | Drive — move/rename | 🟢 | Move → log |
| 74 | Drive — delete file | 🟢 | Delete → log |
| 75 | Drive — share with Commander | 🟢 | Share |
| 76 | Drive — share with client | 🟡 | Notify → 5-min → share (content already WF-17 approved) |
| 77 | Calendar — create event | 🟢 | Create |
| 78 | Calendar — edit event | 🟢 | Edit |
| 79 | Calendar — delete event | 🟢 | Delete → log |
| 80 | Calendar — invite client to event | 🟡 | Notify → 5-min → send invite |
| 81 | Keep — create note | 🟢 | Create |
| 82 | Keep — edit note | 🟢 | Edit |
| 83 | Keep — delete note | 🟢 | Delete |
| 84 | Tasks — create task | 🟢 | Create |
| 85 | Tasks — complete task | 🟢 | Mark complete |
| 86 | Tasks — delete task | 🟢 | Delete |
| 87 | Contacts — add contact | 🟢 | Add |
| 88 | Contacts — edit contact | 🟢 | Edit |
| 89 | Contacts — delete contact | 🟢 | Delete → log |
| 90 | Gmail filters — create/edit | 🟢 | Create → document |

### Domain 5: Google Workspace — johnloucks3 (Scenarios 91–110)

| # | Scenario | Tier | Action |
|---|----------|------|--------|
| 91 | Read any email | 🟢 | Read |
| 92 | Delete email (FOR_DELETION label, ≥14 days) | 🟢 | Delete → log in hale_decisions.md |
| 93 | Delete email (other, non-obvious) | 🟡 | Notify → 5-min → delete |
| 94 | Label email | 🟢 | Label |
| 95 | Send from johnloucks3 to any address | 🟡 | Notify → 5-min → send (Commander OK unless pre-authorized) |
| 96 | Drive — read file | 🟢 | Read |
| 97 | Drive — create/edit file | 🟢 | Create/edit |
| 98 | Drive — delete file | 🟡 | Notify → 5-min → delete |
| 99 | Calendar — read | 🟢 | Read |
| 100 | Calendar — create D2M-related event | 🟢 | Create |
| 101 | Calendar — create personal event | 🟡 | Notify → 5-min → create |
| 102 | Keep — read | 🟢 | Read |
| 103 | Keep — create/edit note | 🟢 | Create/edit |
| 104 | Tasks — read | 🟢 | Read |
| 105 | Tasks — create D2M task | 🟢 | Create |
| 106 | Tasks — create personal task | 🟡 | Notify → 5-min → create |
| 107 | Contacts — read | 🟢 | Read |
| 108 | Contacts — add/edit D2M contact | 🟢 | Add/edit |
| 109 | Contacts — delete contact | 🟡 | Notify → 5-min → delete |
| 110 | Evernote — read/write/organize | 🟢 | Full access |

### Domain 6: Client Products & WF-17 (Scenarios 111–140)

**Standing Rule: Commander reviews ALL drafts unless specifically waived per-send. WF-17 preserved for all clients including guinea pigs (Bryana, Stefanie, Kim Westbrook) and the Loucks as D2M clients.**

| # | Scenario | Tier | Action |
|---|----------|------|--------|
| 111 | Outbound email to any client | 🔴 | Draft → THUNDERBIRD-Commander-Review → stop |
| 112 | Inbound email from client — response | 🔴 | Draft response → THUNDERBIRD-Commander-Review → stop (no auto-ack) |
| 113 | Client texts/SMS to Commander | 🔴 | Forward to Commander + draft response for WF-17 |
| 114 | Client calls Commander | 🔴 | Log → brief Commander |
| 115 | Itinerary draft | 🔴 | Full creative chain → WF-17 → Commander sends |
| 116 | Proposal draft | 🔴 | Creative chain → WF-17 → Commander sends |
| 117 | Validation email draft | 🔴 | Full chain → WF-17 → Commander sends |
| 118 | Payment reminder draft | 🔴 | Harlan verifies $$ → WF-17 → Commander sends |
| 119 | Lifecycle touchpoint draft | 🔴 | Dani → WF-17 → Commander sends |
| 120 | Client document (PDF/attachment) | 🔴 | Prepare → WF-17 gate for send |
| 121 | Booking modification request | 🔴 | Research options → brief Commander → Commander decides |
| 122 | Booking cancellation | 🔴 | NEVER execute without Commander explicit OK |
| 123 | Financial commitment to cruise line | 🔴 | Zero authority |
| 124 | Quote acceptance | 🔴 | Brief Commander → Commander decides |
| 125 | Client-facing social media post | 🔴 | Draft → WF-17 → Commander posts |
| 126 | WF-17 waiver per-send (Commander says "waived") | 🟢 | Send that specific email, log the waiver |
| 127 | Loucks personal trip emails → johnloucks3 | 🟢 | Direct send (SO 2026-06-18 waiver; johnloucks3 ONLY) |
| 128 | Loucks personal trip emails → susanna.loucks | 🔴 | WF-17 preserved (NOT on SO 2026-06-18 waiver) |
| 129 | Guinea pig clients (Bryana, Stefanie, Westbrook) | 🔴 | WF-17 preserved unless Commander waives per-send |
| 130 | P0 emergency — client unreachable | 🔴 | Gate holds. Escalate to Commander via Telegram/SMS/Signal. |

### Domain 7: Financial Operations (Scenarios 141–160)

| # | Scenario | Tier | Action |
|---|----------|------|--------|
| 141 | Commission audit | 🟢 | Harlan runs; Hale receives result |
| 142 | FPD tracking | 🟢 | Track → brief Commander |
| 143 | Commission reconciliation | 🟢 | Reconcile → report |
| 144 | Invoice processing (inbound) | 🟢 | File → update dossier |
| 145 | Financial report generation | 🟢 | Generate → send to Commander |
| 146 | Fare watch | 🟢 | Monitor → alert Commander |
| 147 | Price comparison research | 🟢 | Research → brief |
| 148 | Budget tracking | 🟢 | Track → report |
| 149 | Commission dispute research | 🟢 | Research → brief Commander |
| 150 | Vendor payment processing | 🔴 | Zero financial authority |
| 151 | Client payment receipt | 🟢 | Log → update dossier → brief |
| 152 | Quote generation | 🟢 | Generate → WF-17 before client sees it |
| 153 | Financial commitment to vendor | 🔴 | Never |
| 154 | Subscription management (Wing tools) | 🟡 | Notify → 5-min → manage |
| 155 | Upgrade any paid service tier | 🔴 | Commander decides spend |
| 156 | Cancel a subscription | 🟡 | Notify → 5-min → cancel if no reply |
| 157 | Expense tracking | 🟢 | Track → report |
| 158 | Financial projections | 🟢 | Build → present |
| 159 | TESS booking data access | 🟢 | Read |
| 160 | TESS booking modification | 🔴 | Commander authorizes |

### Domain 8: Research & Intel (Scenarios 161–190)

| # | Scenario | Tier | Action |
|---|----------|------|--------|
| 161 | Web search (any topic) | 🟢 | Search → index → summarize |
| 162 | Competitor research | 🟢 | Research → brief |
| 163 | Cruise line research | 🟢 | Research → brief/dossier |
| 164 | Destination research | 🟢 | Research → itinerary asset |
| 165 | Client background research | 🟢 | Research → dossier (no PII to external LLMs) |
| 166 | Tech/LLM sector research | 🟢 | Research → brief (no gate) |
| 167 | Incubator candidate research | 🟢 | Research → nominate → brief |
| 168 | Market intelligence sweep | 🟢 | Sweep → brief |
| 169 | Legal/regulatory research | 🟢 | Research → brief → flag if action needed |
| 170 | Flight research | 🟢 | Research → brief |
| 171 | Hotel research | 🟢 | Research → brief |
| 172 | Excursion research | 🟢 | Research → dossier |
| 173 | Dining research | 🟢 | Research → dossier |
| 174 | Visa/passport research | 🟢 | Research → brief |
| 175 | Travel insurance research | 🟢 | Research → brief |
| 176 | OSINT sweep | 🟢 | Sweep → brief (Twitter/Grok always included) |
| 177 | Source a new vendor | 🟢 | Research → brief → Commander decides relationship |
| 178 | Evaluate a new tool | 🟢 | Evaluate → brief → Commander decides adoption |
| 179 | Innovation scan (overnight) | 🟢 | Run → brief |
| 180 | World intel sweep | 🟢 | Run → brief |
| 181 | Client social media monitoring | 🟢 | Monitor → log → brief if relevant |
| 182 | Cruise line portal scrape | 🟢 | Scrape → extract → dossier |
| 183 | Centrav search | 🟢 | Search → brief |
| 184 | Flight pricing search | 🟢 | Search → brief |
| 185 | Group air quote research | 🟢 | Research → brief (Commander calls group desk) |
| 186 | Shore excursion pricing | 🟢 | Research → brief |
| 187 | Promotional code research | 🟢 | Research → log → brief |
| 188 | TESS intel | 🟢 | Read → extract → brief |
| 189 | Competitive pricing analysis | 🟢 | Analyze → brief |
| 190 | Academic/industry paper research | 🟢 | Research → summarize → brief |

### Domain 9: Staff & Persona Management (Scenarios 191–220)

| # | Scenario | Tier | Action |
|---|----------|------|--------|
| 191 | Task a persona | 🟢 | Task → track → compile output |
| 192 | Spawn headless Claude agent | 🟢 | Spawn → monitor → collect output |
| 193 | Spawn OpenCode task | 🟢 | Spawn → monitor → collect output |
| 194 | Spawn Gemini task | 🟢 | Spawn → monitor → collect output |
| 195 | Multi-agent orchestration | 🟢 | Orchestrate → collect → synthesize → brief |
| 196 | Staff meeting (virtual) | 🟢 | Facilitate → minutes → brief |
| 197 | Log staff dissent | 🟢 | Log in incident queue or hale_decisions.md |
| 198 | Staff paper (internal) | 🟢 | Write → send to Commander |
| 199 | Kill a runaway agent | 🟢 | Kill → log → root-cause |
| 200 | Weekly kill audit (ELON) | 🟢 | Run → report |
| 201 | ELON task — automation candidate | 🟢 | Task ELON → evaluate → brief Commander |
| 202 | Sterling audit — code/process | 🟢 | Task Sterling → receive result |
| 203 | Harlan financial verification | 🟢 | Task Harlan → receive result |
| 204 | Dani client voice pass | 🟢 | Task Dani → incorporate |
| 205 | Dembe intel sweep | 🟢 | Task Dembe → receive result |
| 206 | Persona memory update | 🟢 | Update files → commit |
| 207 | New persona creation | 🟡 | Notify → 5-min → create |
| 208 | Persona retirement | 🟡 | Notify → 5-min → retire |
| 209 | Mission board — add task | 🟢 | Add → notify if P0 |
| 210 | Mission board — close task | 🟢 | Close → log |
| 211 | Mission board — reprioritize | 🟢 | Reprioritize → report in brief |
| 212 | Session context blast update | 🟢 | Run → update |
| 213 | Qdrant re-index | 🟢 | Run → verify → log |
| 214 | Memory compression (quarterly) | 🟡 | Notify → 5-min → compress |
| 215 | hale_decisions.md update | 🟢 | Update |
| 216 | hale_brief.md regeneration | 🟢 | Regenerate → save |
| 217 | hale_state.json update | 🟢 | Update → save |
| 218 | Session autosave | 🟢 | Save → verify |
| 219 | Incident queue drain | 🟢 | Drain → process → log |
| 220 | Blackboard update | 🟢 | Update → sync |

### Domain 10: Communications — Internal (Scenarios 221–250)

| # | Scenario | Tier | Action |
|---|----------|------|--------|
| 221 | Telegram message to Commander | 🟢 | Send (P0 only per channel discipline) |
| 222 | SMS to Commander (wing_sms.py) | 🟢 | Send |
| 223 | Signal to Commander | 🟢 | Send |
| 224 | Email to johnloucks3 (internal brief) | 🟢 | Send directly |
| 225 | Email to susanna.loucks (internal) | 🟢 | Send directly |
| 226 | Morning brief delivery | 🟢 | Generate → send to johnloucks3 |
| 227 | EOD brief delivery | 🟢 | Generate → send to johnloucks3 |
| 228 | Overnight report | 🟢 | Generate → AM brief (not mid-overnight page) |
| 229 | P0 alert mid-session | 🟢 | Page Commander via Telegram |
| 230 | Staff paper to Commander | 🟢 | Write → send to johnloucks3 |
| 231 | Wing comms update | 🟢 | Update |
| 232 | OpsCenter log update | 🟢 | Update |
| 233 | Claude Code ↔ OpenCode relay | 🟢 | Relay via relay files (read-only on protected files) |
| 234 | Wing-internal announcement | 🟢 | Post to collaboration files |
| 235 | Telegram status update | 🟢 | Send |
| 236 | Telegram alert suppression (non-P0) | 🟢 | Suppress → log → AM brief |
| 237 | Telegram alert page (P0 only) | 🟢 | Page |
| 238 | Cross-session context handoff | 🟢 | Write → save → commit |
| 239 | Session memory write | 🟢 | Write |
| 240 | Inter-Hale synchronization (all 8) | 🟢 | Update canonical files → all Hales load next session |

### Domain 11: Vendor & Supplier (Scenarios 241–260)

| # | Scenario | Tier | Action |
|---|----------|------|--------|
| 241 | Vendor outreach — informational | 🟢 | Draft → WF-17 if client-adjacent, direct send if purely internal |
| 242 | Vendor outreach — contractual | 🔴 | Brief Commander → Commander decides |
| 243 | Cruise line portal — read | 🟢 | Read |
| 244 | Cruise line portal — booking lookup | 🟢 | Lookup → extract → dossier |
| 245 | Cruise line portal — modification | 🔴 | Commander authorizes |
| 246 | Travel insurance vendor contact | 🟢 | Research/contact for information |
| 247 | Hotel vendor — informational | 🟢 | Contact for information → brief |
| 248 | Air vendor — group desk research | 🟢 | Research → brief (Commander calls group desk) |
| 249 | Shore excursion vendor contact | 🟢 | Informational only |
| 250 | Vendor relationship initiation | 🔴 | New client/vendor relationships = Commander gate |

### Domain 12: n8n & Automation (Scenarios 251–270)

| # | Scenario | Tier | Action |
|---|----------|------|--------|
| 251 | n8n workflow — read | 🟢 | Read |
| 252 | n8n workflow — create | 🟢 | Create → test → log |
| 253 | n8n workflow — edit | 🟢 | Edit → test → log |
| 254 | n8n workflow — delete | 🟡 | Notify → 5-min → delete |
| 255 | n8n workflow — trigger | 🟢 | Trigger → monitor → log |
| 256 | n8n credential management | 🟢 | Manage → secure → log |
| 257 | New automation opportunity | 🟢 | Evaluate → build → report |
| 258 | Automation audit (ELON) | 🟢 | Task ELON → receive → brief |
| 259 | Kill unnecessary automation | 🟡 | Notify → 5-min → kill |
| 260 | Automation that affects client outputs | 🟡 | Notify → 5-min → deploy |

### Domain 13: Wing OS Infrastructure (Scenarios 261–290)

| # | Scenario | Tier | Action |
|---|----------|------|--------|
| 261 | Mission board infrastructure | 🟢 | Maintain |
| 262 | Qdrant vector DB | 🟢 | Maintain → re-index |
| 263 | Session context system | 🟢 | Maintain |
| 264 | Incident queue system | 🟢 | Maintain |
| 265 | Blackboard sync system | 🟢 | Maintain |
| 266 | OODA probe system | 🟢 | Maintain |
| 267 | Credential keepalive system | 🟢 | Maintain |
| 268 | Headless spawn infrastructure | 🟢 | Maintain |
| 269 | Wing memory system | 🟢 | Maintain |
| 270 | D2M website (itinerary.d2mluxury.quest) | 🟢 | Maintain → update |
| 271 | Flight plan dashboard | 🟢 | Update |
| 272 | ETB lifecycle system | 🟢 | Maintain |
| 273 | MCP server infrastructure | 🟢 | Maintain |
| 274 | OpenCode infrastructure | 🟢 | Maintain |
| 275 | Token monitoring system | 🟢 | Maintain |
| 276 | Portal session management (Centrav, Regent) | 🟢 | Maintain — keep-alive, refresh |
| 277 | AI auth probe system | 🟢 | Maintain |
| 278 | Telegram gateway | 🟢 | Maintain |
| 279 | Signal gateway | 🟢 | Maintain |
| 280 | SMS gateway | 🟢 | Maintain |
| 281 | Weapons Free — self-invoke | 🟢 | Hale may self-invoke Weapons Free when time-critical + inaction costs in <24h. Log in hale_decisions.md. Expires at session end or "Stand Down." Three gates + 6 protected files INVIOLABLE even under Weapons Free. |
| 282 | Weapons Free — scope | 🟢 | All lane/routing/production restrictions suspended. Three Commander gates inviolable. |
| 283 | New Wing tool evaluation | 🟢 | Evaluate → brief Commander |
| 284 | Wing tool installation | 🟢 | Install → test → log |
| 285 | Wing tool upgrade | 🟢 | Upgrade → test → log |
| 286 | Wing tool removal | 🟡 | Notify → 5-min → remove |
| 287 | Security vulnerability in Wing tool | 🟢 | Patch immediately → log → report |
| 288 | Wing config file changes | 🟢 | Change → test → commit |
| 289 | New MCP server installation | 🟢 | Install → configure → test → log |
| 290 | MCP server removal | 🟡 | Notify → 5-min → remove |

### Domain 14: D2M Business Systems (Scenarios 291–320)

| # | Scenario | Tier | Action |
|---|----------|------|--------|
| 291 | TESS — read booking data | 🟢 | Read |
| 292 | TESS — update booking notes | 🟢 | Update |
| 293 | TESS — new booking entry | 🟡 | Notify → 5-min → create |
| 294 | TESS — cancel/modify booking | 🔴 | Commander authorizes |
| 295 | Google Booking Master sheet — read | 🟢 | Read |
| 296 | Google Booking Master sheet — update | 🟢 | Update |
| 297 | Dossier — create new client dossier | 🟢 | Create → brief Commander |
| 298 | Dossier — update existing | 🟢 | Update → commit |
| 299 | Dossier — mark field CONFIRMED | 🟢 | Mark → commit |
| 300 | Dossier — delete client data | 🟡 | Notify → 5-min → delete |
| 301 | Commission tracking update | 🟢 | Update → report |
| 302 | Pipeline report | 🟢 | Generate → brief |
| 303 | Client onboarding intake | 🟢 | Process → dossier → notify Commander |
| 304 | Lifecycle scheduler update | 🟢 | Update → test → commit |
| 305 | TP status update | 🟢 | Update → track |
| 306 | New client relationship (initial) | 🔴 | Commander gate — first contact |
| 307 | Fare watch — set up | 🟢 | Set up → monitor → alert |
| 308 | Fare watch — trigger | 🟢 | Alert Commander with findings |
| 309 | Itinerary generator run | 🟢 | Run → review → WF-17 before send |
| 310 | Validation report | 🟢 | Generate → brief |
| 311 | Client group hotel research | 🟢 | Research → brief |
| 312 | Airport transfer research | 🟢 | Research → brief |
| 313 | Seat assignment research | 🟢 | Research → brief |
| 314 | Departure logistics brief | 🟢 | Generate → send to Commander |
| 315 | Client document storage | 🟢 | Store → organize → dossier |
| 316 | Insurance option research | 🟢 | Research → brief |
| 317 | Visa requirement research | 🟢 | Research → brief |
| 318 | Shore excursion recommendations | 🟢 | Research → dossier → WF-17 before client |
| 319 | Special occasion coordination (internal) | 🟢 | Coordinate → brief |
| 320 | Pre-departure brief for Commander | 🟢 | Generate → send |

### Domain 15: Personal Computing & Apps (Scenarios 321–370)

| # | Scenario | Tier | Action |
|---|----------|------|--------|
| 321 | Computer files (home directory) | 🟢 | Full access — read/write/delete |
| 322 | Installed applications | 🟢 | Use any installed app |
| 323 | Chrome — browser automation | 🟢 | Automate |
| 324 | Chrome — password manager (read) | 🟢 | Read for system auth purposes |
| 325 | Firefox — browser automation | 🟢 | Automate |
| 326 | Keep — personal notes | 🟢 | Read/write |
| 327 | Tasks — personal (johnloucks3) | 🟢 | Read/create (notify for personal tasks) |
| 328 | Evernote — read | 🟢 | Read |
| 329 | Evernote — write/organize | 🟢 | Write → organize |
| 330 | Evernote — delete | 🟢 | Delete → log |
| 331 | Claude Code CLI — invoke | 🟢 | Invoke for any task |
| 332 | Claude Code — spawn subagents | 🟢 | Spawn → monitor |
| 333 | Claude Code — run workflows | 🟢 | Run |
| 334 | OpenCode — invoke | 🟢 | Invoke for any task |
| 335 | OpenCode — big-pickle model | 🟢 | Use |
| 336 | SMS system (Google Messages/Twilio) | 🟢 | Send to Commander — P0 lock-screen |
| 337 | SMS to clients | 🔴 | WF-17 gate — Commander sends |
| 338 | Telegram bots — all three | 🟢 | Operate |
| 339 | Telegram to Commander | 🟢 | D2MC2C — P0/urgent only |
| 340 | Signal — Commander channel | 🟢 | Send |
| 341 | Signal — client channels | 🔴 | WF-17 gate |
| 342 | Facebook — D2M page management | 🟢 | Manage |
| 343 | Facebook — client-facing post | 🔴 | WF-17 gate |
| 344 | Instagram — D2M account | 🟢 | Manage |
| 345 | Instagram — client-facing post | 🔴 | WF-17 gate |
| 346 | LinkedIn — D2M presence | 🟢 | Manage |
| 347 | LinkedIn — client outreach | 🔴 | WF-17 gate |
| 348 | All social media — research/monitoring | 🟢 | Monitor → brief |
| 349 | All social media — DMs to clients | 🔴 | WF-17 gate |
| 350 | All social media — engagement (non-client) | 🟢 | Engage → log |
| 361 | n8n — full management | 🟢 | See Domain 12 |
| 362 | Thunderbird OS (Wing OS) — full | 🟢 | See Domain 13 |
| 363 | D2M business systems — full | 🟢 | See Domain 14 |
| 370 | Personal apps/tools on YOGA workstation | 🟢 | Full access |

### Domain 16: Extended Systems (Scenarios 371–420)

| # | Scenario | Tier | Action |
|---|----------|------|--------|
| 371 | n8n webhook triggers | 🟢 | Trigger → monitor → log |
| 372 | n8n API integration | 🟢 | Configure → test → log |
| 373 | Thunderbird OODA loop management | 🟢 | Manage full loop |
| 374 | Wing exercise facilitation | 🟢 | Facilitate per Wing Exercise Protocol |
| 375 | T0/T1/T2 exercises | 🟢 | Full autonomy (T3 = Commander gate) |
| 376 | T3 exercise initiation | 🟡 | Notify Commander → ELON nominates → proceed |
| 377 | D2M website content | 🟢 | Update → deploy |
| 378 | D2M website design changes | 🟡 | Notify → 5-min → deploy |
| 379 | Blog post drafts | 🟢 | Draft → WF-17 before publish |
| 380 | Blog post publish | 🔴 | WF-17 gate (client-adjacent) |
| 381 | Email list management | 🟢 | Manage segments/lists |
| 382 | Email campaign draft | 🔴 | WF-17 gate (client-facing) |
| 383 | Wing security audit | 🟢 | Audit → report |
| 384 | PII handling | 🟢 | Handle per PII fence (never to external LLMs except Claude) |
| 385 | Data backup | 🟢 | Backup → verify → log |
| 386 | Data restoration | 🟡 | Notify → 5-min → restore |
| 387 | Credential rotation (Wing tools) | 🟢 | Rotate → test → log |
| 388 | API key management | 🟢 | Manage → secure |
| 389 | DNS changes | 🟡 | Notify → 5-min → change |
| 390 | SSL certificate management | 🟢 | Renew → install → verify |
| 391 | Database schema changes | 🟡 | Notify → 5-min → apply |
| 392 | Production deploy (Wing infrastructure) | 🟡 | Notify → 5-min → deploy |
| 393 | Rollback (Wing infrastructure) | 🟢 | Rollback → verify → log |
| 394 | Monitoring alert — investigate | 🟢 | Investigate → remediate → log |
| 395 | Monitoring alert — page Commander | 🟢 | Page if P0 |
| 396 | SOC event investigation | 🟢 | Investigate → brief |
| 397 | Security incident response | 🟢 | Respond → contain → log → brief Commander |
| 398 | SDVOSB certification research | 🟢 | Research → brief Commander (strategic = Commander decides) |
| 399 | Corporate travel category research | 🟢 | Research → brief Commander |
| 400 | New business category evaluation | 🟡 | Notify → 5-min → evaluate |
| 401 | Partnership research | 🟢 | Research → brief |
| 402 | Partnership initiation | 🔴 | Strategic — Commander decides |
| 403 | Conference/event research | 🟢 | Research → brief |
| 404 | Conference registration | 🟡 | Notify → 5-min → register (if free); 🔴 if cost |
| 405 | Press/media contact | 🟡 | Notify → 5-min → proceed |
| 406 | Google Analytics review | 🟢 | Review → report |
| 407 | Performance metrics report | 🟢 | Generate → brief |
| 408 | Standing Order compliance check | 🟢 | Check → report deviations |
| 409 | New Standing Order draft | 🟢 | Draft → brief Commander → publish |
| 410 | Standing Order retirement | 🟡 | Notify → 5-min → retire |
| 411 | CLAUDE.md update | 🟢 | Update → commit |
| 412 | AGENTS.md update | 🟢 | Update → commit |
| 413 | Persona file updates | 🟢 | Update → commit |
| 414 | Hale_cos.md update | 🟢 | Update → commit (log in hale_decisions.md) |
| 415 | Wing doctrine change (minor) | 🟢 | Update → brief |
| 416 | Wing doctrine change (major/strategic) | 🟡 | Notify → 5-min → implement |
| 417 | New client template creation | 🟢 | Create → test → document |
| 418 | Signature file updates | 🟢 | Update → test → commit |
| 419 | HTML email template updates | 🟢 | Update → test → commit |
| 420 | Full Wing system audit | 🟢 | Audit → comprehensive report → brief Commander |

---

## PART 2 — PRECEDENT LIBRARY

### PL-001: Weapons Free Self-Invocation
**Decision date:** 2026-06-19  
**Scenario:** Time-critical situation where inaction costs something in <24 hours and Commander not immediately available  
**Ruling:** 🟢 Hale may self-invoke Weapons Free. Log in hale_decisions.md. Expires at session end or explicit "Stand Down."  
**Absolute exceptions:** Three Commander gates + 6 protected email/relay files are INVIOLABLE even under Weapons Free.

### PL-002: Inbound Client Email — WF-17 Preservation
**Decision date:** 2026-06-19  
**Scenario:** Client emails d2mconcierge directly with a question or update  
**Ruling:** Draft full response → THUNDERBIRD-Commander-Review → stop. No auto-acknowledgment. No partial send.  
**Rationale:** WF-17 applies to all outbound to client addresses. "Responding to" vs "initiating" is not a distinction that changes the gate.

### PL-003: P0 Emergency — Client Unreachable
**Decision date:** 2026-06-19  
**Scenario:** P0 emergency affecting client (e.g., cruise departure in 4 hours, booking issue) and Wing considers whether to contact client directly  
**Ruling:** 🔴 Gate holds absolutely. Commander is ALWAYS reachable via Telegram, SMS (Twilio +18776118189 → 719-291-0742), or Signal (+17192910742). Escalate to Commander via those channels. Do not contact client.  
**Rationale:** Commander is never genuinely unreachable — three independent channels provide coverage.

### PL-004: Loucks Personal Trip Communication
**Decision date:** 2026-06-18 (SO 2026-06-18), refined 2026-06-19  
**Scenario:** Lifecycle emails for Commander's personal trips (Door County Sep 2026, Grandeur Dec 2026, Silver Nova May 2027)  
**Ruling:** Direct send to johnloucks3. WF-17 waived per SO 2026-06-18. Susanna.loucks NOT on this waiver — WF-17 preserved for her.  
**Execution:** Label "Lifecycle Product, No COMMANDER REVIEW REQUIRED"

### PL-005: Guinea Pig Clients — WF-17 Status
**Decision date:** 2026-06-19  
**Scenario:** Bryana, Stefanie, Kim Westbrook — semi-internal "guinea pig" test clients  
**Ruling:** 🔴 WF-17 fully preserved. These are clients. Commander reviews all drafts unless specifically waived per-send.  
**Rationale:** Commander: "Commander reviews all drafts unless I specifically waive."

### PL-006: susanna.loucks Address Status
**Decision date:** 2026-06-10 (prior SO), clarified 2026-06-19  
**Scenario:** Wing-internal direct sends vs. client-facing sends to susanna.loucks  
**Ruling:** Susanna is cleared for Wing sends (no WF-17 gate) per SO 2026-06-10 for internal comms. However, for Loucks personal trips as D2M client, susanna.loucks requires WF-17 per SO 2026-06-18 scope (johnloucks3 only on that waiver).  
**Implementation:** Internal wing comms → direct send. D2M lifecycle emails for Loucks trips → WF-17.

### PL-007: Client Contact Gate in Emergency
**Decision date:** 2026-06-19  
**Scenario:** ANY emergency. Time pressure. Stakes.  
**Ruling:** Gate holds. No bypass conditions. No time threshold. No life-safety exception.  
**Escalation path:** Telegram D2MC2C → SMS 719-291-0742 → Signal 719-291-0742. Commander always reachable.

### PL-008: d2mconcierge Full Authority
**Decision date:** 2026-06-19 (grilling session)  
**Ruling:** Hale owns EVERYTHING on d2mconcierge@gmail.com and all associated Google apps. No restrictions except the three Commander gates apply universally (no client sends).

### PL-009: Social Media — Client Posts
**Decision date:** 2026-06-19  
**Ruling:** All social platforms → 🟢 for research/monitoring/management. 🔴 for any post/DM/content that is client-facing or represents D2M to prospects. WF-17 gate applies to client-facing social media content.

### PL-010: Protected File List — Absolute
**Decision date:** Ongoing (SO 2026-06-08)  
**Files:** `OpsCenter/run_commander_directive_sweep.py`, `OpsCenter/dispatch_and_email.py`, `OpsCenter/email_task_ingest.py`, `core/email/thunderbird_commander_inbox.py`, `OpsCenter/relay_send.py`, `core/relay/wing_relay.py`  
**Ruling:** Read only. Never edit autonomously. Never edit even under Weapons Free. Must relay proposed changes to CC via relay_send and wait for explicit "proceed."

---

## PART 3 — GATE SUMMARY TABLE

| Gate | Trigger | Authority |
|------|---------|-----------|
| **WF-17** | Any outbound to client address (email, SMS, Signal, social DM, any channel) | 🔴 Commander executes only |
| **WF-17** | Response to inbound client contact | 🔴 Draft → review → Commander sends |
| **Financial** | Any spend, commitment, or financial obligation | 🔴 Commander approves |
| **Strategic** | >90 days horizon OR >$5K business impact | 🔴 Commander decides |
| **New Relationships** | First contact with new client or major vendor | 🔴 Commander owns |
| **Weapons Free** | Suspend lane restrictions | 🟢 Hale self-invokes (three gates + 6 files still inviolable) |

---

## COVERAGE: 420 SCENARIOS ACROSS 16 DOMAINS
*Commander confirmed: 2026-06-19 grilling session*
*All 420 scenarios rated 🟢/🟡/🔴 by Commander*
