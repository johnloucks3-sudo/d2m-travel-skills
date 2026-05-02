from playwright.sync_api import sync_playwright

def test_mozio_link(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        print(f"Navigating to {url}...")
        try:
            page.goto(url, wait_until="networkidle", timeout=20000)
            print(f"Page title: {page.title()}")
            print(f"Final URL: {page.url}")
        except Exception as e:
            print(f"Error accessing Mozio: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    test_mozio_link("https://mozio.linkro24.com/?gad_source=1&gad_campaignid=23391719015&gbraid=0AAAABAp6VpCsPrPMpWpozCkbGVv9QZvES&gclid=CjwKCAjwntHPBhAaEiwA_Xp6RtSd5pkD-Sm-k_R1sa2O292t7vfi_ZHMBJJRqHT-ucEu8B02ieE93hoCa2AQAvD_BwE")
