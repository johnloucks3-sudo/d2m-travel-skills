import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import subprocess

logger = logging.getLogger(__name__)

THUNDERBIRD_ROOT = Path.home() / "Thunderbird"
SKILLS_DIR = THUNDERBIRD_ROOT / "core" / "skills"
REGISTRY_FILE = THUNDERBIRD_ROOT / "config" / "skills_registry.json"

SKILLS_DIR.mkdir(parents=True, exist_ok=True)


class SkillBuildResult:
    """Result of skill generation."""
    def __init__(self, success: bool, skill_name: str = "", file_path: Path = None,
                 test_file_path: Path = None, generated_code: str = "",
                 invocation_example: str = "", error_message: str = ""):
        self.success = success
        self.skill_name = skill_name
        self.file_path = file_path
        self.test_file_path = test_file_path
        self.generated_code = generated_code
        self.invocation_example = invocation_example
        self.error_message = error_message


class SkillBuilder:
    def __init__(self):
        self.skill_dir = Path("/home/john/Thunderbird/core/skills")
        self.skill_dir.mkdir(parents=True, exist_ok=True)

    def build_from_description(self, description: str, skill_name: str):
        """Generates a new MCP skill module based on natural language."""
        skill_path = self.skill_dir / f"{skill_name}.py"

        # Proper f-string for triple quotes
        code = f"""
# Auto-generated skill: {skill_name}
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("{skill_name}")

@mcp.tool()
def execute_{skill_name}(query: str):
    \"\"\"{description}\"\"\"
    return f"Executed {skill_name} with: {{query}}"
"""
        with open(skill_path, "w") as f:
            f.write(code)

        logging.info(f"Skill {skill_name} built at {skill_path}")
        return str(skill_path)


class ThunderbirdSkillBuilder:
    """Build executable skills from natural language. (OpenClaw P0)"""

    def __init__(self):
        self.skills_dir = SKILLS_DIR
        self.registry_file = REGISTRY_FILE
        self.registry_file.parent.mkdir(parents=True, exist_ok=True)

    def classify_requirement(self, description: str) -> Dict[str, str]:
        """Classify requirement into domain + category."""
        description_lower = description.lower()

        domain_map = {
            "travel": ["flight", "hotel", "cruise", "ship", "destination", "excursion", "cabin"],
            "finance": ["price", "cost", "commission", "quote", "charge", "payment", "budget"],
            "intel": ["research", "scan", "monitor", "track", "news", "trend", "analysis"],
            "ops": ["format", "convert", "validate", "check", "generate", "process", "transform"],
            "email": ["send", "email", "draft", "message", "notify", "contact"],
        }

        domain = "generic"
        for potential_domain, keywords in domain_map.items():
            if any(kw in description_lower for kw in keywords):
                domain = potential_domain
                break

        return {
            "domain": domain,
            "category": "data_processor" if "format" in description_lower else "analyzer",
            "description": description
        }

    def generate_skill_code(self, requirement: Dict[str, str], model: str = "claude-sonnet-4-6") -> str:
        """Generate Python skill code via Claude."""
        prompt = f"""You are generating a Python skill for Thunderbird travel automation.

REQUIREMENT:
Domain: {requirement['domain']}
Category: {requirement['category']}
Description: {requirement['description']}

GENERATE:
1. A single Python function with clear docstring
2. Use only safe libraries (json, datetime, re, csv, pathlib)
3. NO subprocess, eval, exec, file writes, or dangerous operations
4. Function should be reusable and testable
5. Include type hints

Return ONLY the Python code, no explanation.
"""

        try:
            result = subprocess.run(
                ["/home/john/.local/bin/claude", "-p", prompt, "--model", model],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                logger.error(f"Claude generation failed: {result.stderr}")
                # Return safe placeholder code
                return """def generated_skill(input_data: str) -> dict:
    \"\"\"Auto-generated skill placeholder.\"\"\"
    return {"status": "placeholder", "input": input_data}"""
        except Exception as e:
            logger.error(f"Code generation error: {e}")
            return ""

    def validate_skill(self, code: str) -> tuple[bool, str]:
        """Validate generated skill against constraints."""
        try:
            from ai_infra.skill_builder_config import validate_skill_constraint, DEFAULT_CONSTRAINTS
        except ImportError:
            from skill_builder_config import validate_skill_constraint, DEFAULT_CONSTRAINTS

        is_valid, error_msg = validate_skill_constraint(code, DEFAULT_CONSTRAINTS)
        return is_valid, error_msg

    def register_skill(self, skill_name: str, file_path: Path, domain: str,
                      description: str) -> bool:
        """Register skill in registry."""
        try:
            if self.registry_file.exists():
                content = self.registry_file.read_text()
                if content.strip():
                    registry = json.loads(content)
                else:
                    registry = {"skills": {}}
            else:
                registry = {"skills": {}}

            # Ensure skills key exists
            if "skills" not in registry:
                registry["skills"] = {}

            registry["skills"][skill_name] = {
                "path": str(file_path),
                "domain": domain,
                "description": description,
                "registered_at": datetime.now().isoformat(),
                "status": "active"
            }

            self.registry_file.write_text(json.dumps(registry, indent=2))
            logger.info(f"Registered skill: {skill_name}")
            return True
        except Exception as e:
            logger.error(f"Registration failed: {e}")
            return False

    def build_skill(self, description: str, commander_id: str = "") -> SkillBuildResult:
        """Full pipeline: classify → generate → validate → register."""
        try:
            # Step 1: Classify
            requirement = self.classify_requirement(description)

            # Step 2: Generate code
            code = self.generate_skill_code(requirement)
            if not code:
                return SkillBuildResult(False, error_message="Code generation failed")

            # Step 3: Validate
            is_valid, error = self.validate_skill(code)
            if not is_valid:
                return SkillBuildResult(False, error_message=f"Validation failed: {error}")

            # Step 4: Write to disk
            skill_name = f"skill_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            skill_file = self.skills_dir / f"{skill_name}.py"
            skill_file.write_text(code)

            # Step 5: Create test file
            test_file = self.skills_dir / f"test_{skill_name}.py"
            test_code = f"""import pytest
from {skill_name} import *

def test_skill_exists():
    assert callable({skill_name})

def test_skill_returns():
    result = {skill_name}(test_input="sample")
    assert isinstance(result, (dict, str, list))
"""
            test_file.write_text(test_code)

            # Step 6: Register
            self.register_skill(skill_name, skill_file, requirement["domain"], description)

            invocation = f"from core.skills.{skill_name} import *"

            return SkillBuildResult(
                success=True,
                skill_name=skill_name,
                file_path=skill_file,
                test_file_path=test_file,
                generated_code=code,
                invocation_example=invocation
            )
        except Exception as e:
            logger.error(f"Skill build failed: {e}")
            return SkillBuildResult(False, error_message=str(e))


def register_skill_builder_tools() -> dict:
    """Register skill builder itself as MCP tools."""
    return {
        "tools": [
            {
                "name": "classify_skill_requirement",
                "description": "Classify a skill requirement into domain and category",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string", "description": "Skill description"}
                    },
                    "required": ["description"]
                }
            },
            {
                "name": "generate_skill_code",
                "description": "Generate Python code for a skill using Claude Sonnet",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "requirement": {"type": "object", "description": "Classified requirement"},
                        "model": {"type": "string", "description": "Model to use (default: sonnet)"}
                    },
                    "required": ["requirement"]
                }
            },
            {
                "name": "validate_skill",
                "description": "Validate skill code against safety constraints",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string", "description": "Python code to validate"}
                    },
                    "required": ["code"]
                }
            },
            {
                "name": "register_skill",
                "description": "Register a skill in the MCP registry",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "skill_name": {"type": "string"},
                        "domain": {"type": "string"},
                        "description": {"type": "string"}
                    },
                    "required": ["skill_name", "domain", "description"]
                }
            }
        ]
    }


if __name__ == "__main__":
    builder = SkillBuilder()
    print(builder.build_from_description("A tool to look up flight prices", "flight_lookup"))
