# Commander Sig — D2M Signature Block Standard

Enforces the canonical Commander signature block for all client-facing D2M emails. Trigger on: "sig block", "commander signature", "check sig", "signature format", "sig block fix", "authorized by", "DREAMS2MEMORIES TRAVEL, LLC signature", or any request to fix, verify, or build the email footer.

**Background:** #02022a · gradient: 180deg,#030338,#02021e · padding: 18px 34px 26px
**Text:** Georgia, 14px, #c8dcff, line-height 1.75

## Exact Format (top-to-bottom, every element mandatory)

1. **DREAMS2MEMORIES TRAVEL, LLC** — div wrapper: Georgia, 12px, bold, uppercase, color #a8c4f0, letter-spacing 2px, margin-bottom 6px
2. **Authorized by: John A Loucks III** — `<br>` terminated
3. **Owner** — `<br>` terminated
4. **719-291-0742** — `<a href="tel:7192910742">` link, color #c8dcff, no underline
5. **johnloucks3@gmail.com** — `<a href="mailto:johnloucks3@gmail.com">` link, color #7fb0ff, bold
6. **D2M logo** — `<img src="https://lh3.googleusercontent.com/d/1HYa61cNwcialWk64DimGwIfCAbUjESsu" width="96" height="71">`, margin-top 10px, display block

## Placement

After Dani's sig, separated by a 1px divider (90deg gradient from transparent through rgba(160,185,255,0.5) to transparent).

## Rules

- "Authorized by:" prefix is **mandatory** — all client emails are written by Dani/Concierge and authorized/sent by John
- "Owner" is a **separate line** — never combine with company name ("Owner, Dreams2Memories Travel, LLC" is wrong)
- "DREAMS2MEMORIES TRAVEL, LLC" is a **standalone brand line** — appears in BOTH Dani's sig AND Commander sig
- Phone uses `<a href="tel:...">` format, email uses `<a href="mailto:...">` format

## Diff Debugging

When told "check my sig block, you missed one":
1. Fetch the sent email's plain-text body via Gmail API
2. Compare against the template's HTML sig block line-by-line
3. Every line in the sent plain-text rendering must match a line in the template
4. Common misses: "Authorized by:" prefix, standalone company name line, "Owner" on its own line
