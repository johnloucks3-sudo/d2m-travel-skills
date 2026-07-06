# Console/Email Parity — Baseline Snapshot (2026-07-06)

Baseline for the new quarterly `scripts/parity_audit.py` routine. Confirms
the state described in `docs/CONSOLE_VS_EMAIL_CAPABILITY_BASELINE_20260706.md`
is durable and mechanically checkable, not just true on the day it was built.

## Why parity holds by construction, not by coincidence

Both paths resolve to the literal same file, `~/.claude/mcp.json`:

- **Console** — Claude Code loads this as its MCP server config directly.
- **Email** — `core/email/hale_email_responder.py` sets
  `GLOBAL_MCP_CONFIG = "/home/john/.claude/mcp.json"` and passes it to
  `spawn_headless_claude(..., mcp_config=GLOBAL_MCP_CONFIG)`.

Because it's one file referenced from two places (not two files kept in
sync by hand), there is no drift to accumulate — until someone points the
email path at a different file. That's the one failure mode this audit
exists to catch.

## Result as of 2026-07-06

Ran `python3 scripts/parity_audit.py`:

| Check | Result |
|---|---|
| Same config file | Yes — both resolve to `/home/john/.claude/mcp.json` |
| MCP servers (Console) | 7: `dreams2memories`, `elevenlabs`, `gmail-d2mconcierge`, `google-workspace-d2mconcierge`, `google-workspace-johnloucks3`, `mcpoogle`, `thunderbird-qdrant` |
| Tool list divergence | None |
| `CLAUDE.md` present | Yes |
| `Personas/hale_cos.md` present | Yes |
| Headless spawn overrides `cwd` | No — child inherits cwd, so the spawned agent auto-loads the same `CLAUDE.md`/persona files Console does |

**Zero divergence, confirmed mechanically, not just asserted in the baseline doc.**

## The one honest, permanent difference: latency

Console is a live synchronous session. Email is async — inbound message →
timer detects it → headless spawn → research → write → send, on the order
of minutes. That gap is a property of the channel (nobody expects an email
reply in 3 seconds) and is explicitly **not** a parity target — see
`docs/CONSOLE_VS_EMAIL_CAPABILITY_BASELINE_20260706.md` for the reasoning
against closing it further.

## Standing routine

See CLAUDE.md § "Parity Audit — Quarterly." Next runs: 2026-10-01,
2027-01-01, 2027-04-01, 2027-07-01 (or immediately, off-cycle, if either
`~/.claude/mcp.json` or `core/email/hale_email_responder.py`'s
`GLOBAL_MCP_CONFIG` is edited).
