# D2M Google Drive Architecture
## MCP Folder Routing Map
## Updated: 2026-03-05 (post-cleanup)

---

## D2M Root: `1KA_b2flnBHTYVRgl3U7erTFIv_aMH9cb`

### Operational Folders

| Folder | ID | Purpose |
|--------|----|---------|
| Thunderbird_Bookings | `1N3oSIWhsEbcaxK89Axz5rt6ZPehrfkzE` | Processed booking confirmations, T&C, insurance |
| Thunderbird_Bookings_Vault | `12-PZh6pZ1SFBXC_RkNs7pumHfA_2dqIi` | Raw booking PDFs, OCR archive |
| Thunderbird_Proposals | `1g2AlDLEjd71cIL-T0HfIh2ytatPBCgVn` | Client-facing hotel guides, tour quotes, cruise proposals |
| Thunderbird_Templates | `1-zJlm-I8eLQfkYtSbE3Wd2fmKb3-MSk5` | Forms, schemas, itinerary masters |
| Thunderbird_Scribe_Templates | `1KrJvuZnxOGKKlrradcfeFcikkthDWQxv` | Legacy templates (Welcome Kit) |
| Thunderbird_AI_Visuals | `16ZLqRO2864VlS2cTc5SdnreUMsl8M7Pj` | AI-generated destination images |
| Thunderbird_Visuals | `1OMC35GXKVNSGC37eBixPfFmGTPYgUJQX` | Ship photos, brand imagery, SOPs |
| Thunderbird_Knowledge_Base | `1MjjbqQVnzMYpHyAtNu-zZej-1mXhHkGk` | Reference docs, SOPs, EARA configs, strategy |
| Thunderbird_Intel | `1joXoapQQjnGsKzxxvpDhZnO6czlCQGqj` | Ship intel, world intel, daily briefs |
| Thunderbird_Intel_POC | `11ZsaL8k4HgKZkT-CUwGXxn_ZkNFfJ6PQ` | Experimental intel reports |
| Thunderbird_Finance | `1k2-DOzj5GEN6hjIlMND19hk4fQhUq-Tm` | Invoices, commission tracking |
| Thunderbird_Marketing | `1ybRe2FB2gFYSo3FeBx5wnWxfFuZ8qlF6` | Marketing materials, campaigns |
| Thunderbird_Shield_Logistics | `13kqZpAX1IRnrr1B04Pe-m61BdChVFkTT` | Insurance, compliance, timeline rules |
| Thunderbird_Commercial_Ops | `1xigsZQiHeh0WZ0JRN0qWzbWxhoBWmt2D` | Agent portals, supplier agreements |
| Thunderbird_Client_Files | `1l3WIjh2aL_fKEuDITmCIgQysfKVDNMUx` | Per-client subfolders (see below) |

### Other Folders in D2M

| Folder | ID | Notes |
|--------|----|-------|
| EARA_HUD on Chrome | `1oIl4oMwU7Rznhe16rQnqFW0woLkPJwYO` | Chrome extension files |
| Travel Advisor | `1WNryCJv-B7dr0ZEuiuSXjYkjbLzht8QZ` | Legacy LGT client folders (12 subflds, 2 docs) |

---

## Client Folders (inside Thunderbird_Client_Files)

| Client | ID | Items |
|--------|----|-------|
| Loucks, John A III | `174sAduc7mdM9iHtjsg5p_WKjt6oER2Yd` | 10 (archives + CRM) |
| Kuklinski, Kyle | `13UC6D_1oq1_XgWiiHGFFHUXMdqV_4Iye` | 38 (Panama Canal booking) |
| Kuklinski, Nick | `1-RVpq0XvDXeNuMwUsC6ETa5jKAvcXNfQ` | 0 (new) |
| Morton, Joshua | `149HYqTbzqASWo9_8PQTdi56zTTxA4_cX` | 0 (new) |
| McLeod, Erik | `1uw4BDWPu3q-HG4ETL6gsMpAxM3vlETUh` | 20 |
| Furlow, John Charles | `14wfPo6HurWaOKrlCzFWhD_kf15Pvgl0d` | 5 |
| Ely, Alfred | `1fTRMpPemTcuXE-XGCiHpZMrhrs1oyA5N` | 3 |
| Nichols, Larry | `1mlNmCJ3Rs-HS5IftzGmaW-Dra6ydQFdE` | 3 |
| Westbrook, Ronald L | `1hkJvLp0_O_HGpv8ffWQIODUXdDGfDXPh` | 0 |
| Guest One | `1yGa6U0MroxWa_WOK3M4dGI_O2ZKDMhOX` | 2 (placeholder) |
| CRUISES AND TOURS UNLIMITED | `1XAK7lwnrlhUaLqhaDAHEyQf2EcQvCddJ` | 0 (host agency?) |

### Loucks Subfolder

| Folder | ID |
|--------|----|
| Booking_Archives | `1sJzrnnyYYgw3WD2a_8kCGW8p8JfaVyee` |

---

## MCP Tool → Folder Routing

| Tool Output | Target Folder ID | Folder Name |
|-------------|------------------|-------------|
| `render_hotel_quote_pdf` | `1g2AlDLEjd71cIL-T0HfIh2ytatPBCgVn` | Thunderbird_Proposals |
| `render_tour_quote_pdf` | `1g2AlDLEjd71cIL-T0HfIh2ytatPBCgVn` | Thunderbird_Proposals |
| `render_flight_quote_pdf` | `1g2AlDLEjd71cIL-T0HfIh2ytatPBCgVn` | Thunderbird_Proposals |
| `extract_pdf_booking_details` | `1N3oSIWhsEbcaxK89Axz5rt6ZPehrfkzE` | Thunderbird_Bookings |
| `extract_pdf_itinerary` | `1N3oSIWhsEbcaxK89Axz5rt6ZPehrfkzE` | Thunderbird_Bookings |
| `run_ship_intelligence_sweep` | `1joXoapQQjnGsKzxxvpDhZnO6czlCQGqj` | Thunderbird_Intel |
| `run_world_intelligence_sweep` | `1joXoapQQjnGsKzxxvpDhZnO6czlCQGqj` | Thunderbird_Intel |
| `generate_ship_comparison_*` | `1joXoapQQjnGsKzxxvpDhZnO6czlCQGqj` | Thunderbird_Intel |
| `generate_weekly_report` | `1k2-DOzj5GEN6hjIlMND19hk4fQhUq-Tm` | Thunderbird_Finance |
| `generate_itinerary_images` | `16ZLqRO2864VlS2cTc5SdnreUMsl8M7Pj` | Thunderbird_AI_Visuals |
| Raw booking PDFs (upload) | `12-PZh6pZ1SFBXC_RkNs7pumHfA_2dqIi` | Thunderbird_Bookings_Vault |
| Client-specific files | Look up client folder by name | Thunderbird_Client_Files/* |

---

## Auth Configuration

| Method | Token | Scope | Permissions |
|--------|-------|-------|-------------|
| OAuth 2.0 (primary) | `~/Thunderbird/drive_token.json` | `drive` | Full: move, delete, create, rename |
| Service Account (fallback) | `~/Thunderbird/credentials.json` | `drive` | Limited: rename, create, read (no reparent) |
| OAuth client ID | `~/Thunderbird/gmail_oauth_credentials.json` | Shared with Gmail | Desktop app flow |

Re-authorize: `python3 thunderbird_drive.py --authorize`

---

## Cleanup Log (2026-03-05)

- 10 TITAN folders renamed to Thunderbird_* and moved into D2M
- 48 loose files sorted from D2M root into correct folders
- 18 Loucks archive files consolidated into Booking_Archives subfolder
- 9 Loucks CRM/history docs moved to canonical folder
- 11 empty Loucks Russian-doll folders trashed
- 20 spam/email files trashed from Travel Advisor
- 2 new client folders created (Kuklinski Nick, Morton Joshua)
- 4 new operational folders created (Templates, AI_Visuals, Proposals, Bookings)
- OAuth Drive access established for full move/delete permissions
- `drive_delete_file` tool added (trash, not permanent delete)
