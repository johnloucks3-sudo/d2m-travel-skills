# BLOCKER — Google Form Creation (Stage 1)
**Date:** 2026-06-19  
**Build:** Kuklinski Excursion Product Set  
**Script:** `scripts/create_kuklinski_excursion_form.py`

---

## What Failed

The script ran but could not create the Google Form.

**Error:** `ValueError: Client secrets must be for a web or installed app.`

**Root cause (corrected):** The file at `~/.gmail-mcp/johnloucks3/credentials.json` is an OAuth **token** file (access_token, refresh_token, scope), not an OAuth client secrets file. The script's `InstalledAppFlow.from_client_secrets_file()` call needs a client secrets file — which exists at `/home/john/.credentials/client_secrets.json`.

Additionally, `~/.gmail-mcp/johnloucks3/token.json` does not exist. The script looks for this file first to load prior Forms API credentials.

**The script needs two things:**
1. A `token.json` at the Forms API token path that includes `forms.body` + `drive.file` scopes
2. The client secrets file at `/home/john/.credentials/client_secrets.json` is correct and will work for the OAuth flow

---

## What the Commander Must Do

**One-time setup — run this from YOGA (requires a browser briefly for OAuth):**

```bash
cd /home/john/Thunderbird && python3 scripts/create_kuklinski_forms_auth.py
```

That script doesn't exist yet — Hale will build it. **Alternatively**, run the direct Python snippet:

```bash
cd /home/john/Thunderbird && python3 - <<'EOF'
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
import json

SCOPES = [
    "https://www.googleapis.com/auth/forms.body",
    "https://www.googleapis.com/auth/drive.file",
]
CLIENT_SECRETS = Path.home() / ".credentials" / "client_secrets.json"
TOKEN_PATH = Path.home() / ".gmail-mcp" / "johnloucks3" / "token.json"

flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRETS), SCOPES)
creds = flow.run_local_server(port=0)
TOKEN_PATH.write_text(creds.to_json())
print(f"Token written to {TOKEN_PATH}")
print(f"Scopes: {creds.scopes}")
EOF
```

This opens a browser OAuth flow. Approve the Google Forms + Drive access.  
Once approved, `~/.gmail-mcp/johnloucks3/token.json` is written with the `forms.body` scope.

Then re-run the form creation script:

```bash
cd /home/john/Thunderbird && python3 scripts/create_kuklinski_excursion_form.py
```

---

## Impact on Build

- **Kyle email draft:** Staged WITH the `FORM_URL_PLACEHOLDER` in the CTA button. The draft is in Commander-Review. Before you send, Commander must:
  1. Run the auth snippet above (one-time, ~2 minutes)
  2. Run `python3 scripts/create_kuklinski_excursion_form.py` — saves URL to `cache/kuklinski_excursion_form.json`
  3. Edit the draft in Gmail to replace `FORM_URL_PLACEHOLDER` with the share URL from the JSON file
  4. Review and send

- **All other build stages:** COMPLETE. Stage 0 (PE appendix), Stage 2 (picklist template), and draft staging are all done.

---

## Verification

After running the auth snippet, verify the token was written:

```bash
python3 -c "
import json
from pathlib import Path
p = Path.home() / '.gmail-mcp' / 'johnloucks3' / 'token.json'
d = json.loads(p.read_text())
print('Scope:', d.get('scopes', d.get('scope', 'NOT FOUND')))
print('Has forms.body:', 'forms.body' in str(d.get('scopes', d.get('scope', ''))))
"
```

---

*Written by Hale · 2026-06-19 · Build log: `cache/kuklinski_build_report.md`*
*Corrected: Root cause was missing token.json (not service account). Client secrets at /home/john/.credentials/client_secrets.json confirmed valid (InstalledApp type).*
