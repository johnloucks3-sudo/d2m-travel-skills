import { launch } from 'cloakbrowser';

async function run() {
  console.log("Launching CloakBrowser to inspect agent login form...");
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
    
    // Dump form inputs
    const inputs = await page.evaluate(() => {
      const allInputs = [...document.querySelectorAll('input')].map(i => ({
        id: i.id,
        name: i.name,
        type: i.type,
        placeholder: i.placeholder,
        value: i.value,
        outerHTML: i.outerHTML.slice(0, 150)
      }));
      const buttons = [...document.querySelectorAll('button, input[type=submit]')].map(b => ({
        id: b.id,
        name: b.name,
        text: (b.innerText || b.value || '').trim(),
        outerHTML: b.outerHTML.slice(0, 150)
      }));
      const forms = [...document.querySelectorAll('form')].map(f => ({
        id: f.id,
        action: f.action,
        outerHTML: f.outerHTML.slice(0, 150)
      }));
      return { inputs, buttons, forms };
    });
    
    console.log("FORMS:");
    console.log(JSON.stringify(inputs.forms, null, 2));
    
    console.log("\nINPUTS:");
    console.log(JSON.stringify(inputs.inputs, null, 2));
    
    console.log("\nBUTTONS:");
    console.log(JSON.stringify(inputs.buttons, null, 2));
    
  } catch (err) {
    console.error("Error:", err);
  } finally {
    if (browser) await browser.close();
  }
}

run();
