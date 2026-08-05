import sys
sys.path.insert(0, '.')
from tcd.collectors import collect_all
items = collect_all(include_gmail=False,include_keep=False,include_sms=False)
p_items = [i for i in items if getattr(i, 'stage', None) == 'P']
print("=== P ITEMS ===")
print("Total P items:", len(p_items))
for i in p_items:
    print(getattr(i, 'id', getattr(i, 'title', 'unknown')), "|", getattr(i, 'type', ''))

d_items = [i for i in items if getattr(i, 'stage', None) == 'D']
print("\n=== D ITEMS (Top 3) ===")
for i in d_items[:3]:
    print(f"ID: {getattr(i, 'id', '')}, Criteria: {getattr(i, 'completion_criteria', getattr(i, 'criteria', ''))}")
