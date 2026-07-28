import json

itinerary_path = "/home/john/Thunderbird/validations/lyons_regent/lyons_august_itinerary.json"
try:
    with open(itinerary_path, 'r') as f:
        data = json.load(f)
        
    print(data.keys())
    
except Exception as e:
    print(f"Error: {e}")
