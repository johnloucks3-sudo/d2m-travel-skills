# Claude Code OTEL / Telemetry Recon
*ELON A12 · 2026-06-21*

## Does CC Expose OTEL?
Yes. Claude Code ships a native OpenTelemetry (OTEL) integration, documented in the CC changelog (confirmed in ~/.claude/cache/changelog.md). Key facts:

**Available OTEL features (as of current CC version):**
- `OTEL_RESOURCE_ATTRIBUTES` — custom labels on all metric datapoints, sliceable by team or repo
- `claude_code.lines_of_code.count` — OTEL metric with `model` attribute attached
- `app.entrypoint` attribute on OTEL metrics (opt-in via `OTEL_METRICS_INCLUDE_ENTRYPOINT=true`) — identifies which entrypoint (session, headless -p, etc.) generated a metric
- `tool_decision` telemetry events — include `tool_parameters` (bash commands, MCP/skill names) when `OTEL_LOG_TOOL_DETAILS=1`
- Security fix: untrusted project settings can no longer set OTEL client-certificate paths without trust confirmation

**No OTEL-specific CLI flags** on `claude --help` — OTEL is configured via environment variables, not CLI flags.

## D2M Application
The `app.entrypoint` metric + `OTEL_RESOURCE_ATTRIBUTES` gives us per-persona, per-session token/tool-call attribution without any custom code. Set `OTEL_RESOURCE_ATTRIBUTES=persona=ELON,wing=thunderbird` on headless spawns and `OTEL_METRICS_INCLUDE_ENTRYPOINT=true` to differentiate interactive vs headless runs in the metrics stream. This directly feeds Sterling's CI metrics dashboard without building a custom attribution layer.

**Next step:** Wire OTEL_RESOURCE_ATTRIBUTES into thunderbird_headless_spawn.py environment injection (alongside CLAUDE_CODE_OAUTH_TOKEN) so every spawn is automatically tagged. Route output to an OTEL-compatible endpoint (Prometheus + Grafana, or just log to a local file with the OTEL text exporter).

*Source: ~/.claude/cache/changelog.md (CC native) · 2026-06-21*
