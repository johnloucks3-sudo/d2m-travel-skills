import * as fs from 'fs';

const html = fs.readFileSync('/home/john/Thunderbird/validations/rssc_scrape/agent_post_login.html', 'utf8');

// Use simple regex to extract links
const links = [];
const regex = /<a\s+[^>]*href=["']([^"']*)["'][^>]*>([\s\S]*?)<\/a>/gi;
let match;
while ((match = regex.exec(html)) !== null) {
  links.push({
    href: match[1],
    text: match[2].replace(/<[^>]*>/g, '').trim()
  });
}

console.log(`Found ${links.length} links on dashboard:`);
for (const l of links) {
  const textLower = l.text.toLowerCase();
  const hrefLower = l.href.toLowerCase();
  if (
    textLower.includes("book") || 
    textLower.includes("reserv") || 
    textLower.includes("account") ||
    textLower.includes("client") ||
    hrefLower.includes("book") || 
    hrefLower.includes("reserv") || 
    hrefLower.includes("account") ||
    hrefLower.includes("client") ||
    hrefLower.includes("agent")
  ) {
    console.log(`- Text: "${l.text}" | Href: ${l.href}`);
  }
}
