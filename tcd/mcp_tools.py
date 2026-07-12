"""
tcd.mcp_tools — expose the TCD data plane + write-back loop as real MCP tools.

2026-07-13: the tcd/ package was CLI/timer-only — Antigravity (or any MCP
client) had no direct handle on it, only the raw sheets_read_data/write_data
tools, which would force reimplementing the schema logic (stage derivation,
dispose-at-source, comment-log formatting to hale_decisions.md) in-context on
every call. These tools wrap the already-tested tcd/ functions instead, so
"AppSheet as backing, Thunderbird as core, Antigravity as an operator" reuses
the real engine rather than duplicating it.

register_tcd_tools(mcp) follows the same pattern as every other module in
core/mcp/travel_mcp_server.py (e.g. register_dossier_scanner_tools).
"""
import json


def register_tcd_tools(mcp_server):
    """Register TCD board tools with the MCP server."""

    @mcp_server.tool(
        name="tcd_get_items",
        annotations={"title": "Get TCD Board Items", "readOnlyHint": True},
    )
    async def tcd_get_items_tool(
        inbox: str = "", stage: str = "", status: str = "",
    ) -> str:
        """Read the current TCD board state from the live Google Sheet.

        Optional filters: inbox (strategic|operational|reference),
        stage (P|D|T|A|C|REF), status (OPEN|REF|DISPOSE). Empty = no filter.
        Read-only — does not trigger a sync or write-back pass.
        """
        from . import writeback
        rows = writeback.read_sheet_rows()
        if inbox:
            rows = [r for r in rows if r.get("inbox") == inbox]
        if stage:
            rows = [r for r in rows if r.get("stage") == stage]
        if status:
            rows = [r for r in rows if r.get("status") == status]
        return json.dumps({"count": len(rows), "items": rows}, indent=2, ensure_ascii=False)

    @mcp_server.tool(
        name="tcd_sync_now",
        annotations={"title": "Sync TCD Board Now", "readOnlyHint": False},
    )
    async def tcd_sync_now_tool(include_gmail: bool = True) -> str:
        """Push the current Thunderbird state (Gmail/Calendar/Drive/Keep/SMS/
        internal) to the TCD Sheet — on-demand instead of waiting for the
        (currently disabled) 10-minute timer. Runs a write-back pass first
        (see tcd_process_writeback) so AppSheet edits aren't clobbered by the
        fresh write. Idempotent — safe to call repeatedly.
        """
        from . import sheet_sync
        rows = sheet_sync.collect_rows(include_gmail=include_gmail)
        # Reuse _live_sync's real Google-API path rather than duplicating it.
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            sheet_sync._live_sync(include_gmail=include_gmail)
        return json.dumps({
            "status": "synced", "row_count": len(rows), "log": buf.getvalue().strip(),
        }, indent=2)

    @mcp_server.tool(
        name="tcd_process_writeback",
        annotations={"title": "Process TCD Write-Back", "readOnlyHint": False},
    )
    async def tcd_process_writeback_tool() -> str:
        """Act on Commander/staff edits made in AppSheet since the last pass:
        status=DISPOSE triggers a REAL cascade delete at the source
        (Gmail-trash, standing-orders/dossiers, hale_state entries), stage
        moves and new comments are logged to hale_decisions.md. This is the
        real, tested dispose-at-source engine — the same one the (currently
        disabled) 10-minute timer calls. Never raises for a single row's
        failure; failures are collected in the returned "errors" list.
        """
        from . import writeback
        result = writeback.process_once()
        return json.dumps(result, indent=2, ensure_ascii=False)
