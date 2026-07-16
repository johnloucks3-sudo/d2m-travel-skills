# d2mluxury.quest Subdomain Audit
## 2026-07-16 · Read-only connectivity + access-recency audit

**Method:** Enumerated the full subdomain list from `~/.cloudflared/config.yml` (the live tunnel ingress — the only ground-truth source; docs and JSON registries were cross-checked but the tunnel config is authoritative for what's actually routable). Tested each with `curl` against the public HTTPS URL. Cross-checked every result against the local origin service (systemd unit + direct `localhost:PORT` request) to separate "Cloudflare edge/tunnel problem" from "backend down." Access recency checked via `journalctl --user` per owning service; where that log window doesn't reach back far enough, said so explicitly rather than guessing.

**No live services were modified.** No CF Access changes, no restarts, no config edits.

---

## 1. Full subdomain list (from `~/.cloudflared/config.yml`, current ingress)

21 active hostnames + apex, all under one tunnel (`0e0f57b6-33a1-4ed1-b3db-9b886f5add72`):

| # | Subdomain | Target Port | Owning systemd unit / process |
|---|-----------|-------------|-------------------------------|
| 1 | `d2mluxury.quest` | :8901 | `d2m-dashboard.service` |
| 2 | `www.d2mluxury.quest` | :8901 | `d2m-dashboard.service` (same origin) |
| 3 | `reverie.d2mluxury.quest` | :8888 | `reverie-frontend.service` |
| 4 | `app.d2mluxury.quest` | :8888 | `reverie-frontend.service` (same origin) |
| 5 | `code.d2mluxury.quest` | :8099 | `ttyd-terminal.service` (nginx `auth_basic` front) |
| 6 | `itinerary.d2mluxury.quest` | :8901 | `d2m-dashboard.service` |
| 7 | `visuals.d2mluxury.quest` | :8900 | `itinerary-server.service` (`thunderbird_dir_server.py`) |
| 8 | `files.d2mluxury.quest` | :8900 | `itinerary-server.service` (same origin) |
| 9 | `portal.d2mluxury.quest` | :8780 | `d2m-portal.service` |
| 10 | `api.d2mluxury.quest` | :8766 | `thunderbird-api.service` |
| 11 | `mcp.d2mluxury.quest` | :8770 | `thunderbird-mcp.service` (nginx `auth_basic` → :8765) |
| 12 | `wa.d2mluxury.quest` | :8769 | `thunderbird-whatsapp-webhook.service` |
| 13 | `ssh.d2mluxury.quest` | `ssh://localhost:22` | system `sshd` |
| 14 | `grace.d2mluxury.quest` | :8911 | `grace_chat_server.py` (bare process, PID 1492 — **not** a systemd `--user` unit) |
| 15 | `spencer.d2mluxury.quest` | :8920 | `spencer-portal.service` |
| 16 | `loucks.d2mluxury.quest` | :8925 | `client-portal-server.service` |
| 17 | `lyons.d2mluxury.quest` | :8925 | `client-portal-server.service` (same origin) |
| 18 | `furlow.d2mluxury.quest` | :8925 | `client-portal-server.service` (same origin) |
| 19 | `elydarrow.d2mluxury.quest` | :8925 | `client-portal-server.service` (same origin) |
| 20 | `nichols.d2mluxury.quest` | :8925 | `client-portal-server.service` (same origin) |
| 21 | `mcleod-survey.d2mluxury.quest` | :8925 | `client-portal-server.service` (same origin) |

**Intentionally decommissioned (not tested — confirmed absent from ingress, not a fault):**
- `costs.d2mluxury.quest` — removed 2026-06-19 per config comment (MISSION-SEC-02, made local-only)
- `tcd.d2mluxury.quest` — retired 2026-07-12 (TCD moved to Sheets/AppSheet/Looker)
- `n8n`, `holyclaude`, `openwebui`, `flowise`, `allm`, `api-reverie` — pruned 2026-06-22, services confirmed not running

**Queued, not yet built** (per `config/client_portals.json._queued`): `mcleod.d2mluxury.quest`, `kuklinski-kyle/roger/morton.d2mluxury.quest`, and `spencer.d2mluxury.quest`'s planned migration off its legacy standalone service. Not live yet, so not scored below.

---

## 2. Live connectivity results

Tested `GET https://<host>/` with a 10s timeout. A `401`/`404` at the app layer counts as **LIVE** (the tunnel + origin answered); only Cloudflare edge codes (5xx) or connection failures count as **DOWN**.

| Subdomain | HTTP result | Status | Notes |
|---|---|---|---|
| `d2mluxury.quest` | 401 (JSON, app-level) | 🟢 LIVE | |
| `www.d2mluxury.quest` | 401 (JSON, app-level) | 🟢 LIVE | |
| `app.d2mluxury.quest` | 200 | 🟢 LIVE | Public |
| `code.d2mluxury.quest` | 401, `WWW-Authenticate: Basic realm="Thunderbird Terminal"` | 🟢 LIVE | nginx Basic Auth working |
| `itinerary.d2mluxury.quest` | 401 (JSON, app-level) | 🟢 LIVE | |
| `files.d2mluxury.quest` | 401, `WWW-Authenticate: Basic realm="D2M Thunderbird"` | 🟢 LIVE | |
| `portal.d2mluxury.quest` | 200 | 🟢 LIVE | Public root |
| `api.d2mluxury.quest` | 401 (JSON, app-level) | 🟢 LIVE | |
| `mcp.d2mluxury.quest` | 401, `WWW-Authenticate: Basic realm="Thunderbird MCP"` | 🟢 LIVE | |
| `wa.d2mluxury.quest` | 404 at `/` | 🟢 LIVE | Webhook-only endpoint, no root route — expected, not a fault |
| `grace.d2mluxury.quest` | 200 | 🟢 LIVE | Public by design |
| `spencer.d2mluxury.quest` | 401, `WWW-Authenticate: Basic realm="Spencer Grand Tour"` | 🟢 LIVE | |
| `loucks.d2mluxury.quest` | 401 | 🟢 LIVE | |
| `lyons.d2mluxury.quest` | 401 | 🟢 LIVE | |
| `furlow.d2mluxury.quest` | 401 | 🟢 LIVE | |
| `elydarrow.d2mluxury.quest` | 401 | 🟢 LIVE | |
| `nichols.d2mluxury.quest` | 401 | 🟢 LIVE | |
| `mcleod-survey.d2mluxury.quest` | 401 | 🟢 LIVE | |
| `ssh.d2mluxury.quest` | TCP 443 connects | 🟢 LIVE | Tunnel reachable (protocol-level test, not HTTP) |
| **`reverie.d2mluxury.quest`** | **525 (SSL handshake failed, Cloudflare edge)** | 🔴 **DOWN** | See root-cause note below |
| **`visuals.d2mluxury.quest`** | **525 (SSL handshake failed, Cloudflare edge)** | 🔴 **DOWN** | See root-cause note below |

### Root-cause note on the two DOWN hosts (important — this is a Cloudflare-side fault, not a backend outage)

I checked the local origin for both directly:

- `reverie.d2mluxury.quest` → tunnel target `:8888`. `reverie-frontend.service` is confirmed **active/running**, and `curl http://localhost:8888/` returns **200** — including with `Host: app.d2mluxury.quest` set, which is the *other* hostname sharing this exact port and returns a clean public **200**.
- `visuals.d2mluxury.quest` → tunnel target `:8900`. `itinerary-server.service` is confirmed **active/running**, and `curl http://localhost:8900/` returns **401** (Basic Auth challenge) — the same origin that correctly serves `files.d2mluxury.quest` (also :8900) with a working 401.

So in both cases: **the backend is up and answering correctly on the port the tunnel is configured to hit; the sibling hostname on the identical port works fine publicly; only these two specific hostnames 525 at the Cloudflare edge.** DNS resolves both to the standard Cloudflare anycast IPs (same as the working hostnames), so it isn't a DNS/proxy-status problem either. This points to a Cloudflare Zero Trust / edge-side configuration issue scoped to these two hostnames specifically (e.g., an Access application or SSL/TLS mode setting applied per-hostname) — not something fixable by restarting a local service. Flagging per instructions, not touching it.

**Priority:** Both are internal tooling (Reverie PWA frontend, internal visual-synthesis dashboard) — not client-facing. Lower priority than a client portal outage would be. No client-facing subdomain is down.

---

## 3. Access recency — methodology caveat (read before trusting any "stale" claim below)

Two independent evidence sources were checked, and they answer **different questions**:

1. **`journalctl --user -u <service>`** — real request logs, but **retention is short**. Confirmed coverage per service starts **2026-07-14 or 2026-07-15** (36–48 hours before this audit), not further back. This is enough to say "no real traffic in the last ~2 days" but **not enough to confirm or deny "no access in 2+ weeks."** No nginx access logs were available as a supplement — `/etc/nginx/nginx.conf` has `access_log` directives commented out, and `/var/log/nginx/` is root-only (no sudo available in this session).
2. **File `mtime` on the served content directories** — this is a **"content last updated"** signal, not a visitor-access signal. Labeled separately below.

I also had to filter my own audit `curl` calls out of the "real access" read — my probes landed in these same logs seconds after I ran them (visible as a burst of `GET /` 401s at 11:52 MT across nearly every service). Those are excluded from the findings below.

### 3a. Real (non-audit) access observed within the retained ~36–48h journal window

| Subdomain / service | Evidence | Verdict |
|---|---|---|
| `d2mluxury.quest` (`d2m-dashboard`, :8901) | External bot `216.73.216.240` hit `/robots.txt` and `/sitemap.xml` on 2026-07-16 11:47 MT. Also a `GET /` every ~3–4 min from the LAN egress IP — pattern matches an automated health-check timer (e.g. `itinerary-watchdog.timer`, fires every 5 min), **not** a human visit. | Confirmed live external traffic today (bot), no confirmed human visit in-window |
| `spencer.d2mluxury.quest` | `GET /favicon.ico` from a browser-shaped request on 2026-07-14 10:20 MT | Real visit 2 days ago — **not stale** |
| `portal.d2mluxury.quest`, `client-portal-server` (loucks/lyons/furlow/elydarrow/nichols/mcleod-survey), `thunderbird-mcp`, `thunderbird-whatsapp-webhook`, `itinerary-server` (visuals/files) | No non-audit request lines found anywhere in the retained journal window | **No confirmed access in ~36–48h** — cannot extend this to "2+ weeks" without longer log retention |
| `code.d2mluxury.quest` (ttyd) | Journal has ~2,200 lines of libwebsockets connection noise back to 2026-07-14, but these are low-level socket lifecycle events, not distinguishable as human terminal sessions without deeper parsing | Inconclusive — not scored |
| `grace.d2mluxury.quest` | Runs as a bare Python process (not a systemd `--user` unit); its request log location wasn't identified in this pass | Not verified — flagged for follow-up, not claimed either way |

### 3b. Content-`mtime` fallback (last-updated, NOT last-visited — do not conflate)

| Client portal directory | Last file touched | Days ago | 2+ week flag |
|---|---|---|---|
| `output/Loucks_Grandeur_Dec2026` | 2026-07-03 21:24 MDT | 13 days | ⚠️ Approaching, not yet past 14d |
| `output/Lyons_Voyages` | 2026-07-03 21:24 MDT | 13 days | ⚠️ Approaching |
| `output/Grandeur_Scandinavia_Portal/furlow` | 2026-07-03 21:24 MDT | 13 days | ⚠️ Approaching |
| `output/Grandeur_Scandinavia_Portal/elydarrow` | 2026-07-03 21:24 MDT | 13 days | ⚠️ Approaching |
| `output/Grandeur_Scandinavia_Portal/nichols` | 2026-07-03 21:24 MDT | 13 days | ⚠️ Approaching |
| `output/McLeod_SilverMuse_PostSurvey` | 2026-07-08 11:26 MDT | 8 days | Not stale |
| `output/Spencer_GrandTour_2027` | 2026-07-10 12:52 MDT | 6 days | Not stale |
| `files.d2mluxury.quest` / `visuals.d2mluxury.quest` root | Serves the entire live repo (`/home/john/Thunderbird`) | N/A — repo is committed to daily | Not stale (not a meaningful metric for a whole-repo mount) |
| `d2mluxury.quest` / `itinerary.d2mluxury.quest` (cruise DB API) | Actively serving live queries (observed real `/api/cruises/search` calls in-session) | 0 | Not stale |

**No subdomain crossed the 2-week threshold on either measure.** The five client-portal directories (Loucks, Lyons, Furlow, Elydarrow, Nichols) at 13 days since last content touch are the closest — worth a look in the next few days if that's meant to be an actively-refreshed set, but this is a **content-freshness** observation, not a **"nobody's visited"** claim; the actual client-portal-server access logs don't go back far enough to confirm or deny visits at all.

---

## 4. Summary for quick reference

- **21 live subdomains tested, 19 confirmed LIVE, 2 confirmed DOWN** (`reverie`, `visuals`) — both internal tooling, not client-facing, and both confirmed to be a Cloudflare-edge-side fault (525) rather than a backend outage (origins verified up and correctly answering on the same ports their working sibling hostnames use).
- **No client-facing subdomain is down.**
- **No subdomain confirmed stale by real access logs** — journal retention (~36–48h) is too short to make a 2-week access claim either way for most hosts; that gap is stated explicitly rather than papered over.
- **Content-mtime fallback**: 5 client-portal directories (Loucks/Lyons/Furlow/Elydarrow/Nichols) sit at 13 days since last file touch — approaching, not past, the 2-week mark.

---

*Audit performed 2026-07-16, read-only. Zero services restarted, zero CF Access/config changes made.*
