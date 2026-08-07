# RT-CLAUDEP — Resolution (2026-08-07)
- **Problem:** headless `claude -p` hung / "Invalid API key"; `/ask` mapping muddled; Sonnet-5 unavailable.
- **AG (first seat) root cause (tested):** ANTHROPIC_API_KEY env pollution overrides OAuth; retired model-id `claude-haiku-4-5-20251001`; unclosed stdin in Popen; missing --mcp-config. Test: env.idx+OAuth+`--model haiku` → 11.2s OK; sonnet → 8.1s OK.
- **CC (AG-first) endorsed:** must-ship = default model→`haiku` + `stdin=DEVNULL`.
- **Applied (Weapons-Free, Commander approved continued):** `thunderbird_headless_spawn.py:153` model→`haiku`; `:399` add `stdin=subprocess.DEVNULL`. Escalation tiers already `["haiku","sonnet","opus"]`.
- **Verified (ground truth):** `claude -p --model haiku --mcp-config ...` → `FIX_OK`, rc 0, no hang.
- **/ask family:** maps to contact_ag (gemini-3.6-flash-high / gemini-3.1-pro-high / claude-sonnet-4-6). Sonnet-5 does NOT exist in agy/Anthropic catalog — use claude-sonnet-4-6.
