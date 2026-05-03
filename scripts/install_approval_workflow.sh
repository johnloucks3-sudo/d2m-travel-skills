#!/bin/bash
# Install & Configure COS Approval Workflow
# Run once to set up entire approval system

set -e

echo "==================================================================="
echo "COS APPROVAL WORKFLOW — INSTALLATION"
echo "==================================================================="

# Step 1: Create directories
echo ""
echo "[1/5] Creating approval directories..."
mkdir -p ~/.thunderbird_approvals
mkdir -p ~/Thunderbird/drafts
mkdir -p ~/Thunderbird/output
echo "✓ Directories created"

# Step 2: Verify scripts exist
echo ""
echo "[2/5] Verifying scripts..."
SCRIPTS=(
    "scripts/create_gmail_draft_direct_v3.py"
    "scripts/cos_approval_monitor.py"
    "scripts/cos_final_draft_generator.py"
    "scripts/setup_d2mconcierge_oauth.py"
    "scripts/cos-approval-monitor.service"
)

for script in "${SCRIPTS[@]}"; do
    if [ ! -f "$HOME/Thunderbird/$script" ]; then
        echo "✗ MISSING: $script"
        exit 1
    fi
done
echo "✓ All scripts present"

# Step 3: Set execute permissions
echo ""
echo "[3/5] Setting permissions..."
chmod +x ~/Thunderbird/scripts/create_gmail_draft_direct_v3.py
chmod +x ~/Thunderbird/scripts/cos_approval_monitor.py
chmod +x ~/Thunderbird/scripts/cos_final_draft_generator.py
chmod +x ~/Thunderbird/scripts/setup_d2mconcierge_oauth.py
chmod +x ~/Thunderbird/scripts/install_approval_workflow.sh
echo "✓ Permissions set"

# Step 4: Install systemd service (requires sudo)
echo ""
echo "[4/5] Installing systemd service..."
echo "This step requires sudo. You may be prompted for your password."

if [ ! -f /etc/systemd/system/cos-approval-monitor.service ]; then
    sudo cp ~/Thunderbird/scripts/cos-approval-monitor.service /etc/systemd/system/
    echo "✓ Service file installed"
else
    echo "✓ Service file already present"
fi

sudo systemctl daemon-reload
echo "✓ Systemd reloaded"

# Step 5: Authenticate d2mconcierge
echo ""
echo "[5/5] Setting up d2mconcierge OAuth..."
echo "A browser window will open. Sign in with d2mconcierge@gmail.com"
echo "Press ENTER to continue..."
read

if [ ! -f ~/.credentials/d2mconcierge.json ]; then
    python3 ~/Thunderbird/scripts/setup_d2mconcierge_oauth.py
else
    echo "✓ d2mconcierge credentials already configured"
fi

# Final steps
echo ""
echo "==================================================================="
echo "✅ INSTALLATION COMPLETE"
echo "==================================================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Start the approval monitor service:"
echo "   sudo systemctl enable --now cos-approval-monitor.service"
echo ""
echo "2. Verify it's running:"
echo "   sudo systemctl status cos-approval-monitor.service"
echo ""
echo "3. Create your first draft:"
echo "   python3 ~/Thunderbird/scripts/create_gmail_draft_direct_v3.py \\"
echo "     --html ~/Thunderbird/drafts/example.html \\"
echo "     --to johnloucks3@gmail.com \\"
echo "     --subject '[DRAFT] Example Proposal'"
echo ""
echo "4. Read the full manual:"
echo "   less ~/Thunderbird/docs/APPROVAL_WORKFLOW_OPERATOR_MANUAL.md"
echo ""
echo "==================================================================="
