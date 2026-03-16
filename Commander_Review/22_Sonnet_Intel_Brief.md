# Claude Sonnet 4.6 Intelligence Brief — March 10, 2026
## Thunderbird OS Strategic Intel

---

### Summary

Claude Sonnet 4.6 released February 17, 2026. Same price as Sonnet 4 ($3/$15 per 1M tokens) but dramatically better — within 1.2 points of Opus on coding benchmarks, 70% preferred over previous Sonnet. Essentially Opus-class intelligence at 1/5 the cost.

**ACTION TAKEN:** `thunderbird_model_router.py` updated from `claude-sonnet-4-20250514` to `claude-sonnet-4-6-20250514`

---

### Key Benchmarks

| Benchmark | Sonnet 4.6 | vs. Opus 4.6 |
|-----------|-----------|-------------|
| SWE-bench Verified (coding) | 79.6% | Within 1.2 pts |
| OSWorld (computer use) | 72.5% | Within 0.2% |
| ARC-AGI-2 (novel reasoning) | 58.3% | — |
| Head-to-head preference | 70% over Sonnet 4.5 | 59% over Opus 4.5 |

---

### Three Game-Changers for Thunderbird

**1. Adaptive Thinking**
- No more manually toggling extended thinking
- Auto-scales reasoning depth — thinks hard on commission math, stays fast on lookups
- Interleaves thinking between MCP tool calls — Sheets→Drive→email chains more coherent

**2. Context Compaction (Beta)**
- Auto-summarizes older context before hitting limits
- Custom summarization instructions preserve booking IDs, client names, commission figures
- Huge for long booking pipeline sessions

**3. 1M Context Window (Beta)**
- Feed entire cruise comparison reports or multiple dossiers for cross-analysis
- Guinea pig itinerary work can leverage this

---

### Other Anthropic Initiatives

| Initiative | Relevance |
|-----------|-----------|
| Claude Cowork | Desktop agentic capabilities for knowledge work (macOS preview) |
| Skills Platform | Org-wide skill management for Team/Enterprise |
| Claude Code Security | Automated codebase vulnerability review |
| SSE/HTTP MCP transport | Broadening remote MCP support (mobile access goal) |
| Claude Agent SDK | Renamed from Code SDK — Sonnet 4.6 recommended model for agents |

---

### On the Horizon: Claude 5 "Fennec"

- Codename "Fennec" for Sonnet 5 — appeared in Google Vertex AI logs
- Expected Q2-Q3 2026
- Rumored: coding surpassing Opus 4.6, "Dev Team" multi-agent mode, ~50% lower pricing
- **Action:** Watch, no action yet

---

### Model Router Change Log

```
# Before (2026-03-10)
CLAUDE_MODEL = "claude-sonnet-4-20250514"

# After (2026-03-10)
CLAUDE_MODEL = "claude-sonnet-4-6-20250514"
```

Same price. Better output. Immediate upgrade.

---

*Intel gathered and synthesized by Thunderbird OS — March 10, 2026*
