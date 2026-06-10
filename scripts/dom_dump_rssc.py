import json, sys, time

from playwright.sync_api import sync_playwright

URL = "https://www.rssc.com/agent/default.aspx?ReturnUrl=%2fagent%2fdashboard%2f"

def dumper(page, label):
    """Attempt multiple evaluate calls, collecting whatever survives."""
    results = {}
    results["label"] = label

    # 1. title, url, readyState
    for key, expr in [
        ("title", "document.title"),
        ("url", "document.URL"),
        ("readyState", "document.readyState"),
    ]:
        try:
            results[key] = page.evaluate(expr)
        except Exception as e:
            results[key] = f"<ERROR: {e}>"

    # 2. inputs
    try:
        inputs = page.evaluate("""() => {
            return Array.from(document.querySelectorAll('input')).map(el => ({
                id: el.id || '',
                name: el.name || '',
                type: el.type || '',
                placeholder: el.placeholder || '',
                className: el.className || '',
                value: el.value || '',
                autocomplete: el.autocomplete || '',
            }));
        }""")
        results["inputs"] = inputs
    except Exception as e:
        results["inputs"] = f"<ERROR: {e}>"

    # 3. buttons
    try:
        buttons = page.evaluate("""() => {
            return Array.from(document.querySelectorAll('button')).map(el => ({
                id: el.id || '',
                type: el.type || '',
                innerText: (el.innerText || '').trim(),
                className: el.className || '',
            }));
        }""")
        results["buttons"] = buttons
    except Exception as e:
        results["buttons"] = f"<ERROR: {e}>"

    # 4. forms
    try:
        forms = page.evaluate("""() => {
            return Array.from(document.querySelectorAll('form')).map(el => ({
                id: el.id || '',
                action: el.action || '',
                method: el.method || '',
                className: el.className || '',
            }));
        }""")
        results["forms"] = forms
    except Exception as e:
        results["forms"] = f"<ERROR: {e}>"

    # 5. visible text (body innerText up to 3000 chars)
    try:
        text = page.evaluate("""() => {
            return (document.body ? document.body.innerText : '(no body)').substring(0, 3000);
        }""")
        results["visibleText"] = text
    except Exception as e:
        results["visibleText"] = f"<ERROR: {e}>"

    # 6. meta viewport / charset
    try:
        meta = page.evaluate("""() => {
            const vp = document.querySelector('meta[name=viewport]');
            const cs = document.querySelector('meta[charset]');
            return {
                viewport: vp ? vp.content : null,
                charset: cs ? cs.getAttribute('charset') : null,
            };
        }""")
        results["meta"] = meta
    except Exception as e:
        results["meta"] = f"<ERROR: {e}>"

    # 7. links
    try:
        links = page.evaluate("""() => {
            return Array.from(document.querySelectorAll('a')).slice(0, 20).map(el => ({
                href: el.href || '',
                text: (el.innerText || '').trim().substring(0, 80),
                id: el.id || '',
                className: el.className || '',
            }));
        }""")
        results["links"] = links
    except Exception as e:
        results["links"] = f"<ERROR: {e}>"

    # 8. script tags
    try:
        scripts = page.evaluate("""() => {
            return Array.from(document.querySelectorAll('script')).slice(0, 10).map(el => ({
                src: el.src || '(inline)',
                type: el.type || '',
                id: el.id || '',
            }));
        }""")
        results["scripts"] = scripts
    except Exception as e:
        results["scripts"] = f"<ERROR: {e}>"

    # 9. total DOM element count
    try:
        count = page.evaluate("document.querySelectorAll('*').length")
        results["domElementCount"] = count
    except Exception as e:
        results["domElementCount"] = f"<ERROR: {e}>"

    return results


def main():
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) "
                "Gecko/20100101 Firefox/128.0"
            ),
            viewport={"width": 1920, "height": 1080},
        )
        page = context.new_page()

        print("=" * 72)
        print("NAVIGATING TO:", URL)
        print("=" * 72)

        try:
            page.goto(URL, wait_until="commit", timeout=30000)
        except Exception as e:
            print(f"Navigation call raised: {e}")
            # continue — we might still have a page object with partial DOM

        time.sleep(1)

        # Dump 1 — immediately after navigation
        d1 = dumper(page, "DUMP 1 — ~1s after navigation start")
        dump = json.dumps(d1, indent=2, default=str)
        print(f"\n{dump}")

        time.sleep(2)

        # Dump 2 — 2s later
        d2 = dumper(page, "DUMP 2 — ~3s after navigation start")
        dump = json.dumps(d2, indent=2, default=str)
        print(f"\n{dump}")

        time.sleep(5)

        # Dump 3 — 5s later
        d3 = dumper(page, "DUMP 3 — ~8s after navigation start")
        dump = json.dumps(d3, indent=2, default=str)
        print(f"\n{dump}")

        browser.close()


if __name__ == "__main__":
    main()
