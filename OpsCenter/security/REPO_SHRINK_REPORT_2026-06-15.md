# Thunderbird-OS Repository Shrink Report
**Date:** 2026-06-15 · **Author:** Hale (research + analysis) · **Repo:** `/home/john/Thunderbird` (private `johnloucks3-sudo/thunderbird-os`, branch `master`) · **Constraint:** $0 solutions only

Ties to **MISSION-264** (secret history-scrub) and the 2026-06-15 SECURITY AUDIT (MISSION-242..245).

---

## 1. Executive Summary

| Metric | Value |
|---|---|
| **Working tree (total on disk)** | **20 GB** |
| **`.git` directory** | **697 MB** (5 packfiles ≈ 589 MB compressed) |
| Commits (all refs) | 597 |
| Branches | 67 · Tags 0 · Refs 67 · Reflog 1.2 MB |
| Tracked files | 7,306 |
| **Broken gitlinks (no `.gitmodules`)** | **5** — `Blackboard`, `mcps/foursquare/foursquare-repo`, `mcps/yelp/yelp-repo`, `reverie`, `tools/fieldflow` |

**Two distinct problems, mostly disjoint:**

- **On-disk bloat (~12 GB of the 20 GB) is NOT a git problem.** The biggest consumer, `.venv` (9.5 GB), is *untracked* — pure `rm -rf` + rebuild. Add `.claude/worktrees` (1.5 GB), `logs` (433 MB), `.smart-env` working copy (387 MB), `.playwright-mcp` (131 MB). **Recoverable today with zero git operations and near-zero risk.**
- **History bloat lives in the 697 MB `.git`.** Driven by two paths committed repeatedly across 597 commits: `.smart-env/multi/*.ajson` (44 MB blobs, many revisions) and `data/qdrant*` (33 MB segment/WAL files). Only a **history rewrite** reclaims this.

**Headline offenders (history, by uncompressed blob churn):**

| Path | Uncompressed blob churn in history | Blobs |
|---|---|---|
| `.smart-env/` | **1,446 MB** | 3,674 |
| `data/qdrant*` | **1,170 MB** | 153 |
| everything else | 297 MB | 6,491 |
| `archive/` | 46 MB | 98 |

> ⚠️ **Honest-numbers caveat:** the 2.6 GB above is the *sum of uncompressed `%(objectsize)`* — it is **churn**, not reclaimable bytes. The packed `.git` is only 697 MB. Realistic outcome of a full history rewrite + gc: **`.git` drops from ~697 MB to roughly ~150–250 MB.** Do not quote "2.6 GB saved." The recoverable history number is bounded by pack size (589 MB).

**Root cause of the history bloat — a one-character `.gitignore` bug.** Line 99 of `.gitignore` reads `.smart-envconfig/portal_creds.json` — the `.smart-env` ignore entry is **glued to the next line with no newline**, so `.smart-env/` was never actually ignored and 3,556 of its files got tracked. Fixing that line is a precondition to everything else.

---

## 2. What's Bloating It

### 2a. On-disk (working tree) — fix first, no git rewrite

| Path | On disk | Tracked? | Why it's there | Should be tracked? |
|---|---|---|---|---|
| `.venv/` | **9.5 GB** | Mostly no (1,922 files / 40 MB tracked) | Python virtualenv | **No** — `rm -rf` + rebuild; ignored already |
| `.claude/worktrees/` | **1.5 GB** | No (`.claude/` ignored) | Claude Code session worktrees | No — disposable cache |
| `logs/` | **433 MB** | No (1 file) | Runtime logs | No — ignored already |
| `.smart-env/` | **387 MB** | **Yes (3,556 files)** | Smart Environment index `.ajson` | **No** — derived/regenerable cache |
| `.playwright-mcp/` | **131 MB** | No | Browser automation profiles | No — ignored already |
| `OpsCenter/` | 243 MB | partial | Mixed ops state + JSON | Mostly state, see §3 |
| `archive/` | 75 MB (46 MB tracked) | Yes (94 files) | Old artifacts | Move out of repo / Drive |
| `data/` | 56 MB | **Yes (qdrant 264 files)** | Qdrant vector store | **No** — regenerable DB |
| `restaurant_images/` | 41 MB (1.8 MB tracked) | partial (7) | Ship/dining photos | No — binaries → Drive/LFS |
| `validations/` | 34 MB (2.1 MB tracked) | Yes (48) | Client validation HTML | Keep small ones; review |

### 2b. History (`.git`) — the only thing a rewrite touches

| Blob / path | Largest single blob | History churn | Tracked now? | Why | Strip from history? |
|---|---|---|---|---|---|
| `.smart-env/multi/OpsCenter_GOOSE_INIT_md.ajson` | 46.7 MB | part of 1,446 MB | Yes | Regenerable index, committed repeatedly | **Yes** |
| `.smart-env/multi/CLAUDE_md.ajson` | 38.8 MB | (same) | Yes | Same | **Yes** |
| `.smart-env/multi/session_autosave_latest_md.ajson` | 35.9 MB | (same) | Yes | Same | **Yes** |
| `data/qdrant/.../payload_storage/page_0.dat` | 33.5 MB | part of 1,170 MB | Yes | Vector DB pages + WAL | **Yes** |
| `data/qdrant_storage/...` | 33.5 MB | (same) | Yes | Duplicate Qdrant tree | **Yes** |
| `.venv/...` (tracked subset) | — | within "other" | Yes (1,922) | Added before ignore rule | **Yes** |
| Secret files (see §5) | small | small | mixed | `portal_creds.json`, `roboform_*.txt`, `itinerary_passwords.txt`, cookies, sqlite | **Yes — MISSION-264** |

---

## 3. Ranked $0 Recommendations

Ordered by **(value ÷ risk)**. Items 1–4 are safe and reclaim ~12 GB on disk + stop growth. Items 5–7 are the coordinated history rewrite. Items 8–10 are ongoing hygiene/performance.

### #1 — Delete untracked on-disk caches (≈11.5 GB)
`.venv` is untracked; deleting it loses nothing git tracks — BUT this host runs live services (MCP :8765, 3 Telegram bots, ~6 keepalive timers). **Verify nothing executes from the venv before deleting it**, or you take the wing down until rebuild:
```bash
cd /home/john/Thunderbird
# PRECHECK — does anything depend on this venv?
grep -rl '/home/john/Thunderbird/.venv' deploy/systemd ~/.config/systemd/user 2>/dev/null
lsof +D /home/john/Thunderbird/.venv 2>/dev/null | head
# If precheck is CLEAN → delete. If it returns hits → stop those services (or rebuild venv) FIRST.
rm -rf .venv .claude/worktrees .playwright-mcp
# rebuild venv when needed:  python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
# logs: truncate rather than delete if services hold handles
find logs -type f -name '*.log' -mtime +7 -delete
```
**Savings:** ~11.5 GB on disk. **Risk:** `.claude/worktrees` + `.playwright-mcp` = none (disposable). `.venv` = **conditional** — safe only if the precheck is clean; otherwise stop/rebuild services first. All three are `.gitignore`d. **Link:** n/a.

### #2 — Fix the broken `.gitignore` line (prevents recurrence)
```bash
# Line 99 is "  .smart-envconfig/portal_creds.json " — split it:
#   .smart-env/
#   config/portal_creds.json
```
**Savings:** stops `.smart-env` from being re-tracked (the root cause). **Risk:** none.
**Link:** https://git-scm.com/docs/gitignore

### #3 — De-track cache/data dirs that should never be in git (`git rm --cached`)
```bash
cd /home/john/Thunderbird
git rm -r --cached --quiet .smart-env data/qdrant data/qdrant_storage 2>/dev/null
# de-track the stale tracked .venv subset:
git ls-files | grep -E '^\.venv/' | xargs -r git rm --cached --quiet
git commit -m "De-track regenerable caches (.smart-env, qdrant, .venv) — pre-shrink (MISSION-264)"
# git rm --cached only de-tracks; the files STAY on disk. To reclaim the
# 387 MB .smart-env / 56 MB data working copies (regenerable caches), also:
rm -rf .smart-env data/qdrant data/qdrant_storage   # regenerate index/vector store on next run
```
**Savings on disk:** ~440 MB once the `rm -rf` runs (the `git rm --cached` alone leaves the bytes on disk). **What de-track does:** stops future growth + removes from the working index.
> ⚠️ **`git rm --cached` does NOT shrink `.git`.** It adds a *removal* commit; every old blob stays in history. `.git` will look unchanged after this step — that is expected. Only the §5 rewrite reclaims pack bytes.
**Link:** https://git-scm.com/docs/git-rm

### #4 — Reclaim loose-object/pack slack WITHOUT a rewrite (gc)
```bash
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```
`gc --aggressive` recomputes deltas (`repack -f`); run only occasionally (post-bulk-change). Reflog expire + `--prune=now` drops the 90-day grace so just-unreferenced objects go now.
**Savings:** modest until the rewrite (history blobs are still *reachable* from 597 commits + 67 branches, so gc can't drop them). Real payoff is gc **after** §5.
**Risk:** low; `--prune=now` is unsafe only with concurrent writers — run when idle.
**Links:** https://git-scm.com/docs/git-gc · https://git-scm.com/docs/git-reflog

### #5 — Rewrite history with `git filter-repo` (the reclaim step) — coordinate with MISSION-264
**`git filter-repo` is the Git-project-recommended replacement for the deprecated `git filter-branch`** (10×+ faster, single-pass, safer). GitHub's own "remove large/sensitive files" docs recommend it. **BFG** is a fine simpler alternative for pure size/secret bulk-strip; **`filter-branch` is deprecated — do not use.**

**Do it ONCE.** Strip the big blobs AND the MISSION-264 secrets in the *same* pass so you only force-push once:
```bash
pip install git-filter-repo            # or: brew install git-filter-repo
# Work on a fresh mirror clone (filter-repo wants a clean clone):
git clone --no-local /home/john/Thunderbird /tmp/tb-rewrite && cd /tmp/tb-rewrite

git filter-repo \
  --path .smart-env --path data/qdrant --path data/qdrant_storage \
  --path .venv \
  --path config/portal_creds.json --path config/roboform_alpha.txt \
  --path config/roboform_beta.txt --path infra/itinerary_passwords.txt \
  --path-glob 'state/**/cookies*' --path-glob 'state/**/*.sqlite*' \
  --invert-paths
# strip-blobs-by-size catch-all for anything >5MB that slipped through:
git filter-repo --strip-blobs-bigger-than 5M
git reflog expire --expire=now --all && git gc --prune=now --aggressive
# NOTE: filter-repo DELETES the 'origin' remote by default (safety feature).
# Re-add it before pushing:
git remote add origin git@github.com:johnloucks3-sudo/thunderbird-os.git
git push --force origin --all && git push --force origin --tags
```
*(Confirm the exact secret file list with MISSION-264 before running; the `.gitignore` "SECURITY AUDIT 2026-06-15" block is the authoritative target set.)*
**After force-push, the live working repo at `/home/john/Thunderbird` still holds OLD hashes — reset it to the rewritten history (`git fetch && git reset --hard origin/master`) or re-clone, and stop services during the swap.**

**Expected savings:** `.git` ~697 MB → ~**150–250 MB**; remote shrinks on force-push.
**Risk:** **HIGH — rewrites every commit hash.** Force-push required; all clones must re-clone. See §5/security caveats below.
**Links:**
- filter-repo: https://github.com/newren/git-filter-repo · docs: https://github.com/newren/git-filter-repo/blob/main/Documentation/git-filter-repo.txt
- BFG: https://rtyley.github.io/bfg-repo-cleaner/
- filter-branch (deprecated): https://git-scm.com/docs/git-filter-branch
- GitHub "About large files / remove": https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github

### #6 — Prune the 67 branches BEFORE rewrite (precondition for #4 and #5)
Objects reachable from *any* of the 67 branch refs survive gc, and `filter-repo` must rewrite all 67. Delete merged/stale branches first so gc can actually drop blobs and the rewrite is smaller.
```bash
git branch --merged master | grep -vE '^\*|master' | xargs -r git branch -d
git remote prune origin
# review remaining: git for-each-ref --sort=-committerdate refs/heads --format='%(committerdate:short) %(refname:short)'
```
**Savings:** enables the gc/rewrite savings above. **Risk:** low (only `-d` merged branches; review unmerged manually).

### #7 — Resolve the 5 broken gitlinks
`Blackboard`, `mcps/foursquare/foursquare-repo`, `mcps/yelp/yelp-repo`, `reverie`, `tools/fieldflow` are mode-160000 gitlinks with **no `.gitmodules`** — broken submodule refs. `Blackboard` on disk is a plain directory. Decide per path: (a) make it a real submodule (`git submodule add <url> Blackboard`), or (b) de-gitlink and track as normal files:
```bash
git rm --cached Blackboard mcps/foursquare/foursquare-repo mcps/yelp/yelp-repo reverie tools/fieldflow
# then re-add as a submodule OR as regular files, per intent
```
**Savings:** correctness; unblocks clean clones (broken gitlinks break `git submodule update`). **Risk:** low.
**Link:** https://git-scm.com/book/en/v2/Git-Tools-Submodules

### #8 — Git LFS for genuine binaries you must keep (PDFs, ship photos)
If any images/PDFs truly belong in the repo, track via LFS instead of bloating packs. **Free quota: 1 GiB storage + 1 GiB/month bandwidth** per account; over that without a payment method = LFS disabled / pointer-only clones. Given the free cap, prefer **Drive** for bulk ship photos (already the D2M pattern) and reserve LFS for a handful of must-version binaries.
**Risk:** low; watch the 1 GiB bandwidth ceiling on clones.
**Links:** https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-git-large-file-storage · https://docs.github.com/billing/managing-billing-for-git-large-file-storage/about-billing-for-git-large-file-storage

### #9 — Background `git maintenance` for ongoing health
Replaces manual periodic gc with scheduled incremental repack/commit-graph/loose-object cleanup.
```bash
git maintenance start     # registers user-level systemd/cron schedule
```
**Risk:** none. **Link:** https://git-scm.com/docs/git-maintenance

### #10 — Partial/sparse clone for performance (post-rewrite)
For fast checkouts on other machines (Chromebook, fresh boxes):
```bash
git clone --filter=blob:none --sparse <url>   # trees+commits now, blobs on demand
git sparse-checkout set OpsCenter dossiers core   # only the dirs you work in
# avoid --depth=1 for dev clones (breaks many commands; GitHub discourages it)
```
**Link:** https://github.blog/open-source/git/get-up-to-speed-with-partial-clone-and-shallow-clone/

---

## 4. Phased Shrink Plan

**Phase 0 — Safety (do first)**
- Full backup mirror: `git clone --mirror /home/john/Thunderbird /tmp/tb-backup.git`
- Confirm no active services writing to `.git`.

**Phase 1 — Safe de-track + on-disk reclaim (TODAY, no rewrite, low risk)**
1. `rm -rf .venv .claude/worktrees .playwright-mcp` + prune old logs → **~11.5 GB on disk** (#1).
2. Fix the broken `.gitignore` line (#2).
3. `git rm --cached` for `.smart-env`, `data/qdrant*`, tracked `.venv` (#3) — *note: `.git` unchanged here, by design.*
4. Prune merged branches (#6); resolve broken gitlinks (#7).
5. `reflog expire` + `git gc` (#4) — small win now, big win after Phase 2.

**Phase 2 — Coordinated history rewrite (with MISSION-264, ONE pass)**
6. On a fresh clone, run `git filter-repo` stripping **big blobs (.smart-env, qdrant, .venv) AND MISSION-264 secrets together** (#5).
7. `gc --prune=now --aggressive` → `.git` ~697 MB → **~150–250 MB**.
8. **Force-push** the rewritten history; **all clones must delete + re-clone** (hashes changed).
9. After force-push, **open a GitHub Support request** to purge unreachable objects + cached PR/diff views server-side (force-push alone leaves them retrievable — critical for the secret scrub).

**Phase 3 — Ongoing hygiene**
10. `git maintenance start` (#9); LFS only for must-keep binaries within the 1 GiB free cap, Drive for the rest (#8); partial/sparse clones on secondary machines (#10).

---

## 5. Security Tie-In (MISSION-264)

- **Smaller history = smaller secret-exposure surface.** The same `filter-repo` pass that strips `.smart-env`/qdrant must strip the secret files the 2026-06-15 audit untracked (`config/portal_creds.json`, `config/roboform_*.txt`, `config/*.txt`, `infra/itinerary_passwords.txt`, `state/**/cookies*`, `state/**/*.sqlite*`). They are currently `.gitignore`d (stops *new* commits) but **remain in history** until rewritten — so de-tracking is not removal.
- **Force-push is necessary but NOT sufficient.** GitHub keeps **unreachable objects** and **cached PR/diff views** after a force-push; the old blobs stay retrievable until you **contact GitHub Support** to run server GC + dereference cached views. Plan this as an explicit Phase-2 step.
- **Rotate, don't just scrub.** Any credential that was ever committed must be treated as compromised and **rotated** regardless of the rewrite (MISSION-242..245 already in motion). History rewrite reduces future exposure; it does not un-leak a past push.
- **Performance/de-risk bonus:** a ~150–250 MB `.git` (down from 697 MB) plus a ~8 GB working tree (down from 20 GB) means faster clones/CI, well under GitHub's <1 GB performance recommendation and far from the 5 GB soft limit / 100 MB hard file cap.

---

## Sources

- git filter-repo (project): https://github.com/newren/git-filter-repo
- git filter-repo docs: https://github.com/newren/git-filter-repo/blob/main/Documentation/git-filter-repo.txt
- BFG Repo-Cleaner: https://rtyley.github.io/bfg-repo-cleaner/
- git-filter-branch (deprecated): https://git-scm.com/docs/git-filter-branch
- GitHub — About large files on GitHub: https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github
- GitHub — Repository limits (5 GB soft / 100 MB file): https://docs.github.com/en/repositories/creating-and-managing-repositories/repository-limits
- GitHub — Removing sensitive data from a repository: https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository
- GitHub — About Git Large File Storage: https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-git-large-file-storage
- GitHub — Git LFS billing / free quota: https://docs.github.com/billing/managing-billing-for-git-large-file-storage/about-billing-for-git-large-file-storage
- git-gc: https://git-scm.com/docs/git-gc
- git-reflog: https://git-scm.com/docs/git-reflog
- git-maintenance: https://git-scm.com/docs/git-maintenance
- git-rm: https://git-scm.com/docs/git-rm
- gitignore: https://git-scm.com/docs/gitignore
- GitHub Blog — partial clone & shallow clone: https://github.blog/open-source/git/get-up-to-speed-with-partial-clone-and-shallow-clone/
- Git submodules: https://git-scm.com/book/en/v2/Git-Tools-Submodules
