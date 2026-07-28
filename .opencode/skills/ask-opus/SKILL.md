---
name: ask-opus
description: "Spawn Claude CC (Opus) headless with full Wing context. Use for complex reasoning, strategy decisions, architecture decisions, anything requiring deep analysis. Triggers on: /ask-opus, ask opus, dispatch opus, opus headless, deep reasoning, complex strategy"
---

# /ask-opus — Spawn Claude CC Headless (Opus)

Same as /ask but routes to Claude Opus — premium reasoning, slower, more thorough.
Use when: complex strategy decisions, architecture choices, multi-factor analysis,
anything where Sonnet quality isn't enough.

Full cross-engine dispatch doctrine: `standing_orders/SO_ASK_DISPATCH_CROSSENGINE_20260726.md`

## How to invoke — CC and OC

```bash
ask-opus 'task description here'
```

**NOTE:** `/ask-opus` is the canonical name (one hyphen, no double-dash).
The old `ask --opus` flag format is deprecated but still works for backward compatibility.
The command is symlinked to `OpsCenter/ask_wrapper.sh` in `~/.local/bin/`.
**Both CC and OC use this exact same syntax** — the wrapper is shared.

## When to use /ask-opus vs /ask vs AG

| Use /ask (Sonnet) | Use /ask-opus (Opus) | Use AG (contact_ag.py) |
|---|---|---|
| Client email drafting | Architecture decisions | Independent engine cross-check |
| Trip validation | Complex strategy analysis | Large corpus (~1M token) |
| Itinerary generation | Multi-factor reasoning | Native vision / image analysis |
| Routine Wing procedures | Decisions with >$1K impact | CC/OC down or rate-limited |
| Research summaries | Conflicting data arbitration | Cross-Hale SSS certification |

## Example

```bash
ask-opus 'Analyze all three Viking Mars options for the Kuklinski group — stateroom categories, dining packages, excursion pre-purchase timing. Recommend the optimal package with full rationale.'
```

## Output location

Results print inline. File saved to `/home/john/Thunderbird/output/`.

---

## Reaching AG (Antigravity / Victory) — Peer Dispatch

For AG dispatch syntax, model rules, and path requirements, see the `/ask` skill or:
`standing_orders/SO_ASK_DISPATCH_CROSSENGINE_20260726.md` Section 2–6.

Quick reference:
```bash
python3 /home/john/Thunderbird/core/relay/contact_ag.py \
  "<task>" \
  --deliverable /home/john/Thunderbird/<ABSOLUTE_path>.md \
  --from OC --tag AG-VERIFY
  # Default model: "Gemini 3.1 Pro (High)" — never let it default to GPT-OSS 120B
```
