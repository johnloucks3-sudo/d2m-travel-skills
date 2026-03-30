# RATE LIMIT STATUS
# Updated manually by Commander or any agent when budget changes.
# Agents check this before routing any task to Claude during 0600-1800 MT.

Updated: 2026-03-30T02:00:00MT
Claude Sonnet: YELLOW — rate-limited, 28hr recovery window as of 0100 MT
Groq: GREEN — available, high RPM, no PII
Deepseek: GREEN — available, arbitration only, no PII
Goose (Gemini): GREEN — primary model during Commander operational hours
Gemini Flash: GREEN — auto-fallback when Claude depleted (existing router)

Budget thresholds:
  GREEN  = < 60% daily usage
  YELLOW = 60-80% daily usage (route to Goose where possible)
  RED    = > 80% daily usage (mandatory Goose-first, Claude only on /use claude override)

---
UPDATE LOG (append below):
[2026-03-30T02:00:00MT] | Claude | Initialized. Claude YELLOW — rate-limited.
