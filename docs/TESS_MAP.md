# TESS / CRM API Map
## Dreams2Memories Travel, LLC — myAgentGenie / Outside Agents
### Last Updated: 2026-05-05 (Initial Discovery)

---

## 1. Authentication

| Property | Value |
|---|---|
| Auth scheme | OAuth 2.0 password grant + JWT bearer |
| Token endpoint | `https://crm.myagentgenie.com/api/token` |
| API base | `https://crm.myagentgenie.com/api/api/` |
| Token lifetime | 7,200 seconds (2 hours) |
| Refresh | Single-use, rotates on each call |
| Client ID | `ngAuthApp` (public client, no secret) |
| Token storage | `~/Thunderbird/tess_token.json` |
| Module | `core/booking/thunderbird_tess.py` |

**Refresh flow:**
```
POST https://crm.myagentgenie.com/api/token
Content-Type: application/x-www-form-urlencoded
grant_type=refresh_token&refresh_token={...}&client_id=ngAuthApp
```

**Programmatic access:**
```python
from thunderbird_tess import TESSAuth, API_BASE_URL
auth = TESSAuth()
token = auth.get_valid_token()  # auto-refreshes if expired
# Use as: Authorization: Bearer {token}
```

---

## 2. Confirmed Working Endpoints

### Identity / Account

| Method | Path | Returns | Notes |
|---|---|---|---|
| GET | `User?userID={id}` | dict | Full user profile + Company + Permissions |
| GET | `Company/{id}` | list[1] | Company record (Dreams2Memories Travel = 72914) |
| POST | `token` | dict | OAuth token grant / refresh |
| GET | `signalR/negotiate?clientProtocol=2.1` | dict | SignalR real-time connection token |

### Bulk Data Export

| Method | Path | Returns | Notes |
|---|---|---|---|
| GET | `Export/ClientExport` | XLSX | All D2M clients (17 records, full PII) |
| GET | `Export/AdjustmentExport` | 500 | Endpoint exists but errors (params unknown) |
| GET | `Export/AgentCheckDueExport` | 404 | Required params unknown |
| GET | `Export/ClientPortalTasksExport` | 405 | Requires POST or specific params |
| GET | `Export/CompanyCheckDueExport` | 404 | Required params unknown |
| GET | `Export/DownloadReport` | 400 | Requires reportID param |
| GET | `Export/UserExport` | 405 | Requires POST or specific params |

### Resource Families (CRUD on `:id` works, list patterns need live capture)

All 30 resources follow the URL pattern `api/{Resource}/:id/:action`:

```
Address           Administration       Airline              Booking
BookingIntegration Calendar            CheckAdjustment      CheckPaid
CheckReceived     Client              ClientLead           Company
Contact           CruiseLine          CustomReports        EmailMarketing
HelpDesk          Note                Property             ReportPDF
Task              TourLine            TourOperator         Trip
TripActivity      TripReservation     User                 UserLead
WorkspaceExtension WorkspaceTab
```

For each, the standard methods are:
| Method | Pattern | Status |
|---|---|---|
| GET | `{Resource}/{id}` | ✅ Works (verified on User, Company) |
| POST | `{Resource}` (with full DTO) | 🟡 Returns 400 with ModelState if body invalid |
| PUT | `{Resource}/{id}` | ⚠️ Untested |
| DELETE | `{Resource}/{id}` | ⚠️ Untested |
| GET | `{Resource}` (bare list) | ❌ Returns 405 (Method Not Allowed) |

---

## 3. Known Action Paths (from JS bundle static analysis)

Specific action endpoints the app calls:

| Path | Method | Purpose |
|---|---|---|
| `Client/PostImport` | POST | Bulk client import |
| `ClientLead/PostImport` | POST | Bulk lead import |
| `UserLead/PostImport` | POST | Bulk user lead import |
| `CustomReports/GenerateExport` | POST? | Custom report generation |
| `HelpDesk/Download` | GET | Help desk file download |
| `HelpDesk/DownloadPost` | POST | Help desk post download |
| `Reporting/CheckPaid` | ? | Commission paid report |
| `Reporting/CheckPaidADPCheck` | ? | ADP commission check report |
| `Reporting/CheckPaidCheck` | ? | Commission check details |
| `Reporting/CheckPaidGroupCheck` | ? | Grouped commission check |
| `Reporting/CheckReceived` | ? | Commission received report |
| `Trip/DownloadDocument` | GET | Download trip document |
| `Trip/UploadDocument?tripID={id}` | POST | Upload to a trip |
| `User/UserPasswordResetRequest` | POST | Password reset |

---

## 4. Data Indexed So Far

### Clients (17 records)

Full client list saved to `output/tess_map/clients_export.json`:

| First Name | Last Name | Email |
|---|---|---|
| Amy | Darrow | amy.darrow@me.com |
| Erica | (Buzzerica) | Buzzerica@gmail.com |
| Alfred | Ely | al.ely58@gmail.com |
| John | Furlow | john.furlow@tpf.org |
| Melissa | Furlow | missy.furlow@gmail.com |
| (12 more — see clients_export.json) | | |

Fields per client:
`First Name · Middle Name · Last Name · Birth Date · Telephone · Email · Address1 · Address2 · City · State/Province · Postal Code · Country · Agent Name`

### Identity

- **User:** UserID 3720865, johnloucks3 / John Loucks
- **Company:** CompanyID 72914 = Dreams2Memories Travel (short: JohnLoucks, OrgLevel 2)

---

## 5. Open Discovery Questions

These require either (a) further reverse engineering of the JS bundle, or (b) live capture of the TESS UI's network traffic:

1. **Trip listing pattern** — How does the app fetch the trips list? Bare GET `/Trip` returns 405. POST returns 400 (needs specific DTO).
2. **Booking listing pattern** — Same as Trip. The app loads bookings somehow.
3. **Commission/CheckPaid listing** — `Reporting/CheckPaid` returns 404 on bare GET. Needs date range or filter params.
4. **Per-resource :action enumeration** — The `api/X/:id/:action` URL pattern allows the app to call dynamic actions on each resource. The full action surface isn't statically discoverable.
5. **Training documents location** — Not yet found. May be inside `HelpDesk` or a separate `Training` namespace.
6. **Destination guides location** — Not yet found.

---

## 6. Discovery Method Path Forward

To complete the map, the most efficient next steps are:

### Option A — Live UI capture (fastest, ~10 minutes)
Commander logs into TESS in Chrome, opens DevTools Network tab (filter Fetch/XHR), and:
1. Clicks "Trips" in the navigation
2. Clicks "Bookings"
3. Clicks "Commissions"
4. Clicks any reports / dashboards
5. Sends the captured URLs back

This gives us the exact endpoints + body payloads the app uses.

### Option B — Headless reverse engineering (slower, autonomous)
A headless Claude agent reads more of the JS bundle (especially the "controllers" and "factories" sections), looking for the pattern where `Resource.$method({id, action})` is invoked. This recovers the action names that fill the `:action` URL placeholder.

### Option C — Playwright session capture (autonomous, requires login)
Spawn a Playwright session that logs into TESS using the JWT token, navigates each major page, and captures all XHR requests automatically. This is the most thorough but requires Playwright session bootstrap.

---

## 7. Module Status

`core/booking/thunderbird_tess.py`:

- ✅ **Auth layer**: Working (OAuth password grant + JWT bearer + auto-refresh)
- ❌ **Endpoint methods**: All point to legacy `outsideagents.com/tess/v2` paths and need re-mapping
  - `get_profile()` — needs new endpoint
  - `list_trips()` — pattern unknown
  - `search_bookings()` — pattern unknown
  - `get_commissions()` — likely `Reporting/CheckPaid` with params
  - `list_clients()` — use `Export/ClientExport` (returns XLSX) until JSON pattern found
  - `get_client(id)` — use `Client/{id}` GET (verified pattern)

`MCP tools` (registered via `register_tess_tools`):
- All depend on the endpoint methods above and will fail until those are re-mapped

---

## 8. Files Generated

All artifacts in `output/tess_map/`:

| File | Purpose |
|---|---|
| `01_static_extract.json` | Resource families from JS bundle |
| `02_live_probe.json` | Live status codes for every resource (GET list/by-id) |
| `03_action_paths.json` | Explicit action paths found in JS strings |
| `04_action_probe.json` | Live status of action paths |
| `05_deep_js_extract.json` | All `apiServiceBaseUri+` paths + $http calls |
| `06_discovery_probe.json` | Dashboard endpoint guesses (none worked) |
| `clients_export.json` | All 17 D2M clients (parsed from XLSX) |
| `clients_export.xlsx` | Raw client export from TESS |

---

*Discovery in progress — auth foundation is solid. Endpoint surface needs live capture or deeper static analysis to complete.*
