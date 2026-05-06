from core.travel.thunderbird_fare_watch import check_fare
import json

# Simulated check - in reality, this would pull from the web search tool
# I am checking the watches at the current baseline
print(json.dumps(check_fare("furlow-grandeur-scandinavia-cruise", 9618.0), indent=2))
print(json.dumps(check_fare("nichols-grandeur-scandinavia-cruise", 9448.0), indent=2))
print(json.dumps(check_fare("ely-darrow-grandeur-scandinavia-cruise", 10320.0), indent=2))
