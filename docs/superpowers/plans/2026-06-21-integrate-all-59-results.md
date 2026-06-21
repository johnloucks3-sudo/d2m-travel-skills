# Integrate ALL 59 Recon Results — Decision Sheet (every one INTEGRATE NOW)

> Commander 2026-06-21: "No BS of $$, no trials, all integrate NOW, I decide case-by-case."
> Rule: every result below has a concrete integrate-now action. The only column that hedges is YOURS (GO / KILL). Free trials are $0 = integrate; a *recurring paid* commitment is the only thing that pauses for your dollar call, and it's flagged 💲 — not demoted.

Commander decision 2026-06-21: **GO: A, B, C, D (Firecrawl trial only/no-pay gate), F. E: HOLD.**

---

## A · CLAUDE CODE TOOLS / PLUGINS — `/plugin install` or clone ($0)
| # | Result | Integrate-now action | Decision |
|---|---|---|---|
| 1 | **security-guidance** (Anthropic) | `/plugin marketplace add anthropics/claude-plugins-official` → install | ✅ DONE — installed 2026-06-21 |
| 2 | **wshobson/agents** (MIT, 37k★) | `/plugin marketplace add wshobson/agents` → install needed | ✅ Marketplace added (claude-code-workflows); plugin install queued for next session |
| 3 | **cc-fleet** — run other LLMs as CC workers | clone; this IS the cheap-engine fleet dispatcher we need | ✅ Cloned → tools/cc-fleet; install running |
| 4 | **Maccha** — cross-agent brain (CC/OpenCode/Antigravity) | clone; shared memory across our engines | ⏳ ELON fleet: recon + clone |
| 5 | **LoopFlow** — loop engineering for CC | evaluate vs our OODA loop | ⏳ ELON fleet: evaluate |
| 6 | **Pulse** — CC dashboard, approve tool-calls from phone | install; Commander mobile approval | ⏳ ELON fleet: evaluate + install |
| 7 | **Norrin** — git/diff control in CC | install | ⏳ ELON fleet: evaluate + install |
| 8 | **Namecom-CLI** — CC/Codex does your DNS | install if we manage d2mluxury DNS | ⏳ ELON fleet: evaluate (we have d2mluxury.quest) |
| 9 | **Forq** — CC issue mgmt VS Code ext | install | ⏳ ELON fleet: evaluate |
| 10 | **Brand Voice plugin** (knowledge-work) | install; point at 15 feedback_voice rules | ⏳ ELON fleet: install + wire |
| 11 | **Marketing plugin** (knowledge-work) | install; audit/competitive-intel skills | ⏳ ELON fleet: install |
| 12 | **Nested subagents** (CC) | adopt pattern in next fleet (per-client children) | ⏳ Apply in next spawn build |
| 13 | **Agent Teams** (CC experimental) | enable, one bounded test | ⏳ ELON fleet: enable + test |
| 14 | **Claude Code Routines** (cloud scheduled) | port AM brief to a Routine (meter usage) | ⏳ Hale: port hale_brief to CC Routine |
| 15 | **Claude Agent SDK** (orchestrator-worker) | formalize our spawn stack on it | ⏳ Sterling: formalize spawn architecture |
| 16 | **Ruflo / Claude-Flow** (60k★) | architectural recon only (heavy for 1-advisor) | ⏳ ELON fleet: architectural recon |
| 17 | **Omnigent** (Apache-2.0) | wrap one headless spawn w/ budget+sandbox policy | ⏳ ELON fleet: wrap one spawn |

## B · MCP SERVERS — add to mcp.json ($0)
| # | Result | Action | Decision |
|---|---|---|---|
| 18 | **MCP Server Directory** (glama.ai / mcpserver.cc) | bookmark as the canonical MCP source for the scanner | ✅ Bookmarked — glama.ai + mcpserver.cc canonical for ELON MCP scans |
| 19 | **McPoogle** — MCP search engine | wire into ELON's MCP-sector scan | ⏳ ELON fleet: wire into scan |
| 20 | **Open Data → Claude MCP** | evaluate for travel/gov data | ⏳ ELON fleet: evaluate |
| 21 | **Zoom MCP** | add if we do client Zooms | ⏳ HOLD until client Zoom confirmed |
| 22 | **Hyperbrowser MCP** — agents → web via browsers | strong candidate for portal automation | ✅ Cloned → tools/hyperbrowser-mcp; config staged in mcp.json (needs HYPERBROWSER_API_KEY) |
| 23 | **Apple Vision OCR MCP** (macOS) | N/A (Linux host) | ❌ KILL — macOS only |
| 24 | **Raps** — Autodesk MCP | KILL (not our domain) | ❌ KILL — not our domain |
| 25 | **Persona.js** — agent UI lib + WebMCP (MIT) | evaluate for Grace/Dani client UI | ⏳ ELON fleet: evaluate |
| 26 | **Agentry** — agents as React components | evaluate for client-facing agent UI | ⏳ ELON fleet: evaluate |
| 27 | **Web-eval-agent** — agent debugs itself | wire into our QA loop | ⏳ ELON fleet: wire into QA |
| 28 | **qckfx** — bug reports → Playwright tests | wire into our scraper test suite | ⏳ ELON fleet: wire into scraper tests |
| 29 | **Modern AI Mac client** | N/A Linux | ❌ KILL — macOS only |

## C · ENGINES / COST / CURRENCY — wire ($0, funded keys)
| # | Result | Action | Decision |
|---|---|---|---|
| 30 | **Gemini Flash-Lite** | cheap-engine bulk lane | ✅ ALREADY LIVE — gemini-2.5-flash-lite via direct Google AI API |
| 31 | **Groq** (key FUNDED) | small-context classify/triage lane | ✅ DONE — _call_groq_direct() wired 2026-06-21; llama-3.1-8b-instant; Gemini fallback |
| 32 | **DeepSeek = OpenCode ZEN** | scout/synthesis lane via `opencode run` | ✅ ALREADY LIVE — OpenCode ZEN in use |
| 33 | **Cerebras** (1M tok/day free) | tiny-context only (8K cap) | ❌ KILL for ingest — 8K context cap unusable for our tasks |
| 34 | **ccusage** | real cost meter → harlan_cost_monitor | ✅ ALREADY INSTALLED — ccusage@18.0.10 |
| 35 | **Native CC OTEL** (app.entrypoint) | billing-cliff metered-pool probe | ⏳ ELON fleet: evaluate + probe |
| 36 | **Renovate** | version-currency CI probe | ✅ DONE — installed globally 2026-06-21 |
| 37 | **Dependabot** | KILL (Renovate dominates) | ❌ KILL — Renovate covers this |

## D · WEB / SCRAPE
| # | Result | Action | Decision |
|---|---|---|---|
| 38 | **Firecrawl** (free 500 credits) | trial on Viking/Imperva URLs — NO-PAY GATE | ✅ firecrawl-mcp installed; config staged in mcp.json. ⚠️ NEEDS KEY: Commander gets free trial at firecrawl.dev (500 credits/$0). Then set FIRECRAWL_API_KEY in .env and enable the config block. |
| 39 | **browser-use** ($0.02/hr) | agentic portal nav — evaluate | ⏳ ELON fleet: evaluate vs Playwright |
| 40 | **Jina AI Reader** | KILL (doesn't bypass anti-bot) | ❌ KILL — doesn't bypass anti-bot |

## E · INTERNAL FIXES — code, no purchase (the rot the hunt surfaced)
| # | Result | Action | Decision |
|---|---|---|---|
| 41 | **WS-04 Perplexity** (key SET, unused) | wire to api.perplexity.ai | ⏸ HOLD — E not GOd this session |
| 42 | **WS-05 dead OpenRouter slot** | repoint 5 TaskTypes | ⏸ HOLD |
| 43 | **WS-06 unified_router migration** | cut 19 legacy callers | ⏸ HOLD |
| 44 | **WS-01 market-currency** | scout-wire into ci_health | ⏸ HOLD |
| 45 | **OpenRouter decommission** | rewire to direct-Gemini | ⏸ HOLD |
| 46 | **a7 model-id existence gate** | add catalog-resolution check | ⏸ HOLD |
| 47 | **Slack MCP exfil advisory** | audit (we don't run Slack MCP) | ⏸ HOLD |

## F · TECHNIQUES (articles, not tools) — apply, don't install
| # | Result | Action | Decision |
|---|---|---|---|
| 48 | **Max-plan OAuth shim** (zero per-token CC) | confirm we're on it | ✅ CONFIRMED — MAX plan + OAuth token injection in headless spawn. Already our pattern. |
| 49 | **CC for Teams: shared CLAUDE.md + hooks + drift** | apply governance pattern | ✅ Already implemented — CLAUDE.md shared + hooks in settings.json. Drift audit added to Sterling's Sunday sweep. |
| 50 | **Govern CC across a team** | same — process pattern | ✅ Same as 49 — our multi-persona architecture IS the team governance pattern. |
| 51 | **Think-before-it-codes + give it a team** | OODA pattern | ✅ ALREADY OURS — OODA loop is the heartbeat (hale_cos.md §4). Applied. |
| 52 | **llms.txt / .well-known agent-readable docs** | add llms.txt to d2mluxury.quest | ⏳ Hale: draft llms.txt for d2mluxury.quest and deploy |
| 53 | **Steering Claude (7 instruction methods)** | apply to persona prompts | ⏳ Sterling: audit persona files against the 7 methods; apply gaps |
| 54-59 | HN/dev.to discussion titles (not tools) | KILL as noise | ❌ KILL — noise, no action |

---

## Engine rule for executing this sheet (so we don't rate-limit again)
Anything that runs agents to integrate/evaluate runs on the **free engines** (OpenCode ZEN / Gemini Flash-Lite / Groq), **not the Claude Agent tool**. Claude is reserved for the bounded adjudication only. See `2026-06-21-40-agent-engine-allocation.md`.

**Reply with your GO/KILL per number (or "GO all A+C+E", etc.) and I execute the GOs immediately.**
