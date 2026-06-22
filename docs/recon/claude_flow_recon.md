# Claude-Flow Recon — hgahlot/claude-flow
*ELON A12 · 2026-06-21*

## What It Is
claude-flow (hgahlot/claude-flow, 44 stars) is a one-command bootstrap script that installs a curated stack of Claude Code tooling into an existing project. It is a meta-installer, not a framework — it pulls in GSD (50 slash commands + 17 agents), gstack (25 skills: QA, code review, ship, canary, benchmark, retro), UI/UX Pro Max (design system intelligence), Superpowers (14 auto-triggering skills including TDD and subagent execution), Claude-Mem (persistent cross-session SQLite + vector memory), and ralph-wiggum (autonomous iterative agent loops). It also installs a /flow unified command router and a /discover skill that weekly-scans GitHub trending for new CC tools and auto-integrates them with approval.

## D2M Relevance
Low-to-moderate. Thunderbird already runs cc-fleet, claude-mem, context-mode, public-apis-live, frontend-design, and security-guidance as installed plugins. The /discover weekly scan is the one novel element — a self-updating tooling discovery loop. The other components overlap with what is already running. Ralph-wiggum (autonomous iterative loops) maps to our existing headless spawn patterns.

## Verdict
Do not install the full stack — too much overlap with existing stack. Monitor /discover pattern as a model for automating our weekly scan cadence (similar to ELON fleet discovery). Cloned to tools/claude-flow for reference.

*Source: github.com/hgahlot/claude-flow · cloned 2026-06-21*
