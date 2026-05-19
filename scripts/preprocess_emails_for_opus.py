"""Pre-process sent emails: group by recipient, subject pattern, and date range.
Produces a compact summary for Opus classification."""
import json, re
from pathlib import Path
from collections import Counter, defaultdict

data = json.load(open('/home/john/Thunderbird/output/johnloucks3_sent_emails_dec2025.json'))
emails = data['emails']

# Group by recipient
recipient_groups = defaultdict(list)
for e in emails:
    to_field = e.get('to', '')
    for addr in to_field.split(','):
        addr_clean = addr.strip().lower()
        if addr_clean:
            recipient_groups[addr_clean].append(e)

# Known D2M client emails
CLIENT_DOMAINS = {'gmail.com', 'yahoo.com', 'icloud.com', 'outlook.com', 'hotmail.com', 'comcast.net'}
KNOWN_CLIENTS = {
    'kyle.kuklinski@gmail.com': 'Kuklinski',
    'roger.kuklinski@gmail.com': 'Kuklinski',
    'nikpack@gmail.com': 'Kuklinski',
    'rosalie.kuklinski@gmail.com': 'Kuklinski',
    'josh@jerichopix.com': 'Kuklinski',
    'buzzerica@gmail.com': 'Kuklinski',
    'rwestbrook3@gmail.com': 'Westbrook',
    'al.ely58@gmail.com': 'Ely',
    'heidi.nichols1@yahoo.com': 'Nichols',
    'larry.nichols4811@gmail.com': 'Nichols',
    'missy.furlow@gmail.com': 'Furlow',
    'susanna.loucks@gmail.com': 'Loucks (personal)',
    'cnuraptor@gmail.com': 'Justin',
}

# Build structured summary
summary = {
    "period": f"{emails[-1]['date'][:16]} to {emails[0]['date'][:16]}",
    "total_sent": len(emails),
    "by_recipient": {},
    "subject_patterns": defaultdict(list),
    "self_sends": [],
    "client_emails": [],
    "system_emails": [],
}

for addr, group in sorted(recipient_groups.items(), key=lambda x: -len(x[1])):
    if len(group) < 3:
        continue  # skip tiny groups
    
    # Determine category
    is_self = any(x in addr for x in ['johnloucks3', 'd2mconcierge', 'd2mluxury', 'concierge@'])
    is_known_client = addr in KNOWN_CLIENTS
    is_system = any(x in addr for x in ['trigger@applet.ifttt', 'evernote', 'noreply', 'no-reply'])
    
    subjects = [(e['date'][:16], e.get('subject', '')[:80], e.get('snippet', '')[:100]) for e in group[:20]]
    
    entry = {
        "recipient": addr,
        "count": len(group),
        "category": "CLIENT" if is_known_client else "SELF" if is_self else "SYSTEM" if is_system else "OTHER",
        "client_name": KNOWN_CLIENTS.get(addr, ""),
        "date_range": f"{group[-1]['date'][:10]} to {group[0]['date'][:10]}",
        "sample_subjects": subjects,
    }
    summary["by_recipient"][addr] = entry

# Build client email threads (grouped by client)
for client_addr, client_name in KNOWN_CLIENTS.items():
    if client_addr in recipient_groups:
        group = recipient_groups[client_addr]
        summary["client_emails"].append({
            "client": client_name,
            "address": client_addr,
            "count": len(group),
            "date_range": f"{group[-1]['date'][:10]} to {group[0]['date'][:10]}",
            "subjects": [(e['date'][:10], e.get('subject','')[:80]) for e in group],
        })

# Self-send pattern (internal workflow)
self_addrs = [a for a in recipient_groups if 'johnloucks3' in a or 'd2mconcierge' in a or 'concierge@d2m' in a]
for addr in self_addrs:
    group = recipient_groups[addr]
    summary["self_sends"].append({
        "from_to": addr,
        "count": len(group),
        "sample_subjects": [(e['date'][:10], e.get('subject','')[:80]) for e in group[:30]],
    })

# Subject line pattern analysis
subject_patterns = Counter()
for e in emails:
    s = e.get('subject', '')
    if 'Re:' in s:
        subject_patterns['REPLY'] += 1
    elif 'Fwd:' in s:
        subject_patterns['FORWARD'] += 1
    elif any(x in s.lower() for x in ['welcome', 'voyage', 'cruise', 'booking', 'travel']):
        subject_patterns['CLIENT_TRAVEL'] += 1
    elif any(x in s.lower() for x in ['fare', 'price', 'flight', 'hotel', 'excursion']):
        subject_patterns['RESEARCH'] += 1
    elif any(x in s.lower() for x in ['payment', 'invoice', 'paid', 'cost', 'commission']):
        subject_patterns['FINANCE'] += 1
    elif any(x in s.lower() for x in ['preflight', 'status', 'system', 'health', 'check']):
        subject_patterns['OPS'] += 1
    elif any(x in s.lower() for x in ['note', 'evernote', 'clip']):
        subject_patterns['NOTE_SYNC'] += 1
    elif any(x in s.lower() for x in ['ifttt', 'trigger', 'automation']):
        subject_patterns['AUTOMATION'] += 1
    else:
        subject_patterns['OTHER'] += 1

summary["subject_patterns"] = dict(subject_patterns.most_common())

# Save compact report
output_path = '/home/john/Thunderbird/output/johnloucks3_email_summary_for_opus.json'
with open(output_path, 'w') as f:
    json.dump(summary, f, indent=2, default=str)

import os
size = os.path.getsize(output_path)
print(f"Compact summary: {size} bytes ({size/1024:.0f} KB)")
print(f"Unique recipients analyzed: {len(summary['by_recipient'])}")
print(f"Clients with emails: {len(summary['client_emails'])}")
print(f"Subject pattern counts: {dict(subject_patterns.most_common())}")
