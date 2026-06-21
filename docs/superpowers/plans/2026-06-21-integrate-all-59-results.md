# Integrate ALL 59 Recon Results — Decision Sheet (every one INTEGRATE NOW)

> Commander 2026-06-21: "No BS of $$, no trials, all integrate NOW, I decide case-by-case."
> Rule: every result below has a concrete integrate-now action. The only column that hedges is YOURS (GO / KILL). Free trials are $0 = integrate; a *recurring paid* commitment is the only thing that pauses for your dollar call, and it's flagged 💲 — not demoted.

Mark each: **GO** (integrate now) · **KILL** (drop, logged with reason) · **HOLD** (you want more first).

---

## A · CLAUDE CODE TOOLS / PLUGINS — `/plugin install` or clone ($0)
| # | Result | Integrate-now action | Decision |
|---|---|---|---|
| 1 | **security-guidance** (Anthropic) | `/plugin marketplace add anthropics/claude-plugins-official` → install | ☐ |
| 2 | **wshobson/agents** (MIT, 37k★) | `/plugin marketplace add wshobson/agents` → install needed | ☐ |
| 3 | **cc-fleet** — run other LLMs as CC workers | clone; this IS the cheap-engine fleet dispatcher we need | ☐ |
| 4 | **Maccha** — cross-agent brain (CC/OpenCode/Antigravity) | clone; shared memory across our engines | ☐ |
| 5 | **LoopFlow** — loop engineering for CC | evaluate vs our OODA loop | ☐ |
| 6 | **Pulse** — CC dashboard, approve tool-calls from phone | install; Commander mobile approval | ☐ |
| 7 | **Norrin** — git/diff control in CC | install | ☐ |
| 8 | **Namecom-CLI** — CC/Codex does your DNS | install if we manage d2mluxury DNS | ☐ |
| 9 | **Forq** — CC issue mgmt VS Code ext | install | ☐ |
| 10 | **Brand Voice plugin** (knowledge-work) | install; point at 15 feedback_voice rules (watch .mcp.json) | ☐ |
| 11 | **Marketing plugin** (knowledge-work) | install; audit/competitive-intel skills | ☐ |
| 12 | **Nested subagents** (CC) | adopt pattern in next fleet (per-client children) | ☐ |
| 13 | **Agent Teams** (CC experimental) | enable, one bounded test | ☐ |
| 14 | **Claude Code Routines** (cloud scheduled) | port AM brief to a Routine (meter usage) | ☐ |
| 15 | **Claude Agent SDK** (orchestrator-worker) | formalize our spawn stack on it | ☐ |
| 16 | **Ruflo / Claude-Flow** (60k★) | architectural recon only (heavy for 1-advisor) | ☐ |
| 17 | **Omnigent** (Apache-2.0) | wrap one headless spawn w/ budget+sandbox policy | ☐ |

## B · MCP SERVERS — add to mcp.json ($0)
| # | Result | Action | Decision |
|---|---|---|---|
| 18 | **MCP Server Directory** (glama.ai / mcpserver.cc) | bookmark as the canonical MCP source for the scanner | ☐ |
| 19 | **McPoogle** — MCP search engine | wire into ELON's MCP-sector scan | ☐ |
| 20 | **Open Data → Claude MCP** | evaluate for travel/gov data | ☐ |
| 21 | **Zoom MCP** | add if we do client Zooms | ☐ |
| 22 | **Hyperbrowser MCP** — agents → web via browsers | strong candidate for portal automation | ☐ |
| 23 | **Apple Vision OCR MCP** (macOS) | N/A (Linux host) — KILL unless on a Mac | ☐ |
| 24 | **Raps** — Autodesk MCP | KILL (not our domain) | ☐ |
| 25 | **Persona.js** — agent UI lib + WebMCP (MIT) | evaluate for Grace/Dani client UI | ☐ |
| 26 | **Agentry** — agents as React components | evaluate for client-facing agent UI | ☐ |
| 27 | **Web-eval-agent** — agent debugs itself | wire into our QA loop | ☐ |
| 28 | **qckfx** — bug reports → Playwright tests | wire into our scraper test suite | ☐ |
| 29 | **Modern AI Mac client** | N/A Linux — KILL | ☐ |

## C · ENGINES / COST / CURRENCY — wire ($0, funded keys)
| # | Result | Action | Decision |
|---|---|---|---|
| 30 | **Gemini Flash-Lite** | cheap-engine bulk lane (built scaffold) — fleet scout engine | ☐ |
| 31 | **Groq** (key FUNDED) | small-context classify/triage lane | ☐ |
| 32 | **DeepSeek = OpenCode ZEN** (corrected: no key, via ZEN) | scout/synthesis lane via `opencode run` | ☐ |
| 33 | **Cerebras** (1M tok/day free) | tiny-context only (8K cap) — KILL for ingest | ☐ |
| 34 | **ccusage** | real cost meter → harlan_cost_monitor | ☐ |
| 35 | **Native CC OTEL** (app.entrypoint) | billing-cliff metered-pool probe | ☐ |
| 36 | **Renovate** | version-currency CI probe | ☐ |
| 37 | **Dependabot** | KILL (Renovate dominates) | ☐ |

## D · WEB / SCRAPE
| # | Result | Action | Decision |
|---|---|---|---|
| 38 | **Firecrawl** (free 500 credits) | trial on Viking/Imperva URLs; 💲$19/mo decision = yours | ☐ |
| 39 | **browser-use** ($0.02/hr) | agentic portal nav — evaluate (wrong shape for fetch) | ☐ |
| 40 | **Jina AI Reader** | KILL (doesn't bypass anti-bot) | ☐ |

## E · INTERNAL FIXES — code, no purchase (the rot the hunt surfaced)
| # | Result | Action | Decision |
|---|---|---|---|
| 41 | **WS-04 Perplexity** (key SET, unused) | wire to api.perplexity.ai; kill OpenRouter detour | ☐ |
| 42 | **WS-05 dead OpenRouter slot** | repoint 5 TaskTypes to live lane; kill false telemetry | ☐ |
| 43 | **WS-06 unified_router migration** | cut 19 legacy callers over; grep-guard | ☐ |
| 44 | **WS-01 market-currency** | internal scout-wire into ci_health (no tool) | ☐ |
| 45 | **OpenRouter decommission** (model_router/safeguards) | rewire to direct-Gemini + regression-assert | ☐ |
| 46 | **a7 model-id existence gate** | add catalog-resolution check | ☐ |
| 47 | **Slack MCP exfil advisory** | audit if we run Slack MCP (we don't — note + close) | ☐ |

## F · TECHNIQUES (articles, not tools) — apply, don't install
| # | Result | Action | Decision |
|---|---|---|---|
| 48 | **Max-plan OAuth shim** (zero per-token CC) | this is our $0 MAX pattern — confirm we're on it | ☐ |
| 49 | **CC for Teams: shared CLAUDE.md + hooks + drift** | apply governance pattern to our CLAUDE.md | ☐ |
| 50 | **Govern CC across a team** | same — process pattern | ☐ |
| 51 | **Think-before-it-codes + give it a team** | OODA pattern, already partly ours | ☐ |
| 52 | **llms.txt / .well-known agent-readable docs** | add llms.txt to d2mluxury.quest | ☐ |
| 53 | **Steering Claude (7 instruction methods)** | apply to persona prompts | ☐ |
| 54-59 | HN/dev.to discussion titles (not tools) | KILL as noise (the kill-pass already flagged these) | ☐ |

---

## Engine rule for executing this sheet (so we don't rate-limit again)
Anything that runs agents to integrate/evaluate runs on the **free engines** (OpenCode ZEN / Gemini Flash-Lite / Groq), **not the Claude Agent tool**. Claude is reserved for the bounded adjudication only. See `2026-06-21-40-agent-engine-allocation.md`.

**Reply with your GO/KILL per number (or "GO all A+C+E", etc.) and I execute the GOs immediately.**
