# RT-KEEPALIVES — Resolution (2026-08-07)
- **Commander:** slim/consolidate all keep-alives; straight-Linux; new-software; STOP 30-min Centrav spam.
- **AG (first seat):** KEEP/MERGE/KILL table; separate OAuth layer; supervisor=passive auditor w/ anti-flap deadband; kill centrav-warm + supertimer dupes; Playwright→HTTPS; NEW-software: Healthchecks.io/Gotify ADOPT, oauth_hub PARTIAL→60-line, Supercronic SKIP.
- **CC (AG-first):** caught root cause — 2026-07-16 already retired these at systemd, but supertimer infra_bot zombie tasks kept running (the live 30-min spam); corrected AG's dispositions (many already dead); flagged d2m-portal-live-probe standing-order conflict (active today despite 07-16 retirement) → Commander call.
- **Applied (Weapons-Free, Commander-ordered):** removed `centrav-warm` + `portal-keepalive` Task() from supertimer/bots/infra_bot.py; centrav-warm disabled in supertimer_infra_bot_state.json (+.bak). Verified compile.
- **Still OPEN (Commander call):** d2m-portal-live-probe standing-order conflict — keep or retire per 2026-07-16 order.
- **Backlog:** Healthchecks.io deadman integration; oauth_refresh_all.py consolidation; portal_http_probe.py (zero-browser).
