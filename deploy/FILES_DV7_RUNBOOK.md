# files.d2mluxury.quest — YOGA→dv7 Sync + File Server Runbook

**Author:** Hale (CC) · **Date:** 2026-07-16 · **Status:** YOGA side LIVE · dv7 side READY-BUT-UNEXECUTED (dv7 offline)

## Goal
Let the Commander reach D2M session output (dossiers, itineraries, intel, blackboard)
from any device **when YOGA is off**, at `https://files.d2mluxury.quest`.

## Ground truth found 2026-07-16 (corrects the original tasking)
1. **dv7 is OFFLINE** — Tailscale reports `john-hp-pavilion-dv7-notebook-pc` (100.78.111.98)
   "offline, last seen 7d ago". Nothing dv7-side could be executed or verified. All dv7
   steps below are a runbook to run from a session that can reach dv7.
2. **`files.d2mluxury.quest` already exists** in the live tunnel config
   (`~/.cloudflared/config.yml`), routing to `localhost:8900` = `scripts/thunderbird_dir_server.py`,
   which serves the **entire `/home/john/Thunderbird` repo** (all dossiers, client data) with
   **weak 4-digit tokens** (`0602`, `7344`, `2502`) and **no Cloudflare Access** — app Basic Auth
   only. See "Security flag" below.
3. **The tunnel runs on YOGA, not dv7.** So today `files.d2mluxury.quest` is DOWN whenever YOGA
   is off — it does not yet meet the Commander's need. Making it always-on requires the origin
   (and the tunnel ingress serving it) to live on dv7.
4. **A healthy Google Drive mirror already runs** (`thunderbird-drive-sync.timer`, last success
   2026-07-15 23:07, exit 0 → `d2mconcierge:Thunderbird_Mirror/`). This already gives always-on
   access to session output via drive.google.com without YOGA — the zero-infra answer for today.

## What is LIVE on YOGA now
- `scripts/yoga_dv7_files_sync.sh` — curated, secret-safe rsync YOGA→`dv7:~/thunderbird_files/`.
  Syncs: `dossiers output intel OpsCenter/collaboration Blackboard session_autosave_latest.md
  hale_brief.md hale_state.json`. Excludes all secrets (`*_token.json`, `*.env`, `*.pem`, `*.key`,
  `creds/**`, …), `logs/` (1GB), storage backups, `.git`, venvs. Skips cleanly when dv7 is offline.
- `deploy/yoga-dv7-files-sync.{service,timer}` — installed + enabled, runs every 20 min.
  Verified: fires, detects dv7 offline, logs `dv7 offline/unreachable — skipped`, exits 0.
  The moment dv7 comes online it will begin pushing automatically.
- `scripts/dv7_files_server.py` — the file server dv7 will run. Verified locally on YOGA:
  401 without auth, 200 with auth, directory browsing, file fetch, path-traversal blocked (404).

## dv7 steps (run when dv7 is online)

### 1. Confirm the sync has landed
```bash
# from YOGA (or wait for the 20-min timer):
bash ~/Thunderbird/scripts/yoga_dv7_files_sync.sh
ssh dv7 'ls ~/thunderbird_files'   # expect: Blackboard dossiers hale_brief.md hale_state.json intel output ...
```

### 2. Copy the server to dv7 and set the password
```bash
scp ~/Thunderbird/scripts/dv7_files_server.py dv7:~/dv7_files_server.py
# choose a strong password (example generator):
FILES_PW=$(openssl rand -hex 12)
echo "files.d2mluxury.quest Basic Auth  user=john  pw=$FILES_PW"   # record it
```

### 3. Install the systemd service on dv7
```bash
ssh dv7 "cat > ~/.config/systemd/user/dv7-files.service" <<EOF
[Unit]
Description=D2M Files server — files.d2mluxury.quest (:8930)
After=network-online.target

[Service]
Type=simple
Environment=DV7_FILES_DIR=%h/thunderbird_files
Environment=DV7_FILES_PORT=8930
Environment=DV7_FILES_USER=john
Environment=DV7_FILES_PW=REPLACE_WITH_STRONG_PW
ExecStart=/usr/bin/python3 %h/dv7_files_server.py
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
EOF
# NOTE: replace REPLACE_WITH_STRONG_PW above with the $FILES_PW value from step 2.
ssh dv7 'systemctl --user daemon-reload && systemctl --user enable --now dv7-files.service'
# smoke test (substitute the real password for the PW shell var):
ssh dv7 "PW='<paste-pw>'; curl -sS -o /dev/null -w '%{http_code}\n' -u \"john:\$PW\" http://127.0.0.1:8930/"  # expect 200
```
> If dv7 systemd user services need `loginctl enable-linger john` to run without an active login, set it once.

### 4. Route files.d2mluxury.quest to dv7's origin — pick ONE

The tunnel currently runs on YOGA. Two clean ways to make files always-on from dv7:

- **Option A (recommended): serve from dv7's own tunnel.** dv7 already runs `d2m-tunnel.service`.
  Add to dv7's cloudflared config ingress (above the `http_status:404` catch-all):
  ```yaml
    - hostname: files.d2mluxury.quest
      service: http://localhost:8930
  ```
  Then in the Cloudflare dashboard, point the `files` CNAME/route at dv7's tunnel, and REMOVE the
  `files.d2mluxury.quest` line from YOGA's `~/.cloudflared/config.yml` so the two tunnels don't
  both claim the hostname. `cloudflared tunnel route dns <dv7-tunnel> files.d2mluxury.quest`.
- **Option B (interim): keep YOGA's tunnel, point it at dv7 over Tailscale.** In YOGA's
  `~/.cloudflared/config.yml` change the existing `files` entry to
  `service: http://100.78.111.98:8930` and bind `dv7_files_server.py` to `0.0.0.0`.
  Downside: still requires YOGA up (defeats the purpose) — use only as a bridge.

### 5. Gate with Cloudflare Access (mandatory — this exposes real client data)
Zero Trust dashboard → Access → Applications → Add application → Self-hosted:
- **Name:** `Files (Internal)`
- **Application domain:** subdomain `files`, domain `d2mluxury.quest`, path blank
- **Session Duration:** 24 hours
- **Policy:** Allow → Include → Emails: `johnloucks3@gmail.com` (+ any staff addresses needed)

Account ID `86ad4247d8ea3f48f8545c2f05024787`. This is the SAME pattern the runbook
`docs/cloudflare_access_dashboards_runbook.md` prescribes for `costs`/`ops` dashboards — CF Access
is the only effective gate for tunnel-to-app hostnames (nginx auth is bypassed by the tunnel).

### 6. Verify end-to-end
```bash
curl -sS -o /dev/null -w '%{http_code}\n' https://files.d2mluxury.quest/   # expect 302 -> cloudflareaccess.com login (Access gate)
# after Access login in a browser: dark-navy file listing of thunderbird_files
```

## Security flag (pre-existing, worth the Commander's decision)
`files.d2mluxury.quest` today → YOGA `:8900` `thunderbird_dir_server.py` serves the WHOLE repo
with 4-digit tokens and no CF Access. Recommend: once dv7 serves the curated set (Option A),
either (a) drop `files` from YOGA's config entirely, or (b) put YOGA's `:8900` server behind CF
Access too and rotate the weak tokens. The curated dv7 set contains no secrets by construction;
the YOGA whole-repo server does not have that guarantee.

## Rollback
- YOGA: `systemctl --user disable --now yoga-dv7-files-sync.timer`; delete the two unit files.
- dv7: `systemctl --user disable --now dv7-files.service`; remove the `files` ingress line; restart cloudflared.
