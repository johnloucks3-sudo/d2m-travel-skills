import json
import os
from playwright.sync_api import sync_playwright

# List of services to test
services = [
    ("Hotelbeds", "hotelbeds_credentials.json"),
    ("Centrav", "centrav_credentials.json"),
    ("GetYourGuide", "getyourguide_credentials.json"),
    ("Viator", "viator_credentials.json"),
    ("Mozio", "mozio_credentials.json"),
    ("Blacklane", "blacklane_credentials.json"),
]

def test_login(service_name, filename):
    filepath = os.path.join("/home/john/Thunderbird/creds/", filename)
    if not os.path.exists(filepath):
        # Fallback to checking root if not in creds/
        filepath = os.path.join("/home/john/Thunderbird/", filename)
        if not os.path.exists(filepath):
            print(f"{service_name}: File not found at {filename}")
            return

    with open(filepath, 'r') as f:
        data = json.load(f)
    
    print(f"Testing {service_name} login...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            if service_name == "Hotelbeds":
                page.goto(data.get("portal_url", "https://app.bedsonline.com"))
                page.fill("input[name='username']", data["portal_username"])
                page.fill("input[name='password']", data["portal_password"])
                page.click("button[type='submit']")
                page.wait_for_load_state("networkidle", timeout=10000)
                if "login" not in page.url:
                    print(f"{service_name}: Success")
                else:
                    print(f"{service_name}: Login failed (still on login page)")
            
            # Add other service login logic here based on their portal structures
            else:
                print(f"{service_name}: Login script not implemented for this service")
        
        except Exception as e:
            print(f"{service_name}: Error - {str(e)}")
        finally:
            browser.close()

if __name__ == "__main__":
    for service, file in services:
        test_login(service, file)
