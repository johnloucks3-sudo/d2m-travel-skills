#!/usr/bin/env bash
# ============================================================
# Thunderbird OS — Chromebook SSH + Tailscale Patch
# Run this ONCE in the Chromebook Crostini terminal.
# Fixes: broken ssh thunderbird alias, Tailscale auto-reconnect
# ============================================================
set -euo pipefail

SHELL_RC="$HOME/.bashrc"
[ -f "$HOME/.zshrc" ] && SHELL_RC="$HOME/.zshrc"

echo "=== Thunderbird Chromebook SSH Patch ==="
echo ""

# --- 1. Fix SSH aliases ---
echo "[1/3] Patching SSH aliases..."

# Remove the broken cloudflare-based alias if present
if grep -q "alias thunderbird=" "$SHELL_RC" 2>/dev/null; then
    sed -i '/alias thunderbird=/d' "$SHELL_RC"
    sed -i '/alias tb=/d' "$SHELL_RC"
    sed -i '/alias yoga=/d' "$SHELL_RC"
    sed -i '/alias tb-local=/d' "$SHELL_RC"
    echo "    Removed old broken aliases"
fi

# Add correct Tailscale-based aliases
cat >> "$SHELL_RC" << 'ALIAS'

# Thunderbird OS — YOGA SSH aliases (patched 2026-05-25)
# Primary: Tailscale MagicDNS (works when Tailscale is up)
alias yoga='ssh john@yoga'
alias tb='ssh john@yoga -t "cd ~/Thunderbird && claude"'
alias thunderbird='ssh john@yoga -t "cd ~/Thunderbird && claude"'
# Fallback: direct Tailscale IP (if MagicDNS is flaky)
alias yoga-ip='ssh john@100.69.222.124'
alias tb-ip='ssh john@100.69.222.124 -t "cd ~/Thunderbird && claude"'
# Local Claude CLI + remote MCP (no YOGA files needed)
alias tb-local='claude'
ALIAS
echo "    New aliases added: yoga, tb, thunderbird, yoga-ip, tb-ip, tb-local"

# --- 2. Tailscale auto-reconnect on login ---
echo "[2/3] Adding Tailscale reconnect on login..."

if grep -q "tailscale_autoconnect" "$SHELL_RC" 2>/dev/null; then
    echo "    Tailscale reconnect already in $SHELL_RC — skipping"
else
    cat >> "$SHELL_RC" << 'TAILSCALE'

# Tailscale auto-reconnect (thunderbird patch 2026-05-25)
# Crostini container drops Tailscale on restart — this reconnects silently
tailscale_autoconnect() {
    if command -v tailscale &>/dev/null; then
        local status
        status=$(tailscale status 2>/dev/null | head -1)
        if echo "$status" | grep -qE "stopped|Stopped|not connected|NeedsLogin"; then
            echo "[Tailscale] Reconnecting..."
            sudo tailscale up 2>/dev/null && echo "[Tailscale] Connected" || echo "[Tailscale] WARNING: reconnect failed — run: sudo tailscale up"
        fi
    fi
}
tailscale_autoconnect
TAILSCALE
    echo "    Tailscale auto-reconnect added to $SHELL_RC"
fi

# --- 3. Remove the broken cloudflare SSH proxy config ---
echo "[3/3] Cleaning up broken SSH config..."
if grep -q "ProxyCommand cloudflared access ssh" ~/.ssh/config 2>/dev/null; then
    # Comment out the old broken entry
    sed -i '/Host thunderbird/,/ProxyCommand cloudflared/s/^/# BROKEN: /' ~/.ssh/config
    echo "    Commented out broken cloudflared SSH entry in ~/.ssh/config"
    echo "    YOGA is now reached via Tailscale directly — no cloudflared needed"
else
    echo "    No cloudflared SSH entry found — nothing to clean"
fi

echo ""
echo "=== PATCH COMPLETE ==="
echo ""
echo "Run: source $SHELL_RC"
echo ""
echo "Then use:"
echo "  yoga           — plain SSH shell on YOGA (via Tailscale)"
echo "  tb             — SSH → YOGA → Claude in ~/Thunderbird/"
echo "  thunderbird    — same as tb"
echo "  yoga-ip        — fallback using raw Tailscale IP 100.69.222.124"
echo "  tb-local       — Claude CLI local + MCP tools (no YOGA needed)"
echo ""
echo "If 'yoga' hangs: Tailscale is probably down. Run: sudo tailscale up"
echo "Then retry: yoga"
echo ""
