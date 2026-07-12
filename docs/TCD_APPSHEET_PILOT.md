# TCD → AppSheet Pilot (Phase 0-1)

**Goal of the pilot:** prove the Google-native front-end — every board item links
to where it actually lives (no dead ends) — on a surface Google hosts and
maintains, *without touching the existing custom TCD* (which stays running as
fallback until Phase 4 is explicitly authorized).

Architecture: **Thunderbird Python (unchanged, on the box) → Google Sheet
(data plane) → AppSheet (interactive board) + Looker Studio (dashboards, later).**

---

## Phase 0 — the data plane (Python, on the box)

The `tcd/` package collects the current TCD dataset, gives every item a real
source deep-link, and writes it to one Google Sheet tab (`Items`).

**Offline check first (no creds needed):**
```bash
cd /home/john/Thunderbird
python -m tcd.sheet_sync --dry-run --no-gmail --out /tmp/rows.json
# → prints "rows missing a link: 0 (all rows linked ✓)"
```

**Live sync (on the box, creds present):**
```bash
# dry-run against real data incl. Gmail — nothing is written to Google:
python -m tcd.sheet_sync --dry-run --out rows.json
#   inspect rows.json: Gmail rows present, every row has a "link"

# live: creates the Sheet on first run, id saved to config/tcd_sheet_config.json
python -m tcd.sheet_sync
# → prints the Sheet URL
```

Open the Sheet. **Phase-0 go/no-go:** click a Gmail row's `link` → that exact
message opens; a Calendar/Drive row → that event/file; a dossier row → a Drive
search that surfaces the dossier. No dead ends.

The `Items` tab columns (order-locked; AppSheet uses the first, `id`, as the key):

| col | purpose |
|---|---|
| `id` | stable key across syncs |
| `inbox` | strategic / operational / reference |
| `type` | decision / paper / brief / email |
| `priority` | p0 / p1 / p2 / routine |
| `stage` | **P-D-T-A-C** pill (P propose · D decide · T task · A accomplish · C certify · REF reference) |
| `title`, `from`, `date`, `snippet`, `body` | display |
| `link` | **URL — deep-link to source (requirement #1)** |
| `sourcePath` | foundation pointer (where Phase-2 write-back will act) |
| `comments` | serialized; Phase-2 write-back appends here |
| `status` | OPEN / REF / DISPOSE (Phase-2 dispose signal) |

Re-running the sync is safe: it's an idempotent full clear+rewrite keyed by `id`.

---

## Phase 1 — the AppSheet board (browser, ~10 min)

> This step is authored in AppSheet's web editor under your Workspace login — it
> can't be scripted for you. AppSheet auto-generates the base app from the
> Phase-0 Sheet in a few clicks.

1. **Create the app.** Go to **appsheet.com** → **Create → App → Start with
   existing data** → connect Google Sheets → pick the
   *"Thunderbird Commander Desktop — Items"* spreadsheet → `Items` tab.
   AppSheet reads the header row and infers columns.

2. **Make `link` clickable.** Data → Columns → `link` → set **Type = URL**.
   (Optionally set its display name to "Open source" and turn on "open in new
   window".) This is the whole point of the pilot — URL-typed columns render as
   clickable links straight to the source.

3. **Stage pills.** Data → Columns → `stage` → **Type = Enum**, values
   `P, D, T, A, C, REF`. (Optional: Format Rules to color each stage — e.g. D
   amber, A orange, C green — for at-a-glance pills.)

4. **Three inbox views.** UX → Views → add table/deck views filtered by
   `inbox`:
   - **Strategic** (`inbox = "strategic"`)
   - **Operational** (`inbox = "operational"`)
   - **Reference** (`inbox = "reference"`)
   Group each by `stage` (or `priority`) for scanability.

5. **Detail view.** AppSheet auto-creates a detail view; confirm it shows
   `title`, `from`, `date`, `body`, the clickable `link`, `stage`, and
   `sourcePath`.

6. **Watch / Outbox slices (optional this phase).** Data → Slices:
   - **Watch** = rows where `stage` is `A` or `C` (work in flight).
   - **Outbox** = rows where `status = "DISPOSE"` (empty until Phase 2).

7. **Lock it down.** Settings → Security → require sign-in, restrict to your
   Workspace account only. No Basic-Auth, no tunnel — Google hosts it.

**Pilot proof (go/no-go for the migration):** open the app on phone + desktop,
click items → links resolve to the real Gmail message / Calendar event / Drive
file / dossier, inside a Google-hosted UI you didn't have to build or babysit.

---

## Keeping it fed (optional, after the pilot passes)

Add a systemd **user** timer on the box mirroring the existing keepalive-timer
pattern, e.g. `tcd-sync.timer` every N minutes → `python -m tcd.sheet_sync`.
Because the sync is an idempotent clear+rewrite keyed by `id`, re-runs are safe.
This one timer is the *only* new box-side service — and it's what eventually
*replaces* `tcd-server.service` + the tunnel + Basic-Auth (Phase 4,
decision-gated).

## Rollback

The sync only ever writes to its own new Sheet and
`config/tcd_sheet_config.json` — it touches no existing files or services. To
back out: stop the timer (if added) and delete the Sheet. The current custom TCD
is untouched throughout the pilot and remains the live fallback.

---

## Phase 3 status: DONE (2026-07-12)

Looker Studio report built by the Commander directly in the editor (report ID
in `config/tcd_sheet_config.json`), three pages — Intel / Tech Scans / Next 7
Days — each a table over the matching Sheet tab with `title`/`date`/`priority`/
`link` columns, `link` set to URL type. Verified: 0 of 51 rows across the
three tabs are missing a `link` value (checked via `sheets_read_data`), so
every row in the rendered report resolves to a real source — same
"no dead ends" bar as Phase 0/1. Read-only, doesn't touch the Items tab or
AppSheet.

## Not in this phase (decision-gated)

- **Phase 4 — decommission** the custom HTML dashboard, tunnel, Basic-Auth,
  `tcd-server.service`.
- **Phase 5 — Keep** (service account + domain-wide delegation) and an Android
  SMS-gateway for Google-Messages-style texting.
