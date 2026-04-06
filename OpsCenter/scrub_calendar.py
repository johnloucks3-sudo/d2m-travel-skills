#!/usr/bin/env python3
import os
import subprocess
import logging

logging.basicConfig(filename='/home/john/Thunderbird/OpsCenter/overwatch.log', level=logging.INFO, format='%(asctime)s - [CALENDAR SCRUB] - %(message)s')

def scrub_calendar():
    targets = ["D2M", "VALIDATION", "SUSPENSE"]
    
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
            if result.stderr:
                logging.error(f"Scrub Error for {target}:\n{result.stderr}")
        except Exception as e:
            logging.error(f"Failed to execute scrub for {target}: {e}")

if __name__ == "__main__":
    scrub_calendar()

