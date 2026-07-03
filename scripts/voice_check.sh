#!/usr/bin/env bash
# voice_check.sh — Verify and restore yoga's mic for Claude Code /voice
# Usage: voice-check [check|test|restore]

MIC_SOURCE="alsa_input.pci-0000_05_00.6.pro-input-0"
TMP="/tmp/voice_check.wav"

restore() {
    amixer -c 1 sset Capture 80% cap >/dev/null 2>&1
    amixer -c 1 sset 'Mic Boost' 1 >/dev/null 2>&1
    echo "✅ ALSA capture: 80%, +10dB boost, switch ON"
}

check() {
    local sw
    sw=$(amixer -c 1 sget Capture 2>/dev/null | grep -oP '\[(on|off)\]' | head -1)
    echo "Default source : $(pactl get-default-source)"
    echo "PW mute        : $(pactl get-source-mute $MIC_SOURCE | awk '{print $2}')"
    echo "PW volume      : $(pactl get-source-volume $MIC_SOURCE | grep -oP '\d+(?=%)' | head -1)%"
    echo "ALSA capture   : $sw"
    [[ "$sw" == "[off]" ]] && echo "⚠️  ALSA capture switch is OFF — run: voice-check restore"
}

test_capture() {
    echo "Recording 2s... speak now"
    rec -q -r 16000 -c 1 "$TMP" trim 0 2 2>/dev/null
    local rms max
    rms=$(sox "$TMP" -n stat 2>&1 | grep "RMS.*amplitude" | awk '{print $3}')
    max=$(sox "$TMP" -n stat 2>&1 | grep "Maximum amplitude" | awk '{print $3}')
    echo "RMS: $rms  Max: $max"
    [[ $(echo "$max > 0.0001" | bc -l 2>/dev/null) == "1" ]] && \
        echo "✅ Signal detected — mic working" || \
        echo "⚠️  Near-silent — check mic or speak louder"
    play -q "$TMP" 2>/dev/null && echo "(played back)"
}

case "${1:-check}" in
    restore) restore ;;
    test)    check; restore; test_capture ;;
    check)   check ;;
    *)       check ;;
esac
