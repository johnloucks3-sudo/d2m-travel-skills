"""Mission Board MCP Tools — AGY (Antigravity) capability-gap fix, 2026-07-16.

Commander directive 2026-07-16: give Antigravity (the 3rd Hale seat) real
Mission Board capability, alongside Claude Code and OpenCode.

THE GAP: ~/.gemini/settings.json excludes Antigravity's built-in
run_shell_command / read_file / write_file / edit tools — unlike Claude Code
and OpenCode (both full coding agents with unrestricted shell), AGY cannot
run `python3 OpsCenter/mission_board_sync.py ...` directly. excludeTools
governs gemini-cli's own built-ins only — it does NOT gate MCP tool calls,
and AGY already carries an explicit `mcp(thunderbird-travel/*)` wildcard
grant against this exact server (verified live 2026-07-13, see
project_hale_ag_antigravity_wired.md — the "thunderbird-travel" entry in
~/.gemini/config/mcp_config.json points at this same travel_mcp_server.py
process on 127.0.0.1:8765). So: expose the board here, and AGY gets it for
free the next time this server (thunderbird-mcp.service / thunderbird-mcp-
tailscale.service) restarts — no new server, no new OAuth scope.

Every tool below is a thin wrapper around OpsCenter/mission_board_sync.py's
existing primitives (acquire_lock / load_board / save_board / add_mission /
_find_open_duplicate), reached via the tcd._imports shim already used by
tcd/writeback.py — reused, not reimplemented. mission_board_add() is the
one tool that can't just shell out to process_exec_command(), because that
CLI parser truncates titles to 3 words; it instead calls add_mission()
directly under the same lock/save discipline, so it is STILL the same
single dedup code path as the CLI and TCD's writeback layer, not a fourth
one. See mission_board_sync.py::_find_open_duplicate's REGRESSION FIX note
(2026-07-16) for why that distinction matters — this system has already
been bitten three times by hand-rolled creation paths that skipped dedup.
"""
import json

from tcd._imports import load_mission_board_sync


def _mbs():
    return load_mission_board_sync()


def register_mission_board_tools(mcp):
    @mcp.tool(
        name="mission_board_list",
        annotations={"title": "List Wing Mission Board", "readOnlyHint": True},
    )
    async def mission_board_list(filter: str = "board") -> str:
        """List missions on the Wing Tasking board.

        Args:
            filter: "board" (active missions, default), "suspended", or
                "complete".
        """
        mbs = _mbs()
        try:
            return mbs.process_exec_command(f"list {filter}")
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool(
        name="mission_board_status",
        annotations={"title": "Mission Board — Mission Detail", "readOnlyHint": True},
    )
    async def mission_board_status(mission_id: str) -> str:
        """Show full detail (status, priority, assignment, logs, suspense
        date) for one mission by ID, e.g. "MISSION-042"."""
        mbs = _mbs()
        try:
            return mbs.process_exec_command(f"status {mission_id}")
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool(name="mission_board_add")
    async def mission_board_add(
        title: str,
        description: str = "",
        priority: str = "P2",
        assigned_to: str = "unassigned",
    ) -> str:
        """File a new mission on the Wing Tasking board.

        Runs the SAME open-duplicate check (_find_open_duplicate) the CLI
        and TCD's "Create Task" action both run before creating anything —
        if the title matches an already-open mission (active, in_progress,
        pending, open, or pending_review), no new mission is created; the
        existing mission's id and status are returned instead.

        Args:
            title: Mission title. Unlike the raw `EXEC: add` CLI parser
                (which is limited to 3 words because it splits on
                whitespace), this takes the full string — pass a real
                title, not a truncated one.
            description: Longer description / context / source snippet.
            priority: One of P0, P1, P2, P3 (default P2 — P0 is reserved
                for the Commander/Hale escalation path, not a bare
                default for new AGY-filed missions).
            assigned_to: Staff assignment (default "unassigned").
        """
        mbs = _mbs()
        priority = priority.upper() if priority.upper() in ("P0", "P1", "P2", "P3") else "P2"
        try:
            fd = mbs.acquire_lock()
        except SystemExit:
            return json.dumps({
                "error": "board locked — another process is writing, retry in a few seconds"
            })
        try:
            board = mbs.load_board()
            message, mission_id = mbs.add_mission(
                board,
                title,
                description or "No description",
                priority,
                assigned_to,
                source="agy_mcp_tool",
            )
            mbs.save_board(board, fd)
            return json.dumps({"message": message, "mission_id": mission_id})
        except Exception as e:
            mbs.release_lock(fd)
            return json.dumps({"error": str(e)})

    @mcp.tool(name="mission_board_complete")
    async def mission_board_complete(mission_id: str) -> str:
        """Mark a mission complete by ID, e.g. "MISSION-042"."""
        mbs = _mbs()
        try:
            return mbs.process_exec_command(f"complete {mission_id}")
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool(name="mission_board_log")
    async def mission_board_log(mission_id: str, message: str) -> str:
        """Append a log entry / status update to an existing mission by ID."""
        mbs = _mbs()
        try:
            return mbs.process_exec_command(f"log {mission_id} {message}")
        except Exception as e:
            return json.dumps({"error": str(e)})
