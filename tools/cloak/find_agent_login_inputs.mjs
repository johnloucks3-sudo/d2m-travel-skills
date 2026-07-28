import { launch } from 'cloakbrowser';

async function run() {
  console.log("Launching CloakBrowser to find login inputs...");
  let browser;
  try {
    browser = await launch({ headless: true, humanize: true });
    const page = await browser.newPage();
    
    await page.goto("https://www.rssc.com/agent/default.aspx", { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(5000);
    
    // Accept cookies
    try {
      await page.click('#onetrust-accept-btn-handler', { timeout: 3000 });
    } catch(_) {}
    
    const fields = await page.evaluate(() => {
      const inputs = [...document.querySelectorAll('input')].map(i => ({
        id: i.id,
        name: i.name,
        type: i.type,
        placeholder: i.placeholder,
        value: i.value,
        outerHTML: i.outerHTML
      }));
      return inputs;
    });
    
    console.log("ALL INPUT FIELDS:");
    for (const f of fields) {
      if (f.type !== 'hidden') {
        console.log(`- Type: ${f.type} | ID: ${f.id} | Name: ${f.name} | Placeholder: ${f.placeholder}`);
        console.log(`  HTML: ${f.outerHTML}`);
      }
    }
    
  } catch (err) {
    console.error("Error:", err);
  } finally {
    if (browser) await browser.close();
  }
}

run();
