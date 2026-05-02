import json
from playwright.sync_api import sync_playwright

def inject_cookies(page, cookie_file):
    """Injects cookies into a playwright page context."""
    with open(cookie_file, 'r') as f:
        cookies = json.load(f)
        # Handle cases where cookies might be nested under a 'cookies' key
        if 'cookies' in cookies:
            cookies = cookies['cookies']
        
        # If it's a dict, convert to list of name/value
        if isinstance(cookies, dict):
            cookie_list = [{'name': k, 'value': v, 'domain': '.bedsonline.com', 'path': '/'} for k, v in cookies.items()]
        else:
            cookie_list = cookies
            
        page.context.add_cookies(cookie_list)
    print(f"Cookies injected from {cookie_file}")

def verify_session(cookie_file, target_url, dashboard_url):
    """Verifies session health by visiting a dashboard."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        # Go to target domain first to set context
        page.goto(target_url)
        inject_cookies(page, cookie_file)
        
        # Navigate to dashboard to verify
        page.goto(dashboard_url)
        page.wait_for_load_state("networkidle")
        
        # Check if still on dashboard (not redirected to login)
        if "login" not in page.url:
            print(f"Session valid: {page.url}")
            return True
        else:
            print(f"Session expired: {page.url}")
            return False

if __name__ == "__main__":
    # Test Hotelbeds/Bedsonline
    verify_session(
        cookie_file="/home/john/Thunderbird/hotelbeds_credentials.json", 
        target_url="https://app.bedsonline.com",
        dashboard_url="https://app.bedsonline.com/dashboard"
    )
