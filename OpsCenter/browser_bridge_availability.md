# Browser Bridge — Available Tool Catalog
**Status:** ✅ DEPLOYED 2026-07-25 07:57 MT  
**Version:** 0.14.3  
**Service:** Systemd `browser-bridge` (localhost:8765)

---

## Quick Reference

Browser Bridge is now available as an MCP server for AI agents to automate web interactions. Acts as a real Chrome browser with agent control.

**Key facts:**
- Server running on localhost:8765
- Bearer token at ~/.browser-bridge/token
- Chrome extension requires manual load (`chrome://extensions/` → Load unpacked from `/home/john/Thunderbird/tools/browser-bridge/extension/dist`)
- Full docs: `/home/john/Thunderbird/tools/browser-bridge/THUNDERBIRD_INTEGRATION.md`

---

## Available Tool Categories

### DOM Interaction (No banner)
`browser_navigate`, `browser_click`, `browser_type`, `browser_fill_form`, `browser_get_page_text`, `browser_press_key`, `browser_hover`, `browser_drag`, `browser_drop`

### Inspection & Capture
`browser_screenshot`, `browser_snapshot`, `net_capture_start`, `net_capture_get`, `net_capture_stop`, `browser_console_messages`, `browser_network_requests`

### JavaScript (banner-free default)
`browser_eval_js`, `browser_cdp_eval` (shows banner)

### Security Testing (Authorized engagements only)
`authz_matrix`, `request_to_curl`, `jwt_decode`

### Playbooks (Self-healing automation)
`playbook_record_start`, `playbook_record_stop`, `playbook_save`, `playbook_run`, `playbook_list`

### Session & Tabs
`browser_tabs`, `browser_activate`, `browser_close`, `browser_handle_dialog`, `browser_select_option`, `browser_file_upload`

### Utilities
`bridge_status`, `debugger_attach`, `debugger_detach`, `browser_press_key`, `browser_resize`

---

## Immediate Use Cases

| Use Case | Tools | Status |
|---|---|---|
| Regent suite automation | `browser_navigate`, `browser_click`, `playbook_*` | Ready |
| PE price scraping | `browser_navigate`, `net_capture_start`, `net_capture_get` | Ready |
| VacationsToGo form filling | `browser_fill_form`, `browser_screenshot` | Ready |
| D2M booking flow BOLA testing | `authz_matrix` | Ready (auth required) |
| Playbook-based booking flows | `playbook_record_*`, `playbook_run` | Ready |

---

## Deployment Notes

- Service auto-starts at login (systemd)
- Logs: `journalctl --user -u browser-bridge -f`
- Health check: `curl -s http://127.0.0.1:8765/health`
- To uninstall: `cd /home/john/Thunderbird/tools/browser-bridge/server && npm run uninstall-service`

---

**Installation source:** https://github.com/vitalysim/browser-bridge  
**Installed by:** Hale @ 2026-07-25 07:57 MT  
**Commander approval:** Direct order ("build")
