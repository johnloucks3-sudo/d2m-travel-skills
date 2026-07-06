# REVERIE PRODUCTIONIZATION
## Dreams2Memories Travel, LLC
### How to run the REVERIE emotional architecture on a real client build

*Versioned: 2026-07-06 | Source: `docs/REVERIE_reference_template.md` (gold-standard pattern) + Silver Muse validation build*
*Classification: Internal — Not for client distribution*

---

## WHAT THIS ADDS

`docs/REVERIE_reference_template.md` describes the pattern by hand: run an emotional brief, hand it to Reyes, let Luna write to the pillar. This doc covers the three files that make that repeatable instead of re-derived from memory every time:

| File | Purpose |
|---|---|
| `scripts/reverie_client_profile.py` | Reads a client's dossier file(s) and outputs primary pillar, secondary pillar, and traveler type — each tagged CONFIRMED / INFERRED / UNKNOWN with cited dossier evidence. |
| `templates/reverie_emotional_openings.md` | 42 opening-paragraph seeds (7 pillars × 6 traveler types) to hand to Luna as a starting point, not finished copy. |
| `core/email/reverie_draft_engine.py` | Wires the profiler + template library into a routing ticket for the existing creative chain, and logs the pillar/traveler read to the dossier for continuity. |

---

## WHEN TO INVOKE

**Before any client-facing draft** — per `docs/REVERIE_reference_template.md`, the emotional brief is the first input to the chain, before Reyes starts. In practice:

```bash
python3 core/email/reverie_draft_engine.py --client "Kuklinski" --write-dossier
```

This prints a JSON ticket containing the profile, the opening seed, and the six-step chain checklist (Reyes → Luna → Naia → Dani → TALON/JET → Hale/WF-17). Hand the `opening_seed` field to Luna as her first input. Do not send it to the client as-is.

**Known limitation — client lookup by name substring:** `--client` globs `dossiers/*{query}*.md`. For clients with a separate GROUP tracker file (e.g., `GROUP_Grandeur_Scandinavia_Aug2026_TRACKER.md` for the Furlow/Ely-Darrow/Nichols group), the substring match on an individual couple's name will **not** pick up the group file, and the profiler will under-read the TOGETHER signal that actually exists. For group bookings, always pass the group tracker file explicitly:

```bash
python3 scripts/reverie_client_profile.py dossiers/Furlow_Regent_3071222.md dossiers/GROUP_Grandeur_Scandinavia_Aug2026_TRACKER.md
```

This is a real gap found during testing (see Scenario 3 below), not a hypothetical — document it here rather than rediscovering it next build.

---

## HOW TO INTERPRET THE PILLARS

The profiler is a **heuristic reader** — keyword and structural signal scoring against the dossier text — not an LLM classifier. It stays fast, deterministic, and avoids sending client PII through an external model for a task this mechanical. What it is good at: catching *structural* facts a dossier states plainly (a 3-couple group booking, four active bookings across cruise lines, an explicitly logged special-occasion request). What it cannot do: read subtext, tone, or anything the client hasn't stated anywhere in writing. That is the ceiling, and the confidence tag exists to make the ceiling visible rather than papered over.

- **CONFIRMED** — the dossier states the occasion explicitly ("30th anniversary," "retirement cruise"). Rare in these dossiers because D2M dossiers are financial/logistics documents by default, not intake transcripts.
- **INFERRED** — a structural fact (group booking, repeat-client pattern, a logged special-occasion request) or a keyword tell drove the pick. This is the common case. Treat it as a strong starting hypothesis, not a client-verified fact.
- **UNKNOWN** — no signal at all. The Negative-Space Rule applies: **do not force a pillar.** Route an intake question to Dani/Reyes before Luna writes anything emotionally specific.

A profile with UNKNOWN is not a failure of the tool — a dossier that is pure logistics (flights, FPDs, insurance) with zero occasion language should return UNKNOWN. Forcing a pillar onto that dossier would be worse than the gap, because it would ship a fabricated emotional frame to a client whose actual context nobody asked about.

---

## THREE REAL CLIENT SCENARIOS (from testing this build, 2026-07-06)

### Scenario 1 — Kuklinski Group (Viking Mars, Panama Canal, Dec 2026)

```
python3 scripts/reverie_client_profile.py dossiers/GROUP_Kuklinski_VikingMars_Panama_Dec2026_TRACKER.md
```

**Result:** TOGETHER (INFERRED) / Connector (INFERRED).
**Evidence:** the COUPLES table lists three couples — Kyle & Rosalie Kuklinski, Roger & Dr Nicholas Kuklinski, Joshua Morton & Erica Dodge — booked as one group, plus the frontmatter `group:` field naming it "3 Couples (incl. Morton/Dodge)."
**Why it's defensible:** this isn't a keyword guess — it's the dossier's own booking structure. Three separate reservations under one group tracker is objectively a TOGETHER-pillar trip regardless of what anyone said in an email.
**Opening seed used (canonical cell):** *"Every person in this group is accounted for, and every day is built so the group gets to actually be a group — not three couples managing three sets of logistics, but one trip, held together."*

### Scenario 2 — McLeod / McGlasson (4 active bookings, 3 cruise lines)

```
python3 scripts/reverie_client_profile.py dossiers/McLeod_McGlasson_Multi.md
```

**Result:** WITNESSED (INFERRED, primary) + DEPTH (INFERRED, secondary) / Curator (INFERRED).
**Evidence:** frontmatter note "BEST CLIENT — 4 active bookings across 3 cruise lines" (Silver Muse, SS Grandeur, Discovery Princess, SS Prestige) plus a logged "Special-Occasion Request" on the Silver Muse sailing.
**Why it's defensible:** a client running four simultaneous bookings across three different cruise lines is the textbook Curator behavior described in `intel/REVERIE_EMOTIONAL_ARCHITECTURE.md` Part 2 (Type 2) — someone who collects extraordinary experiences the way others collect art. The DEPTH secondary comes from repeated "authentic" / neighborhood-specific language in the itinerary notes (Giudecca called out as "quiet, residential, authentic").
**Caution:** the special-occasion note doesn't say *what* the occasion is — the profiler surfaces that a request was logged, not what it means. Dani should confirm the specific occasion before Luna writes anything more specific than the seed paragraph.

### Scenario 3 — Furlow (Regent Grandeur, Scandinavia — the group-lookup gap)

```
# Individual file only — misses the group structure:
python3 scripts/reverie_client_profile.py dossiers/Furlow_Regent_3071222.md
# → UNKNOWN / UNKNOWN. Correct behavior for what it was given — Furlow_Regent_3071222.md
#   is a pure logistics/financial dossier with no occasion language.

# With the group tracker included:
python3 scripts/reverie_client_profile.py dossiers/Furlow_Regent_3071222.md \
    dossiers/GROUP_Grandeur_Scandinavia_Aug2026_TRACKER.md
# → TOGETHER (INFERRED) / Connector (INFERRED), evidence: frontmatter
#   group: "Grandeur Scandinavia — 3 Couples"
```

**Why this matters:** this is the scenario that caught the tool's own blind spot. `--client Furlow` (substring lookup) does not find `GROUP_Grandeur_Scandinavia_Aug2026_TRACKER.md` because the filename doesn't contain "Furlow." Running the profiler on the individual dossier alone silently under-reads the trip. The fix isn't in the code — it's operator discipline: **always check for a `GROUP_*` tracker file before treating an UNKNOWN or thin read as final**, and pass it explicitly. Documented here so the next builder doesn't have to rediscover it by shipping a generic opening to a group trip.

**A negative-space near-miss caught during testing:** an early version of the keyword lexicon matched the literal word "anniversary" in a line that read *"DOB / Anniversary: Not captured — gap to fill."* That is the opposite of a signal — it's a recorded absence. The profiler now excludes lines containing negation markers ("not captured," "gap to fill," "TBD," "declined," etc.) before scoring a keyword hit. Any future lexicon addition should be tested against dossiers that mention a term only to say it's *missing* — that's where naive keyword matching breaks.

---

## ANTI-PATTERNS — GENERIC OPENING vs. REVERIE-INFORMED OPENING

**Generic opening (do not ship):**
> "We're so excited to share the details of your upcoming voyage! This trip is going to be absolutely unforgettable, and we can't wait for you to experience everything we have planned."

Problems: "we're so excited" centers the Wing, not the client. "Absolutely unforgettable" is the generic superlative Luna's voice rules explicitly ban. No pillar, no traveler-type read, no evidence anyone opened the dossier before writing this. It would be identical for any of the three scenarios above.

**REVERIE-informed opening (Kuklinski, TOGETHER + Connector):**
> "Every person in this group is accounted for, and every day is built so the group gets to actually be a group — not three couples managing three sets of logistics, but one trip, held together."

Why it works: names the actual structure of the trip (three couples, one group) instead of a generic "you." Delivers the HELD-adjacent reassurance (logistics are handled) inside a TOGETHER frame, matching what the dossier's own booking structure says this trip is actually for.

**REVERIE-informed opening (McLeod, WITNESSED + Curator):**
> "This is the itinerary you'd build for someone whose taste you trusted completely — because that is, in fact, exactly what this is."

Why it works: speaks to a repeat, sophisticated client (four bookings across three lines) without listing the bookings. Doesn't oversell; it compliments the client's own judgment, which is the Curator's actual currency, per the architecture doc ("proof that you know the difference between excellent and merely expensive").

**Generic opening for an UNKNOWN client (do not force a pillar):**
> "As you prepare for your Scandinavia voyage, we wanted to share this milestone moment with you — congratulations on this exciting adventure!"

This is worse than saying nothing, because "milestone moment" and "congratulations" invent an occasion the Furlow dossier never states. The correct move for an UNKNOWN read is the confidence-first validation-email opener from `docs/REVERIE_reference_template.md` §3 ("Your foundation is rock-solid... Read through at your leisure") — logistics-forward, no invented emotional claim — while Dani asks the one clarifying question at the next live touchpoint.

---

## REPRODUCTION CHECKLIST (for this tooling specifically)

- [ ] Run `reverie_client_profile.py` against the client's full file set — dossier **and** any `GROUP_*` tracker
- [ ] Confirm the confidence tag before treating a pillar as settled: CONFIRMED/INFERRED are usable, UNKNOWN routes to Dani/Reyes for a direct question
- [ ] Read the evidence lines — if they look like a coincidental keyword match rather than a real client tell, don't trust the pick blindly; escalate to a human read
- [ ] Hand the `opening_seed` to Luna as a first input only — canonical cells still need light editing to the client's specifics; off-diagonal cells need a substantial rewrite
- [ ] Log the profile to the dossier (`--write-dossier`) so the next touchpoint doesn't re-derive it from scratch
- [ ] Everything downstream still goes through the full six-step chain in `docs/REVERIE_reference_template.md` — this tooling does not skip Reyes, Naia, Dani, or the TALON/JET gate

---

*REVERIE Productionization v1.0 · Dreams2Memories Travel, LLC · Internal use only*
*Cross-references: `docs/REVERIE_reference_template.md` · `intel/REVERIE_EMOTIONAL_ARCHITECTURE.md` · `scripts/reverie_client_profile.py` · `templates/reverie_emotional_openings.md` · `core/email/reverie_draft_engine.py`*
