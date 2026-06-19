#!/usr/bin/env python3
"""
Thunderbird AI Metrics Dashboard — Dreams2Memories Travel, LLC
================================================================
Combined dashboard for Claude usage + OpenRouter activity tracking.

Provides:
1. Real-time Claude usage metrics (from claude_usage_tracker.py)
2. OpenRouter activity and cost tracking (from thunderbird_openrouter_monitor.py)
3. Google Sheets export for Looker Studio integration
4. Telegram notification when dashboard updates

Usage:
  python3 thunderbird_ai_metrics_dashboard.py              # Default port 8767
  python3 thunderbird_ai_metrics_dashboard.py --port 9000  # Custom port
  python3 thunderbird_ai_metrics_dashboard.py --export     # Export to Google Sheets only
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional

try:
    from flask import Flask, render_template_string, jsonify, request
    import requests
except ImportError as e:
    print(f"ERROR: Missing dependency: {e}")
    print("Install with: pip install flask requests")
    sys.exit(1)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import our usage trackers
from core.intel.thunderbird_openrouter_monitor import OpenRouterMonitor

# ── Configuration ──────────────────────────────────────────────────────────

THUNDERBIRD_DIR = Path("/home/john/Thunderbird")
LOG_DIR = THUNDERBIRD_DIR / "logs"
AI_METRICS_LOG = LOG_DIR / "ai_metrics_dashboard.log"
AI_METRICS_STATE = THUNDERBIRD_DIR / "state" / "ai_metrics_state.json"

# Google Sheets configuration (for Looker Studio integration)
GOOGLE_SHEETS_ID = os.environ.get("D2M_METRICS_SHEET_ID", "")  # Set this for Looker Studio
GOOGLE_SHEETS_RANGE = "AI_Metrics!A:Z"

# Telegram notification configuration
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_C2_CHAT_ID", "")

# ── Logging ────────────────────────────────────────────────────────────────

LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=str(AI_METRICS_LOG),
    level=logging.INFO,
    format='%(asctime)s [AI_METRICS_DASHBOARD] %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)

# ── Flask App ──────────────────────────────────────────────────────────────

app = Flask(__name__)
app.json.sort_keys = False

# ── Data Collection Functions ──────────────────────────────────────────────

def get_claude_usage() -> Dict[str, Any]:
    """Get Claude usage metrics from claude_usage_tracker.py."""
    try:
        # Import and use the claude usage tracker
        from OpsCenter.claude_usage_tracker import get_status as get_claude_status
        
        status = get_claude_status()
        
        # Calculate percentages
        session_pct = (status.get("effective_messages", 0) / status.get("session_limit", 1)) * 100
        weekly_pct = (status.get("weekly_messages", 0) / status.get("weekly_limit", 1)) * 100
        sonnet_pct = (status.get("sonnet_messages_today", 0) / status.get("sonnet_daily_limit", 1)) * 100
        
        return {
            "session": {
                "messages": status.get("session_messages", 0),
                "limit": status.get("session_limit", 225),
                "percentage": round(session_pct, 1),
                "effective_messages": status.get("effective_messages", 0),
                "start_time": status.get("session_start", ""),
            },
            "weekly": {
                "messages": status.get("weekly_messages", 0),
                "limit": status.get("weekly_limit", 1500),
                "percentage": round(weekly_pct, 1),
                "start_time": status.get("weekly_start", ""),
            },
            "sonnet_daily": {
                "messages": status.get("sonnet_messages_today", 0),
                "limit": status.get("sonnet_daily_limit", 25),
                "percentage": round(sonnet_pct, 1),
                "start_time": status.get("sonnet_day_start", ""),
            },
            "sources": status.get("sources", {}),
            "budget_status": status.get("budget_status", "UNKNOWN"),
            "last_message_at": status.get("last_message_at", ""),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to get Claude usage: {e}")
        return {"error": str(e), "timestamp": datetime.now().isoformat()}

def get_openrouter_metrics() -> Dict[str, Any]:
    """Get OpenRouter metrics from thunderbird_openrouter_monitor.py."""
    try:
        monitor = OpenRouterMonitor()
        
        # Get usage stats
        usage_stats = monitor.get_usage_stats()
        if "error" in usage_stats:
            logger.warning(f"OpenRouter usage stats error: {usage_stats['error']}")
        
        # Get credit balance
        credit_info = monitor.get_credits()
        if "error" in credit_info:
            logger.warning(f"OpenRouter credit info error: {credit_info['error']}")
        
        # Get models (for cost analysis)
        models = monitor.get_models()
        
        return {
            "usage": {
                "total_usd": usage_stats.get("total_usage", 0),
                "daily_usd": usage_stats.get("daily_usage", 0),
                "weekly_usd": usage_stats.get("weekly_usage", 0),
                "monthly_usd": usage_stats.get("monthly_usage", 0),
                "byok_usd": usage_stats.get("byok_usage", 0),
                "is_free_tier": usage_stats.get("is_free_tier", False),
            },
            "credits": {
                "total_credits": credit_info.get("total_credits", 0),
                "total_usage": credit_info.get("total_usage", 0),
                "remaining": credit_info.get("remaining", 0),
            },
            "models_used": len(models),
            "top_models": models[:5] if models else [],
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to get OpenRouter metrics: {e}")
        return {"error": str(e), "timestamp": datetime.now().isoformat()}

def get_operational_metrics() -> Dict[str, Any]:
    """Get qualitative operational metrics (Satisfaction, Morale)."""
    metrics_file = THUNDERBIRD_DIR / "OpsCenter" / "d2m_operational_metrics.json"
    try:
        with open(metrics_file, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load operational metrics: {e}")
        return {
            "commander_satisfaction": 0.0,
            "staff_morale": 0.0,
            "client_operational_stats": {"open_dossiers": 0},
            "last_updated": "UNKNOWN"
        }

def get_combined_metrics() -> Dict[str, Any]:
    """Get combined Claude + OpenRouter + Operational metrics."""
    claude_data = get_claude_usage()
    openrouter_data = get_openrouter_metrics()
    ops_data = get_operational_metrics()
    
    # Calculate overall cost efficiency
    claude_messages = claude_data.get("session", {}).get("messages", 0)
    openrouter_cost = openrouter_data.get("usage", {}).get("daily_usd", 0)
    
    cost_per_message = 0
    if claude_messages > 0 and openrouter_cost > 0:
        cost_per_message = openrouter_cost / claude_messages
    
    return {
        "timestamp": datetime.now().isoformat(),
        "claude": claude_data,
        "openrouter": openrouter_data,
        "operational": ops_data,
        "summary": {
            "total_messages_today": claude_messages,
            "total_cost_today": openrouter_cost,
            "cost_per_message": round(cost_per_message, 4),
            "budget_status": claude_data.get("budget_status", "UNKNOWN"),
            "is_free_tier": openrouter_data.get("usage", {}).get("is_free_tier", False),
        },
    }

# ── Google Sheets Export (for Looker Studio) ───────────────────────────────

def export_to_google_sheets(metrics: Dict[str, Any]) -> bool:
    """Export metrics to Google Sheets for Looker Studio integration."""
    if not GOOGLE_SHEETS_ID:
        logger.warning("No Google Sheets ID configured for Looker Studio export")
        return False
    
    try:
        import gspread
        from google.oauth2 import service_account
        
        # Use existing credentials from Thunderbird
        credentials_file = THUNDERBIRD_DIR / "credentials.json"
        if not credentials_file.exists():
            logger.error(f"Google credentials file not found: {credentials_file}")
            return False
        
        creds = service_account.Credentials.from_service_account_file(
            str(credentials_file),
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        
        gc = gspread.authorize(creds)
        sheet = gc.open_by_key(GOOGLE_SHEETS_ID)
        
        # Prepare data for Google Sheets
        timestamp = metrics["timestamp"]
        summary = metrics["summary"]
        claude = metrics["claude"]
        openrouter = metrics["openrouter"]
        
        row_data = [
            timestamp,
            summary["total_messages_today"],
            summary["total_cost_today"],
            summary["cost_per_message"],
            summary["budget_status"],
            summary["is_free_tier"],
            claude.get("session", {}).get("percentage", 0),
            claude.get("weekly", {}).get("percentage", 0),
            claude.get("sonnet_daily", {}).get("percentage", 0),
            openrouter.get("usage", {}).get("daily_usd", 0),
            openrouter.get("usage", {}).get("monthly_usd", 0),
            openrouter.get("credits", {}).get("remaining", 0),
        ]
        
        # Append to sheet
        worksheet = sheet.worksheet("AI_Metrics") if "AI_Metrics" in [ws.title for ws in sheet.worksheets()] else sheet.add_worksheet(title="AI_Metrics", rows=1000, cols=20)
        worksheet.append_row(row_data)
        
        logger.info(f"Exported metrics to Google Sheets: {timestamp}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to export to Google Sheets: {e}")
        return False

# ── Telegram Notifications ─────────────────────────────────────────────────

def send_telegram_notification(message: str) -> bool:
    """Send notification via Telegram."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram bot token or chat ID not configured")
        return False
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
        }
        
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        
        logger.info(f"Sent Telegram notification: {message[:50]}...")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send Telegram notification: {e}")
        return False

# ── Endpoints ──────────────────────────────────────────────────────────────

@app.route("/ai-metrics", methods=["GET"])
def ai_metrics_dashboard():
    """Main AI metrics dashboard page."""
    metrics = get_combined_metrics()
    
    # HTML template for the dashboard
    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>D2M AI Metrics Dashboard — Dreams2Memories Travel</title>
        <style>
            :root {
                --navy: #0d1b2e;
                --navy2: #152540;
                --navy3: #1e3358;
                --gold: #c9a84c;
                --gold-light: #e8c97a;
                --white: #f0f0f0;
                --red: #e74c3c;
                --orange: #f39c12;
                --yellow: #f1c40f;
                --green: #27ae60;
                --blue: #3498db;
            }
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: var(--navy);
                color: var(--white);
                line-height: 1.6;
                padding: 20px;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
            }
            header {
                text-align: center;
                margin-bottom: 40px;
                padding-bottom: 20px;
                border-bottom: 2px solid var(--gold);
            }
            h1 {
                color: var(--gold);
                font-size: 2.5rem;
                margin-bottom: 10px;
            }
            .subtitle {
                color: var(--gold-light);
                font-size: 1.2rem;
                opacity: 0.9;
            }
            .timestamp {
                color: var(--white);
                font-size: 0.9rem;
                opacity: 0.7;
                margin-top: 10px;
            }
            .dashboard-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
                gap: 25px;
                margin-bottom: 40px;
            }
            .card {
                background: var(--navy2);
                border-radius: 10px;
                padding: 25px;
                box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
                border: 1px solid var(--navy3);
                transition: transform 0.2s;
            }
            .card:hover {
                transform: translateY(-5px);
                border-color: var(--gold);
            }
            .card-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 20px;
                padding-bottom: 15px;
                border-bottom: 1px solid var(--navy3);
            }
            .card-title {
                font-size: 1.4rem;
                color: var(--gold-light);
            }
            .status-badge {
                padding: 5px 15px;
                border-radius: 20px;
                font-weight: bold;
                font-size: 0.9rem;
            }
            .status-green { background: var(--green); }
            .status-yellow { background: var(--yellow); color: #000; }
            .status-red { background: var(--red); }
            .status-blue { background: var(--blue); }
            .metric-row {
                display: flex;
                justify-content: space-between;
                margin-bottom: 12px;
                padding: 8px 0;
                border-bottom: 1px dotted var(--navy3);
            }
            .metric-label {
                color: var(--white);
                opacity: 0.9;
            }
            .metric-value {
                font-weight: bold;
                color: var(--gold);
            }
            .progress-bar {
                height: 10px;
                background: var(--navy3);
                border-radius: 5px;
                margin: 15px 0;
                overflow: hidden;
            }
            .progress-fill {
                height: 100%;
                border-radius: 5px;
                transition: width 0.5s ease;
            }
            .fill-green { background: var(--green); }
            .fill-yellow { background: var(--yellow); }
            .fill-red { background: var(--red); }
            .fill-blue { background: var(--blue); }
            .actions {
                display: flex;
                gap: 15px;
                margin-top: 30px;
                justify-content: center;
            }
            .btn {
                padding: 12px 25px;
                background: var(--navy3);
                color: var(--white);
                border: 1px solid var(--gold);
                border-radius: 5px;
                text-decoration: none;
                font-weight: bold;
                transition: all 0.2s;
            }
            .btn:hover {
                background: var(--gold);
                color: var(--navy);
            }
            footer {
                text-align: center;
                margin-top: 50px;
                padding-top: 20px;
                border-top: 1px solid var(--navy3);
                color: var(--white);
                opacity: 0.7;
                font-size: 0.9rem;
            }
            .error {
                color: var(--red);
                background: rgba(231, 76, 60, 0.1);
                padding: 15px;
                border-radius: 5px;
                border: 1px solid var(--red);
                margin: 20px 0;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>🚀 D2M AI Metrics Dashboard</h1>
                <div class="subtitle">Real-time Claude Usage + OpenRouter Activity Tracking</div>
                <div class="timestamp">Last updated: {{ metrics.timestamp }}</div>
            </header>
            
            {% if metrics.claude.error or metrics.openrouter.error %}
                <div class="error">
                    <h3>⚠️ Data Collection Errors</h3>
                    {% if metrics.claude.error %}
                        <p><strong>Claude:</strong> {{ metrics.claude.error }}</p>
                    {% endif %}
                    {% if metrics.openrouter.error %}
                        <p><strong>OpenRouter:</strong> {{ metrics.openrouter.error }}</p>
                    {% endif %}
                </div>
            {% endif %}
            
            <div class="dashboard-grid">
                <!-- Operational Metrics Card -->
                <div class="card">
                    <div class="card-header">
                        <div class="card-title">🏢 Operational Metrics</div>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">Commander Satisfaction</span>
                        <span class="metric-value">{{ metrics.operational.commander_satisfaction }}/10</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">Staff Morale</span>
                        <span class="metric-value">{{ metrics.operational.staff_morale }}/10</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">Open Dossiers</span>
                        <span class="metric-value">{{ metrics.operational.client_operational_stats.open_dossiers }}</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">Deadlines (30d)</span>
                        <span class="metric-value">{{ metrics.operational.client_operational_stats.upcoming_deadlines_30d }}</span>
                    </div>
                </div>

                <!-- Summary Card -->
                <div class="card">
                    <div class="card-header">
                        <div class="card-title">📊 Summary</div>
                        <div class="status-badge status-{{ metrics.summary.budget_status.lower() if metrics.summary.budget_status != 'UNKNOWN' else 'blue' }}">
                            {{ metrics.summary.budget_status }}
                        </div>
                    </div>
                    
                    <div class="metric-row">
                        <span class="metric-label">Total Messages Today</span>
                        <span class="metric-value">{{ metrics.summary.total_messages_today }}</span>
                    </div>
                    
                    <div class="metric-row">
                        <span class="metric-label">Total Cost Today</span>
                        <span class="metric-value">${{ "%.2f"|format(metrics.summary.total_cost_today) }}</span>
                    </div>
                    
                    <div class="metric-row">
                        <span class="metric-label">Cost per Message</span>
                        <span class="metric-value">${{ "%.4f"|format(metrics.summary.cost_per_message) }}</span>
                    </div>
                    
                    <div class="metric-row">
                        <span class="metric-label">Free Tier Status</span>
                        <span class="metric-value">{{ "✅ Active" if metrics.summary.is_free_tier else "❌ Not Active" }}</span>
                    </div>
                </div>
                
                <!-- Claude Usage Card -->
                <div class="card">
                    <div class="card-header">
                        <div class="card-title">🤖 Claude Usage</div>
                        <div class="status-badge status-{{ metrics.claude.budget_status.lower() if 'budget_status' in metrics.claude else 'blue' }}">
                            {{ metrics.claude.budget_status if 'budget_status' in metrics.claude else 'ACTIVE' }}
                        </div>
                    </div>
                    
                    <div class="metric-row">
                        <span class="metric-label">Session Usage</span>
                        <span class="metric-value">{{ metrics.claude.session.percentage if 'session' in metrics.claude else 0 }}%</span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill fill-{{ 'green' if metrics.claude.session.percentage < 60 else 'yellow' if metrics.claude.session.percentage < 80 else 'red' if 'session' in metrics.claude else 'blue' }}" 
                             style="width: {{ metrics.claude.session.percentage if 'session' in metrics.claude else 0 }}%"></div>
                    </div>
                    
                    <div class="metric-row">
                        <span class="metric-label">Weekly Usage</span>
                        <span class="metric-value">{{ metrics.claude.weekly.percentage if 'weekly' in metrics.claude else 0 }}%</span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill fill-{{ 'green' if metrics.claude.weekly.percentage < 60 else 'yellow' if metrics.claude.weekly.percentage < 80 else 'red' if 'weekly' in metrics.claude else 'blue' }}" 
                             style="width: {{ metrics.claude.weekly.percentage if 'weekly' in metrics.claude else 0 }}%"></div>
                    </div>
                    
                    <div class="metric-row">
                        <span class="metric-label">Sonnet Daily</span>
                        <span class="metric-value">{{ metrics.claude.sonnet_daily.percentage if 'sonnet_daily' in metrics.claude else 0 }}%</span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill fill-{{ 'green' if metrics.claude.sonnet_daily.percentage < 70 else 'yellow' if metrics.claude.sonnet_daily.percentage < 90 else 'red' if 'sonnet_daily' in metrics.claude else 'blue' }}" 
                             style="width: {{ metrics.claude.sonnet_daily.percentage if 'sonnet_daily' in metrics.claude else 0 }}%"></div>
                    </div>
                    
                    <div class="metric-row">
                        <span class="metric-label">Last Message</span>
                        <span class="metric-value">{{ metrics.claude.last_message_at[:16] if metrics.claude.last_message_at else 'Never' }}</span>
                    </div>
                </div>
                
                <!-- OpenRouter Card -->
                <div class="card">
                    <div class="card-header">
                        <div class="card-title">🌐 OpenRouter Activity</div>
                        <div class="status-badge status-{{ 'green' if metrics.openrouter.usage.daily_usd < 2 else 'yellow' if metrics.openrouter.usage.daily_usd < 5 else 'red' if 'usage' in metrics.openrouter else 'blue' }}">
                            ${{ "%.2f"|format(metrics.openrouter.usage.daily_usd) if 'usage' in metrics.openrouter else '?' }}
                        </div>
                    </div>
                    
                    <div class="metric-row">
                        <span class="metric-label">Daily Cost</span>
                        <span class="metric-value">${{ "%.2f"|format(metrics.openrouter.usage.daily_usd) if 'usage' in metrics.openrouter else '0.00' }}</span>
                    </div>
                    
                    <div class="metric-row">
                        <span class="metric-label">Monthly Cost</span>
                        <span class="metric-value">${{ "%.2f"|format(metrics.openrouter.usage.monthly_usd) if 'usage' in metrics.openrouter else '0.00' }}</span>
                    </div>
                    
                    <div class="metric-row">
                        <span class="metric-label">Credits Remaining</span>
                        <span class="metric-value">${{ "%.2f"|format(metrics.openrouter.credits.remaining) if 'credits' in metrics.openrouter else '0.00' }}</span>
                    </div>
                    
                    <div class="metric-row">
                        <span class="metric-label">Free Tier</span>
                        <span class="metric-value">{{ "✅ Yes" if metrics.openrouter.usage.is_free_tier else "❌ No" if 'usage' in metrics.openrouter else 'Unknown' }}</span>
                    </div>
                    
                    <div class="metric-row">
                        <span class="metric-label">Models Tracked</span>
                        <span class="metric-value">{{ metrics.openrouter.models_used if 'models_used' in metrics.openrouter else 0 }}</span>
                    </div>
                </div>
                
                <!-- Sources Breakdown Card -->
                <div class="card">
                    <div class="card-header">
                        <div class="card-title">📋 Message Sources</div>
                        <div class="status-badge status-blue">
                            {{ metrics.claude.sources.values()|sum if 'sources' in metrics.claude else 0 }} total
                        </div>
                    </div>
                    
                    {% if 'sources' in metrics.claude %}
                        {% for source, count in metrics.claude.sources.items() %}
                            <div class="metric-row">
                                <span class="metric-label">{{ source|title }}</span>
                                <span class="metric-value">{{ count }}</span>
                            </div>
                            <div class="progress-bar">
                                {% set total = metrics.claude.sources.values()|sum %}
                                {% set pct = (count / total * 100) if total > 0 else 0 %}
                                <div class="progress-fill fill-blue" style="width: {{ pct }}%"></div>
                            </div>
                        {% endfor %}
                    {% else %}
                        <div class="metric-row">
                            <span class="metric-label">No source data available</span>
                            <span class="metric-value">—</span>
                        </div>
                    {% endif %}
                </div>
            </div>
            
            <div class="actions">
                <a href="/ai-metrics/json" class="btn" target="_blank">📊 JSON API</a>
                <a href="/ai-metrics/export" class="btn">📤 Export to Looker Studio</a>
                <a href="/ai-metrics/refresh" class="btn">🔄 Refresh Data</a>
                <a href="/dashboard" class="btn">🏠 Main Dashboard</a>
            </div>
            
                <footer>
                <p>Dreams2Memories Travel, LLC — AI Metrics Dashboard v1.0</p>
                <p>Looker Studio Integration Ready • Telegram Notifications Enabled</p>
                <p>Dashboard URL: <code>https://datastudio.google.com/u/0/reporting/8a4737e8-2759-4684-8dff-fb519be8f371/page/WSxnF/edit</code></p>
            </footer>
        </div>
        
        <script>
            // Auto-refresh every 60 seconds
            setTimeout(() => {
                window.location.reload();
            }, 60000);
            
            // Add click handlers for export buttons
            document.addEventListener('DOMContentLoaded', function() {
                const exportBtn = document.querySelector('a[href="/ai-metrics/export"]');
                if (exportBtn) {
                    exportBtn.addEventListener('click', function(e) {
                        e.preventDefault();
                        fetch('/ai-metrics/export', { method: 'POST' })
                            .then(response => response.json())
                            .then(data => {
                                if (data.success) {
                                    alert('✅ Metrics exported to Looker Studio!');
                                } else {
                                    alert('❌ Export failed: ' + data.message);
                                }
                            })
                            .catch(error => {
                                alert('❌ Export error: ' + error);
                            });
                    });
                }
            });
        </script>
    </body>
    </html>
    """
    
    return render_template_string(html_template, metrics=metrics)

@app.route("/ai-metrics/json", methods=["GET"])
def ai_metrics_json():
    """JSON API endpoint for AI metrics."""
    metrics = get_combined_metrics()
    return jsonify(metrics)

@app.route("/ai-metrics/export", methods=["POST"])
def ai_metrics_export():
    """Export metrics to Google Sheets for Looker Studio."""
    metrics = get_combined_metrics()
    success = export_to_google_sheets(metrics)
    
    if success:
        # Send Telegram notification
        message = f"""🚀 <b>AI Metrics Dashboard Update</b>

📊 <b>Claude Usage:</b> {metrics['claude']['session']['percentage']}% of session limit
💰 <b>OpenRouter Cost:</b> ${metrics['openrouter']['usage']['daily_usd']:.2f} today
📈 <b>Messages:</b> {metrics['summary']['total_messages_today']} total
🎯 <b>Status:</b> {metrics['summary']['budget_status']}

✅ <i>Data exported to Looker Studio</i>
📅 {datetime.now().strftime('%Y-%m-%d %H:%M MT')}"""
        

    return jsonify({
        "success": success,
        "message": "Exported to Google Sheets for Looker Studio" if success else "Export failed",
        "timestamp": metrics["timestamp"],
    })

@app.route("/ai-metrics/refresh", methods=["GET"])
def ai_metrics_refresh():
    """Force refresh of metrics data."""
    metrics = get_combined_metrics()
    
    return jsonify({
        "success": True,
        "message": "Metrics refreshed",
        "timestamp": metrics["timestamp"],
    })

@app.route("/")
def index():
    """Redirect to AI metrics dashboard."""
    return '<script>window.location.href = "/ai-metrics";</script>'

# ── Main Entry Point ───────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Thunderbird AI Metrics Dashboard")
    parser.add_argument("--port", type=int, default=8767, help="Port to run on (default: 8767)")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--export", action="store_true", help="Export to Google Sheets and exit")
    
    args = parser.parse_args()
    
    if args.export:
        # Export-only mode
        logger.info("Running export-only mode for Looker Studio")
        metrics = get_combined_metrics()
        success = export_to_google_sheets(metrics)
        
        if success:
            logger.info(f"✅ Successfully exported metrics to Google Sheets: {metrics['timestamp']}")
            # Green export = silent. Picked up in AM brief. No D2MC2C page.
        else:
            logger.error("❌ Failed to export metrics to Google Sheets")
            send_telegram_notification("🔴 AI Metrics export FAILED — check Google Sheets auth")
        
        sys.exit(0 if success else 1)
    
    # Start Flask server
    logger.info(f"Starting AI Metrics Dashboard on {args.host}:{args.port}")
    logger.info(f"Looker Studio URL: https://datastudio.google.com/u/0/reporting/8a4737e8-2759-4684-8dff-fb519be8f371/page/WSxnF/edit")
    
    app.run(host=args.host, port=args.port, debug=args.debug)

if __name__ == "__main__":
    main()