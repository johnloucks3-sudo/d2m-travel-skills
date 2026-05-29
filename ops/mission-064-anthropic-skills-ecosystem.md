# MISSION-064: Anthropic Skills Ecosystem Investigation

**Classification:** Intelligence Report  
**Date:** 2026-05-25  
**Analyst:** A7 Sterling  
**Status:** Complete  

---

## 1. Executive Summary

Anthropic launched **Claude for Small Business** on May 13, 2026 — a one-click plugin bundling 15 agentic workflows and 31 reusable skills across finance, sales, marketing, customers, HR, and operations, wired into 12+ connectors (QuickBooks, PayPal, HubSpot, Canva, DocuSign, Google Workspace, Microsoft 365, Slack, Stripe, Square). The skills follow the open **Agent Skills Specification** (`agentskills.io`) — a directory of `SKILL.md` with YAML frontmatter (`name`, `description`, `license`, `metadata`, `compatibility`, `allowed-tools`) plus optional `scripts/`, `references/`, and `assets/` subdirectories. Distribution is decentralized: an official Anthropic marketplace ships with every Claude Code install, community marketplaces (GitHub repos with `marketplace.json`) host 2,000+ third-party skills, and package managers like `skm`, `ccpm`, `skills-market`, and `skillstore.io` provide CLI/MCP-based discovery. No single app-store chokepoint exists — anyone can create a marketplace by pushing a `.claude-plugin/marketplace.json` to a Git repo. Day-one downloads hit ~382K, proving massive demand. For D2M's skill builder pipeline, this validates skill development as a distribution channel: we can publish travel-domain skills (itinerary planning, cruise booking workflows, supplier price lookups) via our own GitHub marketplace or third-party registries, reaching Claude Code / Claude Cowork users directly. Lock-in risk is low — the spec is MIT-licensed and platform-agnostic (skills work on Claude Code, Codex CLI, Cursor, Gemini CLI, Copilot, Windsurf, and others). Recommendation: **build and publish 3-5 D2M travel operations skills** targeting the vertical gap Anthropic's SMB launch explicitly leaves open (deep domain expertise is the unmet need).

---

## 2. What Anthropic's Small-Business Skills Are

### 2.1 The Product

Claude for Small Business is an **add-on capability layer** inside Claude Cowork (Anthropic's agent-forward desktop app). It is not a standalone product — it ships at no extra cost on top of existing Claude Pro, Max, or Team subscriptions.

It bundles three things:
- **15 ready-to-run agentic workflows** — multi-step orchestrations with defined inputs/outputs (e.g., `/close-month` reconciles books, flags mismatches, writes a P&L narrative, exports a close packet)
- **31 reusable skills** (originally reported as 15 + 15, actual count is 31 bundled) — modular capabilities invoked conversationally (e.g., "draft an invoice chase sequence")
- **12+ connectors** — QuickBooks, PayPal, HubSpot, Canva, DocuSign, Google Workspace, Microsoft 365, Slack, Stripe, Square

### 2.2 Skill Categories (31 skills)

From Charlie Hills' breakdown and Anthropic's official materials:

| Category | Count | Examples |
|---|---|---|
| Money / Finance | 10 | Payroll planner, monthly close, invoice chaser, margin analyzer, tax organizer, cash-flow forecaster |
| Sales & CRM | 6 | Lead triager, contract reviewer, deal scorer |
| Marketing | 3 | Content strategist, campaign manager, asset generator (Canva) |
| Customer Service | 4 | Ticket triage, draft replies, escalation |
| Briefings | 3 | Morning brief, business insights, weekly snapshot |
| Setup, Hiring & Legal | 5 | `/smb-onboard`, HR onboarder, contract reviewer, hiring packet builder |

### 2.3 Skill Format & Structure

The **Agent Skills Specification** (open standard at `agentskills.io`, MIT-licensed) defines:

```
skill-name/
├── SKILL.md          # Required: YAML frontmatter + Markdown instructions
├── scripts/          # Optional: executable code (Python, JS, etc.)
├── references/       # Optional: supporting documentation
├── assets/           # Optional: templates, resources
└── ...
```

**`SKILL.md` frontmatter (YAML):**

| Field | Required | Constraints |
|---|---|---|
| `name` | Yes | Max 64 chars, lowercase + hyphens only |
| `description` | Yes | Max 1024 chars, what it does and when to use it |
| `license` | No | SPDX identifier or reference |
| `compatibility` | No | Max 500 chars, env requirements |
| `metadata` | No | Arbitrary key-value pairs (author, version, category, etc.) |
| `allowed-tools` | No | Experimental tool allowlist |

**Progressive disclosure model:**
1. **Metadata** (~100 tokens) — `name` + `description` loaded at startup for all skills
2. **Instructions** (<5000 tokens recommended) — full `SKILL.md` body loaded on activation
3. **Resources** — scripts/references loaded on-demand via tool calls

**Versioning:** Not enforced by the spec — handled by marketplace/distribution layer. Community tools like `skm` use semver tags; Anthropic's plugin system pins to commit SHAs.

### 2.4 Key Design Pattern: Workflow ≠ Skill

- **Workflow** = multi-step orchestration with fixed flow and approval gates (e.g., "run the month-end close")
- **Skill** = focused capability invoked conversationally (e.g., "summarize this month's PayPal settlements")
- Workflows *compose* skills + connectors + routing logic

---

## 3. How Skills Are Distributed

### 3.1 Marketplace Architecture

Anthropic chose a **decentralized, Git-repo-as-marketplace** model — not an app store.

```
marketplace.json  (at repo root .claude-plugin/marketplace.json)
├── name: "my-marketplace"
├── plugins:
│   ├── name: "my-plugin"
│   │   source: ./plugins/my-plugin      (relative path)
│   │   └── skills/, commands/, agents/, hooks/
│   ├── name: "external-plugin"
│   │   source:
│   │     github: org/repo
│   │     ref: v1.0.0
```

### 3.2 Available Marketplaces

| Marketplace | Source | Scope | Size |
|---|---|---|---|
| **Anthropic Official** | `anthropics/claude-plugins-official` | Auto-installed; curated by Anthropic | ~50 plugins |
| **Anthropic Skills Repo** | `anthropics/skills` | Public; community contributed | 139K stars, 16K forks |
| **Community Marketplace** | `anthropics/claude-plugins-community` | Automated validation + safety screen | ~200 plugins |
| **daymade/claude-code-skills** | GitHub | 52 production-ready skills | 1.1K stars |
| **claudekit-skills** | `mrgoonie/claudekit-skills` | Plugin marketplace format | 2K+ stars |
| **skills-market** | `Equality-Machine/skills-market` | Open marketplace, NPX-installable | Catalog UI + MCP bridge |
| **AI Skillstore** | `aiskillstore/marketplace` | Security-audited, review-gated | ~100 skills |
| **AaaS Vault** | `ibossyNr1/aaas-vault` | 5,400+ skills, 52 categories | Largest registry |
| **TonsofSkills** | Community | 425 plugins, 2,810 skills | Package manager `ccpi` |

### 3.3 Installation Methods

**A. Plugin Marketplace (Recommended, Claude Code):**
```bash
/plugin marketplace add owner/repo
/plugin install plugin-name@marketplace-name
```

**B. Direct Git Clone (Manual):**
```bash
git clone https://github.com/owner/skills ~/.claude/skills/skill-name
```

**C. Package Managers:**
- **`skm`** — `skm install skill-name` (symlinks, semver, multi-registry)
- **`ccpm` / `claude-skills-mcp`** — npm-based, Supabase registry, MCP protocol
- **`skills-market`** — `npx skills-market install skill-name`, auto-detects agent homes
- **`npx skills add`** — Anthropic's own tool for the `anthropics/skills` repo

### 3.4 Distribution Model

- **No centralized app store** — anyone can create a marketplace from a GitHub repo
- **No approval gate** for community marketplaces (unlike Anthropic official)
- **Plugin signing and provenance** not yet implemented (expected within 12 months)
- **Private marketplaces** supported for team/internal distribution

### 3.5 Adoption Trajectory

- **Day-one downloads:** ~382K (May 13, 2026)
- **Community marketplaces:** 2,000+ third-party skills shipped as of May 2026
- **Official marketplace:** "hundreds of plugins" per Anthropic docs
- **Skills.sh ecosystem:** Indexing multiple registries via `skm`
- **AaaS Vault:** 5,400+ skills, the largest curated registry
- **TonsofSkills:** 425 plugins, 2,810 skills with its own CLI package manager
- The trajectory mirrors early npm — explosive community growth, quality variance, consolidation expected within 12-18 months

---

## 4. Relevance to D2M's Skill Builder Pipeline

### 4.1 Direct Applicability

D2M's skill builder pipeline (`skill-creator` skill, SKILL.md authoring, validation tools) maps **directly** onto the Agent Skills Specification. Our existing pipeline already produces the same format Anthropic and the community use.

**What matches:**
- `SKILL.md` with YAML frontmatter — our standard output format
- `name`/`description` metadata — already in our templates
- `scripts/` for executable code — our Python tooling
- `references/` for support docs — our references directory pattern
- Progressive disclosure — we already structure for this

**What's new:**
- `marketplace.json` packaging for distribution
- Plugin wrapping (skills → plugins) for the Claude Code ecosystem
- `allowed-tools` experimental field
- Multi-platform compatibility headers

### 4.2 Strategic Opportunity

The SMB launch exposes a **vertical gap** that analysts have explicitly identified:

> *"If you are in a deep vertical that needs domain expertise — SAP, Salesforce, legal, medical, construction — you are better served by a focused skill pack."* — CLSkills review

> *"QuickBooks is the most heavily integrated connector. Gaps remain in Shopify, ServiceTitan, Jobber."* — Self Employed review

**D2M can fill the travel operations vertical** — a domain no one has addressed in the skill ecosystem. Travel agency workflows (itinerary construction, cruise booking verification, supplier price lookups, multi-client trip coordination, commission reconciliation) are complex, repetitive, and AI-augmentable — exactly the pattern Anthropic's skill architecture targets.

---

## 5. Recommendations

### 5.1 Build Skills for Distribution (Yes)

**Priority: High.** The ecosystem is early, the spec is open, distribution is free (GitHub), and the travel vertical is empty.

**Recommended category: Travel Operations for Claude Cowork & Claude Code**

Suggested 3-5 skill candidates:

| Skill | Description | Connector Potential |
|---|---|---|
| `itinerary-builder` | Construct multi-day trip itineraries from supplier data, verify timing/transfers, output PDF | Google Sheets, Canva, DocuSign |
| `cruise-cost-compare` | Pull cabin prices from multiple lines, compare amenities, flag best-value options | (manual input or future API) |
| `invoice-reconciler` | Match supplier invoices against client bookings, flag discrepancies | QuickBooks, PayPal |
| `trip-dossier-generator` | Compile client trip dossier from booking data, supplier contacts, hotel confirmations | Google Docs, Canva |
| `client-portal-emailer` | Draft and send personalized portal activation emails with trip details | Gmail, HubSpot |

### 5.2 Distribution Strategy

1. **Publish a D2M marketplace** — GitHub repo with `.claude-plugin/marketplace.json` listing travel plugins
2. **Submit to community marketplace** — `anthropics/claude-plugins-community` for auto-validation
3. **Register on skillstore.io** — security-audited, higher trust signal
4. **List on skills.sh** — `skm` package manager ecosystem
5. **Optional: publish via npm** — for `npx` install pattern

### 5.3 Technical Investment Required

- Adapt skill-creator to output `marketplace.json` alongside `SKILL.md`
- Add `compatibility` field generation (target: `Claude Code 2.0+`, `Claude Cowork`)
- Add `allowed-tools` for skills that need Bash/File I/O
- Implement plugin wrapping (skills + optional commands/hooks/agents)
- Set up CI pipeline with skill validation (`npx skill-validate`)

### 5.4 Timing

**Window: Q2-Q3 2026.** The ecosystem is in the "hobbyist → professional" transition. Early curated publishers will establish credibility before the expected consolidation wave. Target: publish MVP marketplace by July 2026.

---

## 6. Risk Assessment

### 6.1 Lock-in Risk: LOW

**Mitigating factors:**
- Agent Skills Specification is **MIT-licensed** and platform-agnostic
- Skills work on Claude Code, Codex CLI, Cursor, Gemini CLI, Copilot, Windsurf, Cline, Goose, Aider, and more
- The spec is owned by `agentskills.io` (community), not Anthropic
- Git-based distribution means zero platform dependency for hosting

**Residual risk:**
- Anthropic controls the official marketplace inclusion (their discretion)
- `allowed-tools` is experimental and may evolve
- If Anthropic shifts to a proprietary format, community support for the open spec may fragment

### 6.2 Ecosystem Opportunity: HIGH

**Positive signals:**
- 382K day-one downloads
- 2,000+ community skills in 2 months
- 5,400+ skills in the largest registry
- Multiple competing package managers (signals demand)
- Analyst consensus: ecosystem will grow and consolidate
- Anthropic's own pattern (vertical skills + connectors) is repeatable

### 6.3 Specific Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Skill quality fragmentation | High | Low | Our skills will be curated, vetted, production-grade |
| Anthropic changes spec | Medium | Medium | MIT license allows forking; we can maintain own compliance |
| Discovery overload | Medium | Medium | Register on multiple marketplaces; leverage branded presence |
| Connector availability | High (for travel APIs) | Medium | Design skills to degrade gracefully without connectors |
| Competitor enters travel vertical | Medium | Medium | First-mover advantage; deep domain specificity |

### 6.4 Overall Verdict

**Proceed.** The ecosystem opportunity substantially outweighs lock-in risk. The travel operations vertical is unoccupied, the distribution cost is near-zero, and D2M's existing skill builder pipeline is already compatible with the Agent Skills Specification. The risk of *not* entering is higher — the ecosystem will consolidate around established publishers within 12 months.

---

## 7. Sources

- Anthropic official: [Claude for Small Business announcement](https://www.anthropic.com/news/claude-for-small-business)
- Anthropic docs: [Plugin marketplace system](https://code.claude.com/docs/en/discover-plugins)
- Anthropic docs: [Create plugin marketplaces](https://code.claude.com/docs/en/plugin-marketplaces)
- Agent Skills Specification: [agentskills.io/specification](https://agentskills.io/specification)
- Claude for Small Business plugin page: [claude.com/plugins/small-business](https://claude.com/plugins/small-business)
- Forbes coverage (May 14, 2026)
- SiliconANGLE coverage (May 13, 2026)
- The Verge coverage (May 13, 2026)
- Charlie Hills Substack: 31-skill breakdown
- CLSkills review: gap analysis
- GitHub: `anthropics/skills`, `daymade/claude-code-skills`, `Equality-Machine/skills-market`, `aiskillstore/marketplace`

---

*End of report. Prepared by A7 Sterling for Dreams2Memories Travel, LLC.*
