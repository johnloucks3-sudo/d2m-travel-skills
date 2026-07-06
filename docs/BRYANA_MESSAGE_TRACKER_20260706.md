# Bryana Jarboe — Message Tracker & Quota
**Built:** 2026-07-06 · Mechanism: `core/email/user_message_quota.py` + `config/user_quotas.json`

## Current allowance
**750 messages/month, for now.** Every email she sends that reaches Hale counts as one query against this — tracked automatically, no manual bookkeeping.

- Soft limit, not a hard cutoff. Crossing 750 does **not** stop Hale from replying mid-conversation — that would be bad service to a friend. It raises a flag (logged, visible in her status) for a real conversation about increasing the number, before it becomes a problem, not after.
- Check anytime: `python3 -c "from core.email.user_message_quota import status; print(status('bryanajarboe@gmail.com'))"`

## If she (or we) need more

| | Current — Free tier | Upgrade — Developer tier |
|---|---|---|
| **Price** | $0/month | **$20/month** |
| Inboxes (whole AgentMail account, not just Bryana) | 3 | 10 |
| Emails/month (whole account) | 3,000 | 10,000 |
| Emails/day (whole account) | 100 | **No daily cap** |
| Storage | 3 GB | 10 GB |

**What actually changes for Bryana specifically:** her 750/month number isn't an AgentMail platform limit — it's a number we set. We could raise Bryana's own number today, for free, as long as the whole account stays under the shared 3,000/month, 100/day free-tier ceiling everyone (Hale's own C2 traffic + Nancy + Kim + Stefanie + Bryana + Susan) draws from.

**When the $20/month upgrade actually matters:** if the Wing's *combined* usage across every named-waiver correspondent plus Hale's own C2 traffic starts bumping the shared 100/day or 3,000/month ceiling — not because of Bryana alone, but because five people plus Hale's own channel are all drawing from the same bucket. The upgrade removes the daily cap entirely and triples the monthly ceiling and inbox count, giving room to raise everyone's individual number, not just Bryana's.

**Recommendation:** don't upgrade preemptively. Watch actual combined usage (`core/email/agentmail_quota.py` tracks the account-wide count already) and revisit if it's genuinely getting tight — that's a $20/month decision, small enough not to agonize over, but real enough to make on evidence, not a guess.
