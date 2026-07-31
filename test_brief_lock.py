import sys
import threading
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

# Mock external modules that cause import errors
sys.modules['thunderbird_world_intel'] = MagicMock()
sys.modules['thunderbird_temporal_memory'] = MagicMock()
sys.modules['thunderbird_anchor_dates'] = MagicMock()
sys.modules['thunderbird_reconciliation'] = MagicMock()

# Import the module
sys.path.insert(0, str(Path('/home/john/Thunderbird/agents')))
import thunderbird_morning_briefing

send_count = 0
temp_dir = tempfile.mkdtemp()
temp_path = Path(temp_dir) / f"morning_brief_sent_{datetime.now().strftime('%Y%m%d')}.lock"

def mock_lock_path():
    return temp_path

def mock_send_email(*args, **kwargs):
    global send_count
    send_count += 1
    time.sleep(1)

@patch("thunderbird_morning_briefing._morning_brief_lock_path", side_effect=mock_lock_path)
@patch("thunderbird_morning_briefing.send_briefing_email", side_effect=mock_send_email)
@patch("thunderbird_morning_briefing.send_briefing_json", MagicMock())
@patch("thunderbird_morning_briefing._get_sheets_client", MagicMock())
@patch("thunderbird_morning_briefing.fetch_commander_log", MagicMock(return_value=[]))
@patch("thunderbird_morning_briefing.fetch_intel_log", MagicMock(return_value=[]))
@patch("thunderbird_morning_briefing.fetch_pricing_tracker", MagicMock(return_value=[]))
@patch("thunderbird_morning_briefing.fetch_tech_news", MagicMock(return_value=[]))
@patch("thunderbird_morning_briefing.fetch_fare_log", MagicMock(return_value=[]))
@patch("thunderbird_morning_briefing.fetch_completed_actions", MagicMock(return_value=set()))
@patch("thunderbird_morning_briefing.build_executive_summary", MagicMock(return_value={"alert_level": "GREEN", "alert_text": "Test"}))
@patch("thunderbird_morning_briefing.render_briefing_html", MagicMock(return_value="<html></html>"))
@patch("thunderbird_morning_briefing.fetch_heartbeat_findings", MagicMock(return_value={}))
@patch("thunderbird_morning_briefing.fetch_overnight_outputs", MagicMock(return_value=[]))
@patch("thunderbird_morning_briefing.fetch_system_status", MagicMock(return_value={}))
def test_concurrent_briefing(*args):
    results = []

    def worker():
        try:
            res = thunderbird_morning_briefing.run_briefing(preview=False, force=False)
            results.append(res)
        except Exception as e:
            results.append(f"Error: {e}")

    # Create two threads
    t1 = threading.Thread(target=worker)
    t2 = threading.Thread(target=worker)

    t1.start()
    t2.start()

    t1.join()
    t2.join()
    
    print(f"Total sends: {send_count}")
    print(f"Results: {results}")

if __name__ == "__main__":
    test_concurrent_briefing()
