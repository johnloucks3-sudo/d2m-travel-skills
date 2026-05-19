#!/usr/bin/env python3
"""
AI Metrics Export Script for Looker Studio
===========================================
Simple script to export AI metrics to Google Sheets for Looker Studio integration.
Can be run via cron or systemd timer.

Usage:
  python3 ai_metrics_export.py          # Export once and exit
  python3 ai_metrics_export.py --cron   # Cron mode (quiet, logs to file)
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.ops.thunderbird_ai_metrics_dashboard import (
    get_combined_metrics,
    export_to_google_sheets,
    send_telegram_notification,
)

def main():
    parser = argparse.ArgumentParser(description="AI Metrics Export for Looker Studio")
    parser.add_argument("--cron", action="store_true", help="Cron mode (quiet logging)")
    parser.add_argument("--debug", action="store_true", help="Debug mode")
    args = parser.parse_args()
    
    # Setup logging
    log_file = Path("/home/john/Thunderbird/logs/ai_metrics_export.log")
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format='%(asctime)s [AI_METRICS_EXPORT] %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(str(log_file)),
            logging.StreamHandler() if not args.cron else logging.NullHandler()
        ]
    )
    logger = logging.getLogger(__name__)
    
    logger.info("Starting AI metrics export for Looker Studio")
    
    try:
        # Get combined metrics
        metrics = get_combined_metrics()
        logger.info(f"Retrieved metrics: {metrics['summary']}")
        
        # Export to Google Sheets
        success = export_to_google_sheets(metrics)
        
        if success:
            logger.info(f"✅ Successfully exported metrics to Google Sheets: {metrics['timestamp']}")
            
            # Send Telegram notification (only for significant updates)
            claude_pct = metrics['claude']['session']['percentage']
            daily_cost = metrics['openrouter']['usage']['daily_usd']
            
            # Only send notification if:
            # 1. First export of the day, OR
            # 2. Claude usage > 80%, OR  
            # 3. Daily cost > $2, OR
            # 4. Budget status is RED
            should_notify = (
                claude_pct > 80 or 
                daily_cost > 2.0 or 
                metrics['summary']['budget_status'] == "RED"
            )
            
            if should_notify:
                message = f"""📊 <b>AI Metrics Auto-Export</b>

🤖 <b>Claude:</b> {claude_pct}% of session limit
💰 <b>OpenRouter:</b> ${daily_cost:.2f} today
🎯 <b>Status:</b> {metrics['summary']['budget_status']}
📈 <b>Messages:</b> {metrics['summary']['total_messages_today']} total

✅ <i>Data exported to Looker Studio</i>
📅 {datetime.now().strftime('%Y-%m-%d %H:%M MT')}"""
                
                telegram_success = send_telegram_notification(message)
                if telegram_success:
                    logger.info("✅ Telegram notification sent")
                else:
                    logger.warning("⚠️ Telegram notification failed")
            
            # Also log to a simple status file for monitoring
            status_file = Path("/home/john/Thunderbird/logs/ai_metrics_last_export.json")
            status_data = {
                "last_export": datetime.now().isoformat(),
                "claude_percentage": claude_pct,
                "daily_cost": daily_cost,
                "budget_status": metrics['summary']['budget_status'],
                "success": True
            }
            status_file.write_text(json.dumps(status_data, indent=2))
            
        else:
            logger.error("❌ Failed to export metrics to Google Sheets")
            
            # Send error notification
            error_msg = f"""❌ <b>AI Metrics Export Failed</b>

Failed to export data to Looker Studio.

⚠️ Check logs at: {log_file}
📅 {datetime.now().strftime('%Y-%m-%d %H:%M MT')}"""
            
            send_telegram_notification(error_msg)
            
            # Update status file
            status_file = Path("/home/john/Thunderbird/logs/ai_metrics_last_export.json")
            status_data = {
                "last_export": datetime.now().isoformat(),
                "success": False,
                "error": "Export failed"
            }
            status_file.write_text(json.dumps(status_data, indent=2))
            
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"❌ Critical error during export: {e}", exc_info=True)
        
        # Send critical error notification
        error_msg = f"""🚨 <b>AI Metrics Export Critical Error</b>

Error: {str(e)[:200]}

🔧 Check system immediately!
📅 {datetime.now().strftime('%Y-%m-%d %H:%M MT')}"""
        
        send_telegram_notification(error_msg)
        sys.exit(1)

if __name__ == "__main__":
    main()