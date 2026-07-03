#!/usr/bin/env python3
"""
dictate_hotkey.py — Global hotkey daemon for dictation
Listens for Meta+D, records 5s, transcribes via Vosk, copies to clipboard.
Run: python3 dictate_hotkey.py  (leave running in background)
"""
import subprocess, threading, os
from pynput import keyboard

SCRIPT = os.path.expanduser("~/Thunderbird/scripts/dictate.sh")
HOTKEY = {keyboard.Key.cmd, keyboard.KeyCode.from_char('d')}
pressed = set()
running = False

def run_dictation():
    global running
    if running:
        return
    running = True
    try:
        subprocess.Popen(["bash", SCRIPT], start_new_session=True)
    finally:
        running = False

def on_press(key):
    pressed.add(key)
    if HOTKEY.issubset(pressed):
        threading.Thread(target=run_dictation, daemon=True).start()

def on_release(key):
    pressed.discard(key)

print("🎙️ Dictation hotkey active — press Meta+D to dictate")
print("   Ctrl+C to stop")

with keyboard.Listener(on_press=on_press, on_release=on_release) as l:
    l.join()
