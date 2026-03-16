# Thunderbird HUD — Workspace Add-on Deployment

## Your Connection Details

- **Tunnel URL:** `https://tear-andale-livestock-plastic.trycloudflare.com`
  (Changes on restart — check `~/Thunderbird/tunnel.log` for current URL)
- **API Key:** See `~/Thunderbird/api_key.txt`

## Step 1 — Create the Apps Script Project

1. Go to https://script.google.com
2. Click **New project**
3. Name it: `Thunderbird HUD`

## Step 2 — Add the Code

1. Delete the placeholder `function myFunction() {}` code
2. Paste the entire contents of `Code.gs` into the editor
3. Click **Project Settings** (gear icon on left)
4. Check **Show "appsscript.json" manifest file in editor**
5. Click **Editor** (< > icon), click `appsscript.json` tab
6. Replace its contents with the `appsscript.json` file from this folder

## Step 3 — Set API Connection

1. In the script editor, select `setApiConfig` from the function dropdown
2. First, edit the function to use your actual values:
   - `THUNDERBIRD_URL`: Your tunnel URL from above
   - `THUNDERBIRD_API_KEY`: Contents of `~/Thunderbird/api_key.txt`
3. Click Run
4. Authorize when prompted (Gmail + external request permissions)

## Step 4 — Test Deployment

1. Click **Deploy** > **Test deployments**
2. Under **Application type**, select **Google Workspace Add-on**
3. Click **Install**
4. Open Gmail — you should see the Thunderbird icon in the right sidebar

## Step 5 — Use on Phone

1. Open Gmail app on Samsung Z Fold 6
2. The add-on appears when viewing any email (contextual trigger)
3. Tap the Thunderbird icon to see: Summary, Draft Reply, Search Similar
4. Homepage shows: Briefing, Fare Watches, Intel tools

## Tunnel Management

The tunnel URL changes each time the service restarts. To get the current URL:

```bash
grep -oP 'https://[a-z0-9-]+\.trycloudflare\.com' ~/Thunderbird/tunnel.log | tail -1
```

Then update in Apps Script:
1. Open script.google.com > Thunderbird HUD
2. Update the URL in `setApiConfig()` > Run it

For a permanent URL, create a free Cloudflare account and set up a named tunnel.

## Running Services

```bash
systemctl status d2m-scheduler    # Intel scheduler
systemctl status d2m-api          # REST API (port 8766)
systemctl status d2m-tunnel       # Cloudflare tunnel
```
