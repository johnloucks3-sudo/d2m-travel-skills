#!/bin/bash
# Fix Thunderbird daemon memory limits on YOGA
# Run on YOGA: ssh yoga bash /home/john/Thunderbird/scripts/fix_memory_ceilings.sh

set -e

echo "🔧 Applying memory ceilings to Thunderbird daemons..."

# Directories for systemd user service overrides
USER_UNIT_DIR="$HOME/.config/systemd/user"
OVERRIDE_DIR="$USER_UNIT_DIR/service.d"

mkdir -p "$OVERRIDE_DIR"

# ============================================================================
# 1. OpenCode SPSA Monitor — Set to 2GB max (was infinity)
# ============================================================================
echo "Setting OpenCode → 2GB MemoryMax..."
cat > "$OVERRIDE_DIR/opencode-spsa-monitor-memory.conf" << 'EOF'
[Service]
MemoryMax=2147483648
MemoryHigh=1610612736
EOF

# ============================================================================
# 2. Qdrant (if it starts later) — Set to 4GB max (was infinity)
# ============================================================================
echo "Setting Qdrant → 4GB MemoryMax..."
cat > "$OVERRIDE_DIR/qdrant-memory.conf" << 'EOF'
[Service]
MemoryMax=4294967296
MemoryHigh=3221225472
EOF

# ============================================================================
# 3. D2M Gmail AgentMail Bridge — Set to 1.5GB (new ceiling)
# ============================================================================
echo "Setting AgentMail bridge → 1.5GB MemoryMax..."
cat > "$OVERRIDE_DIR/d2m-gmail-agentmail-bridge-memory.conf" << 'EOF'
[Service]
MemoryMax=1610612736
MemoryHigh=1342177280
EOF

# ============================================================================
# 4. Credential Health Check — Set to 512MB (new ceiling)
# ============================================================================
echo "Setting Credential check → 512MB MemoryMax..."
cat > "$OVERRIDE_DIR/hale-credential-check-memory.conf" << 'EOF'
[Service]
MemoryMax=536870912
MemoryHigh=469762048
EOF

# ============================================================================
# 5. Any other Thunderbird service — Add generic backstop
# ============================================================================
echo "Setting fallback ceiling for all services..."
cat > "$OVERRIDE_DIR/thunderbird-default-memory.conf" << 'EOF'
# Default memory limit for any Thunderbird service without explicit override
[Service]
MemoryMax=1073741824
MemoryHigh=805306368
EOF

# ============================================================================
# Reload and restart
# ============================================================================
echo ""
echo "Reloading systemd user services..."
systemctl --user daemon-reload

echo "Restarting services with new memory limits..."
systemctl --user restart opencode-spsa-monitor.service 2>/dev/null || echo "  (opencode-spsa-monitor not running, will start with limit when needed)"
systemctl --user restart d2m-gmail-agentmail-bridge.service 2>/dev/null || echo "  (agentmail bridge not running)"
systemctl --user restart hale-credential-check.service 2>/dev/null || echo "  (credential check not running)"

echo ""
echo "✅ Memory ceilings applied. Checking config..."
echo ""
echo "OpenCode SPSA Monitor:"
systemctl --user show opencode-spsa-monitor.service -p MemoryMax -p MemoryHigh 2>/dev/null || echo "  (not found)"

echo ""
echo "Qdrant:"
systemctl --user show qdrant.service -p MemoryMax -p MemoryHigh 2>/dev/null || echo "  (not found)"

echo ""
echo "AgentMail bridge:"
systemctl --user show d2m-gmail-agentmail-bridge.service -p MemoryMax -p MemoryHigh 2>/dev/null || echo "  (not found)"

echo ""
echo "📊 System memory status:"
free -h

echo ""
echo "✅ DONE. Swap thrashing should be prevented now."
echo ""
echo "Next: Monitor swap usage over the next hour:"
echo "  watch -n 5 'free -h && echo && vmstat 1 3'"
