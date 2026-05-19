"""Build and dispatch the email classification prompt to Claude."""
import json
from pathlib import Path

# Load the email data
raw = json.load(open('/home/john/Thunderbird/output/johnloucks3_sent_emails_dec2025.json'))

# Build a targeted prompt with the structured summary + raw client emails
prompt_parts = []
prompt_parts.append("""# D2M Email Classification Analysis

You are analyzing 2,032 sent emails from johnloucks3@gmail.com (Dec 1, 2025 – May 17, 2026).

## THE D2M RE-ORG v1 HAT RACK

D2M is a 1-person luxury travel agency (Commander = John Loucks). These are hats he wears:

### HAT 1: DANI — Client Voice
- Warm, anticipatory travel advisor emails TO clients
- Booking confirmations, welcome emails, itinerary delivery, excursion recommendations, guest forms, insurance, pre-departure briefs, send-offs, post-voyage follow-ups
- Recipients: D2M clients (Kuklinski, Westbrook, Ely, Nichols, Furlow, etc.)
- Subject examples: "Welcome Aboard", "Your Panama Canal", "Flight Planning", "Excursion Options"

### HAT 2: DEMBE (A2) — Research Engine
- Research findings sent TO the Commander (johnloucks3@gmail.com or d2mconcierge)
- Airfare reports, hotel options, excursion research, dining intel, fare watches
- These are data products, not client-facing
- Subject examples: "Weekly Airfare", "Hotel Research", "Excursion Options — Cartagena"

### HAT 3: HARLAN (A9) — Cost Validation
- Cost analysis, price validation, commission tracking, payment confirmations
- Internal financial analysis, sent to Commander
- Subject examples: price comparisons, cost breakdowns

### HAT 4: HALE — Quality Gate / Ops
- Internal ops: preflight checks, system health, workflow coordination, batch run results
- Weekly ops reviews, status updates
- Subject examples: "Preflight Check", "System Status", "Batch Run Complete"

### HAT 5: STRATEGIC — On-Call (JET, TALON, CASTILLO, A10, REYES)
- Pricing tool fixes, vendor negotiations, partnership discussions, strategy, planning
- Subject examples: pricing tool debug, vendor contract, partnership discussion

### HAT 6: PERSONAL / SYSTEM
- Personal emails, newsletters, IFTTT triggers, Evernote syncs, automated notifications, bounce messages, spam, forwarding loops

## YOUR TASK

1. Classify each EMAIL CLUSTER below into one hat using the raw email data provided
2. Identify patterns and gaps in the hat rack model
3. Recommend additions, splits, or removals

## STRUCTURED SUMMARY OF ALL 2,032 EMAILS

""")

# Add the structured summary
summary = json.load(open('/home/john/Thunderbird/output/johnloucks3_email_summary_for_opus.json'))
prompt_parts.append(json.dumps(summary, indent=2))

prompt_parts.append("""

## RAW EMAILS — Grouped by Client

Below are ALL raw emails to known D2M clients, newest first, with subject, date, to, and snippet:

""")

# Add raw client emails
client_keywords = ['kuklinski', 'westbrook', 'ely', 'nichols', 'furlow', 'goddard', 'loucks']
for e in raw['emails']:
    to_lower = e.get('to', '').lower()
    subj_lower = e.get('subject', '').lower()
    # Include if it's a client-facing email, or a research/ops email
    is_reply = subj_lower.startswith('re:') or subj_lower.startswith('fwd:')
    is_short = len(e.get('snippet', '')) < 10 and is_reply
    
    # Always include client conversations
    include = any(c in to_lower for c in client_keywords)
    # Also include research reports and ops
    include = include or any(w in subj_lower for w in ['fare', 'airfare', 'excursion', 'hotel', 'research',
                                                         'preflight', 'status', 'report', 'weekly',
                                                         'payment', 'commission', 'cost', 'invoice',
                                                         'welcome', 'voyage', 'cruise', 'booking',
                                                         'insurance', 'guest', 'profile', 'form',
                                                         'validation', 'brief', 'embarkation',
                                                         'portal', 'dossier', 'lifecycle'])
    
    if include and not is_reply:
        prompt_parts.append(f"[{e['date'][:10]}] TO: {e['to'][:40]:<40} | {e.get('subject','')[:80]}")
        if e.get('snippet'):
            prompt_parts.append(f"  → {e['snippet'][:150]}")
        prompt_parts.append("")

prompt_parts.append("""
## RAW EMAILS — All to d2mconcierge / d2mluxury (internal workflow)

""")

# Add self-send/internal workflow emails
for e in raw['emails']:
    to_lower = e.get('to', '').lower()
    if 'd2mconcierge' in to_lower or 'd2mluxury' in to_lower or 'concierge@' in to_lower:
        prompt_parts.append(f"[{e['date'][:10]}] TO: {e['to'][:40]:<40} | {e.get('subject','')[:80]}")
        if e.get('snippet') and len(e['snippet']) > 10:
            prompt_parts.append(f"  → {e['snippet'][:150]}")
        prompt_parts.append("")

# Add non-client, non-self emails (the rest)
prompt_parts.append("""
## 50 SAMPLE — Other Significant Emails

""")

other_count = 0
for e in raw['emails']:
    to_lower = e.get('to', '').lower()
    is_client = any(c in to_lower for c in client_keywords)
    is_self = 'd2mconcierge' in to_lower or 'd2mluxury' in to_lower
    is_reply = e.get('subject','').startswith('Re:')
    is_system = 'ifttt' in to_lower or 'evernote' in to_lower
    
    if not is_client and not is_self and not is_reply and not is_system and other_count < 50:
        prompt_parts.append(f"[{e['date'][:10]}] TO: {e['to'][:40]:<40} | {e.get('subject','')[:80]}")
        if e.get('snippet') and len(e['snippet']) > 10:
            prompt_parts.append(f"  → {e['snippet'][:150]}")
        prompt_parts.append("")
        other_count += 1

prompt_parts.append("""

## OUTPUT INSTRUCTIONS

Return a structured analysis:

1. **HAT DISTRIBUTION**: Estimated % for each hat (DANI, DEMBE, HARLAN, HALE, STRATEGIC, PERSONAL/SYSTEM)
2. **CLIENT BREAKDOWN**: For each client (Kuklinski, Westbrook, etc.), which hats were worn and key dates
3. **GAPS**: What lifecycle stages or functions are missing from the current hat rack?
4. **RECOMMENDATIONS**: Should any hat be split, merged, added, or removed?
5. **HAT RACK v2**: Your proposed revised hat rack based on actual email patterns

Base your analysis on the actual email data provided above. Be specific.
""")

# Write the prompt
prompt_file = '/home/john/Thunderbird/output/opus_classification_prompt_v2.json'
with open(prompt_file, 'w') as f:
    f.write('\n'.join(prompt_parts))

import os
size = os.path.getsize(prompt_file)
print(f"Prompt file: {size} bytes ({size/1024:.0f} KB)")
