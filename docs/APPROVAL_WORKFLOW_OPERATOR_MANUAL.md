# COS Approval Workflow — Operator Manual
**Version 1.0 | 2026-05-03 | Complete Operator Guide**

---

## OVERVIEW

This is the approval workflow for email drafts that need Commander review before final send.

**Process:**
1. Generate draft HTML
2. Create draft in d2mconcierge (NOT sent)
3. Forward draft to johnloucks3 for approval
4. Commander replies "approve"
5. COS automatically generates final draft in d2mconcierge
6. Commander edits and sends from Gmail UI

---

## PREREQUISITES

### 1. Install d2mconcierge OAuth Credentials

```bash
cd ~/Thunderbird
python3 scripts/setup_d2mconcierge_oauth.py
```

**What happens:**
- Browser opens
- Sign in with d2mconcierge@gmail.com
- Grant Gmail API access
- Token saved to `~/.credentials/d2mconcierge.json`

**Verify:**
```bash
ls -la ~/.credentials/d2mconcierge.json
```

### 2. Install Approval Monitor as Systemd Service

```bash
sudo cp ~/Thunderbird/scripts/cos-approval-monitor.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now cos-approval-monitor.service
```

**Verify:**
```bash
sudo systemctl status cos-approval-monitor.service --no-pager -l
```

Expected output:
```
Active: active (running)
```

### 3. Check Logs

```bash
# Monitor in real-time
sudo journalctl -u cos-approval-monitor.service -f

# Or check file logs
tail -50 ~/.thunderbird_approvals/monitor.log
```

---

## WORKFLOW — Step by Step

### STEP 1: Create Draft HTML

Generate your email content as HTML. Example:

```html
<html>
<head>
  <meta charset="utf-8">
  <style>
    body { background-color: #f7f3ea; color: #0000ff; font-family: Georgia, serif; }
    .container { width: 600px; padding: 20px; }
  </style>
</head>
<body>
  <div class="container">
    <h1>Proposal for Client</h1>
    <p>Here's your custom itinerary...</p>
  </div>
</body>
</html>
```

Save to a file, e.g., `/home/john/Thunderbird/drafts/proposal_client_20260503.html`

### STEP 2: Create Draft in d2mconcierge

```bash
python3 ~/Thunderbird/scripts/create_gmail_draft_direct_v3.py \
  --html ~/Thunderbird/drafts/proposal_client_20260503.html \
  --to johnloucks3@gmail.com \
  --subject "[DRAFT] Itinerary for Client XYZ"
```

**What happens:**
- HTML is preprocessed (CSS inlined, unsafe tags removed, divs converted to tables)
- Draft created in d2mconcierge (NOT sent)
- Draft tracking file saved: `~/.thunderbird_approvals/draft_{DRAFT_ID}.json`
- Original HTML saved: `~/.thunderbird_approvals/html_{DRAFT_ID}.txt`

**Output:**
```
✓ Draft created for: johnloucks3@gmail.com
✓ Draft tracking saved to ~/.thunderbird_approvals/draft_abc123xyz.json
✓ Original HTML saved to ~/.thunderbird_approvals/html_abc123xyz.txt
Draft ID: abc123xyz
```

Save the Draft ID for your records.

### STEP 3: Forward Draft to johnloucks3

The draft is now in d2mconcierge Drafts folder. Forward it to johnloucks3:

1. Open Gmail
2. Go to d2mconcierge Drafts folder
3. Open the draft
4. Click "Forward"
5. Send to: johnloucks3@gmail.com
6. Subject: Keep the "[DRAFT]" prefix
7. Send

**Result:** Commander receives draft in johnloucks3 inbox for review.

### STEP 4: Commander Reviews & Approves

Commander opens draft in johnloucks3 inbox and reviews it. If approved:

1. Click "Reply"
2. Type: `approve`
3. Send

**Important:** The approval monitor watches for replies containing the word "approve" (case-insensitive). Any reply with this keyword triggers final draft generation.

### STEP 5: Final Draft Automatically Generated

When the approval monitor detects the "approve" reply:

1. Monitor polls johnloucks3 inbox (every 60 seconds)
2. Detects reply with "approve" keyword
3. Reads original HTML from `html_{DRAFT_ID}.txt`
4. Generates final draft in d2mconcierge Drafts folder
5. Sends notification to johnloucks3: "Draft Ready for Editing"

**Typical timeline:** 60–120 seconds from approval reply to final draft ready.

### STEP 6: Commander Edits & Sends

When Commander gets the "Draft Ready for Editing" notification:

1. Open d2mconcierge Gmail
2. Go to Drafts folder
3. Find the draft with matching subject
4. Open and review
5. Make any edits needed (styling is fully preserved)
6. Click "Send" when ready

**Done.** Email sent with full formatting intact.

---

## MONITORING & TROUBLESHOOTING

### Check Monitor Status

```bash
sudo systemctl status cos-approval-monitor.service --no-pager -l
```

### View Recent Activity

```bash
tail -50 ~/.thunderbird_approvals/monitor.log
```

Look for entries like:
```
[INFO] Found approval: draft_abc123xyz
[INFO] Triggering final draft generator for draft_abc123xyz
[INFO] ✓ Final draft generated
```

### If Approval Detector Fails

**Symptom:** Draft created, but approval monitor doesn't detect reply.

**Diagnosis:**
1. Check monitor is running: `sudo systemctl status cos-approval-monitor.service`
2. Check logs for errors: `tail -50 ~/.thunderbird_approvals/monitor.log`
3. Verify reply was sent to johnloucks3 (not d2mconcierge)
4. Verify reply contains word "approve"

**Fix:**
- Restart monitor: `sudo systemctl restart cos-approval-monitor.service`
- Manually trigger generator: `python3 ~/Thunderbird/scripts/cos_final_draft_generator.py --draft-id {DRAFT_ID} --to johnloucks3@gmail.com --subject "[DRAFT] ..."`

### If Final Draft Generation Fails

**Symptom:** Approval detected, but final draft not created.

**Diagnosis:**
1. Check generator log: `tail -50 ~/.thunderbird_approvals/generator.log`
2. Verify d2mconcierge credentials: `ls -la ~/.credentials/d2mconcierge.json`
3. Verify original HTML saved: `ls -la ~/.thunderbird_approvals/html_{DRAFT_ID}.txt`

**Fix:**
- Re-authenticate d2mconcierge: `python3 scripts/setup_d2mconcierge_oauth.py`
- Re-run generator manually (see command above)

---

## APPROVAL TRACKING

### View All Drafts & Status

```bash
ls -la ~/.thunderbird_approvals/draft_*.json
```

Each file shows:
- Draft ID
- Recipient
- Subject
- Creation time
- Approval status
- Final draft generation status

### Manually Check Draft Status

```bash
cat ~/.thunderbird_approvals/draft_abc123xyz.json
```

Output:
```json
{
  "draft_id": "abc123xyz",
  "to": "johnloucks3@gmail.com",
  "subject": "[DRAFT] Itinerary for Client XYZ",
  "created_at": "2026-05-03T14:32:15.123456",
  "approved": false,
  "approval_email": null,
  "final_draft_generated": false
}
```

After approval:
```json
{
  "draft_id": "abc123xyz",
  "to": "johnloucks3@gmail.com",
  "subject": "[DRAFT] Itinerary for Client XYZ",
  "created_at": "2026-05-03T14:32:15.123456",
  "approved": true,
  "approval_email": "2026-05-03T14:35:42.654321",
  "final_draft_generated": true,
  "final_draft_generated_at": "2026-05-03T14:36:00.123456",
  "final_draft_id": "draft_xyz789abc"
}
```

---

## FORMATTING GUARANTEES

✅ **What's Preserved:**
- Background colors (#f7f3ea cream, #0000ff blue)
- Font families (Georgia serif)
- Text colors and styling
- Images and links
- Table layouts
- Line breaks and spacing
- Inline CSS

❌ **What's Removed (for Gmail safety):**
- Script tags and event handlers
- Unsafe CSS (animation, transform, position:fixed)
- Embedded SVGs
- iFrames
- Unsafe attributes (onload, onclick, etc.)

**Why:** Gmail's rendering engine is strict about unsafe content. Our preprocessor removes these BEFORE creating the draft, so what you see in Gmail is exactly what was sent.

---

## QUICK COMMAND REFERENCE

| Task | Command |
|------|---------|
| Setup d2mconcierge OAuth | `python3 ~/Thunderbird/scripts/setup_d2mconcierge_oauth.py` |
| Install monitor service | `sudo cp ~/Thunderbird/scripts/cos-approval-monitor.service /etc/systemd/system/ && sudo systemctl daemon-reload && sudo systemctl enable --now cos-approval-monitor.service` |
| Create draft | `python3 ~/Thunderbird/scripts/create_gmail_draft_direct_v3.py --html <file> --to johnloucks3@gmail.com --subject "[DRAFT] ..."` |
| Check monitor status | `sudo systemctl status cos-approval-monitor.service` |
| View monitor logs | `tail -50 ~/.thunderbird_approvals/monitor.log` |
| View generator logs | `tail -50 ~/.thunderbird_approvals/generator.log` |
| Manually trigger generator | `python3 ~/Thunderbird/scripts/cos_final_draft_generator.py --draft-id {ID} --to johnloucks3@gmail.com --subject "..."` |
| List all drafts | `ls -la ~/.thunderbird_approvals/draft_*.json` |
| Check draft status | `cat ~/.thunderbird_approvals/draft_{ID}.json` |

---

## APPROVAL FLOW DIAGRAM

```
┌─────────────────────────────────────────────────────────────┐
│ COS: Create Draft HTML                                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ↓
┌─────────────────────────────────────────────────────────────┐
│ create_gmail_draft_direct_v3.py                             │
│ • Preprocess HTML (CSS inline, unsafe tags remove)         │
│ • Create draft in d2mconcierge (NOT sent)                  │
│ • Save tracking metadata                                    │
│ • Save original HTML                                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ↓
┌─────────────────────────────────────────────────────────────┐
│ COS: Forward draft to johnloucks3                           │
│ • Open d2mconcierge Drafts                                  │
│ • Forward to johnloucks3@gmail.com                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ↓
┌─────────────────────────────────────────────────────────────┐
│ Commander: Review & Approve                                │
│ • Open johnloucks3 inbox                                    │
│ • Review draft                                              │
│ • Reply: "approve"                                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ↓
┌─────────────────────────────────────────────────────────────┐
│ cos_approval_monitor.py (daemon)                            │
│ • Polls johnloucks3 inbox every 60 seconds                 │
│ • Detects reply with "approve"                              │
│ • Triggers cos_final_draft_generator.py                     │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ↓
┌─────────────────────────────────────────────────────────────┐
│ cos_final_draft_generator.py                                │
│ • Load d2mconcierge OAuth                                   │
│ • Read original HTML                                        │
│ • Create final draft in d2mconcierge Drafts                │
│ • Send notification to johnloucks3                          │
│ • Update tracking metadata                                  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ↓
┌─────────────────────────────────────────────────────────────┐
│ Commander: Edit & Send                                      │
│ • Receive "Draft Ready for Editing" notification           │
│ • Open d2mconcierge Drafts                                  │
│ • Edit as needed                                            │
│ • Click "Send"                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## SUPPORT & DEBUGGING

**For approval monitor failures:**
```bash
# Check if monitor is still running
ps aux | grep cos_approval_monitor.py

# Check systemd journal for errors
sudo journalctl -u cos-approval-monitor.service -n 50

# Restart the service
sudo systemctl restart cos-approval-monitor.service
```

**For d2mconcierge OAuth issues:**
```bash
# Re-authenticate
python3 ~/Thunderbird/scripts/setup_d2mconcierge_oauth.py

# Verify credentials file
file ~/.credentials/d2mconcierge.json
```

**For formatting issues:**
- Check original HTML is valid (well-formed tags, proper encoding)
- Verify no unsupported CSS (animation, transform, position:fixed)
- See GMAIL_TEMPLATE_SOLUTION_IRONCLAD.md for complete list of safe/unsafe properties

---

*Operator Manual v1.0 | 2026-05-03 | COS — Col Victoria "Iron Vic" Hale*
