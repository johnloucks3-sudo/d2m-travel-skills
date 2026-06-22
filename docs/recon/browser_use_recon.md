# Browser-Use vs Playwright — Portal Automation Verdict
*ELON A12 · 2026-06-21*

## Browser-Use
browser-use/browser-use (99,903 stars, Python, MIT) is an AI-native browser automation library: an LLM drives a real browser by reasoning about the DOM, not by executing pre-written selectors. The agent sees the page, decides what to click, and adapts when layouts change. Cost: ~$0.02/hr on their cloud tier; self-hosted is free but requires an LLM API key per run.

## Our Playwright Stack
Our Playwright scrapers (Centrav, Regent, Princess portals) use session-cookie injection + hardcoded CSS selectors (see `core/travel/data/centrav_ff_profile`). They are fast, deterministic, and free at runtime. Failure mode: selector rot when portals update their UI.

## Verdict (150 words)
Keep Playwright as primary. Browser-use solves a different problem: it handles portal UIs that change constantly and resist selector-based scraping. Our Regent and Centrav portals are relatively stable; our existing selenium/Playwright patterns with fresh cookies work. Browser-use would add LLM API cost per automation run ($0.02/hr minimum), introduce non-determinism (the LLM might mis-click), and require more complex error handling. Where browser-use wins: any net-new portal we have not yet scripted, or portals behind Cloudflare/bot-detection where our current approach fails. Recommendation: keep browser-use in tools/ as a break-glass option for portals that defeat Playwright. Centrav and Regent stay on Playwright. If a new portal proves unscrapable with selectors, trial browser-use on that target only — per the default-ADOPT + client-path canary doctrine.

*Source: github.com/browser-use/browser-use · not yet installed (pip install browser-use) · 2026-06-21*
