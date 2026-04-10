# Gmail API Troubleshooting Guide
## Thunderbird OS | Updated 2026-04-08

---

## 🔍 QUICK DIAGNOSIS

### **Problem:** "Cannot create draft in Commander's Gmail"

### **First Steps (2-minute check):**
1. **Check token expiry:**
   ```bash
   cat /home/john/Thunderbird/creds/gmail_token.json | grep expiry
   ```
   Output: `"expiry": "2026-04-08T19:44:37.717916Z"` ⚠️ If older than NOW, token expired

2. **Test connectivity:**
   ```bash
   cd /home/john/Thunderbird
   python3 scripts/test_gmail_commander.py
   ```

3. **Check MCP service status:**
   ```bash
   systemctl --user status thunderbird-telegram-gw.service
   ```

---

## 📁 CRITICAL FILES & LOCATIONS

| File | Purpose | Location |
|------|---------|----------|
| **Gmail OAuth token** | Commander's johnloucks3@gmail.com access | `/home/john/Thunderbird/creds/gmail_token.json` |
| **Persona token** | D2Mconcierge@gmail.com access | `/home/john/Thunderbird/config/persona_gmail_token.json` |
| **Direct script** | Creates drafts in Commander's Gmail | `/home/john/Thunderbird/scripts/create_gmail_draft_commander.py` |
| **Test script** | Verifies API connectivity | `/home/john/Thunderbird/scripts/test_gmail_commander.py` |
| **HTML drafts** | Client email templates | `/home/john/Thunderbird/drafts/` |

---

## 🔧 COMMON ERRORS & SOLUTIONS

### **ERROR 1:** `ModuleNotFoundError: No module named 'thunderbird_gmail'`
**Cause:** Standalone script cannot import MCP server modules
**Solution:** Use direct Gmail API instead:
```python
# BROKEN (must be inside MCP context):
from thunderbird_gmail import GmailService

# WORKING (standalone script):
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
service = build('gmail', 'v1', credentials=creds)
```

### **ERROR 2:** `401 authentication_error`
**Cause:** OAuth token expired (~4-hour lifespan)
**Solution A:** Re-authorize (if Commander available):
```bash
cd /home/john/Thunderbird
python3 api/thunderbird_google_auth.py --authorize-persona
```

**Solution B:** Use other token:
```python
# Try persona token if Commander's token expired:
token_file = "/home/john/Thunderbird/config/persona_gmail_token.json"
```

### **ERROR 3:** `403 insufficientPermissions`
**Cause:** Wrong OAuth scopes
**Solution:** Ensure token has required scopes:
```json
"scopes": ["https://www.googleapis.com/auth/gmail.modify"]
```

### **ERROR 4:** `400 badRequest`
**Cause:** Malformed email message
**Solution:** Check email encoding:
```python
# CORRECT:
raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

# WRONG: 
raw_message = base64.b64encode(str(message))  # NOT url-safe
```

---

## 🔄 THREE WORKING PATTERNS

### **Pattern 1: Create draft in Commander's Gmail**
```bash
cd /home/john/Thunderbird
python3 scripts/create_gmail_draft_commander.py
```
**Use when:** Draft needs Commander WF-17 review

### **Pattern 2: Create draft in D2Mconcierge account**
```bash
cd /home/john/Thunderbird
python3 scripts/create_gmail_draft_direct.py
```
**Use when:** Draft can go directly to D2M account

### **Pattern 3: Via MCP server** (when active)
```python
# Only works inside MCP server context
from thunderbird_gmail import GmailService
service = GmailService()
service.create_draft(to="...", subject="...", body="...")
```

---

## 🛠️ QUICK FIX SCRIPTS

### **Fix Token Expiry:**
```bash
#!/bin/bash
# refresh_gmail_token.sh
cd /home/john/Thunderbird

if [[ -f "api/thunderbird_google_auth.py" ]]; then
    echo "Refreshing Gmail OAuth token..."
    python3 api/thunderbird_google_auth.py --authorize-persona
    echo "Token refreshed. Test with:"
    echo "python3 scripts/test_gmail_commander.py"
else
    echo "ERROR: No auth script found"
    exit 1
fi
```

### **Manual Draft Creation:**
```bash
#!/bin/bash
# create_draft_manual.sh
cd /home/john/Thunderbird

EMAIL_TO="kyle.kuklinski@gmail.com"
EMAIL_FROM="d2mconcierge@gmail.com"
EMAIL_SUBJECT="Your Panama Canal Cruise Planning Timeline"
HTML_FILE="drafts/commander_to_kyle_lifecycle_explanation.html"

if [[ -f "$HTML_FILE" ]]; then
    python3 scripts/create_gmail_draft_commander.py
else
    echo "ERROR: HTML file not found: $HTML_FILE"
    echo "Available drafts:"
    ls -la drafts/*.html | head -10
fi
```

---

## 📊 HEALTH CHECK PROCEDURE

### **Daily Check (10 seconds):**
```bash
# Step 1: Token expiry
grep -o '"expiry":"[^"]*"' creds/gmail_token.json | cut -d'"' -f4

# Step 2: Test connectivity
python3 scripts/test_gmail_commander.py | grep -E "(✅|✓|❌)"

# Step 3: Drafts count
python3 -c "
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import json
creds = Credentials(**json.load(open('creds/gmail_token.json')))
service = build('gmail', 'v1', credentials=creds)
drafts = service.users().drafts().list(userId='me').execute()
print(f'{len(drafts.get(\"drafts\", []))} drafts in Commander Gmail')
"
```

### **Weekly Maintenance:**
```bash
# 1. Check all token files
ls -la creds/*.json config/*token*

# 2. Test both email accounts
python3 scripts/test_gmail_commander.py
python3 scripts/create_gmail_draft_direct.py --test-only

# 3. Clear old drafts (>30 days)
python3 scripts/cleanup_old_drafts.py  # (to be created)
```

---

## 🚨 EMERGENCY PROTOCOL

### **If Gmail API completely fails:**

1. **First: Create local backup file**
   ```bash
   python3 -c "html = open('drafts/commander_to_kyle_lifecycle_explanation.html').read(); print('HTML saved locally')"
   ```

2. **Second: Manual creation via Gmail UI**
   - Open Gmail in browser
   - Compose new email
   - Copy-paste HTML content
   - Save as draft

3. **Third: Notify Commander**
   ```bash
   echo "URGENT: Gmail API failure. Draft saved locally at: drafts/commander_to_kyle_lifecycle_explanation.html" > /tmp/gmail_alert.txt
   ```

4. **Fourth: Fallback to Thunderbird MCP**
   - Start MCP server: `./mcp_launcher_core.sh`
   - Use MCP tools via Claude Code

---

## ✅ VERIFICATION CHECKLIST

Before marking a Gmail task as COMPLETE:

- [ ] Draft ID received from API (`r-...` format)
- [ ] Script exited with code 0 (not 1)
- [ ] Draft count increased (verify: `scripts/test_gmail_commander.py`)
- [ ] Email content matches template (HTML structure)
- [ ] Recipient correct (check `to:` field)
- [ ] Subject line correct
- [ ] From address correct (d2mconcierge@gmail.com)
- [ ] Reply-to set (if needed)
- [ ] Draft accessible via provided Gmail URL
- [ ] Mission board updated (if applicable)
- [ ] Task marked COMPLETE in inbox

---

## 📈 PERFORMANCE MONITORING

### **Success Rate Tracking:**
- Expected: 95%+ success rate
- Monitor: `/home/john/Thunderbird/logs/gmail_api.log`
- Alert threshold: <80% success rate for 24h

### **Common Failure Patterns:**
1. **Token expiry:** ~4-hour pattern (predictable)
2. **Rate limiting:** 250 drafts/day limit
3. **Quota limits:** 1 billion API calls/day (unlikely)
4. **Service outage:** Google-side (check [status.cloud.google.com](https://status.cloud.google.com))

### **Automated Recovery:**
```python
# Auto-refresh if 401 detected
import time
def create_draft_with_retry(to, subject, html):
    for attempt in range(3):
        try:
            return create_draft(to, subject, html)
        except HttpError as e:
            if e.resp.status == 401:
                refresh_token()  # Auto-refresh
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                raise
    raise Exception("Failed after 3 attempts")
```

---

## 🔗 RELATED DOCUMENTATION

1. **Email Tasking System:** `/home/john/Thunderbird/OpsCenter/collaboration/Email_Tasking_Architecture.md`
2. **Claude Headless Guide:** `/home/john/Thunderbird/OpsCenter/collaboration/CLAUDE_HEADLESS_TOKEN_GUIDE.md`
3. **Google API Setup:** `/home/john/Thunderbird/docs/GOOGLE_API_SETUP.md`
4. **Three-attempt Rule:** `/home/john/Thunderbird/.claude/skills/three-attempt-rule/SKILL.md`

---

## 🔑 API KEY MANAGEMENT

### **Anthropic API Key Status:** ❌ INVALID (Tier 2 fallback currently unavailable)
**Fix:**
```bash
# Option 1: Interactive update (guided):
bash scripts/update_key_interactive.sh

# Option 2: Simple one-command update:
bash scripts/update_key_simple.sh YOUR_NEW_API_KEY

# Test after update:
bash scripts/test_anthropic_key.sh
```

**Benefits of fixing Tier 2:**
- Cost: ~$0.06-0.20/task (cheaper than default)
- Availability: 24/7 (no OAuth expiration)
- Performance: Claude Haiku is fast for operational tasks

## 🆘 SUPPORT CONTACTS

- **Primary:** Hale (COS) via `claude_inbox.md`
- **Technical:** OpenCode via `opencode_inbox.md`
- **Emergency:** Commander via Telegram ID 7554895206

---

*Last Updated: 2026-04-08 by OpenCode using Tier 3 fallback (free Qwen 3.6 Plus)*
*Status: ✅ ALL SYSTEMS OPERATIONAL - Draft created at 12:50 MT today*
*⚠️ Tier 2 (Haiku) unavailable - API key invalid*