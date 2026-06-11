# D2M Front Door — Deploy Notes (Commander step)

Non-technical request intake. No auth, no account. Public form → reference number → status check.
Built + tested locally by ELON (A12). **NOT deployed — deployment is a Commander action.**

## What it is
- `server.py` — FastAPI, port **8790**. 3 endpoints: `GET /` (page), `POST /api/request`, `GET /api/status/{ref}`.
- `static/index.html` — single page, two tabs (Send a Request / Check Status). D2M palette.
- `requests.jsonl` — created on first real submit. **Source of truth** for status. Wing updates status by appending a row (last-write-wins).

## Safety model (load-bearing — do not change without re-reading)
The live watcher `OpsCenter/thunderbird_tasking_watcher.py` AUTO-SPAWNS a headless agent on inbox
entries whose status is in `TRIGGER_STATUSES` (PENDING / UNREAD / ACTIVE-CRITICAL / FLAGGED-OVERDUE / NEXUS:).
This form is unauthenticated, so it writes **`status: TRIAGE`** + `from: Front Door (external)` to
`opencode_inbox.md` — an inert status the watcher ignores. Public input never auto-spawns an agent and
never impersonates the Commander. A human routes triage items.
Control characters in submissions are collapsed so a payload can't forge a task header or a trigger status.

## Run locally
```
/home/john/Thunderbird/.venv/bin/python /home/john/Thunderbird/web/frontdoor/server.py
# http://127.0.0.1:8790/
```

## Deploy (Commander step — not done)
1. **systemd unit** — mirror `deploy/d2m-portal.service`. Create `deploy/d2m-frontdoor.service`:
   ```ini
   [Unit]
   Description=D2M Front Door — public request intake
   After=network.target

   [Service]
   Type=simple
   WorkingDirectory=/home/john/Thunderbird/web/frontdoor
   ExecStart=/home/john/Thunderbird/.venv/bin/python /home/john/Thunderbird/web/frontdoor/server.py
   Restart=always
   User=john

   [Install]
   WantedBy=default.target
   ```
   Install: `systemctl --user daemon-reload && systemctl --user enable --now d2m-frontdoor`
2. **Cloudflare tunnel route** — add a hostname (e.g. `start.d2mluxury.quest` or `frontdoor.d2mluxury.quest`)
   → `http://127.0.0.1:8790`, same pattern as the portal/itinerary tunnel (`deploy/start_tunnel.sh`).
3. **Verify:** `curl https://<hostname>/health` → `{"ok":true,...}`.
4. **Wing wiring (optional):** to surface front-door triage items in Hale's brief, point a reader at
   `opencode_inbox.md` blocks with `from: Front Door (external)`. Status updates are written back to
   `requests.jsonl` (set `status` + optional `note` on a new appended row for that ref).

## Notes
- Rate limit: 5 submissions / hour / IP (in-memory; resets on restart). Honors `X-Forwarded-For` for tunnel.
- Bind is `127.0.0.1` — reach it only through the tunnel, never exposed raw.
