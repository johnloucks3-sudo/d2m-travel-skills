#!/usr/bin/env python3
import os
import subprocess
import logging

logging.basicConfig(filename='/home/john/Thunderbird/OpsCenter/overwatch.log', level=logging.INFO, format='%(asctime)s - [CALENDAR SCRUB 2.0] - %(message)s')

def scrub_calendar():
    # The Commander specifically noted "Anchor Dates" might be missing. 
    # Let's expand the search vectors to catch any variations in naming conventions.
    targets = ["Anchor", "D2M Anchor", "[EARA]", "Validation", "Suspense", "D2M"]
    
    for target in targets:
        logging.info(f"Initiating aggressive Calendar Scrub for keyword: {target}")
        
        cmd = [
            "/home/john/Thunderbird/.venv/bin/python3",
            "/home/john/Thunderbird/delete_calendar_events.py",
            target,
            "--yes"
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            logging.info(f"Scrub Result for '{target}':\n{result.stdout}")
        except Exception as e:
            logging.error(f"Failed to execute scrub for '{target}': {e}")

if __name__ == "__main__":
    scrub_calendar()

