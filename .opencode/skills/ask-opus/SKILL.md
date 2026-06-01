---
name: ask-opus
description: "Spawn Claude CC (Opus) headless with full Wing context. Use for complex reasoning, strategy decisions, architecture decisions, anything requiring deep analysis. Triggers on: /ask-opus, ask opus, dispatch opus, opus headless, deep reasoning, complex strategy"
---

# /ask-opus — Spawn Claude CC Headless (Opus)

Same as /ask but routes to Claude Opus — premium reasoning, slower, more thorough.
Use when: complex strategy decisions, architecture choices, multi-factor analysis,
anything where Sonnet quality isn't enough.

## How to invoke

```bash
ask --opus 'task description here'
```

## When to use /ask-opus vs /ask

| Use /ask (Sonnet) | Use /ask-opus (Opus) |
|---|---|
| Client email drafting | Architecture decisions |
| Trip validation | Complex strategy analysis |
| Itinerary generation | Multi-factor reasoning |
| Routine Wing procedures | Decisions with >$1K impact |
| Research summaries | Conflicting data arbitration |

## Example

```bash
ask --opus 'Analyze all three Viking Mars options for the Kuklinski group — stateroom categories, dining packages, excursion pre-purchase timing. Recommend the optimal package with full rationale.'
```

## Output location

Results print inline. File saved to `/home/john/Thunderbird/output/`.
