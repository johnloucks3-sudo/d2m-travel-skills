# TESS / CRM API Map
## Dreams2Memories Travel, LLC — myAgentGenie / Outside Agents
### Last Updated: 2026-05-05 (Discovery Complete + Module Patched)

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

## 5. Discovery Resolved — Pagination Was The Key

**One insight unlocked everything:** the AngularJS `$resource` URL template `api/{X}/:id/:action`
collapses to bare `api/{X}` when both `id` and `action` are empty. List endpoints **require**
`pageNumber` + `pageSize` query params — without them, the server returns 405. With them, every
resource list returns paginated JSON `{Items, CountFiltered, CountUnfiltered, PageNumber, PageSize}`.

**Confirmed live (verified with bearer token, 2026-05-05):**

| Concern | Working URL |
|---|---|
| Trip list | `GET /api/api/Trip?pageNumber=1&pageSize=50&sortBy=CreatedDateTimeUTC&sortAscending=false` |
| Booking list (financial pulse) | `GET /api/api/Booking?pageNumber=1&pageSize=50&sortBy=BookingDate&sortAscending=false` |
| Client list (JSON) | `GET /api/api/Client?pageNumber=1&pageSize=50` |
| CheckReceived list (commissions in) | `GET /api/api/CheckReceived?pageNumber=1&pageSize=50` |
| CheckPaid list (payouts) | `GET /api/api/CheckPaid?pageNumber=1&pageSize=50` |
| Per-check PDF report | `GET /api/api/Reporting/CheckReceived?checkID={id}&format=PDF` |

**Action endpoints (where `:action` is set but `:id` is empty):** Angular emits the action as a
**query parameter** (`?action=ActionName`), NOT a path segment. Examples:

| Resource | Action | Use |
|---|---|---|
| Trip | `?action=TripAccessGetListForDashboard` | Dashboard tile |
| Trip | `?action=TripAccessGetListGroupedByCountryByUserID` | Reporting |
| Booking | `?action=GetBookingSalesGroupedDashboard` | Sales dashboard |
| Booking | `?action=GetUnclaimedBookings` | Unclaimed bookings |
| CheckPaid | `?action=CheckPaidByCompanyIDGet` | Per-company check list |

**General URL rules for any resource in the `:id/:action` family:**

| Goal | URL |
|---|---|
| Get one record | `GET /api/api/{X}/{id}` |
| List all (paginated) | `GET /api/api/{X}?pageNumber=1&pageSize=10[&filters]` |
| Call collection action | `GET /api/api/{X}?action=ActionName[&params]` |
| Call instance action | `GET /api/api/{X}/{id}?action=ActionName[&params]` |
| Update | `PUT /api/api/{X}/{id}` (body = full DTO) |
| Save/insert | `POST /api/api/{X}` or `POST /api/api/{X}?action=...` |

## 6. Live D2M Snapshot (verified 2026-05-05)

| Resource | Count | Notes |
|---|---|---|
| Trips | 12 | Active book + completed |
| Bookings | 17 | $23.4K in top 5 alone, full Commission objects per record |
| Clients | 18 | JSON list works (XLSX export still available as fallback) |
| CheckReceived | 1 | $244.80 from Outside Agents, CheckID 605635, dated 2026-03-03 |
| CheckPaid | 0 | D2M is OrgLevel 2 — no downline payouts |

## 7. Still Out of Scope

These remain to be mapped (low-priority, non-blocking):

1. **Action-level write payloads** — POST/PUT body DTOs for create/update operations
2. **Training documents** — not visible in this bundle, may be a separate module
3. **Destination guides** — not in this bundle, likely on-demand load
4. **`Export/AgentCheckDueExport` + `CompanyCheckDueExport`** — return 404 on bare GET, need
   `userID` / `companyID` query params (mirror `AdjustmentExport` pattern)
5. **Per-resource instance `:action` enumeration** — full catalog requires exhaustive bundle grep

---

## 8. Module Status

`core/booking/thunderbird_tess.py` — **patched 2026-05-05, all read methods working:**

| Method | Status | Underlying call |
|---|---|---|
| `get_profile()` | ✅ live | `GET User?userID={tokenUserID}` |
| `get_company(id)` | ✅ live | `GET Company/{id}` |
| `list_trips(page, page_size, **filters)` | ✅ live | paginated Trip query |
| `get_trip(id)` | ✅ live | `GET Trip/{id}` |
| `update_trip(id, dto)` | ⚠️ untested | `PUT Trip/{id}` |
| `list_bookings(page, page_size, **filters)` | ✅ live | paginated Booking query (with Commission) |
| `get_booking(id)` | ✅ live | `GET Booking/{id}` |
| `search_bookings(filters)` | ✅ live | shim → `list_bookings` |
| `update_booking(id, dto)` | ⚠️ untested | `PUT Booking/{id}` |
| `list_clients(page, page_size, **filters)` | ✅ live | paginated Client query (JSON) |
| `get_client(id)` | ✅ live | `GET Client/{id}` |
| `update_client(id, dto)` | ⚠️ untested | `PUT Client/{id}` |
| `list_checks_received(...)` | ✅ live | paginated CheckReceived query |
| `get_check_received(id)` | ✅ live | `GET CheckReceived/{id}` |
| `list_checks_paid(...)` | ✅ live (empty for D2M) | paginated CheckPaid query |
| `get_commissions()` | ✅ shim | `list_checks_received` (compat) |
| `get_commission_summary()` | ✅ live | local aggregate from CheckReceived |
| `download_check_received_report(id, fmt)` | ✅ live (75 KB PDF confirmed) | `Reporting/CheckReceived?checkID&format` |
| `download_check_paid_report(id, fmt)` | ✅ live | `Reporting/CheckPaid?checkID&format` |
| `download_client_export()` | ✅ live | `Export/ClientExport` (XLSX) |

Methods removed (require write DTO discovery — out of scope):
`create_trip`, `create_booking`, `create_client`. POST/PUT bodies need full DTOs;
add back as each is needed with payload reverse-engineered from the UI.

## 9. Files Generated

All artifacts in `output/tess_map/`:

| File | Purpose |
|---|---|
| `01_static_extract.json` | Resource families from JS bundle |
| `02_live_probe.json` | Live status codes for every resource (initial sweep) |
| `03_action_paths.json` | Explicit action paths found in JS strings |
| `04_action_probe.json` | Live status of action paths |
| `05_deep_js_extract.json` | All `apiServiceBaseUri+` paths + $http calls |
| `06_discovery_probe.json` | Dashboard endpoint guesses (none worked) |
| `07_deep_re.md` | **Background agent's deep reverse-engineering report — the breakthrough** |
| `clients_export.json` | All 17 D2M clients (parsed from XLSX) |
| `clients_export.xlsx` | Raw client export from TESS |

---

*Discovery complete. Auth + read endpoints working live against D2M production data. Write
endpoints (POST/PUT create) deferred until specific consumers surface a need.*
