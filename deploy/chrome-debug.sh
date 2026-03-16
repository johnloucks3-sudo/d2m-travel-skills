#!/bin/bash
# Launch Chrome with CDP remote debugging for Outside Agents portal automation.
# Usage: ./chrome-debug.sh
#
# After launch, log into portals in Chrome, then use oa_* MCP tools.
# To refresh profile from main Chrome: delete ~/.config/google-chrome-debug and rerun.

CHROME_DEBUG_DIR="$HOME/.config/google-chrome-debug"
CDP_PORT=9222

# Check if debug Chrome is already running
if curl -sf "http://127.0.0.1:$CDP_PORT/json/version" > /dev/null 2>&1; then
    echo "✓ Chrome debug already running on port $CDP_PORT"
    curl -sf "http://127.0.0.1:$CDP_PORT/json/version" | python3 -m json.tool 2>/dev/null
    exit 0
fi

# Sync profile from main Chrome if debug profile doesn't exist
if [ ! -d "$CHROME_DEBUG_DIR" ]; then
    echo "Creating debug Chrome profile from main profile..."
    cp -r "$HOME/.config/google-chrome" "$CHROME_DEBUG_DIR"
    rm -f "$CHROME_DEBUG_DIR"/SingletonLock "$CHROME_DEBUG_DIR"/SingletonCookie "$CHROME_DEBUG_DIR"/SingletonSocket
    echo "✓ Profile copied"
fi

echo "Launching Chrome with CDP on port $CDP_PORT..."
google-chrome-stable \
    --remote-debugging-port=$CDP_PORT \
    --user-data-dir="$CHROME_DEBUG_DIR" \
    2>/dev/null &

# Wait for debug port
for i in $(seq 1 10); do
    sleep 1
    if curl -sf "http://127.0.0.1:$CDP_PORT/json/version" > /dev/null 2>&1; then
        echo "✓ Chrome ready on port $CDP_PORT"
        exit 0
    fi
done

echo "✗ Chrome failed to start with debug port"
exit 1
