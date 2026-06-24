

# OPENCODE HALE INIT — Key Protocols

## D2M EMAIL TEMPLATE — HARD RULE (2026-06-23, CANONICAL — CORRECTED)
ALL D2M client emails MUST use `scripts/d2m_email_builder.py` — never build email HTML from scratch.
CANONICAL format = FULL DARK NAVY throughout (NOT cream body — that was the old, retired format).
Source: Kuklinski Panama December email sent 2026-06-20. Commander directive: this IS the template.

Colors (bgcolor ATTRIBUTE survives Gmail; CSS gradient = enhancement only):
- Outer: `bgcolor="#07076b"` | Header: `bgcolor="#0a0a68"` | Body: `bgcolor="#08086e"` | text `color:#e8f1ff`
- Shimmer bars: `bgcolor="#c8d8ff"` 3px | Dani sig: `bgcolor="#040448"` | Commander: `bgcolor="#02022a"`
- ❌ NEVER use `bgcolor="#f7f3ea"` (cream) for client emails — RETIRED

Builder: `python3 scripts/d2m_email_builder.py --body [body.html] --to [addr] --subject "[s]" [--name "First"]`
Template: `storage/templates/d2m_canonical_darknavy.html` ({{BODY_CONTENT}} placeholder)

## EOD + INCUBATOR (SO-EOD-INCUBATOR-20260610)
- 1730 MT: Nomination ping → Telegram. 5-min window. No reply = execute.
- 1800 MT: EOD brief → johnloucks3. 4 sections (prose Done List, tight Search section).
- Overnight: build gate candidate. AM brief surfaces results.
- Config: `OpsCenter/eod_incubator_config.json` | Full SO: `standing_orders/SO_EOD_INCUBATOR_PROTOCOL_20260610.md`

# BLACKBOARD_START — auto-updated by blackboard_sync.py — do not edit manually
<!-- Last sync: 2026-06-24 08:34 MT -->
```
=== THUNDERBIRD BLACKBOARD [2026-06-24 08:34 MT] ===
Budget: Claude MAX Wkly-40% | Sonnet-46% | Runs-9/15 | Sess-4% | OpenCode GREEN | Groq UNKNOWN | Deepseek UNKNOWN
Active tasks: 0
Last Deepseek ruling: NONE
Open items: none logged
Next priority: check session_autosave_latest.md
Standing: Claude=judgment | OpenCode=ops | Deepseek=arbitrator | PII fence: Deepseek
Session checkpoint: /home/john/Thunderbird/session_autosave_latest.md
Full blackboard: /home/john/Thunderbird/OpsCenter/collaboration/blackboard.md
================================================
```
# BLACKBOARD_END
