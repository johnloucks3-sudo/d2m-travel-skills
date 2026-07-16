# MAGOA Portal Operations Guide
## Dreams2Memories Travel, LLC
### Invoice, Payment Collection & Booking Metadata Reference
### Last Updated: March 9, 2026

---

## 1. Outside Agents Portal Ecosystem

MAGOA (My Agent Genie / Outside Agents) provides three integrated portals:

**MAGtap** (tap.myagentgenie.com)
- Agent community, training, resources, booking engine access

**Odysseus** (book.myagentgenie.com)
- Cruise and hotel booking engine, booking management, customer profiles

**TESS** (crm.myagentgenie.com)
- Trip/travel management, CRM, client management, invoicing, commissions

All three share the same login credentials (johnloucks3). MAGtap is the hub that links to Odysseus (bookings) and TESS (CRM/trips).

---

## 2. Sending Invoices from TESS

### Step 1: Ensure Trip Has Active Bookings
Navigate to **Trip Management > Trips** > select the trip.

The BOOKINGS tab must show at least one active booking with a package price. If BOOKINGS shows (0), the invoice renders $0.00 with warning: *"An invoice cannot be generated because this trip has no active bookings."*

### Step 2: Ensure Trip Has Travelers
The trip must have at least one traveler linked via the trip Details tab.

### Step 3: Navigate to Communication Tab
From the trip page, click the **COMMUNICATION** tab.

### Step 4: Select Invoice Template
On the left side, click one of the templates in the Template Name list:

| Template | Description |
|----------|-------------|
| MAG Invoice | Basic invoice format |
| MAG Invoice 2018 | Updated format with client name in subject |
| **MAG Invoice Detail** | Most detailed: itemized bookings, payment schedule, itinerary, flight info **(RECOMMENDED)** |

### Step 5: Select Client
On the right side, use the **Client** dropdown to select which client receives the invoice.

### Step 6: Review and Send
The invoice preview renders showing:
- Invoice number (format: `ClientID-TripID-Sequence`)
- Invoice date and amount (total from all active bookings)
- Payment breakdown per booking (package price, payments received, balance)
- Final payment due dates
- Trip itinerary, flight info, security/passport reminders

Three action buttons:
- **Export to PDF** — Downloads invoice as PDF
- **Email Test Invoice** — Sends to YOUR email first (**always do this first!**)
- **Email Invoice** — Sends to the selected client

### Step 7: Customizing Invoice Templates
Default templates are TESS Library (read-only). To customize:

1. Go to **My Account > Templates > Email Templates**
2. Filter by Email Type: **Invoice**
3. Click the template you want
4. Click **"Add to my library"** (green button, left sidebar)
5. This creates an editable copy in your library
6. Click **"Edit Template"** to open the email builder
7. Add payment instructions, Zelle info, or other custom content

---

## 3. Collecting Client Payments

### The Client Portal (Recommended Secure Method)

TESS provides a Client Portal where clients securely submit credit card information.

**How it works:**
1. From trip Communication tab, select **"Client Portal Activation"** template
2. Select the client and click **"Email Client Portal Activation"**
3. Client receives email with **"ACTIVATE NOW"** button
4. Client registers using Passkey or One-Time Email Code
5. Once activated, client can:
   - View trip details, itineraries, and bookings
   - View invoices and track due dates
   - **Add credit card information securely**
   - Pre-approve payments
   - Upload/share documents and complete tasks

### Where Credit Cards Appear (Agent Side)

When a client adds a credit card through the portal:

1. Go to **Client Management > Clients** > select client
2. Click the **TRACKING** tab
3. **CREDIT CARDS** section shows:
   - Masked card number (`************** XXXX`)
   - Expiration date
   - Name on card and billing address
   - **"Decrypt"** button to reveal full card number
   - DEFAULT flag for primary card
4. You can also manually add cards via **"Add Credit Card"** button

### Other Payment Methods

| Method | Details |
|--------|---------|
| Phone | Client calls, reads card; agent enters into booking system |
| Zelle/Venmo | Add instructions to customized invoice template |
| Check | Add mailing address to customized invoice template |
| Secure Link | Use Stripe Payment Links or Square Invoices |

> **NEVER collect credit card numbers via regular email — PCI compliance violation.**

---

## 4. Odysseus Booking Metadata (Report View)

Odysseus captures **71 data fields** per booking in Report View. This is the richest data source for booking dossiers and Google Sheets.

### Booking Identification
- **Product** (Cruise/Hotel)
- **Agency Conf#** (internal reference, e.g., CUW88R8)
- **PNR** (Passenger Name Record)
- **Conf#** (supplier confirmation, e.g., 9595029)
- **Status** (Confirmed, Waitlisted, Held, Cancelled, Pending, Expired, Ticketed, Fraud)

### Customer Information
- Customer FirstName, MiddleName, LastName
- Email, Phone
- IP Address (booking origin)
- Customer Ref 1, Customer Ref 2

### Supplier & Product Details
- Supplier (e.g., Viking Ocean)
- Cruise Ship (e.g., Viking Mars)
- Category (e.g., V1, DV1) + Category Type (e.g., Balcony)
- Rate Code (e.g., OMAPSF26-3)
- Booking Class
- Destination (e.g., Mexico)
- Depart City/Country, Arrive City/Country

### Dates & Schedule
- From DateTime (departure), To DateTime (return)
- Created DateTime, Modified DateTime
- Deposit Due Date, Deposit Paid Date
- Final Due Date, Final Paid Date
- Insurance Paid Date

### Financial Data
- **Total** (booking price)
- Commissionable Fare, Taxes, Insurance, CCF
- **Cruise Commission**, Total Commission, Agent Comm
- Service Fee, CC Processing Fee
- Aff Markup, Discount
- Add On Items, Package Services
- Currency (USD)

### Booking Provenance
- Site Name (e.g., MAGtap - 1372507)
- Sid1, Sid2 (site IDs)
- Created By, Modified By (agent name)
- App (B2B/B2C)
- Referrer/Promo, ReferrerID2, Referrer3
- API (supplier API), Office, Ticketing Office
- Booking Mode (Online, Lead, Group, Manual, Quote, Import)

### Analytics & Device
- Device (Desktop/Mobile/Tablet)
- OS (e.g., Windows 10), Browser (e.g., Chrome 144.0)
- Pax Count, Segment Count
- Confirmed/Ticketed, Total Count, Fraud Count
- Insurance Policy No

### Agency Use Fields
- AgencyUseCol1, AgencyUseCol2 (custom agent notes)
- AgencyUseDate1 (custom date field)

---

## 5. Current Bookings (March 9, 2026)

**Viking Mars — Panama City to Ft Lauderdale — Dec 17-27, 2026**

| Field | Booking 1 | Booking 2 | Booking 3 |
|-------|-----------|-----------|-----------|
| Customer | Morton, Joshua | Kuklinski, Kyle Stanley | Kuklinski, Roger David |
| Agency Conf# | CUW88R8 | 1TSWFQR | LJ2O4YG |
| Conf# | 9595029 | 9593880 | 9593873 |
| Status | Confirmed | Confirmed | Confirmed |
| Category | V1 Balcony | DV1 Balcony | DV1 Balcony |
| Rate Code | OMAPSF26-3 | OMAFSV26-3 | OMAFSV26-3 |
| Pax | 2 | 2 | 2 |
| Total | $6,198.00 | $7,598.00 | $7,598.00 |
| Commission | $1,053.66 | $1,291.66 | $1,291.66 |
| Final Due | 03/10/2026 | 03/10/2026 | 03/10/2026 |
| Balance | $6,148.00 | $7,548.00 | $7,548.00 |
| Deposit Paid | — | 02/08/2026 | 02/08/2026 |

**PORTFOLIO TOTAL: $21,394.00 | TOTAL COMMISSION: $3,636.98**

---

## 6. Odysseus-to-Sheets Field Mapping

Key fields to sync from Odysseus Report View into Google Sheets Booking Master:

| Odysseus Field | Sheets Column |
|---------------|---------------|
| Agency Conf# | Booking ID |
| Conf# | Supplier Confirmation |
| Customer Last/First | Client Name |
| Supplier + Cruise Ship | Supplier / Product |
| Category + Type | Room/Cabin Type |
| From/To DateTime | Travel Dates |
| Total | Total Cost |
| Cruise Commission | Commission Amount |
| Status | Booking Status |
| Deposit Due/Paid Date | Deposit Status |
| Final Due/Paid Date | Final Payment Status |
| Depart City/Country | Origin |
| Arrive City/Country | Destination |
| Rate Code | Rate Code |
| Pax Count | Passengers |

---

## 7. CDP Automation (Thunderbird Integration)

All three portals are accessible via Chrome DevTools Protocol (CDP):

1. **Launch Chrome:** `~/Thunderbird/deploy/chrome-debug.sh` (alias: `chrome`)
2. **Log into portals** in Chrome (handles 2FA, Cloudflare, fingerprinting)
3. **MCP tools** connect via CDP: `oa_connect`, `oa_browse`, `oa_action`, `oa_status`
4. **Automation rides** the live Chrome session — same cookies, fingerprint

**Why CDP:** Odysseus uses Cloudflare Bot Management + ClientJS fingerprinting. Playwright's own browser gets 403'd. CDP connects to the real Chrome — undetectable.

| Config | Value |
|--------|-------|
| Module | `~/Thunderbird/thunderbird_outside_agents.py` |
| Chrome profile | `~/.config/google-chrome-debug/` |
| CDP port | 9222 |

**Correction (2026-07-16):** Section 1's "all three share the same login" does not mean single-sign-on across tabs — each portal requires its own explicit login in the CDP Chrome profile even when the Commander is logged into another. Verified live: TESS tab authenticated (`crm.myagentgenie.com/app/views/trips`) while an Odysseus tab opened in the same profile still showed `login.aspx` ("PLEASE LOGIN"). Confirm `oa_status`/`oa_connect` per-portal `authenticated` flag before assuming a Commander login covers all three.
