"""
Test Suite for Thunderbird Skill Builder

Covers:
- Code generation quality
- Constraint validation
- Hot-reload integration
- Metadata handling
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from core.ai_infra.thunderbird_skill_builder import (
    ThunderbirdSkillBuilder,
    SkillIntent,
    SkillDomain,
    SkillConstraintError,
    SkillGenerationError,
)
from core.ai_infra.skill_builder_config import (
    validate_skill_constraint,
    validate_skill_name,
    DEFAULT_CONSTRAINTS,
)


# ============================================================================
# TEST DATA & FIXTURES
# ============================================================================

@pytest.fixture
def temp_thunderbird_root():
    """Create temporary Thunderbird directory structure"""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "core" / "travel").mkdir(parents=True)
        (root / "core" / "intel").mkdir(parents=True)
        (root / "core" / "ops").mkdir(parents=True)
        (root / "tests").mkdir(parents=True)
        yield root


@pytest.fixture
def skill_builder(temp_thunderbird_root):
    """Create SkillBuilder instance with temporary directory"""
    return ThunderbirdSkillBuilder(thunderbird_root=temp_thunderbird_root)


# ============================================================================
# UNIT TESTS — CLASSIFICATION
# ============================================================================

class TestSkillClassification:
    """Test intent classification from requirements"""

    def test_classify_travel_skill(self, skill_builder):
        """Classify hotel/cruise/flight requirements as TRAVEL domain"""
        intent = skill_builder._classify_requirement("Check hotel prices in Paris")
        assert intent.domain == SkillDomain.TRAVEL

        intent = skill_builder._classify_requirement("Find available Silversea cabins")
        assert intent.domain == SkillDomain.TRAVEL

    def test_classify_intel_skill(self, skill_builder):
        """Classify research/monitoring requirements as INTEL domain"""
        intent = skill_builder._classify_requirement("Monitor cruise line news")
        assert intent.domain == SkillDomain.INTEL

        intent = skill_builder._classify_requirement("Scan competitor pricing")
        assert intent.domain == SkillDomain.INTEL

    def test_classify_email_skill(self, skill_builder):
        """Classify email/draft requirements as EMAIL domain"""
        intent = skill_builder._classify_requirement("Format validation emails")
        assert intent.domain == SkillDomain.EMAIL

    def test_classify_finance_skill(self, skill_builder):
        """Classify price/cost requirements as FINANCE domain"""
        intent = skill_builder._classify_requirement("Calculate commissions")
        assert intent.domain == SkillDomain.FINANCE

    def test_classify_ops_skill(self, skill_builder):
        """Classify task/queue requirements as OPS domain"""
        intent = skill_builder._classify_requirement("Manage mission board tasks")
        assert intent.domain == SkillDomain.OPS

    def test_skill_name_generation(self, skill_builder):
        """Generate valid skill name from requirement"""
        intent = skill_builder._classify_requirement("Check hotel prices in Paris")
        assert intent.skill_name
        assert len(intent.skill_name) <= 40
        assert "_" in intent.skill_name or len(intent.skill_name.split()) == 1

    def test_external_send_detection(self, skill_builder):
        """Detect when requirement implies client-facing send"""
        intent = skill_builder._classify_requirement("Send email to all clients")
        assert intent.requires_external_send is True

        intent = skill_builder._classify_requirement("Format email body")
        assert intent.requires_external_send is False


# ============================================================================
# UNIT TESTS — CONSTRAINTS
# ============================================================================

class TestSkillConstraints:
    """Test constraint validation"""

    def test_constraint_no_subprocess(self):
        """Reject code using subprocess module"""
        code = """
import subprocess
def my_skill():
    subprocess.run(["ls"])
"""
        valid, msg = validate_skill_constraint(code)
        assert not valid
        assert "subprocess" in msg.lower()

    def test_constraint_no_exec(self):
        """Reject code using exec()"""
        code = "def my_skill():\n    exec('print(1)')"
        valid, msg = validate_skill_constraint(code)
        assert not valid

    def test_constraint_no_eval(self):
        """Reject code using eval()"""
        code = "def my_skill():\n    x = eval('1+1')"
        valid, msg = validate_skill_constraint(code)
        assert not valid

    def test_constraint_no_shell_true(self):
        """Reject code using shell=True"""
        code = 'import subprocess\nsubprocess.run("ls", shell=True)'
        valid, msg = validate_skill_constraint(code)
        assert not valid

    def test_constraint_safe_code_passes(self):
        """Accept safe code"""
        code = """
def check_price(city: str) -> dict:
    if not city:
        return {"error": "city required"}
    return {"city": city, "price": 100}
"""
        valid, msg = validate_skill_constraint(code)
        assert valid


# ============================================================================
# UNIT TESTS — NAMING RULES
# ============================================================================

class TestSkillNamingRules:
    """Test skill name validation"""

    def test_valid_skill_names(self):
        """Accept valid skill names"""
        valid_names = ["check_hotel_prices", "monitor_cruise_news", "format_csv"]
        for name in valid_names:
            is_valid, msg = validate_skill_name(name)
            assert is_valid, f"{name} should be valid: {msg}"

    def test_invalid_skill_names(self):
        """Reject invalid skill names"""
        invalid_names = [
            "_check_price",  # starts with underscore
            "CheckPrice",  # mixed case
            "check-price",  # hyphen
            "x",  # too short
            "a" * 100,  # too long
        ]
        for name in invalid_names:
            is_valid, msg = validate_skill_name(name)
            assert not is_valid, f"{name} should be invalid"


# ============================================================================
# INTEGRATION TESTS — CODE GENERATION
# ============================================================================

class TestCodeGeneration:
    """Test skill code generation (mocked Sonnet calls)"""

    @patch("core.ai_infra.thunderbird_skill_builder.Anthropic")
    def test_generate_valid_python(self, mock_anthropic_class, skill_builder):
        """Generated code is syntactically valid Python"""
        # Mock Sonnet response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="""
def check_hotel_prices(city: str, star_rating: int = 4) -> dict:
    if not isinstance(city, str):
        return {"error": "city must be string"}
    return {"city": city, "hotels": []}
""")]
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_class.return_value = mock_client
        skill_builder.client = mock_client

        intent = SkillIntent("Check hotel prices", SkillDomain.TRAVEL, "check_hotels", False)
        code = skill_builder._generate_skill_code("Check hotel prices", intent)

        # Should be compilable
        try:
            compile(code, "test", "exec")
        except SyntaxError as e:
            pytest.fail(f"Generated code has syntax error: {e}")

    @patch("core.ai_infra.thunderbird_skill_builder.Anthropic")
    def test_generate_includes_type_hints(self, mock_anthropic_class, skill_builder):
        """Generated code includes type hints"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="""
def check_hotels(city: str) -> dict:
    return {"hotels": []}
""")]
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_class.return_value = mock_client
        skill_builder.client = mock_client

        intent = SkillIntent("Check hotels", SkillDomain.TRAVEL, "check_hotels", False)
        code = skill_builder._generate_skill_code("Check hotels", intent)

        assert ":" in code  # Type hints use colons
        assert "->" in code  # Return type annotation

    @patch("core.ai_infra.thunderbird_skill_builder.Anthropic")
    def test_generate_includes_error_handling(self, mock_anthropic_class, skill_builder):
        """Generated code includes error handling"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="""
def check_hotels(city: str) -> dict:
    try:
        return {"hotels": []}
    except Exception as e:
        return {"error": str(e)}
""")]
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_class.return_value = mock_client
        skill_builder.client = mock_client

        intent = SkillIntent("Check hotels", SkillDomain.TRAVEL, "check_hotels", False)
        code = skill_builder._generate_skill_code("Check hotels", intent)

        assert "try:" in code
        assert "except" in code


# ============================================================================
# INTEGRATION TESTS — END-TO-END SKILL BUILDING
# ============================================================================

class TestSkillBuilding:
    """Test full skill building workflow"""

    @patch("core.ai_infra.thunderbird_skill_builder.Anthropic")
    def test_build_skill_creates_files(self, mock_anthropic_class, skill_builder):
        """Building a skill creates Python file and test file"""
        # Mock Sonnet responses
        mock_client = MagicMock()

        # Mock skill code generation
        skill_response = MagicMock()
        skill_response.content = [MagicMock(text="""
def check_hotel_prices(city: str) -> dict:
    if not city:
        return {"error": "city required"}
    return {"city": city, "hotels": []}
""")]

        # Mock test code generation
        test_response = MagicMock()
        test_response.content = [MagicMock(text="""
import pytest

def test_valid_city():
    result = check_hotel_prices("Paris")
    assert "hotels" in result

def test_empty_city():
    result = check_hotel_prices("")
    assert "error" in result
""")]

        mock_client.messages.create.side_effect = [skill_response, test_response]
        mock_anthropic_class.return_value = mock_client
        skill_builder.client = mock_client

        # Build skill
        result = skill_builder.build_skill("Check hotel prices in any city", "7554895206")

        # Verify result
        assert result.success
        assert result.skill_name
        assert result.file_path.exists()
        assert result.test_file_path.exists()

        # Verify file contents
        code = result.file_path.read_text()
        assert "def " in code
        assert "hotel" in code.lower()

        tests = result.test_file_path.read_text()
        assert "def test_" in tests

    def test_build_skill_with_constraint_violation(self, skill_builder):
        """Building skill with client-facing send requirement fails"""
        with pytest.raises(SkillConstraintError):
            skill_builder.build_skill("Send email to all clients", "7554895206")

    @patch("core.ai_infra.thunderbird_skill_builder.Anthropic")
    def test_build_skill_stores_metadata(self, mock_anthropic_class, skill_builder):
        """Skill generation stores metadata JSON"""
        # Mock responses
        mock_client = MagicMock()
        skill_response = MagicMock()
        skill_response.content = [MagicMock(text="def test_skill(): return {}")]
        test_response = MagicMock()
        test_response.content = [MagicMock(text="def test_test(): pass")]
        mock_client.messages.create.side_effect = [skill_response, test_response]
        mock_anthropic_class.return_value = mock_client
        skill_builder.client = mock_client

        result = skill_builder.build_skill("Test skill", "7554895206")

        # Check metadata file
        metadata_file = result.file_path.with_suffix(".json")
        assert metadata_file.exists()

        import json
        metadata = json.loads(metadata_file.read_text())
        assert "created" in metadata
        assert metadata["commander_id"] == "7554895206"
        assert metadata["domain"] == "generic"


# ============================================================================
# INTEGRATION TESTS — MCP REGISTRATION (MOCK)
# ============================================================================

class TestMCPIntegration:
    """Test MCP server hot-reload (mocked)"""

    @patch("core.ai_infra.thunderbird_skill_builder.Anthropic")
    def test_skill_registration_metadata(self, mock_anthropic_class, skill_builder):
        """Generated skill includes all metadata for MCP registration"""
        mock_client = MagicMock()
        skill_response = MagicMock()
        skill_response.content = [MagicMock(text="def hotel_checker(): pass")]
        test_response = MagicMock()
        test_response.content = [MagicMock(text="pass")]
        mock_client.messages.create.side_effect = [skill_response, test_response]
        mock_anthropic_class.return_value = mock_client
        skill_builder.client = mock_client

        result = skill_builder.build_skill("Check hotels", "7554895206")

        # Metadata should enable MCP registration
        assert result.metadata["skill_name"]
        assert result.metadata["domain"]
        assert result.metadata["created"]


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

class TestPerformance:
    """Test skill builder performance"""

    @patch("core.ai_infra.thunderbird_skill_builder.Anthropic")
    def test_build_skill_completes_in_reasonable_time(self, mock_anthropic_class, skill_builder):
        """Skill building completes within 30 seconds (mocked)"""
        import time

        mock_client = MagicMock()
        skill_response = MagicMock()
        skill_response.content = [MagicMock(text="def s(): return {}")]
        test_response = MagicMock()
        test_response.content = [MagicMock(text="pass")]
        mock_client.messages.create.side_effect = [skill_response, test_response]
        mock_anthropic_class.return_value = mock_client
        skill_builder.client = mock_client

        start = time.time()
        result = skill_builder.build_skill("Test", "7554895206")
        elapsed = time.time() - start

        assert result.success
        assert elapsed < 30  # Should be very fast with mocks


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
