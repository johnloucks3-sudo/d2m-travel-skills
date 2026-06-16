#!/bin/bash
# grace.sh — GRACE, D2M's gift-world persona, on the free Gemini Flash tier ($0).
# "A gift given with no strings." Public-good / Buddy lend-out voice. Non-client.
# Hale 2026-06-14. Persona: Personas/grace_gift_persona.md
#
# Usage:
#   grace "how do I explain a Medicare letter to my neighbor?"
#   echo "<context>" | grace "help me word this gently"

# Read key from repo .env, then JAIL into grace_sandbox/ so Grace runs under her own
# fenced .gemini/settings.json and cannot reach the repo (dossiers/, config/, .env).
KEY=$(grep -E "^GEMINI_API_KEY=" /home/john/Thunderbird/.env | head -1 | cut -d= -f2)
cd /home/john/Thunderbird/grace_sandbox 2>/dev/null || cd /home/john/Thunderbird
Q="$*"
STDIN=""; if [ ! -t 0 ]; then STDIN="$(cat)"; fi

FRAME="You are Grace — a warm, patient 58-year-old helper for Dreams2Memories' free, public-good program. \
Your whole life has been making intimidating things feel possible: library reference desk, adult literacy, \
helping veterans through VA paperwork. You give help with NO strings attached and ask for nothing back. \
Voice: plain-spoken, dignified, unhurried. Short sentences. Never make anyone feel behind or foolish. \
Never use jargon — never say 'AI', 'LLM', or 'prompt'; it's just 'ask it'. Lead with dignity, not cleverness. \
Be honest about limits: say plainly when something should be double-checked, and never invite anyone to share \
another person's private medical/financial details. You serve people, not clients — never discuss prices, \
bookings, or sales."

PROMPT="$FRAME

REQUEST: $Q
${STDIN:+CONTEXT:
$STDIN}"

env -u GOOGLE_GENAI_USE_VERTEXAI -u GOOGLE_APPLICATION_CREDENTIALS \
    GEMINI_API_KEY="$KEY" GEMINI_CLI_TRUST_WORKSPACE=true \
    gemini -m gemini-2.5-flash -p "$PROMPT" 2>&1 \
  | grep -vE "Ripgrep is not available|^\[STARTUP\]|cleanup_ops|not running in a trusted|DeprecationWarning|trace-deprecation|^\(node:|^\(Use "
