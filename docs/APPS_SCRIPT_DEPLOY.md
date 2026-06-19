# Apps Script Deployment — Thunderbird Wing Dashboard

**Target Sheet:** `1GFjUe8RvP-GT4YHGn0DYv_BEAZGXlYfwEicFrm8ANuU` (Booking Master)
**Script file:** `scripts/apps_script/wing_dashboard.gs`
**clasp version:** 3.3.0

---

## One-Time Setup

### Step 1 — Login (requires browser)

Run in a terminal connected to a display:

```bash
clasp login
```

This opens a browser window. Authorize with **johnloucks3@gmail.com**.
On success, `~/.clasprc.json` is created.

### Step 2 — Create and deploy bound script

```bash
bash /home/john/Thunderbird/scripts/clasp_init.sh
```

This does three things:
1. Creates an Apps Script project bound to the Booking Master sheet
2. Updates `.clasp.json` with the real `scriptId`
3. Pushes `wing_dashboard.gs` and `appsscript.json`

### Step 3 — Verify in the sheet

Open the Booking Master sheet. Look for the **Wing Ops** menu in the toolbar.
If it does not appear: Refresh → Extensions → Apps Script → Run `onOpen` manually.

### Step 4 — Enable hourly trigger

```bash
cd /home/john/Thunderbird/scripts/apps_script
clasp run createHourlyTrigger
```

This installs the time-driven trigger that auto-formats the sheet hourly.

---

## Subsequent Deployments

After `wing_dashboard.gs` is edited, push the update:

```bash
bash /home/john/Thunderbird/scripts/deploy_apps_script.sh
```

The script checks for auth and a valid `scriptId` before pushing.

---

## File Layout

```
scripts/apps_script/
  wing_dashboard.gs      # Main Apps Script source
  appsscript.json        # Manifest (timezone, runtime V8)
  package.json           # clasp project metadata
  .clasp.json            # scriptId (PLACEHOLDER until clasp_init.sh runs)
scripts/
  clasp_init.sh          # One-time setup — run after clasp login
  deploy_apps_script.sh  # Incremental push — run after each .gs edit
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `~/.clasprc.json` missing | Run `clasp login` |
| `scriptId` is PLACEHOLDER | Run `clasp_init.sh` |
| `clasp push` fails with 403 | Re-run `clasp login` — token expired |
| Menu not visible in sheet | Refresh sheet; run `onOpen` from Apps Script editor |
| Trigger not firing | Check Apps Script editor → Triggers tab |

---

*Last updated: 2026-06-19*
