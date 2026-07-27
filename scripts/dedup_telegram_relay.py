#!/usr/bin/env python3
"""
Deduplicate Telegram C2 Relay Queue to prevent duplicate alert spam.
"""
import json
import os

def main():
    queue_path = "/home/john/Thunderbird/OpsCenter/relay_queue.jsonl"
    if not os.path.exists(queue_path):
        print("Relay queue path does not exist.")
        return

    seen_ids = set()
    unique_msgs = []
    
    with open(queue_path, "r") as f:
        for line in f:
            line_str = line.strip()
            if not line_str:
                continue
            try:
                data = json.loads(line_str)
                msg_id = data.get("id")
                if msg_id and msg_id not in seen_ids:
                    seen_ids.add(msg_id)
                    unique_msgs.append(line_str)
            except Exception:
                unique_msgs.append(line_str)

    with open(queue_path, "w") as f:
        for item in unique_msgs:
            f.write(item + "\n")

    print(f"Relay queue deduplicated. Preserved {len(unique_msgs)} unique items.")

if __name__ == "__main__":
    main()
