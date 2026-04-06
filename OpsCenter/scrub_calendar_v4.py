#!/usr/bin/env python3
import os
import subprocess
import logging

logging.basicConfig(filename='/home/john/Thunderbird/OpsCenter/overwatch.log', level=logging.INFO, format='%(asctime)s - [CALENDAR SCRUB V4] - %(message)s')

def scrub_calendar():
    # The Commander explicitly named these client groups. They likely have lingering automated touchpoint events.
    targets = ["Furlow", "Nichols", "Ely", "McLeod", "Kuklinski", "Morton"]
    
    for target in targets:
        logging.info(f"Initiating Calendar Scrub for keyword: {target}")
        
        cmd = [
            "/home/john/Thunderbird/.venv/bin/python3",
            "/home/john/Thunderbird/delete_calendar_events.py",
            target,
            "--yes"
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            logging.info(f"Scrub Result for {target}:\n{result.stdout}")
        except Exception as e:
            logging.error(f"Failed to execute scrub for {target}: {e}")

if __name__ == "__main__":
    scrub_calendar()

