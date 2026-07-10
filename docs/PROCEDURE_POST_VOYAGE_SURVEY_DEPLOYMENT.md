# Post-Voyage Survey Portal Deployment Procedure
**Tested & Working:** 2026-07-08 (McLeod/McGlasson Silver Muse)
**Clarity Level:** Haiku-executable (step-by-step, no inference required)

---

## PART 1: LOCATE THE REAL FORM

**Step 1.1** Check `~/drafts/` for existing McLeod survey HTML files:
```bash
grep -l "docs.google.com/forms" ~/Thunderbird/drafts/survey_McLeod*.html
```

**Step 1.2** If a form is found, extract its ID from the URL. The ID is the string between `/forms/d/` and `/viewform`:
```
https://docs.google.com/forms/d/[ID_HERE]/viewform
```

**Step 1.3** If no form is found in drafts, search Google Drive:
- Search Drive for "McLeod" + "survey" or "post-voyage"
- Open the form, copy its full share link
- Extract the form ID from the URL

**✓ Success criteria:** You have a valid Google Form ID that shows 40+ questions about the actual trip (flights, ports, dining, etc.)

---

## PART 2: CREATE THE PORTAL ENTRY

**Step 2.1** Open `/home/john/Thunderbird/config/client_portals.json`

**Step 2.2** Add a new entry in this format (replace bracketed values with your data):
```json
"[SUBDOMAIN].d2mluxury.quest": {
  "slug": "[unique-slug]",
  "name": "[Client Name — Trip Type]",
  "dir": "output/[Folder_Name]",
  "user": "[USERNAME]",
  "pw": "[PASSWORD]",
  "added": "[TODAY'S DATE]",
  "note": "[Brief description]"
}
```

**Example (McLeod):**
```json
"mcleod-survey.d2mluxury.quest": {
  "slug": "mcleod-silvermuse-postsurvey",
  "name": "Erik McLeod & Melissa McGlasson — Silver Muse Post-Voyage Survey",
  "dir": "output/McLeod_SilverMuse_PostSurvey",
  "user": "ERIK",
  "pw": "260618-MUSE",
  "added": "2026-07-08",
  "note": "TP 5.2 post-voyage survey for Silver Muse Mediterranean (Jun 23-Jul 3, 2026). 41 questions on portal. Submit → responses land in form's Google Sheet."
}
```

**✓ Success criteria:** Entry is valid JSON and placed BEFORE the catch-all `"_queued"` section.

---

## PART 3: UPDATE CLOUDFLARE TUNNEL CONFIG

**Step 3.1** Open `~/.cloudflared/config.yml`

**Step 3.2** Locate the section that starts with `# MULTI-CLIENT PORTAL SERVER (2026-07-03)` and the list of existing client hostnames (loucks, lyons, furlow, elydarrow, nichols).

**Step 3.3** Add ONE new line before the catch-all `- service: http_status:404`:
```yaml
  - hostname: [SUBDOMAIN].d2mluxury.quest
    service: http://localhost:8925
```

**Example:**
```yaml
  - hostname: mcleod-survey.d2mluxury.quest
    service: http://localhost:8925
  - service: http_status:404
```

**✓ Success criteria:** YAML is valid (no indentation errors), new line is placed BEFORE the catch-all rule.

---

## PART 4: CREATE OUTPUT DIRECTORY

**Step 4.1** Create the output folder that matches the `"dir"` value from Step 2.2:
```bash
mkdir -p /home/john/Thunderbird/output/McLeod_SilverMuse_PostSurvey/html
```

**Step 4.2** Create the portal HTML page at `/home/john/Thunderbird/output/McLeod_SilverMuse_PostSurvey/html/index.html`:

Use this template. Replace `[FORM_ID]` with your actual form ID (from Step 1.3):

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Silver Muse Post-Voyage Survey — Dreams2Memories Travel</title>
<style>
  * { box-sizing: border-box; }
  body{margin:0;font-family:Georgia,serif;color:#e8f1ff;background:#07076b;
    background:radial-gradient(ellipse at 50% -10%,#2428b0 0%,#0e1088 20%,#07076b 50%,#040450 80%,#02022e 100%);
    background-attachment:fixed;padding:32px 12px}
  .wrap{max-width:640px;margin:0 auto}
  .card{background:#08086e;background:linear-gradient(175deg,#10118c 0%,#09096e 35%,#06065e 70%,#04044c 100%);
    border-radius:10px;overflow:hidden;box-shadow:0 20px 60px rgba(0,0,0,.4)}
  .header{background:#0a0a68;background:linear-gradient(180deg,#0c0c80 0%,#060650 100%);
    padding:26px 24px;text-align:center}
  .header .brand{color:#f0f6ff;font-size:12px;letter-spacing:3.5px;margin-top:6px}
  .shimmer{height:3px;background:linear-gradient(90deg,#07076b 0%,rgba(220,235,255,1) 50%,#07076b 100%)}
  .body{padding:32px 34px}
  h1{color:#f0f6ff;font-size:22px;font-weight:normal;margin:0 0 6px}
  .sub{color:#a8c4f0;font-size:14px;margin:0 0 26px}
  p.lead{line-height:1.8;margin:0 0 20px}
</style>
</head>
<body>
<div class="wrap">
  <div class="card">
    <div class="header">
      <div class="brand">DREAMS2MEMORIES TRAVEL, LLC</div>
    </div>
    <div class="shimmer"></div>
    <div class="body">
      <h1>A few things I'd love your feedback on</h1>
      <p class="sub">Silver Muse Mediterranean · Jun 23 &ndash; Jul 3, 2026</p>

      <p class="lead">Erik and Melissa — welcome home! Your full trip survey is below, covering every leg of the
      journey from the Longmont pickup through Venice. Rate what you'd like, skip what you don't — candor is
      the whole point.</p>

      <div style="background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 8px 24px rgba(0,0,0,.35)">
        <iframe src="https://docs.google.com/forms/d/e/[FORM_EMBED_ID]/viewform?embedded=true"
                width="100%" height="4200" frameborder="0" marginheight="0" marginwidth="0"
                style="display:block">Loading survey…</iframe>
      </div>

      <p style="text-align:center;margin-top:18px">
        <a href="https://docs.google.com/forms/d/e/[FORM_EMBED_ID]/viewform"
           target="_blank" style="color:#a8c4f0;font-size:13px">Open survey in a new tab &rarr;</a>
      </p>
    </div>
  </div>
</div>
</body>
</html>
```

**CRITICAL:** Replace `[FORM_EMBED_ID]` with the form's **embed ID**, which you extract like this:
- Get the form's view URL: `https://docs.google.com/forms/d/e/[EMBED_ID]/viewform`
- The embed ID is the string between `/d/e/` and `/viewform`
- It's different from the edit ID — use the one from the `/viewform` URL

**✓ Success criteria:** File is created at the correct path with valid HTML and the embed URL is correct.

---

## PART 5: REGISTER DNS & RESTART TUNNEL

**Step 5.1** Register the DNS route:
```bash
cloudflared tunnel route dns thunderbird [SUBDOMAIN].d2mluxury.quest
```

**Example:**
```bash
cloudflared tunnel route dns thunderbird mcleod-survey.d2mluxury.quest
```

**Step 5.2** Kill any stale cloudflared processes:
```bash
ps aux | grep cloudflared | grep -v grep | grep -v systemd
```

If you see a process that's NOT the systemd service (check `systemctl --user status thunderbird-tunnel.service` for the MainPID), kill it:
```bash
kill [PID]
```

**Step 5.3** Restart the tunnel service:
```bash
systemctl --user restart thunderbird-tunnel.service
sleep 2
systemctl --user status thunderbird-tunnel.service
```

**✓ Success criteria:** Service shows "active (running)" and no stale cloudflared processes remain.

---

## PART 6: VERIFY PORTAL IS LIVE

**Step 6.1** Test no-auth (should get 401):
```bash
curl -s -o /dev/null -w "%{http_code}\n" --noproxy '*' https://[SUBDOMAIN].d2mluxury.quest/
```

**Step 6.2** Test wrong password (should get 401):
```bash
curl -s -o /dev/null -w "%{http_code}\n" -u "ERIK:wrongpass" --noproxy '*' https://[SUBDOMAIN].d2mluxury.quest/
```

**Step 6.3** Test correct credentials (should get 200):
```bash
curl -s -o /dev/null -w "%{http_code}\n" -u "ERIK:[REDACTED-see-storage/passwords]" --noproxy '*' https://[SUBDOMAIN].d2mluxury.quest/
```

**Step 6.4** Verify the form is embedded (should print the form's ID):
```bash
curl -s -u "ERIK:[REDACTED-see-storage/passwords]" --noproxy '*' https://[SUBDOMAIN].d2mluxury.quest/ | grep -o "1FAIpQLS[^\"]*" | head -1
```

**✓ Success criteria:** No-auth → 401, wrong pw → 401, correct creds → 200, form ID appears in output.

---

## PART 7: CREATE GMAIL DRAFT

**Step 7.1** Update `~/Thunderbird/drafts/survey_McLeod_McGlasson_1782926528.html` (or create it) with this body section:

```html
<p style="margin:0 0 24px 0">John put together a full survey covering every leg of the trip — the Longmont pickup, both flights, Rome, Florence, embarkation, every port, dining, the birthday celebration, disembarkation, and the trip home. Rate what you'd like, skip what you don't. It's on a private page just for the two of you:</p>

<div style="text-align:center;margin:8px 0 24px 0">
  <a href="https://[SUBDOMAIN].d2mluxury.quest/"
     style="background:#c8d8ff;color:#07076b;padding:14px 32px;border-radius:6px;font-family:Georgia,serif;font-size:16px;font-weight:bold;text-decoration:none;display:inline-block">
    Share Your Feedback &rarr;
  </a>
</div>

<p style="margin:0 0 8px 0;text-align:center;color:#c8dcff;font-size:14px">
  <strong>Username:</strong> ERIK &nbsp;&middot;&nbsp; <strong>Password:</strong> 260618-MUSE
</p>
<p style="margin:0 0 24px 0;text-align:center;color:#a8c4f0;font-size:12px;font-style:italic">
  If the button doesn't work, copy this link: https://[SUBDOMAIN].d2mluxury.quest/
</p>

<p style="margin:0 0 20px 0">Reply whenever you have a moment — no rush, I know there's jet lag to sort through. And if anything went sideways during the trip itself that we should know about, please tell me that too.</p>
```

**Step 7.2** Create the Gmail draft via:
```bash
python3 /home/john/Thunderbird/scripts/create_johnloucks3_draft.py \
  --html /home/john/Thunderbird/drafts/survey_McLeod_McGlasson_1782926528.html \
  --to "emcleod@gmail.com; memcglas@gmail.com" \
  --subject "A few things I'd love your feedback on, Erik and Melissa"
```

**✓ Success criteria:** Script outputs "SUCCESS! Draft created" with a Draft ID.

---

## PART 8: SEND & CONFIRM

**Step 8.1** Commander reviews draft in `johnloucks3@gmail.com` drafts folder

**Step 8.2** Commander clicks the survey link to verify it loads

**Step 8.3** Commander sends the draft

**✓ Success criteria:** Client receives email and can click through to survey with login ERIK/260618-MUSE.

---

## CHECKLIST — Run This to Verify All Steps

```bash
# 1. Form exists
grep -o "1FAIpQLS[^\"]*" ~/Thunderbird/drafts/survey_McLeod*.html | head -1

# 2. Portal registry entry exists
grep "mcleod-survey.d2mluxury.quest" ~/Thunderbird/config/client_portals.json

# 3. Cloudflare config entry exists
grep "mcleod-survey.d2mluxury.quest" ~/.cloudflared/config.yml

# 4. Output directory exists
test -d ~/Thunderbird/output/McLeod_SilverMuse_PostSurvey/html && echo "OK"

# 5. HTML file exists
test -f ~/Thunderbird/output/McLeod_SilverMuse_PostSurvey/html/index.html && echo "OK"

# 6. Portal is live
curl -s -o /dev/null -w "%{http_code}\n" -u "ERIK:[REDACTED-see-storage/passwords]" --noproxy '*' https://mcleod-survey.d2mluxury.quest/

# 7. Form is embedded
curl -s -u "ERIK:[REDACTED-see-storage/passwords]" --noproxy '*' https://mcleod-survey.d2mluxury.quest/ | grep "1FAIpQLS" | wc -l
```

---

## TROUBLESHOOTING

| Symptom | Cause | Fix |
|---------|-------|-----|
| Portal returns 404 | Cloudflared process is stale or config not reloaded | Kill stale processes (Step 5.2), restart service (Step 5.3) |
| Portal returns 401 even with correct creds | Basic Auth credentials mismatch | Verify `user` and `pw` in registry match what you're testing with |
| Form doesn't load in iframe | Embed ID is wrong or form is not publicly accessible | Extract embed ID from `/viewform` URL, verify form can be opened in incognito mode |
| Gmail draft doesn't appear in drafts | Script failed silently or wrong account | Check script output for error message, verify `create_johnloucks3_draft.py` exists |

---

## REFERENCE

- **Portal server:** `/home/john/Thunderbird/scripts/client_portal_server.py` (port 8925, Basic Auth, static files)
- **Registry:** `/home/john/Thunderbird/config/client_portals.json` (JSON file defining all clients)
- **Tunnel config:** `~/.cloudflared/config.yml` (Cloudflare tunnel routing)
- **Form responses:** Responses land directly in the Google Form's Responses sheet (visible to Commander via `forms_get_responses` MCP tool)
