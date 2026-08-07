# RT-LOGOFF — Recurring OC auto-logoff (War Room session)
**Opened:** 2026-08-07 ~07:05 MT · **Status:** INVESTIGATING · **Missions:** MISSION-794 · **Invoker:** OC (authorized any-HALE)

## Symptom
OpenCode (OC) session auto-logs-off / disconnects **repeatedly** (hand 3–4× across 2026-08-06→07, incl. tonight) — interrupts work, "auto logged off" inputs from Commander.

## Evidence gathered
- Grenlt off is **NOT** Telegram-gateway related (clean since 06:43) and not a normal crash-traceback.
- opencode.log: many `created ... "New session"` + `exiting loop` cycles = reconnect cycling.
- **GO spend over $10 cap** (meter: $11.55, 115%).
- account.json: `active.opencode-go` (API key) present; **no `plan`/`zen`/`credit` field surfaced** → GO plan state opaque from config.
- **GO default model** is `anthropic/claude-sonnet-4-6` (MAX) for the main path + **agents default to `opencode/deepseek-v4-flash-free`** (ZEN free).
- opencode.json has **no explicit `opencode`/`zen` provider** → built-in Go/ZEN layer governs; can't locally force "free independent of GO" without opencode product support.

## Hypotheses (rank)
1. **GO credit exhaustion** → OpenCode terminates/throttles the session (even ZEN) at full-account level. ← strongest, unproven.
2. **Auth/token refresh race** (opencode-go key) → intermittent re-auth loop.
3. **Terminal/tty network drop** (tmux/UI) cycling the client.

## CONFIRMED priority
- **Partial:** Agents already default to `deepseek-v4-flash-free` ($0/ZEN) — if those were GO-billed, ZEN isn't independent. Kill every non-free route (paid `deepseek-v4-flash`) so ZEN is the ONLY lane → GO exposure → $0 → GO cap never binds → log-off driver (h1) starved.

## Action plan (Commands)
1. Disable/pin the non-free `deepseek-v4-flash` (Poe) route + verify NO session uses a paid node.
2. Deep-probe opencode.log for a GO/plan/enforce line at the exact disconnect timestamps (New session churn boundaries) to CONFIRM h1 vs h2.
3. Confirm ZEN free lane continues while GO over-cap (test call) — if ZEN blocked → document OpenCode-product coupling; pursue config/account fix (e.g., disable the opencode-go auth so it falls back to anonymous/ZEN?).
4. If h2 (token refresh): check for refresh/expiry lines at disconnect time.
5. Record verdict + repairs to this file & commit. Under DOC-MANDATORY.

## Standing
- Commander: "GO funding should not influence OpenCode ZEN." → target end-state: **GO cap is decoupled — ZEN/free never gated by GO funding.**
- War Room standing: this is a mandatory-priority subject.

— Victory | RT-LOGOFF session