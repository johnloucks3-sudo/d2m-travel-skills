#!/usr/bin/env node
// One-off probe: capture network requests during a United one-way search
// to find the internal fare-search JSON/XHR endpoint (more robust than DOM scrape).
import { launch } from 'cloakbrowser';

const url = process.argv[2] || "https://www.united.com/en/us/fsr/choose-flights?f=DEN&t=ORD&d=2026-08-15&tt=1&sc=7&px=1&taxng=1&idx=1";

let browser;
const apiCalls = [];
try {
  browser = await launch({ headless: true, humanize: true });
  const page = await browser.newPage();
  page.on('response', async (resp) => {
    try {
      const req = resp.request();
      const rurl = req.url();
      const ct = resp.headers()['content-type'] || '';
      if (ct.includes('json') && !rurl.includes('.js') && (rurl.includes('fsr') || rurl.includes('search') || rurl.includes('flight') || rurl.includes('fare') || rurl.includes('graphql') || rurl.includes('api'))) {
        let bodySnippet = '';
        try {
          const body = await resp.text();
          bodySnippet = body.slice(0, 300);
        } catch (_) {}
        apiCalls.push({ url: rurl, method: req.method(), status: resp.status(), contentType: ct, bodySnippet });
      }
    } catch (_) {}
  });
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(15000); // let AJAX settle
  console.log(JSON.stringify(apiCalls, null, 2));
} catch (err) {
  console.error('error:', err.message);
} finally {
  if (browser) await browser.close();
}
