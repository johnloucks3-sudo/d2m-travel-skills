import sys
from . import _imports

def collect_multi_tab() -> list:
    try:
        gauth = _imports.load_google_auth()
        sheets = gauth.get_sheets()
    except Exception as e:
        print(f"tcd.multi_tab: google auth unavailable: {e}", file=sys.stderr)
        return []
        
    sheet_id = "1L7WWppZ7LB9Is5EUBp9zu6FThPghcyuGuB4IEQtYsUQ"
    
    tcd_data = _imports.load_tcd_data()
    state = tcd_data._load_json(tcd_data.HALE_STATE, {})
    existing_missions = tcd_data.build_missions(state)
    existing_mission_ids = {m["id"] for m in existing_missions}
    
    try:
        res = sheets.spreadsheets().values().batchGet(
            spreadsheetId=sheet_id,
            ranges=["CommanderReview", "Missions", "ELON 77", "TechScans", "Next7"]
        ).execute()
        value_ranges = res.get("valueRanges", [])
    except Exception as e:
        print(f"tcd.multi_tab: sheets fetch failed: {e}", file=sys.stderr)
        return []

    def parse_sheet(vr):
        values = vr.get("values", [])
        if not values: return []
        header = values[0]
        rows = []
        for raw in values[1:]:
            # Ensure raw is padded to length of header
            raw_padded = raw + [""] * (len(header) - len(raw))
            row = dict(zip(header, raw_padded))
            rows.append(row)
        return rows
        
    tabs = {vr["range"].split("!")[0].strip("'"): parse_sheet(vr) for vr in value_ranges}
    
    items = []
    
    # 1. CommanderReview
    cr_mission_ids = set()
    cr_count = 0
    cr_dropped = 0
    for row in tabs.get("CommanderReview", []):
        mid = row.get("Mission ID", "")
        if not mid: continue
        cr_count += 1
        item_id = f"mission-{mid}"
        if item_id in existing_mission_ids:
            cr_dropped += 1
            continue
        
        cr_mission_ids.add(item_id)
        if row.get("Status", "").lower() in ("active", "pending_review"):
            items.append({
                "id": item_id,
                "inbox": "strategic", "folder": "s-clientstrat", "type": "decision",
                "stage": "P",
                "priority": row.get("Priority", "routine").lower(),
                "title": row.get("Title", ""),
                "from": row.get("Assigned To", ""),
                "date": "",
                "snippet": row.get("Description", "")[:220],
                "body": row.get("Description", ""),
                "link": row.get("Link", ""),
                "status": row.get("Status", ""),
                "recommendation": row.get("CMDR ACTION", ""),
            })

    # 2. Missions
    m_mission_ids = set()
    m_count = 0
    m_dropped_cr = 0
    m_dropped_existing = 0
    for row in tabs.get("Missions", []):
        mid = row.get("Mission ID", "")
        if not mid: continue
        m_count += 1
        item_id = f"mission-{mid}"
        if item_id in cr_mission_ids:
            m_dropped_cr += 1
            continue
        if item_id in existing_mission_ids:
            m_dropped_existing += 1
            continue
            
        m_mission_ids.add(item_id)
        if row.get("Status", "").lower() in ("active", "pending_review"):
            items.append({
                "id": item_id,
                "inbox": "strategic", "folder": "s-clientstrat", "type": "decision",
                "stage": "P",
                "priority": row.get("Priority", "routine").lower(),
                "title": row.get("Title", ""),
                "from": row.get("Assigned To", ""),
                "date": row.get("updated_at", ""),
                "snippet": row.get("Description", "")[:220],
                "body": row.get("Description", ""),
                "link": row.get("Link", ""),
                "status": row.get("Status", ""),
                "recommendation": row.get("CMDR ACTION", ""),
            })

    # 3. ELON 77
    e_count = 0
    e_dropped = 0
    for row in tabs.get("ELON 77", []):
        mid = row.get("Mission ID", "")
        if not mid: continue
        e_count += 1
        item_id = f"mission-{mid}"
        if item_id in cr_mission_ids or item_id in m_mission_ids or item_id in existing_mission_ids:
            e_dropped += 1
            continue
            
        if row.get("Status", "").lower() in ("active", "pending_review"):
            items.append({
                "id": item_id,
                "inbox": "strategic", "folder": "s-elon", "type": "decision",
                "stage": "P",
                "priority": row.get("Priority", "routine").lower(),
                "title": row.get("Title", ""),
                "from": row.get("Assigned To", ""),
                "date": row.get("Created", ""),
                "snippet": row.get("REMARKS", "")[:220],
                "body": row.get("REMARKS", ""),
                "link": "",
                "status": row.get("Status", ""),
                "recommendation": row.get("CMDR ACTION", ""),
            })

    # TechScans / Next7
    for tab_name, prefix in [("TechScans", "techscan"), ("Next7", "next7")]:
        for row in tabs.get(tab_name, []):
            if row.get("CMDR ACTION") == "SEE REMARKS":
                continue
            item_id = f"{prefix}-{row.get('id', '')}"
            items.append({
                "id": item_id,
                "inbox": row.get("inbox", "strategic"),
                "folder": row.get("folder", "s-inbox"),
                "type": row.get("type", "decision"),
                "stage": row.get("stage") or "P",
                "priority": row.get("priority", "routine"),
                "title": row.get("title", ""),
                "from": row.get("from", ""),
                "date": row.get("date", ""),
                "snippet": row.get("snippet", ""),
                "body": row.get("body", ""),
                "link": row.get("link", ""),
                "status": row.get("status", ""),
                "recommendation": row.get("CMDR ACTION", ""),
            })
            
    print(f"AG Dedup stats: CommanderReview={cr_count} (dropped {cr_dropped} via Items), Missions={m_count} (dropped {m_dropped_cr} via CR, {m_dropped_existing} via Items), ELON 77={e_count} (dropped {e_dropped} via CR/Missions/Items)", file=sys.stderr)

    return items
