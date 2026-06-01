#!/usr/bin/env bash
# multi_model_skill.sh
# Integration script for multi-model orchestration skill

# Create necessary directories
mkdir -p /home/john/Thunderbird/core/multi_model
mkdir -p /home/john/Thunderbird/logs

# Make scripts executable
chmod +x /home/john/Thunderbird/core/multi_model/multi_model_orchestrator.py
chmod +x /home/john/Thunderbird/core/multi_model/multi_model_mcp_server.py

# Add to MCP configuration
MCP_CONFIG="/home/john/.claude/mcp.json"
if [ -f "$MCP_CONFIG" ]; then
    # Backup original config
    cp "$MCP_CONFIG" "$MCP_CONFIG.backup.$(date +%Y%m%d_%H%M%S)"
    
    # Add multi-model server to config
    jq '.mcpServers += {"multi-model": {"command": "/home/john/Thunderbird/core/multi_model/multi_model_mcp_server.py"}}' "$MCP_CONFIG" > "$MCP_CONFIG.tmp"
    mv "$MCP_CONFIG.tmp" "$MCP_CONFIG"
    
    echo "✅ Added multi-model server to MCP config"
else
    echo "❌ MCP config not found: $MCP_CONFIG"
fi

# Create systemd service for persistent MCP server
cat > /tmp/multi_model_mcp.service << 'EOF'
[Unit]
Description=Multi-Model MCP Server for Thunderbird
After=network.target

[Service]
Type=simple
User=john
WorkingDirectory=/home/john/Thunderbird
Environment=PYTHONPATH=/home/john/Thunderbird
ExecStart=/home/john/Thunderbird/.venv/bin/python /home/john/Thunderbird/core/multi_model/multi_model_mcp_server.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo mv /tmp/multi_model_mcp.service /etc/systemd/system/
sudo systemctl daemon-reload

# Test the multi-model skill
echo "🧪 Testing multi-model skill..."
cd /home/john/Thunderbird
source .venv/bin/activate
python core/multi_model/multi_model_orchestrator.py

echo ""
echo "🎉 Multi-Model Skill Installation Complete!"
echo ""
echo "Usage:"
echo "  python core/multi_model/multi_model_orchestrator.py"
echo "  python core/multi_model/multi_model_mcp_server.py --test"
echo ""
echo "MCP Tools Available:"
echo "  - multi_model_analysis: 9-model spectrum analysis with Claude MAX synthesis"