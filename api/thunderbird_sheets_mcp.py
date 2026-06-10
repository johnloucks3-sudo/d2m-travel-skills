"""
Dreams2Memories Google Sheets MCP Module
=========================================

Extends the travel MCP server with Google Sheets operations:
- List sheet tabs in a spreadsheet
- Read cell data from ranges
- Write data to ranges
- Append rows
- Create new spreadsheets
- Get spreadsheet metadata

Auth: Uses thunderbird_google_auth.get_sheets() — the unified OAuth token
      with the spreadsheets scope already granted.

Integrates with: travel_mcp_server.py
Dependencies: google-api-python-client (via thunderbird_google_auth)
"""

import json
import logging
from typing import Any

from pydantic import Field
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)


def register_sheets_mcp_tools(mcp: FastMCP):
    """Register all Google Sheets tools with the MCP server.

    Each tool is a @mcp.tool() decorated function that returns a JSON string.
    Errors are caught and returned as structured JSON — never thrown.
    """
    try:
        from api.thunderbird_google_auth import get_sheets
    except ImportError as e:
        logger.error(f"Failed to import get_sheets: {e}")
        _register_fallback_tools(mcp, f"Import error: {e}")
        return

    # ------------------------------------------------------------------
    # 1. sheets_list_sheets
    # ------------------------------------------------------------------
    @mcp.tool(
        name="sheets_list_sheets",
        annotations={
            "title": "List Sheet Tabs in Spreadsheet",
            "readOnlyHint": True,
        },
    )
    async def sheets_list_sheets(
        spreadsheet_id: str = Field(
            ..., description="Google Sheets spreadsheet ID (from the URL)"
        ),
    ) -> str:
        """List all sheet tabs in a spreadsheet with their properties."""
        try:
            service = get_sheets()
            spreadsheet = (
                service.spreadsheets()
                .get(spreadsheetId=spreadsheet_id, fields="sheets.properties")
                .execute()
            )
            sheets = spreadsheet.get("sheets", [])
            result = []
            for s in sheets:
                props = s.get("properties", {})
                result.append(
                    {
                        "sheetId": props.get("sheetId"),
                        "title": props.get("title"),
                        "index": props.get("index"),
                        "rowCount": props.get("gridProperties", {}).get("rowCount"),
                        "columnCount": props.get("gridProperties", {}).get("columnCount"),
                    }
                )
            return json.dumps(
                {"status": "success", "count": len(result), "sheets": result}, indent=2
            )
        except Exception as e:
            logger.error(f"sheets_list_sheets error: {e}")
            return json.dumps({"error": str(e), "type": "sheets_error"})

    # ------------------------------------------------------------------
    # 2. sheets_read_data
    # ------------------------------------------------------------------
    @mcp.tool(
        name="sheets_read_data",
        annotations={
            "title": "Read Cell Data from Sheet",
            "readOnlyHint": True,
        },
    )
    async def sheets_read_data(
        spreadsheet_id: str = Field(
            ..., description="Google Sheets spreadsheet ID"
        ),
        sheet_name: str = Field(
            ..., description="Sheet tab name (e.g. 'Sheet1')"
        ),
        range_str: str = Field(
            "",
            description=(
                "A1 notation range (e.g. 'A1:C10'). "
                "Leave empty to read the entire sheet."
            ),
        ),
    ) -> str:
        """Read cell data from a sheet range. Returns a 2D array of values."""
        try:
            service = get_sheets()
            # Build the range string
            if range_str:
                full_range = f"'{sheet_name}'!{range_str}"
            else:
                full_range = sheet_name

            result = (
                service.spreadsheets()
                .values()
                .get(spreadsheetId=spreadsheet_id, range=full_range)
                .execute()
            )
            values = result.get("values", [])

            return json.dumps(
                {
                    "status": "success",
                    "range": result.get("range", ""),
                    "rows": len(values),
                    "values": values,
                },
                indent=2,
            )
        except Exception as e:
            logger.error(f"sheets_read_data error: {e}")
            return json.dumps({"error": str(e), "type": "sheets_error"})

    # ------------------------------------------------------------------
    # 3. sheets_write_data
    # ------------------------------------------------------------------
    @mcp.tool(
        name="sheets_write_data",
        annotations={
            "title": "Write Data to Sheet Range",
            "readOnlyHint": False,
        },
    )
    async def sheets_write_data(
        spreadsheet_id: str = Field(
            ..., description="Google Sheets spreadsheet ID"
        ),
        sheet_name: str = Field(
            ..., description="Sheet tab name (e.g. 'Sheet1')"
        ),
        range_str: str = Field(
            ...,
            description=(
                "A1 notation range to write to (e.g. 'A1:C3'). "
                "Must be provided — the write target."
            ),
        ),
        values_json: str = Field(
            ...,
            description=(
                "JSON array of arrays with cell values. "
                'Example: [["Name","Age"],["Alice","30"],["Bob","25"]]'
            ),
        ),
    ) -> str:
        """Write data to a specific range in a sheet. Overwrites existing values."""
        try:
            values = json.loads(values_json)
            if not isinstance(values, list):
                return json.dumps(
                    {"error": "values_json must be a JSON array", "type": "validation_error"},
                    indent=2,
                )

            service = get_sheets()
            full_range = f"'{sheet_name}'!{range_str}"
            body = {"values": values}

            result = (
                service.spreadsheets()
                .values()
                .update(
                    spreadsheetId=spreadsheet_id,
                    range=full_range,
                    valueInputOption="USER_ENTERED",
                    body=body,
                )
                .execute()
            )

            return json.dumps(
                {
                    "status": "success",
                    "updated_range": result.get("updatedRange", ""),
                    "updated_cells": result.get("updatedCells", 0),
                    "updated_rows": result.get("updatedRows", 0),
                    "updated_columns": result.get("updatedColumns", 0),
                },
                indent=2,
            )
        except json.JSONDecodeError as e:
            logger.error(f"sheets_write_data JSON parse error: {e}")
            return json.dumps({"error": f"Invalid values_json: {e}", "type": "validation_error"})
        except Exception as e:
            logger.error(f"sheets_write_data error: {e}")
            return json.dumps({"error": str(e), "type": "sheets_error"})

    # ------------------------------------------------------------------
    # 4. sheets_append_row
    # ------------------------------------------------------------------
    @mcp.tool(
        name="sheets_append_row",
        annotations={
            "title": "Append Row(s) to Sheet",
            "readOnlyHint": False,
        },
    )
    async def sheets_append_row(
        spreadsheet_id: str = Field(
            ..., description="Google Sheets spreadsheet ID"
        ),
        sheet_name: str = Field(
            ..., description="Sheet tab name (e.g. 'Sheet1')"
        ),
        values_json: str = Field(
            ...,
            description=(
                "JSON array of values for one row: [\"col1\", \"col2\"]\n"
                "OR array of arrays for multiple rows: [[\"a\",\"b\"],[\"c\",\"d\"]]\n"
                "The API auto-detects the append position."
            ),
        ),
    ) -> str:
        """Append one or more rows to the end of a sheet."""
        try:
            parsed = json.loads(values_json)

            # Normalize: if it's a flat list of scalars, wrap it as a single row
            if parsed and isinstance(parsed[0], str | int | float | bool):
                values = [parsed]
            elif parsed and isinstance(parsed[0], list):
                values = parsed
            else:
                values = [parsed] if parsed else []

            if not values:
                return json.dumps(
                    {"error": "values_json must contain at least one value", "type": "validation_error"},
                    indent=2,
                )

            service = get_sheets()
            body = {"values": values}

            result = (
                service.spreadsheets()
                .values()
                .append(
                    spreadsheetId=spreadsheet_id,
                    range=sheet_name,
                    valueInputOption="USER_ENTERED",
                    insertDataOption="INSERT_ROWS",
                    body=body,
                )
                .execute()
            )

            updates = result.get("updates", {})
            return json.dumps(
                {
                    "status": "success",
                    "updated_range": updates.get("updatedRange", ""),
                    "updated_rows": updates.get("updatedRows", 0),
                    "updated_cells": updates.get("updatedCells", 0),
                    "spreadsheet_id": updates.get("spreadsheetId", spreadsheet_id),
                },
                indent=2,
            )
        except json.JSONDecodeError as e:
            logger.error(f"sheets_append_row JSON parse error: {e}")
            return json.dumps({"error": f"Invalid values_json: {e}", "type": "validation_error"})
        except Exception as e:
            logger.error(f"sheets_append_row error: {e}")
            return json.dumps({"error": str(e), "type": "sheets_error"})

    # ------------------------------------------------------------------
    # 5. sheets_create_spreadsheet
    # ------------------------------------------------------------------
    @mcp.tool(
        name="sheets_create_spreadsheet",
        annotations={
            "title": "Create New Spreadsheet",
            "readOnlyHint": False,
        },
    )
    async def sheets_create_spreadsheet(
        title: str = Field(
            ..., description="Title of the new spreadsheet"
        ),
        sheet_names_json: str = Field(
            '["Sheet1"]',
            description=(
                "JSON array of initial sheet tab names. "
                'Default: ["Sheet1"]'
            ),
        ),
    ) -> str:
        """Create a new Google Sheets spreadsheet with the given title and sheets."""
        try:
            sheet_names = json.loads(sheet_names_json)
            if not isinstance(sheet_names, list) or not sheet_names:
                return json.dumps(
                    {
                        "error": "sheet_names_json must be a non-empty JSON array of strings",
                        "type": "validation_error",
                    },
                    indent=2,
                )

            sheets_body = [
                {"properties": {"title": name}} for name in sheet_names
            ]

            body = {
                "properties": {"title": title},
                "sheets": sheets_body,
            }

            service = get_sheets()
            result = service.spreadsheets().create(body=body).execute()

            return json.dumps(
                {
                    "status": "success",
                    "spreadsheet_id": result.get("spreadsheetId", ""),
                    "title": result.get("properties", {}).get("title", title),
                    "url": result.get("spreadsheetUrl", ""),
                    "sheets": [
                        {
                            "sheetId": s.get("properties", {}).get("sheetId"),
                            "title": s.get("properties", {}).get("title"),
                        }
                        for s in result.get("sheets", [])
                    ],
                },
                indent=2,
            )
        except json.JSONDecodeError as e:
            logger.error(f"sheets_create_spreadsheet JSON parse error: {e}")
            return json.dumps({"error": f"Invalid sheet_names_json: {e}", "type": "validation_error"})
        except Exception as e:
            logger.error(f"sheets_create_spreadsheet error: {e}")
            return json.dumps({"error": str(e), "type": "sheets_error"})

    # ------------------------------------------------------------------
    # 6. sheets_get_spreadsheet_info
    # ------------------------------------------------------------------
    @mcp.tool(
        name="sheets_get_spreadsheet_info",
        annotations={
            "title": "Get Spreadsheet Metadata",
            "readOnlyHint": True,
        },
    )
    async def sheets_get_spreadsheet_info(
        spreadsheet_id: str = Field(
            ..., description="Google Sheets spreadsheet ID"
        ),
    ) -> str:
        """Get spreadsheet metadata: title, URL, owner info, sheets, and permissions."""
        try:
            service = get_sheets()
            spreadsheet = (
                service.spreadsheets()
                .get(
                    spreadsheetId=spreadsheet_id,
                    fields="spreadsheetId,properties,sheets.properties,sheets.protectedRanges,developerMetadata",
                )
                .execute()
            )

            props = spreadsheet.get("properties", {})
            sheets = spreadsheet.get("sheets", [])

            sheet_list = []
            for s in sheets:
                sp = s.get("properties", {})
                sheet_list.append(
                    {
                        "sheetId": sp.get("sheetId"),
                        "title": sp.get("title"),
                        "index": sp.get("index"),
                        "rowCount": sp.get("gridProperties", {}).get("rowCount"),
                        "columnCount": sp.get("gridProperties", {}).get("columnCount"),
                        "hidden": sp.get("hidden", False),
                        "sheetType": sp.get("sheetType", "GRID"),
                        "protectedRanges": len(s.get("protectedRanges", [])),
                    }
                )

            return json.dumps(
                {
                    "status": "success",
                    "spreadsheetId": spreadsheet.get("spreadsheetId"),
                    "title": props.get("title"),
                    "locale": props.get("locale"),
                    "timeZone": props.get("timeZone"),
                    "url": props.get("spreadsheetUrl"),
                    "autoRecalc": props.get("autoRecalc"),
                    "defaultFormat": props.get("defaultFormat"),
                    "sheets": sheet_list,
                    "sheetCount": len(sheet_list),
                },
                indent=2,
            )
        except Exception as e:
            logger.error(f"sheets_get_spreadsheet_info error: {e}")
            return json.dumps({"error": str(e), "type": "sheets_error"})

    logger.info("Google Sheets MCP tools registered successfully")


def _register_fallback_tools(mcp: FastMCP, reason: str):
    """Register fallback tools that return an error message.

    Used when the google API client is not available — users still
    get discoverable tool names with a clear error on invocation.
    """
    tool_names = [
        ("sheets_list_sheets", "List Sheet Tabs in Spreadsheet"),
        ("sheets_read_data", "Read Cell Data from Sheet"),
        ("sheets_write_data", "Write Data to Sheet Range"),
        ("sheets_append_row", "Append Row(s) to Sheet"),
        ("sheets_create_spreadsheet", "Create New Spreadsheet"),
        ("sheets_get_spreadsheet_info", "Get Spreadsheet Metadata"),
    ]

    for name, title in tool_names:
        # Create a closure to capture name and reason
        def make_handler(tool_name: str, err_reason: str):
            async def handler(**kwargs) -> str:
                return json.dumps(
                    {
                        "error": f"Google Sheets not available: {err_reason}",
                        "type": "import_error",
                        "tool": tool_name,
                    },
                    indent=2,
                )
            # Copy annotations for Field params
            handler.__name__ = tool_name
            return handler

        handler = make_handler(name, reason)
        # Add the tool — no annotations needed for error tools
        mcp.tool(name=name, annotations={"title": title, "readOnlyHint": True})(handler)

    logger.warning(f"Google Sheets tools registered as fallbacks (reason: {reason})")


if __name__ == "__main__":
    print("thunderbird_sheets_mcp.py — MCP tool registration module.")
    print("Import and call register_sheets_mcp_tools(mcp) to register tools.")
    print()
    print("Test with:")
    print("  from mcp.server.fastmcp import FastMCP")
    print("  mcp = FastMCP('test')")
    print("  register_sheets_mcp_tools(mcp)")
