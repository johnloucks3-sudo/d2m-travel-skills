# 📜 STANDING ORDER: SO-REPORTING-2026
**THUNDERBIRD WING UNIVERSAL REPORTING GOVERNANCE & CONSOLIDATION**
*Effective Date: July 28, 2026 | Authority: Commander Directive & SES-6 Governance*

---

## 1. PURPOSE & SCOPE
This Standing Order establishes the universal reporting governance for Thunderbird Wing. It eliminates fragmented report generation, enforces direct inbox delivery for internal staff briefs, mandates draft staging in `johnloucks3@gmail.com` for client products, consolidates report timing into two daily windows, and prohibits stale data repetition.

---

## 2. HARD RULES OF REPORTING

1. **DIRECT INBOX DELIVERY FOR INTERNAL REPORTS:** All internal briefs (Morning Brief, Evening EOD, Intel Digests, Innovation Reviews, Tech Scans) MUST be delivered directly to `johnloucks3@gmail.com` INBOX. Internal briefs shall NEVER be staged as Gmail drafts.
2. **CLIENT DRAFT ROUTING:** All client-facing products (itinerary previews, excursion menus, intake follow-ups) MUST be staged in `johnloucks3@gmail.com` DRAFTS labeled `THUNDERBIRD-Commander-Review`. Client drafts shall NEVER be staged in `d2mconcierge` drafts.
3. **BATCHED DELIVERY WINDOWS (2 WINDOWS ONLY):**
   * **06:30 MT Morning Consolidated Brief:** Merges Operational Suspenses, World & Airline OSINT, Fare Watch, and TCD Daily Priorities into a single email.
   * **18:30 MT Evening Consolidated Brief & EOD:** Merges Gauge (A7) Quality & Code Audit, Harlan (A9) Financial Sign-Off, ELON Innovation Digest, and Radical Tech Analysis into a single email.
4. **ZERO REPETITION & ANTI-THEATER RULE:** Reports must never repeat unchanged static text or old findings. Only NEW findings, status deltas, and actionable items shall be presented.
5. **DARK NAVY HTML STANDARD:** All report emails must use the canonical Dark Navy (`#07076b`) HTML template with premailer CSS inlining and canonical signature blocks.

---

## 3. TAB A: EXAMPLE REPORT FORMAT (TRUE COLORS & DARK NAVY CSS)

```html
<div bgcolor="#07076b" style="margin:0;padding:32px 12px;font-family:Georgia,serif;background-color:#07076b;background:radial-gradient(ellipse at 50% -10%,#2428b0 0%,#0e1088 20%,#07076b 50%,#040450 80%,#02022e 100%)">
  <table cellpadding="0" cellspacing="0" border="0" width="100%">
    <tbody>
      <tr>
        <td align="center" bgcolor="#07076b" style="padding:24px 12px;background-color:#07076b">
          <table cellpadding="0" cellspacing="0" border="0" width="600" style="max-width:600px">
            <tbody>
              <tr>
                <td bgcolor="#0a0a68" style="background-color:#0a0a68;padding:22px 24px;text-align:center">
                  <div style="color:#f0f6ff;font-family:Georgia,serif;font-size:14px;letter-spacing:3.5px">
                    DREAMS2MEMORIES TRAVEL, LLC — CONSOLIDATED BRIEF
                  </div>
                </td>
              </tr>
              <tr>
                <td bgcolor="#08086e" style="padding:34px;font-family:Georgia,serif;font-size:16px;line-height:1.8;color:#e8f1ff">
                  <!-- REPORT CONTENT BODY GOES HERE -->
                </td>
              </tr>
              <tr>
                <td bgcolor="#02022a" style="padding:18px 34px;font-size:12px;color:#a8c4f0">
                  DREAMS2MEMORIES TRAVEL, LLC | Authorized by: John A Loucks III, Owner
                </td>
              </tr>
            </tbody>
          </table>
        </td>
      </tr>
    </tbody>
  </table>
</div>
```

---

## 4. TAB B: REVISED & EXPANDED INTELLIGENCE SOURCES

| Report Domain | Primary Data Sources & APIs | Verification & Deduplication Protocol |
|---|---|---|
| **World & Airline OSINT** | FlightAware API, Flightradar24 API, US State Dept Travel Advisories, RSS Feeds | Deduplicated against Qdrant vector database (`d2m-qdrant-reindex`) |
| **Airfare & Fare Watch** | Amadeus GDS, Centrav B2B, Sky Bird Consolidator, Google Flights | Verified live against 200 OK endpoints; delta logged daily |
| **Cruise & Land Suppliers** | Regent RSSC Portal, Silversea TA, Perx Interline, Viator, GetYourGuide | Scraped via headless cloak runners; rates normalized |
| **Code Quality & Governance** | Gauge (A7) Audit Engine, Systemd Timers Auditor, Pre-Commit Hooks | Audited against SO-2026-05-04 and rules registry |
| **Financial Sign-Off** | Victor Harlan (A9) 6-Step Engine, Host Tiers (OA 80/20, Nexion 70/30) | Independent 6-step sign-off on all dollar figures |

---

*BY ORDER OF THE COMMANDER*  
*Ms. Victoria "Victory" Hale, SES-6 — Chief of Staff, Thunderbird Wing*
