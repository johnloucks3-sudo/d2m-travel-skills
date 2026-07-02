#!/usr/bin/env node
// cloak_fetch.mjs — CloakBrowser stealth-fetch tier for Anansi escalation.
// Self-contained. Defeats Akamai/Imperva/Cloudflare where plain HTTP is walled.
// Usage: node cloak_fetch.mjs <url> [--output markdown|text|html] [--timeout ms]
// Exit 0 with content on stdout; non-zero on failure/empty.
import { launch } from 'cloakbrowser';

function arg(flag, def) {
  const i = process.argv.indexOf(flag);
  return i !== -1 && process.argv[i + 1] ? process.argv[i + 1] : def;
}

const url = process.argv[2];
if (!url || url.startsWith('--')) {
  process.stderr.write('usage: node cloak_fetch.mjs <url> [--output markdown|text|html] [--timeout ms]\n');
  process.exit(2);
}
const output = arg('--output', 'markdown');
const timeout = parseInt(arg('--timeout', '45000'), 10);

// Light HTML→Markdown: strip scripts/styles, collapse whitespace. Good enough for content extraction.
function htmlToMarkdown(html) {
  return html
    .replace(/<script[\s\S]*?<\/script>/gi, '')
    .replace(/<style[\s\S]*?<\/style>/gi, '')
    .replace(/<h([1-6])[^>]*>([\s\S]*?)<\/h\1>/gi, (_, n, t) => '\n' + '#'.repeat(+n) + ' ' + t.replace(/<[^>]+>/g, '').trim() + '\n')
    .replace(/<li[^>]*>([\s\S]*?)<\/li>/gi, (_, t) => '- ' + t.replace(/<[^>]+>/g, '').trim() + '\n')
    .replace(/<\/(p|div|br|tr)>/gi, '\n')
    .replace(/<[^>]+>/g, '')
    .replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&#39;/g, "'").replace(/&quot;/g, '"')
    .replace(/\n{3,}/g, '\n\n').replace(/[ \t]{2,}/g, ' ').trim();
}

let browser;
try {
  browser = await launch({ headless: true, humanize: true });
  const page = await browser.newPage();
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout });
  await page.waitForTimeout(3000);
  let content;
  if (output === 'html') {
    content = await page.content();
  } else if (output === 'text') {
    content = await page.evaluate(() => document.body ? document.body.innerText : '');
  } else {
    content = htmlToMarkdown(await page.content());
  }
  content = (content || '').trim();
  if (!content) { process.stderr.write('[cloak_fetch] empty content\n'); process.exit(1); }
  process.stdout.write(content + '\n');
  process.exit(0);
} catch (err) {
  process.stderr.write('[cloak_fetch] error: ' + (err && err.message ? err.message : String(err)) + '\n');
  process.exit(1);
} finally {
  if (browser) { try { await browser.close(); } catch (_) {} }
}
