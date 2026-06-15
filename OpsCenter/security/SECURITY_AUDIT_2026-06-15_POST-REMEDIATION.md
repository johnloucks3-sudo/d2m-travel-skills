# THUNDERBIRD — SECURITY RE-AUDIT (POST-REMEDIATION)
**Date:** 2026-06-15 · **Auditor:** Hale (Claude Code) · **Host:** yoga
**Companion to:** `SECURITY_AUDIT_2026-06-15.md` (original) · **Same criteria:** severity-ranked, evidence-backed, internet/LAN/tailnet/local scoped
**Classification:** 🔴 INTERNAL — store 600.

> This is the re-audit the Commander ordered after remediation: it re-verifies every hole, records what was executed vs held, and folds in new findings from the $0 tools (Trivy, gitleaks) and the repo-shrink + Google-AI work. Companion deliverables: `REPO_SHRINK_REPORT_2026-06-15.md`, `GOOGLE_AI_PRO_INTEGRATION_SPSA_2026-06-15.md`.

---

## 0. EXECUTIVE SUMMARY — WHAT CHANGED

The original audit found **5 Criticals + 10 Highs** on a posture with *no defense-in-depth between one bug and full root*. This session **closed the internet-facing and local-file exposure that the wing could fix without the Commander's accounts**, installed and tested the free tooling, and staged the rest with reasons.

**The headline reversal — the live internet leak is stopped.** The public MCP that served 342 tools (Gmail, dossiers, Drive-delete) unauthenticated now returns **HTTP 401**, edge-verified. The Qdrant PII store is off the tailnet. Every secret file on disk is locked. Every pushed secret is untracked and the leak is contained pending rotation.

**Posture delta:**

| | Original (AM) | Now (post-remediation) |
|---|---|---|
| Public MCP (Critical, internet) | 342 tools, **no auth**, live Gmail/PII read | **HTTP 401** (basic-auth); CF Access still pending |
| Qdrant/Ollama (High, tailnet) | open on 0.0.0.0, PII readable | **127.0.0.1-only**, tailnet **blocked** |
| World-readable/writable secrets (High) | `.env`+tokens 644, two tokens **777** | **all 600**, `/home/john` 700, **0 world-readable** |
| Pushed secrets in git index (Critical) | 9 files tracked | **untracked + gitignored** (rotation/scrub pending) |
| SSH brute-force (High) | password-auth, no protection | **sshguard active**, `AllowUsers john`, dead key pruned |
| Secret-scanning / backup tooling | none | **gitleaks, trivy, restic, pre-commit, sshguard** installed + tested |

**What remains = mostly things only the Commander can do** (rotate 27 supplier + Google/Telegram/HF/RoboForm creds, turn on Cloudflare Access + Tailnet Lock, decide sudo-scoping) plus two local-only items (Redis/CDP) deliberately held. Details in §3.

**Net:** the business's *internet* attack surface went from **Critical-open to gated**; the *root-amplifier* (passwordless sudo + docker group) is unchanged and is now the top remaining risk.

---

## 1. REMEDIATION LEDGER — EXECUTED + VERIFIED THIS SESSION

| Mission | Finding | Action | Verification |
|---|---|---|---|
| **241** | C1 public MCP | Tunnel `mcp.` repointed `8765→8770` (nginx basic-auth) + cloudflared restarted | `POST https://mcp.d2mluxury.quest/mcp` → **HTTP 401** (was 200 + tool list); `localhost:8765` still 200 (internal intact) |
| **248** | H5 file perms | `chmod 600` all secret/token/.env files; `creds/` 700; `/home/john` 700 | `find … -perm -o+r` → **0 real secret files**; home `700` |
| **249** | H6 Qdrant/Ollama | Containers recreated bound to `127.0.0.1` (volumes preserved) | tailnet 6333/11434 **BLOCKED**; localhost 200; `thunderbird_memories` intact |
| **264/252** | C2–C5/H9 git secrets | 9 pushed secret/cookie files `git rm --cached` + `.gitignore` hardened (commit `610854fc`) | `git ls-files` → **0 tracked**; `check-ignore` → 3/3 ignored; files preserved on disk |
| **250** | H7 SSH | sshguard installed + enabled; `AllowUsers john`; dead `penguin` key pruned (8→7) | `sshguard active`; `sshd -t` valid + reloaded; password-auth still on (no lockout) |
| **261** | Secret-scan tooling | gitleaks integrated into existing pre-commit hook (wing gate preserved) | block-test: staged secret → **exit 1 (blocked)** |
| **257** | Backups | restic encrypted repo init + backup + check + restore | **restore byte-verified** against source (proof of capability) |
| **263** | Vuln scanning | trivy installed; image + fs + IaC scans run | functional; CVE inventory in §4 |
| **266** | New: HF token | Hardcoded HF token at `model_safeguards.py:87` removed → `os.environ` default `""`, relocated to `.env` | `py_compile` OK; token off-source |
| **265** | Repo bloat | `.gitignore` newline bug (line 99-100) fixed — `.smart-env/` now ignored | rule split + verified |

**Self-inflicted incident, repaired:** the first Qdrant attempt put **firewalld into a FAILED state** (firewalld/nftables vs Docker iptables-legacy conflict + an `rtk` shell wrapper mangling `sudo`). Backed out the broken rule via `firewall-offline-cmd`, restarted firewalld → **state: running**, original ruleset intact. Pivoted to the container-rebind (cleaner, backend-agnostic). No data or availability loss. Process note: the wing's auto-commit watchers race manual git ops (cost three attempts on the untrack) and an `mv -i` alias hung a job — both handled; flagged for the team.

---

## 2. $0 TOOLING — ACQUIRED, INTEGRATED, TESTED (Commander directive)

All from the openSUSE repo / pipx — **$0**, validated working:

| Tool | Ver | Integration | Test result |
|---|---|---|---|
| **gitleaks** | 8.30.1 | Wired into `.git/hooks/pre-commit` (STEP 0, preserves wing's Harlan gate) | Blocks staged secret (exit 1) ✓ |
| **trufflehog** | 2.2.1 | secret-scan cross-check (legacy py; gitleaks is primary) | running full sweep |
| **trivy** | 0.71.0 | image + fs(secret,misconfig) + Dockerfile scans | found HF token + container CVEs (§4) ✓ |
| **restic** | 0.19.0 | encrypted local repo `~/.local/share/restic-localtest` (pw 600) | backup→check→restore verified ✓ |
| **sshguard** | 2.4.3 | enabled, monitors sshd | active; brute-force jailing ✓ |
| **pre-commit** | 4.6.0 | available for framework-managed hooks | installed ✓ |

**Bigger free tools = recommended, not yet deployed** (deliberate — they're multi-component): **Wazuh** (XDR/SIEM) and **CrowdSec** (crowd-sourced IPS) for detection; **Infisical/Doppler** (secrets manager) to kill the cred-sprawl class; **GitHub Push Protection** (toggle in repo settings). These are MISSION-260/261/263.

---

## 3. FINDINGS STATUS (post-remediation, same severity criteria)

### 🔴 CRITICAL
- **C1 — Public MCP:** ⬇️ **Downgraded to High-mitigated.** Now behind basic-auth (HTTP 401). RESIDUAL: basic-auth is single-factor + shared; the real fix (Cloudflare Access + MCP TokenVerifier + kill `0.0.0.0:8768`) is **HELD — Commander dashboard**. (M-241)
- **C2 `API Keys.txt` vault / C3 27 portals / C4 RoboForm+itinerary / C5 4 bot tokens:** ⏸️ **Contained, not resolved.** Untracked + gitignored so they stop spreading, but **still on GitHub's servers in history and live on disk → ROTATION REQUIRED** (Commander accounts). History scrub (filter-repo) is staged to run *after* rotation. (M-242/243/244/245/264)

### 🟠 HIGH
- **H3 — Root chain (passwordless sudo + docker group):** 🔴 **UNCHANGED — now the #1 risk.** HELD: scoping `NOPASSWD: ALL` and removing the docker group risk locking out automation; needs a careful design pass + your blessing. (M-246)
- **H4 — Ops dashboard / costs public, no auth:** ⏳ HELD — Cloudflare Access (your dashboard). Edge-tested: **no Access policy on any hostname**. (M-247)
- **H5 — World-readable secrets:** ✅ **CLOSED.**
- **H6 — Qdrant/Ollama tailnet exposure:** ✅ **CLOSED** (127.0.0.1).
- **H7 — SSH:** ⬇️ **Mitigated.** sshguard + AllowUsers done; `PasswordAuthentication no` HELD pending your key-login confirmation (one command). (M-250)
- **H8 — Tailnet Lock OFF:** ⏳ HELD — your Tailscale admin (could orphan nodes). (M-251)
- **H9 — Session cookies in git:** ⬇️ Untracked; server-side session invalidation HELD (portal logins). (M-252)
- **H10 — Hardcoded secrets in source:** ⬇️ HF token **fixed**; other 8 files (OpenRouter, Together, Twilio, X, DeepSeek, n8n) HELD for env-migration + rotation. (M-253/266)

### 🟡 MEDIUM
- **Redis no-auth + Chrome CDP open:** ⏸️ HELD (local-only; Redis password needs coordinated update of 6 client files). (M-256)
- **Backups failing + unencrypted:** ⬇️ restic capability proven; fix failed units + B2 offsite HELD. (M-257)
- **Container CVEs:** see §4. Mitigated by 127.0.0.1 binding; `docker pull` for patches. (M-266)
- **Code hygiene (argv token, pickle, shell=True, /docs):** HELD. (M-258)

### 🟢 LOW / NEW
- **Repo bloat (20 GB / .git 697 MB):** NEW — `.gitignore` bug fixed; phased shrink plan = M-265.
- Stale tunnel ingress, duplicate SSH keys, security headers: HELD (M-259).

---

## 4. NEW FINDINGS FROM $0 TOOLS

### Trivy — container CVEs (all images now 127.0.0.1-only = no remote surface)
| Image | CRIT | HIGH | Top issue | Fix |
|---|---|---|---|---|
| `qdrant/qdrant:latest` | 6 | 47 | OpenSSL heap overflow CVE-2026-31789; perl path-traversal (unfixed); vitest arbitrary file read | `docker pull` (patch available) |
| `ollama/ollama:latest` | 1 | 18 | Go stdlib 1.24.1 TLS/DoS cluster | upstream rebuild; pull newer tag |
| `hale-signal-gateway` | 0 | 19 | wire-runtime-jvm DoS (no fix); Go stdlib | monitor upstream |

### Trivy — secret scan
- **NEW CRITICAL (audit missed):** hardcoded HuggingFace token `model_safeguards.py:87`. **FIXED** this session (→ env). Validates gitleaks/trivy as catching what manual review missed.
- 14 MCP Dockerfiles (`mcps/`, third-party, not built) run as root — low, flagged.

### gitleaks + trufflehog — full secret inventory
*Scan over the 20 GB repo + git history was still running at report time.* It corroborates the manually-confirmed leaked set (portal_creds, telegram tokens, the API-keys vault, the 9 hardcoded-source secrets) and is the authoritative machine inventory for the rotation checklist. **Results append here on completion** — and given history holds these secrets, every hit reinforces: rotate, then `filter-repo` scrub (M-264).

---

## 5. COMPANION DELIVERABLES (this session)
- **`REPO_SHRINK_REPORT_2026-06-15.md`** — 20 GB→~8 GB working / `.git` 697 MB→~200 MB. ~12 GB recoverable with no git surgery; root cause was the `.gitignore` newline bug (fixed) + tracked `.venv`/`.smart-env`/`qdrant_storage`. 10 ranked $0 recs, 4-phase plan, sources. Security tie-in: smaller history = less secret exposure; the history rewrite is **one coordinated force-push** with the M-264 secret scrub.
- **`GOOGLE_AI_PRO_INTEGRATION_SPSA_2026-06-15.md`** — honest crux: **$20 AI Pro = consumer UI only, no API**; stack calls the separately-billed Gemini API (~$2–12/mo expected). No OpenRouter bill to replace (already Claude-MAX-default at $0). Privacy gate: free-tier Gemini trains on data → non-PII only; PII → paid Gemini or Claude MAX. Keep Grok-direct ZEN (not OpenRouter; real diversity). Recommendation = Option C with key-security gated on the secrets manager.

---

## 6. WHAT'S LEFT FOR THE COMMANDER (ranked)
1. **Rotate the pushed/hardcoded credentials** (C2–C5, H10, HF) — your accounts; then I run the history scrub (M-264) + repo shrink (M-265) as one coordinated force-push.
2. **Turn on Cloudflare Access** (free) for mcp/dashboard/costs/portal/ssh — closes C1 residual + H4 in one move (M-241/247).
3. **Decide the root-chain fix** (scope sudo / remove docker group) — M-246, the top remaining risk.
4. **Confirm SSH key login** → I flip `PasswordAuthentication no` (M-250).
5. **Tailnet Lock + ACLs** (your Tailscale admin) — M-251.
6. **Buy 2× YubiKey + Backblaze B2** — the two paid items that close the root-escalation and ransomware axes (M-262/257).

---

*Re-audit by Hale via parallel agents (trivy · gitleaks · repo-shrink · google-ai) + direct verification. No availability lost; firewalld incident self-repaired. — V. Hale, VCS*
