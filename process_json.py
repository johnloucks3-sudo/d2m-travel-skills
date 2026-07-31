import json

with open('tests/no_direct_sends_baseline.json', 'r') as f:
    d = json.load(f)

for key in ['gmail', 'telegram']:
    if key in d:
        new_list = []
        for v in d[key]:
            if 'worktrees' in v:
                continue
            if 'thunderbird_daily_brief.py' in v:
                continue
            if 'thunderbird_eod_brief.py' in v:
                continue
            if 'thunderbird_morning_briefing.py' in v:
                continue
            if 'morning_brief_engine.py' in v:
                continue
            if 'brief_email_sender.py' in v:
                continue
            new_list.append(v)
        d[key] = new_list

with open('tests/no_direct_sends_baseline.json', 'w') as f:
    json.dump(d, f, indent=1)
    f.write('\n')
