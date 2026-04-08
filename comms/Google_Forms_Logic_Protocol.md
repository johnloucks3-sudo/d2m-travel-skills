# Google Forms Logic & Send Timing Protocol
## Dreams2Memories Travel, LLC

### Forms Inventory (Based on create_guest_profile_form.py)

**Primary Forms in Google Drive:**
1. **D2M Guest Profile Form** - Comprehensive client information
2. **Dining Preferences Form** - Cuisine, allergies, special requests  
3. **Excursion Interest Form** - Activity preferences, fitness level
4. **Travel Style Assessment** - Pace, priorities, dream experiences
5. **Special Requests Form** - Celebrations, accommodations, VIP needs

### Form Send Timing Logic

**Trigger: Booking Confirmation (Anchor Date: Booking)**
- **Within 24 hours:** Send **D2M Guest Profile Form**
- **Rationale:** Capture essential info while excitement is high
- **Form:** Basic info, emergency contacts, travel documents

**Trigger: 90 Days Pre-Embarkation**
- **Send:** **Dining Preferences Form** + **Travel Style Assessment**
- **Rationale:** Time for restaurant reservations, experience planning
- **Forms:** Cuisine preferences, dietary restrictions, pace/style

**Trigger: 60 Days Pre-Embarkation**
- **Send:** **Excursion Interest Form**
- **Rationale:** Excursion booking windows opening, need client preferences
- **Form:** Activity interests, fitness level, group preferences

**Trigger: 30 Days Pre-Embarkation**
- **Send:** **Special Requests Form**
- **Rationale:** Final opportunity for special arrangements
- **Form:** Celebrations, VIP requests, special accommodations

**Trigger: Payment Received**
- **Resend:** Any incomplete forms with reminder
- **Rationale:** Payment commitment increases form completion rate

### Form Completion Tracking

**Integration Points:**
- **Google Sheets:** `EARA_D2M_Command_Center` (Sheet ID: 1RIOIFmmI4u4OSPA00HaBPPI9DnEftYBcS0TXWQ21ueU)
- **Dossier System:** Form responses → client dossier updates
- **Anchor Date Engine:** Form sends triggered by T-minus milestones

### Automated Workflow

```python
def should_send_form(client, form_type):
    """Determine if form should be sent based on client lifecycle"""
    
    anchors = get_anchor_dates(client.booking_ref)
    forms_sent = get_forms_sent_history(client.email)
    
    # Guest Profile: within 24h of booking
    if form_type == 'guest_profile':
        if not forms_sent.get('guest_profile') and \
           datetime.now() - anchors['booking_date'] < timedelta(hours=24):
            return True
    
    # Dining/Travel Style: 90 days pre-embarkation  
    elif form_type in ['dining_preferences', 'travel_style']:
        if anchors['embarkation_date'] - datetime.now() < timedelta(days=90):
            return True
    
    # Excursion: 60 days pre-embarkation
    elif form_type == 'excursion_interest':
        if anchors['embarkation_date'] - datetime.now() < timedelta(days=60):
            return True
    
    # Special Requests: 30 days pre-embarkation
    elif form_type == 'special_requests':
        if anchors['embarkation_date'] - datetime.now() < timedelta(days=30):
            return True
    
    return False
```

### Form Response Handling

**Process:**
1. **Response received** → Google Sheets
2. **Auto-parse** → Update client dossier
3. **Flag incomplete** → Follow-up reminder
4. **Special requests** → Route to appropriate staff (A2/A6/A9)
5. **Validation** → Cross-check with existing client data

### Quality Assurance

**Before Send Checklist:**
- [ ] Form link tested and working
- [ ] Pre-filled with known client data
- [ ] Customized greeting with client name
- [ ] Clear call-to-action and timeframe
- [ ] Mobile-responsive design verified

**After Send Tracking:**
- [ ] Log sent timestamp
- [ ] Set follow-up reminder (7 days if no response)
- [ ] Monitor response rate
- [ ] Escalate incomplete forms to Commander

### Integration with Lifecycle Revision

This protocol will integrate with the revised event-driven lifecycle architecture:
- **Node 1 (Unpredictable Triggers):** Initial form send after booking
- **Node 2 (Hard Anchors):** Time-based form sends at 90/60/30 days
- **Node 3 (Fluid Tasks):** Form completion tracking and follow-up
- **Node 4 (Staff Review):** Form response analysis and action

---

*Created: 2026-04-07 | Integrated with MISSION-010*