"""
Phantom MCP Builder — Self-Expanding Toolbox for Thunderbird OS
================================================================

Dreams2Memories Travel, LLC · Thunderbird OS

When the wing hits a task it can't do with existing MCP tools, Phantom:
  1. Identifies the capability gap (via Claude Haiku)
  2. Generates an MCP tool stub matching travel_mcp_server.py conventions
  3. Validates Python syntax (ast.parse)
  4. Backs up the server file
  5. Appends the new tool BEFORE the `if __name__` block
  6. Reloads the MCP server (systemctl)
  7. Tests the new tool (MCP tools/list probe)
  8. Logs everything to logs/phantom_mcp_builds.log

Usage:
    from phantom_mcp_builder import PhantomMCPBuilder
    builder = PhantomMCPBuilder()
    result = builder.build("I need to check the current EUR/USD exchange rate")

CLI:
    python3 phantom_mcp_builder.py build "task description"
    python3 phantom_mcp_builder.py identify "task description"
    python3 phantom_mcp_builder.py list-builds
"""

import ast
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
THUNDERBIRD_DIR = Path(__file__).resolve().parent.parent.parent  # ~/Thunderbird
MCP_SERVER_PATH = Path(__file__).resolve().parent / "travel_mcp_server.py"
BUILD_LOG_PATH = THUNDERBIRD_DIR / "logs" / "phantom_mcp_builds.log"
ENV_PATH = THUNDERBIRD_DIR / ".env"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger("phantom_mcp_builder")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s [PHANTOM] %(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)


def _load_api_key() -> str:
    """Load ANTHROPIC_API_KEY from .env."""
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            line = line.strip()
            if line.startswith("ANTHROPIC_API_KEY="):
                val = line.split("=", 1)[1].strip().strip("'\"")
                if val:
                    return val
    # Fallback to env var
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY not found in .env or environment. "
            f"Checked: {ENV_PATH}"
        )
    return key


# ============================================================================
# PHANTOM MCP BUILDER
# ============================================================================


class PhantomMCPBuilder:
    """
    Self-building MCP tool generator.
    When Thunderbird OS identifies a capability gap, this class generates
    and registers new MCP tools automatically.
    """

    # The model used for gap identification — Haiku for cost efficiency
    IDENTIFY_MODEL = "claude-haiku-4-5-20251001"

    # Marker line that precedes the __main__ block in travel_mcp_server.py
    SERVER_TAIL_MARKER = "if __name__ == \"__main__\":"
    SERVER_SECTION_MARKER = "# SERVER INITIALIZATION"

    def __init__(self, server_path: Optional[Path] = None, dry_run: bool = False):
        self.server_path = server_path or MCP_SERVER_PATH
        self.dry_run = dry_run
        self._api_key: Optional[str] = None

    @property
    def api_key(self) -> str:
        if self._api_key is None:
            self._api_key = _load_api_key()
        return self._api_key

    # ------------------------------------------------------------------
    # 1. IDENTIFY GAP
    # ------------------------------------------------------------------

    def identify_gap(self, task_description: str) -> Dict[str, Any]:
        """
        Use Claude Haiku to analyze what MCP tool is missing for a given task.

        Returns dict:
            {
                "name": "tool_snake_case_name",
                "description": "One-line tool description",
                "parameters": [
                    {"name": "param1", "type": "str", "description": "...", "required": true}
                ],
                "handler_pseudocode": "Step-by-step logic",
                "annotations": {"readOnlyHint": true/false}
            }
        """
        import anthropic

        client = anthropic.Anthropic(api_key=self.api_key)

        prompt = textwrap.dedent(f"""\
            You are an MCP tool architect for a luxury travel automation system
            called Thunderbird OS (Dreams2Memories Travel, LLC).

            The system already has 120+ tools (cruise search, hotel search, Gmail,
            Google Drive, booking management, intel sweeps, etc.).

            A task FAILED because no existing tool handles it:
            "{task_description}"

            Design a NEW MCP tool to fill this gap. Respond with valid JSON only —
            no markdown fences, no explanation outside the JSON.

            JSON schema:
            {{
                "name": "snake_case_tool_name",
                "description": "One-line description of what the tool does",
                "parameters": [
                    {{
                        "name": "param_name",
                        "type": "str|int|float|bool|Optional[str]",
                        "description": "Parameter description",
                        "required": true,
                        "default": null
                    }}
                ],
                "handler_pseudocode": "Step-by-step implementation logic",
                "annotations": {{
                    "readOnlyHint": true
                }},
                "imports_needed": ["httpx", "etc"],
                "category": "exchange_rates|search|data|communication|intel|booking"
            }}

            Rules:
            - Name must be unique, descriptive, snake_case
            - The tool is async (async def), returns JSON string via json.dumps
            - Parameters use pydantic Field() with descriptions
            - Keep it focused — one tool, one job
            - Include error handling in pseudocode
        """)

        logger.info(f"Identifying gap for: {task_description[:80]}...")
        response = client.messages.create(
            model=self.IDENTIFY_MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = response.content[0].text.strip()

        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)

        try:
            gap = json.loads(raw)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse gap JSON: {e}\nRaw: {raw[:500]}")
            raise ValueError(f"Claude returned invalid JSON: {e}") from e

        # Validate required fields
        required = {"name", "description", "parameters", "handler_pseudocode"}
        missing = required - set(gap.keys())
        if missing:
            raise ValueError(f"Gap spec missing required fields: {missing}")

        logger.info(f"Gap identified: {gap['name']} — {gap['description']}")
        return gap

    # ------------------------------------------------------------------
    # 2. GENERATE TOOL STUB
    # ------------------------------------------------------------------

    def generate_tool_stub(self, gap: Dict[str, Any]) -> str:
        """
        Generate Python function code for the MCP tool, matching
        travel_mcp_server.py conventions exactly.

        Returns the complete tool function as a string.
        """
        name = gap["name"]
        desc = gap["description"]
        params = gap.get("parameters", [])
        pseudocode = gap.get("handler_pseudocode", "# TODO: implement")
        annotations = gap.get("annotations", {"readOnlyHint": True})
        imports_needed = gap.get("imports_needed", [])

        # Build annotations dict string
        ann_str = json.dumps(annotations)
        # Add title from name
        title = name.replace("_", " ").title()
        ann_dict = {"title": title, **annotations}
        ann_str = json.dumps(ann_dict)

        # Build parameter lines
        param_lines = []
        for p in params:
            ptype = p.get("type", "str")
            pdesc = p.get("description", "")
            required = p.get("required", True)
            default = p.get("default")

            # Map type strings to Python types
            type_map = {
                "str": "str",
                "int": "int",
                "float": "float",
                "bool": "bool",
                "Optional[str]": "Optional[str]",
                "Optional[int]": "Optional[int]",
                "Optional[float]": "Optional[float]",
                "Optional[bool]": "Optional[bool]",
            }
            py_type = type_map.get(ptype, "str")

            if required:
                field_str = f'Field(..., description="{pdesc}")'
            elif default is not None:
                field_str = f'Field({json.dumps(default)}, description="{pdesc}")'
            else:
                field_str = f'Field(None, description="{pdesc}")'

            param_lines.append(f"    {p['name']}: {py_type} = {field_str}")

        params_block = ",\n".join(param_lines) if param_lines else ""

        # Build handler body — wrap pseudocode in try/except
        pseudocode_lines = pseudocode.strip().split("\n")
        handler_comment = "\n".join(
            f"        # {line.strip()}" for line in pseudocode_lines
        )

        # Build import block (at top of stub, as comments — actual imports
        # should already be available in the server module scope)
        import_note = ""
        if imports_needed:
            import_note = (
                "\n# Phantom: This tool may need: "
                + ", ".join(imports_needed)
                + "\n"
            )

        code = textwrap.dedent(f"""\

# ============================================================================
# PHANTOM-GENERATED TOOL: {name}
# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# Gap: {desc}
# ============================================================================
{import_note}
@mcp.tool(
    name="{name}",
    annotations={ann_str},
)
async def {name}(
{params_block}
) -> str:
    \"\"\"{desc}\"\"\"
    try:
        logger.info(f"[PHANTOM] {name} called")
{handler_comment}
        result = {{
            "status": "success",
            "tool": "{name}",
            "message": "Phantom-generated tool executed",
            "requires_implementation": "Replace this stub with actual logic",
        }}
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"[PHANTOM] {name} error: {{e}}")
        return json.dumps({{"error": str(e), "tool": "{name}"}}, indent=2)
""")

        return code

    # ------------------------------------------------------------------
    # 3. VALIDATE SYNTAX
    # ------------------------------------------------------------------

    @staticmethod
    def validate_syntax(code: str) -> bool:
        """Validate that the generated code is syntactically valid Python."""
        # Wrap in a minimal context so the decorators/imports resolve
        test_module = textwrap.dedent("""\
            import json
            from typing import Optional
            from pydantic import Field

            class _FakeMCP:
                def tool(self, **kw):
                    def _dec(fn): return fn
                    return _dec

            mcp = _FakeMCP()

            class _Logger:
                def info(self, *a, **kw): pass
                def error(self, *a, **kw): pass

            logger = _Logger()
        """) + code

        try:
            ast.parse(test_module)
            return True
        except SyntaxError as e:
            logger.error(f"Syntax validation failed: {e}")
            return False

    # ------------------------------------------------------------------
    # 4. APPEND TO SERVER
    # ------------------------------------------------------------------

    def append_to_server(self, tool_code: str, tool_name: str) -> bool:
        """
        Safely append new tool to travel_mcp_server.py.

        - Creates a backup at travel_mcp_server.py.bak
        - Inserts BEFORE the SERVER INITIALIZATION comment/if-__name__ block
        - Validates the complete file parses after edit
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Would append {tool_name} to {self.server_path}")
            return True

        if not self.server_path.exists():
            logger.error(f"Server file not found: {self.server_path}")
            return False

        content = self.server_path.read_text()

        # Check for duplicate tool name
        if f'name="{tool_name}"' in content:
            logger.error(f"Tool '{tool_name}' already exists in server file")
            return False

        # Find insertion point — before SERVER INITIALIZATION section
        # Look for the comment block preceding if __name__
        insertion_markers = [
            "\n# ============================================================================\n# SERVER INITIALIZATION",
            "\nif __name__ == \"__main__\":",
        ]

        insert_pos = -1
        for marker in insertion_markers:
            pos = content.rfind(marker)
            if pos > 0:
                insert_pos = pos
                break

        if insert_pos < 0:
            logger.error("Could not find insertion point in server file")
            return False

        # Create backup
        backup_path = self.server_path.with_suffix(".py.bak")
        shutil.copy2(self.server_path, backup_path)
        logger.info(f"Backup created: {backup_path}")

        # Insert the tool code
        new_content = content[:insert_pos] + tool_code + "\n" + content[insert_pos:]

        # Validate the complete file parses
        try:
            ast.parse(new_content)
        except SyntaxError as e:
            logger.error(f"Post-edit syntax check failed: {e}")
            logger.info("Restoring from backup")
            shutil.copy2(backup_path, self.server_path)
            return False

        # Write the updated file
        self.server_path.write_text(new_content)
        logger.info(f"Tool '{tool_name}' appended to {self.server_path}")
        return True

    # ------------------------------------------------------------------
    # 5. RELOAD SERVER
    # ------------------------------------------------------------------

    @staticmethod
    def reload_server() -> Dict[str, Any]:
        """Signal MCP server to reload via systemctl."""
        result = {"action": "reload", "status": "unknown"}

        try:
            # Check if service is running
            check = subprocess.run(
                ["systemctl", "is-active", "thunderbird-mcp.service"],
                capture_output=True, text=True, timeout=10,
            )
            is_active = check.stdout.strip() == "active"

            if not is_active:
                result["status"] = "skipped"
                result["reason"] = "thunderbird-mcp.service is not running"
                logger.info("MCP service not running — reload skipped")
                return result

            # Restart the service
            restart = subprocess.run(
                ["sudo", "systemctl", "restart", "thunderbird-mcp.service"],
                capture_output=True, text=True, timeout=30,
            )
            if restart.returncode == 0:
                result["status"] = "success"
                logger.info("MCP service restarted successfully")
            else:
                result["status"] = "error"
                result["stderr"] = restart.stderr.strip()
                logger.error(f"MCP restart failed: {restart.stderr.strip()}")

        except subprocess.TimeoutExpired:
            result["status"] = "timeout"
            logger.error("systemctl command timed out")
        except FileNotFoundError:
            result["status"] = "skipped"
            result["reason"] = "systemctl not found"
            logger.info("systemctl not available — reload skipped")
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            logger.error(f"Reload failed: {e}")

        return result

    # ------------------------------------------------------------------
    # 6. TEST TOOL
    # ------------------------------------------------------------------

    def test_tool(self, tool_name: str) -> Dict[str, Any]:
        """
        Verify the new tool loaded by checking MCP tools/list endpoint.
        """
        if self.dry_run:
            return {"status": "skipped", "reason": "dry_run mode"}

        result = {"tool": tool_name, "status": "unknown"}

        try:
            import httpx

            # Send MCP JSON-RPC tools/list request
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
                "params": {},
            }
            with httpx.Client(timeout=10) as client:
                resp = client.post(
                    "http://127.0.0.1:8765/mcp",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )

            if resp.status_code == 200:
                data = resp.json()
                tools = data.get("result", {}).get("tools", [])
                tool_names = [t.get("name") for t in tools]
                if tool_name in tool_names:
                    result["status"] = "verified"
                    result["message"] = f"Tool '{tool_name}' found in MCP tools/list"
                else:
                    result["status"] = "not_found"
                    result["message"] = (
                        f"Tool '{tool_name}' NOT in tools/list "
                        f"({len(tool_names)} tools loaded)"
                    )
            else:
                result["status"] = "error"
                result["http_status"] = resp.status_code

        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            logger.warning(f"Tool test failed (server may be offline): {e}")

        return result

    # ------------------------------------------------------------------
    # 7. LOG BUILD
    # ------------------------------------------------------------------

    @staticmethod
    def log_build(
        gap: Dict[str, Any],
        tool_name: str,
        success: bool,
        dry_run: bool = False,
        error: Optional[str] = None,
    ) -> None:
        """Append build record to phantom_mcp_builds.log."""
        BUILD_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

        entry = {
            "timestamp": datetime.now().isoformat(),
            "tool_name": tool_name,
            "description": gap.get("description", ""),
            "category": gap.get("category", "unknown"),
            "success": success,
            "dry_run": dry_run,
            "parameters": [p.get("name") for p in gap.get("parameters", [])],
        }
        if error:
            entry["error"] = error

        line = json.dumps(entry) + "\n"
        with open(BUILD_LOG_PATH, "a") as f:
            f.write(line)

        logger.info(
            f"Build logged: {tool_name} "
            f"({'SUCCESS' if success else 'FAILED'}"
            f"{' [DRY RUN]' if dry_run else ''})"
        )

    # ------------------------------------------------------------------
    # 8. BUILD — FULL PIPELINE
    # ------------------------------------------------------------------

    def build(self, task_description: str) -> Dict[str, Any]:
        """
        Full Phantom pipeline: identify -> generate -> validate -> append
        -> reload -> test -> log.

        Returns a summary dict with all step results.
        """
        result = {
            "task": task_description,
            "dry_run": self.dry_run,
            "steps": {},
            "success": False,
        }

        # Step 1: Identify the gap
        try:
            gap = self.identify_gap(task_description)
            result["steps"]["identify"] = {"status": "ok", "gap": gap}
        except Exception as e:
            result["steps"]["identify"] = {"status": "error", "error": str(e)}
            self.log_build(
                {"description": task_description}, "unknown", False,
                dry_run=self.dry_run, error=str(e),
            )
            return result

        tool_name = gap["name"]
        result["tool_name"] = tool_name

        # Step 2: Generate tool stub
        try:
            tool_code = self.generate_tool_stub(gap)
            result["steps"]["generate"] = {
                "status": "ok",
                "code_length": len(tool_code),
            }
        except Exception as e:
            result["steps"]["generate"] = {"status": "error", "error": str(e)}
            self.log_build(gap, tool_name, False, dry_run=self.dry_run, error=str(e))
            return result

        # Step 3: Validate syntax
        if self.validate_syntax(tool_code):
            result["steps"]["validate"] = {"status": "ok"}
        else:
            result["steps"]["validate"] = {"status": "error", "error": "syntax invalid"}
            self.log_build(gap, tool_name, False, dry_run=self.dry_run, error="syntax")
            return result

        # Step 4: Append to server
        try:
            appended = self.append_to_server(tool_code, tool_name)
            result["steps"]["append"] = {
                "status": "ok" if appended else "error",
                "dry_run": self.dry_run,
            }
            if not appended and not self.dry_run:
                self.log_build(
                    gap, tool_name, False, dry_run=self.dry_run, error="append failed",
                )
                return result
        except Exception as e:
            result["steps"]["append"] = {"status": "error", "error": str(e)}
            self.log_build(gap, tool_name, False, dry_run=self.dry_run, error=str(e))
            return result

        # Step 5: Reload server (skip in dry_run)
        if not self.dry_run:
            reload_result = self.reload_server()
            result["steps"]["reload"] = reload_result
        else:
            result["steps"]["reload"] = {"status": "skipped", "reason": "dry_run"}

        # Step 6: Test tool
        test_result = self.test_tool(tool_name)
        result["steps"]["test"] = test_result

        # Step 7: Log
        result["success"] = True
        result["tool_code"] = tool_code
        self.log_build(gap, tool_name, True, dry_run=self.dry_run)

        return result

    # ------------------------------------------------------------------
    # LIST BUILDS
    # ------------------------------------------------------------------

    @staticmethod
    def list_builds(limit: int = 20) -> list:
        """Return recent build log entries."""
        if not BUILD_LOG_PATH.exists():
            return []
        lines = BUILD_LOG_PATH.read_text().strip().splitlines()
        entries = []
        for line in lines[-limit:]:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                pass
        return entries


# ============================================================================
# CLI INTERFACE
# ============================================================================


def main():
    """CLI entry point for Phantom MCP Builder."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  phantom_mcp_builder.py build   \"task description\"")
        print("  phantom_mcp_builder.py identify \"task description\"")
        print("  phantom_mcp_builder.py list-builds")
        print()
        print("Options:")
        print("  --dry-run    Generate and validate but don't modify server")
        sys.exit(1)

    command = sys.argv[1]
    dry_run = "--dry-run" in sys.argv
    args = [a for a in sys.argv[2:] if a != "--dry-run"]

    builder = PhantomMCPBuilder(dry_run=dry_run)

    if command == "build":
        if not args:
            print("Error: provide a task description")
            sys.exit(1)
        task = " ".join(args)
        result = builder.build(task)
        print(json.dumps(result, indent=2, default=str))
        sys.exit(0 if result["success"] else 1)

    elif command == "identify":
        if not args:
            print("Error: provide a task description")
            sys.exit(1)
        task = " ".join(args)
        gap = builder.identify_gap(task)
        print(json.dumps(gap, indent=2))

    elif command == "list-builds":
        builds = builder.list_builds()
        if not builds:
            print("No builds recorded yet.")
        else:
            for b in builds:
                ts = b.get("timestamp", "?")
                name = b.get("tool_name", "?")
                ok = "OK" if b.get("success") else "FAIL"
                dry = " [DRY RUN]" if b.get("dry_run") else ""
                print(f"  [{ts}] {name} — {ok}{dry}")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
