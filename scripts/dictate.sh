#!/usr/bin/env bash
# dictate.sh — Hold to record, release to transcribe, result goes to clipboard
# Assign to a keyboard shortcut in KDE System Settings > Shortcuts > Custom Shortcuts
# Paste result: Ctrl+V anywhere

DURATION="${1:-5}"   # seconds to record (default 5)
TMP_WAV="/tmp/dictate_input.wav"
MODEL="$HOME/.local/share/vosk/vosk-model-small-en-us-0.15"
NOTIFY="notify-send -a Dictation -t 3000"

cleanup() { rm -f "$TMP_WAV"; }
trap cleanup EXIT

# Visual cue: recording started
$NOTIFY "🎙️ Recording..." "Speak now (${DURATION}s)" &

# Record from default source (Laptop_DMIC)
rec -q -r 16000 -c 1 "$TMP_WAV" trim 0 "$DURATION" 2>/dev/null

$NOTIFY "⚙️ Transcribing..." ""

# Transcribe with Vosk
TEXT=$(python3 - <<'PYEOF'
import sys, json, wave
import vosk

model = vosk.Model("/home/john/.local/share/vosk/vosk-model-small-en-us-0.15")
wf = wave.open("/tmp/dictate_input.wav", "rb")
rec = vosk.KaldiRecognizer(model, wf.getframerate())
rec.SetWords(False)

results = []
while True:
    data = wf.readframes(4000)
    if not data:
        break
    if rec.AcceptWaveform(data):
        r = json.loads(rec.Result())
        if r.get("text"):
            results.append(r["text"])

final = json.loads(rec.FinalResult())
if final.get("text"):
    results.append(final["text"])

print(" ".join(results).strip())
PYEOF
)

if [[ -n "$TEXT" ]]; then
    echo -n "$TEXT" | xclip -selection clipboard
    $NOTIFY "✅ Copied to clipboard" "$TEXT"
else
    $NOTIFY "⚠️ No speech detected" "Try again"
fi
