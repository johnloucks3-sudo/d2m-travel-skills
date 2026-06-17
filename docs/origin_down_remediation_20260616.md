# MISSION-072 — ORIGIN-DOWN REMEDIATION RUNBOOK
**Gauge (A7 Sterling) · 2026-06-16 · PREP ONLY — Read-only diagnostic. Zero live changes.**
**Source:** `output/dead_link_audit_20260616.md` + port probes + systemd/nginx/cloudflared inspection

---

## COUNTS

| Category | Count |
|---|---|
| Broken endpoints audited | 12 |
| Root cause identified (confirmed) | 10 |
| Root cause undetermined (requires CF dashboard) | 2 |
| Safe quick-wins (tonight / no maintenance window) | 4 |
| Maintenance window required | 5 |
| CF dashboard action required (no local fix possible) | 3 |

---

## EXECUTIVE SUMMARY

Three failure modes account for all 12 broken items:

1. **Origin service down (CF-502)** — service stopped or never started. Cloudflared correctly routes to the port; nothing is listening. Three subdomains.
2. **Self-signed cert at origin (CF-525 apex + assets)** — CF Full(Strict) mode rejects the `d2mluxury.crt` self-signed certificate nginx presents. Cert SAN covers the domain correctly but CA is untrusted. Three endpoints (bare domain + 2 asset paths on the same vhost).
3. **Orphaned DNS records with no nginx vhost (CF-525 wa/dossier/thunderbird)** — subdomains have CF DNS A records pointing to the server IP, but no nginx `server_name` block matches them. Nginx serves the first-loaded SSL vhost (`costs.d2mluxury.quest` cert) as a fallback, causing SNI mismatch → CF-525. Three subdomains.
4. **Health endpoints not implemented (404)** — services are running; the `/healthz` and `/api/health` paths simply do not exist in the application code. Two endpoints.

Additional structural finding: **duplicate cloudflared tunnel processes** — `cloudflared.service` and `thunderbird-tunnel.service` both run tunnel `0e0f57b6`. Not tonight's problem, but creates connector sprawl and config-drift risk.

---

## REMEDIATION TABLE

### GROUP A — CF-502: ORIGIN SERVICE DOWN (3 subdomains)

| Endpoint | Audit Status | Root Cause | Exact Fix | Risk | Window |
|---|---|---|---|---|---|
| `n8n.d2mluxury.quest` | CF-502 | `n8n-docker.service` is ENABLED but `inactive (dead)`. Requires Docker. Port 5678 not listening on either IPv4 or IPv6. | `systemctl --user start n8n-docker.service` (verify docker.service is running first: `systemctl status docker`). Confirm: `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5678/` → 200. | Low — isolated Docker container, no config changes | **QUICK-WIN** — tonight |
| `allm.d2mluxury.quest` | CF-502 | AnythingLLM Docker container not running. No systemd unit manages it. `deploy/anythingllm/docker-compose.yml` maps port 3001:3001. Port 3001 not listening. | `cd /home/john/Thunderbird/deploy/anythingllm && docker compose up -d`. Confirm: `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:3001/` → 200. Consider adding a systemd unit for auto-restart. | Low — isolated container | **QUICK-WIN** — tonight |
| `tg.d2mluxury.quest` | CF-502 | `thunderbird-telegram-gw.service` is ACTIVE but runs in **polling mode** (`getUpdates`). It binds **no HTTP port** — 8769 is never opened. The cloudflared ingress rule `tg → http://localhost:8769` is vestigial with no listener behind it. **COMMANDER NOTE:** Your Telegram C2 channel (D2MC2C_bot, d2m_channels_bot) is polling-based and is **completely unaffected** by this 502. The `tg.d2mluxury.quest` subdomain serves no operational function in current architecture. | **Option A (recommended):** Delete or disable the CF DNS record for `tg.d2mluxury.quest` and remove the ingress rule from `~/.cloudflared/config.yml`. No service is lost. **Option B:** If webhook mode is ever desired, bind the gateway to 8769 and update the service. Commander decides. | Low (either option) — no operational impact from the 502 | CF dashboard + maintenance window for DNS; config edit otherwise |
| | | **Bonus: Telegram bot "Not Found" errors** — gateway logs show `TG API getUpdates error: Not Found` on at least one bot. HTTP 404 on an API token path = invalid or revoked bot token. Identify which bot (`D2MC2C_bot` or `d2m_channels_bot`) and rotate/regenerate via @BotFather. | `systemctl --user status thunderbird-telegram-gw.service` → inspect logs for which token returns 404. Regenerate via @BotFather. | Low | **QUICK-WIN** (investigate tonight; rotate on Commander OK) |

---

### GROUP B — CF-525: SELF-SIGNED CERT AT APEX (3 endpoints, same nginx vhost)

| Endpoint | Audit Status | Root Cause | Exact Fix | Risk | Window |
|---|---|---|---|---|---|
| `d2mluxury.quest` (bare domain) | CF-525 | nginx at port 443 presents `/etc/nginx/ssl/d2mluxury.crt` — a self-signed cert (CN=d2mluxury.quest, SANs match). **CF Full(Strict) mode requires a valid CA-signed or Cloudflare Origin CA cert. Self-signed is rejected.** Note: IPv6 binding is NOT the cause — www.d2mluxury.quest (also IPv4-only on :8080) works. IPv4 happy-eyeballs fallback is confirmed operational. | Replace `/etc/nginx/ssl/d2mluxury.crt` + `.key` with a **Cloudflare Origin CA certificate** (free, 15-year, generated in CF dashboard → SSL/TLS → Origin Server → Create Certificate). Install cert, `nginx -t && systemctl reload nginx`. Alternatively, issue a Let's Encrypt cert (certbot). | Medium — requires `sudo` nginx cert swap + reload. Test in nginx before live. | **Maintenance window recommended** — brief downtime on reload. Urgent: Commander-facing. |
| `d2mluxury.quest/logo-navy.png` | CF-525 | Same nginx vhost (d2mluxury_root.conf), same self-signed cert. Asset served via nginx proxy to :8901. Root cause is identical to bare domain. | Fixed automatically by the cert swap above. No additional action. | Same as above | Same as above |
| `d2mluxury.quest/assets/d2m-banner.png` | CF-525 | Same. | Fixed by cert swap. | Same | Same |

**Note on apex fix path options:**
- **Option 1 (preferred):** CF Origin CA cert — free, 15-year, no ACME renewal, works with CF Full(Strict). Generate in CF dashboard, install in nginx. No public CA involvement.
- **Option 2:** Let's Encrypt via certbot. Requires port 80 ACME challenge or DNS challenge. Works but adds renewal maintenance.
- **Option 3:** Switch CF SSL mode for `d2mluxury.quest` to "Full" (not Strict). Accepts self-signed. Quick but reduces security posture. Not recommended as permanent fix.

---

### GROUP C — CF-525: ORPHANED DNS RECORDS, NO NGINX VHOST (3 subdomains)

| Endpoint | Audit Status | Root Cause | Exact Fix | Risk | Window |
|---|---|---|---|---|---|
| `wa.d2mluxury.quest` | CF-525 | CF DNS A record points to server public IP. No nginx `server_name wa.d2mluxury.quest` block exists. CF routes directly to origin IP:443. Nginx has no matching vhost → serves first-loaded SSL vhost (`costs.d2mluxury.quest` cert, CN mismatch) → CF-525. No tunnel ingress rule in `config.yml` either. Service/app at this subdomain: **unknown — never deployed.** | **If service was never deployed (likely):** Delete the CF DNS A record for `wa.d2mluxury.quest`. Problem disappears. **If service is needed:** Create nginx vhost + SSL cert + provision the service. Commander decides whether `wa` was ever a real service. | Low (DNS delete) / Medium (new vhost) | CF dashboard for DNS delete; nginx vhost = maintenance window |
| `dossier.d2mluxury.quest` | CF-525 | Same as wa — no nginx server block, no tunnel ingress. CF proxies to server IP:443, gets costs.crt CN mismatch. | Same options as wa. Commander should confirm if a dossier web service was ever planned. If not, delete CF DNS record. | Low | CF dashboard |
| `thunderbird.d2mluxury.quest` | CF-525 | Same as wa/dossier. | Same. Commander confirms intent. | Low | CF dashboard |

**Commander action required for GROUP C:** These three require a CF dashboard decision — are these records stale ghosts of services never deployed, or planned services? If stale: three DNS deletes fixes all three 525s instantly with zero risk. Do not need a maintenance window for the DNS delete itself; it's a CF dashboard action.

---

### GROUP D — 404: HEALTH ENDPOINTS NEVER IMPLEMENTED (2 endpoints)

| Endpoint | Audit Status | Root Cause | Exact Fix | Risk | Window |
|---|---|---|---|---|---|
| `costs.d2mluxury.quest/healthz` | 404 | Service on :8903 (or :8902 — see port mismatch note) is responding; the `/healthz` path simply does not exist in the application. No route defined. | Add a `/healthz` route to the costs service that returns `200 OK`. Alternatively, add a stub nginx `location /healthz { return 200 "OK"; }` if a real app-level check is premature. | Low | QUICK-WIN (nginx stub) or Medium (app-level) |
| `portal.d2mluxury.quest/api/health` | 404 | Portal service on :8780 is responding; `/api/health` path not implemented. | Same pattern — add health route or nginx stub. | Low | QUICK-WIN (nginx stub) |

---

## STRUCTURAL FINDINGS (NOT IN ORIGINAL AUDIT — BONUS)

### FINDING B-1: Duplicate Cloudflared Tunnel Processes

**What:** Two systemd services run the same tunnel (`0e0f57b6-33a1-4ed1-b3db-9b886f5add72`):
- `cloudflared.service` — uses `~/.cloudflared/config.yml` (21 ingress rules, explicit routing)
- `thunderbird-tunnel.service` — runs `cloudflared tunnel run thunderbird` with NO config file, uses CF dashboard routes

**Risk:** Duplicate connectors to same tunnel. If CF dashboard routes diverge from `config.yml`, traffic split is unpredictable. Creates silent mismatch vector.

**Fix:** Disable one. Recommended: keep `cloudflared.service` (explicit config.yml gives A7 audit visibility). Disable `thunderbird-tunnel.service`: `systemctl --user disable --now thunderbird-tunnel.service`.

**Window:** Maintenance window — verify primary connector stays healthy after disabling duplicate. Brief connectivity risk during transition.

### FINDING B-2: Port Mismatch — costs.d2mluxury.quest

**What:** `~/.cloudflared/config.yml` routes `costs.d2mluxury.quest → http://localhost:8903`. But `/etc/nginx/vhosts.d/costs.conf` proxies to `http://127.0.0.1:8902`. Two different ports; two different paths (tunnel bypass vs nginx proxy).

**Risk:** Traffic arriving via cloudflared tunnel hits :8903 (direct). Traffic arriving via CF proxied A record hits nginx:443 → :8902. If these ports run different processes or have different data, responses diverge. Needs Sterling + Commander clarification on which path is authoritative.

**Fix:** Align to one port. Either update config.yml to :8902 OR update costs.conf to :8903 after confirming what listens on each.

---

## DECISION MATRIX FOR COMMANDER

| Item | Commander Action Required | Urgency |
|---|---|---|
| n8n start | None — Wing can execute | Tonight (quick-win) |
| allm Docker start | None — Wing can execute | Tonight (quick-win) |
| tg subdomain fate | Decide: delete DNS record (recommended) vs webhook mode | Low urgency |
| Telegram bot "Not Found" | @BotFather token check — Commander or Wing on OK | Moderate — affects bot reliability |
| Apex CF-525 (cert swap) | Authorize maintenance window; generate CF Origin CA cert in dashboard | High urgency — bare domain down |
| wa / dossier / thunderbird DNS | Confirm: were these ever live services? If no: authorize DNS deletes | Medium — clean up orphans |
| costs port mismatch | Clarify which port is authoritative for costs service | Low — service may be working via one path |
| Duplicate cloudflared | Authorize disable of `thunderbird-tunnel.service` | Low urgency |

---

## QUICK-WIN EXECUTION CHECKLIST (Wing executes on Commander OK, no maintenance window)

```
[ ] 1. systemctl --user start n8n-docker.service  (verify docker running first)
        confirm: curl -s http://127.0.0.1:5678/ → non-zero response
[ ] 2. cd /home/john/Thunderbird/deploy/anythingllm && docker compose up -d
        confirm: curl -s http://127.0.0.1:3001/ → non-zero response
[ ] 3. Check tg gateway logs → identify which bot token returns "Not Found"
        systemctl --user status thunderbird-telegram-gw.service --no-pager -l | tail -20
[ ] 4. CF dashboard: verify SSL/TLS mode for d2mluxury.quest apex
        (confirms whether Full vs Full(Strict) → determines cert fix path)
[ ] 5. CF dashboard: confirm wa/dossier/thunderbird DNS records exist → mark for delete decision
```

---

## MAINTENANCE WINDOW CHECKLIST (schedule separately, not tonight)

```
[ ] MW-1. Generate Cloudflare Origin CA cert for d2mluxury.quest (in CF dashboard)
          Install to /etc/nginx/ssl/d2mluxury.crt + .key
          sudo nginx -t && sudo systemctl reload nginx
          Verify: curl -sv https://d2mluxury.quest/ → no 525 from CF

[ ] MW-2. (On Commander OK) Delete CF DNS records: wa / dossier / thunderbird
          Removes three 525s instantly, no local changes needed

[ ] MW-3. Disable thunderbird-tunnel.service to eliminate duplicate tunnel
          systemctl --user disable --now thunderbird-tunnel.service
          Watch CF dashboard: verify cloudflared.service maintains healthy connectors

[ ] MW-4. Add /healthz stubs to costs and portal nginx configs (low risk but requires nginx reload)
          Example: location = /healthz { return 200 "OK\n"; add_header Content-Type text/plain; }

[ ] MW-5. Resolve costs port mismatch (:8902 vs :8903) after clarifying authoritative path
```

---

*A7 Sterling — MISSION-072 Remediation Prep · 2026-06-16*
*No live changes made. All findings from read-only diagnostic. Runbook ready for Commander review and execution authorization.*
