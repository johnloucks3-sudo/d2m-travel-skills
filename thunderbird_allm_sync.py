"""
AnythingLLM Dossier Sync
Uploads all active dossiers to the D2M Intelligence workspace.
Run once manually: python3 thunderbird_allm_sync.py
Also callable from Telegram C2 via /allm command (future).
"""
import os
import json
import urllib.request
import urllib.error
from pathlib import Path

ALLM_API = "http://localhost:3001/api/v1"
ALLM_KEY = "***REMOVED-SECRET***"
WORKSPACE_SLUG = "my-workspace"
DOSSIER_DIR = Path(__file__).parent / "dossiers"

ACTIVE_DOSSIERS = [
    "Loucks_Personal_SilverNova_Japan.md",
    "DOSSIER_SilverNova_Pacific_Apr2026.md",
    "Furlow_Regent_3071222.md",
    "Ely_Darrow_Regent_3096289.md",
    "Nichols_Regent_3078056.md",
    "DOSSIER_Grandeur_Scandinavia_Aug2026.md",
    "DOSSIER_VikingMars_PanamaCanal_Dec2026.md",
    "Kuklinski_Viking_Panama.md",
    "Morton_Joshua_Erica_Viking_Panama.md",
    "Lyons_Nancy_Ken.md",
]

HEADERS = {
    "Authorization": f"Bearer {ALLM_KEY}",
    "Content-Type": "application/json",
}


def api(method: str, path: str, data: dict = None):
    url = f"{ALLM_API}{path}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"error": e.read().decode()}


def upload_raw_text(filename: str, content: str) -> dict:
    """Upload raw text to AnythingLLM document store."""
    boundary = "----D2MBoundary"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: text/plain\r\n\r\n"
    ).encode() + content.encode() + f"\r\n--{boundary}--\r\n".encode()

    url = f"{ALLM_API}/document/raw-text"
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {ALLM_KEY}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        # Fallback: use text-based document creation
        return {"error": error_body}


def upload_via_text_endpoint(title: str, content: str) -> dict:
    """Use AnythingLLM's text ingestion endpoint."""
    data = {
        "textContent": content,
        "metadata": {"title": title, "source": "D2M Thunderbird Dossier"},
        "addToWorkspace": WORKSPACE_SLUG,
    }
    return api("POST", "/document/create-folder", {"name": "dossiers"})


def main():
    print(f"AnythingLLM Dossier Sync — {ALLM_API}")
    print(f"Workspace: {WORKSPACE_SLUG}")
    print()

    # Create dossiers folder in ALLM
    folder_result = api("POST", "/document/create-folder", {"name": "dossiers"})
    print(f"Folder: {folder_result.get('message', folder_result)}")

    uploaded = 0
    for fname in ACTIVE_DOSSIERS:
        fpath = DOSSIER_DIR / fname
        if not fpath.exists():
            print(f"  ⚠️  Not found: {fname}")
            continue

        content = fpath.read_text()
        # Trim to reasonable size (AnythingLLM handles chunking)
        if len(content) > 100_000:
            content = content[:100_000]

        print(f"  Uploading {fname} ({len(content):,} chars)...", end=" ")

        # Try raw text upload
        boundary = "----D2MBoundary"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{fname}"\r\n'
            f"Content-Type: text/plain\r\n\r\n"
        ).encode() + content.encode() + f"\r\n--{boundary}--\r\n".encode()

        url = f"{ALLM_API}/document/upload"
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Authorization": f"Bearer {ALLM_KEY}",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read())
                doc_location = result.get("documents", [{}])[0].get("location", "")
                print(f"✅  location={doc_location[:40]}")

                # Add to workspace
                if doc_location:
                    embed_result = api("POST", f"/workspace/{WORKSPACE_SLUG}/update-embeddings", {
                        "adds": [doc_location],
                        "deletes": [],
                    })
                    status = embed_result.get("workspace", {}).get("name", embed_result)
                    print(f"     Embedded: {status}")
                uploaded += 1

        except urllib.error.HTTPError as e:
            print(f"❌  {e.code}: {e.read().decode()[:100]}")
        except Exception as ex:
            print(f"❌  {ex}")

    print(f"\nDone — {uploaded}/{len(ACTIVE_DOSSIERS)} dossiers synced to AnythingLLM.")
    print(f"Chat at: https://allm.d2mluxury.quest")


if __name__ == "__main__":
    main()
