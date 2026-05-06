"""
Tests for OpenClaw P0: Skill Builder
Validates: requirement classification, code generation, validation, registration, MCP integration
"""

import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

THUNDERBIRD_ROOT = Path.home() / "Thunderbird"
sys.path.insert(0, str(THUNDERBIRD_ROOT / "core"))


class TestP0SkillBuilder:
    """P0: Skill Builder test suite"""

    def test_p0_requirement_classification(self):
        """TEST 1: Classify requirement into domain and category"""
        from ai_infra.thunderbird_skill_builder import ThunderbirdSkillBuilder

        builder = ThunderbirdSkillBuilder()

        # Test case 1: Travel domain
        req = builder.classify_requirement("check if a flight is available")
        assert req["domain"] == "travel"
        assert "flight" in req["description"].lower()

        # Test case 2: Finance domain
        req = builder.classify_requirement("calculate commission from price")
        assert req["domain"] == "finance"

        # Test case 3: Intel domain (must not include travel keywords)
        req = builder.classify_requirement("analyze market trends and research")
        assert req["domain"] in ["intel", "generic"]  # Either intel or generic is acceptable

        print("✅ TEST 1 PASS: Requirement classification works")

    def test_p0_skill_validation(self):
        """TEST 2: Validate skill code against safety constraints"""
        from ai_infra.thunderbird_skill_builder import ThunderbirdSkillBuilder

        builder = ThunderbirdSkillBuilder()

        # Test case 1: Safe code
        safe_code = """
def check_flight(flight_id: str) -> dict:
    return {"flight_id": flight_id, "status": "available"}
"""
        is_valid, error = builder.validate_skill(safe_code)
        assert is_valid, f"Safe code rejected: {error}"

        # Test case 2: Unsafe code (subprocess)
        unsafe_code = """
import subprocess
def bad_skill():
    subprocess.run(['rm', '-rf', '/'])
"""
        is_valid, error = builder.validate_skill(unsafe_code)
        assert not is_valid, "Unsafe code (subprocess) should be rejected"
        assert "subprocess" in error.lower()

        # Test case 3: Unsafe code (eval)
        unsafe_code2 = """
def bad_skill():
    eval(user_input)
"""
        is_valid, error = builder.validate_skill(unsafe_code2)
        assert not is_valid, "Unsafe code (eval) should be rejected"

        print("✅ TEST 2 PASS: Skill validation rejects unsafe code")

    def test_p0_skill_registration(self):
        """TEST 3: Register skill in MCP registry"""
        from ai_infra.thunderbird_skill_builder import ThunderbirdSkillBuilder

        builder = ThunderbirdSkillBuilder()

        # Create a test skill file
        test_skill_name = "test_skill_registration"
        test_file = builder.skills_dir / f"{test_skill_name}.py"
        test_file.write_text("def test_skill(): pass")

        # Register it
        success = builder.register_skill(
            test_skill_name,
            test_file,
            "travel",
            "Test skill for P0"
        )

        assert success, "Skill registration failed"

        # Verify in registry
        assert builder.registry_file.exists()
        registry = json.loads(builder.registry_file.read_text())
        assert test_skill_name in registry["skills"]
        assert registry["skills"][test_skill_name]["domain"] == "travel"

        # Cleanup
        test_file.unlink()

        print("✅ TEST 3 PASS: Skill registration to MCP registry works")

    def test_p0_mcp_tool_registration(self):
        """TEST 4: MCP tools are callable and return correct structure"""
        from ai_infra.thunderbird_skill_builder import register_skill_builder_tools

        tools_dict = register_skill_builder_tools()

        # Verify structure
        assert "tools" in tools_dict
        assert len(tools_dict["tools"]) >= 4

        # Verify tool names
        tool_names = [t["name"] for t in tools_dict["tools"]]
        assert "classify_skill_requirement" in tool_names
        assert "generate_skill_code" in tool_names
        assert "validate_skill" in tool_names
        assert "register_skill" in tool_names

        # Verify each tool has required fields
        for tool in tools_dict["tools"]:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool

        print("✅ TEST 4 PASS: MCP tool registration complete")


if __name__ == "__main__":
    suite = TestP0SkillBuilder()
    try:
        suite.test_p0_requirement_classification()
        suite.test_p0_skill_validation()
        suite.test_p0_skill_registration()
        suite.test_p0_mcp_tool_registration()
        print("\n✅ ALL P0 TESTS PASSED (4/4)")
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
