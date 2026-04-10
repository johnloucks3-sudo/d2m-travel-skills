#!/bin/bash
# Simple one-command API key update

echo "=== SIMPLE API KEY UPDATE ==="
echo ""
echo "Usage:"
echo "  bash update_key_simple.sh YOUR_NEW_API_KEY"
echo ""

if [ $# -eq 0 ]; then
    echo "❌ Please provide your API key as an argument"
    echo "Example: bash update_key_simple.sh sk-ant-abc123...xyz"
    exit 1
fi

new_key="$1"

# Validate format
if [[ ! $new_key == sk-ant-* ]]; then
    echo "❌ ERROR: Key must start with 'sk-ant-'"
    echo "Get key from: https://console.anthropic.com/settings/keys"
    exit 1
fi

# Update .env
echo "Updating .env file..."
sed -i "s/^ANTHROPIC_API_KEY=.*/ANTHROPIC_API_KEY=$new_key/" /home/john/Thunderbird/.env

# Test
echo "Testing key..."
if env -i ANTHROPIC_API_KEY="$new_key" /home/john/.local/bin/claude --model claude-haiku-4-5-20251001 -p "test" --dangerously-skip-permissions 2>&1 | grep -q "Invalid API key"; then
    echo "❌ Key validation failed"
    echo "Please check your key at: https://console.anthropic.com/settings/keys"
    exit 1
else
    echo "✅ Key updated successfully!"
    echo "Tier 2 fallback (Claude Haiku) activated"
    echo "Cost: ~$0.06-0.20 per task"
fi