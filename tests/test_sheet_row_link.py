import unittest
from datetime import datetime, timezone, timedelta
import sys
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
sys.path.insert(0, str(ROOT))

from tcd.permalink import sheet_row_link

class TestSheetRowLink(unittest.TestCase):
    def test_sheet_row_link(self):
        # Setup fake config
        now = datetime.now(timezone.utc)
        fresh_sync = now.isoformat()
        stale_sync = (now - timedelta(minutes=25)).isoformat()
        
        cfg = {
            "spreadsheet_url": "https://docs.google.com/spreadsheets/d/fake/edit",
            "spreadsheet_gid": 758571255,
            "last_sync_at": fresh_sync,
            "item_rows": {
                "known-id-1": 42
            }
        }
        
        # Case (a): known id + fresh sync -> correct URL containing the real gid and right range
        url = sheet_row_link("known-id-1", cfg=cfg)
        self.assertEqual(url, "https://docs.google.com/spreadsheets/d/fake/edit#gid=758571255&range=A42")
        
        # Case (b): unknown id -> ''
        self.assertEqual(sheet_row_link("unknown-id", cfg=cfg), "")
        
        # Case (c): last_sync_at older than 20 min -> ''
        stale_cfg = cfg.copy()
        stale_cfg["last_sync_at"] = stale_sync
        self.assertEqual(sheet_row_link("known-id-1", cfg=stale_cfg), "")
        
        # Case (d): missing/empty config -> '' and no exception
        self.assertEqual(sheet_row_link("known-id-1", cfg={}), "")
        
if __name__ == "__main__":
    unittest.main()
