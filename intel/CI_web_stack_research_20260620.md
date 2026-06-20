# CRITICAL-INFRASTRUCTURE WEB STACK RESEARCH
## Portal Access (Playwright replacement) + Anansi Enhancer
**Author:** Lt Col Marcus "Wraith" Dembe, A2 · **Date:** 2026-06-20 · **Classification:** Internal / Wing
**Tasking:** Commander directive 2026-06-20 — cruise-line portal access is Critical-Infrastructure.

---

## BOTTOM LINE UP FRONT

The discriminating axis is **bot-wall TYPE, not tool popularity.** Our four portal walls each need a different fix, and the hardest one (Imperva rate-limit that blocked the Commander's own residential IP) **is not solved by any browser swap** — it is an IP-reputation problem.

Independent 2026 benchmark evidence (Paterson 651-verdict test; techinz multi-system harness; PROXIES.SX Akamai/Imperva guide) converges on one finding: modern anti-bot is a **layered trust score** — IP reputation + TLS/JA4 fingerprint + behavioral ML — and you must beat **all three layers**, not one. (Confidence: HIGH on the *architecture* — three independent sources agree. Per-tool rankings below are MODERATE — they rest partly on vendor blogs and search summaries, not yet on our own portal tests.)

**Key scoping caveat (changes the spend):** We are logging into **D2M's own legitimate accounts**, not evading defenses on hostile/adversary sites. For keep-a-session-warm against our own portals, a **clean residential proxy — or even a single stable, non-flagged IP — very likely suffices. Mobile proxy is probably an over-buy.** The "undetectable stack" / mobile-proxy framing in the cited guide comes from a proxy vendor and assumes a hostile-scraping mission; do not let it inflate the spend at the financial gate.

- **(a) Portal-access CI tool → ADOPT Camoufox run headed with a persistent profile (one tool = Akamai bypass + keep-warm) + a clean residential proxy / stable IP (IP layer).** Self-hostable, free software, ~$29–99/mo proxy (residential, not mobile). Weakest link: the proxy spend is a **new line item** (none configured in the codebase today) and is a **Commander financial gate**.
- **(b) Anansi enhancer → ADOPT Trafilatura (self-host, free, single-digit-ms) as the default clean-extract pass; WATCH Jina AI Reader (r.jina.ai) as the zero-setup fallback.** Weakest link: neither renders JS — keep Anansi `--browser` for SPA pages.

---

## GROUND-TRUTH CHECK (codebase, this session)
- **No residential/mobile proxy provider configured anywhere** — grep across `*.py/*.json/.env` returned only stdlib/SDK internal `_proxy.py` files and two incidental log mentions. **Proxy access = new spend, Commander gate.** (Confidence: HIGH.)
- Anansi (`Arachne`) exposes `fetch / mcp / crawls`; `--browser` headless + `--proxy` live on the `fetch` subcommand per prior ground truth.

## OUR FOUR WALLS, MAPPED TO FIX TYPE
| Portal | Wall type | What actually fixes it |
|---|---|---|
| **Finnair (reference)** | TLS/JA4 fingerprint | curl_cffi — **already works, don't re-buy** |
| **Regent (Akamai/ASPXAUTH)** | TLS + behavioral; kills headless keepalive | Stealth browser w/ real Chrome/FF TLS + **persistent profile** (no headless keepalive) |
| **Centrav (laravel_session)** | Light/session | Persistent-profile driver; already near-working via `centrav_serve.py` |
| **Viking (CloudFront 403)** | Header/UA/WAF | Header/UA correction; often no stealth browser needed |
| **Imperva (blocked Commander's IP)** | **Rate-limit / IP reputation** | **Clean residential/mobile proxy — NO browser swap fixes this** |

---

# TASK 1 — PLAYWRIGHT REPLACEMENT (portal access: auth capture + bot-wall bypass + keep-warm)

| Tool | What (one line) | Case (fit for D2M portal) | Rec |
|---|---|---|---|
| **Camoufox** | Firefox fork, C++-level fingerprint patches; 0% headless-detection; `proxy=`+`humanize=True` built in | **Best fingerprint+behavioral layer for Regent/Akamai.** Real FF TLS, authentic JA4/canvas/WebGL, human mouse/scroll. ~200MB/inst, ~42s on Turnstile — fine for low-volume portal logins. Self-host, free. | **Adopt** |
| **Patchright** | Drop-in Playwright(Node) fork; patches Chromium at build (kills Runtime.enable/HeadlessChrome leaks); `channel=chrome` real TLS | Passes nowsecure/Cloudflare; **varies on Akamai/PerimeterX behavioral**. Best path if we stay on Playwright/Node. Self-host, free. | **Adopt** (Chromium lane) |
| **nodriver** | Direct-CDP successor to undetected-chromedriver; no Playwright shim; persistent user-data-dir | Wins on **basic** detection, lightest (~80–120MB), **excellent for keep-warm via persistent profile** — but **blocked on Akamai v4 behavioral** (no fake mouse/scroll/keystroke). Good for Centrav/Viking, not Regent alone. Self-host, free. | **Adopt** (light/keep-warm lane) |
| **undetected-chromedriver** | Selenium-based UC; older anti-detect patches | Superseded by nodriver from same author; heavier, Selenium baggage. | **Skip** |
| **playwright-stealth (v2.x)** | Python JS-injection stealth plugin; active (v2.0.2 Apr 2026) | Beats basic walls; JS-injection is detectable by Object.defineProperty guards; weaker than binary-patch tools on Akamai. | **Watch** |
| **playwright-extra (stealth)** | Node stealth plugin | **No meaningful update since Mar 2023; ineffective vs Akamai v4/Cloudflare Ent.** | **Skip** |
| **CloakBrowser** | Patched Chromium, 49 C++ fingerprint mods, drop-in Playwright API | Mid-pack in Paterson benchmark; custom binary license; less battle-tested than Camoufox. | **Watch** |
| **Botasaurus** | All-in-one Selenium-based framework; bundles botasaurus-requests (hrequests-derived), header/cipher ordering, UA rotation | Convenience wrapper; anti-detect is real but Selenium-rooted; weaker ceiling vs Camoufox/nodriver on Akamai behavioral. | **Watch** |
| **hrequests** | Python HTTP+browser hybrid w/ browser-like TLS/header ordering | TLS-layer tool (curl_cffi class). Overlaps what curl_cffi already gives us. | **Skip** (redundant) |
| **curl_cffi / curl-impersonate** | Python curl wrapper spoofing TLS/JA4, no JS engine | **Already in our kit; beats TLS-fingerprint walls (Finnair). Does NOT beat rate-limit or behavioral.** Keep for what it's for. | **Adopt** (already have — don't re-spend) |
| **browser-use** | LLM-driven DOM-first agent over Playwright | Inherits Playwright's detection profile unless paired w/ stealth; LLM token cost per step. Automation *brain*, not a bot-wall *fix*. | **Watch** |
| **Stagehand** | LLM browser automation, native Browserbase integration | Same: agent layer, not stealth layer. Useful atop a hosted stealth browser. | **Watch** |
| **Skyvern** | Vision+DOM agent, 3-phase loop (85.85% WebVoyager v2) | Strong autonomous form/login navigation; still needs a stealth/IP layer underneath for protected portals. | **Watch** |
| **Steel.dev** | Hosted stealth browser API; $29/mo (290 hrs, 2.9GB proxy, CAPTCHA solves), $99/mo popular | **Bundles browser + clean IP + CAPTCHA in one** — absorbs the proxy problem. Open foundation. Recurring spend, Commander gate. | **Watch → Adopt-if-no-self-host-appetite** |
| **Browserbase** | Hosted stealth browser; free 1hr, $20/mo dev, $99 startup; proxy ~$10–12/GB; persistent sessions+replay, Stagehand-native | Polish/DX leader; **persistent sessions = keep-warm solved**; clean IP pool included. Recurring spend. | **Watch → Adopt-if-no-self-host-appetite** |
| **Hyperbrowser** | Hosted browser, ~$0.10/browser-hr, credit-based | Cheapest hosted; best when browser is one piece of a larger agent build. | **Watch** |

### Task-1 read
- **No single tool wins.** Beating Regent (Akamai) needs Camoufox/Patchright (fingerprint+behavioral). Beating the **Imperva rate-limit needs a clean IP** — software alone fails. Keeping Regent's ASPXAUTH warm needs a **persistent real-browser profile**, not headless keepalive (which Akamai already kills).
- Confidence the **layered model is correct: HIGH.** Confidence in any **vendor "beats Akamai" marketing claim: LOW** until we test against our own portals.

---

# TASK 2 — ANANSI ENHANCER (faster/cleaner non-auth content extraction)

| Tool | What (one line) | Case (fit vs Anansi for plain fetch) | Rec |
|---|---|---|---|
| **Trafilatura** | Heuristic Python extractor, no ML/GPU, **single-digit ms/page**; best mean F1 (0.883) across 8-dataset benchmark | **Beats Anansi on speed + clean-text quality for article/static pages.** Free, self-host, trivial dep. Pipe Anansi/curl HTML → Trafilatura → markdown. No JS render. | **Adopt** (default clean pass) |
| **Jina AI Reader (r.jina.ai)** | URL→clean markdown via hosted API, no browser | **Zero-setup fallback** — free + instant single-URL, rate-limited; token tier $0.02/1K. Basic JS render, **no anti-bot.** Good for ad-hoc/one-off. | **Watch / Adopt-as-fallback** |
| **Crawl4AI** | Self-host Python crawler, full JS render, LLM-ready markdown, free | **Best self-host when JS render IS needed** (where Trafilatura/Jina fail). More setup than Trafilatura; overlaps Anansi `--browser`. | **Watch** |
| **Firecrawl** | Hosted crawl/extract API; full Playwright JS render, schema extract, `/crawl` `/map`; free 500 credits, paid from $16/mo | Production full-site crawl + structured JSON; **overkill + recurring cost** for our single-page fetches. Self-host version "still isn't there." | **Skip** (for fetch); revisit if we need site-wide crawl |
| **ScrapeGraphAI** | LLM-graph-driven extraction | Pulls an LLM into every fetch — token cost + latency for a job heuristics already do. | **Skip** |
| **Markdowner** | Lightweight URL→markdown service | Thin Jina-class alternative; less proven. | **Skip** |
| **Reader-LM** | Small LM that converts HTML→markdown | Model-based; heavier than Trafilatura for the same output on clean pages. | **Skip** |

### Task-2 read
- For **non-authenticated content**, Trafilatura **beats Anansi head-to-head** on speed (ms vs browser-class latency) and clean-text F1, at zero cost and near-zero setup. It is a *complement*: feed it Anansi/curl-fetched HTML.
- Neither Trafilatura nor Jina renders JS — **keep Anansi `--browser`** (or Crawl4AI) for SPA/JS pages. This is the named weakest link of the enhancer pick.

---

## TOP RECOMMENDATIONS

### (a) Portal-access CI tool
**ADOPT a two-layer stack, self-host-first:**
1. **Automation/fingerprint layer — Camoufox, run headed with a persistent `user_data_dir`.** For Regent this is **one tool doing both jobs**: Camoufox beats the Akamai fingerprint/behavioral layer AND its persistent profile keeps the ASPXAUTH session warm (no separate keep-warm tool needed). **nodriver** is the light lane for Centrav/Viking (lighter, persistent profile, fine where there's no heavy behavioral wall). Both free, self-host. Patchright if we want to stay in the Playwright/Node API.
2. **IP layer — a clean residential proxy, or potentially just a single stable non-flagged IP.** This is the part software cannot replace and the only thing that fixes the Imperva rate-limit. The vendor guide rates mobile-proxy+stealth at 89–95% against Akamai/Imperva — but that figure is **a proxy vendor's own number (LOW confidence, commercial bias) for hostile scraping.** For our own-account logins, residential is almost certainly enough; **do not over-buy mobile.**
3. **Keep-warm — persistent user-data-dir profile** (folded into #1), never headless keepalive (Akamai kills it; this is exactly the Regent ASPXAUTH failure we already logged).

**Conditional fork (decision the Commander owns — it's a spend gate):**
- **If proxy budget is approved** → self-host Camoufox/nodriver + ~$29–99/mo residential/mobile proxy. Lowest recurring cost, highest maintenance burden (our problem to run).
- **If we'd rather not self-host the stack** → **Browserbase or Steel.dev** absorbs browser + clean IP + CAPTCHA + persistent sessions in one bill ($20–99/mo). Higher recurring cost, near-zero maintenance. Browserbase = best DX/persistence; Steel = more open.

**Weakest link (named):** We have **no proxy access today** and the Imperva wall is an **IP-reputation** problem — so any "just swap the browser" plan fails the exact case that burned the Commander. The proxy line is a Commander financial gate. **Confidence: HIGH** on the diagnosis and the two-layer architecture (three independent sources); **MODERATE** on the per-tool rankings (partly vendor-blog / search-summary sourced, not yet tested against our own portals) and on which specific proxy/host wins until tested against Regent + the Imperva-walled portal with a clean IP. The 89–95% bypass figure is **LOW confidence** — proxy-vendor marketing.

### (b) Anansi enhancer
**ADOPT Trafilatura** as the default clean-extraction pass behind Anansi/curl for static + article content (free, self-host, single-digit ms, top F1). **WATCH/keep Jina AI Reader** as the zero-setup fallback for ad-hoc single URLs.
**Weakest link (named):** **No JS rendering** in either — SPA/JS-heavy pages still route through Anansi `--browser` or Crawl4AI. **Confidence: HIGH** that Trafilatura beats Anansi for non-auth static fetch on speed and clean text; **MODERATE** on exact speed delta vs Anansi until benchmarked on our own target pages.

---

## SOURCES
- Ian L. Paterson — Anti-detect browser benchmark 2026 (7 tools, 31 Cloudflare targets, 651 verdicts): https://ianlpaterson.com/blog/anti-detect-browser-benchmark-patchright-nodriver-curl-cffi/
- techinz/browsers-benchmark (Cloudflare/DataDome/Imperva/Akamai/PerimeterX harness; states proxy is REQUIRED for valid results): https://github.com/techinz/browsers-benchmark
- PROXIES.SX — DataDome & Akamai Bypass Guide 2026 (JA4, layered trust score, mobile-proxy + stealth-browser stack): https://www.proxies.sx/blog/datadome-akamai-bypass-mobile-proxies
- ScrapeWise — Playwright Stealth 2026 (Patchright vs Camoufox vs noDriver, per-tool detection rates): https://scrapewise.ai/blogs/playwright-stealth-2026
- Use Apify — Firecrawl vs Jina Reader 2026 (feature/pricing matrix, verified Jun 2026): https://use-apify.com/blog/firecrawl-vs-jina-reader-2026
- serp.fast / murroughfoley.com / Barbaresi blog — Trafilatura speed + F1 (0.883 mean F1; single-digit ms; rs-trafilatura 0.910): https://serp.fast/guides/web-extraction-benchmarks
- APIScout / Respan / SourceForge — Browserbase vs Steel vs Hyperbrowser pricing & session persistence (verified 2026): https://apiscout.dev/guides/browserbase-vs-steel-vs-hyperbrowser-browser-infrastructure-2026
- Skyvern / DEV Community — browser-use vs Stagehand vs Skyvern framework comparison (Feb 2026): https://www.skyvern.com/blog/browser-use-vs-stagehand-which-is-better/

*— Dembe, A2 · Intel collection complete. Written to /home/john/Thunderbird/intel/CI_web_stack_research_20260620.md*
