#!/bin/bash
# Test Anthropic API Key

echo "=== ANTHROPIC API KEY TEST ==="

KEY=$(grep '^ANTHROPIC_API_KEY=' /home/john/Thunderbird/.env | cut -d= -f2)

if [ -z "$KEY" ]; then
    echo "❌ No API key found in .env"
    exit 1
fi

echo "Key length: ${#KEY} characters"
echo "Key format: ${KEY:0:10}...${KEY: -10}"
echo ""

echo "Testing with Claude Haiku..."
OUTPUT=$(timeout 15 env -i ANTHROPIC_API_KEY="$KEY" /home/john/.local/bin/claude --model claude-haiku-4-5-20251001 -p "Test API key connectivity" --dangerously-skip-permissions 2>&1)
EXIT_CODE=$?

echo "$OUTPUT" | head -5

echo ""
if echo "$OUTPUT" | grep -q "Invalid API key"; then
    echo "❌ API KEY INVALID - Tier 2 fallback will fail"
    echo "Get new key from: https://console.anthropic.com/settings/keys"
    echo "Then update .env file with new key"
elif [ $EXIT_CODE -eq 0 ]; then
    echo "✅ API KEY VALID - Tier 2 fallback will work"
    echo "Cost: ~\$0.06-0.20 per task"
    echo "Availability: 24/7 (no OAuth expiration)"
elif [ $EXIT_CODE -eq 124 ]; then
    echo "⚠️  Test timed out - key may be working (check logs)"
    echo "Check: tail -5 /home/john/Thunderbird/logs/claude_headless.log"
else
    echo "❌ API KEY FAILED - Exit code: $EXIT_CODE"
    echo "Get new key from: https://console.anthropic.com/settings/keys"
fi