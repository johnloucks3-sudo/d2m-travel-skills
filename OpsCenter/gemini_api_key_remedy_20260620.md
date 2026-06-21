# Gemini API Key — Security Remedy Note

**Filed:** 2026-06-20
**Source:** Commander email "Re: [Correction] [Action Required] Secure your Gemini API access by Jun 19, 2026" (johnloucks3, msg id 19ed89c9f7fe5fc6), instruction: "Explain and suggest remedy." Underlying notice: Google AI Studio (googleaistudio-noreply@google.com), updated Jun 17, 2026.
**Author:** Backlog agent (file-only; no keys rotated, no files changed — FLAG ONLY)

> ⚠️ This note deliberately uses MASKED key values (`AIzaSy…XXX`) and paths only. Do not paste live key strings into any committed file.

---

## 1. What happened — two separate issues

### Issue A — Google policy notice (the email)
Google AI Studio notified John (first Jun 11, corrected/expanded Jun 17) that his project **`eara-titan-01`** contains at least one **unrestricted** API key:
- Affected key ID (from the email): **`e71595a4-…-01fe0db3a7c1`** in project `eara-titan-01`.
- Google's policy: keys created in AI Studio are restricted-by-default to the Gemini API; an *unrestricted* key in the same project can also call the Gemini API, which is a risk.
- **Deadline: June 19, 2026 — ALREADY PASSED** (today is 2026-06-20). After the deadline, Google states the Gemini API will *no longer accept requests that use unrestricted keys*. So this key may already be rejected by the API; service may break until it is restricted or replaced.
- This is a **policy/deprecation notice, not a breach report.**

### Issue B — Plaintext keys committed/stored in the repo (HIGHER SEVERITY — found by repo scan)
A scan of `/home/john/Thunderbird` (excluding `.venv/`) found **live `AIza…`-format Google API keys in plaintext on disk** across several files. This is the more serious problem: anyone with read access to the working tree or any synced/backup copy has the keys. Distinct masked keys observed:
- `AIzaSyC2a…EyUOc`
- `AIzaSyCsd…GluoTQ`
- `AIzaSyAiH…oC4Hs8`
- `AIzaSyD0Y…BAen4w`
- `AIzaSyAkt…sy2AxU`
- `AIzaSyDf3…uHFFUiQ`

## 2. The risk
Per Google's own notice and standard exposure rules:
- **Financial:** unauthorized parties can burn quota / run up the bill on any active key.
- **Data exposure:** a usable key can reach AI workloads / conversation histories.
- **Plaintext-on-disk (Issue B)** means each key must be treated as **compromised**. We cannot verify from files which keys are still active, so assume all are and rotate.

## 3. Where the keys are on disk (paths only — NO live values)
Git-tracking status checked: **all of the following are UNTRACKED in git** (good — no committed-history scrub required for these specific files; they live only in the working tree / backups). They are still plaintext-on-disk and must be cleaned.

Active-area / config & scripts:
- `/home/john/Thunderbird/.env`  ← primary live env (also matches `.gitignore` `.env*`, so ignored but present on disk)
- `/home/john/Thunderbird/.env.bak.20260404`
- `/home/john/Thunderbird/.env.bak.20260615_consolidation`
- `/home/john/Thunderbird/scratch/~~DO NOT DELETE API Keys.txt`  ← (`scratch/` is gitignored, but plaintext keys on disk)

Reports / logs (keys leaked into output):
- `/home/john/Thunderbird/output/THUNDERBIRD_MODEL_PLAN_FULL_20260516.md`
- `/home/john/Thunderbird/output/audit_git_repo_20260406.md`
- `/home/john/Thunderbird/output/OPUS_OPTION1_EVALUATION_AND_GEMINI_FIX.txt`
- `/home/john/Thunderbird/logs/c2_command_log.jsonl`
- `/home/john/Thunderbird/backups/continuity_rollback_20260610_2200/systemd_user/d2m-telegram-c2.service.DISABLED`

Browser-profile caches (transient but readable on disk):
- `/home/john/Thunderbird/.playwright-mcp/console-2026-06-*.log` (multiple)
- `/home/john/Thunderbird/browser_profiles/projectexpedition/Default/Cache/…` and `Code Cache/…`
- `/home/john/Thunderbird/browser_profiles/x_twitter/Default/shared_proto_db/000003.log`
- `/home/john/Thunderbird/core/travel/data/centrav_ff_profile/cache2/entries/…`
- `/home/john/Thunderbird/core/travel/data/serve_url_profile/{cache2/entries,places.sqlite}`
- `/home/john/Thunderbird/storage/browser_profiles/odysseus/Default/{Cache,Code Cache}/…`

*(Full enumerable list reproducible via `grep -rloE 'AIza[0-9A-Za-z_-]{30,}' /home/john/Thunderbird | grep -v '.venv/'`.)*

## 4. Concrete remedy (recommended order — requires Commander, involves live-key + spend actions)

1. **ROTATE every exposed key — treat all as compromised.**
   In Google Cloud Console → APIs & Services → Credentials (and AI Studio → API keys): delete/regenerate each `AIzaSy…` key found above, including the `eara-titan-01` key `e71595a4-…`. Rotating is the only way to neutralize a plaintext-exposed key.
2. **RESTRICT the replacements (fixes Issue A directly).**
   For each new key set **API restriction = Gemini API (`generativelanguage.googleapis.com`)** and, where possible, application restrictions (IP / referrer). This is exactly what Google's Jun-19 deadline demanded. Prefer binding the key to a service account scoped to Gemini APIs.
3. **MOVE the live key out of the repo entirely.**
   Keep the single active key only in `/home/john/.env` style location *outside* the repo (the pattern already used for telegram creds: `/home/john/.telegram_gw_live.env`), referenced by env var `GEMINI_API_KEY` / `GOOGLE_API_KEY`. Nothing in `/home/john/Thunderbird` should contain a literal key.
4. **SCRUB the plaintext copies on disk.**
   Delete `.env.bak.*`, purge keys from `scratch/~~DO NOT DELETE API Keys.txt`, redact the three `output/*` reports and `logs/c2_command_log.jsonl`, and clear the browser-profile caches / `.playwright-mcp` console logs. (These are untracked, so a working-tree delete + cache clear suffices — no `git filter-repo` history rewrite needed for *these* files.)
5. **VERIFY .gitignore is doing its job + add log/output coverage.**
   `.gitignore` already covers `.env*`, `*.env`, `*.key`, `*.api_key`, `scratch/`. Gap: keys are leaking into `output/*.md` and `logs/*.jsonl`, which are *not* secret-typed. Add a redaction step to whatever writes those, or gitignore the specific leak-prone artifacts. Then run a tracked-history check across the repo (`git grep -nE 'AIza[0-9A-Za-z_-]{30,}' $(git rev-list --all)` if a full-history audit is wanted) to confirm no key was ever committed.
6. **Confirm service continuity.**
   After rotate+restrict, smoke-test any Gemini-dependent path (Grace free tier, gemini_file_reader, GEMINI_LARGE_CONTEXT tier) to confirm the new restricted key works before retiring the old one.

## 5. Status / gates
- This note is **file-only.** No keys were rotated, no files were edited, nothing committed.
- Steps 1–2 touch live Google credentials and the project billing surface → **Commander action** (financial/credential gate). Steps 3–5 are infra cleanup Hale can execute, but are flagged here rather than performed so the Commander sees the full exposure first.
- **Most urgent:** the Google deadline already passed (Jun 19) — the `eara-titan-01` unrestricted key may already be failing, AND plaintext keys are sitting readable on disk. Rotate first, restrict second.
