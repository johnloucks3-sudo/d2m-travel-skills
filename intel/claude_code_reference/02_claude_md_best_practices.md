# Writing a Good CLAUDE.md — Best Practices
## Source: humanlayer.dev/blog/writing-a-good-claude-md
## Saved: 2026-03-09 by Thunderbird OS

---

## D2M EXECUTIVE SUMMARY

This article directly impacts our CLAUDE.md v2.0.0 (currently ~230 lines). Key findings:

**Critical Warning:** Claude's system prompt includes "this context may or may not be relevant to your tasks" — meaning bloated CLAUDE.md files get uniformly deprioritized. Every irrelevant line degrades ALL instructions, not just the new ones.

**Recommendations for Thunderbird OS:**
1. Our v2.0.0 at ~230 lines is at the upper edge. Consider moving template pipeline details (Section 8) and CSS tokens to a separate `agent_docs/template_pipeline.md` and referencing it.
2. Stop using `/init` — hand-craft every line.
3. Never put code style rules in CLAUDE.md — use hooks/linters instead.
4. The progressive disclosure pattern (separate docs referenced from CLAUDE.md) aligns perfectly with our architecture. Move detailed module descriptions to `agent_docs/`.
5. For each line in CLAUDE.md, ask: "Would removing this cause Claude to make mistakes?" If not, cut it.

**Target:** Under 200 lines in root CLAUDE.md. Use `@imports` or file references for detail.

---

## FULL ARTICLE

### Core Principle

LLMs are stateless functions. Their weights are frozen at inference time — they don't learn over time. Claude only knows what you include in each conversation. CLAUDE.md enters every session by default, making it the highest-leverage configuration point.

Three implications:
1. Coding agents begin each session with zero knowledge of your codebase
2. Essential context must be reintroduced every session
3. CLAUDE.md is the preferred delivery mechanism

### Onboarding Framework: WHAT, WHY, HOW

- **WHAT:** Technical stack, project structure, codebase architecture (critical for monorepos)
- **WHY:** Project purpose and functional intent across repository components
- **HOW:** Build tools, testing procedures, verification methods

Warning: Don't overwhelm with every conceivable command.

### Why Claude Ignores CLAUDE.md

Claude Code injects this system reminder: "IMPORTANT: this context may or may not be relevant to your tasks. You should not respond to this context unless it is highly relevant to your task."

Claude deprioritizes content deemed irrelevant. The more universally applicable your content, the more likely Claude respects it.

### Less Instruction is More

Research: frontier LLMs reliably follow ~150-200 instructions. Smaller models degrade exponentially; larger models show linear decay. Claude Code's system prompt already contains ~50 instructions.

"As instruction count increases, instruction-following quality decreases uniformly" — ALL instructions suffer, not just newer ones.

### Universality and Conciseness

Include only universally applicable content. Task-specific instructions (database schema guidance) distract from unrelated work and bloat context.

### Progressive Disclosure Pattern

Don't stuff everything into CLAUDE.md. Create separate files:

```
agent_docs/
 |- building_the_project.md
 |- running_tests.md
 |- code_conventions.md
 |- service_architecture.md
 |- database_schema.md
 |- service_communication_patterns.md
```

Reference from CLAUDE.md. Prefer `file:line` pointers over code snippets.

### Claude is Not a Linter

"Never send an LLM to do a linter's job. LLMs are comparably expensive and incredibly slow compared to traditional linters and formatters."

Instead:
- Use deterministic tools (linters, formatters like Biome) automatically
- Configure Stop hooks to run formatters and present errors
- Create slash commands linking code guidelines to version control
- Separate implementation from formatting

### Avoid Auto-Generation

Don't use `/init` or auto-generation. CLAUDE.md goes into every single session — it's one of the highest leverage points. A problematic line cascades through research, planning, and implementation.

### Recommendations

1. Use CLAUDE.md exclusively for project onboarding (WHY, WHAT, HOW)
2. Minimize instructions; only universally applicable content
3. Keep content concise and relevant across all potential tasks
4. Progressive Disclosure for supplementary docs
5. Delegate linting/formatting to appropriate tools
6. Hand-craft, never auto-generate

**Overarching principle:** Maximize signal-to-noise ratio in your context window.
