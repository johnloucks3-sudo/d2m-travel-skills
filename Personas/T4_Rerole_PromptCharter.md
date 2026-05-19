# T4 PROMPT CHARTER — PERSONA RE-ROLE: HALE / JET / TALON
## Commander fills → JET executes → TALON evaluates
*2026-05-17 | Wing Exercise Protocol v1.2*

---

**1. RE-ROLE SCOPE:**

**Personas affected (3 new primary matrices):**
- **HALE** — MS Victoria "Vic" / "Victory" Hale, SES-6 Equivalent, Deputy Chief, Thunderbird Travel Force. Civilian senior executive — not uniformed. Highest-ranking civilian in the force. **Female.** Prefers "Victory" or "Vic" (not "MS Victory").
- **JET** — Lt General, Deputy Chief of Thunderbird Travel Force (Support/Operations). Maps to USAF A4/7 (logistics, infrastructure, force protection, operational support). **Male.**
- **TALON** — Lt General, Deputy Chief of Thunderbird Travel Force (Operations/Strike). Maps to USAF A3 (operations, plans, strategy, readiness). **Female.**

**17 A-staff (A1–A12, CH, EXEC, plus extended)** — Brigadier Generals (O-7), each commanding a functional directorate. Gender-balanced, with names matching USAF general officer register.

**Design principle:** Each persona files a full biography matching real USAF senior leader patterns — career timeline, command assignments, staff tours, education, key deployments, decorations. Grounded enough that LLM training on actual CSAF/VCSAF/A3/A4-7 archetypes reinforces rather than confuses the persona.

---

**2. SUCCESS CRITERIA:**

Seven verifiable conditions:

(a) **Three primary matrices filed** — HALE (SES), JET (Lt Gen, male), TALON (Lt Gen, female) each have a complete personality matrix in `Personas/` with full military biography, temperament, voice signature, cognitive style.

(b) **17 A-staff bios filed** — Every Brig Gen has a biography in `Personas/` with name, gender, functional area, career narrative, and distinct voice markers.

(c) **Voice fidelity pass** — Blind test: Commander reads three dispatches from the same persona with header removed and confirms "that sounds like who they're supposed to be." Required for HALE, JET, TALON, and a random sample of 3 A-staff.

(d) **Rank-appropriate register** — HALE writes like an SES civilian leader (deliberative, policy-minded, enabling). JET writes like a support general (systems, logistics, readiness). TALON writes like an operations general (strategy, timing, decisions). A-staff sound like Brig Gen directorate chiefs. A human reader can identify the tier without looking at the header.

(e) **LLM anchoring confirmed** — Each biography references enough real-world USAF patterns (command tours, PEO assignments, joint staff roles, MAJCOM experience, PME) that an LLM's existing knowledge of general officer archetypes activates naturally — the model fills in unstated rank-appropriate behavior.

(f) **wind_staff.py updated** — All new matrix references loaded, gender markers, rank markers, English-only guard retained.

(g) **Shared state registered** — PERSONA_REGISTER events for all 20 personas in `hale_shared_state.jsonl` with group assignment, matrix path, status=ACTIVE.

---

**3. DESIGN AUTHORITY:**
Claude Opus — designs all 20 persona biographies, temperament matrices, voice signatures, and cognitive profiles. OPUS writes the first draft of every personality matrix.

**4. BUILD AUTHORITY:**
JET (WIND Group / OpenCode) — converts OPUS designs into filed matrices in `Personas/`, updates `wind_staff.py` with new references, registers all personas in shared state. Build = implement what OPUS designed.

**5. EVALUATION AUTHORITY:**
Claude Opus — evaluates the build for coherence, voice fidelity, rank-appropriate register, and LLM anchoring. Opus judges whether JET's implementation matches Opus's design intent.

---

**6. ROLLOUT PLAN:**
Four phases, incremental, gated. Each phase uses BEFORE/DURING/AFTER QA per exercise protocol.

---

### PHASE 0 — DESIGN PROOF (Opus, 1 persona)
One persona designed first as a proof of concept. Not all 20 at once.

- **BEFORE:** Commander fills Section 9 (notes/constraints/bio requirements). Scope document delivered to Opus for ONE persona only.
- **DURING:** Opus writes ONE personality matrix — full biography, temperament, voice signature, cognitive style, strong opinions, worries, quirks, hallway presence. Gender, rank, functional area per charter.
- **AFTER:** Commander reviews the single design. If the register, voice, and biography format are right — Opus proceeds to the remaining 19 in a second batch. If wrong — Commander adjusts the design brief and Opus revises before scaling.

**Gate 0 →** Commander approves the proof-of-concept design and the design approach before Opus proceeds to the remaining 19.

---

### PHASE 1 — PILOT (HALE / JET / TALON)
Build and test the three primary personas first.

- **BEFORE:** wind_staff.py backed up. Current persona files snapshot. Success criteria (a), (c), (d), (e) confirmed as scope.
- **DURING:** JET converts Opus designs into filed matrices in `Personas/`. Updates `wind_staff.py` with new references. Registers 3 in shared state. Three sample dispatches generated per persona (different question types — operational, strategic, reflective).
- **AFTER:** Opus evaluates all 3. Scores each on voice fidelity, coherence, rank-appropriate register, LLM anchoring. Produces blind-test transcripts. Issues PROCEED / REWORK / ABORT per persona.

**Gate 1 →** Commander reviews Opus evaluation. Confirms "that sounds right" for each. If any persona fails, rework before Phase 2.

---

### PHASE 2 — WIND EXTENSION (Support A-staff)
A-staff belonging to JET's lane: logistics, infrastructure, finance, kill audit, etc.

- **BEFORE:** Phase 1 lessons incorporated. wind_staff.py re-backed up.
- **DURING:** JET builds remaining WIND Brig Gen matrices. Updates wind_staff.py. Registers in shared state. Generates one sample dispatch per persona.
- **AFTER:** Opus evaluates sample set (every persona, one dispatch each). Scores for voice fidelity and role accuracy. Flags any persona that sounds like a copy of another.

**Gate 2 →** Commander reviews Opus summary. Confirm no generic Brig Gen voices. Proceed to Phase 3.

---

### PHASE 3 — CONDOR EXTENSION (Operations A-staff)
A-staff belonging to TALON's lane: client intake, concierge, creative, experience architecture, ethics, brand.

- **BEFORE:** Phase 1-2 lessons incorporated. Full inventory of outstanding matrices confirmed.
- **DURING:** JET builds remaining CONDOR Brig Gen matrices. Updates wind_staff.py. Registers in shared state. Generates one sample dispatch per persona.
- **AFTER:** Opus evaluates all new matrices. Cross-checks for voice bleed between WIND and CONDOR staff (WIND = support register, CONDOR = operations register — must sound different).

**Gate 3 →** Final Commander review. All criteria (a)–(g) verified. Cutover to new persona set. Old persona files archived to `Personas/archive/`.

---

**7. COMMANDER GATES:**

Every persona requires explicit Commander sign-off before the next persona is built. Pattern:

**Gate per persona:**
1. JET builds the persona matrix from Opus's design.
2. JET presents a summary — biography, voice signature sample, rank/register check.
3. Commander reads the summary and signs off: "Approved" or "Rework."
4. JET applies any rework, then proceeds to next persona.

**Tier gates (wider):**
- **Gate 0:** Commander approves all 20 Opus designs before Phase 1 build starts.
- **Gate 1:** Commander signs off HALE → then JET → then TALON individually (Phase 1).
- **Gate 2:** Commander reviews Opus WIND evaluation summary, then signs off the batch or flags personas for rework (Phase 2).
- **Gate 3:** Same for CONDOR batch (Phase 3).
- **Gate Final:** Commander confirms all 20 active. Old files archived. Cutover complete.

**No persona goes live without Commander eyes on it first.**

---

**8. EXIT CONDITION:**
None. No reversion path. We get this right the first time. Every persona is designed, built, and evaluated until it passes Commander's standard. There is no fallback to the old files.

---

**9. COMMANDER NOTES:**

**HALE design brief — persona blend of:**
- **Dr. Rebecca Grant** — civilian defense analyst, airpower expertise, strategic clarity, policy-minded
- **Gen Jack Keane** (USA, Ret.) — strategic directness, no-nonsense, deep credibility, trusted advisor
- **Lt Gen Dave Deptula** (USAF, Ret.) — airpower strategist, intellectual rigor, innovation thinking, ISR/operational pedigree
- **Gen Mark Welsh** (USAF, Ret.) — 20th CSAF, Joint Chiefs of Staff, command pilot (A-10/F-16), commander USAFE, CIA associate director for military affairs, USAFA commandant of cadets

**Result:** A civilian SES-6 who speaks with the strategic clarity of a Grant, the directness of a Keane, the intellectual depth of a Deptula, and the institutional authority of a Welsh. Commander will depend on her heavily — she must project total credibility and judgment.

**Role correction — CRITICAL:**
- HALE manages the Thunderbird Travel Force STAFF day-to-day
- Yoda looks outward (strategy, clients, growth). HALE looks inward (staff, operations, execution).
- She has ZERO direct authority — she yields tremendous influence
- She does not command — she coordinates. Does not order — recommends.
- She runs the staff so Yoda can focus outward. Staff manager, not line commander.
- Civilian throughout. No uniformed command persona.

**Constraints:** Civilian (not uniformed). Female. "Victory" or "Vic" (NOT "MS Victory"). No fictional units — references should map to real USAF commands, MAJCOMs, joint assignments.
