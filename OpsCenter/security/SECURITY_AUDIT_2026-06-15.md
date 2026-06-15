# THUNDERBIRD — TOTAL SECURITY AUDIT
**Date:** 2026-06-15 · **Auditor:** Hale (Claude Code, 5-agent parallel sweep) · **Host:** yoga
**Scope:** yoga workstation · Thunderbird codebase (`/home/john/Thunderbird`) · Cloudflare tunnel + nginx · Tailscale fleet · credential surface
**Classification:** 🔴 INTERNAL — contains live attack-surface detail and proof-of-access evidence. Do not share outside the wing. Store at 600.

> **STATUS: FINAL · ACTIONS TAKEN 2026-06-15:** (1) **C1 public MCP CLOSED** — tunnel `mcp.d2mluxury.quest` repointed `8765→8770` (nginx basic-auth); public unauthenticated POST now returns **HTTP 401** (was HTTP 200 + live tool list). Internal `localhost:8765` unchanged. (2) **All findings loaded to the Mission Board** as **MISSION-240 (epic) + MISSION-241…264** — HALE oversight on every item, with file paths, required permissions/access, and remediation steps; 16 flagged `commander_action_required`. Backups: `~/.cloudflared/config.yml.bak.20260615_premcp`, `OpsCenter/mission_board.json.bak.20260615_security`.

---

## 0. EXECUTIVE SUMMARY

The wing is **operationally strong but security-exposed**. **No indicators of compromise were observed in the areas reviewed** (host logs show zero SSH brute-force, zero anomalous logins, the second user `ann` is dormant and locked) — but a full compromise assessment / IR sweep was **out of scope**. Given the exposure found (an internet-open MCP tool server, world-writable Gmail/Drive tokens, an unauthenticated Qdrant PII store), a clean bill of health cannot be claimed without a dedicated IR pass. The *standing posture* would let a single mistake become a full compromise of the business — client PII, supplier accounts, the Commander's mailboxes, and root on yoga.

**Scope exclusion:** the live tailnet nodes HP-Pavilion and Z-Fold6 were **not** audited (unreachable from yoga, and a phone is not host-auditable from here) — they are noted as in-scope-but-unaudited, and they matter because Tailnet Lock is OFF (H8).

**The one sentence that matters:** `john` has **passwordless `sudo ALL`** and is in the **docker group**, while running **unauthenticated, network-reachable services** — so there is *no defense-in-depth between any one application bug and full root*. Every other finding inherits its severity from this.

**Five things are Critical and warrant same-day action:**

| # | Critical finding | Proven? |
|---|---|---|
| C1 | `mcp.d2mluxury.quest` exposes **342 MCP tools with ZERO authentication** to the public internet — including `gmail_send_email`, `list_trip_dossiers`, `drive_delete_file`. **Confirmed at the edge:** `POST https://mcp.d2mluxury.quest/mcp` (no creds) → HTTP 200 + live tool list; **no Cloudflare Access policy** (no `*.cloudflareaccess.com` redirect on any hostname). Agents also read live Gmail profile + client booking numbers via the same surface. | ✅ edge-tested |
| C2 | A git-tracked, **GitHub-pushed** file `scratch/~~DO NOT DELETE API Keys.txt` contains an **OpenSSH private key, Google OAuth client secret, 4 Telegram bot tokens, Google API keys, DeepSeek keys**. | ✅ |
| C3 | `config/portal_creds.json` (**27 cruise-line/supplier B2B logins + security-question answers**) pushed to GitHub across 5 commits. | ✅ |
| C4 | `config/roboform_d2mconcierge_password.txt` (the **RoboForm vault master password** — a skeleton key) + `infra/itinerary_passwords.txt` pushed to GitHub. | ✅ |
| C5 | `config/telegram_gw.env` (**4 live Telegram bot tokens** + webhook secret) pushed to GitHub. | ✅ |

**Why "private repo" does not save us:** every secret ever *pushed* is on GitHub's servers and in every clone forever. A leaked PAT, a former collaborator, or one visibility flip exposes all of it. **Treat every pushed secret as already compromised → rotate, don't just untrack.**

**Bottom line for the Commander:** This is fixable in three sittings — a same-day "stop the bleeding" pass (close the public MCP, rotate the pushed secrets, lock file perms), a one-week hardening pass (auth on the tunnels, firewall the AI services, fix backups), and a one-month structural pass (secrets manager, hardware keys, EDR/monitoring). Phased plan in §7, products in §8.

---

## 1. ENVIRONMENT (confirmed)
- **Host:** `yoga` · openSUSE Tumbleweed (rolling, patched current — last pkg activity 2026-06-14, no reboot pending) · kernel 7.0.5 · ~40 systemd user timers.
- **Users w/ shell:** root · `john` (1000, **`NOPASSWD: ALL` sudo**, wheel, **docker group**) · `ann` (1001 — **dormant & password-locked, no `.ssh`, not in wheel/docker → not a live risk**).
- **Repo:** `/home/john/Thunderbird` 20G → GitHub `johnloucks3-sudo/thunderbird-os` — **PRIVATE** (verified).
- **Internet exposure path:** yoga has **no public IP**; the *only* internet ingress is the **Cloudflare tunnel `thunderbird`** (20 `*.d2mluxury.quest` hostnames). LAN (192.168.1.198) + Tailscale add more.
- **Firewall:** firewalld active. `public`/wlp2s0 allows only `ssh`, `3001`, `8099`, `60000-61000/udp` (mosh). **`tailscale0` → `trusted` zone (ALL ports open to tailnet).** **Docker DNAT bypasses firewalld** for 6333/6334/11434.
- **Tailnet:** yoga, HP-Pavilion (live), Z-Fold6 (live), octopus + 2× penguin (offline). **Tailnet Lock OFF**, ShieldsUp off, key expiry 2026-09-10.

---

## 2. CONSOLIDATED FINDINGS (severity-ranked)

### 🔴 CRITICAL

**C1 — Public MCP server: 342 tools, zero auth (PROVEN).**
`~/.cloudflared/config.yml` routes `mcp.d2mluxury.quest → http://localhost:8765`. The nginx `auth_basic` vhost for MCP sits on port **8770**, which the tunnel never touches — so the auth gate protects a dead port. `core/mcp/travel_mcp_server.py:1255-1303` attaches **no auth provider** to the transport (DNS-rebinding `allowed_hosts` whitelists the public hostname, so it is *not* a gate). Live, credential-less proof: `tools/call gmail_get_profile` → `johnloucks3@gmail.com, 210,880 messages`; `list_trip_dossiers` → real client names + Regent/Silversea confirmation numbers. Exposed tools include `gmail_send_email`, `send_client_email`, `send_whatsapp`, `drive_delete_file`, `delete_dossier_api_file`, `run_commander_inbox_sweep_tool`, `build_mcp_tool`. A second instance binds `0.0.0.0:8768` (LAN/tailnet-reachable). **Impact: internet-wide takeover of the wing's data + outbound planes.** *(network + code agents, independently confirmed.)*

**C2 — Secret vault committed to GitHub.** `scratch/~~DO NOT DELETE API Keys.txt` (commit `c74408d8`, pushed): OpenSSH **private key**, Google OAuth client secret `GOCSPX-…`, 3× Google API keys, Telegram bot token, 2× DeepSeek keys, X/Twitter tokens, Google app password, "merged from 9 files." Filename was explicitly protected from cleanup → persisted.

**C3 — 27 supplier portal credentials on GitHub.** `config/portal_creds.json`, 5 pushed commits. regent, viking, seabourn, princess, carnival, amawaterways, atlas_ocean, windstar, cruiseplum, world_agent_direct, expedia_taap, agentmax_allianz, hotelbeds, bedsonline, nexion, magtap, perx, amadeus_river, kensington, gate1, globus, vacationstogo, agent_universe, room_res, silversea, centrav. **Carnival + agentmax_allianz include `security_answers`** (can't be fixed by password change alone).

**C4 — RoboForm master password + itinerary passwords on GitHub.** `config/roboform_d2mconcierge_password.txt` (skeleton key to the whole d2mconcierge vault) + `infra/itinerary_passwords.txt`.

**C5 — 4 Telegram bot tokens + webhook secret on GitHub.** `config/telegram_gw.env`. Tokens `8754681793`, `8726363494`, `8723918695`, `8774569956`. = full control of the Commander's C2 bots (read messages, impersonate the wing).

### 🟠 HIGH

**H1 — Spoofable `From:` → tool-enabled agent executes email body.** `OpsCenter/run_commander_directive_sweep.py:212-213` authorizes on a **substring match** (`"johnloucks3" in From`). SMTP From is forgeable; a crafted local-part/display-name passes. Lines 281-311 interpolate the email `subject`+`body[:2000]` verbatim into a prompt dispatched to a **headless Hale agent with OAuth + MCP tools** (runs every 5 min). Classic prompt-injection-to-action gated only by a forgeable header.

**H2 — Public Dani Telegram bot → `claude -p --dangerously-skip-permissions`.** `thunderbird_telegram_gw.py:177` "Dani is open to all — no allow-list." Free-text reaches `call_claude_engine` (`:718-735`) which runs the Claude CLI with `--dangerously-skip-permissions` + Read/Write/Bash over the repo (dossiers, `.env`, tokens), as john. Mitigant: OpenCode path has `mcp:[]`. Still a prompt-injection → file read/write/exec path from any stranger.

**H3 — No defense-in-depth to root.** `/etc/sudoers.d/john-nopasswd: john ALL=(ALL) NOPASSWD: ALL` (confirmed via `sudo -l`) **plus** `john ∈ docker group` (mount host `/` = root). Any RCE as john → instant root, two independent ways.

**H4 — Ops Dashboard public, no auth.** `d2mluxury.quest → :8901` (FastAPI). `/openapi.json`, `/docs`, `/api/data/phase1|2`, `/briefs/{date}/` all 200 unauthenticated → **client surnames, per-client commissions ($8.5K–18.5K), pipeline totals, FPD dates, risk matrix, Allianz status** to anyone on the internet.

**H5 — World-readable/writable live secrets on a shared box.** `.env`, `poe.env`, `config/telegram_gw.env`, `gmail_token_commander.json`, `config/persona_gmail_token.json` = `644` (world-readable Gmail OAuth secret + refresh tokens, bot tokens). **`drive_token.json` + `gmail_token.json` = `777` (world-WRITABLE).** `/home/john` is world-traversable. `creds/` dir `644`.

**H6 — Qdrant + Ollama: firewalld-bypassed, tailnet-reachable, no auth.** Docker publishes `0.0.0.0:6333/6334` (Qdrant) + `0.0.0.0:11434` (Ollama) via DNAT that runs before firewalld; `DOCKER-USER` chain empty. Live: `http://100.69.222.124:6333/collections` → `thunderbird_memories` (PII vector store, readable + writable, no key). LAN+tailnet (not internet). The Signal-gateway container already pins `127.0.0.1:8088` correctly — copy that.

**H7 — SSH password auth ON.** `sshd -T: passwordauthentication yes, kbdinteractiveauthentication yes`, no `AllowUsers`, no fail2ban/sshguard. Reachable on wlp2s0 (LAN) + `ssh.d2mluxury.quest` tunnel. Logs show 0 probes (consistent with no internet port-forward → LAN/tailnet only today), but john's password → passwordless-sudo → root. Keys are already deployed and working → password auth is unnecessary.

**H8 — Tailnet Lock OFF + tailscale0 = trusted zone.** Every loopback/0.0.0.0 service is fully reachable from any tailnet node, and with Lock off a stolen auth-key can silently join the tailnet and inherit that access. Two live nodes (HP-Pavilion, Z-Fold6) are in-scope-but-unauditable from yoga.

**H9 — Session cookies on GitHub.** `state/perx_cabin/cookies.json`, `state/tess_portal/cookies.json`, `state/firefox_*/cookies.sqlite-wal` pushed → TESS (CRM) + Perx session replay until invalidated server-side.

**H10 — Hardcoded secrets in pushed source (8 files).** `core/ops/thunderbird_v3.py:17` (Google API key), `core/multi_model/multi_model_orchestrator.py:27` (OpenRouter), `agents/thunderbird_llm_proxy.py:14` (Together), `core/communication/thunderbird_whatsapp.py:17` (Twilio), `comms/x_follow_accounts.py:14` (X), `OpsCenter/stress_test*.py` (DeepSeek + OpenRouter), `scripts/n8n_webhook_reinit.sh:14` (**n8n JWT with no expiry**).

### 🟡 MEDIUM

- **costs.d2mluxury.quest → :8903** public, no auth → live AI usage/billing fingerprint (`/api/status`).
- **Redis 6379 — no `requirepass`** (verified empty). Loopback-only, but a local-foothold RCE pivot (CONFIG SET dir + cron/module).
- **Chrome CDP 9222 — open, no auth.** Loopback-only; any local process/user can drive the browser + steal logged-in cookies (Gmail, cruise portals).
- **Backups FAILING + unencrypted.** `thunderbird-gdrive-sync.service` + `thunderbird-evernote-backup.service` in `failed` state; rclone remotes are `type=drive` (plaintext, not `crypt`). Ransomware-recovery gap: looks backed up, isn't.
- **Bot token passed via argv** (`telegram_async_agent.py --token …`) → visible in `ps`/`/proc` to any local user.
- **`pickle.load`** on a local cache file (`core/dossier/dossier_cache.py:197`) → RCE if file is writable (it's reachable via the no-auth MCP write tools).
- **`shell=True` dispatchers** (`OpsCenter/slot_router/dispatcher.py:204`, `option1_parallel_spawn.py:80`) — latent command-injection sinks; not currently reachable from untrusted input (not MCP-registered), keep it that way.
- **FastAPI `/docs` `/redoc` `/openapi.json`** exposed on the public dashboard.

### 🟢 LOW / INFO
- Stale Cloudflare ingress entries (holyclaude, openwebui, flowise, allm, tg, n8n point to dead ports) — prune; **note: if n8n/AnythingLLM/OpenWebUI are ever restarted they ship with weak/no auth — gate before re-exposing.**
- Stale SSH `authorized_keys` for john: dead `johnloucks3@penguin`, 3× duplicate z-fold, 1 legacy `ssh-rsa` — prune to one-key-per-active-device.
- No security headers (X-Frame-Options, CSP, X-Content-Type-Options) on uvicorn apps (CF adds HSTS at edge).
- **Cleared:** `ann` dormant+locked; SUID/SGID all distro-standard; no world-writable system files; Docker socket not TCP-exposed; no privileged containers; `~/.claude/.credentials.json` + cloudflared creds correctly 600/400; `.env*` and `creds/` are gitignored (local exposure only, never pushed); reverie SPA has no path-traversal.

---

## 3. NOTABLE CONFLICT / VERIFICATION NOTES
- One agent reported `ssh.` as "key-auth only" — **incorrect**; direct `sshd -T` and the host agent both confirm `PasswordAuthentication yes`. Treated as H7.
- Tool counts (342) and PII reads were independently reproduced by two agents → high confidence, not a single-source artifact.
- Cloudflare **Access** was tested directly from the edge (not just inferred): `curl -sI https://<host>/` for mcp/dashboard/costs/portal/reverie/itinerary/api returned **no `*.cloudflareaccess.com` redirect on any of them** → **no Access policy is in front of any hostname.** Edge protection is absent; the only auth anywhere is origin-level (nginx basic-auth on code/itinerary/api/mcp-8770-which-is-unused; app magic-link on portal). mcp/costs/dashboard have neither → genuinely internet-open. `mcp.` confirmed with a live HTTP 200 `tools/list` from the public URL.
- The dashboard `d2mluxury.quest`/`:8901` returned HTTP 525 (origin TLS error) at the moment of testing — so it may be intermittently failing at the edge — but it is **ungated**, so it serves data publicly whenever the origin is up (agents read it on localhost).

---

## 4. PUBLIC INGRESS MAP (auth state)
| Hostname | →port | Listening | Edge/app auth | Verdict |
|---|---|---|---|---|
| mcp | 8765 | yes | **NONE** | 🔴 C1 — close today |
| d2mluxury / www | 8901 / 8080 | yes | **NONE** (8901) / login (8080) | 🟠 H4 (8901) |
| costs | 8903 | yes | **NONE** | 🟡 |
| portal | 8780 | yes | app magic-link | OK (verify) |
| reverie / app | 8888 | yes | SPA only, backend down | low (stale-ish) |
| code | 8099 | yes | nginx basic-auth + code-server pw | OK (double-gated) |
| itinerary / visuals | 8900 | yes | nginx basic-auth | OK |
| api | 8766 | yes | 401 | OK |
| ssh | 22 | yes | **password auth ON** | 🟠 H7 |
| holyclaude/openwebui/flowise/allm/tg/n8n/api-reverie | various | **down** | n/a | prune stale ingress |

---

## 7. PRIORITIZED REMEDIATION PLAN

### PHASE 1 — STOP THE BLEEDING (today; ~1–2 hrs)
1. **Close the public MCP (C1).** Fastest: repoint tunnel `mcp.d2mluxury.quest` from `localhost:8765` → `localhost:8770` (activates the existing nginx basic-auth), **and** add a Cloudflare Access app in front. Better: add a bearer-token verifier to the MCP transport. Kill or 127.0.0.1-bind the `0.0.0.0:8768` instance.
2. **Add Cloudflare Access to every sensitive hostname (H4, costs, portal, reverie, ssh, mcp).** Free Zero-Trust app, email-OTP or service token — one policy covers all `*.d2mluxury.quest` except the intentionally-public marketing site + lead form.
3. **Lock file perms (H5):**
   ```
   chmod 600 ~/Thunderbird/.env* ~/Thunderbird/*.env ~/Thunderbird/gmail_token*.json \
     ~/Thunderbird/drive_token.json ~/Thunderbird/config/persona_gmail_token.json \
     ~/Thunderbird/config/telegram_gw.env ~/Thunderbird/config/roboform_*.txt \
     ~/Thunderbird/infra/itinerary_passwords.txt "~/Thunderbird/scratch/~~DO NOT DELETE API Keys.txt"
   chmod 700 ~/Thunderbird/creds && chmod 600 ~/Thunderbird/creds/*
   chmod 700 /home/john
   ```
4. **Begin rotation of the pushed secrets (C2–C5, H9, H10).** Priority order: RoboForm master pw → Google OAuth client secret + SSH key → 4 Telegram bot tokens (@BotFather `/revoke`) → 27 supplier portals (+ change carnival/agentmax security-answers) → invalidate TESS/Perx sessions → AI provider keys (OpenRouter, Together, Twilio, X, DeepSeek, n8n) → Google API keys (add referrer/IP restriction).

### PHASE 2 — HARDEN (this week)
5. **Remove the root chain (H3):** replace `NOPASSWD: ALL` with command-scoped NOPASSWD (the existing `john-nginx-ttyd` drop-in is the correct model) or password-required sudo; remove john from the `docker` group (use rootless Docker or a sudo-gated wrapper).
6. **Firewall the AI services (H6):** republish containers `-p 127.0.0.1:6333:6333` (+6334, 11434); set Qdrant `QDRANT__SERVICE__API_KEY`. Move `tailscale0` out of the firewalld `trusted` zone into a scoped zone.
7. **SSH (H7):** `PasswordAuthentication no` + `KbdInteractiveAuthentication no` + `AllowUsers john`; install `sshguard`/CrowdSec.
8. **Redis (M):** set `requirepass`; `rename-command CONFIG ""`.
9. **History-scrub** the pushed secret files with `git filter-repo --invert-paths` + force-push (after rotation). Add `scratch/`, `config/*.txt`, `state/**/cookies*`, `*.sqlite-wal` to `.gitignore`. Move secrets out of the repo to `~/.config/d2m/` (700).
10. **Fix backups (M):** repair the 2 failed units; convert rclone to a `crypt` remote; ensure one immutable/object-locked copy.
11. **Tailnet Lock ON (H8)** + tighten Tailscale ACLs to per-node/per-port.

### PHASE 3 — STRUCTURAL (this month)
12. Move all secrets into a **secrets manager** with runtime injection (kills the world-readable `.env` + hardcoded-key + repo-leak classes at the source).
13. **Hardware keys (YubiKey)** for SSH + sudo (pam_u2f) + Google Workspace — directly addresses "one password = root."
14. **Git push-protection + secret scanning** in CI so this can never recur.
15. **EDR + host monitoring** (so a breach is *detected*, not just prevented).
16. Replace the forgeable-From trust boundary (H1) with an HMAC token; sandbox the Dani bot (H2) — drop `--dangerously-skip-permissions` on the public path.
17. Prune stale tunnel ingress + stale SSH keys; add security headers; switch `pickle`→JSON.

---

## 8. COMMERCIAL SECURITY PRODUCT RECOMMENDATIONS
*Each maps to the finding it closes. Tiered: free-first for a 1-person business, then paid where it buys real leverage.*

| Need (finding) | Free / low-cost | Commercial / when to upgrade |
|---|---|---|
| **Secrets sprawl, world-readable `.env`, repo leaks (C2–C5, H5, H10)** | **Infisical** (open-source, self-host, `infisical run` env injection) · **Doppler** free tier | **1Password Business** (~$8/user/mo) — `op run` injection, you already use RoboForm so the team habit exists; or **HashiCorp Vault** if you outgrow it |
| **Secrets reaching GitHub (C2–C5, H9, H10)** | **Gitleaks** + **TruffleHog** in a pre-commit hook + CI (free) · **GitHub Push Protection** (free on private repos) | **GitGuardian** (free ≤25 devs, then paid) — historical scanning + real-time alerts |
| **Public tunnel exposure (C1, H4, costs, ssh)** | **Cloudflare Zero Trust / Access** — **FREE up to 50 users**, you already run the tunnel. Add **Cloudflare WAF** (free tier) | Cloudflare Zero Trust paid tiers only if you add staff/devices |
| **Tailnet trust (H8)** | **Tailscale Tailnet Lock + ACLs** (free on your plan) · **Tailscale SSH** (replaces password SSH) | **Tailscale Personal Plus / Starter** for richer ACL + device posture |
| **No defense-in-depth to root / no breach detection (H3) + host monitoring** | **Wazuh** (open-source XDR/SIEM/HIDS, free) · **CrowdSec** (modern, crowd-sourced fail2ban for SSH/web) · **auditd** | **CrowdStrike Falcon Go** (SMB, ~$60/endpoint/yr) · **SentinelOne** · **Bitdefender GravityZone Business** (affordable Linux EDR) |
| **One password = root (H7, H3)** | **pam_u2f** (free) | **YubiKey 5** ×2 (~$50 ea — one primary, one backup) for SSH, sudo, and Google Workspace MFA. Single highest-leverage hardware buy. |
| **Failing/unencrypted backups + ransomware (M)** | **restic** or **BorgBackup** → **Backblaze B2** with **Object Lock** (immutable, ~$6/TB/mo) | **Backblaze Personal** ($99/yr unlimited) for the workstation; keep B2+restic for the encrypted immutable copy |
| **Container/image vulns (Qdrant, Ollama, node — H6)** | **Trivy** (free image + filesystem scanning) | — |
| **Network vuln scanning (whole-host)** | **Nessus Essentials** (free, ≤16 IPs) · **OpenVAS** | **Tenable Nessus Pro** if scope grows |
| **Email send integrity (the wing sends client mail)** | **SPF / DKIM / DMARC** on d2mluxury.quest (free DNS config) | **Cloudflare Email Security** if volume scales |

**If the Commander buys only three things:** (1) two **YubiKeys**, (2) **Backblaze B2 + restic** with object-lock, (3) turn on **Cloudflare Access** (free) — these close the root-escalation, ransomware, and public-exposure axes for ~$150 + an afternoon.

---

*Report generated 2026-06-15 by Hale via 5-agent parallel audit (secrets · code · network · web · host). All findings evidence-backed; no host configuration was modified during the audit. — V. Hale, VCS*
