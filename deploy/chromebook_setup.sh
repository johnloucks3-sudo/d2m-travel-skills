#!/usr/bin/env bash
# ============================================================
# Thunderbird OS — Chromebook One-Shot Setup
# Run this ONCE on the Chromebook (Crostini Linux terminal).
# After this, just type: thunderbird
# ============================================================
set -euo pipefail

echo "=== Thunderbird Chromebook Setup ==="
echo ""

# --- 1. Install cloudflared if missing ---
if ! command -v cloudflared &>/dev/null; then
    echo "[1/4] Installing cloudflared..."
    ARCH=$(uname -m)
    case "$ARCH" in
        x86_64)  CF_ARCH="amd64" ;;
        aarch64) CF_ARCH="arm64" ;;
        armv7l)  CF_ARCH="arm"   ;;
        *)       echo "ERROR: Unknown architecture: $ARCH"; exit 1 ;;
    esac
    curl -fsSL "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${CF_ARCH}" \
        -o /tmp/cloudflared
    sudo install -m 755 /tmp/cloudflared /usr/local/bin/cloudflared
    rm /tmp/cloudflared
    echo "    cloudflared installed: $(cloudflared --version)"
else
    echo "[1/4] cloudflared already installed: $(cloudflared --version)"
fi

# --- 2. SSH config ---
echo "[2/4] Configuring SSH..."
mkdir -p ~/.ssh
chmod 700 ~/.ssh

if grep -q "Host thunderbird" ~/.ssh/config 2>/dev/null; then
    echo "    SSH config already has 'thunderbird' entry — skipping"
else
    cat >> ~/.ssh/config << 'EOF'

# Thunderbird OS — YOGA via Cloudflare Tunnel
Host thunderbird
    HostName ssh.d2mluxury.quest
    User john
    ProxyCommand cloudflared access ssh --hostname %h
EOF
    chmod 600 ~/.ssh/config
    echo "    SSH config entry added"
fi

# --- 3. SSH key (generate if needed, show pubkey for YOGA) ---
echo "[3/4] SSH key..."
if [ ! -f ~/.ssh/id_ed25519 ]; then
    ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N "" -C "chromebook-thunderbird"
    echo ""
    echo "    NEW KEY GENERATED. Add this to YOGA:"
    echo "    ────────────────────────────────────"
    echo "    ssh thunderbird   (log in with password first)"
    echo "    Then on YOGA run:"
    echo "    echo '$(cat ~/.ssh/id_ed25519.pub)' >> ~/.ssh/authorized_keys"
    echo "    ────────────────────────────────────"
    echo ""
else
    echo "    SSH key exists"
fi

# --- 4. MCP-only fallback (Claude CLI local + remote tools) ---
echo "[4/6] Setting up MCP-only fallback..."
if command -v claude &>/dev/null; then
    echo "    Claude CLI found: $(claude --version 2>/dev/null || echo 'installed')"
else
    echo "    Claude CLI not found — installing via npm..."
    if command -v npm &>/dev/null; then
        npm install -g @anthropic-ai/claude-code
        echo "    Claude CLI installed"
    else
        echo "    WARNING: npm not found. Install Node.js first, then run:"
        echo "    npm install -g @anthropic-ai/claude-code"
    fi
fi

# --- 5. MCP config for remote tools ---
echo "[5/6] Configuring MCP remote endpoint..."
mkdir -p ~/.claude
if [ -f ~/.claude/mcp.json ]; then
    echo "    mcp.json already exists — skipping (check it points to mcp.d2mluxury.quest)"
else
    cat > ~/.claude/mcp.json << 'MCP'
{
  "mcpServers": {
    "dreams2memories_travel_mcp": {
      "type": "streamable-http",
      "url": "https://mcp.d2mluxury.quest/mcp"
    }
  }
}
MCP
    echo "    mcp.json created — 97 D2M tools available remotely"
fi

# --- 6. Shell aliases ---
echo "[6/6] Adding shell aliases..."
SHELL_RC="$HOME/.bashrc"
[ -f "$HOME/.zshrc" ] && SHELL_RC="$HOME/.zshrc"

if grep -q "alias thunderbird=" "$SHELL_RC" 2>/dev/null; then
    echo "    Aliases already exist — skipping"
else
    cat >> "$SHELL_RC" << 'ALIAS'

# Thunderbird OS — Chromebook launchers
# Primary: SSH to YOGA, full access
alias thunderbird='ssh thunderbird -t "cd ~/Thunderbird && claude"'
alias tb='ssh thunderbird -t "cd ~/Thunderbird && claude"'
alias yoga='ssh thunderbird'
# Fallback: Local Claude CLI + remote MCP tools (no YOGA files, but all 97 tools work)
alias tb-local='claude'
ALIAS
    echo "    Added aliases: thunderbird, tb, yoga, tb-local"
fi

echo ""
echo "=== SETUP COMPLETE ==="
echo ""
echo "Open a new terminal or run: source $SHELL_RC"
echo ""
echo "Commands:"
echo "  thunderbird  — SSH to YOGA → Claude in ~/Thunderbird/ (full access)"
echo "  tb           — same thing, shorter"
echo "  yoga         — SSH to YOGA (plain shell)"
echo "  tb-local     — Claude CLI local + remote MCP tools (fallback)"
echo ""
echo "If 'thunderbird' fails (YOGA down, tunnel issue):"
echo "  tb-local gives you all 97 D2M tools via mcp.d2mluxury.quest"
echo "  No file access to YOGA, but bookings/search/intel all work"
echo ""
