"""
D2M Google Drive Reorganization Script
Dreams2Memories Travel, LLC — johnloucks3@gmail.com
------------------------------------------------------
- Uses OAuth (client_secret.json) for Drive write access
- Safe mode: skips files that already exist in destination
- Detailed log of every action taken
- Run: python d2m_drive_reorg.py
"""

import os
import sys
import json
import logging
from datetime import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ── CONFIG ──────────────────────────────────────────────────────────────────

CLIENT_SECRET_FILE = "client_secret.json"   # path to your OAuth JSON
TOKEN_FILE         = "token_drive_reorg.json"
SCOPES             = ["https://www.googleapis.com/auth/drive"]

LOG_FILE = f"d2m_reorg_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# ── LOGGING ─────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ]
)
log = logging.getLogger("D2M_REORG")

# ── AUTH ─────────────────────────────────────────────────────────────────────

def get_drive_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
    return build("drive", "v3", credentials=creds)

# ── DRIVE HELPERS ────────────────────────────────────────────────────────────

def find_item(service, name, mime_type=None, parent_id=None):
    """Return the first matching item ID, or None."""
    q = f"name = '{name}' and trashed = false"
    if mime_type:
        q += f" and mimeType = '{mime_type}'"
    if parent_id:
        q += f" and '{parent_id}' in parents"
    result = service.files().list(q=q, fields="files(id,name,mimeType,parents)").execute()
    files = result.get("files", [])
    return files[0] if files else None


def find_all(service, name, mime_type=None):
    """Return all matching items (any parent)."""
    q = f"name = '{name}' and trashed = false"
    if mime_type:
        q += f" and mimeType = '{mime_type}'"
    result = service.files().list(q=q, fields="files(id,name,mimeType,parents)", pageSize=50).execute()
    return result.get("files", [])


def find_by_name_contains(service, fragment, mime_type=None):
    """Return all items whose name contains fragment."""
    q = f"name contains '{fragment}' and trashed = false"
    if mime_type:
        q += f" and mimeType = '{mime_type}'"
    result = service.files().list(q=q, fields="files(id,name,mimeType,parents)", pageSize=100).execute()
    return result.get("files", [])


def create_folder(service, name, parent_id=None):
    """Create a folder; return its ID. If it already exists under parent, return existing ID."""
    existing = find_item(service, name, mime_type="application/vnd.google-apps.folder", parent_id=parent_id)
    if existing:
        log.info(f"  FOLDER EXISTS  '{name}' (id={existing['id']}) — skipping create")
        return existing["id"]
    meta = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
    if parent_id:
        meta["parents"] = [parent_id]
    folder = service.files().create(body=meta, fields="id").execute()
    log.info(f"  CREATED FOLDER '{name}' (id={folder['id']})")
    return folder["id"]


def move_item(service, file_id, dest_folder_id, file_name="?"):
    """Move file_id into dest_folder_id. Safe mode: skip if name exists there."""
    # Check destination for same name
    file_meta = service.files().get(fileId=file_id, fields="name,parents").execute()
    name = file_meta.get("name", file_name)
    existing = find_item(service, name, parent_id=dest_folder_id)
    if existing and existing["id"] != file_id:
        log.warning(f"  SKIP (exists)  '{name}' already in destination — not moved")
        return False
    current_parents = ",".join(file_meta.get("parents", []))
    service.files().update(
        fileId=file_id,
        addParents=dest_folder_id,
        removeParents=current_parents,
        fields="id,parents"
    ).execute()
    log.info(f"  MOVED          '{name}' → folder id={dest_folder_id}")
    return True


def rename_item(service, file_id, new_name):
    service.files().update(fileId=file_id, body={"name": new_name}, fields="id,name").execute()
    log.info(f"  RENAMED        id={file_id} → '{new_name}'")


def list_children(service, folder_id):
    """Return all direct children of a folder."""
    q = f"'{folder_id}' in parents and trashed = false"
    result = service.files().list(q=q, fields="files(id,name,mimeType)", pageSize=200).execute()
    return result.get("files", [])


def merge_folders(service, source_id, dest_id, source_name):
    """Move all contents of source into dest, then log source as empty."""
    children = list_children(service, source_id)
    if not children:
        log.info(f"  MERGE          '{source_name}' is empty — nothing to merge")
        return
    for child in children:
        move_item(service, child["id"], dest_id, child["name"])
    log.info(f"  MERGE DONE     '{source_name}' contents moved into dest id={dest_id}")


# ── MAIN REORG ───────────────────────────────────────────────────────────────

def run_reorg(service):
    log.info("=" * 70)
    log.info("D2M GOOGLE DRIVE REORGANIZATION — START")
    log.info("=" * 70)

    # ── STEP 1: Create root D2M folder ──────────────────────────────────────
    log.info("\n[1/7] Creating root D2M folder structure...")
    root_id     = create_folder(service, "D2M — Dreams2Memories Travel")
    clients_id  = create_folder(service, "01 · CLIENTS",               parent_id=root_id)
    personal_id = create_folder(service, "02 · PERSONAL TRAVEL",       parent_id=root_id)
    research_id = create_folder(service, "03 · RESEARCH & REFERENCE",  parent_id=root_id)
    brand_id    = create_folder(service, "04 · BRAND & MARKETING",     parent_id=root_id)
    system_id   = create_folder(service, "05 · SYSTEM — EARA & THUNDERBIRD", parent_id=root_id)

    # ── STEP 2: CLIENT FOLDERS ───────────────────────────────────────────────
    log.info("\n[2/7] Setting up client folders...")

    # Sciacca — merge two duplicate folders
    sciacca_id = create_folder(service, "Sciacca — RSSC Explorer Dec 2025", parent_id=clients_id)
    for old_name in ["2512 Sciacca RSSC Explorer", "Sciacca 251225 RSSC Explorer"]:
        items = find_all(service, old_name, mime_type="application/vnd.google-apps.folder")
        for item in items:
            merge_folders(service, item["id"], sciacca_id, old_name)
            move_item(service, item["id"], sciacca_id, old_name)

    # Furrow-Nichols — rename and move
    furrow_dest_id = create_folder(service, "Furrow-Nichols-Darrow & Ely — RSSC Grandeur Aug 2026", parent_id=clients_id)
    furrow = find_item(service, "260829 RSSC Grandeur Furrow-Nichols-Darrow/Ely",
                       mime_type="application/vnd.google-apps.folder")
    if furrow:
        merge_folders(service, furrow["id"], furrow_dest_id, furrow["name"])
    else:
        log.warning("  NOT FOUND      '260829 RSSC Grandeur Furrow-Nichols-Darrow/Ely'")

    # Erik McLeod
    erik = find_item(service, "Erik McLeod and Melissa McGlasson Italy 2026",
                     mime_type="application/vnd.google-apps.folder")
    if erik:
        rename_item(service, erik["id"], "Erik McLeod & Melissa McGlasson — Italy 2026")
        move_item(service, erik["id"], clients_id, "Erik McLeod & Melissa McGlasson — Italy 2026")
    else:
        log.warning("  NOT FOUND      'Erik McLeod and Melissa McGlasson Italy 2026'")

    # Felda Looper
    felda = find_item(service, "Felda Looper-Mark Beesley Maldives Jan 2027 (Feb)",
                      mime_type="application/vnd.google-apps.folder")
    if felda:
        rename_item(service, felda["id"], "Felda Looper & Mark Beesley — Maldives 2027")
        move_item(service, felda["id"], clients_id, "Felda Looper & Mark Beesley — Maldives 2027")
    else:
        log.warning("  NOT FOUND      'Felda Looper-Mark Beesley Maldives Jan 2027 (Feb)'")

    # Create 7-subfolder template inside each client folder
    log.info("\n  Creating standard 7-subfolder template in each client folder...")
    client_subfolders = [
        "01 · Proposals & Quotes",
        "02 · Bookings & Confirmations",
        "03 · Itineraries & Documents",
        "04 · Correspondence",
        "05 · Research & Intel",
        "06 · Photos & Media",
        "07 · Post-Trip",
    ]
    for cid in [sciacca_id, furrow_dest_id]:
        for sf in client_subfolders:
            create_folder(service, sf, parent_id=cid)

    # Erik and Felda folders — fetch their new IDs
    erik_new  = find_item(service, "Erik McLeod & Melissa McGlasson — Italy 2026",
                          mime_type="application/vnd.google-apps.folder", parent_id=clients_id)
    felda_new = find_item(service, "Felda Looper & Mark Beesley — Maldives 2027",
                          mime_type="application/vnd.google-apps.folder", parent_id=clients_id)
    for cid in [x["id"] for x in [erik_new, felda_new] if x]:
        for sf in client_subfolders:
            create_folder(service, sf, parent_id=cid)

    # ── STEP 3: PERSONAL TRAVEL ──────────────────────────────────────────────
    log.info("\n[3/7] Setting up personal travel folders...")

    med_cruise_id = create_folder(service, "2025-04 RSSC Grandeur Mediterranean Cruise", parent_id=personal_id)
    vimeo_id      = create_folder(service, "Vimeo Uploads", parent_id=med_cruise_id)

    # All dated port/day folders
    med_folders = [
        "250330 DEN-BCN", "250401 BCN", "250402 RSSC Grandeur Videos-Pics",
        "250403 Cooking Class", "250404 Malta", "250405 Cephalonia",
        "250406 Buffet at Sea", "250407 & 8 Egypt Photos-Videos April 2025",
        "250409 Limasol", "250411 Heraklion", "250412 Santorini",
        "250413 Kusadasi", "250414 Pergamon", "250415 Istanbul",
        "250430 RSSC Grandeur pre-cruise and cruise vlogs",
        "Egypt photos April 2025",
    ]
    for fname in med_folders:
        item = find_item(service, fname, mime_type="application/vnd.google-apps.folder")
        if item:
            move_item(service, item["id"], med_cruise_id, fname)
        else:
            # Try partial match
            results = find_by_name_contains(service, fname[:15], mime_type="application/vnd.google-apps.folder")
            if results:
                move_item(service, results[0]["id"], med_cruise_id, results[0]["name"])
            else:
                log.warning(f"  NOT FOUND      '{fname}'")

    # Vimeo folders — merge all into Vimeo Uploads
    vimeo_names = [
        "Vimeo uploads", "For Vimeo", "For Vimeo- Kusadasi",
        "For Vimeo-Limasol", "To upload",
    ]
    for vname in vimeo_names:
        items = find_all(service, vname, mime_type="application/vnd.google-apps.folder")
        for item in items:
            merge_folders(service, item["id"], vimeo_id, vname)

    # Unlabeled "For Vimeo" duplicates (multiple with same name)
    for item in find_by_name_contains(service, "For Vimeo", mime_type="application/vnd.google-apps.folder"):
        if item["id"] != vimeo_id:
            merge_folders(service, item["id"], vimeo_id, item["name"])

    # Loucks-Lyons Paris trip
    paris = find_item(service, "Loucks-Lyons Oct 2025 Paris-Switz",
                      mime_type="application/vnd.google-apps.folder")
    if paris:
        rename_item(service, paris["id"], "2025-10 Loucks-Lyons Paris & Switzerland")
        move_item(service, paris["id"], personal_id, "2025-10 Loucks-Lyons Paris & Switzerland")
    else:
        log.warning("  NOT FOUND      'Loucks-Lyons Oct 2025 Paris-Switz'")

    # National Parks
    parks = find_item(service, "2026 National Parks Trip",
                      mime_type="application/vnd.google-apps.folder")
    if parks:
        move_item(service, parks["id"], personal_id, "2026 National Parks Trip")
    else:
        log.warning("  NOT FOUND      '2026 National Parks Trip'")

    # ── STEP 4: RESEARCH & REFERENCE ─────────────────────────────────────────
    log.info("\n[4/7] Moving research & reference folders...")

    regent = find_item(service, "Regent E-Brochures",
                       mime_type="application/vnd.google-apps.folder")
    if regent:
        move_item(service, regent["id"], research_id, "Regent E-Brochures")
    else:
        log.warning("  NOT FOUND      'Regent E-Brochures'")

    # ── STEP 5: BRAND & MARKETING — archive LGT era ──────────────────────────
    log.info("\n[5/7] Archiving old LGT branding folders...")

    archive_id = create_folder(service, "Archive — LGT Era", parent_id=brand_id)
    lgt_folders = [
        "JL3 Love Group Travel Website",
        "LGT Website",
        "Luxury Travel Web Site and Partnership",
    ]
    for fname in lgt_folders:
        item = find_item(service, fname, mime_type="application/vnd.google-apps.folder")
        if item:
            move_item(service, item["id"], archive_id, fname)
        else:
            log.warning(f"  NOT FOUND      '{fname}'")

    # ── STEP 6: LOOSE FILES AT ROOT ──────────────────────────────────────────
    log.info("\n[6/7] Homing loose files from root...")

    # Business Analysis Report → LGT archive
    biz = find_item(service, "Business Analysis Report")
    if biz:
        move_item(service, biz["id"], archive_id, "Business Analysis Report")
    else:
        log.warning("  NOT FOUND      'Business Analysis Report'")

    # Elena dispute doc → Sciacca Post-Trip
    sciacca_posttip_id = find_item(service, "07 · Post-Trip",
                                   mime_type="application/vnd.google-apps.folder",
                                   parent_id=sciacca_id)
    elena_doc = find_item(service, "SUMMARY OF PERSONALIZED SERVICES ISSUES and MISSED RISK MITIGATION OPPORTUNITIES")
    if elena_doc and sciacca_posttip_id:
        move_item(service, elena_doc["id"], sciacca_posttip_id["id"], "Elena dispute doc")
    else:
        log.warning("  NOT FOUND or no dest  'Elena dispute doc'")

    # National Parks driving tour doc → National Parks folder
    parks_folder = find_item(service, "2026 National Parks Trip",
                             mime_type="application/vnd.google-apps.folder",
                             parent_id=personal_id)
    parks_doc = find_item(service, "14-Day Driving Tour: Glacier, Yellowstone & Grand Teton National Parks from Claude Presents")
    if parks_doc and parks_folder:
        move_item(service, parks_doc["id"], parks_folder["id"], "National Parks driving tour doc")
    else:
        log.warning("  NOT FOUND or no dest  'National Parks driving tour doc'")

    # Felda Maldives itinerary + research → Felda client folders
    felda_new2 = find_item(service, "Felda Looper & Mark Beesley — Maldives 2027",
                           mime_type="application/vnd.google-apps.folder",
                           parent_id=clients_id)
    if felda_new2:
        felda_proposals_id = find_item(service, "01 · Proposals & Quotes",
                                       mime_type="application/vnd.google-apps.folder",
                                       parent_id=felda_new2["id"])
        felda_research_id  = find_item(service, "05 · Research & Intel",
                                       mime_type="application/vnd.google-apps.folder",
                                       parent_id=felda_new2["id"])

        maldives_itin = find_item(service, "Overview:  7-day itinerary ")
        if maldives_itin and felda_proposals_id:
            move_item(service, maldives_itin["id"], felda_proposals_id["id"], "Maldives 7-day itinerary")

    # ── STEP 7: SYSTEM FOLDER NOTE ───────────────────────────────────────────
    log.info("\n[7/7] System folder — EARA D2M Thunderbird v2 stays in place (locked).")
    log.info("  Folder 05 · SYSTEM — EARA & THUNDERBIRD created as reference only.")
    log.info("  Do NOT move the spreadsheet — its file ID is hardcoded in your pipeline.")

    # ── DONE ─────────────────────────────────────────────────────────────────
    log.info("\n" + "=" * 70)
    log.info("D2M REORG COMPLETE")
    log.info(f"Log saved to: {LOG_FILE}")
    log.info("=" * 70)
    log.info("\nRoot structure created:")
    log.info(f"  D2M — Dreams2Memories Travel  (id={root_id})")
    log.info(f"    01 · CLIENTS                (id={clients_id})")
    log.info(f"    02 · PERSONAL TRAVEL        (id={personal_id})")
    log.info(f"    03 · RESEARCH & REFERENCE   (id={research_id})")
    log.info(f"    04 · BRAND & MARKETING      (id={brand_id})")
    log.info(f"    05 · SYSTEM — EARA...       (id={system_id})")


# ── ENTRY POINT ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not os.path.exists(CLIENT_SECRET_FILE):
        print(f"\n❌  '{CLIENT_SECRET_FILE}' not found in current directory.")
        print("    Place your OAuth client_secret.json here and re-run.\n")
        sys.exit(1)

    try:
        service = get_drive_service()
        log.info("✅  Authenticated as johnloucks3@gmail.com")
        run_reorg(service)
    except HttpError as e:
        log.error(f"Google API error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        log.warning("Interrupted by user.")
        sys.exit(0)
