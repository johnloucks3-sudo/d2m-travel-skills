# browser-search stack — deployment notes (2026-07-01)

Self-hosted web tools from github.com/Johell1NS/browser-search, added as tiers behind Anansi.

## Running containers (Docker, `--restart unless-stopped` → survive reboot)

| Tool | Container | Bind | Purpose | Status |
|---|---|---|---|---|
| **SearXNG** | `searxng` | `127.0.0.1:8890` | Self-hosted metasearch (JSON) | ✅ up |
| **Camofox** | `camofox-browser` | `127.0.0.1:9377` | REST-API stealth browser (tabs/sessions/extract) | ✅ up |
| **CloakBrowser** | (npm, not Docker) | — | Stealth Chromium — Anansi's Akamai escalation tier | see `tools/cloak/` + `core/web/smart_fetch.py` |

Docker is usable after the 2026-07-01 `usermod -aG docker john`; in a shell that predates the
group change, prefix with `sg docker -c "…"`.

## Config
- SearXNG: `deploy/searxng/settings.yml` (secret_key inline — treat as sensitive; `use_default_settings: true`, `search.formats: [html, json]`, `limiter: false`).
- Camofox: `deploy/camofox/.env` (**gitignored** — holds `CAMOFOX_API_KEY`; `CAMOFOX_CRASH_REPORT_ENABLED=false` — telemetry to camofox-telemetry.askjo.workers.dev is DISABLED for D2M privacy).

## Smoke tests (verified)
- SearXNG: `curl "http://127.0.0.1:8890/search?q=regent+seven+seas&format=json"` → 17 results.
- Camofox: `curl http://127.0.0.1:9377/health` → 200; `/openapi.json` → 200; interactive docs at `/docs`.

## Restart / manage
```
sg docker -c "docker restart searxng camofox-browser"
sg docker -c "docker logs --tail 20 camofox-browser"
```

## Notes / ROI
- **CloakBrowser is the proven high-value piece** (defeats Akamai — Regent 403→200, verified). Wired as Anansi's escalation tier.
- **SearXNG** — useful self-hosted search (no API key, unlimited).
- **Camofox** — a second stealth browser; overlaps CloakBrowser + Anansi's browser fetcher. Running on REST :9377. **Wired 2026-07-16** into `core/web/smart_fetch.py` as opt-in **Tier 4** (`allow_camofox_tier=True`) — tried only when CloakBrowser (Tier 3) also fails; `_run_camofox()` does start→open-tab→snapshot with one session-expiry retry. Also backs the new `smart_fetch.search()` free-text primitive via the `@google_search` macro (Camofox fallback behind SearXNG). Opt-in because it is heavier and session-stateful (sessions expire between calls → auto-restart-once).
- **SearXNG free-text search** — now the primary engine for `smart_fetch.search(query)` (JSON metasearch, 127.0.0.1:8890). Closes the anansi free-text-search gap (MISSION-629): anansi only does `fetch <URL>`, so scans that passed raw NL queries got empty output. `search()` gives a real, tested free-text primitive (18 live results for a COS→GRB fare query, verified 2026-07-16).
- 8080/8888 were already occupied → SearXNG moved to 8890.
