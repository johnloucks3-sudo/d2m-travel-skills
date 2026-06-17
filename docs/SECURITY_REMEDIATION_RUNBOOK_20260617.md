# THUNDERBIRD SECURITY REMEDIATION RUNBOOK
**Owner:** Sterling (A7) | **Compiled:** 2026-06-17 | **Scope:** Overnight attack session 2026-06-16/17 — ALL security findings
**Format:** Commander works top-down. Each item: one concrete action · rotation/force-push/account flag · risk if skipped · source doc

---

## TIER 1 — DO TONIGHT (P0: Active public exposure / alerting gap)

### P0-1 · costs.d2mluxury.quest — PUBLICLY EXPOSED (NO AUTH)
**Action:** CF Zero Trust dashboard → Applications → Add Self-hosted → hostname: `costs.d2mluxury.quest` → Allow policy: `Email is johnloucks3@gmail.com` → Save.
**Account needed:** Cloudflare login (Account ID `86ad4247d8ea3f48f8545c2f05024787`)
**Defense-in-depth (Wing executes after CF Access is live):** change `realtime_tracker.py` line 539 `host="0.0.0.0"` → `host="127.0.0.1"` so the port only binds loopback.
**Risk if skipped:** Token-burn rate, model costs, and client pipeline cost data are live and publicly queryable at HTTP 200 — no credential required from any IP.
**Source:** `docs/cloudflare_access_dashboards_runbook.md` · MISSION-247

---

### P0-2 · Off-box heartbeat alert never fires (dead-man switch disconnected)
**Action (3 steps, in order):**
1. `cd /home/john/Thunderbird && git add .github/workflows/offbox_heartbeat_force_fail_test.yml && git commit -m "stage: MISSION-220 forced-failure cert test" && git push origin master`
2. `gh secret set TELEGRAM_BOT_TOKEN` (paste interactively from `.env` — bot ID 8754681793)
3. `gh workflow run offbox_heartbeat_force_fail_test.yml -f confirm=CERT` — confirm Telegram message arrives.
**Account needed:** GitHub CLI authenticated (`gh auth status`); Telegram D2MC2C bot visible.
**Risk if skipped:** Yoga goes down — no page fires, Commander does not know. The prober runs every 15 min but the alert leg is silently broken (verified: `BOT:` is empty in all Action run logs).
**Source:** `docs/offbox_heartbeat_continuity_plan.md` · MISSION-220

---

## TIER 2 — THIS WEEK (P1: Burned credentials requiring rotation; active attack-surface fixes)

> **Read first:** These are already-pushed-to-GitHub items. Rotation is the ONLY effective mitigation while history still exists. Untacking + gitignore alone does nothing for already-pushed secrets. History purge (Tier 3) follows AFTER rotation.

---

### P1-A · `scratch/~~DO NOT DELETE API Keys.txt` — vault file (127 lines, 11-day exposure)
**Secrets in file (ALL must be rotated):**
- OpenSSH private key → regenerate keypair (`ssh-keygen`); revoke old pub key from all authorized_keys
- Google OAuth client secret (`GOCSPX-…`) → GCP Console → OAuth 2.0 clients → Delete + recreate; this same secret is also hardcoded in 3 OAuth scripts (see P1-B)
- 3× Google API keys → GCP Console → Credentials → Delete + create new; scope replacements to minimum needed services
- Telegram bot token (overlaps MISSION-245) → @BotFather /revoke (see P1-C)
- 2× DeepSeek API keys → platform.deepseek.com → regenerate
- X/Twitter tokens → developer.twitter.com → regenerate
- Google App Password → Google Account → App Passwords → revoke + reissue
**Action:** Rotate every item above BEFORE running history scrub. Order: SSH key first (highest privilege), then OAuth/API keys, then bot tokens.
**Rotation needed:** Yes, all items. **Force-push needed:** YES — after rotation, history scrub via Tier 3 removes the burned creds from all clones.
**Risk if skipped:** Any GitHub clone (including the exposure window 2026-06-04 to 2026-06-15 when repo was PUBLIC) holds a working skeleton key to the entire D2M infrastructure.
**Source:** MISSION-242 · `output/executor_results/MISSION-242_20260615.md`

---

### P1-B · Hardcoded secrets in 9 source files (gitleaks cycle-1 findings + MISSION-253)
**Files and secrets:**
1. `core/ops/thunderbird_v3.py:17` — Google API key (literal string)
2. `core/multi_model/multi_model_orchestrator.py:27` — OpenRouter API key
3. `agents/thunderbird_llm_proxy.py:14` — Together AI key
4. `core/communication/thunderbird_whatsapp.py:17` — Twilio token
5. `comms/x_follow_accounts.py:14` — X/Twitter token
6. `OpsCenter/stress_test*.py` — DeepSeek + OpenRouter keys
7. `scripts/n8n_webhook_reinit.sh:14` — n8n JWT (NO expiry — must be REVOKED, not just rotated)
8. `deploy/d2m-scheduler.service:16` — `TELEGRAM_BOT_TOKEN=` inline (git-tracked service unit)
9. `scripts/termius_termux_setup.md` — ed25519 private SSH key embedded in doc
**Action per file:** Replace literal with `os.environ.get("KEY_NAME")`. Move value to `~/.env` or `~/.thunderbird_scheduler.env` (for systemd: use `EnvironmentFile=` directive). Then rotate each key at its provider.
**Special handling:**
- n8n JWT: revoke at n8n admin panel + reissue with explicit expiry
- ed25519 key (`termius_termux_setup.md`): regenerate keypair entirely; revoke old public key from all `authorized_keys`; strip the embedded private key block from the doc
- `d2m-scheduler.service`: move token → `EnvironmentFile=/home/john/.thunderbird_scheduler.env` → commit → rotate the Telegram token value
**Rotation needed:** Yes, all 9. **Force-push needed:** YES — same reason as P1-A; history purge removes burned literals.
**Risk if skipped:** Each is a live credential embedded in a file that exists in git history. Code path exposure = provider account compromise.
**Source:** MISSION-253 · MISSION-260 (`docs/secrets_manager_adoption_plan.md`) · Cycle 6 findings

---

### P1-C · 4 Telegram bot tokens + webhook secret (config/telegram_gw.env — PUSHED)
**Tokens exposed:** 8754681793 (D2MC2C), 8726363494 (Dani), 8723918695, 8774569956 + TELEGRAM_WEBHOOK_SECRET
**Action:** @BotFather → `/revoke` for each of the 4 bots → regenerate tokens → update live config (`config/telegram_gw.env` OUT OF REPO, or use EnvironmentFile) → rotate TELEGRAM_WEBHOOK_SECRET → untrack `config/telegram_gw.env` → add to `.gitignore`.
**Account needed:** Telegram account + @BotFather access.
**Rotation needed:** Yes. **Force-push needed:** YES — once history-purged.
**Risk if skipped:** Anyone who cloned the repo has full C2 bot control — can impersonate D2MC2C bot to the Commander, intercept directives, send arbitrary messages.
**Source:** MISSION-245

---

### P1-D · RoboForm vault master password + itinerary passwords (config/ — PUSHED, PUBLIC)
**Exposure:** `config/roboform_d2mconcierge_password.txt` (vault master password, 11-day public exposure) + `infra/itinerary_passwords.txt`
**Action:** (1) Change RoboForm account password at roboform.com FIRST — this is a skeleton key to the entire d2mconcierge credential vault. (2) Rotate itinerary passwords. (3) Untrack both files, add to `.gitignore`.
**Account needed:** RoboForm account login (Commander action only).
**Rotation needed:** Yes. **Force-push needed:** YES.
**Risk if skipped:** Vault master password is the single key to all stored d2mconcierge logins; anyone who cloned during the public window holds it.
**Source:** MISSION-244 · `output/executor_results/MISSION-244_20260615.md`

---

### P1-E · TESS + Perx session cookies (cookies pushed, session replay possible)
**Exposure:** `state/perx_cabin/cookies.json`, `state/tess_portal/cookies.json`, `state/firefox_*/cookies.sqlite-wal` — tracked and pushed; enable TESS (CRM) + Perx session hijack without password until server-side invalidated.
**Action:** (1) Log out of TESS portal — forces server-side session invalidation. (2) Log out of Perx portal. (3) Files are already untracked + gitignored (done Cycle 3). Step 4: history purge (Tier 3) removes the pushed copies.
**Account needed:** TESS login, Perx login (Commander's portal credentials).
**Rotation needed:** Session invalidation (log-out) is sufficient — no credential rotation needed, just force the old cookies dead.
**Risk if skipped:** Anyone with the pushed cookies can replay a TESS or Perx session until the server expires it (session expiry is server-controlled, not file-controlled).
**Source:** MISSION-252

---

### P1-F · Dani bot running --dangerously-skip-permissions (open public bot, no user filter)
**Action:** Apply 2 edits to `OpsCenter/thunderbird_telegram_gw.py`:
- Edit 1 (~line 696): parameterize `call_claude_engine(prompt, model, extra_flags=None)` — default preserves Commander-bot behavior
- Edit 2 (~line 1681): add `_DANI_SANDBOX_FLAGS = ["--tools", ""]`; pass `extra_flags=_DANI_SANDBOX_FLAGS` from `dani_claude_engine()`
Then: `systemctl --user restart thunderbird-telegram-gw.service`
**No rotation needed.** No force-push needed (config change, not credential).
**Risk if skipped:** Any Telegram user who discovers the Dani bot can invoke it with full filesystem/tool permissions — Claude runs with no sandbox against the production Thunderbird tree.
**Source:** `docs/dani_bot_sandbox_plan.md` · MISSION-255

---

### P1-G · HMAC directive-trust gate (email directive trust = trivial substring bypass)
**Action:** Open a new Claude Code session. Cite MISSION-254. Instruct Hale: "Apply the three-layer trust gate per `docs/hmac_directive_trust_design.md`. You are authorized to modify `OpsCenter/run_commander_directive_sweep.py` for this change."
**Account needed:** No external account — requires an AUTHORIZED Claude Code session per SO_EMAIL_SCANNER_PROTECT_20260608.md (this is a protected file; Wing cannot self-authorize).
**Rotation needed:** No. **Force-push:** No.
**Risk if skipped:** Current check `if "johnloucks3" not in d_from:` is bypassed by display-name spoofing — `From: johnloucks3 <attacker@evil.com>` passes with zero email infrastructure. Any attacker who knows the check exists can issue directives to the Commander sweep.
**Source:** `docs/hmac_directive_trust_design.md` · MISSION-254

---

### P1-H · CF Access — apex domain + api/docs (secondary exposure)
**Action (same CF Zero Trust session as P0-1):**
- Protect `d2mluxury.quest` (apex): Applications → Add → resolve CF-525 first (tunnel routes OK) — adds auth to bare domain before fixing the SSL/525 error
- Optionally restrict `api.d2mluxury.quest/docs`: Swagger UI is public-facing; add Access policy if endpoint docs expose internal API schema
**Account needed:** Cloudflare login (same session as P0-1).
**Risk if skipped:** API documentation publicly browsable; apex CF-525 persists (images/logo broken).
**Source:** `docs/cloudflare_access_dashboards_runbook.md` · `output/dead_link_audit_20260616.md`

---

## TIER 3 — STRUCTURAL (P2: Architectural hardening; some Commander-gated)

### P2-A · Git history purge (burned secrets still in every clone forever until this runs)
**Dependency:** ALL rotations in Tier 2 must complete first. Purging before rotating is backwards — the secret is still live while the old copy persists in clone history.
**Action (Commander-gated — force-push is a one-way door):**
```bash
pip install git-filter-repo
git filter-repo --path "scratch/~~DO NOT DELETE API Keys.txt" --invert-paths
git filter-repo --path "config/telegram_gw.env" --invert-paths
git filter-repo --path "config/roboform_d2mconcierge_password.txt" --invert-paths
git filter-repo --path "infra/itinerary_passwords.txt" --invert-paths
git filter-repo --path "scripts/termius_termux_setup.md" --invert-paths  # contains ed25519 key
git filter-repo --path "state/perx_cabin/cookies.json" --invert-paths
git filter-repo --path "state/tess_portal/cookies.json" --invert-paths
# For inline secrets in source files: filter-repo --replace-text with a secrets map
git push --force origin master
```
**Account needed:** GitHub push access (Commander's git credentials). Force-push is irreversible on any diverged clones.
**Risk if skipped:** Even after rotation, all burned credentials remain permanently recoverable from any pre-purge clone or GitHub's servers. The attack surface does not shrink until the history is gone.
**Source:** MISSION-264 · MISSION-265 · `output/repo_shrink_plan_20260616.md`

---

### P2-B · Repo size shrink (working tree 19G · .git 288M)
**Action (A7 executes after Commander approves Tier 3):**
- Tier 2 (autonomous): delete stale tarballs (~685M), second venv (~439M), rotate logs (capped)
- Tier 3 (Commander-gated, same session as P2-A): filter-repo removes `.smart-env/multi/*.ajson` blobs (23+ blobs, ~950M uncompressed), qdrant `.dat` files (2× 33M) — projects .git from 288M → ~60-100M
**Risk if skipped:** 19G working tree on Yoga; .git pack files grow every commit cycle; `git clone` costs compound on every new dev/Chromebook session.
**Source:** `output/repo_shrink_plan_20260616.md` · MISSION-265

---

### P2-C · Infisical secrets manager adoption
**Action:**
1. Commander (30 min): `docker compose up -d` at Infisical self-hosted on Yoga → create org + project → web UI at `http://yoga:8080`
2. A7 (3-4 hours, autonomous after Commander sets up): migrate all 73 secret variables from 19 `.env` files → Infisical project → replace `.env` reads with `infisical run -- python3 script.py` (zero code changes to `os.getenv()` calls) → issue Machine Identity tokens per daemon
3. Remove `.env` files from repo tracking → add to `.gitignore`
**Commander needed:** Initial Docker setup + Infisical account creation only.
**Risk if skipped:** 19 `.env` files continue to accumulate on disk; gitleaks CI will continue blocking commits that accidentally include secrets; no centralized audit log of who accessed what.
**Source:** `docs/secrets_manager_adoption_plan.md` · MISSION-260

---

### P2-D · Gitleaks CI — enable after secrets removed (MISSION-261)
**Action:** After Tier 2 secrets are removed from source files:
```bash
pip install pre-commit
pre-commit install
```
Then enable the GitHub Actions secret-scan workflow (already staged as `.github/workflows/secret-scan.yml`). The pre-commit hook and CI gate are built — they are blocked only by the existing secrets in tracked files.
**Risk if skipped:** The gitleaks tooling built in Cycle 1 remains inert; new secrets can be committed without detection.
**Source:** MISSION-261 · Cycle 1 findings

---

### P2-E · YubiKey hardware authentication
**Action:** Procurement + setup guide in `intel/yubikey_guide_20260616.md` (drafted Cycle 6). YubiKey 5C NFC recommended. Integrates with GitHub SSH signing, Google account 2FA, and Tailscale device auth.
**Commander needed:** Purchase decision + physical setup.
**Risk if skipped:** All authentication remains software-only; phished/leaked passwords on any provider = full account takeover.
**Source:** MISSION-262 · Cycle 6 (Grace)

---

### P2-F · EDR (Endpoint Detection and Response)
**Action:** Options research in `intel/edr_options_20260616.md` (drafted Cycle 5). Top candidates at zero/low cost: Wazuh (open-source SIEM+EDR, self-hosted), CrowdStrike Falcon Go (free tier).
**Commander needed:** Choice + install authorization.
**Risk if skipped:** No behavioral monitoring on Yoga; secrets exfiltration or malware would be undetected until post-incident.
**Source:** MISSION-263 · Cycle 5 (Grace)

---

## QUICK REFERENCE — TAG MATRIX

| Item | Rotation | Force-push | Commander account | Wing-executable |
|------|----------|-----------|-------------------|----------------|
| P0-1 CF Access costs | No | No | CF login | No — Commander |
| P0-2 GH secret + cert | No | Yes (cert workflow) | GitHub CLI | Partial (Step 1 Wing) |
| P1-A vault file (242) | YES — all items | YES after Tier 3 | Multiple providers | No — all rotations are Commander |
| P1-B hardcoded secrets (253) | YES — 9 files | YES after Tier 3 | Provider portals | Wing removes literals; Commander rotates |
| P1-C Telegram tokens (245) | YES — 4 tokens | YES after Tier 3 | @BotFather | No — Commander |
| P1-D RoboForm/itinerary (244) | YES | YES after Tier 3 | RoboForm account | No — Commander |
| P1-E TESS/Perx cookies (252) | Session invalidation only | YES after Tier 3 | TESS + Perx portals | No — Commander logs out |
| P1-F Dani sandbox (255) | No | No | No | YES — 2 code edits + restart |
| P1-G HMAC trust (254) | No | No | Authorized CC session | Via authorized Hale session |
| P1-H CF apex + api/docs | No | No | CF login | No — Commander |
| P2-A history purge (264) | N/A | YES — irreversible | GitHub push | A7 runs filter-repo; Commander approves push |
| P2-B repo shrink (265) | N/A | YES (Tier 3 component) | GitHub push | Tier 2 autonomous; Tier 3 Commander-gated |
| P2-C Infisical (260) | N/A | No | Docker on Yoga (setup) | Partial |
| P2-D gitleaks enable (261) | N/A | No | No | YES — Wing |
| P2-E YubiKey (262) | N/A | No | Purchase | Commander setup |
| P2-F EDR (263) | N/A | No | Install auth | Commander choice |

---

## SEQUENCE DEPENDENCY CHAIN

```
Rotate everything (P1-A through P1-E)
    ↓
Remove literals from source files (P1-B)
    ↓
git push --force origin master  [Tier 3 — P2-A]
    ↓
Enable gitleaks CI (P2-D)  ← now passes because secrets are gone
    ↓
Infisical adoption (P2-C)  ← centralized management going forward
```

P0-1, P0-2, P1-F, P1-G run independently in parallel with the above chain.

---

*A7 Sterling — Runbook compiled from 7 overnight security cycles*
*Source missions: 220, 242, 244, 245, 247, 252, 253, 254, 255, 260, 261, 262, 263, 264, 265*
*P0 items: 2 | Most urgent: P0-1 (costs.d2mluxury.quest — active public exposure, live HTTP 200, no auth)*
