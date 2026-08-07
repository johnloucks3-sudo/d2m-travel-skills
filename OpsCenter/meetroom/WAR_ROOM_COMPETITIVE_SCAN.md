# WAR ROOM — COMPETITIVE SCAN (evening 2026-08-06, web-lane)
_Source: live web search (5 lanes). Perplexity lane down (401 expired key — flagged for rotation). Real links, no fabrication._

## Bottom line
Someone HAS built it, advanced + flashy: **ATO** is a drop-in "multi-LLM war-room" — open-source, free, MIT — closer to our exact concept than anything else found. **Recommendation: prototype ATO before we build more of our own.**

## The 5 to choose from
| # | Name | URL | What it actually is | Fit note |
|---|---|---|---|---|
| 1 | **ATO — Agentic Tool Optimization** | agentictool.ai (github WillNigri/Agentic-Tool-Optimization) | Multi-LLM **war-rooms**: Claude/Codex/Gemini seats in one room, tool-call receipts, replay, sessions, "kill the runaway," real-time shared team workspaces, browser↔desktop tether, MCP server, local-first, MIT, **free** | 🎯 Nearest. Seats + receipts + replay = our 6 principles, already built. Desktop app, not web-deck |
| 2 | **LangGraph Studio + LangSmith** | langchain.com | "First agent IDE" — visualize/debug agent graphs, per-node state, **interrupt + replay** a step | Orchestration + debug/replay (no human-meeting framing) |
| 3 | **AgentOps** | agentops.ai | Agent observability: **session timeline**, **time-travel rewind/replay** of multi-agent runs, cost, 400+ LLM/framework integrations | The replay/recorder layer, production-grade |
| 4 | **ChatDev 2.0 (DevAll)** | github.com/OpenBMB/ChatDev | Zero-code multi-agent platform: visual canvas, drag-drop workflows, live logs, **human-in-the-loop**, web console + SDK | The "agents talk in a room" builder UI |
| 5 | **llm-war-room / War Room (community)** | github.com/harris-mohamed/war-room · github.com/tienshen/llm-war-room | Open-source LLM **council/debate**: officers of differing persona, several rounds, CEO ruling, streamed live in browser | Closest to "Commander at the table — seats debate, you decide" |

## Worth stealing vs refused (appraisal)
**Steal:**
- ATO: seat-receipts, real-time shared room, kill-the-runaway, MCP-to-agent. Model-agnostic, open.
- AgentOps: session replay/timeline for the recorder layer.
- llm-war-room: structured multi-round debate → referee/CEO ruling (mirrors Commander presides).

**Refuse (heavier than we need):**
- Zoom/Meet/LiveKit (no voice) · LangGraph full graph rewrite (overkill; we'd throw away our simpler harness) · ChatDev full platform (whole env).

## ADOPT-vs-BUILD (one-liner)
**Adopt ATO (or fork it) as the engine; keep our HTML deck + `rt_view.py` as the Commander-facing briefing surface if ATO's dev-flavored UI doesn't fit a briefing feel.** Build only the thin glue we still lack — don't re-derive a war-room.

## Caveats / flagged
- ATO is a **Tauri desktop app** (mac/win/linux) — is is our `d2mluxury.quest` web surface; model keys local. Check desktop vs web before committing.
- ATO targets **code** (tool-call reviews) more than the "4 AI staff brief a Commander" persona — we'd bend it to our seat/brief model. Verify before adopting.
- ChatDev 2.0 web console is a credible "meeting room" alternative if we prefer a maintained UI to a desktop CLI.