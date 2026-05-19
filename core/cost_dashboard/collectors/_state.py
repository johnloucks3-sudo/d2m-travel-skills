import json
import os

STATE_FILE = os.path.expanduser("~/Thunderbird/storage/.collector_state.json")

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"claude": {}, "openrouter": {"last_id": None}}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)
