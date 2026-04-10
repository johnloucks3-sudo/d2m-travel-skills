#!/bin/bash
# Interactive Anthropic API Key Update

echo "=== ANTHROPIC API KEY UPDATE ==="
echo ""

# Step 1: Get the key
read -p "1. Open https://console.anthropic.com/settings/keys in your browser (press Enter when ready)"
echo ""

# Step 2: Copy the new key
read -sp "2. Copy your NEW Anthropic API key (it will start with 'sk-ant-'): " new_key
echo ""
echo ""

# Step 3: Verify format
if [[ ! $new_key == sk-ant-* ]]; then
    echo "❌ ERROR: Key format invalid. Should start with 'sk-ant-'"
    echo "Please check and try again."
    exit 1
fi

echo "Key format looks good!"
echo ""

# Step 4: Update .env file
echo "3. Updating /home/john/Thunderbird/.env..."
sed -i "s/^ANTHROPIC_API_KEY=.*/ANTHROPIC_API_KEY=$new_key/" /home/john/Thunderbird/.env

# Step 5: Test the key
echo "4. Testing new key..."
OUTPUT=$(env -i ANTHROPIC_API_KEY="$new_key" /home/john/.local/bin/claude --model claude-haiku-4-5-20251001 -p "test" --dangerously-skip-permissions 2>&1)

if echo "$OUTPUT" | grep -q "Invalid API key"; then
    echo "❌ Key validation FAILED"
    echo "Output: $OUTPUT"
    echo ""
    echo "Please check:"
    echo "- Key is from https://console.anthropic.com/settings/keys"
    echo "- Key starts with 'sk-ant-'"
    echo "- Account has API access enabled"
    exit 1
else
    echo "✅ Key validation SUCCESSFUL!"
    echo ""
    echo "Tier 2 fallback (Claude Haiku) is now ACTIVE"
    echo "Cost: ~$0.06-0.20 per task"
    echo "Availability: 24/7 (no expiration)"
    echo ""
    echo "The watcher will now use this for fallback tasks"
fi

echo ""
echo "=== UPDATE COMPLETE ==="
echo "New key: ${new_key:0:10}...${new_key: -10}"