# Sector J — CRM | 2026-07-02
**Scanned by:** ELON (A12) | **Posture:** Adopt-first

---

## Top 3 Findings

1. **NetHunt CRM lives inside Gmail and does what our custom dossier system does — but with a UI, pipelines, and Telegram integration built in.** Native Google Workspace app (Chrome extension + sidebar), real-world travel agency case study (Bon Vivant, luxury London advisory), pipeline tracking, automated follow-ups, Telegram integration, Zapier hooks (7,000 apps). March 2026: NetHunt released a standalone version (no longer requires Gmail). An MCP integration layer exists via Composio. This is the closest match to our Gmail → dossier → TESS workflow in an off-the-shelf product. Free trial available.

2. **Ezus is a full travel-agency-specific platform — but it's for DMCs and tour operators, not cruise-specialist advisors.** 3,000+ agencies in 80+ countries, Gmail + Zapier + Stripe integration, AI content generation in 6 languages. The problem: Ezus is designed for building custom itineraries from a supplier catalog. D2M's model is cruise-line-sourced, not supplier-catalog-built. Ezus would require significant workflow re-mapping to fit, and it adds a monthly subscription cost we'd have to justify against our custom stack.

3. **The honest answer: D2M's custom dossier system + TESS is already better for our use case than any off-the-shelf CRM.** Our markdown dossiers are AI-native (Claude reads them natively), version-controlled (git), and integrated directly into our Thunderbird workflow. No commercial CRM offers git integration, Claude-native read, or the degree of custom automation we've built. The kill-audit finding here is not "replace dossiers with a CRM" — it's "add the CRM features we're missing without adding bloat." Specifically: pipeline visualization, lifecycle stage tracking, and auto-population from Gmail threads.

---

## Adoption Recommendations

| Tool/Move | Priority | Rationale | Estimated effort |
|---|---|---|---|
| **NetHunt CRM trial** — pipeline view only, layered over existing Gmail | P1 | $0 to trial. Specific test: does the Bon Vivant case study pattern match D2M's workflow? If pipeline visualization + automated follow-up reminders replace our manual lifecycle TP tracking in hale_state.json, it's a win. If not, we learned in a week. | 1 day trial setup |
| **Build Gmail → dossier auto-extract** — Python script using Claude to read email threads and append to dossier | P0 | We already have the tools. Client sends an email, Claude reads it, extracts preferences/updates, appends to their dossier. This is the core AI CRM feature — and we can build it on our stack without a subscription. | 2-3 days |
| **Pipeline dashboard** — simple JSON → HTML dashboard showing all 16 clients, lifecycle stage, next TP, days to FPD | P1 | We have the data in hale_state.json. We don't have a visual pipeline view. One-time build. No ongoing cost. | 1 day |
| **Evaluate Ezus** — request demo specifically for cruise-specialist workflow | WATCH | Not ready to adopt without a trial that shows cruise-line-sourced booking fit. Ezus's AI features (content generation, translation) are interesting. Their core workflow is not us. | 2-hour demo |

---

## Kill Audit — What to Replace

| Current approach | Candidate replacement | Confidence |
|---|---|---|
| Manual dossier updates (type after client email) | Gmail → Claude → auto-dossier append script | HIGH — build in-house |
| hale_state.json as pipeline tracker (JSON, no visual) | Simple HTML dashboard generated from existing JSON | HIGH — 1-day build |
| No lifecycle stage visualization | Pipeline view (either NetHunt trial or in-house HTML) | HIGH |
| ClientBase (if D2M ever used it) | Not in our stack — skip | N/A |
| Manual TP scheduling in hale_state.json | Already mostly automated via tp_scheduler — continue improving | MEDIUM |

**CRM verdict: Build over Buy.** Our stack is AI-native in a way no commercial CRM can match. The missing pieces (pipeline view, auto-extract from email) are 2-3 day builds on existing infrastructure. The only scenario where a commercial CRM wins is if D2M scales to 50+ active clients — then the maintenance overhead of the custom system exceeds the subscription cost of NetHunt or Ezus.

---

## Watch List (not adopt yet)

- **HubSpot CRM (free tier)** — powerful, but not travel-specific. The Gmail integration is good. The automation is strong. The problem: HubSpot is a marketing-first tool and will constantly push D2M toward campaign-style outreach, which conflicts with our high-touch relationship model. Watch if we ever build a marketing funnel.
- **Creatio** — no-code CRM workflow builder with AI. Enterprise pricing. Not the right scale for D2M now.
- **monday.com CRM** — cited for travel agency group booking support. Feels like project management with a CRM wrapper. Our custom stack does this better for our specific workflow.
- **Salesforce Travel Cloud** — enterprise only. Not relevant at D2M's scale.
- **AI dossier extraction startups** — multiple YC and seed-stage companies building "read your email, build client profiles automatically." This space will mature in 12-18 months. Watch for a tool that does Gmail → structured CRM record with zero prompt engineering required.

---

## ZEN Counter-Voice

The "build over buy" recommendation is correct for now but has a compounding maintenance tax. Every time D2M hires a staff member (human or AI), they have to learn the custom dossier system. Every new integration (new cruise line, new booking system) requires a custom script. The custom stack scales to maybe 30-40 clients before the maintenance burden starts eating the time savings. The counter-recommendation: build the Gmail → dossier extract now (genuine gap, high ROI), but spend the next 6 months architecting the dossier system to be importable into a commercial CRM later. If the data model is clean, the migration cost stays low. If we build the custom stack without export discipline, we're locked in forever — and "locked in" only looks like a moat until someone builds a better tool.

---

*Sources: [NetHunt travel agency CRM](https://nethunt.com/blog/8-best-crm-for-travel-agencies/) · [NetHunt Bon Vivant case study](https://nethunt.com/case-studies/bon-vivant) · [NetHunt MCP/Composio integration](https://composio.dev/toolkits/nethunt_crm) · [Ezus travel CRM overview](https://ezus.io/post/best-crm-for-travel-agents-2026) · [Ezus integrations](https://ezus.io/integrations) · [Monday travel CRM](https://monday.com/blog/crm-and-sales/travel-agent-crm/) · [AI CRM adoption 2026](https://www.jotform.com/ai/ai-crm/) · [SaaStr CRM 2026-27](https://www.saastr.com/which-crm-should-you-use-in-2026-2027-follow-the-agents/)*
