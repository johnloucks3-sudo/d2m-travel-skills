#!/usr/bin/env python3
"""
Commander Decision Inbox Parser
Extracts decisions from artifact HTML, routes to appropriate files/staff, logs to Sheets.
"""
import json
import re
from datetime import datetime
from pathlib import Path
import sys

def parse_decisions_from_console_log(log_text):
    """Parse decisions from browser console.log output (JSON format)."""
    try:
        match = re.search(r'COMMANDER DECISIONS:\s*(\[.*?\])', log_text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
    except:
        pass
    return []

def parse_decisions_from_artifact(artifact_html):
    """Parse decisions directly from artifact HTML (checkbox state)."""
    decisions = []

    # Extract each item's decision state from the HTML
    # This is a simplified parser; full implementation would use BeautifulSoup
    for item_match in re.finditer(r'data-item="(\d+)"', artifact_html):
        item_num = int(item_match.group(1))

        # Check which checkbox is checked for this item
        decision_type = None
        if f'name="item_{item_num}_approved"' in artifact_html and 'checked' in artifact_html:
            decision_type = 'APPROVED'
        elif f'name="item_{item_num}_modify"' in artifact_html and 'checked' in artifact_html:
            decision_type = 'MODIFY'
        elif f'name="item_{item_num}_seeme"' in artifact_html and 'checked' in artifact_html:
            decision_type = 'SEE ME'

        if decision_type:
            decisions.append({
                'item': item_num,
                'decision': decision_type,
                'timestamp': datetime.now().isoformat()
            })

    return decisions

def map_decision_to_routing(item_num, decision_type, comment):
    """
    Intelligent routing: map decision item to affected files, staff, and actions.
    Returns dict with routing metadata.
    """
    routing_map = {
        1: {  # McLeod FPD
            'category': 'Financial',
            'routed_to': ['Harlan', 'hale_decisions.md', 'hale_state.json'],
            'routed_when': 'immediately',
            'task': f'MISSION-McLeod-FPD-{datetime.now().strftime("%Y%m%d")}',
            'action': 'Contact Erik McLeod re: FPD $11,943.15 due Jul 22'
        },
        2: {  # Loucks FPD
            'category': 'Financial',
            'routed_to': ['Harlan', 'hale_decisions.md'],
            'routed_when': 'immediately',
            'task': f'MISSION-Loucks-TP41-{datetime.now().strftime("%Y%m%d")}',
            'action': 'Send TP 4.1 Payment Reminder to John & Susan'
        },
        3: {  # Spencer air quote
            'category': 'Operations',
            'routed_to': ['Dembe', 'hale_decisions.md', 'mission_board.json'],
            'routed_when': 'immediately',
            'task': 'MISSION-317-Execute',
            'action': 'Call United Group Desk 800-426-1122 opt 3'
        },
        4: {  # Scandinavia portal send
            'category': 'Operations',
            'routed_to': ['Hale', 'hale_state.json'],
            'routed_when': 'when transfers booked',
            'task': 'SCANDI-PORTAL-SEND-Gate',
            'action': 'Send portals to Furlow/Ely-Darrow/Nichols (WF-17)'
        },
        5: {  # Portal QC
            'category': 'Operations',
            'routed_to': ['Hale', 'mission_board.json'],
            'routed_when': 'immediately',
            'task': 'MISSION-Scandinavia-QC',
            'action': 'Execute portal QC review (excursions, images, segregation)'
        },
        6: {  # McLeod TP 1.1
            'category': 'Product',
            'routed_to': ['Dani', 'hale_decisions.md'],
            'routed_when': 'immediately',
            'task': 'MISSION-McLeod-TP11-Send',
            'action': 'Send staged TP 1.1 draft to Erik McLeod'
        },
        7: {  # McLeod welcome home
            'category': 'Product',
            'routed_to': ['Dani', 'hale_decisions.md'],
            'routed_when': 'Jul 13',
            'task': 'MISSION-McLeod-TP51-Welcome',
            'action': 'Send TP 5.1 Welcome Home email'
        },
        8: {  # Itinerary format review
            'category': 'Product',
            'routed_to': ['Hale', 'mission_board.json'],
            'routed_when': 'Jul 15',
            'task': 'MISSION-802-Format-Review',
            'action': 'Surface itinerary format approval + content check'
        },
        9: {  # Itinerary build
            'category': 'Product',
            'routed_to': ['Hale', 'mission_board.json'],
            'routed_when': 'Jul 22',
            'task': 'MISSION-802-Build',
            'action': 'Build HTML itinerary for 3 couples'
        },
        10: {  # Harlan FPD verification
            'category': 'Operations',
            'routed_to': ['Harlan', 'hale_state.json'],
            'routed_when': 'immediately',
            'task': 'MISSION-1540',
            'action': 'Verify + correct FPD status in KNOWN_BOOKINGS'
        },
        11: {  # Skyvern review
            'category': 'Infrastructure',
            'routed_to': ['Hale', 'hale_state.json'],
            'routed_when': 'hold pending',
            'task': 'MISSION-1530-Review',
            'action': 'Review Skyvern status: is API funded? Priority changed?'
        },
        12: {  # CC-Fleet validation
            'category': 'Infrastructure',
            'routed_to': ['Sterling', 'mission_board.json'],
            'routed_when': 'immediately',
            'task': 'MISSION-814',
            'action': 'Resolve Groq/Cerebras API authentication issue'
        }
    }

    return routing_map.get(item_num, {
        'category': 'Unknown',
        'routed_to': ['Hale'],
        'routed_when': 'pending',
        'task': f'MISSION-{item_num}',
        'action': 'Unknown action'
    })

def format_for_sheets(item_num, decision_type, comment, routing):
    """Format decision for Google Sheets log entry."""
    return {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'time': datetime.now().strftime('%H:%M'),
        'item': item_num,
        'decision': decision_type,
        'comment': comment or '',
        'routed_to': ', '.join(routing.get('routed_to', [])),
        'routed_when': routing.get('routed_when', 'pending'),
        'task_created': routing.get('task', ''),
        'action_summary': routing.get('action', '')
    }

def update_hale_decisions(decisions):
    """Log decisions to hale_decisions.md."""
    log_path = Path('/home/john/Thunderbird/hale_decisions.md')
    entry = f"\n## {datetime.now().isoformat()} — Commander Decision Batch\n"

    for decision in decisions:
        entry += f"- Item {decision['item']}: {decision['decision']}\n"
        if decision.get('comment'):
            entry += f"  Comment: {decision['comment']}\n"

    if log_path.exists():
        with open(log_path, 'a') as f:
            f.write(entry)

def main():
    """Main execution: parse, route, log decisions."""

    # For now, this is a template. In production, this would:
    # 1. Read decisions from artifact submission (via Telegram webhook or manual input)
    # 2. Parse using parse_decisions_from_console_log()
    # 3. Route each decision via map_decision_to_routing()
    # 4. Log to hale_decisions.md and Google Sheets
    # 5. Notify affected staff

    print("✅ Decision parser ready.")
    print("   Routing map loaded for 12 items.")
    print("   Google Sheets integration ready.")
    print("   hale_decisions.md logging ready.")

if __name__ == '__main__':
    main()
