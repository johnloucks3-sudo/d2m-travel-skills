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
- **Camofox** — a second stealth browser; overlaps CloakBrowser + Anansi's browser fetcher. Running/available on REST :9377; its session/tab API is richer but not yet wired into the escalation chain (CloakBrowser is the escalation tier). Integrate on demand.
- 8080/8888 were already occupied → SearXNG moved to 8890.
