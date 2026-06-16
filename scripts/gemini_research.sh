#!/bin/bash
# gemini_research.sh — first-pass RESEARCH lane on the free Gemini Flash tier ($0, 1,500/day).
# For Reyes (A8 experience layer) + Dembe (A2 intel). Hale 2026-06-14.
#
# This is a DRAFT/SCAFFOLD tool, NOT a client-copy tool. Output is raw research the domain
# owner shapes. Per SO-PIPELINE-INTEGRITY: tag every claim CONFIRMED / INFERRED / UNKNOWN.
# Nothing from here reaches a client without the creative chain + primary-source verification.
#
# Usage:
#   gemini_research.sh reyes "shore excursion options in Santorini for limited-mobility guests"
#   gemini_research.sh dembe "Panama Canal cruise port intel Dec 2026, weather + tendering"
#   echo "<context>" | gemini_research.sh reyes "accessibility notes for these ports"

cd /home/john/Thunderbird 2>/dev/null
KEY=$(grep -E "^GEMINI_API_KEY=" /home/john/Thunderbird/.env | head -1 | cut -d= -f2)
ROLE="${1:-reyes}"; shift
QUERY="$*"
STDIN=""; if [ ! -t 0 ]; then STDIN="$(cat)"; fi

case "$ROLE" in
  reyes) FRAME="You are a travel experience researcher producing FIRST-PASS scaffolding for a luxury travel advisor. Focus: excursions, dining, accessibility/mobility, port-readiness, upsell flags. Be specific and practical." ;;
  dembe) FRAME="You are an intelligence analyst producing FIRST-PASS OSINT scaffolding for a luxury travel advisor. Focus: destination/port intel, logistics, timing, weather, risk, competitor offerings. Use your own knowledge only — do not attempt web search." ;;
  *)     FRAME="You are a research assistant producing first-pass scaffolding for a travel advisor." ;;
esac

PROMPT="$FRAME

TASK: $QUERY
${STDIN:+CONTEXT:
$STDIN}

RULES:
- This is a draft for an expert to refine, NOT final client copy.
- Tag each substantive claim with [CONFIRMED] (widely established fact), [INFERRED] (reasonable but unverified), or [UNKNOWN] (needs primary-source check: portal/TESS/dossier).
- Flag anything that MUST be verified against the specific booking (tender port, dates, vendor, price)."

env -u GOOGLE_GENAI_USE_VERTEXAI -u GOOGLE_APPLICATION_CREDENTIALS \
    GEMINI_API_KEY="$KEY" GEMINI_CLI_TRUST_WORKSPACE=true \
    gemini -m gemini-2.5-flash -p "$PROMPT" 2>&1 \
  | grep -vE "Ripgrep is not available|^\[STARTUP\]|cleanup_ops|not running in a trusted|DeprecationWarning|trace-deprecation|^\(node:|^\(Use "
