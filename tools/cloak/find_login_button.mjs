import { launch } from 'cloakbrowser';

async function run() {
  console.log("Launching CloakBrowser to locate agent login submit button...");
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
    
    const buttonDetails = await page.evaluate(() => {
      const emailInput = document.querySelector('#uxAgentHomePage_uxAgentRegister_uxLoginEmailAddressTextbox');
      if (!emailInput) return "Email input not found";
      
      const form = emailInput.closest('form');
      if (!form) return "Parent form not found";
      
      const buttons = [...form.querySelectorAll('button, input[type=submit], input[type=image], a.btn')].map(b => ({
        id: b.id,
        tagName: b.tagName,
        type: b.type,
        text: (b.innerText || b.value || '').trim(),
        outerHTML: b.outerHTML
      }));
      
      return {
        formId: form.id,
        formAction: form.action,
        buttons: buttons
      };
    });
    
    console.log("LOGIN FORM BUTTON DETAILS:");
    console.log(JSON.stringify(buttonDetails, null, 2));
    
  } catch (err) {
    console.error("Error:", err);
  } finally {
    if (browser) await browser.close();
  }
}

run();
