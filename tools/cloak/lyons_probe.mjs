import { launch } from 'cloakbrowser';
let browser;
try {
  browser = await launch({ headless: true, humanize: true });
  const page = await browser.newPage();
  const resp = await page.goto('https://www.rssc.com/sign-in', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(5000);
  process.stderr.write('HTTP ' + (resp && resp.status ? resp.status() : '?') + ' | title: ' + (await page.title()) + ' | url: ' + page.url() + '\n');
  const fields = await page.evaluate(() => {
    const out = [];
    document.querySelectorAll('input,button,form,a[href*=sign],a[href*=login],a[href*=account]').forEach(el => {
      out.push({tag: el.tagName, type: el.type||'', id: el.id||'', name: el.name||'', ph: el.placeholder||'', txt: (el.innerText||el.value||'').slice(0,40), href: (el.href||'').slice(0,80)});
    });
    return out;
  });
  console.log(JSON.stringify(fields, null, 1));
  await page.screenshot({ path: '/home/john/Thunderbird/validations/lyons_regent/01_signin.png' });
  process.exit(0);
} catch (e) { process.stderr.write('ERR ' + e.message + '\n'); process.exit(1); }
finally { if (browser) try { await browser.close(); } catch(_){} }
