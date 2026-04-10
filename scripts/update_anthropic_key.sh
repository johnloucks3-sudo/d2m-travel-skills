#!/bin/bash
# Secure Anthropic API Key Update Script
# Run with: bash scripts/update_anthropic_key.sh

echo "=== ANTHROPIC API KEY UPDATE ==="
echo "Current key status: $(grep -c "ANTHROPIC_API_KEY" /home/john/Thunderbird/.env)"
echo ""

# Check if key is currently invalid
echo "Testing current API key..."
if env -i ANTHROPIC_API_KEY="$(grep '^ANTHROPIC_API_KEY=' /home/john/Thunderbird/.env | cut -d= -f2)" /home/john/.local/bin/claude --model claude-haiku-4-5-20251001 -p "test" --dangerously-skip-permissions 2>&1 | grep -q "Invalid API key"; then
    echo "❌ Current API key is INVALID"
    NEEDS_UPDATE=true
else
    echo "✅ Current API key appears valid"
    NEEDS_UPDATE=false
fi

echo ""
if [ "$NEEDS_UPDATE" = true ]; then
    echo "TO UPDATE YOUR ANTHROPIC API KEY:"
    echo "1. Get new key from: https://console.anthropic.com/settings/keys"
    echo "2. Run this command:"
    echo "   read -sp 'Enter new Anthropic API key: ' new_key && echo"
    echo "   sed -i 's/^ANTHROPIC_API_KEY=.*/ANTHROPIC_API_KEY='\"\$new_key\"\'/g' /home/john/Thunderbird/.env"
    echo "3. Test with: bash scripts/test_anthropic_key.sh"
else
    echo "Current key appears valid. To update anyway, follow steps above."
fi

echo ""
echo "Current key format:"
grep '^ANTHROPIC_API_KEY=' /home/john/Thunderbird/.env | head -c20
echo "..."

echo ""
echo "After update, Tier 2 fallback (Claude Haiku) will work for:"
echo "• ~\$0.06-0.20 per task"
echo "• 24/7 availability"
echo "• Fast operational tasks"