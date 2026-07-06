#!/usr/bin/env python3
"""
D2M Thunderbird Tasking Watcher — Simple Working Version
========================================================
Minimal implementation that watches key files and avoids crashes.
"""

import os
import sys
import time
import logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [TASK WATCHER SIMPLE] - %(message)s",
)

# Paths
BASE = Path("/home/john/Thunderbird")
CLAUDE_INBOX = BASE / "claude_inbox.md"
OPENCODE_INBOX = BASE / "OpsCenter/collaboration/opencode_inbox.md"
ACTIVITY_BOARD = BASE / "OpsCenter/collaboration/activity_board.md"


class FileChangeHandler(FileSystemEventHandler):
    """Handle file changes"""

    def on_modified(self, event):
        if event.is_directory:
            return

        file_path = event.src_path
        logging.info(f"File modified: {file_path}")

        # Check which file was modified
        if file_path.endswith("claude_inbox.md"):
            self.handle_claude_inbox()
        elif file_path.endswith("opencode_inbox.md"):
            self.handle_opencode_inbox()
        elif file_path.endswith("activity_board.md"):
            self.handle_activity_board()

    def handle_claude_inbox(self):
        """Handle changes to Claude inbox"""
        try:
            with open(CLAUDE_INBOX, "r") as f:
                content = f.read()
                # Check for UNREAD tasks
                if "status: UNREAD" in content:
                    logging.info("New UNREAD task in claude_inbox.md")
                    # Telegram notification is handled by gateway service
        except Exception as e:
            logging.error(f"Error reading claude_inbox: {e}")

    def handle_opencode_inbox(self):
        """Handle changes to OpenCode inbox"""
        try:
            with open(OPENCODE_INBOX, "r") as f:
                content = f.read()
                # Check for new tasks
                if "status: UNREAD" in content or "NEXUS:" in content:
                    logging.info("New task in opencode_inbox.md")
        except Exception as e:
            logging.error(f"Error reading opencode_inbox: {e}")

    def handle_activity_board(self):
        """Handle activity board changes"""
        try:
            logging.info("Activity board updated")
        except Exception as e:
            logging.error(f"Error with activity board: {e}")


def main():
    """Main watcher loop"""
    logging.info("Thunderbird Task Watcher (Simple) starting...")

    # Check required files exist
    for path in [CLAUDE_INBOX, OPENCODE_INBOX, ACTIVITY_BOARD]:
        if not path.exists():
            logging.warning(f"Required file not found: {path}")
            path.touch()
            logging.info(f"Created empty file: {path}")

    # Set up file watcher
    observer = Observer()
    event_handler = FileChangeHandler()

    # Watch directories containing the files
    watch_dirs = {
        os.path.dirname(str(CLAUDE_INBOX)),  # ~/Thunderbird/
        os.path.dirname(str(OPENCODE_INBOX)),  # ~/Thunderbird/OpsCenter/collaboration/
        os.path.dirname(str(ACTIVITY_BOARD)),  # same as opencode dir
    }

    for d in watch_dirs:
        if os.path.exists(d):
            observer.schedule(event_handler, d, recursive=False)
            logging.info(f"Watching directory: {d}")
        else:
            logging.warning(f"Watch directory not found: {d}")

    # Start observer
    observer.start()
    logging.info("Watcher running. Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(30)  # Check every 30 seconds for any cleanup
    except KeyboardInterrupt:
        logging.info("Watcher shutting down (Ctrl+C).")
    except Exception as e:
        logging.error(f"Watcher error: {e}")
    finally:
        observer.stop()
        observer.join()
        logging.info("Watcher stopped.")


if __name__ == "__main__":
    main()
