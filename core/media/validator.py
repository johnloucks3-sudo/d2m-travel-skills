"""
validator.py — Automated Itinerary Media Link Validator & Fallback
Dreams2Memories Travel, LLC | Thunderbird Wing
"""

import os
import urllib.request
import urllib.parse
import json

PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")

def verify_url(url: str) -> bool:
    """Check if a URL is active by issuing a HEAD request with custom User-Agent."""
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=2.5) as resp:
            return resp.status == 200
    except Exception:
        return False

def get_pexels_fallback(query: str) -> str:
    """Fetch the first high-res photo URL from Pexels API matching the query."""
    encoded_q = urllib.parse.quote(query)
    url = f"https://api.pexels.com/v1/search?query={encoded_q}&per_page=1"
    try:
        req = urllib.request.Request(url, headers={
            "Authorization": PEXELS_API_KEY,
            "User-Agent": "Mozilla/5.0"
        })
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("photos"):
                return data["photos"][0]["src"]["large2x"]
    except Exception as e:
        print(f"Pexels fallback query failed for '{query}': {e}")
    # Return a generic luxury cruise/travel fallback if Pexels fails
    return "https://images.pexels.com/photos/32609062/pexels-photo-32609062.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940"

def validate_media_dict(media_dict: dict, search_queries: dict) -> dict:
    """Validate all URLs in a media dictionary. Automatically resolves fallback on failure."""
    validated = {}
    for key, url in media_dict.items():
        print(f"Checking media asset '{key}'...")
        if verify_url(url):
            validated[key] = url
        else:
            query = search_queries.get(key, key.replace("_", " "))
            print(f"  --> Failed! Sourcing fallback for '{query}'...")
            validated[key] = get_pexels_fallback(query)
    return validated

if __name__ == "__main__":
    # Test execution
    test_dict = {
        "cannes": "https://images.unsplash.com/photo-1534008741893-c044df703c9c?auto=format&fit=crop&w=800&q=80", # broken unsplash
        "athens": "https://images.pexels.com/photos/36825391/pexels-photo-36825391.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940" # active pexels
    }
    queries = {
        "cannes": "cannes french riviera beach yachts",
        "athens": "athens acropolis"
    }
    res = validate_media_dict(test_dict, queries)
    print("Verification result:", json.dumps(res, indent=2))
