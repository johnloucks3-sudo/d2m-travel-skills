# Secrets Manager Adoption Plan — MISSION-260
## Thunderbird Wing · Dreams2Memories Travel, LLC
**Author:** A7 Sterling | **Date:** 2026-06-17 | **Status:** APPROVED FOR EXECUTION

---

## EXECUTIVE SUMMARY

**Problem:** The Wing has leaked secrets to git at least 5 times (MISSION-242/244/245/253/261).
Root cause: secrets are hardcoded and scattered across 19 .env files, 4 config/*.env files,
1 systemd service file with inline token, and 197 Python files that contain secret-pattern
assignments. gitleaks (MISSION-261) is the backstop — but backstops fail. The fix is
elimination of the threat surface, not just detection.

**Recommendation:** Infisical (self-hosted on yoga via Docker).

**Effort:** 4–6 hours total. Commander action required: ~30 minutes.

**Success metric:** Zero new secrets in any file tracked by git.
Measurement: gitleaks pre-commit pass rate = 100% at 30-day mark.
Owner: A7 Sterling.
Review cadence: weekly Baldrige sweep (Sunday 18:00 MT).

---

## SECTION 1 — CURRENT SECRETS INVENTORY

### 1A. Secret Store Locations

| Location | Count | Status |
|---|---|---|
| `.env` (root) | 1 | Active — primary secrets file |
| `.env.vault` | 1 | Encrypted backup of root .env |
| `.env.telegram` | 1 | Telegram bot tokens (split file) |
| `.env.concierge` | 1 | Gmail concierge credentials |
| `.env.bak.*` | 2 | Stale backups (.bak.20260404, .bak.20260615_consolidation) |
| `.env.tmp` | 1 | Temporary (should not persist) |
| `.env.keys` | 1 | Keys index |
| `poe.env` | 1 | Poe API key |
| `config/d2mc2c_bot.env` | 1 | Telegram D2MC2C bot token |
| `config/dani_poe.env` | 1 | Dani Poe access key |
| `config/poe.env` | 1 | Poe config duplicate |
| `config/telegram_gw.env` | 1 | Telegram gateway config |
| `config/portal_creds.json` | 1 | Portal credentials (gitignored) |
| `config/persona_gmail_token.json` | 1 | Gmail OAuth token (gitignored) |
| `config/roboform_d2mconcierge_password.txt` | 1 | RoboForm password (gitignored) |
| `deploy/d2m-scheduler.service` | 1 | **INLINE TOKEN — tracked in git** |
| `storage/reverie/api/.env` | 1 | Reverie API secrets |
| `backups/continuity_rollback_*/oauth.env` | 1 | Backup OAuth env |

**Total on-disk env files: 19**
**Currently git-tracked env files: 0** (gitignore is effective post-MISSION-264/265)
**Critical gap: `deploy/d2m-scheduler.service` contains an inline `TELEGRAM_BOT_TOKEN=` that is git-tracked**

### 1B. Secret Categories (73 unique variable names — all values REDACTED)

**AI / LLM APIs (11):**
`ANTHROPIC_API_KEY`, `DEEPSEEK_API_KEY`, `GEMINI_API_KEY`, `GOOGLE_AI_API_KEY`,
`GOOGLE_GENERATIVE_AI_API_KEY`, `GOOSE_API_KEY`, `GROQ_API_KEY`, `HF_API_KEY`,
`OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `XAI_API_KEY`

**Telegram (9):**
`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHANNELS_BOT_TOKEN`, `TELEGRAM_COMMANDER_ID`,
`TELEGRAM_DANI_TOKEN`, `TELEGRAM_GOOSE_TOKEN`, `TELEGRAM_RELAY_CHAT_ID`,
`TELEGRAM_RELAY_TOKEN`, `TELEGRAM_WEBHOOK_SECRET`, `BOT_USERNAME`

**Google / OAuth (4):**
`GOOGLE_API_KEY`, `GOOGLE_MAPS_API_KEY`, `GOOGLE_APPLICATION_CREDENTIALS`,
`CLAUDE_USAGE_API_KEY`

**Poe (4):**
`POE_API_KEY`, `DANI_POE_ACCESS_KEY`, `POE_BASE_URL`, `POE_MODEL`

**Twilio (5):**
`TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_SMS_NUMBER`,
`TWILIO_WHATSAPP_SANDBOX`, `TWILIO_WHATSAPP_JOIN_KEYWORD`

**Travel Portals (4):**
`ROOM_RES_EMAIL`, `ROOM_RES_PASSWORD`, `RSSC_GUEST_LYONS_USER`, `RSSC_GUEST_LYONS_PASS`

**Infrastructure (10):**
`MCP_AUTH_TOKEN`, `RABBITMQ_PASSWORD`, `SECRET_KEY`, `JWT_ALGORITHM`,
`THUNDERBIRD_API_KEY`, `SMTP_PASSWORD`, `PINECONE_API_KEY`, `PINECONE_INDEX_URL`,
`SERPER_API_KEY`, `PERPLEXITY_API_KEY`

**Media / Other (5):**
`UNSPLASH_ACCESS_KEY`, `UNSPLASH_SECRET_KEY`, `PEXELS_API_KEY`,
`CLAUDE_WRAPPER`, `OAUTH_BACKUP`

**Non-secret config (also in .env files — these do NOT need secrets management):**
`PYTHONPATH`, `PATH`, `DEBUG`, `CORS_ORIGINS`, `WEBHOOK_BASE_URL`,
`SMTP_HOST`, `SMTP_PORT`, `POE_MODE`, `ROUTE_ALL_OPENCODE`, etc.

### 1C. Code Patterns — How Secrets Are Currently Consumed

| Pattern | Count | Assessment |
|---|---|---|
| `os.environ` / `os.getenv` / `environ.get` | 491 occurrences | GOOD — already env-var based |
| Python files with secret-pattern assignments (`KEY = '...'`) | 197 files flagged | Most are env-var lookups; some are hardcoded defaults or test fixtures |
| `python-dotenv` / `load_dotenv()` calls | 132 occurrences | MEDIUM — loads from .env at runtime |
| Systemd `EnvironmentFile=` | Rare | Some services have no env injection |
| Systemd inline `Environment=TOKEN=<value>` | 1 confirmed | RED — `deploy/d2m-scheduler.service` line 16 |

**Key finding:** The code is largely already env-var-based. The problem is the SOURCE of those
env vars (flat .env files scattered on disk with inconsistent gitignore coverage and historical
leakage). A secrets manager replaces the source — the code changes are minimal.

### 1D. Existing Controls (from MISSION-261)

- `gitleaks` pre-commit hook: ACTIVE, mandatory (blocks commit if binary missing)
- `gitleaks` GitHub Actions CI: ACTIVE (`secret-scan.yml`)
- `.gitignore`: covers all known .env patterns + credential JSON files
- `.gitleaks.toml`: present (allow-list for false positives)
- Pre-commit custom hook: credential scan (keyword + assignment + 16+ char quoted string)

**Gap:** Controls catch secrets AFTER they enter staged files. A secrets manager prevents
them from ever being written to disk in the repo.

---

## SECTION 2 — OPTIONS COMPARISON

### Context for evaluation
- 1-person shop on Linux (OpenSUSE, yoga server)
- Consumers: ~40 Python scripts, ~15 systemd services, 3 headless Claude agents, OpenCode
- All consumers run locally on yoga (no cloud-to-cloud injection)
- No team collaboration requirement
- Budget: minimal — this is a 1-person operation

---

### Option A — Infisical (Self-Hosted via Docker)

**What it is:** Open-source secrets management platform. Self-hosted on yoga. Web UI + CLI + Python SDK.

**Pros:**
- Open-source, free tier covers everything needed here
- Docker-based — one `docker-compose up` install
- Python SDK: `from infisical_sdk import InfisicalClient; client.secrets.get("TELEGRAM_BOT_TOKEN")`
- CLI: `infisical run -- python3 script.py` injects secrets as env vars (zero code change for existing scripts)
- Systemd integration: `ExecStart=infisical run -- /path/to/script.py` in service file
- Web UI for viewing/rotating secrets
- Machine Identity tokens: headless agents get a non-human identity with scoped access
- Universal Secret Sync: can push to .env file on rotation (bridge for legacy consumers)
- Full audit log: who/what accessed which secret, when
- Self-hosted = no PII or travel credential leaves yoga

**Cons:**
- Requires Docker on yoga (may already be installed)
- Self-hosted = you are the ops team (backups, upgrades)
- Machine Identity token must be managed (it is itself a secret — but only one, not 73)
- Port 8080 (or custom) must be reserved on yoga

**Cost:** $0 for self-hosted open-source tier

**Effort:** 3–4 hours (install + migrate 73 secrets + update service files + test)

---

### Option B — 1Password (+ `op run`)

**What it is:** Commercial password manager with CLI (`op`) and secret injection via `op run`.

**Pros:**
- `op run -- python3 script.py` injects secrets as env vars — identical pattern to Infisical CLI
- Mature, polished UX — Commander already may use 1Password personally
- Service accounts: headless agents get a scoped vault token
- Native systemd integration via `op run` in `ExecStart=`
- No Docker required — cloud-hosted, always available
- Mobile app for Commander to view secrets on the go
- Strong audit log

**Cons:**
- $3/month (Individual) — trivial but nonzero
- Cloud-hosted: travel portal passwords (ROOM_RES, RSSC) and Gmail tokens leave yoga
  (mitigatable: keep sensitive creds in a local-only vault item with careful policy)
- `op` binary must be present on yoga and authed — headless agents need a service account token
- Service account tokens expire and must be rotated (adds maintenance)
- Requires 1Password account (Commander must create if none exists)

**Cost:** $3/month (~$36/year)

**Effort:** 2–3 hours (account + CLI install + migrate + update scripts)

---

### Option C — Bitwarden Secrets Manager

**What it is:** Bitwarden's dedicated secrets management product (separate from Bitwarden password manager).

**Pros:**
- Open-source clients; self-host server option available
- Machine accounts for headless agents
- Python SDK available
- Free tier for individuals

**Cons:**
- Secrets Manager is a newer, less mature product than Bitwarden's core password manager
- Python SDK and CLI tooling less polished than Infisical or 1Password
- Self-hosted Bitwarden server (Vaultwarden) adds Docker complexity
- Cloud-hosted free tier: secrets leave yoga
- Smaller community/documentation base for the Secrets Manager product specifically
- `bws run` (CLI injection) is available but less battle-tested

**Cost:** $0 (cloud free tier) or self-hosted at $0 + Docker complexity

**Effort:** 3–5 hours (more complex CLI integration)

---

### Option D — HashiCorp Vault (HCP Vault Secrets)

**What it is:** Enterprise-grade secrets management. HCP Vault Secrets = cloud-hosted managed tier.

**Pros:**
- Gold standard in enterprise environments
- Dynamic secrets: generates short-lived credentials on demand (overkill here but powerful)
- Fine-grained policies, audit logging, namespaces

**Cons:**
- Significant operational complexity for a 1-person shop
- HCP free tier is limited; production use requires paid plan (~$0.03/secret/month)
- Dynamic secrets require secrets-aware app code (not simple env injection)
- Vault agent sidecar pattern is complex to configure
- The operational overhead is disproportionate to this use case

**Cost:** $0 (free tier, capped) → $0.03+/secret/month at scale

**Effort:** 8–12 hours (overconfigured for 1-person shop)

---

### Comparison Matrix

| Criterion | Infisical | 1Password | Bitwarden SM | HCP Vault |
|---|---|---|---|---|
| Cost | $0 | $3/mo | $0 | $0-variable |
| Effort (hours) | 3–4 | 2–3 | 3–5 | 8–12 |
| Python SDK | Yes | Yes (`op`) | Yes | Yes |
| systemd integration | `infisical run` | `op run` | `bws run` | vault agent |
| Headless agent support | Machine Identity | Service Account | Machine Account | AppRole |
| Data stays on yoga | Yes (self-hosted) | No (cloud) | Optional | No (cloud) |
| Audit log | Yes | Yes | Yes | Yes |
| Maturity | Good (2022+) | Excellent | Medium | Excellent |
| Fit for 1-person shop | Excellent | Excellent | Good | Poor |

---

## SECTION 3 — RECOMMENDATION: INFISICAL (SELF-HOSTED)

**Rationale:**

1. **Data sovereignty.** Travel portal passwords (ROOM_RES, RSSC) and Gmail OAuth tokens are
   sensitive client-service credentials. They should not leave yoga. Infisical self-hosted keeps
   everything on-machine.

2. **Zero cost.** A 1-person operation should not pay for secrets management infrastructure
   when a self-hosted open-source solution meets all requirements.

3. **CLI injection pattern fits the existing codebase.** `infisical run -- python3 script.py`
   injects all secrets as environment variables. The 491 `os.getenv()` calls in the codebase
   require ZERO code changes. The migration is: move values from .env into Infisical, then
   replace the .env loader with `infisical run`.

4. **Systemd integration is clean.** `ExecStart=infisical run -- /path/to/script.py` replaces
   `EnvironmentFile=/path/to/secret.env` without changing the Python code at all.

5. **Machine Identity for headless agents.** Each headless Claude spawn, OpenCode session, and
   long-running daemon gets a scoped identity. Audit trail shows exactly which agent accessed
   which secret.

6. **gitleaks integration is additive, not replaced.** Infisical does not conflict with the
   MISSION-261 gitleaks gate. Both run: Infisical prevents new secrets from being written to
   files; gitleaks is the backstop for anything that slips through.

---

## SECTION 4 — MIGRATION PATH

### Phase 0 — Immediate Action (Before Installation)
**Fix the one confirmed tracked secret — `deploy/d2m-scheduler.service`**

The inline `TELEGRAM_BOT_TOKEN=` on line 16 is currently git-tracked. This is the same class
of defect that caused prior incidents.

```
# Before migration, fix this manually:
# 1. Move token to /home/john/.thunderbird_scheduler.env (not in repo)
# 2. In d2m-scheduler.service, replace the inline Environment= line with:
#    EnvironmentFile=/home/john/.thunderbird_scheduler.env
# 3. git add deploy/d2m-scheduler.service && git commit "fix: remove inline token from scheduler service"
# 4. Rotate the Telegram bot token (it may already be exposed in git history)
```

Timeframe: complete before any other migration step.

---

### Phase 1 — Install Infisical on Yoga (Commander + A7)

**Prerequisites:**
- Docker installed on yoga: `docker --version`
- Docker Compose installed: `docker compose version`

**Install steps:**
```bash
# On yoga, as john
mkdir -p /home/john/infisical
cd /home/john/infisical

# Download official docker-compose
curl -o docker-compose.yml \
  https://raw.githubusercontent.com/Infisical/infisical/main/docker-compose.prod.yml

# Generate a strong encryption key and set in docker-compose.yml
# ENCRYPTION_KEY: 32-char random string (openssl rand -hex 16)

# Start
docker compose up -d

# Verify
docker compose ps
# Web UI available at http://localhost:8080
```

**Commander action (one-time, ~15 minutes):**
1. Open browser → `http://yoga:8080` (or `http://localhost:8080`)
2. Create account (admin — local only, no email confirmation in self-hosted)
3. Create organization: `Dreams2Memories`
4. Create project: `Thunderbird`
5. Create three environments: `production`, `development`, `test`

---

### Phase 2 — Populate Secrets (A7 automated migration)

A7 will write a migration script that reads the existing .env files and pushes values
into Infisical via the API. Commander sets ONE bootstrap token (the Infisical admin token)
in a temporary file outside the repo; the script runs once, then the bootstrap token is
deleted.

**Secret groupings (by environment/project path):**
```
/thunderbird/ai-apis/          ANTHROPIC_API_KEY, XAI_API_KEY, OPENROUTER_API_KEY, etc.
/thunderbird/telegram/         TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNELS_BOT_TOKEN, etc.
/thunderbird/travel-portals/   ROOM_RES_EMAIL, ROOM_RES_PASSWORD, RSSC_GUEST_*
/thunderbird/google/           GOOGLE_MAPS_API_KEY, GOOGLE_APPLICATION_CREDENTIALS
/thunderbird/twilio/           TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, etc.
/thunderbird/infrastructure/   RABBITMQ_PASSWORD, MCP_AUTH_TOKEN, SECRET_KEY, etc.
/thunderbird/media/            UNSPLASH_ACCESS_KEY, PEXELS_API_KEY, etc.
```

Non-secret config vars (`PYTHONPATH`, `DEBUG`, `SMTP_HOST`, `WEBHOOK_BASE_URL`, etc.) stay
in .env files or systemd `Environment=` lines — they are NOT secrets and do not belong in
a secrets manager.

---

### Phase 3 — Update Consumers

#### 3A. Python scripts that use `load_dotenv()`

**Before:**
```python
from dotenv import load_dotenv
load_dotenv("/home/john/Thunderbird/.env")
telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
```

**After (zero Python code change — use CLI injection instead):**
```bash
# Run via infisical instead of directly
infisical run --projectId=<proj> --env=production -- python3 thunderbird_telegram_gw.py
```

OR, for scripts that must self-load (not launched via CLI):
```python
from infisical_sdk import InfisicalClient
client = InfisicalClient(token=os.getenv("INFISICAL_TOKEN"))
secret = client.secrets.get("TELEGRAM_BOT_TOKEN", project_id="<proj>", env_slug="production")
```

**Priority:** CLI injection first (zero code change). SDK only where CLI injection is not possible
(e.g., scripts embedded in larger processes).

#### 3B. Systemd services

**Before (`deploy/d2m-scheduler.service`):**
```ini
[Service]
Environment=TELEGRAM_BOT_TOKEN=<hardcoded>
```

**After:**
```ini
[Service]
ExecStart=infisical run --projectId=<proj> --env=production \
  -- /home/john/Thunderbird/.venv/bin/python3 /home/john/Thunderbird/agents/d2m_scheduler.py
```

OR, for services that cannot use `infisical run` as wrapper:
```ini
[Service]
ExecStartPre=/usr/local/bin/infisical export --projectId=<proj> --env=production \
  --format=dotenv --output=/run/thunderbird/secrets.env
EnvironmentFile=/run/thunderbird/secrets.env
ExecStart=/path/to/script.py
```
(`/run/thunderbird/` is tmpfs — secrets never hit disk permanently)

All ~40 `.env` file consumers get the same treatment: replace `EnvironmentFile=` pointer
to a flat file with `infisical run` wrapper.

#### 3C. Headless Claude agents and OpenCode

Headless Claude spawns (via `thunderbird_headless_spawn.py`) already inherit environment
from the calling process. If the parent process is launched via `infisical run`, the
child inherits all injected env vars — no change to headless spawn logic.

For OpenCode sessions started interactively: add `infisical run -- opencode` as the launch
alias in the Commander's shell profile.

#### 3D. Machine Identity for daemons

Each always-running daemon (Telegram gateway, MCP server, scheduler, watcher) gets its own
Infisical Machine Identity with access scoped to only the secrets it needs.

```
d2m-telegram-gw      → /thunderbird/telegram/* only
d2m-mcp              → /thunderbird/infrastructure/MCP_AUTH_TOKEN only
d2m-scheduler        → /thunderbird/telegram/* + /thunderbird/ai-apis/*
thunderbird-watcher  → /thunderbird/infrastructure/* only
```

Machine Identity tokens are stored at `/home/john/.infisical/<service>.token` (outside repo,
backed up with vault backup, NOT in .env files).

---

### Phase 4 — Decommission .env Files

After all consumers are migrated and tested:

1. Archive current .env files: `cp .env /home/john/backups/env_archive_$(date +%Y%m%d).env`
   (outside repo, encrypted)
2. Delete .env files from the working directory
3. Verify `grep -r "load_dotenv" /home/john/Thunderbird --include="*.py"` → 0 results
   (or all remaining usages explicitly documented as non-secret config only)
4. Keep `.env.example` as documentation of variable names (values blank/placeholder)
5. Add `/home/john/infisical/` to local disk backup rotation

---

### Phase 5 — gitleaks Integration (Additive)

Infisical does not replace gitleaks. Both serve different roles:

- **Infisical:** prevents secrets from being written to files (upstream prevention)
- **gitleaks:** detects secrets that slip into staged files (downstream detection)

One integration point: add a gitleaks rule to detect Infisical Machine Identity token patterns
if they appear in code (they look like `st.v3.*` prefix):

In `.gitleaks.toml`, add:
```toml
[[rules]]
id = "infisical-machine-identity-token"
description = "Infisical Machine Identity Token"
regex = '''st\.v3\.[a-zA-Z0-9/+]{40,}'''
tags = ["infisical", "token"]
```

This closes the loop: if an Infisical token itself ever gets committed, gitleaks catches it.

---

## SECTION 5 — ROLLOUT STEPS

### Commander Actions Required (~30 minutes total)

- [ ] **Step 1 (10 min):** Confirm Docker is installed on yoga: `docker --version && docker compose version`
  If not installed: `sudo zypper install docker docker-compose` (OpenSUSE)
- [ ] **Step 2 (5 min):** Review and confirm Phase 0 fix for `deploy/d2m-scheduler.service`
  (A7 will prepare the exact diff — Commander approves + commits)
- [ ] **Step 3 (15 min):** Complete Infisical web UI setup (account + org + project + 3 environments)
  at `http://yoga:8080` after A7 runs the Docker install

Everything else (secret migration, script updates, service file updates, gitleaks rule) is A7.

### A7 Execution Timeline

| Step | Task | Estimated Time |
|---|---|---|
| Phase 0 | Fix d2m-scheduler.service inline token | 20 min |
| Phase 1 | Install Infisical via Docker | 30 min |
| Phase 2 | Write + run migration script (73 secrets) | 60 min |
| Phase 3A | Update Python scripts (infisical run wrappers) | 60 min |
| Phase 3B | Update systemd service files | 45 min |
| Phase 3C | Verify headless agent inheritance | 20 min |
| Phase 3D | Create Machine Identity tokens per daemon | 30 min |
| Phase 4 | Decommission .env files, archive | 20 min |
| Phase 5 | gitleaks .toml rule update | 10 min |
| Verify | End-to-end test all services | 45 min |
| **Total** | | **~5.5 hours** |

---

## SECTION 6 — SUCCESS METRICS AND THRESHOLDS

| Metric | Target | Red Flag |
|---|---|---|
| gitleaks pre-commit pass rate | 100% at 30 days | Any failure = immediate review |
| .env files in repo | 0 | >0 = RED |
| Inline `Environment=<secret>` in tracked service files | 0 | >0 = RED |
| Python scripts using `load_dotenv` on secret vars | 0 | >0 after migration = audit |
| Infisical uptime (yoga Docker) | >99.5% monthly | <99% = add restart policy |
| Secret rotation coverage (annual) | 100% of AI API keys | <80% at 12 months = audit |

**Owner:** A7 Sterling
**Measurement:** Weekly Baldrige sweep Sunday 18:00 MT
**Dashboard:** `OpsCenter/a7_metrics_dashboard.json` — add `secrets_in_repo_count` and `infisical_uptime_pct` KPIs

---

## APPENDIX A — FILES TO DECOMMISSION (post-migration)

| File | Action |
|---|---|
| `/home/john/Thunderbird/.env` | Archive then delete |
| `/home/john/Thunderbird/.env.vault` | Archive then delete (Infisical is the new vault) |
| `/home/john/Thunderbird/.env.telegram` | Archive then delete |
| `/home/john/Thunderbird/.env.concierge` | Archive then delete |
| `/home/john/Thunderbird/.env.bak.20260404` | Delete (stale) |
| `/home/john/Thunderbird/.env.bak.20260615_consolidation` | Delete (stale) |
| `/home/john/Thunderbird/.env.tmp` | Delete |
| `/home/john/Thunderbird/.env.keys` | Archive then delete |
| `/home/john/Thunderbird/poe.env` | Archive then delete |
| `/home/john/Thunderbird/config/d2mc2c_bot.env` | Archive then delete |
| `/home/john/Thunderbird/config/dani_poe.env` | Archive then delete |
| `/home/john/Thunderbird/config/poe.env` | Archive then delete |
| `/home/john/Thunderbird/config/telegram_gw.env` | Archive then delete |
| `/home/john/Thunderbird/storage/reverie/api/.env` | Archive then delete |

Keep: `storage/reverie/api/.env.example` (template only, no real values)

---

## APPENDIX B — BACKUP AND RECOVERY

Infisical self-hosted data lives in a Postgres container. A7 will configure a daily backup:

```bash
# Add to daily cron (A7 task)
docker exec infisical_db pg_dump -U infisical infisical | \
  gzip > /home/john/backups/infisical_db_$(date +%Y%m%d).sql.gz

# Keep 30 days
find /home/john/backups -name "infisical_db_*.sql.gz" -mtime +30 -delete
```

Recovery: `docker exec -i infisical_db psql -U infisical infisical < infisical_db_YYYYMMDD.sql`

This is the Wing's only remaining single point of failure for secrets. Acceptable risk for
a 1-person shop; mitigated by daily backup.

---

*A7 Sterling — Thunderbird Wing · MISSION-260 · 2026-06-17*
*"Waste is theft from the client experience. Scattered secrets are waste with teeth."*
