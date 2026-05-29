# LESSON: Google Drive Upload — Step-by-Step for Lesser Models

## WHY THIS EXISTS

The Google Drive upload path has TWO broken approaches and ONE working approach.
A lesser model will try the broken approaches first. This document prevents that.

## BROKEN APPROACHES — Do Not Attempt

### BROKEN-1: n8n webhook (`d2m_drive_upload.py`)
**Script:** `/home/john/Thunderbird/d2m_drive_upload.py`
**Error:** HTTP 500 — "No Respond to Webhook node found in the workflow"
**Root cause:** The n8n workflow at `https://n8n.d2mluxury.quest/webhook/drive-upload` lacks a "Respond to Webhook" node. It accepts the file but never completes the HTTP handshake.
**Do not use this script.**

### BROKEN-2: MCP tool import (`upload_to_drive.py`)
**Script:** `/home/john/Thunderbird/upload_to_drive.py`
**Error:** `ModuleNotFoundError: No module named 'mcp.server'`
**Root cause:** The script inserts `/home/john/Thunderbird/core` into `sys.path` before site-packages. There is a `/home/john/Thunderbird/core/mcp/` directory that shadows the installed `mcp` package (which lives in the venv's site-packages). Python finds `core/mcp/` first, which has no `server/fastmcp` submodule.
**Do not use this script.**

## WORKING APPROACH — Direct Google API Client

Use the Google Drive API directly via `googleapiclient`. Do NOT import anything from `thunderbird_drive.py` or use MCP tools.

### Step-by-Step

```python
import json
from pathlib import Path
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# SETUP — Environment (required for OAuth on headless)
# export OAUTHLIB_INSECURE_TRANSPORT=1

# STEP 1 — Load OAuth token
# Valid token exists at: /home/john/Thunderbird/drive_token.json
# If missing, run: python3 api/thunderbird_google_auth.py --authorize-headless
token_file = Path("/home/john/Thunderbird/drive_token.json")
if not token_file.exists():
    print("ERROR: No drive_token.json found. Run OAuth authorization first.")
    exit(1)

# STEP 2 — Load and refresh credentials
creds = Credentials.from_authorized_user_file(
    str(token_file),
    ["https://www.googleapis.com/auth/drive"]
)

if creds and creds.expired and creds.refresh_token:
    creds.refresh(Request())
    # Save refreshed token back
    token_file.write_text(creds.to_json())

# STEP 3 — Build Drive service
service = build("drive", "v3", credentials=creds)

# STEP 4 — Upload a file
def upload_to_drive(local_path, drive_filename=None):
    p = Path(local_path)
    name = drive_filename or p.name

    # Determine MIME type
    if p.suffix == ".html":
        mime = "text/html"
    elif p.suffix == ".md":
        mime = "text/markdown"
    elif p.suffix == ".pdf":
        mime = "application/pdf"
    else:
        mime = "application/octet-stream"

    media = MediaFileUpload(str(p), mimetype=mime, resumable=True)
    metadata = {"name": name}
    # Optional: add to a specific folder
    # metadata["parents"] = ["FOLDER_ID_HERE"]

    uploaded = service.files().create(
        body=metadata,
        media_body=media,
        fields="id, name, webViewLink"
    ).execute()

    return {
        "file_id": uploaded["id"],
        "name": uploaded["name"],
        "link": uploaded["webViewLink"]
    }

# STEP 5 — Call it
result = upload_to_drive(
    local_path="/home/john/Thunderbird/output/my_file.html",
    drive_filename="My_File.html"
)
print(f"Uploaded: {result['link']}")
```

## KEY FOLDER IDs

| Folder | ID |
|--------|-----|
| D2M root | `1MjjbqQVnzMYpHyAtNu-zZej-1mXhHkGk` |
| Kuklinski | `1aVU22PPvcKMUFtyRDDpAYhqCvWTBohR7` |

## TOKEN REFRESH

The `drive_token.json` file auto-refreshes via `creds.refresh(Request())` above.
If token is expired AND has no refresh_token (e.g., it's a service account), re-run:
```
python3 api/thunderbird_google_auth.py --authorize-headless
```

## COMMANDER'S QUICK COMMAND
For future sessions, to upload a file, run this ONE-LINER:
```bash
cd /home/john/Thunderbird && source .venv/bin/activate && python3 << 'PYEOF'
import json; from pathlib import Path; from google.oauth2.credentials import Credentials; from google.auth.transport.requests import Request; from googleapiclient.discovery import build; from googleapiclient.http import MediaFileUpload
c=Credentials.from_authorized_user_file(str(Path("drive_token.json")),["https://www.googleapis.com/auth/drive"])
if c.expired: c.refresh(Request()); Path("drive_token.json").write_text(c.to_json())
s=build("drive","v3",credentials=c)
m=MediaFileUpload("output/FILE_NAME",resumable=True)
r=s.files().create(body={"name":"DRIVE_NAME"},media_body=m,fields="id,webViewLink").execute()
print(r["webViewLink"])
PYEOF
```
Replace `FILE_NAME` and `DRIVE_NAME` with your values.
