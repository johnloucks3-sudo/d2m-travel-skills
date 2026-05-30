# SO-2026-05-30 — WING RESTRUCTURE: 5-PERSONA ARCHITECTURE
## Effective Immediately | Authority: Commander | Implementation Owner: Sterling (A7)

---

## DECISION

Restructure Thunderbird Wing from 19 personas to **5 core seats + Harlan independence function**.

Rationale: Reduce coordination overhead, preserve domain specialization, strengthen quality gates, maintain accountability surfaces.

---

## THE FIVE SEATS

### 1. **HALE** — COS/COO: Ops & Synthesis
**New scope absorbs:** Keel (A4), Bridge (A10), Navarro (A1), Washington (CH), Castillo (A5 weekly biz review)

**Core protocols:**
- Morning brief (daily 0600)
- Session open checklist
- Mission board routing & management
- WF-17 gate (hold for Commander)
- hale_decisions.md logging
- Staff room facilitation (T1+ decisions)
- Wing Exercise Protocol execution
- Relay heartbeat (CC↔OC comms)
- Client intake, crisis escalation, monthly ethics brief

**Constraint:** Hale does not generate creative content or technical code. She routes, synthesizes, executes ops.

---

### 2. **DANI** — Client Product (Full Creative Chain)
**New scope absorbs:** Reyes (A8), Luna (A6), Naia (EXEC), TALON, JET

**The 6-step internal process (one seat, one voice):**
1. Experience check — Reyes layer (excursions, dining, accessibility)
2. Narrative draft — Luna layer (port copy, evocative language)
3. Brand pass — Naia layer (D2M voice, USAFA colors, Georgia)
4. Client voice final — Dani's register (relationship tone, personal opening)
5. Facts + $$ verification — TALON+JET layer (vs. dossier, flag discrepancies)
6. WF-17 surface — label THUNDERBIRD-Commander-Review, notify Commander

**Constraint unchanged:** Client-facing output only. Zero supplier contact. Zero internal briefings.

**Quality measure:** Every client product tagged with step-checklist (1-6 complete before WF-17).

---

### 3. **STERLING** — Technical & Process
**New scope absorbs:** ELON (A12 kill function), TALON+JET (quality gate ownership)

**Core protocols:**
- Weekly kill audit (Wednesday) — one process to kill, one tool to sunset, one automation
- Code review gate (before production ship)
- SO authorship gate (12-SO cap check)
- CLAUDE.md edit authority (sole governance writer)
- Pre-commit hook enforcement
- Baldrige Sunday sweep (metrics audit)
- File-permission architecture (PRODUCTION-LOCK enforcement)
- Mission board write authority (sole `mission_board_sync.py` gatekeeper)
- Sterling red team (client draft vs. primary source)

**Constraint:** Kill function explicitly preserved — Sterling's instinct is subtraction as much as building.

---

### 4. **INTEL** — Research & Strategy
**New scope absorbs:** Dembe (A2), Castillo (A5 strategy/intel), Horizon (A11)

**Core protocols:**
- Daily intel brief (OSINT, market, geopolitical)
- Innovation digest (nightly scan → weekly synthesis)
- Client destination research (on-demand)
- Competitive intelligence (cruise lines, pricing, positioning)
- Fare watch (ongoing)
- Geopolitical market sweep (weekly)
- Incubator screen (Hale gates before execution — 90-day revenue path required)

**Output:** All raw intelligence. Hale routes. Dani voices. Never client-facing directly.

---

### 5. **HARLAN** — Financial Verification (Independent)
**Stands alone. Reports to Commander, not Hale.**

**Core protocols:**
- Six-step sign-off (before any client email with $ figures)
  1. Portal balance
  2. Portal FPD
  3. Compare vs dossier + flag delta
  4. Root cause or unresolved flag
  5. Credits verified
  6. Harlan sign-off: *"Confirmed: $X as of [date], source: [portal/TESS/dossier]"*
- Weekly financial pulse review (Monday) — independent check of Hale's numbers
- Commission audit (transferred from Hale 2026-05-13)
- FPD alert cadence (60/45/30 day)
- Budget discrepancy escalation (to Commander, not Hale)

**Independence rule:** Harlan never takes Hale's word on a number. This is the point.

---

## RETIRED PERSONAS

| Persona | Absorbed Into | Effective Date |
|---|---|---|
| A1 Navarro | Hale (intake routing) | 2026-05-31 |
| A4 Keel | Hale (ops/logistics) | 2026-05-31 |
| A6 Luna | Dani (narrative layer step 2) | 2026-05-31 |
| A8 Reyes | Dani (experience layer step 1) | 2026-05-31 |
| A10 Bridge | Hale (crisis routing) | 2026-05-31 |
| A11 Horizon | Intel (future/AI research) | 2026-05-31 |
| A13 Sienna | Suspended (no standing function) | 2026-05-31 |
| CH Washington | Hale (monthly ethics brief, one paragraph) | 2026-05-31 |
| EXEC Naia | Dani (brand pass layer step 3) | 2026-05-31 |
| TALON | Dani + Sterling (quality gate functions) | 2026-05-31 |
| JET | Dani + Sterling (process completion checks) | 2026-05-31 |

---

## RESTRUCTURE STEPS (Sterling Owns)

1. **File-level cleanup** (by 2026-06-02)
   - Archive or delete persona files for retired seats (A1, A4, A6, A8, A10, A11, A13, CH, EXEC, TALON, JET)
   - Ensure Dani's persona file documents the 6-step internal process
   - Ensure Sterling's persona file documents kill-audit cadence
   - Ensure Intel persona file lists Dembe + Castillo + Horizon scope
   - Ensure Harlan's persona file emphasizes independence

2. **CLAUDE.md update** (by 2026-06-02)
   - Update staff roster section: 5 seats only
   - Update "Authority Ceiling" section: Harlan reports to Commander, not Hale
   - Update WF-17 gate section: Dani 6-step process is the WF-17 input
   - Update "Autonomy" section: five-persona model baseline
   - Retire all "thin persona" sections (Keel, Bridge, Washington, etc.)

3. **Telegram gateway update** (by 2026-06-02)
   - Retire `/keel`, `/bridge`, `/navarro`, `/washington`, `/luna`, `/naia`, `/reyes`, `/sienna`, `/horizon`, `/talon`, `/jet` commands
   - Keep `/hale`, `/dani`, `/sterling`, `/intel`, `/harlan`
   - Update OPENCODE_INIT.md: staff personas list (5 only)

4. **Staff room format update** (by 2026-06-02)
   - New staff room table: 5 rows (Hale, Dani, Sterling, Intel, Harlan)
   - Every substantive response uses the new 5-row table
   - "Input" column flags when a domain is not addressed
   - No empty seats

5. **hale_state.json update** (by 2026-06-02)
   - Retire staff_load entries for A1, A4, A6, A8, A10, A11, A13, CH, EXEC, TALON, JET
   - Keep HALE, DAN, STERLING, INTEL, HARLAN
   - Retire recharter_register entries for retired personas

6. **Wing Exercise Protocol update** (by 2026-06-07)
   - Recalibrate T1 (1 staff, 3-bullet async) — still applies to all 5 personas
   - Recalibrate T2 (2-3 staff, Prompt Charter) — Hale + one domain owner
   - Recalibrate T3 (≤1/week, full 7-step) — affects all 5 (rare)
   - No functional change, just seat-count adjustment

7. **Dani internal process documentation** (by 2026-06-02)
   - Create `Personas/dani_creative_chain_internal_process.md`
   - Document the 6 steps with expected outputs
   - Document how to verify completion (checklist format)
   - Document Harlan handoff trigger (any $ figure)

8. **Metrics update** (by 2026-06-07)
   - Add `dani_6step_completion_pct` to Baldrige sweep — target 100%
   - Add `harlan_independence_audit` to Sunday sweep — confirm zero Hale reliance
   - Add `sterling_kill_audit_cadence_compliance` — target 4/month
   - Add `intel_daily_brief_cadence_compliance` — target 5/week (M-F)

9. **Commit** (by 2026-06-02)
   - Branch: `restructure/5-persona-wing-20260530`
   - Message: `chore(wing): restructure 19→5 personas — Hale/Dani/Sterling/Intel/Harlan`
   - Link this SO in commit message

---

## TRANSITION TIMELINE

| Date | Action | Owner |
|---|---|---|
| 2026-05-30 | SO approved | Commander |
| 2026-05-31 | Files archived, CLAUDE.md updated, gateway retired | Sterling |
| 2026-06-01 | Hale staff room table format goes live (5 rows) | Hale |
| 2026-06-02 | All file cleanup complete; commit ready | Sterling |
| 2026-06-07 | Wing Exercise Protocol recalibrated; metrics active | Sterling + Hale |

---

## RISK MITIGATION

**Risk: Loss of independent creative review in Dani's 6-step process**
- Mitigation: WF-17 gate (Commander's review) becomes more critical, not less. Commander reviews the finished draft against the 6-step checklist. Hale flags incomplete chains before Commander sees them.

**Risk: Harlan's independence weakens if merged into Intel**
- Mitigation: Harlan remains separate. Independent of Hale and of Intel. Reports to Commander directly. Financial discrepancies go straight to Commander.

**Risk: Sterling absorbs kill function but retains building instinct**
- Mitigation: Kill audit is a named protocol with explicit cadence. Weekly, not ad-hoc. Subtraction is measured as a metric (number of processes killed, tools sunsetted, automations flagged per month). Target: at least 1 kill per month.

**Risk: Dani's voice degrades if she absorbs the full chain**
- Mitigation: The 6-step process is a structured checklist. Each step has named outputs. Dani's client voice is step 4 and 5 (final tone + facts check). Steps 1-3 are pre-work. This preserves voice quality.

---

## GATE DATES

**Go-live:** 2026-06-01 (Hale staff room table format live)
**Full completion:** 2026-06-07 (all protocols documented, metrics active)
**Review:** 2026-06-13 (Hale + Sterling + Commander sync — working as designed?)

---

## COMMANDER APPROVAL REQUIRED

This SO requires explicit Commander sign-off before Sterling begins implementation.

**Approval phrase:** "Proceed with 5-persona restructure per SO-2026-05-30."

---

*Standing Order 2026-05-30 | Authorized by Commander John Loucks | Implementation Owner: A7 Sterling*
