# ELON Fleet — Phase 2 Results
*A12 ELON · 2026-06-21 · Integration-59 Phase 2 Evaluation*

---

## A — CC Plugins

- `❌ A4 Maccha` — no GitHub repo found under any search variant (maccha+claude, maccha+agent, maccha+cross-agent); name may be internal or vaporware; cannot clone
- `❌ A5 LoopFlow` — no GitHub repo found (loopflow+claude+code, loopflow+loop+engineering); name may be aspirational or misremembered; cannot clone
- `❌ A6 Pulse` — no GitHub repo found (pulse+claude+dashboard+mobile, pulse+claude+code+approval); no installable plugin; cannot clone
- `❌ A7 Norrin` — not found in any configured marketplace (tried `claude plugins install norrin`); no GitHub repo hit; likely unmaintained or never published
- `❌ A8 Namecom-CLI` — no GitHub repo found (namecom+dns+mcp, namecom+claude); no MCP server or CC plugin for Name.com DNS management exists in indexed sources
- `❌ A9 Forq` — no GitHub repo found; qckfx/qckfx turns out to be iOS screenshot testing, not GitHub issue management; Forq as described does not exist
- `❌ A10 Brand Voice (knowledge-work)` — `knowledge-work/claude-plugins` repo does not exist on GitHub; `claude plugins install brand-voice` fails in all 6 configured marketplaces; plugin is not published
- `❌ A11 Marketing plugin (knowledge-work)` — same as A10: knowledge-work org/repo not found; `claude plugins install marketing` fails; plugin not published
- `✅ A12 Nested Subagents pattern` — documented per-client children pattern; written to `/home/john/Thunderbird/docs/patterns/nested_subagents.md`
- `⏳ A13 Agent Teams (CC experimental)` — `claude agent-teams --help` resolves to top-level CC help (not a subcommand); the `--agents` JSON flag IS available for inline agent definition; no dedicated `agent-teams` experimental mode found in this CC version; feature may be available via `--agents '{"name": {...}}'` flag
- `⏳ A14 CC Routines` — `claude routines --help` resolves to top-level CC help (not a subcommand); Routines is a cloud-scheduled feature accessible via Claude.ai dashboard, not via CLI flag; schedule a routine at claude.ai/settings/routines
- `✅ A15 Claude Agent SDK` — confirmed real: `@anthropic-ai/claude-agent-sdk` v0.3.185 on npm (223 versions published); Anthropic publishes it; description: "SDK for building AI agents with Claude Code's capabilities"; source: github.com/anthropics/claude-agent-sdk-typescript; NOT `@anthropic-ai/agent-sdk` (404) — correct package name is `claude-agent-sdk`
- `✅ A16 Ruflo/Claude-Flow (hgahlot)` — found as hgahlot/claude-flow (44 stars, not 60k — may be confused with a different repo); cloned to `tools/claude-flow`; 200-word summary written to `docs/recon/claude_flow_recon.md`; it is a meta-installer for GSD+gstack+Superpowers+Claude-Mem+ralph-wiggum+/flow router
- `✅ A17 Omnigent (Apache-2.0)` — confirmed real at omnigent-ai/omnigent (4,296 stars); cloned to `tools/omnigent`; headless-wrap-with-budget pattern written to `docs/recon/omnigent_recon.md`; alpha status, Python 3.12+, policy governance + cloud sandbox + budget cap

---

## B — MCP Evaluation

- `✅ B19 McPoogle` — real tool: graphlit/mcpoogle-mcp-server-remote (2 stars); MCP search engine for 7000+ MCP server READMEs; remote MCP endpoint at https://mcp.mcpoogle.com/sse; alpha; cloned to `tools/mcpoogle`; add as disabled entry in mcp.json: `{"mcpoogle": {"url": "https://mcp.mcpoogle.com/sse", "enabled": false}}`
- `✅ B20 Open Data → Claude MCP` — real: lzinga/us-gov-open-data-mcp (103 stars); 300+ tools, 40+ US gov APIs (Treasury, FRED, Congress, FDA, CDC, FEC); 20+ APIs require no key; `npx us-gov-open-data-mcp` to run; cloned to `tools/us-gov-open-data-mcp`; low direct D2M value (travel/gov data mismatch) but FRED economic data + transport APIs are adjacent
- `⏳ B25 Persona.js + WebMCP` — WebMCP is a W3C-adjacent browser API standard (`navigator.modelContext`), not a CC plugin; multiple CC skills found that implement WebMCP on websites (mstublefield/claude-skill-webmcp, getmasset/webmcp-skill); Persona.js as a standalone package not found; these are web-dev tools for making websites AI-accessible, not Thunderbird-relevant
- `✅ B26 Agentry` — real: colinds/agentry (8 stars); React-component model for AI agents — define behavior declaratively, compose agents like components, supports Anthropic + OpenAI; cloned to `tools/agentry`; interesting pattern for future Wing UI if we ever build a React frontend for client ops
- `⚠️ B27 Web-eval-agent` — SUNSET: refreshdotdev/web-eval-agent (1,241 stars) is discontinued; the repo README says "PROJECT HAS BEEN SUNSET"; the operative.sh MCP server is the active replacement (operative.sh/mcp); cloned to `tools/web-eval-agent` for reference; active tool is browser-use-powered and available at operative.sh
- `❌ B28 qckfx` — misidentified in Phase 1 research; qckfx/qckfx (9 stars) is an iOS visual regression screenshot testing tool, not a bug-report→Playwright pipeline; not relevant to our web scraper suite

---

## C — Native CC OTEL

- `✅ C35 Native CC OTEL` — confirmed: CC exposes full OTEL stack via env vars (no CLI flags); key vars: `OTEL_RESOURCE_ATTRIBUTES` (custom labels on metrics), `OTEL_METRICS_INCLUDE_ENTRYPOINT=true` (tags app.entrypoint per spawn), `OTEL_LOG_TOOL_DETAILS=1` (tool parameters in telemetry); recon written to `docs/recon/cc_otel_recon.md`; immediate action: add OTEL env vars to thunderbird_headless_spawn.py for per-persona attribution

---

## D — Browser Automation

- `✅ D39 browser-use` — real and massive (99,903 stars, Python, MIT); AI-native browser automation via LLM reasoning over DOM (not selectors); verdict written to `docs/recon/browser_use_recon.md`; recommendation: keep as break-glass for portals that defeat Playwright; Centrav + Regent stay on Playwright; not installed (pip install browser-use when needed)

---

## Summary Stats
- Items evaluated: 26
- Repos found + cloned: 7 (omnigent, claude-flow, agentry, web-eval-agent, mcpoogle, us-gov-open-data-mcp, claude-agent-sdk confirmed on npm)
- Plugins installed: 0 (none found in marketplace)
- Not found / vaporware: 10 (Maccha, LoopFlow, Pulse, Norrin, Namecom-CLI, Forq, brand-voice, marketing plugin, Persona.js, qckfx-as-described)
- Sunset: 1 (web-eval-agent → operative.sh replacement)
- Recon docs written: 4 (claude_flow_recon, omnigent_recon, browser_use_recon, cc_otel_recon)
- Pattern docs written: 1 (nested_subagents)

## Top Actionable Findings
1. **Claude Agent SDK** (`@anthropic-ai/claude-agent-sdk` v0.3.185) — Anthropic's own SDK for building agents programmatically. Install and evaluate for Wing automation.
2. **CC OTEL** — wire `OTEL_RESOURCE_ATTRIBUTES` + `OTEL_METRICS_INCLUDE_ENTRYPOINT=true` into thunderbird_headless_spawn.py now. Zero code cost, immediate attribution visibility.
3. **Omnigent** — alpha but architecturally aligned with our budget/policy gate doctrine. Watch for stable release; trial on internal (non-client-path) spawns.
4. **McPoogle** — useful for MCP server discovery; add as disabled entry to mcp.json, enable when evaluating new MCPs.

*— ELON, A12 Innovation & Disruption · 2026-06-21 18:45 MT*
