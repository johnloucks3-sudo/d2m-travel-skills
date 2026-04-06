#!/bin/bash
# Uninstall OpenCode and revert to Claude Code + Goose only
# Run: bash ~/Thunderbird/scripts/uninstall_opencode.sh

set -e

echo "=== Uninstalling OpenCode ==="

# Use built-in uninstaller if available
if command -v opencode &>/dev/null || [ -f ~/.opencode/bin/opencode ]; then
    export PATH=~/.opencode/bin:$PATH
    opencode uninstall 2>/dev/null || true
fi

# Manual cleanup
rm -rf ~/.opencode
rm -rf ~/.local/share/opencode
rm -f ~/Thunderbird/.opencode.json

# Remove PATH entry from .bashrc
sed -i '/# opencode/d' ~/.bashrc
sed -i '/\.opencode\/bin/d' ~/.bashrc

echo "=== OpenCode removed ==="
echo "Claude Code ($(claude --version 2>/dev/null || echo 'not found')) remains installed."
echo "To reinstall: curl -fsSL https://opencode.ai/install | bash"
