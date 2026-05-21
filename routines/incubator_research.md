# Routine: /incubator-research
## AI Incubator — Research Pipeline

Research a specific question or technology for potential adoption in Thunderbird OS.

Given a research prompt, I will:
1. Search the web for current information
2. Evaluate against these criteria:
   - Cost: $0 or Claude MAX (no OpenRouter, no paid APIs)
   - Integration effort: days vs weeks
   - Maintenance burden: self-hosted vs managed
   - Replacement risk: would this replace an existing component?
3. Classify: IMPLEMENT / PROTOTYPE / WATCH / SKIP
4. If IMPLEMENT or PROTOTYPE, outline the minimal first step

Output format:
```
## [Topic]
**Classification:** [IMPLEMENT | PROTOTYPE | WATCH | SKIP]
**Why:** 1-2 sentence rationale

### What I found
Key findings from research

### How to start (if implement/prototype)
Step-by-step first action

### Alternatives considered
Other approaches that don't fit as well
```
