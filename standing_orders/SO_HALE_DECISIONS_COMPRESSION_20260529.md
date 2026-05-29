# SO — HALE_DECISIONS.MD COMPRESSION PROTOCOL
## Standing Order 2026-05-29 | Approved: Commander John Loucks
## Classification: Process/Tech (A7 Sterling domain) | Status: ACTIVE

---

## ISSUE

`hale_decisions.md` has grown to 3,195 lines / 128KB as of 2026-05-29. It is too large to regularly load into context without token cost. The raw log contains routine task completions, health check confirmations, and routing notes that dilute the principles worth preserving. Without compression, the file becomes unusable and institutional memory is lost by accumulation rather than preserved by it.

---

## AUTHORITY

**Process owner:** A7 Sterling — owns the compression, archive, and distillation process.
**Executor:** Hale — executes the file operations Sterling specifies.
**Trigger authority:** Either Sterling (scheduled) or Hale (size threshold breach) may initiate. Sterling's process governs both cases.

---

## TRIGGER CONDITIONS

Run compression when EITHER:

1. **Quarterly schedule** — First of each quarter: Jan 1, Apr 1, Jul 1, Oct 1. First run: 2026-07-01.
2. **Size threshold** — `hale_decisions.md` exceeds 150KB at any time. Check: `wc -c hale_decisions.md`.

---

## WHAT TO COMPRESS AWAY (does not survive into distillation)

- Individual task completions ("drafted X email," "ran health check," "scanned inbox")
- Routine routing confirmations ("routed to Harlan," "forwarded to Castillo")
- Health check logs and system status entries
- Duplicate entries — same principle already captured
- Entries with no extractable principle (pure status: "DONE," "COMPLETE," "sent")

---

## WHAT SURVIVES — PERMANENT ENTRIES (never compressed)

These stay in the active `hale_decisions.md` file permanently:

- **SO births** — any entry that created or amended a standing order
- **Persona recharters** — any entry that changed a persona's authority, domain, or charter
- **Commander overrides of Hale recommendations** — whenever Commander chose differently than Hale advised; these are institutional correctives
- **Gate decisions** — any entry where a four-gate decision was surfaced and decided
- **Doctrine changes** — entries that established new operating doctrine (e.g., Execute+Report, the four-gate model)

---

## COMPRESSION PROCESS (Sterling owns, step by step)

**Step 1 — Sterling audit pass**
Sterling reads `hale_decisions.md` in full. Flags entries for: PRESERVE (permanent), DISTILL (extract principle), COMPRESS (no value).

**Step 2 — Distillation file**
Write extracted principles to: `data/decisions_distillation_[YYYY]Q[#].md`
Format per principle:
```
## [Principle Title]
- **Date range:** [first entry → last entry]
- **Entry count:** [N entries compressed into this principle]
- **Principle:** [one to three sentences — the durable lesson]
- **Source type:** [routing / client ops / financial / infrastructure / persona / workflow]
```
Target: ~50 lines. No more than 80. If it takes more than 80 lines, split into two distillations.

**Step 3 — Archive raw log**
Move current `hale_decisions.md` to: `data/archive/hale_decisions_[YYYY]_Q[N].md`
Do not delete. Archive is permanent.

**Step 4 — Reset active file**
Create new `hale_decisions.md` containing:
- Header with compression date and pointer to distillation + archive
- All PRESERVE entries (permanent entries, verbatim)
- A single-line summary: "Q[N] [YYYY] entries compressed → see `data/decisions_distillation_[YYYY]Q[N].md`"

**Step 5 — MEMORY.md update**
Add pointer to distillation file under "## Wing Institutional Memory" in MEMORY.md. Format:
`- [Decisions Distillation Q[N] [YYYY]](decisions_distillation_[YYYY]Q[N].md): [N] principles extracted from [date range]; [entry count] entries compressed`

---

## OUTPUT ARTIFACTS

| Artifact | Path | Purpose |
|---|---|---|
| Distillation | `data/decisions_distillation_[YYYY]Q[#].md` | Principles only — load-safe |
| Archive | `data/archive/hale_decisions_[YYYY]_Q[N].md` | Full raw log — permanent |
| Reset active | `hale_decisions.md` | Clean slate + permanents + pointer |

---

## ANTI-PATTERNS

- Do NOT compress entries that changed doctrine, even if they appear routine in isolation
- Do NOT let distillation grow past 80 lines — split rather than expand
- Do NOT delete the archive — disk is cheap, institutional memory is not
- Do NOT run compression mid-session when Commander is active — schedule for session close or off-hours

---

## METRIC

Sterling tracks: `decisions_compression_ratio` = (entries compressed) / (entries total). Target: ≥ 60% compressible per quarter. Below 60% means the file is being used well; above 80% means entries are being logged too granularly.

Report to Hale at each compression. Hale notes in hale_brief.md.

---

*V. Hale, VCS · Sterling (A7) process owner · 2026-05-29*
