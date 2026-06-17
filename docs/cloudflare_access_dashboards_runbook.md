# Cloudflare Access — Dashboards Security Runbook
## MISSION-247 · Audit Date: 2026-06-17 · Author: Sterling (A7)
## Status: PLAN ONLY — No live changes made

---

## EXECUTIVE SUMMARY — FINDINGS

| Finding | Severity | Status |
|---------|----------|--------|
| `costs.d2mluxury.quest` (:8903) — PUBLICLY REACHABLE, NO AUTH | **P0 RED** | OPEN — confirmed live 200 |
| `api.d2mluxury.quest/docs` — Swagger schema publicly exposed | P1 YELLOW | Open |
| `:8903 realtime_tracker binds 0.0.0.0` — all interfaces | P1 YELLOW | Open (defense-in-depth) |
| `d2mluxury.quest` apex root — CF-525 (SSL fail, unreachable) | P1 YELLOW | Origin broken; Ops :8901 not currently serving |
| `api.d2mluxury.quest/api/health` — publicly reachable | P2 GREEN | Acceptable (health endpoint only) |
| nginx `auth_basic` on mcp/:8770, code/:8099 — effective | OK | These are protected correctly |

**Bottom line:** The cost tracker at `costs.d2mluxury.quest` is live and returning HTTP 200 with no authentication — token usage, Claude cost, "sk-ant key cost" figures, and window data are visible to any internet user who knows the URL. This is the immediate remediation priority.

The Ops Dashboard at `:8901` is currently unreachable via the Cloudflare tunnel (`d2mluxury.quest` returns CF-525). Cloudflare Access steps below should be applied now to close the door before the origin SSL issue is resolved — so that fixing the 525 does not inadvertently open an unprotected dashboard.

---

## ARCHITECTURE NOTE — WHY NGINX AUTH DOES NOT PROTECT THESE SERVICES

This is load-bearing context for the Commander's CF configuration decisions.

The Cloudflare tunnel (`cloudflared`) routes inbound HTTPS requests **directly to application ports on localhost** — it does not go through nginx. The mapping is:

```
Internet → Cloudflare Edge → cloudflared tunnel → localhost:PORT (app directly)
```

Nginx sits in parallel on the same host, serving requests that arrive on standard ports (80/443) from LAN clients. Its `auth_basic` directives protect those paths — but they are **invisible to traffic arriving via the CF tunnel**.

**Concrete example:**
- `mcp.d2mluxury.quest` → cloudflared config routes to `:8770` → nginx is listening on `:8770` with `auth_basic "Thunderbird MCP"`. Protected correctly because cloudflared points at the nginx listener.
- `costs.d2mluxury.quest` → cloudflared routes to `:8903` → `realtime_tracker.py` directly (nginx `costs.conf` proxies `:8902`, a different port/service entirely). No nginx layer. No auth.

**Therefore: Cloudflare Access is the correct and only effective control layer for dashboard hostnames tunneled directly to application ports.** Adding nginx auth to these services would only help LAN clients. CF Access gates the tunnel at the edge before any request reaches YOGA.

---

## CURRENT SERVICE INVENTORY

### Services Behind Cloudflare Tunnel

| Subdomain | CF Tunnel Target | Local Service | Auth Layer | Status |
|-----------|-----------------|---------------|------------|--------|
| `d2mluxury.quest` | `:8901` | `server.py` — D2M Ops Dashboard + Hale Briefs (FastAPI) | None (nginx on :443 also points here but is bypassed by tunnel) | **CF-525 — origin unreachable** |
| `www.d2mluxury.quest` | `:8080` | code-server / Reverie | App-level login wall (redirects /login → 200) | Redirect→Login |
| `costs.d2mluxury.quest` | `:8903` | `realtime_tracker.py` — Claude token/cost tracker | **NONE** | **200 — EXPOSED** |
| `itinerary.d2mluxury.quest` | `:8900` | Itinerary/visual dashboard | App-level 401 | Protected (app layer) |
| `code.d2mluxury.quest` | `:8099` | nginx → ttyd terminal | `auth_basic` via nginx (effective — CF points at :8099 nginx listener) | Protected |
| `mcp.d2mluxury.quest` | `:8770` | nginx → MCP server :8765 | `auth_basic` via nginx (effective — CF points at :8770 nginx listener) | Protected |
| `api.d2mluxury.quest` | `:8766` | Wing API (FastAPI) | App-level 401 on `/` and `/health`; `/api/health` and `/docs` are public | Partial |
| `grace.d2mluxury.quest` | `:8911` | Grace gift persona service | None (intentionally public) | Public by design |
| `portal.d2mluxury.quest` | `:8780` | Guest portal | App-level (root 200, /api/health 404) | Review needed |
| `n8n.d2mluxury.quest` | `:5678` | n8n automation | CF-502 — origin down | Broken |
| `app.d2mluxury.quest` | `:8888` | D2M web app | App-level login wall | Protected |
| `ssh.d2mluxury.quest` | `ssh://localhost:22` | SSH | SSH key auth (protocol-level) | Protected |

### Services NOT in Cloudflare Tunnel (nginx-only, LAN/local)
| vhost | nginx Port | Local Port | Auth |
|-------|-----------|-----------|------|
| `vscode.d2mluxury.quest` | 8100 | :8080 | None (listen :8100, not in CF tunnel) |
| `syncthing.d2mluxury.quest` | 8101 | :8384 | None (listen :8101, not in CF tunnel) |

These are only accessible from LAN (yoga) since CF tunnel does not advertise ports 8100/8101. Low risk but noted for completeness.

### Port Discrepancy — Two Cost Services

| Service | Port | Bind | Exposed Via |
|---------|------|------|------------|
| `core/cost_dashboard/app.py` | :8901 (hardcoded) | 127.0.0.1 | Same port as Ops Dashboard — potential conflict |
| `core/cost_dashboard/app.py` (systemd `cost-dashboard.service`) | :8902 | 127.0.0.1 | nginx `costs.conf` on :443 (LAN only, no CF tunnel) |
| `core/cost_dashboard/realtime_tracker.py` | :8903 | **0.0.0.0** | CF tunnel → `costs.d2mluxury.quest` — **EXPOSED** |

There are two cost services. The nginx `costs.conf` proxies `:8902` (app.py). The CF tunnel serves `:8903` (realtime_tracker.py). These are different apps. The exposed one is the realtime_tracker on :8903.

---

## IMPORTANT CAVEAT — CF ACCESS CURRENT STATE

Cloudflare Access applications and policies are **managed remotely in the Zero Trust dashboard**, not in the local `config.yml`. The local config only controls ingress routing (which subdomain → which port). Access policies live at `dash.cloudflare.com → Zero Trust → Access → Applications`.

Current Access state was inferred from probe behavior (dead-link audit):
- `d2mluxury.quest/buddy/grace` returned redirect to `cloudflareaccess.com` login — confirms at least one Access app exists for this path
- `costs.d2mluxury.quest/` returned HTTP 200 with no Access redirect — confirms no Access app is protecting this hostname

**Commander must verify the full Access application list** in the Zero Trust dashboard (Step 0 below) before applying new policies — the local runbook cannot see what policies already exist.

Account ID (from tunnel credentials): `86ad4247d8ea3f48f8545c2f05024787`
Tunnel ID (active): `0e0f57b6-33a1-4ed1-b3db-9b886f5add72`

---

## REMEDIATION RUNBOOK

### PRIORITY ORDER
1. Apply CF Access to `costs.d2mluxury.quest` — **P0, do this first**
2. Apply CF Access to `d2mluxury.quest` (Ops Dashboard) — before fixing the CF-525
3. Add CF Bypass for `/buddy/` and grace paths — restores Buddy public link
4. (Optional) Add CF Bypass for `api.d2mluxury.quest/docs` or restrict it

---

### STEP 0 — Verify Current Access Applications (Read-Only Audit)

Before adding anything, audit what already exists.

1. Navigate to: `dash.cloudflare.com` → select account → **Zero Trust** (left nav)
2. Go to: **Access** → **Applications**
3. Look for any existing applications on `d2mluxury.quest` or subdomains
4. Note: which subdomains have an Access application, which policy type (Allow/Bypass), which identity provider

If you see `d2mluxury.quest` (apex) listed with an Allow policy — the Ops dashboard may already be behind Access (even though it's currently 525). Verify before creating a duplicate.

---

### STEP 1 — Protect `costs.d2mluxury.quest` (P0 — DO THIS FIRST)

**What this protects:** Claude token burn data, cost-per-session figures, "sk-ant key cost" totals, and session window consumption. Currently fully public.

**In Zero Trust dashboard:**

1. Go to: **Access** → **Applications** → **Add an application**
2. Select: **Self-hosted**
3. Fill in:
   - **Application name:** `Costs Dashboard (Internal)`
   - **Session Duration:** `24 hours` (or `1 day`)
   - **Application domain:**
     - Subdomain: `costs`
     - Domain: `d2mluxury.quest`
     - Path: _(leave blank — protects the entire hostname)_
4. Click **Next** → Configure a policy:
   - **Policy name:** `Commander Only`
   - **Action:** Allow
   - **Include rule:**
     - Selector: **Emails**
     - Value: `johnloucks3@gmail.com`
     - _(Add a second email if Susan or another operator needs access)_
5. Click **Next** → no additional settings needed
6. Click **Save**

**Verify:** Open a private browser window → navigate to `https://costs.d2mluxury.quest/` → should redirect to `[your-team].cloudflareaccess.com/cdn-cgi/access/login` — not load the dashboard.

---

### STEP 2 — Protect `d2mluxury.quest` Apex (Ops Dashboard :8901)

**What this protects:** D2M Ops Dashboard, Hale Briefs, client lifecycle data, brief snapshots, financial waterfall, task heatmap. Currently CF-525 (unreachable), but the 525 is an origin SSL issue — fix it and the dashboard becomes live. Apply Access now so it is gated when the origin comes back up.

**In Zero Trust dashboard:**

1. Go to: **Access** → **Applications** → **Add an application**
2. Select: **Self-hosted**
3. Fill in:
   - **Application name:** `Ops Dashboard (Internal)`
   - **Session Duration:** `24 hours`
   - **Application domain:**
     - Subdomain: _(leave blank or enter apex)_
     - Domain: `d2mluxury.quest`
     - Path: _(leave blank — protect all paths on apex)_
4. **Exception:** Before saving, proceed to Step 3 — you will add a Bypass policy for `/buddy/` at this same step (one application, two policies).

---

### STEP 3 — Buddy Link Analysis: What CF Bypass Can and Cannot Fix

**CRITICAL: Read before assuming a CF Bypass policy restores the Buddy link.**

The dead-link audit surfaced two distinct Buddy probe results on two different hosts. They have different root causes and require different fixes:

| URL Probed | HTTP | Gate Type | Root Cause |
|-----------|------|-----------|------------|
| `www.d2mluxury.quest/buddy/` | 401 | App-level JSON `{"error":"Unauthorized"}` — **not CF Access** | The :8080 origin app (Reverie/code-server) requires auth and returns 401 regardless of CF policy |
| `d2mluxury.quest/buddy/grace` | 200 (CF Access wall) | CF Access redirect to `cloudflareaccess.com` | An Access application is protecting this path |

**A CF Access Bypass policy removes CF edge authentication — it cannot remove an app-level 401.** If the canonical public Buddy URL is `www.d2mluxury.quest/buddy/`, adding a Bypass policy on `www.d2mluxury.quest/buddy/` does nothing — the request passes CF edge and then hits the app's own 401.

**The apex path has a second problem:** The CF tunnel routes `d2mluxury.quest` directly to `:8901` (server.py, the Ops Dashboard). `server.py` mounts no `/buddy/` route — it serves dashboard data only. nginx's `/buddy/` static alias in `d2mluxury_root.conf` only applies when nginx is serving the request on :443, which the CF tunnel bypasses entirely. A visitor to `d2mluxury.quest/buddy/` via the tunnel would hit server.py and receive a 404 or redirect, not the Buddy files.

**What would actually fix Buddy (planning note, not tonight's task):**

Option A — Nginx-fronted routing for www: Fix the app-level auth gate on :8080 to allow `/buddy/` unauthenticated. This is a code/config change to the app, not a CF change.

Option B — Grace subdomain (already working): `grace.d2mluxury.quest` returns HTTP 200 with no auth. If the public Buddy link points to `grace.d2mluxury.quest`, it already works. Verify whether this is the canonical public URL before doing anything else.

Option C — Add a dedicated CF ingress + nginx route for buddy static files: Add `buddy.d2mluxury.quest` (or a path on grace.d2mluxury.quest) in cloudflared config pointing to nginx on a port that serves only `/srv/www/htdocs/buddy/` statically, with no app auth layer. Then a CF Bypass on that hostname works correctly.

**CF Bypass that IS valid (narrow, for the apex/grace path):**

If Access is also protecting `d2mluxury.quest/buddy/grace` (which the probe confirms — it returned an Access wall), and the intent is for `grace.d2mluxury.quest` (already public, HTTP 200) to be the canonical grace path, the apex `/buddy/grace` Access gate is redundant. A Bypass policy on `d2mluxury.quest/buddy/grace` removes the CF edge gate, but the tunnel still routes to server.py which has no `/buddy/grace` route — so this is a no-op until the routing is fixed.

**Recommendation for tonight:** Do Steps 1 and 2 (costs + ops protection). Flag the Buddy routing as a separate follow-on task. The public-facing Buddy link is currently broken regardless of CF Access state, and fixing it requires a routing/architecture decision (Option A, B, or C above) that is out of scope for tonight's plan-only cycle.

**CF Bypass steps (for future use, when routing is confirmed correct):**

When the routing to buddy static files is confirmed working (probe returns 200 via the intended tunnel path), add a separate CF Access application:
1. **Application name:** `Buddy Public`
2. **Domain:** the confirmed hostname / Path: `/buddy/` (or blank if using a dedicated subdomain)
3. **Policy:** Bypass / Everyone

This is the reliable pattern — a separate Bypass application on the specific hostname/path, not a mixed-policy within the same Allow app. Separate app = most-specific-hostname wins cleanly.

---

### STEP 4 — (Optional) Restrict `api.d2mluxury.quest/docs`

**Finding:** `api.d2mluxury.quest/docs` returns HTTP 200 publicly — exposes the full Swagger/FastAPI API schema, endpoint list, and request/response shapes. Not a credential leak, but it hands an attacker a map of the Wing's API surface.

**Option A — No action:** Accept the risk. The API itself requires auth for functional endpoints. Docs reveal surface only.

**Option B — Add Access app for `api.d2mluxury.quest`:**
- Application name: `Wing API (Internal)`
- Domain: `api.d2mluxury.quest`
- Path: _(blank — full hostname)_
- Add Bypass policy for `/api/health` path if external health monitoring is in use

**Recommendation:** Apply Option B during the same Zero Trust session as Steps 1-3. Low additional effort.

---

### STEP 5 — Defense-in-Depth: Change realtime_tracker Bind Address

**Not a Commander step — this is a code change for the Wing to stage.**

`realtime_tracker.py` binds to `0.0.0.0:8903` (all interfaces). Since only cloudflared needs to reach it, and cloudflared runs on the same host, binding to `127.0.0.1:8903` would eliminate any local-network exposure path even if CF Access is misconfigured.

File: `/home/john/Thunderbird/core/cost_dashboard/realtime_tracker.py`
Line 539: `uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="warning")`

Change to: `uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")`

Then restart: `systemctl --user restart cost-tracker.service`

This is a defense-in-depth change, not the primary control. CF Access is the primary. Make this change after CF Access is applied and verified.

---

## SUMMARY — COMMANDER'S CF ZERO TRUST STEPS

Quick reference for the browser session:

| Order | Action | Dashboard Path |
|-------|--------|---------------|
| 0 | Audit existing Access apps | Zero Trust → Access → Applications |
| 1 | Add Access app for `costs.d2mluxury.quest` (Allow: Commander email) | Applications → Add → Self-hosted |
| 2 | Add Access app for `d2mluxury.quest` apex (Allow: Commander email) | Applications → Add → Self-hosted |
| 3 | READ Step 3 before acting — Buddy block is app-level 401, not CF Access; bypass will not restore it | Step 3 analysis |
| 4 | (Optional) Add Access app for `api.d2mluxury.quest` with /api/health bypass | Applications → Add → Self-hosted |
| 5 | Verify costs: private window → costs.d2mluxury.quest → should see Access wall | Browser |
| 6 | Verify ops: private window → d2mluxury.quest/ → should see Access wall (after apex 525 is resolved) | Browser |

**Account:** `dash.cloudflare.com` → account `86ad4247d8ea3f48f8545c2f05024787` → Zero Trust

---

## FINDINGS REGISTER (A7 Permanent Record)

| ID | Finding | Severity | Metric | Threshold | Owner | Remediation |
|----|---------|----------|--------|-----------|-------|-------------|
| CF-001 | `costs.d2mluxury.quest` live-200 with no auth — token cost/burn data public | P0 RED | Auth gate present (yes/no) | Must be YES | Commander (CF config) | Step 1 above |
| CF-002 | `api.d2mluxury.quest/docs` Swagger schema public | P1 YELLOW | Auth gate on /docs (yes/no) | Should be YES | Commander (CF config) | Step 4 above |
| CF-003 | `realtime_tracker.py` binds 0.0.0.0 not 127.0.0.1 | P1 YELLOW | Bind address | Must be 127.0.0.1 | Sterling (code change) | Step 5 above |
| CF-004 | Ops Dashboard `:8901` CF-525 — origin broken | P1 YELLOW | HTTP status | Must be 200 after fix | Hale (infra) | Separate nginx/SSL fix; apply Access before fixing |
| CF-005 | Buddy link broken — `www/buddy/` returns app-level 401 (not CF gate); apex `/buddy/` routing bypasses nginx, hits server.py (no route) | P2 YELLOW | HTTP 200 on canonical Buddy URL | Must be 200 | Hale (routing fix required before CF Bypass is useful) | Step 3 above — routing fix is a separate task |
| CF-006 | `nginx` auth_basic on mcp/:8770, code/:8099 — effective, but only because CF points at nginx listener ports | INFO | Auth present | OK | — | Confirm routing unchanged if nginx ports ever change |

**Measurement cadence:** Re-audit all P0/P1 findings within 48 hours of Commander completing CF Zero Trust steps. Verify using `curl -sS -L --max-time 15 -o /dev/null -w "%{http_code}"` against each endpoint. Results logged to `output/dead_link_audit_YYYYMMDD.md`.

---

*Runbook authored: 2026-06-17 | A7 Sterling | Plan only — no nginx, cloudflared, or mission_board.json changes made*
*Source files read: /etc/nginx/vhosts.d/*.conf, ~/.cloudflared/config.yml, core/cost_dashboard/realtime_tracker.py, core/cost_dashboard/app.py, core/visual_synthesis/dashboard_app/server.py, output/dead_link_audit_20260616.md*
