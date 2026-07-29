"""
image_selector_cli.py — CLI Image Sourcing & Gallery Selector
Dreams2Memories Travel, LLC | Thunderbird Wing
"""

import os
import sys
import urllib.request
import urllib.parse
import json

PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")

def fetch_pexels_choices(query: str, per_page: int = 3) -> list:
    """Fetch multiple photo options from Pexels API matching the query."""
    encoded_q = urllib.parse.quote(query)
    url = f"https://api.pexels.com/v1/search?query={encoded_q}&per_page={per_page}"
    try:
        req = urllib.request.Request(url, headers={
            "Authorization": PEXELS_API_KEY,
            "User-Agent": "Mozilla/5.0"
        })
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return [photo["src"]["large2x"] for photo in data.get("photos", [])]
    except Exception as e:
        print(f"Error fetching from Pexels: {e}")
        return []

def generate_html_selector(query: str, images: list, output_path: str = "/home/john/Thunderbird/cruises_web/image_options.html"):
    """Generate a simple, responsive HTML page to view options side-by-side."""
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Select Image for: {query}</title>
    <style>
        body {{ font-family: sans-serif; background: #0c1524; color: #fff; text-align: center; padding: 20px; }}
        .grid {{ display: flex; justify-content: center; gap: 20px; flex-wrap: wrap; margin-top: 20px; }}
        .card {{ background: #1b263b; border-radius: 8px; padding: 10px; width: 300px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }}
        img {{ width: 100%; height: 200px; object-fit: cover; border-radius: 4px; }}
        .url {{ font-size: 10px; color: #a8c8ff; word-break: break-all; margin: 10px 0; }}
        button {{ background: #c8a400; border: none; padding: 8px 16px; color: #000; font-weight: bold; cursor: pointer; border-radius: 4px; }}
        button:hover {{ background: #f0e040; }}
    </style>
</head>
<body>
    <h1>Select Image Options for query: <i>"{query}"</i></h1>
    <div class="grid">
    """
    for idx, img in enumerate(images):
        html_content += f"""
        <div class="card">
            <h3>Option {idx + 1}</h3>
            <img src="{img}" alt="Option {idx + 1}">
            <div class="url">{img}</div>
            <button onclick="navigator.clipboard.writeText('{img}'); alert('Copied option {idx + 1} URL to clipboard!');">Copy URL</button>
        </div>
        """
    html_content += """
    </div>
</body>
</html>
"""
    with open(output_path, "w") as f:
        f.write(html_content)
    print(f"Generated HTML selector gallery at: {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 image_selector_cli.py <search_query>")
        sys.exit(1)
        
    query = " ".join(sys.argv[1:])
    print(f"Searching Pexels for alternatives for '{query}'...")
    choices = fetch_pexels_choices(query)
    if not choices:
        print("No image options found.")
    else:
        generate_html_selector(query, choices)
