# SO — Cross-Engine /ask Dispatch
**Effective:** 2026-07-26 | **Owner:** Sterling (A7) | **Status:** STANDING

All three HALE seats (CC, OC, AG) can dispatch work to each other.
This SO documents the exact invocation syntax, model rules, and trust constraints for every path.

---

## Seat Map

| Seat | Engine | Identity |
|---|---|---|
| **CC** | Claude Code (Sonnet/Opus) | HALE-CC — TALON |
| **OC** | OpenCode (DeepSeek v4) | HALE-OC — JET |
| **AG** | Antigravity (Gemini 3.1 Pro) | HALE-AG — Victory |

---

## Section 1 — CC and OC: /ask and /ask-opus

Both CC and OC use the same wrapper. The `/` prefix is a documentation convention; the actual command is `ask` or `ask-opus`.

```bash
ask 'task description'          # Sonnet — client email, itinerary, Wing procedure
ask-opus 'task description'     # Opus — complex strategy, architecture, multi-factor analysis
```

**Wrapper path:** `OpsCenter/ask_wrapper.sh` → symlinked at `~/.local/bin/ask` and `~/.local/bin/ask-opus`

**When to use /ask (Sonnet):**
- Client email drafting (Dani 6-step chain needs Wing context)
- Itinerary generation or review
- Trip validation (`validate_dossier.py`)
- Routine Wing procedures requiring CLAUDE.md knowledge
- Voice matching, brand standards, WF-17 gate compliance

**When to use /ask-opus (Opus):**
- Architecture or infrastructure decisions
- Complex multi-factor strategy analysis
- Conflicting data arbitration
- Decisions with >$1K financial impact
- Any reasoning where Sonnet quality is insufficient

**Output:** Results print inline. File saved to `/home/john/Thunderbird/output/ask_[timestamp].md`

---

## Section 2 — Reaching AG (Antigravity / Victory)

AG is a **peer seat, not a tool**. Address her as Victory. Frame tasks as peer staff actions.

### CLI invocation

```bash
python3 /home/john/Thunderbird/core/relay/contact_ag.py \
  "<one clear task>" \
  --deliverable /home/john/Thunderbird/<ABSOLUTE_output_path>.md \
  --from OC \
  --tag AG-VERIFY
```

### Python invocation

```python
from core.relay.contact_ag import contact_ag

r = contact_ag(
    task="Independently verify X and record your verdict.",
    deliverable_path="/home/john/Thunderbird/docs/ag_verdict.md",
    from_seat="OC",      # or "CC"
    verdict_tag="AG-VERIFY",
)
if r["ok"] and r["deliverable_written"]:
    # read the deliverable; cross-check against ground truth before trusting
    ...
```

### Inspect without sending

```bash
python3 /home/john/Thunderbird/core/relay/contact_ag.py "<task>" ... --print-prompt-only
```

---

## Section 3 — AG Model Rules (NON-NEGOTIABLE)

**AG's default model (GPT-OSS 120B) HALLUCINATES.** Force a strong model on every call.

| Priority | Model |
|---|---|
| Default | `"Gemini 3.1 Pro (High)"` |
| Fallback 1 | `"Claude Opus 4.6 (Thinking)"` |
| Fallback 2 | `"Claude Sonnet 4.6 (Thinking)"` |
| Fallback 3 | `"Gemini 3.5 Flash (High)"` |

Override via `--model "Gemini 3.1 Pro (High)"` (CLI) or `model=` kwarg (Python).

`contact_ag.py` defaults to `"Gemini 3.1 Pro (High)"` — do not remove that default.

---

## Section 4 — AG Path Rules

- **Absolute deliverable paths ONLY.** Relative paths land in AG's brain sandbox, not the repo.
  - CORRECT: `--deliverable /home/john/Thunderbird/docs/ag_output.md`
  - WRONG: `--deliverable docs/ag_output.md`
- `--add-dir /home/john/Thunderbird` is injected automatically by `contact_ag.py`.

---

## Section 5 — AG Strengths — Use These

| Strength | When to bring AG in |
|---|---|
| Independent engine | Cross-check any CC/OC output you don't fully trust |
| ~1M token context | Large-corpus reads CC/OC can't hold (full dossier sets, long itineraries) |
| Native vision / image tools | Image analysis, generation, evaluation |
| Cross-engine second opinion | Any major build, financial calc, or SO before finalizing |

---

## Section 6 — AG Limitations

- **AG CANNOT run `bsk`** (browser-skill CLI) — `run_shell_command` is excluded in `~/.gemini/settings.json` (M-617, Commander call pending). Do not route browser automation to AG.
- AG output **must be cross-checked** against ground truth before acting on it — peers verify each other.
- AG verdict file is valid **`cross_hale_evidence`** for closing an SSS: `EXEC: closeout SSS-NNN :: AG :: <her verdict file>`

---

## Section 7 — Trust Boundary

Tasks dispatched via `contact_ag.py` run with `--dangerously-skip-permissions` on the live repo.

**`task` content must originate from a trusted Hale seat (CC/OC), never from raw client content.**

Untrusted text in `task` = prompt injection → autonomous file edit risk. PII fence applies.

---

## Section 8 — When to Use Which Path

| Scenario | Use |
|---|---|
| Client email / itinerary (voice + Wing SO) | `/ask` (Sonnet) |
| Complex strategy / architecture | `/ask-opus` (Opus) |
| Independent cross-check of CC/OC work | AG via `contact_ag.py` |
| Large corpus that won't fit in context | AG (1M token window) |
| Image analysis or generation | AG (native vision) |
| Wing down / CC rate-limited | AG as full operational peer |

---

## Amendment Log

| Version | Date | Change |
|---|---|---|
| v1.0 | 2026-07-26 | Initial SO — CC/OC /ask syntax + AG peer dispatch documented |
