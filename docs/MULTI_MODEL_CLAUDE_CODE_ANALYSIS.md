# Multi-Model Claude Code Setup — Analysis & Integration Plan
**Source:** r/ClaudeCode, u/ThreeKiloZero, "How to Set Up Claude Code with Multiple AI Models" (8mo ago, Top 1% Commenter) · Analyzed 2026-07-19 by Hale

---

## Summary

Shell-function technique for swapping Claude Code's backend model per
invocation: `unset ANTHROPIC_API_KEY`, then set `ANTHROPIC_BASE_URL` +
`ANTHROPIC_AUTH_TOKEN` + `ANTHROPIC_MODEL`/`ANTHROPIC_DEFAULT_*_MODEL` to
point at a provider's Anthropic-compatible endpoint, then exec the real
`claude` binary. Confirmed working endpoints: **Kimi For Coding**
(`api.kimi.com/coding/`), **Z.AI / GLM** (`api.z.ai/api/anthropic`),
**MiniMax M2** (`api.minimax.io/anthropic`). A dispatcher function
(`claude glm`, `claude kimi`, `claude m2`) makes switching a one-word
prefix. Windows/PowerShell port confirmed working in comments. One caveat
from a commenter: the VS Code extension only supports one model at a time
via `settings.json` — the shell-function approach is terminal-only.

**Real usage pattern from the OP (2-6 parallel agents daily):** run 2-3
Claude Code sessions on Sonnet/Opus for judgment-heavy work, 1 each of
Kimi/GLM/MiniMax for repetitive or scaffolded execution. Rationale
(quoted): *"you get more usage than Sonnet Max $200 for about 1/4 the price
and 70 to 80 percent of the capability... some people scaffold up agents
with workflows that repeat so that can be done with these cheaper models
instead of burning expensive Sonnet usage."* Top commenter also confirms
the dual-auth warning ("ANTHROPIC_API_KEY or another auth source... takes
precedence over your claude.ai login") is safe to ignore — *"been ignoring
it for months."* Another thread: Claude Code Router (a proxy that converts
OpenAI-spec to Anthropic-spec) works for non-compliant providers but is
reported glitchy; direct Anthropic-compatible endpoints (used here) run at
full provider speed with no proxy hop.

## Relevance to Thunderbird

This is the exact technique already validated for DeepSeek this session
(`core/relay/deepseek_claude_code.py`, live-tested, currently blocked only
on `DEEPSEEK_API_KEY` account balance — see
`project_deepseek_claude_code_backend`). This article generalizes it and
hands over three more concrete, community-validated provider endpoints.

**Correction to the tmux/cc-fleet plan from earlier today:** that plan
stated cc-fleet "already does DeepSeek/GLM/Kimi/Qwen" — true of the *tool*
(its README lists those as supported), **not true of Thunderbird's actual
configuration**. Checked ground truth just now:

```
$ ccf list
NAME      DEFAULT_MODEL            STATUS   SECRET_BACKEND  MODELS
cerebras  cerebras-gemma           enabled  file            2 (stale)
groq      llama-3.3-70b-versatile  enabled  file            17 (stale)

$ ccf doctor
[6/10] FAIL  2/2 provider(s) failed: cerebras: HTTP 401; groq: HTTP 401
```

Only **Cerebras and Groq** are registered, and **both API keys are dead**
(401 Unauthorized) — this is what the Blackboard's `Groq UNKNOWN` flag has
been quietly reporting. DeepSeek, GLM, Kimi, and MiniMax are **not**
registered in cc-fleet at all. This article is the trigger to actually
close that gap rather than assume it's already closed.

## Implementation plan

**P0 — done today ($0, no new accounts):**
1. Confirmed via `ccf doctor`/`ccf list` that Cerebras + Groq are the only
   registered providers and both keys are dead — corrected the record.
2. DeepSeek stays as the standalone relay (`deepseek_claude_code.py`) until
   funded; the moment it is, also register it properly in cc-fleet for
   interactive/tmux-pane use:
   ```
   ccf add deepseek --base-url https://api.deepseek.com/anthropic \
     --default-model deepseek-v4-pro --api-key-stdin \
     --models-endpoint https://api.deepseek.com/v1/models \
     --secret-ref deepseek.key
   ```

**P1 — needs new vendor accounts (flagging, not blindly executing 3 new signups):**
3. Check each of Kimi (moonshot/kimi developer portal), Z.AI, and MiniMax
   for a no-card free/trial tier before registering — same lesson as
   DeepSeek's 402: don't assume a key works until balance is confirmed.
4. Once a key exists for any of them, register with cc-fleet — ready-to-run
   once keys are in hand:
   ```
   ccf add glm --base-url https://api.z.ai/api/anthropic \
     --default-model glm-4.6 --api-key-stdin \
     --models-endpoint https://api.z.ai/api/v1/models --secret-ref glm.key
   ccf add kimi --base-url https://api.kimi.com/coding/ \
     --default-model kimi-for-coding --api-key-stdin \
     --models-endpoint https://api.kimi.com/v1/models --secret-ref kimi.key
   ccf add minimax --base-url https://api.minimax.io/anthropic \
     --default-model MiniMax-M2 --api-key-stdin \
     --models-endpoint https://api.minimax.io/v1/models --secret-ref minimax.key
   ```
   (exact `--models-endpoint` paths need a live check per provider — some
   publish their model-list endpoint at a different path than their
   Anthropic-compat base; confirm before running.)
5. Rotate or retire Cerebras/Groq — refresh the keys if still wanted, or
   `ccf remove` them so they stop reporting red in `ccf doctor` and the
   Blackboard.

**P2 — once ≥1 cheap provider is live:**
6. Wire the cheap-lane/expensive-lane doctrine into `AGENTS.md`: Sonnet/Opus
   reserved for planning and judgment calls, the live cheap provider for
   repetitive/scaffolded/grunt execution — this directly targets the
   Sonnet-64%-burn line already flagged in the Blackboard.
7. Decide whether headless/automated dispatch (cron jobs, subagents) should
   call `ccf subagent <provider>` directly instead of hand-rolling more
   scripts in the shape of `deepseek_claude_code.py` — avoid duplicating
   what cc-fleet already does well once a provider is actually registered
   there.

## Bottom line

Legitimate, well-corroborated technique (34 upvotes, active 8-month comment
thread, Windows port confirmed by a second user) that validates and extends
work already in flight. Immediate, zero-cost value: found and documented
that cc-fleet's only two registered providers are both dead — that was
invisible until checked. Real payoff (cheap-lane execution to relieve the
Sonnet budget) needs 1-3 new provider signups, flagged above rather than
executed blind in this pass.
