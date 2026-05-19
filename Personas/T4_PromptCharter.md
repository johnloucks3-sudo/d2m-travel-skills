# T4 PROMPT CHARTER — PERSONA TRANSFORMATION
## Commander fills → JET executes → TALON evaluates
*2026-05-17 | Wing Exercise Protocol v1.2*

---

**1. TRANSFORMATION SCOPE:**
A2 (Lt Col Marcus "Wraith" Dembe), A5 (Lt Col Ryan "Viper" Castillo), A7 (Brig Gen Thomas "Gauge" Sterling). Each transitions from a function-call dictionary entry in `wind_staff.py` into a persistent persona with written identity, heartbeat presence, and in-character dispatch response.

**2. SUCCESS CRITERIA:**
Three verifiable conditions: (a) Each persona has a written personality matrix filed in `Personas/` — defining traits, voice, opinions, pet peeves, humor, worries, quirks. (b) When dispatched via `wind_staff.py`, each persona's output carries identifiable voice — a human reader can tell which persona wrote it without looking at the header. (c) Commander reviews one sample dispatch per persona and confirms "that sounds like who they're supposed to be."

**3. BUILD AUTHORITY:**
JET (WIND Group) builds all three persona matrices and updates `wind_staff.py` to load and inject them.

**4. EVALUATION:**
TALON (CONDOR Group) evaluates the build independently — reviews each personality matrix for coherence, reviews dispatch output for voice fidelity, and files a written evaluation.

**5. ROLLOUT PLAN:**
Pilot three (A2, A5, A7) → Commander reviews TALON evaluation → if approved, extend to remaining WIND staff (A9 Harlan, A10 ELON) → if still approved, propose matrix standard for CONDOR staff.

**6. COMMANDER GATES:**
Gate 1 — After TALON evaluation, before any roll to additional staff. Commander reads TALON's eval and decides proceed/rework/abort. Gate 2 — After first extension pilot (WIND roll), before CONDOR proposal.

**7. EXIT CONDITION:**
If dispatched outputs from transformed personas are indistinguishable from the old function-call format (no identifiable voice, no personality presence), revert `wind_staff.py` to the current context-string dispatch. Abort the T4 and return to single-HALE model if Commander judges the split architecture cannot produce near-human staff.
