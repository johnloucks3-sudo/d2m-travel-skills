from core.travel.thunderbird_fare_watch import list_watches
import json
print(json.dumps(list_watches(active_only=True), indent=2))
