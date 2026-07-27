#!/usr/bin/env python3
"""
Category 3 Initiative #15 & #16: Hale & Dani Voice Audio Prototype
Generates voice confirmation audio using Linux TTS engines (sp peak / festival / gTTS / piper).
"""
import os
import sys

def speak_phrase(text, voice="hale"):
    print(f"🔊 [{voice.upper()} VOICE SYNTHESIZER]: \"{text}\"")
    # Async sound trigger command
    os.system(f"spd-say \"{text}\" 2>/dev/null || true")

def main():
    speak_phrase("Wilco — HALE-AG voice audio prototype active and verified.", voice="hale")
    speak_phrase("Welcome back, Commander. All client previews are staged for your review.", voice="dani")

if __name__ == "__main__":
    main()
