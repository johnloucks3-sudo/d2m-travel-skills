"""
simple_map_generator.py
Fallback map generation using Python visualization libraries
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from typing import List, Tuple


def generate_simple_route_map(
    coordinates: List[Tuple[float, float]], locations: List[str], title: str
) -> str:
    """
    Generate a simple route map using Python visualization
    """
    try:
        # Create a simple plot
        fig, ax = plt.subplots(figsize=(10, 8))

        # Extract latitudes and longitudes
        lats = [coord[0] for coord in coordinates]
        lons = [coord[1] for coord in coordinates]

        # Plot the route
        ax.plot(lons, lats, "b-", linewidth=2, alpha=0.7)
        ax.plot(lons, lats, "bo", markersize=8)

        # Add start and end markers
        ax.plot(lons[0], lats[0], "go", markersize=12, label="Start")
        ax.plot(lons[-1], lats[-1], "ro", markersize=12, label="End")

        # Add location labels
        for i, (lat, lon, location) in enumerate(zip(lats, lons, locations)):
            ax.annotate(
                location.split(",")[0],
                (lon, lat),
                xytext=(5, 5),
                textcoords="offset points",
                fontsize=8,
            )

        ax.set_title(title, fontsize=14)
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        ax.legend()
        ax.grid(True, alpha=0.3)

        # Save to file
        import os

        os.makedirs("/home/john/Thunderbird/storage/reverie/maps", exist_ok=True)

        safe_title = "".join(c for c in title if c.isalnum() or c in " -_").rstrip()
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"map_{safe_title}_{timestamp}.png"
        filepath = f"/home/john/Thunderbird/storage/reverie/maps/{filename}"

        plt.savefig(filepath, dpi=150, bbox_inches="tight")
        plt.close()

        print(f"Simple map generated: {filepath}")
        return filepath

    except Exception as e:
        print(f"Simple map generation failed: {e}")
        return None


def test_waikiki_simple_map():
    """Test with Waikiki locations"""
    coordinates = [
        (21.2814798, -157.8353909),  # Hale Koa Hotel
        (21.276847, -157.826791),  # Waikiki Beach
        (21.267500, -157.808400),  # Diamond Head
    ]

    locations = ["Hale Koa Hotel", "Waikiki Beach", "Diamond Head"]

    return generate_simple_route_map(
        coordinates, locations, "Waikiki Transportation Route"
    )


if __name__ == "__main__":
    test_waikiki_simple_map()
