# Commander Sig — D2M Signature Block Standard

Enforces the canonical Commander signature block for all client-facing D2M emails. Trigger on: "sig block", "commander signature", "check sig", "signature format", "sig block fix", "authorized by", "DREAMS2MEMORIES TRAVEL, LLC signature", or any request to fix, verify, or build the email footer.

**⚠️ UPDATED 2026-08-10 — colors only, wording unchanged.** Dark-navy retired for Academy Blue/Gold/White. Full sourcing: `~/.claude/skills/theme-factory/themes/usafa.md` (Claude Code path — read the file directly, you don't have the Skill tool).

**Background:** #002554 (Class Royal), flat fill — no gradient. Left edge: 4px solid #FFCE00 (Class Gold) rule. Padding: 18px 34px 24px 30px (30px left, inside the gold rule)
**Text:** Georgia, 13px, #dde4f0, line-height 1.75

**⚠️ NOTE — pre-existing mismatch found 2026-08-10, not introduced by this color update:** the actual production template (`storage/templates/d2m_canonical_darknavy.html`) has NEVER used "Authorized by: John A Loucks III" as a separate line, or "Owner" as its own line. It reads `John A Loucks III<br>Owner, Dreams2Memories, LLC<br>` — combined, no "Authorized by:" prefix. That's been true since before today's color redesign; this skill doc's wording rules (items 2-3 below) describe a format that doesn't match what's actually in the template. Flagging, not silently fixing — Commander should confirm which is correct before this skill doc's wording rules get trusted.

## Exact Format (top-to-bottom, colors current; wording per the mismatch note above)

1. **DREAMS2MEMORIES TRAVEL, LLC** — div wrapper: Georgia, 11px, bold, uppercase, color #a8bde0, letter-spacing 2px, margin-bottom 6px
2. **Authorized by: John A Loucks III** — `<br>` terminated *(see mismatch note — actual template just says "John A Loucks III")*
3. **Owner** — `<br>` terminated *(see mismatch note — actual template says "Owner, Dreams2Memories, LLC" combined)*
4. **719-291-0742** — `<a href="tel:7192910742">` link, color #dde4f0, no underline
5. **johnloucks3@gmail.com** — `<a href="mailto:johnloucks3@gmail.com">` link, color #8fb4ff, bold
6. **D2M logo** — `<img src="https://lh3.googleusercontent.com/d/1HYa61cNwcialWk64DimGwIfCAbUjESsu" width="96" height="71">`, margin-top 10px, display block

## Placement

After Dani's sig, separated by a 1px solid #B2B4B2 (Academy Grey) divider — flat line, no gradient.

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
