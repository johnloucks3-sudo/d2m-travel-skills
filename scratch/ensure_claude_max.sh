#!/bin/bash
# Ensure Claude MAX is available and working
# Run this before any Claude operations in Thunderbird

set -e

LOG_FILE="/home/john/Thunderbird/logs/claude_max.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

log "Starting Claude MAX availability check"

# Check if claude CLI is available
if ! command -v claude &> /dev/null; then
    log "ERROR: claude CLI not found in PATH"
    echo "❌ Claude CLI not found. Please install Claude Code."
    exit 1
fi

log "Claude CLI found: $(claude --version)"

# Test Claude MAX OAuth
echo "Testing Claude MAX OAuth access..."
log "Testing Claude MAX OAuth access"

# Remove API keys to force OAuth usage
export ANTHROPIC_API_KEY=""
export ANTHROPIC_BASE_URL=""
export CLAUDE_CODE_OAUTH_TOKEN=""

TEMP_OUT=$(mktemp)
TEMP_ERR=$(mktemp)

# Test with a simple prompt
if env -u ANTHROPIC_API_KEY -u ANTHROPIC_BASE_URL \
    claude --dangerously-skip-permissions -p "Test message from Thunderbird. Please respond with 'Claude MAX working!'" \
    2>"$TEMP_ERR" 1>"$TEMP_OUT"; then
    
    RESPONSE=$(cat "$TEMP_OUT")
    if echo "$RESPONSE" | grep -q "Claude MAX working"; then
        log "✅ Claude MAX OAuth is working!"
        echo "✅ Claude MAX OAuth is working!"
        
        # Create Thunderbird cache with timestamp
        CACHE_FILE="/home/john/Thunderbird/OpsCenter/.claude_oauth_cache"
        echo "CLAUDE_CODE_OAUTH_TOKEN=verified_max_$(date +%s)" > "$CACHE_FILE"
        log "Updated Thunderbird cache: $CACHE_FILE"
        
        echo "Claude MAX is ready for Thunderbird operations"
        
        rm "$TEMP_OUT" "$TEMP_ERR"
        exit 0
    else
        log "Claude responded but not as expected: ${RESPONSE:0:100}..."
        echo "⚠️ Claude responded but not as expected"
    fi
else
    ERROR=$(cat "$TEMP_ERR" | head -5)
    log "Claude OAuth test failed: $ERROR"
    
    if echo "$ERROR" | grep -q "401\|Invalid authentication"; then
        echo "❌ Claude OAuth token invalid or expired"
        echo ""
        echo "To fix Claude MAX OAuth:"
        echo "1. Open Claude Desktop (the GUI application)"
        echo "2. Make sure you're logged in with your MAX subscription"
        echo "3. Wait for Claude Desktop to be fully loaded"
        echo "4. Then run this script again"
        echo ""
        echo "Your Claude MAX subscription ($100/month) provides free access"
        echo "via OAuth through Claude Desktop."
    else
        echo "❌ Claude error: $ERROR"
    fi
fi

rm "$TEMP_OUT" "$TEMP_ERR" 2>/dev/null || true
exit 1