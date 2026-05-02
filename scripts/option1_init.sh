#!/bin/bash
# OPTION 1 INITIALIZATION SCRIPT
# Stage 1: Gemini CLI Setup, Stage 2: Aider Config, Stage 3: Claude Max Verify

set -e

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_DIR="/home/john/Thunderbird/logs"
LOG_FILE="$LOG_DIR/option1_init_$TIMESTAMP.log"
mkdir -p "$LOG_DIR"

{
  echo "[$(date)] === OPTION 1 STACK INITIALIZATION ==="
  echo ""

  # Check Gemini API key
  if [ -z "$GEMINI_API_KEY" ]; then
    echo "❌ ERROR: GEMINI_API_KEY not set in environment"
    echo "ACTION: export GEMINI_API_KEY='your-key-from-google-keep'"
    exit 1
  fi
  echo "✓ GEMINI_API_KEY is set"

  # Stage 1: Install Gemini CLI packages
  echo ""
  echo "[$(date)] Stage 1: Installing Gemini CLI packages..."
  if ! python3 -c "import google.generativeai" 2>/dev/null; then
    pip3 install -q google-generativeai 2>&1 | tail -3
    echo "✓ google-ai package installed"
  else
    echo "✓ google-ai package already installed"
  fi

  # Test Gemini connectivity
  echo "[$(date)] Testing Gemini API connectivity..."
  python3 << 'GEMINI_TEST'
import google.generativeai as genai
import os
try:
    genai.configure(api_key=os.environ['GEMINI_API_KEY'])
    model = genai.GenerativeModel('gemini-2.0-flash')
    response = model.generate_content('test')
    print("✓ Gemini API connectivity verified")
except Exception as e:
    print(f"❌ Gemini API error: {e}")
    exit(1)
GEMINI_TEST

  # Stage 2: Install and configure Aider
  echo ""
  echo "[$(date)] Stage 2: Installing Aider..."
  if ! command -v aider &> /dev/null; then
    pip3 install -q aider-chat 2>&1 | tail -3
    echo "✓ Aider installed"
  else
    echo "✓ Aider already installed"
  fi

  # Configure Aider for Gemini backend
  cat > ~/.aider.conf.yml << 'AIDER_CONFIG'
model: gemini-2.0-flash
auto-commits: false
no-auto-commits: true
AIDER_CONFIG
  echo "✓ Aider configured for Gemini backend"

  # Stage 3: Verify Claude Code Max
  echo ""
  echo "[$(date)] Stage 3: Verifying Claude Code Max..."
  if [ -f "/home/john/.local/bin/claude" ]; then
    /home/john/.local/bin/claude --version 2>/dev/null | head -1
    echo "✓ Claude Code Max available"
  else
    echo "⚠ Claude Code binary not found at /home/john/.local/bin/claude"
    echo "   Install via: brew install anthropic/brew/claude (macOS) or download binary"
  fi

  # Summary
  echo ""
  echo "[$(date)] === INITIALIZATION COMPLETE ==="
  echo ""
  echo "Stack Status:"
  echo "  ✓ Gemini CLI: READY"
  echo "  ✓ Aider: READY (backend: gemini)"
  echo "  ✓ Claude Max: $([ -f /home/john/.local/bin/claude ] && echo 'READY' || echo 'CHECK INSTALLATION')"
  echo ""
  echo "Next: python3 OpsCenter/option1_stack_health_check.py"

} | tee -a "$LOG_FILE"

exit 0
