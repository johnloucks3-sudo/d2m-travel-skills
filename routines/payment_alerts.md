# Routine: /payment-alerts
## FPD Payment Deadline Scanner

Check these payment deadlines against today's date. Today is $(date +%Y-%m-%d).

**Client payment schedule:**
(List your active FPD deadlines here — or say "read from the last briefing")

For each deadline within 45 days, alert with:
- Days remaining
- Amount due
- Payment status (paid/unpaid/partial)
- Recommended action

Format as:
```
🚨 [DAYS] days: [CLIENT] — $[AMOUNT] due [DATE]
   Action: [send reminder / mark paid / escalate]
```
