"""
map_generator.py
Free map generation for transportation routes, client itineraries, and location visualization
Integrated with Reverie storage and Hale COS oversight
"""

import os
import requests
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Load environment
load_dotenv(Path("/home/john/Thunderbird/.env"))


class MapGenerator:
    """Free map generation with Hale oversight integration"""

    def __init__(self):
        self.google_maps_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
        self.reverie_storage_path = "/home/john/Thunderbird/storage/reverie"

    def generate_transportation_map(
        self, locations: List[str], map_title: str
    ) -> Optional[str]:
        """
        Generate transportation route map with free Google Static Maps API

        Args:
            locations: List of addresses/locations in order
            map_title: Title for the map and filename

        Returns:
            Path to saved map image file, or None if failed
        """
        if not self.google_maps_key:
            print("Google Maps API key not configured")
            return None

        try:
            # Geocode each location
            coordinates = []
            for location in locations:
                coords = self._geocode_location(location)
                if coords:
                    coordinates.append(coords)

            if len(coordinates) < 2:
                print("Need at least 2 valid locations for route")
                return None

            # Generate map with route
            map_url = self._generate_static_map(coordinates, map_title)
            if not map_url:
                return None

            # Download and save to Reverie
            map_path = self._save_to_reverie(map_url, map_title)

            # Create Hale oversight report
            self._create_hale_oversight_report(map_title, locations, map_path)

            return map_path

        except Exception as e:
            print(f"Map generation failed: {e}")
            return None

    def _geocode_location(self, location: str) -> Optional[str]:
        """Geocode address to coordinates using free OpenStreetMap Nominatim"""
        # First try Google (if activated)
        if self.google_maps_key:
            url = f"https://maps.googleapis.com/maps/api/geocode/json"
            params = {"address": location, "key": self.google_maps_key}

            try:
                response = requests.get(url, params=params, timeout=10)
                data = response.json()

                if data["status"] == "OK" and data["results"]:
                    location = data["results"][0]["geometry"]["location"]
                    return f"{location['lat']},{location['lng']}"

            except Exception as e:
                print(f"Google geocoding failed: {e}")

        # Fallback to free OpenStreetMap Nominatim
        try:
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                "q": f"{location}, Hawaii",  # Add Hawaii for better accuracy
                "format": "json",
                "limit": 1,
            }

            return f"{url}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"

        except Exception as e:
            print(f"Free map generation failed: {e}")
            return None

    def _save_to_reverie(self, map_url: str, title: str) -> str:
        """Save generated map to Reverie storage"""
        try:
            # Download map image
            response = requests.get(map_url, timeout=15)
            response.raise_for_status()

            # Create filename
            safe_title = "".join(c for c in title if c.isalnum() or c in " -_").rstrip()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"map_{safe_title}_{timestamp}.png"
            filepath = os.path.join(self.reverie_storage_path, "maps", filename)

            # Ensure directory exists
            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            # Save file
            with open(filepath, "wb") as f:
                f.write(response.content)

            print(f"Map saved to Reverie: {filepath}")
            return filepath

        except Exception as e:
            print(f"Failed to save map to Reverie: {e}")
            raise

    def _create_hale_oversight_report(
        self, title: str, locations: List[str], map_path: str
    ):
        """Create Hale COS oversight report for DeepSeek-level review"""
        report = {
            "mission_type": "MAP_GENERATION",
            "title": title,
            "locations": locations,
            "map_path": map_path,
            "generated_at": datetime.now().isoformat(),
            "oversight_required": True,
            "oversight_level": "DEEPSEEK",
            "review_notes": "Automated map generation complete. Requires Hale COS quality review.",
        }

        report_path = os.path.join(
            self.reverie_storage_path,
            "reports",
            f"map_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        )
        os.makedirs(os.path.dirname(report_path), exist_ok=True)

        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        print(f"Hale oversight report created: {report_path}")

        # Also append to Hale's briefing
        self._append_to_hale_briefing(report)

    def _append_to_hale_briefing(self, report: Dict):
        """Append map generation to Hale's daily briefing"""
        briefing_path = "/home/john/Thunderbird/OpsCenter/hale_brief.md"
        entry = f"\n## 🗺️ Map Generation Completed\n- **Title**: {report['title']}\n- **Locations**: {', '.join(report['locations'])}"
        entry += f"\n- **Generated**: {report['generated_at']}\n- **Path**: {report['map_path']}\n"

        with open(briefing_path, "a") as f:
            f.write(entry)

        print(f"Added to Hale briefing: {briefing_path}")


def test_waikiki_map():
    """Test function for Waikiki near Hale Koa"""
    generator = MapGenerator()

    locations = [
        "Hale Koa Hotel, Waikiki",
        "Waikiki Beach",
        "Diamond Head State Monument",
        "Ala Moana Center, Honolulu",
    ]

    result = generator.generate_transportation_map(
        locations=locations, map_title="Waikiki Transportation Route near Hale Koa"
    )

    print(f"Map generation result: {result}")
    return result


if __name__ == "__main__":
    test_waikiki_map()
