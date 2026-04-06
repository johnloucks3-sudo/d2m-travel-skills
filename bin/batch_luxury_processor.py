import json
import time
from google import genai
from google.genai import types

# 2026 High-Efficiency Models
TEXT_MODEL = "gemini-2.5-flash"
IMAGE_MODEL = "gemini-2.5-flash"  # Unified on 2.5 Flash

client = genai.Client(api_key="YOUR_API_KEY")

def create_branding_cache(style_guide_text):
    """Caches branding instructions for a 90% input discount."""
    return client.caches.create(
        model=TEXT_MODEL,
        config=types.CreateCachedContentConfig(
            display_name="luxury_itinerary_style",
            system_instruction=style_guide_text,
            ttl="86400s" # 24-hour cache
        )
    )

def start_batch_image_job(ports_list):
    """Submits all port images at once for a 50% discount."""
    # Create JSONL for the Batch API
    requests = []
    for port in ports_list:
        req = {
            "request": {
                "contents": [{"parts": [{"text": f"Luxury travel photo of {port}, cinematic lighting"}]}]
            }
        }
        requests.append(req)

    with open("image_requests.jsonl", "w") as f:
        for r in requests:
            f.write(json.dumps(r) + "\n")

    # Upload and execute batch job
    uploaded_file = client.files.upload(file="image_requests.jsonl")
    batch_job = client.batches.create(
        model=IMAGE_MODEL,
        src=uploaded_file,
        config={"display_name": f"itinerary_images_{int(time.time())}"}
    )
    print(f"✅ Batch Job Created: {batch_job.name}")
    return batch_job.name
