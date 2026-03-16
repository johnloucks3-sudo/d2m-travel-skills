# Cloudflare Email Routing + Gmail Send As Setup
## concierge@d2mluxury.quest -> johnloucks3@gmail.com
### Dreams2Memories Travel, LLC

---

## Step 1: Enable Cloudflare Email Routing

1. Log in to Cloudflare dashboard: https://dash.cloudflare.com
2. Select domain: **d2mluxury.quest**
3. Sidebar: **Email** > **Email Routing**
4. Click **Get Started** (or **Enable Email Routing** if not yet active)
5. Add destination address: `johnloucks3@gmail.com`
6. Cloudflare will send a verification email -- click the link in Gmail to confirm

## Step 2: Configure Catch-All Rule

1. In Email Routing > **Routing rules** tab
2. Set **Catch-all** rule:
   - Action: **Forward to**
   - Destination: `johnloucks3@gmail.com`
3. This ensures *@d2mluxury.quest all lands in your inbox

Optional: add specific rules before the catch-all for explicit routing:
- `concierge@d2mluxury.quest` -> `johnloucks3@gmail.com`
- `john@d2mluxury.quest` -> `johnloucks3@gmail.com`

Both are covered by the catch-all, but explicit rules make intent clear and survive catch-all changes.

## Step 3: DNS Records (Cloudflare auto-adds most, verify these exist)

### MX Records (Cloudflare adds automatically)
Cloudflare Email Routing auto-creates the required MX records. Verify they exist:
- `d2mluxury.quest MX isaac.mx.cloudflare.net 13`
- `d2mluxury.quest MX linda.mx.cloudflare.net 86`
- (or similar Cloudflare MX hostnames)

### SPF Record
Add or update the TXT record for `d2mluxury.quest`:
```
v=spf1 include:_spf.google.com include:_spf.mx.cloudflare.net ~all
```
- `include:_spf.google.com` -- authorizes Gmail to send as your domain
- `include:_spf.mx.cloudflare.net` -- authorizes Cloudflare email routing

If a TXT/SPF record already exists, MERGE (do not create a second SPF record).

### DMARC Record
Add a TXT record for `_dmarc.d2mluxury.quest`:
```
v=DMARC1; p=none; rua=mailto:johnloucks3@gmail.com
```
- `p=none` -- monitoring mode (no rejection yet)
- Once confident email flows correctly, consider upgrading to `p=quarantine` or `p=reject`

### DKIM (Optional but Recommended)
If using Gmail SMTP to send (Step 4), Gmail handles DKIM signing automatically for the gmail.com domain. For d2mluxury.quest DKIM:
1. Google Workspace Admin > Apps > Gmail > Authenticate email (only if on Workspace)
2. For personal Gmail with Send As, Gmail signs with its own DKIM -- this is acceptable

## Step 4: Gmail Send As Configuration

### Alias 1: concierge@d2mluxury.quest (AI Staff)

1. Open Gmail: https://mail.google.com
2. **Settings** (gear icon) > **See all settings** > **Accounts and Import** tab
3. In "Send mail as" section, click **Add another email address**
4. Fill in:
   - Name: `D2M Concierge` (or any persona name -- can change later)
   - Email: `concierge@d2mluxury.quest`
   - Uncheck "Treat as an alias" (keep checked if you want replies in same thread)
5. Click **Next Step**
6. SMTP configuration:
   - SMTP Server: `smtp.gmail.com`
   - Port: `587`
   - Username: `johnloucks3@gmail.com`
   - Password: **Gmail App Password** (NOT your regular password)
   - Select: **Secured connection using TLS**
7. Click **Add Account**
8. Gmail sends a verification email to `concierge@d2mluxury.quest`
   - Cloudflare forwards it to `johnloucks3@gmail.com`
   - Open the email, click the verification link or enter the code
9. Done -- you can now select `concierge@d2mluxury.quest` as the From address in Gmail

### Alias 2: john@d2mluxury.quest (Commander)

Repeat the same process for the Commander's personal D2M address:

1. In "Send mail as" section, click **Add another email address**
2. Fill in:
   - Name: `John Loucks, Dreams2Memories Travel`
   - Email: `john@d2mluxury.quest`
   - Keep "Treat as an alias" checked
3. Click **Next Step**
4. SMTP configuration: same as above
   - SMTP Server: `smtp.gmail.com`
   - Port: `587`
   - Username: `johnloucks3@gmail.com`
   - Password: **Same Gmail App Password**
   - Select: **Secured connection using TLS**
5. Click **Add Account**
6. Verify via the forwarded email in Gmail
7. Done -- john@d2mluxury.quest is now available as a From address

### Creating a Gmail App Password
1. Go to https://myaccount.google.com/apppasswords
2. (Requires 2FA enabled on the Google account)
3. App name: `D2M Send As`
4. Click **Create**
5. Copy the 16-character password -- use this in Step 4.6 above
6. Store it securely (you will not see it again)

## Step 5: Verification Checklist

- [ ] Cloudflare Email Routing enabled and green
- [ ] Catch-all rule active: *@d2mluxury.quest -> johnloucks3@gmail.com
- [ ] SPF TXT record includes both `_spf.google.com` and `_spf.mx.cloudflare.net`
- [ ] DMARC TXT record on `_dmarc.d2mluxury.quest`
- [ ] Gmail Send As: `concierge@d2mluxury.quest` verified and available
- [ ] Gmail Send As: `john@d2mluxury.quest` verified and available
- [ ] Test: send email FROM concierge@d2mluxury.quest to a test address
- [ ] Test: send email FROM john@d2mluxury.quest to a test address
- [ ] Test: send email TO concierge@d2mluxury.quest, confirm it arrives in Gmail
- [ ] Test: send email TO john@d2mluxury.quest, confirm it arrives in Gmail
- [ ] Test: reply to a concierge@ email, confirm Reply-To works

## D2M Email Address Directory

| Address | Role | Usage |
|---------|------|-------|
| `john@d2mluxury.quest` | Commander (John Loucks) | Personal D2M email — used when persona_id is COMMANDER |
| `concierge@d2mluxury.quest` | AI Staff (persona-based display names) | All Wing personas (COS, EXEC, A2, A3, etc.) |

Both addresses forward inbound to `johnloucks3@gmail.com` via Cloudflare catch-all.
Outbound uses Gmail Send As aliases configured in Step 4.

## Notes

- The `thunderbird_gmail.py` module sets `From: "Persona Name" <concierge@d2mluxury.quest>` for AI staff and `From: "John Loucks, Dreams2Memories Travel" <john@d2mluxury.quest>` for COMMANDER persona
- `Reply-To: johnloucks3@gmail.com` is set on all outbound emails
- Gmail API `users.messages.send()` respects Send As aliases once verified
- All persona emails route replies back to John's inbox via Reply-To header
- Email send/draft actions are logged to `~/Thunderbird/logs/email_sent.log`
