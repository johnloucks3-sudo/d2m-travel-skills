#!/bin/bash
# Quick Status Check — Run anytime to see current operational state
# Usage: ./quick_status_check.sh

echo "🔍 THUNDERBIRD OPERATIONAL STATUS — $(date)"
echo "=================================================="
echo ""

echo "📊 PROCESS STATUS:"
ps aux | grep -E "3094752|3094753|3094754|3082652" | grep -v grep | awk '{print "  PID " $2 ": " $11 " (Running)"}'
echo ""

echo "📁 OUTPUT FILES (Capability Builds):"
ls -lh /home/john/Thunderbird/output/CAPABILITY_*.txt 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}' || echo "  (None yet)"
echo ""

echo "📁 OUTPUT FILES (Opus Consultation):"
ls -lh /home/john/Thunderbird/output/OPUS_AUTONOMY_*.txt 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}' || echo "  (None yet)"
echo ""

echo "📋 VENDOR LETTERS (Ready for Approval):"
echo "  ✓ VENDOR_LETTER_TESS_DRAFT_20260429.md"
echo "  ✓ VENDOR_LETTER_HOTELBEDS_DRAFT_20260429.md"
echo ""

echo "📑 NEW DOSSIERS:"
ls -1 /home/john/Thunderbird/dossiers/ | grep -E "Westbrook_.*UPDATED|Heer_.*ProBono|Heer_.*Japan|Spencer_Prospect|Piontek_Prospect" | sed 's/^/  ✓ /'
echo ""

echo "🚨 ERROR CHECK (Last 10 lines):"
grep -ih "error\|failed\|fatal" /home/john/Thunderbird/logs/capability_*.log /home/john/Thunderbird/logs/opus_*.log 2>/dev/null | tail -10 | sed 's/^/  ⚠️  /' || echo "  ✅ No errors detected"
echo ""

echo "📊 SYSTEM HEALTH:"
[ -f ~/.claude/.credentials.json ] && echo "  ✅ OAuth credentials exist" || echo "  ❌ OAuth credentials MISSING"
systemctl --user is-active claude-token-monitor.timer > /dev/null 2>&1 && echo "  ✅ Token monitor running" || echo "  ❌ Token monitor DOWN"
systemctl --user is-active thunderbird-watchdog.timer > /dev/null 2>&1 && echo "  ✅ Watchdog running" || echo "  ❌ Watchdog DOWN"
curl -s http://localhost:8765/status > /dev/null 2>&1 && echo "  ✅ MCP server online" || echo "  ⚠️  MCP server offline"
echo ""

echo "📖 DOCUMENTATION (For Full Context):"
echo "  📄 RECONSTRUCTION_GUIDE_20260429.md — Start here if lost"
echo "  📊 OPERATIONAL_STATUS_DASHBOARD_20260429.md — Monitoring + recovery"
echo "  📋 HALE_CAPABILITIES_ASSESSMENT_20260429.md — What's being built"
echo ""

echo "⏱️  TIMELINE:"
echo "  ✅ Capability builds: Should be done by 17:45 MT (10 min from start)"
echo "  ⏳ TESS/Hotelbeds credentials: Expected May 2"
echo "  🎯 Full 7-capability stack: May 13"
echo ""

echo "💡 NEXT ACTION:"
echo "  1. Review + approve vendor letters"
echo "  2. Check capability build outputs when ready"
echo "  3. Provide Spencer/Piontek/Heer details"
echo ""

echo "=================================================="
